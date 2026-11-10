"""Ca đóng gói (Packhouse Shift): the bunches it took in, by lô and ribbon colour from confirmed harvest lines of the sổ lô,
and what it packed. Spec 002 (US6): the shift is entered on its own (no Packout Run, no Harvest Lot); cartons and
finished goods are split over its sources by kg (packout_rules). The stock receipt of finished goods is a separate,
draft document made by the accountant (finance.costing.receive_shift). ERP remains the stock authority."""
import frappe
from frappe.utils import add_days, cint, flt, get_datetime, getdate, nowdate

from lotus_farm import packout_rules as rules
from lotus_farm.controls import lock, whole_count
from lotus_farm.daily_operations import DailyDocument, day_guard, number

SHIFT, SOURCE, ENTRY = "Packhouse Shift", "Packhouse Shift Source", "Lotus Work Entry"
TRACE_DAYS = 90


def _harvested(blocks_tags):
    """Confirmed harvest of these (lô, màu): {(lô, màu): bunches}."""
    if not blocks_tags:
        return {}
    rows = frappe.get_all(ENTRY, filters={"stage": "Harvest", "state": "Confirmed", "farm_block": ["in", sorted({b for b, _ in blocks_tags})]},
                          fields=["farm_block", "bunch_tag", "qty"], limit_page_length=0)
    out = {}
    for r in rows:
        key = (r.farm_block, r.bunch_tag)
        if key in blocks_tags:
            out[key] = out.get(key, 0) + cint(r.qty)
    return out


def _received_elsewhere(blocks_tags, shift_name=None):
    """Bunches of these (lô, màu) already taken by other shifts that are not cancelled."""
    if not blocks_tags:
        return {}
    rows = frappe.db.sql(f"""select s.farm_block, s.bunch_tag, sum(s.bunches) as bunches from `tab{SOURCE}` s
                             join `tab{SHIFT}` p on p.name = s.parent and s.parenttype = %(shift)s
                             where p.docstatus < 2 and p.name != %(name)s and s.farm_block in %(blocks)s
                             group by s.farm_block, s.bunch_tag""",
                         {"shift": SHIFT, "name": shift_name or "", "blocks": sorted({b for b, _ in blocks_tags})}, as_dict=True)
    return {(r.farm_block, r.bunch_tag): cint(r.bunches) for r in rows if (r.farm_block, r.bunch_tag) in blocks_tags}


class ShiftDocument(DailyDocument):
    def validate_daily(self):
        if get_datetime(self.ended_at) <= get_datetime(self.started_at):
            frappe.throw("Giờ kết thúc ca phải sau giờ bắt đầu.")
        if getdate(self.started_at) != getdate(self.posting_date):
            frappe.throw("Giờ bắt đầu ca phải đúng ngày làm việc.")
        if frappe.db.exists(self.doctype, {"farm": self.farm, "posting_date": self.posting_date, "shift_code": self.shift_code, "docstatus": ["<", 2],
                                           "name": ["!=", self.name]}):
            frappe.throw("Ca này đã tồn tại cho vườn/ngày.")
        self._check_labor()
        for row in self.preprocessing:
            if whole_count(row.processed_bunches, "Processed bunches") < 1:
                frappe.throw("Sơ chế cần số buồng là số nguyên dương.")
            number(row.processed_kg, "Processed kg", positive=True)
            if row.started_at and row.ended_at and get_datetime(row.ended_at) <= get_datetime(row.started_at):
                frappe.throw("Giờ kết thúc sơ chế phải sau giờ bắt đầu.")
        self._check_sources()
        self.input_kg = round(sum(flt(s.kg) for s in self.sources), 3)
        result = rules.outputs(self.input_kg, self.finished_kg, self.secondary_kg)
        if result.get("error"):
            frappe.throw(result["error"])
        self.loss_kg, self.packout_percent = result["loss_kg"], result["packout_percent"]
        if cint(self.cartons) < 0:
            frappe.throw("Số thùng không được âm.")

    def _check_labor(self):
        seen = set()
        for row in self.labor:
            if row.employee in seen:
                frappe.throw("Nhân viên xuất hiện hai lần trong ca.")
            seen.add(row.employee)
            employee = frappe.get_doc("Employee", row.employee)
            employee.check_permission("read")
            lock("Employee", row.employee)
            if employee.company != self.company or employee.status != "Active":
                frappe.throw("Nhân viên của ca phải đang làm việc trong công ty này.")
            days = number(row.workdays, "Shift workdays", positive=True)
            other = frappe.db.sql(f"""select l.workdays from `tabPackhouse Shift Labor` l join `tab{SHIFT}` s on s.name = l.parent
                                      where s.posting_date = %s and s.docstatus = 1 and l.employee = %s and s.name != %s FOR UPDATE""",
                                  (self.posting_date, row.employee, self.name))
            # Buổi in the field (sổ lô): each buổi is half a công.
            field_days = flt(frappe.db.sql("""select count(distinct session) from `tabLotus Work Session` where employee = %s and posting_date = %s""",
                                           (row.employee, self.posting_date))[0][0]) / 2
            capacity = 1
            if frappe.db.exists("DocType", "Attendance"):
                statuses = set(frappe.get_all("Attendance", filters={"employee": row.employee, "attendance_date": self.posting_date, "docstatus": 1},
                                              pluck="status"))
                capacity = 0 if statuses & {"Absent", "On Leave"} else (0.5 if "Half Day" in statuses else 1)
            if sum(flt(v[0]) for v in other) + field_days + days > capacity + 0.000001:
                frappe.throw(f"{employee.employee_name}: công ngoài vườn và ở xưởng vượt một công trong ngày.")

    def _check_sources(self):
        rows = [s.as_dict() for s in self.sources]
        errors = rules.check_sources(rows)
        blocks = {b.name: b for b in frappe.get_all("Farm Block", filters={"name": ["in", [s.farm_block for s in self.sources] or [""]]},
                                                       fields=["name", "farm", "block_code"])}
        tags = {t.name: t for t in frappe.get_all("Bunch Tag", filters={"name": ["in", [s.bunch_tag for s in self.sources] or [""]]},
                                                  fields=["name", "farm", "color_label"])}
        for index, s in enumerate(self.sources, 1):
            if blocks.get(s.farm_block, frappe._dict()).farm != self.farm:
                errors.append(f"Dòng {index}: lô không thuộc vườn của ca.")
            if tags.get(s.bunch_tag, frappe._dict()).farm != self.farm:
                errors.append(f"Dòng {index}: đợt màu không thuộc vườn của ca.")
            if s.harvest_entry:
                line = frappe.db.get_value(ENTRY, s.harvest_entry, ["farm_block", "bunch_tag", "stage", "state", "posting_date"], as_dict=True)
                if not line or line.stage != "Harvest" or line.state != "Confirmed" or (line.farm_block, line.bunch_tag) != (s.farm_block, s.bunch_tag):
                    errors.append(f"Dòng {index}: dòng thu hoạch phải đã xác nhận, cùng lô và đợt màu.")
                elif getdate(line.posting_date) > getdate(self.posting_date):
                    errors.append(f"Dòng {index}: buồng thu sau ngày của ca.")
        if errors:
            frappe.throw("<br>".join(errors))
        keys = {(s.farm_block, s.bunch_tag) for s in self.sources}
        for key in sorted(keys):
            lock("Farm Block", key[0])
        for over in rules.over_received(rows, _harvested(keys), _received_elsewhere(keys, None if self.is_new() else self.name)):
            block = blocks[over["farm_block"]].block_code
            colour = tags[over["bunch_tag"]].color_label or over["bunch_tag"]
            errors.append(f"Lô {block}, màu {colour}: nhận {over['bunches']} buồng nhưng chỉ còn {over['left']} buồng đã thu chưa vào xưởng.")
        if errors:
            frappe.throw("<br>".join(errors))

    def before_submit(self):
        if not self.sources:
            frappe.throw("Ca cần nguồn buồng: lô và đợt màu đã thu.")
        if flt(self.finished_kg) <= 0:
            frappe.throw("Ca cần số kg thành phẩm.")

    def before_cancel(self):
        day_guard(self)
        state = frappe.db.get_value("Stock Entry", self.stock_entry, "docstatus") if self.stock_entry else None
        if state == 1:
            frappe.throw("Ca đã nhập kho thành phẩm. Hủy phiếu nhập kho trước khi hủy ca.")
        receipt, self.stock_entry = self.stock_entry, None
        if state == 0:
            # A draft receipt goes with its shift: left behind it could be neither submitted nor deleted.
            frappe.db.set_value(SHIFT, self.name, "stock_entry", None, update_modified=False)
            frappe.delete_doc("Stock Entry", receipt, ignore_permissions=True)


def release_receipt(doc, method=None):
    """Stock Entry before_cancel and on_trash: the shift lets go of its receipt, so a posted receipt can be cancelled and
    a wrong draft deleted (the shift can then be received again). Without this the two documents hold each other."""
    name = doc.get("lotus_packhouse_shift")
    if name and frappe.db.get_value(SHIFT, name, "stock_entry") == doc.name:
        frappe.db.set_value(SHIFT, name, "stock_entry", None, update_modified=False)


def shift_summary(shift):
    """Legacy: the Packout Runs of a shift (old chain, removed with the legacy tables)."""
    result = dict(input_kg=0, finished_kg=0, secondary_kg=0, loss_kg=0, cartons=0, packout_percent=None, runs=[])
    if not frappe.db.exists("DocType", "Packout Run"):
        return result
    for name in frappe.get_list("Packout Run", filters={"packhouse_shift": shift.name, "docstatus": ["<", 2]}, pluck="name", limit_page_length=10000):
        run = frappe.get_doc("Packout Run", name)
        run.check_permission("read")
        result["runs"].append(dict(name=name, docstatus=run.docstatus,
                                   stock_status=frappe.db.get_value("Stock Entry", run.stock_entry, "docstatus") if run.stock_entry else None))
        if run.docstatus != 1:
            continue
        result["input_kg"] += flt(run.input_kg)
        result["loss_kg"] += flt(run.reject_kg) + flt(run.other_loss_kg)
        for row in run.outputs:
            result["finished_kg" if row.output_type == "Finished" else "secondary_kg"] += flt(row.net_kg)
            if row.output_type == "Finished":
                result["cartons"] += int(row.cartons or 0)
    if result["input_kg"]:
        result["packout_percent"] = result["finished_kg"] / result["input_kg"] * 100
    return result


def shift_link_guard(doc, method=None):
    if not doc.get("packhouse_shift"):
        return
    shift = frappe.get_doc(SHIFT, doc.packhouse_shift)
    shift.check_permission("read")
    lock(SHIFT, shift.name)
    date = doc.get("packing_date") or doc.get("posting_date")
    if shift.farm != doc.farm or getdate(date) != getdate(shift.posting_date):
        frappe.throw("Ca phải khớp vườn và ngày làm việc.")
    if shift.docstatus != 0:
        frappe.throw("Ca đã đóng/hủy không nhận thay đổi; mở lại bằng cách hủy rồi lập bản sửa.")


def scale_link_guard(doc, method=None):
    references = [(doc.get("scale_reading"), doc.get("gross_weight_kg") or doc.get("released_raw_kg"))]
    if doc.doctype == "Packout Run":
        references = [(r.get("scale_reading"), r.net_kg) for r in doc.outputs]
    for name, weight in references:
        if not name:
            continue
        reading = frappe.get_doc("Scale Reading", name)
        reading.check_permission("read")
        if reading.farm != doc.farm or abs(flt(reading.net_kg) - flt(weight)) > 0.0005:
            frappe.throw("Vườn/số kg tịnh của lần cân phải khớp giao dịch.")


# ---------------------------------------------------------------- Xưởng screen (lotus_farm.shift.*)

def _require(farm, write=False):
    """Packhouse staff are not in the field teams: the shift's own permission and the farm scope decide."""
    from lotus_farm.controls import farm_allowed
    if frappe.session.user == "Guest" or not farm or not farm_allowed(farm):
        frappe.throw("Bạn không có quyền với vườn này.", frappe.PermissionError)
    if frappe.has_permission(SHIFT, "write" if write else "read") or (not write and _can_receive()):
        return
    frappe.throw("Bạn không có quyền với ca đóng gói.", frappe.PermissionError)


def can_open():
    """The Xưởng screen: whoever may read shifts, and the accountant who receives closed shifts into stock."""
    return bool(frappe.has_permission(SHIFT, "read") or _can_receive())


def _read(doc):
    from lotus_farm.controls import farm_allowed
    if _can_receive() and farm_allowed(doc.farm):
        return
    doc.check_permission("read")


def _labels(farm):
    blocks = {b.name: b.block_code for b in frappe.get_all("Farm Block", filters={"farm": farm}, fields=["name", "block_code"], limit_page_length=0)}
    tags = {t.name: {"label": t.color_label or t.name, "code": t.color_code or "", "week": t.week_number}
            for t in frappe.get_all("Bunch Tag", filters={"farm": farm}, fields=["name", "color_label", "color_code", "week_number"], limit_page_length=0)}
    return blocks, tags


@frappe.whitelist()
def harvest_sources(farm, date=None, name=None):
    """Confirmed harvest lines up to the shift day whose bunches are not all in a shift yet, newest first."""
    _require(farm)
    day = getdate(date or nowdate())
    lines = frappe.get_all(ENTRY, filters={"farm": farm, "stage": "Harvest", "state": "Confirmed", "posting_date": ["between", [add_days(day, -TRACE_DAYS), day]]},
                           fields=["name", "farm_block", "bunch_tag", "posting_date", "qty", "weight_kg", "work_team"],
                           order_by="posting_date desc, creation desc", limit_page_length=0)
    keys = {(l.farm_block, l.bunch_tag) for l in lines}
    # Bunches other shifts already took are counted against the oldest harvest lines of the lô and colour first, so each
    # line shows what is still left of that line and a line fully packed is no longer offered.
    taken = _received_elsewhere(keys, name)
    remaining = {}
    for h in frappe.get_all(ENTRY, filters={"farm": farm, "stage": "Harvest", "state": "Confirmed", "posting_date": ["<=", day],
                                            "farm_block": ["in", sorted({b for b, _ in keys}) or [""]]},
                            fields=["name", "farm_block", "bunch_tag", "qty"], order_by="posting_date asc, creation asc", limit_page_length=0):
        key = (h.farm_block, h.bunch_tag)
        if key not in keys:
            continue
        used = min(cint(h.qty), taken.get(key, 0))
        taken[key] = taken.get(key, 0) - used
        remaining[h.name] = cint(h.qty) - used
    blocks, tags = _labels(farm)
    out = []
    for l in lines:
        left = remaining.get(l.name, 0)
        if left <= 0:
            continue
        out.append({"harvest_entry": l.name, "farm_block": l.farm_block, "block_code": blocks.get(l.farm_block, ""), "bunch_tag": l.bunch_tag,
                    "colour": tags.get(l.bunch_tag, {}).get("label", ""), "colour_code": tags.get(l.bunch_tag, {}).get("code", ""),
                    "week": tags.get(l.bunch_tag, {}).get("week"), "posting_date": str(l.posting_date), "bunches": cint(l.qty),
                    "kg": flt(l.weight_kg), "left": left})
    return out


SHIFT_FIELDS = ["name", "shift_code", "posting_date", "docstatus", "input_kg", "finished_kg", "secondary_kg", "loss_kg", "cartons", "packout_percent",
                "stock_entry", "modified"]


@frappe.whitelist()
def shifts(farm, from_date=None, to_date=None):
    _require(farm)
    end = getdate(to_date or nowdate())
    begin = getdate(from_date or add_days(end, -30))
    reader = frappe.get_list if frappe.has_permission(SHIFT, "read") else frappe.get_all  # the accountant passed _require
    rows = reader(SHIFT, filters={"farm": farm, "posting_date": ["between", [begin, end]], "docstatus": ["<", 2]}, fields=SHIFT_FIELDS,
                           order_by="posting_date desc, shift_code asc", limit_page_length=0)
    counts = {r.parent: (cint(r.bunches), cint(r.lots)) for r in frappe.db.sql(
        f"select parent, sum(bunches) as bunches, count(distinct farm_block) as lots from `tab{SOURCE}` where parent in %(names)s group by parent",
        {"names": [r.name for r in rows] or [""]}, as_dict=True)}
    receipts = {r.name: r.docstatus for r in frappe.get_all("Stock Entry", filters={"name": ["in", [r.stock_entry for r in rows if r.stock_entry] or [""]]},
                                                           fields=["name", "docstatus"])}
    return [dict(r, posting_date=str(r.posting_date), bunches=counts.get(r.name, (0, 0))[0], lots=counts.get(r.name, (0, 0))[1],
                 receipt_state=_live(receipts.get(r.stock_entry))) for r in rows]


def _live(docstatus):
    """A cancelled receipt counts as no receipt: the shift can be received again."""
    return docstatus if docstatus in (0, 1) else None


@frappe.whitelist()
def shift(name):
    doc = frappe.get_doc(SHIFT, name)
    _read(doc)
    blocks, tags = _labels(doc.farm)
    sources = [dict(s.as_dict(), block_code=blocks.get(s.farm_block, ""), colour=tags.get(s.bunch_tag, {}).get("label", "")) for s in doc.sources]
    split = rules.split([{k: s[k] for k in ("farm_block", "bunch_tag", "bunches", "kg", "harvest_entry", "block_code", "colour")} for s in sources],
                        doc.finished_kg, doc.secondary_kg, doc.cartons)
    return {"doc": doc.as_dict(), "split": split, "can_write": frappe.has_permission(SHIFT, "write", doc),
            "can_receive": _can_receive(),
            "receipt_state": _live(frappe.db.get_value("Stock Entry", doc.stock_entry, "docstatus")) if doc.stock_entry else None}


def _can_receive():
    try:
        from lotus_farm.finance import setup as finance_setup
        return bool(finance_setup.can_post())
    except Exception:
        return False


@frappe.whitelist(methods=["POST"])
def save_shift(farm, values, name=None, expected_modified=None):
    """Create or change a draft shift: code, times, sources (lô, đợt màu, buồng, kg, dòng thu hoạch) and what it packed."""
    _require(farm, write=True)
    values = frappe.parse_json(values) if isinstance(values, str) else values
    if name:
        doc = frappe.get_doc(SHIFT, name)
        if doc.docstatus != 0:
            frappe.throw("Ca đã đóng; muốn sửa thì hủy rồi lập bản sửa.")
        if expected_modified and str(doc.modified) != str(expected_modified):
            frappe.throw("Ca vừa được người khác sửa. Tải lại rồi làm tiếp.")
    else:
        doc = frappe.new_doc(SHIFT)
        doc.update({"farm": farm, "company": frappe.db.get_value("Farm", farm, "company"), "supervisor": frappe.session.user})
    for key in ("shift_code", "posting_date", "started_at", "ended_at", "finished_kg", "secondary_kg", "cartons", "notes"):
        if key in values:
            doc.set(key, values.get(key))
    if "sources" in values:
        doc.set("sources", [])
        for s in values.get("sources") or []:
            doc.append("sources", {"farm_block": s.get("farm_block"), "bunch_tag": s.get("bunch_tag"), "bunches": cint(s.get("bunches")),
                                   "kg": flt(s.get("kg")), "harvest_entry": s.get("harvest_entry") or None})
    doc.save()
    return shift(doc.name)


@frappe.whitelist(methods=["POST"])
def close_shift(name, expected_modified=None):
    doc = frappe.get_doc(SHIFT, name)
    if expected_modified and str(doc.modified) != str(expected_modified):
        frappe.throw("Ca vừa được người khác sửa. Tải lại rồi làm tiếp.")
    doc.submit()
    return shift(name)


@frappe.whitelist()
def trace(shift):
    """Where the fruit of a shift came from: each source → its harvest lines → the spraying on that lô in the
    TRACE_DAYS before the harvest (product, dose, cách ly)."""
    doc = frappe.get_doc(SHIFT, shift)
    _read(doc)
    blocks, tags = _labels(doc.farm)
    out = []
    for s in doc.sources:
        harvests = frappe.get_all(ENTRY, filters={"farm_block": s.farm_block, "bunch_tag": s.bunch_tag, "stage": "Harvest", "state": "Confirmed",
                                                  "posting_date": ["<=", doc.posting_date]},
                                  fields=["name", "posting_date", "qty", "weight_kg", "work_team", "daily_report"], order_by="posting_date asc",
                                  limit_page_length=0)
        if s.harvest_entry:
            harvests = [h for h in harvests if h.name == s.harvest_entry] or harvests
        last = max([getdate(h.posting_date) for h in harvests] or [getdate(doc.posting_date)])
        sprays = frappe.db.sql(f"""select e.name, e.posting_date, e.work_type, w.work_name, m.item_code, i.item_name, m.qty, m.dose,
                                          i.lotus_phi_days as phi_days
                                   from `tab{ENTRY}` e join `tabLotus Work Entry Material` m on m.parent = e.name and m.parenttype = %(entry)s
                                   left join `tabItem` i on i.name = m.item_code left join `tabWork Type` w on w.name = e.work_type
                                   where e.farm_block = %(block)s and e.state = 'Confirmed' and e.posting_date between %(begin)s and %(end)s
                                   order by e.posting_date desc""",
                               {"entry": ENTRY, "block": s.farm_block, "begin": add_days(last, -TRACE_DAYS), "end": last}, as_dict=True)
        out.append({"farm_block": s.farm_block, "block_code": blocks.get(s.farm_block, ""), "bunch_tag": s.bunch_tag,
                    "colour": tags.get(s.bunch_tag, {}).get("label", ""), "bunches": s.bunches, "kg": s.kg,
                    "harvests": [dict(h, posting_date=str(h.posting_date)) for h in harvests],
                    "sprays": [dict(r, posting_date=str(r.posting_date)) for r in sprays]})
    return {"shift": doc.name, "posting_date": str(doc.posting_date), "sources": out}
