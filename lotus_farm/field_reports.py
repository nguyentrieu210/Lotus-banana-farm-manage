"""Báo cáo theo người xem (spec 002, US5): Sáng nay, Tuần, Tháng.

Each answer is a list of cards: a title, one figure, a tone, and the detail rows the card opens (columns given, so the
screen can show and export them as they are). Everything is read from what already exists: the tổ reports and the sổ lô
(lot_report, lot_ledger), the vòng chăm sóc (care_cycle), the bảng màu dây (ribbon_board), the xưởng (Packhouse Shift)
and the frozen forecast (forecast_snapshot). Nothing here writes.
"""
import datetime as dt

import frappe
from frappe.utils import add_days, cint, flt, get_last_day, getdate, nowdate

from lotus_farm import care_cycle, ribbon_board
from lotus_farm import field_report as field
from lotus_farm import forecast_snapshot
from lotus_farm import lot_report as lr

ENTRY, SHIFT, SOURCE = "Lotus Work Entry", "Packhouse Shift", "Packhouse Shift Source"
STATE_TEXT = {None: "Chưa có báo cáo", "Draft": "Chưa gửi", "Reopened": "Mở lại để sửa", "Sent": "Chờ xác nhận", "Confirmed": "Đã xác nhận"}


def _col(field_, label, kind=None):
    return {"field": field_, "label": label, **({"kind": kind} if kind else {})}


def _card(key, title, value, rows, columns, tone="info", unit="", note=""):
    return {"key": key, "title": title, "value": value, "unit": unit, "tone": tone, "note": note, "rows": rows, "columns": columns}


def _supervised(farm):
    """The đội whose tổ reports this user follows: every đội for the quản lý vườn, else the đội they lead."""
    crews = sorted(field._visible_crews(farm))
    return [c for c in crews if field.access(farm, c).supervisor]


def _codes(farm):
    return {b.name: b.block_code for b in frappe.get_all("Farm Block", filters={"farm": farm}, fields=["name", "block_code"], limit_page_length=0)}


def _works(names):
    return {w.name: w.work_name for w in frappe.get_all("Work Type", filters={"name": ["in", list(names) or [""]]}, fields=["name", "work_name"])}


def _tags(farm):
    return {t.name: t.color_label or t.name for t in frappe.get_all("Bunch Tag", filters={"farm": farm}, fields=["name", "color_label"], limit_page_length=0)}


# ---------------------------------------------------------------- Sáng nay

@frappe.whitelist()
def morning(farm, date=None):
    """What the đội trưởng and the quản lý vườn check first thing: yesterday's reports (not sent, waiting), numbers that
    look wrong, care work overdue, lô under quarantine and colours to harvest."""
    field.require_farm(farm)
    today = getdate(nowdate())
    day = getdate(date) if date else add_days(today, -1)
    crews = _supervised(farm)
    teams_rows, anomalies, overdue = [], [], []
    names = {t.name: t.team_name for t in field._teams(farm)}
    for crew in crews:
        status = lr.status(farm, crew, str(day))
        teams_rows += [dict(t, crew_name=names.get(crew, crew), state_text=STATE_TEXT.get(t["state"], t["state"])) for t in status["teams"]]
        anomalies += [dict(a, crew_name=names.get(crew, crew)) if isinstance(a, dict) else {"message": str(a), "crew_name": names.get(crew, crew)}
                      for a in status["anomalies"]]
        due = care_cycle.due(farm, crew)
        overdue += [r for r in due["rows"] if r["status"] == "overdue"]
    not_sent = [t for t in teams_rows if t["state"] in (None, "Draft", "Reopened")]
    waiting = [t for t in teams_rows if t["state"] == "Sent"]
    held = frappe.get_all("Farm Block", filters={"farm": farm, "active": 1, "lotus_quarantine_until": [">=", today]},
                          fields=["block_code", "farm_zone", "lotus_quarantine_until"], order_by="lotus_quarantine_until asc", limit_page_length=0)
    harvest = ribbon_board.harvest_due(farm)
    team_cols = [_col("crew_name", "Đội"), _col("team_name", "Tổ"), _col("state_text", "Báo cáo"), _col("lines", "Số dòng", "number")]
    cards = [
        _card("not_sent", f"Tổ chưa gửi báo cáo {day.strftime('%d/%m')}", len(not_sent), not_sent, team_cols, "bad" if not_sent else "good", "tổ"),
        _card("waiting", "Báo cáo chờ xác nhận", len(waiting), waiting, team_cols, "warn" if waiting else "good", "tổ"),
        _card("anomalies", "Số bất thường", len(anomalies), anomalies, [_col("crew_name", "Đội"), _col("block", "Lô"), _col("message", "Điều cần xem")],
              "warn" if anomalies else "good", "lô"),
        _card("overdue", "Việc quá hạn vòng chăm sóc", len(overdue),
              [dict(r, last_done=r["last_done"] or "") for r in sorted(overdue, key=lambda r: -r["overdue_days"])],
              [_col("code", "Lô"), _col("work_name", "Việc"), _col("overdue_days", "Quá (ngày)", "number"), _col("last_done", "Xong lần trước", "date"),
               _col("team_name", "Đang giao tổ")], "bad" if overdue else "good", "việc"),
        _card("quarantine", "Lô đang cách ly thuốc", len(held),
              [{"code": h.block_code, "zone": h.farm_zone, "until": str(h.lotus_quarantine_until)} for h in held],
              [_col("zone", "Khu"), _col("code", "Lô"), _col("until", "Cách ly đến", "date")], "warn" if held else "good", "lô"),
        _card("harvest_due", "Màu dây đến tuổi thu", sum(cint(r["left"]) for r in harvest), harvest,
              [_col("code", "Lô"), _col("colour", "Màu"), _col("week", "Tuần cắt", "number"), _col("left", "Còn (buồng)", "number"),
               _col("start", "Thu từ", "date"), _col("end", "Đến", "date"), _col("quarantine_until", "Cách ly đến", "date")],
              "info", "buồng"),
    ]
    return {"date": str(day), "today": str(today), "crews": crews, "cards": cards}


# ---------------------------------------------------------------- Tuần

def _week(week=None):
    if not week:
        day = getdate(nowdate())
    elif "-W" in str(week).upper():
        year, number = str(week).upper().split("-W")
        day = dt.date.fromisocalendar(cint(year), cint(number), 1)
    else:
        day = getdate(week)
    monday = day - dt.timedelta(days=day.weekday())
    return monday, monday + dt.timedelta(days=6)


def lot_status(farm, monday, sunday):
    """Per lô for the map: held by a quarantine, late with care work, harvested in the week, else fine."""
    today = getdate(nowdate())
    blocks = frappe.get_all("Farm Block", filters={"farm": farm, "active": 1}, fields=["name", "block_code", "farm_zone", "lotus_quarantine_until"],
                            limit_page_length=0)
    late = {}
    for crew in field._visible_crews(farm):
        if field.access(farm, crew).read:
            for r in care_cycle.due(farm, crew)["rows"]:
                if r["status"] == "overdue":
                    late[r["farm_block"]] = late.get(r["farm_block"], 0) + 1
    harvested = {r.farm_block: cint(r.qty) for r in frappe.db.sql(f"""select farm_block, sum(qty) as qty from `tab{ENTRY}` where farm = %s and stage = 'Harvest'
        and state = 'Confirmed' and posting_date between %s and %s group by farm_block""", (farm, monday, sunday), as_dict=True)}
    rows = []
    for b in blocks:
        held = b.lotus_quarantine_until and getdate(b.lotus_quarantine_until) >= today
        status = "held" if held else "late" if late.get(b.name) else "harvest" if harvested.get(b.name) else "ok"
        rows.append({"block": b.name, "code": b.block_code, "zone": b.farm_zone or "", "status": status, "late": late.get(b.name, 0),
                     "harvested": harvested.get(b.name, 0), "quarantine_until": str(b.lotus_quarantine_until or "") or None})
    return rows


@frappe.whitelist()
def week(farm, week=None):
    """A week of one farm: work by lô, the bảng màu dây, harvest and the xưởng, the forecast against what came in, and
    the state of each lô for the map."""
    field.require_farm(farm)
    monday, sunday = _week(week)
    codes, tags = _codes(farm), _tags(farm)
    lines = frappe.get_all(ENTRY, filters={"farm": farm, "state": "Confirmed", "posting_date": ["between", [monday, sunday]]},
                           fields=["farm_block", "work_type", "stage", "qty", "uom", "done", "weight_kg", "bunch_tag", "posting_date"], limit_page_length=0)
    names = _works({l.work_type for l in lines})
    work = {}
    for l in lines:
        key = (l.farm_block, l.work_type)
        slot = work.setdefault(key, {"code": codes.get(l.farm_block, ""), "work_name": names.get(l.work_type, l.work_type), "qty": 0.0, "uom": l.uom or "",
                                      "days": set(), "done": False})
        slot["qty"] += flt(l.qty)
        slot["days"].add(str(l.posting_date))
        slot["done"] = slot["done"] or bool(l.done)
    work_rows = sorted(({**v, "days": len(v["days"]), "done": "Xong cả lô" if v["done"] else ""} for v in work.values()),
                       key=lambda r: (len(r["code"]), r["code"], r["work_name"]))
    harvest = [{"date": str(l.posting_date), "code": codes.get(l.farm_block, ""), "colour": tags.get(l.bunch_tag, ""), "bunches": cint(l.qty), "kg": flt(l.weight_kg)}
               for l in lines if l.stage == "Harvest"]
    harvest.sort(key=lambda r: (r["date"], len(r["code"]), r["code"]))
    board = ribbon_board.board(farm)
    shifts = frappe.get_all(SHIFT, filters={"farm": farm, "docstatus": 1, "posting_date": ["between", [monday, sunday]]},
                            fields=["name", "shift_code", "posting_date", "input_kg", "finished_kg", "cartons", "packout_percent"], order_by="posting_date asc",
                            limit_page_length=0)
    key = f"{monday.isocalendar()[0]}-W{monday.isocalendar()[1]:02d}"
    variance = forecast_snapshot.variance(farm, key, key, "block")
    statuses = lot_status(farm, monday, sunday)
    forecast_total = sum(flt(r.get("forecast_bunches")) for r in variance["rows"])
    actual_total = sum(flt(r.get("actual_bunches")) for r in variance["rows"])
    diff = round((actual_total - forecast_total) / forecast_total * 100, 1) if forecast_total else None
    cards = [
        _card("work", "Việc đã làm (đã xác nhận)", len(work_rows), work_rows,
              [_col("code", "Lô"), _col("work_name", "Việc"), _col("qty", "Khối lượng", "number"), _col("uom", "Đơn vị"), _col("days", "Số ngày", "number"),
               _col("done", "Xong")], "info", "lô × việc"),
        _card("ribbon", "Còn trên cây", board["left"], [dict(c, lots=len(c["lots"])) for c in board["cards"] if c["status"] != "done"],
              [_col("colour", "Màu"), _col("week", "Tuần", "number"), _col("lots", "Số lô", "number"), _col("cut", "Cắt bắp", "number"), _col("bag", "Đã bao", "number"),
               _col("harvested", "Đã thu", "number"), _col("left", "Còn", "number"), _col("start", "Thu từ", "date"), _col("end", "Đến", "date")],
              "warn" if board["overdue"] else "info", "buồng", f"Đến tuổi thu {board['due']}, quá tuổi {board['overdue']}"),
        _card("harvest", "Thu hoạch", sum(r["bunches"] for r in harvest), harvest,
              [_col("date", "Ngày", "date"), _col("code", "Lô"), _col("colour", "Màu"), _col("bunches", "Buồng", "number"), _col("kg", "Kg", "number")],
              "info", "buồng", f"{round(sum(r['kg'] for r in harvest)):,} kg".replace(",", ".")),
        _card("packhouse", "Xưởng đóng gói", sum(cint(s.cartons) for s in shifts),
              [dict(s, posting_date=str(s.posting_date)) for s in shifts],
              [_col("posting_date", "Ngày", "date"), _col("shift_code", "Ca"), _col("input_kg", "Kg vào", "number"), _col("finished_kg", "Thành phẩm (kg)", "number"),
               _col("cartons", "Thùng", "number"), _col("packout_percent", "Tỷ lệ (%)", "number")], "info", "thùng"),
        _card("forecast", "Dự thu so với thực tế", diff, variance["rows"],
              [_col("block_code", "Lô"), _col("forecast_bunches", "Dự thu (buồng)", "number"), _col("actual_bunches", "Thực tế (buồng)", "number"),
               _col("diff_pct", "Lệch (%)", "number")],
              "info" if diff is None else "good" if abs(diff) <= 10 else "warn" if abs(diff) <= 15 else "bad", "%",
              "Chưa có bản chốt của tuần này" if not variance["snapshots"] else f"Dự thu {round(forecast_total)} · thực tế {round(actual_total)} buồng"),
        _card("lots", "Lô cần chú ý", sum(1 for s in statuses if s["status"] in ("held", "late")),
              [s for s in statuses if s["status"] != "ok"],
              [_col("zone", "Khu"), _col("code", "Lô"), _col("status_text", "Tình trạng"), _col("late", "Việc quá hạn", "number"),
               _col("harvested", "Thu trong tuần", "number"), _col("quarantine_until", "Cách ly đến", "date")], "info", "lô"),
    ]
    status_text = {"held": "Đang cách ly", "late": "Có việc quá hạn", "harvest": "Có thu hoạch", "ok": "Bình thường"}
    for row in cards[-1]["rows"]:
        row["status_text"] = status_text[row["status"]]
    return {"week": key, "from": str(monday), "to": str(sunday), "cards": cards, "lots": statuses}


# ---------------------------------------------------------------- Tháng

def _pay_blocks(farm):
    """Lô whose khoán money this user sees in the month report: every lô for the manager (None), the khu of the đội for
    its đội trưởng, none for a tổ trưởng or kỹ thuật vườn (a tổ trưởng sees their tổ in Tiền khoán theo người)."""
    if field.is_manager():
        return None
    zones = set()
    for t in field._teams(farm):
        if t.lotus_team_level == field.CREW and t.lotus_leader == frappe.session.user:
            zones |= set(field.rules.crew_zones(t.lotus_zones))
    return {name for name, b in field._block_map(farm).items() if b["zone"] in zones}


@frappe.whitelist()
def month(farm, month=None):
    """A month of one farm: harvest and the rates that drive the forecast (cắt bắp per tree, thu per cắt bắp, kg and
    cartons per bunch), công and tiền khoán per lô, and materials issued from stock against those reported used."""
    field.require_farm(farm)
    begin = getdate((month or nowdate())[:7] + "-01")
    end = get_last_day(begin)
    codes = _codes(farm)
    trees = {b.name: cint(b.lotus_tree_count) for b in frappe.get_all("Farm Block", filters={"farm": farm}, fields=["name", "lotus_tree_count"], limit_page_length=0)}
    by_lot = {}
    for r in frappe.db.sql(f"""select farm_block, stage, sum(qty) as qty, sum(weight_kg) as kg from `tab{ENTRY}` where farm = %s and state = 'Confirmed'
                               and posting_date between %s and %s and stage in ('Cut Bud', 'Harvest') group by farm_block, stage""", (farm, begin, end), as_dict=True):
        slot = by_lot.setdefault(r.farm_block, {"cut": 0, "harvested": 0, "kg": 0.0})
        if r.stage == "Cut Bud":
            slot["cut"] += cint(r.qty)
        else:
            slot["harvested"] += cint(r.qty)
            slot["kg"] += flt(r.kg)
    packed = {r.farm_block: r for r in frappe.db.sql(f"""select s.farm_block, sum(s.bunches) as bunches, sum(s.kg) as kg,
                 sum(p.cartons * s.kg / nullif(p.input_kg, 0)) as cartons from `tab{SOURCE}` s join `tab{SHIFT}` p on p.name = s.parent
                 where p.farm = %s and p.docstatus = 1 and p.posting_date between %s and %s group by s.farm_block""", (farm, begin, end), as_dict=True)}
    rate_rows = []
    for block in sorted(set(by_lot) | set(packed), key=lambda b: (len(codes.get(b, "")), codes.get(b, ""))):
        slot = by_lot.get(block, {"cut": 0, "harvested": 0, "kg": 0.0})
        pack = packed.get(block)
        rate_rows.append({"code": codes.get(block, ""), "trees": trees.get(block, 0), "cut": slot["cut"], "harvested": slot["harvested"], "kg": round(slot["kg"], 1),
                          "cut_per_tree": round(slot["cut"] / trees[block], 3) if trees.get(block) else None,
                          "kg_per_bunch": round(slot["kg"] / slot["harvested"], 2) if slot["harvested"] else None,
                          "cartons_per_bunch": round(flt(pack.cartons) / cint(pack.bunches), 2) if pack and cint(pack.bunches) else None})
    total_cut = sum(r["cut"] for r in rate_rows)
    total_harvest = sum(r["harvested"] for r in rate_rows)
    total_kg = sum(r["kg"] for r in rate_rows)
    pay_blocks = _pay_blocks(farm)
    # Công (buổi of the sổ lô, weighted) and money per lô: khoán số lượng lines confirmed in the month, khoán lô locked in it.
    labour = {r.farm_block: flt(r.sessions) for r in frappe.db.sql(f"""select s.farm_block, sum(s.weight) as sessions from `tabLotus Work Session` s
        join `tab{ENTRY}` e on e.name = s.entry and e.state = 'Confirmed'
        where s.farm = %s and s.posting_date between %s and %s group by s.farm_block""", (farm, begin, end), as_dict=True)}
    count_pay = {r.farm_block: flt(r.amount) for r in frappe.db.sql(f"""select farm_block, sum(amount) as amount from `tab{ENTRY}` where farm = %s
        and state = 'Confirmed' and pay_mode = 'Count' and posting_date between %s and %s group by farm_block""", (farm, begin, end), as_dict=True)}
    lot_pay = {r.farm_block: flt(r.amount) for r in frappe.db.sql(f"""select farm_block, sum(amount) as amount from `tab{field.ASSIGNMENT}` where farm = %s
        and state = 'Locked' and pay_mode = 'Lot' and locked_at between %s and %s group by farm_block""", (farm, begin, f"{end} 23:59:59"), as_dict=True)}
    pay_rows = [{"code": codes.get(b, ""), "workdays": round(labour.get(b, 0) / 2, 2), "count_pay": round(count_pay.get(b, 0)), "lot_pay": round(lot_pay.get(b, 0)),
                 "total": round(count_pay.get(b, 0) + lot_pay.get(b, 0))}
                for b in sorted(set(labour) | set(count_pay) | set(lot_pay), key=lambda b: (len(codes.get(b, "")), codes.get(b, "")))
                if pay_blocks is None or b in pay_blocks]
    # Materials: reported on confirmed lines against issued from stock to the lô (Material Issue rows carrying the lô).
    used = frappe.db.sql(f"""select e.farm_block, m.item_code, sum(m.qty) as qty from `tabLotus Work Entry Material` m join `tab{ENTRY}` e on e.name = m.parent
        where e.farm = %s and e.state = 'Confirmed' and e.posting_date between %s and %s group by e.farm_block, m.item_code""", (farm, begin, end), as_dict=True)
    issued = frappe.db.sql("""select d.lotus_farm_block as farm_block, d.item_code, sum(d.transfer_qty) as qty from `tabStock Entry Detail` d
        join `tabStock Entry` s on s.name = d.parent where s.docstatus = 1 and s.purpose = 'Material Issue' and d.lotus_farm = %s
        and s.posting_date between %s and %s and ifnull(d.lotus_farm_block, '') != '' group by d.lotus_farm_block, d.item_code""", (farm, begin, end), as_dict=True) \
        if frappe.get_meta("Stock Entry Detail").has_field("lotus_farm_block") else []
    material = {}
    for r in used:
        material.setdefault((r.farm_block, r.item_code), {"used": 0.0, "issued": 0.0})["used"] += flt(r.qty)
    for r in issued:
        material.setdefault((r.farm_block, r.item_code), {"used": 0.0, "issued": 0.0})["issued"] += flt(r.qty)
    items = {i.name: i.item_name for i in frappe.get_all("Item", filters={"name": ["in", list({k[1] for k in material}) or [""]]}, fields=["name", "item_name"])}
    material_rows = sorted(({"code": codes.get(b, ""), "item": items.get(i, i), "used": round(v["used"], 3), "issued": round(v["issued"], 3),
                             "gap": round(v["issued"] - v["used"], 3)} for (b, i), v in material.items()), key=lambda r: (len(r["code"]), r["code"], r["item"]))
    gaps = sum(1 for r in material_rows if abs(r["gap"]) > 0.001)
    lots_cols = [_col("code", "Lô"), _col("trees", "Số cây", "number"), _col("cut", "Cắt bắp", "number"), _col("harvested", "Thu (buồng)", "number"), _col("kg", "Kg", "number"),
                 _col("cut_per_tree", "Cắt bắp/cây", "number"), _col("kg_per_bunch", "Kg/buồng", "number"), _col("cartons_per_bunch", "Thùng/buồng", "number")]
    cards = [
        _card("harvest", "Sản lượng thu", total_harvest, rate_rows, lots_cols, "info", "buồng", f"{round(total_kg):,} kg".replace(",", ".")),
        _card("cut", "Cắt bắp", total_cut, rate_rows, lots_cols, "info", "buồng",
              (str(round(total_harvest / total_cut * 100, 1)).replace(".", ",") + "% số đã cắt đã thu trong tháng") if total_cut else ""),
        _card("kg_per_bunch", "Kg mỗi buồng", round(total_kg / total_harvest, 2) if total_harvest else None, rate_rows, lots_cols, "info", "kg"),
        _card("pay", "Tiền khoán theo lô", sum(r["total"] for r in pay_rows), pay_rows,
              [_col("code", "Lô"), _col("workdays", "Công", "number"), _col("count_pay", "Khoán số lượng (đ)", "number"), _col("lot_pay", "Khoán lô (đ)", "number"),
               _col("total", "Cộng (đ)", "number")], "info", "đ", "Theo người: mở Tiền khoán theo người"),
        _card("materials", "Vật tư xuất và báo dùng lệch", gaps, material_rows,
              [_col("code", "Lô"), _col("item", "Vật tư"), _col("issued", "Xuất kho", "number"), _col("used", "Báo dùng", "number"), _col("gap", "Chênh", "number")],
              "warn" if gaps else "good", "dòng"),
    ]
    if pay_blocks is not None and not pay_blocks:
        cards = [c for c in cards if c["key"] != "pay"]
    return {"month": str(begin)[:7], "from": str(begin), "to": str(end), "cards": cards}
