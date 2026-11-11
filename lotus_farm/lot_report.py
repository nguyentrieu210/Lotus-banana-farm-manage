"""Báo cáo ngày của tổ: every job on every lô of one tổ for one day, entered lô by lô (thẻ lô + hộp nhập), sent once,
confirmed once by the đội trưởng. Lines are the sổ lô (Lotus Work Entry); the report is their header (Lotus Daily Report).

Who may do what (field_report.access):
  - the tổ trưởng enters and sends their tổ's report; the đội trưởng or a manager may enter it for them (nhập hộ);
  - the đội trưởng (or a manager) confirms; nobody confirms a line they entered, so a report the đội trưởng entered
    is confirmed by the quản lý vườn;
  - a confirmed line is corrected only by voiding it with a reason and writing a new one (amend).
"""
import json

import frappe
from frappe.utils import add_days, cint, flt, get_first_day, get_last_day, getdate, now_datetime, nowdate

from lotus_farm import field_report as field
from lotus_farm import lot_ledger
from lotus_farm import lot_ledger_rules as rules
from lotus_farm.controls import lock

REPORT, ENTRY, SESSION, PERSON = lot_ledger.REPORT, lot_ledger.ENTRY, field.SESSION, "Lotus Work Entry Person"
REASON_GROUP = "BUONG"
MAX_LINES = 40
LINE_FIELDS = ["name", "farm_block", "work_type", "stage", "pay_mode", "cycle_no", "posting_date", "qty", "uom", "area_ha", "bunch_tag",
               "reject_stage", "reason", "weight_kg", "disease", "severity", "done", "state", "source_type", "source_key", "machine_read",
               "review_flags", "rate", "amount", "entered_by", "confirmed_by", "confirmed_at", "assignment", "notes", "replaces",
               "morning_people", "afternoon_people", "daily_report", "work_team"]
REPORT_FIELDS = ["name", "farm", "company", "crew", "work_team", "report_date", "state", "entered_by", "on_behalf", "source", "sent_at",
                 "confirmed_by", "confirmed_at", "reopen_reason", "present_morning", "present_afternoon", "notes", "modified"]


# ---------------------------------------------------------------- access

def _team(farm, team):
    row = frappe.db.get_value("Work Team", team, ["name", "farm", "team_name", "lotus_team_level", "lotus_parent_team", "lotus_leader"], as_dict=True)
    if not row or row.farm != farm or row.lotus_team_level != field.TEAM or not row.lotus_parent_team:
        frappe.throw("Chọn tổ thuộc một đội của vườn.")
    return row


def _rights(farm, team):
    field.require_farm(farm)
    row = _team(farm, team)
    rights = field.access(farm, row.lotus_parent_team)
    write = rights.supervisor or team in rights.teams
    if not (write or rights.inspector):
        frappe.throw("Bạn không thuộc đội của tổ này.", frappe.PermissionError)
    return frappe._dict(rights, team=row, write=write, confirm=rights.supervisor)


def _load(report, for_update=False):
    doc = frappe.get_doc(REPORT, report, for_update=for_update)
    return doc, _rights(doc.farm, doc.work_team)


def _store(doc):
    token = field._writing.set(True)
    try:
        doc.save(ignore_permissions=True)
    finally:
        field._writing.reset(token)
    return doc


# ---------------------------------------------------------------- reference data

def _reasons():
    group = frappe.db.get_value("Cancellation Reason Group", {"group_code": REASON_GROUP})
    return frappe.get_all("Cancellation Reason", filters={"reason_group": group or "", "active": 1}, fields=["name", "reason_name"],
                          order_by="reason_name asc", limit_page_length=0)


def _diseases():
    return frappe.get_all("Disease", filters={"active": 1}, fields=["name", "disease_code", "disease_name"], order_by="disease_name asc",
                          limit_page_length=0)


def _tags(farm, day):
    return {t.name: t for t in field._ribbon_tags(farm, day)}


def _crew_blocks(farm, rights):
    return {name: b for name, b in field._block_map(farm).items() if b["zone"] in rights.zones}


def _cycles(blocks):
    return dict(frappe.get_all("Farm Block", filters={"name": ["in", list(blocks) or [""]]}, fields=["name", "lotus_current_cycle_no"], as_list=True))


def _work_rows(works):
    return [{"name": w.name, "code": w.code, "label": w.label, "uom": w.uom, "stage": w.stage, "group": w.group, "pay_mode": w.pay_mode,
             "requires_material": w.requires_material, "records_disease": w.records_disease} for w in works.values()]


def _ledger_rows(blocks, exclude_report=None):
    """Live (not voided) bunch-stage lines of these lô; the caps count drafts too, they are the tổ's own numbers."""
    filters = {"farm_block": ["in", list(blocks) or [""]], "state": ["!=", rules.VOIDED], "stage": ["is", "set"]}
    if exclude_report:
        filters["daily_report"] = ["!=", exclude_report]
    return frappe.get_all(ENTRY, filters=filters, fields=["name", "farm_block", "bunch_tag", "stage", "reject_stage", "qty", "cycle_no",
                                                          "daily_report", "state"], limit_page_length=0)


def _colours(rows, tags):
    """Per lô: colours with bunches still to bag or harvest, newest first."""
    balance = rules.colour_balance(rows)
    result = {}
    for (block, tag), b in balance.items():
        t = tags.get(tag)
        if not t:
            continue
        # lần (week_half) tells two batches of one colour and week apart, e.g. Tím tuần 45 lần 1 and lần 2.
        result.setdefault(block, []).append({"tag": tag, "label": t.color_label or t.display_name, "code": t.color_code, "week": t.week_number,
                                             "lan": cint(t.get("week_half")) or None,
                                             "cut": b["cut"], "bag": b["bag"], "used": b["used"], "left": b["left"],
                                             "bag_left": max(b["cut"] - b["bag"], 0)})
    for colours in result.values():
        colours.sort(key=lambda c: (-(c["week"] or 0)))
    return result


def _present(company, day, team, crew_teams):
    people = field.presence(company, day)
    rows = [dict(p, own=p.get("team") == team) for p in people.values() if p.get("team") in crew_teams]
    rows.sort(key=lambda p: (not p["own"], p.get("employee_name") or ""))
    return rows


# ---------------------------------------------------------------- views

def _report_row(name):
    row = frappe.db.get_value(REPORT, name, REPORT_FIELDS, as_dict=True)
    row["report_date"], row["modified"] = str(row.report_date), str(row.modified)
    for f in ("sent_at", "confirmed_at"):
        row[f] = str(row[f]) if row[f] else None
    names = field._user_names([row.entered_by, row.confirmed_by])
    row["entered_name"], row["confirmed_name"] = names.get(row.entered_by, row.entered_by or ""), names.get(row.confirmed_by, row.confirmed_by or "")
    return row


def _lines(report=None, block=None, **filters):
    if report:
        filters["daily_report"] = report
    if block:
        filters["farm_block"] = block
    filters.setdefault("state", ["!=", rules.VOIDED])
    rows = frappe.get_all(ENTRY, filters=filters, fields=LINE_FIELDS, order_by="creation asc", limit_page_length=0)
    if not rows:
        return []
    people = {}
    for p in frappe.get_all(PERSON, filters={"parenttype": ENTRY, "parent": ["in", [r.name for r in rows]]},
                            fields=["parent", "employee", "employee_name", "morning", "afternoon"], order_by="idx asc", limit_page_length=0):
        people.setdefault(p.parent, []).append({"employee": p.employee, "employee_name": p.employee_name, "morning": p.morning, "afternoon": p.afternoon})
    materials = {}
    for m in frappe.get_all("Lotus Work Entry Material", filters={"parenttype": ENTRY, "parent": ["in", [r.name for r in rows]]},
                            fields=["parent", "item_code", "qty", "uom", "dose", "stock_entry", "phi_days"], order_by="idx asc", limit_page_length=0):
        materials.setdefault(m.parent, []).append({k: m[k] for k in ("item_code", "qty", "uom", "dose", "stock_entry", "phi_days")})
    for r in rows:
        r.update(posting_date=str(r.posting_date), confirmed_at=str(r.confirmed_at) if r.confirmed_at else None,
                 people=people.get(r.name, []), materials=materials.get(r.name, []))
    return rows


def _assignments(farm, team, day):
    """Lô given to the tổ: standing bunch care, and open Round phiếu (giao theo vòng) from their day on."""
    rows = frappe.get_all(field.ASSIGNMENT, filters={"farm": farm, "work_team": team, "state": ["in", list(field.OPEN_STATES)],
                                                     "assigned_on": ["<=", day]},
                          fields=["name", "kind", "farm_block", "work_type", "due_date", "state", "pay_mode"], limit_page_length=0)
    for r in rows:
        r["due_date"] = str(r.due_date) if r.due_date else None
    return rows


def _paper(report):
    """The paper form of the report: printed or not, the photo read and what the reader noted."""
    if not report:
        return None
    try:
        draft = json.loads(frappe.db.get_value(REPORT, report, "machine_draft") or "{}") or {}
    except ValueError:
        return None
    if not draft:
        return None
    return {"printed_at": draft.get("printed_at"), "photo": draft.get("photo"), "read_at": draft.get("read_at"), "notes": draft.get("notes") or []}


@frappe.whitelist(methods=["POST"])
def open_report(farm, team, date=None):
    """The tổ's report of a day, created as a draft the first time someone allowed to enter starts entering or sends."""
    day = str(getdate(date or nowdate()))
    rights = _rights(farm, team)
    if not rights.write:
        frappe.throw("Bạn chỉ nhập cho tổ của mình.", frappe.PermissionError)
    if getdate(day) > getdate(nowdate()):
        frappe.throw("Không nhập cho ngày tương lai.")
    name = frappe.db.get_value(REPORT, {"farm": farm, "work_team": team, "report_date": day})
    if not name:
        field._closed(frappe.db.get_value("Farm", farm, "company"), getdate(day))
        lock("Farm", farm)
        name = frappe.db.get_value(REPORT, {"farm": farm, "work_team": team, "report_date": day})
    if not name:
        doc = frappe.new_doc(REPORT)
        doc.update({"farm": farm, "company": frappe.db.get_value("Farm", farm, "company"), "crew": rights.team.lotus_parent_team,
                    "work_team": team, "report_date": day, "state": rules.DRAFT, "entered_by": frappe.session.user,
                    "on_behalf": 0 if rights.team.lotus_leader == frappe.session.user else 1, "source": "Phone"})
        _store(doc)
        name = doc.name
    return _report_row(name)


@frappe.whitelist()
def today(farm, team, date=None):
    """Everything one tổ needs for one day: the lô cards, the việc, the colours, who the clock shows present, and the
    report if it exists (open_report creates it). Reading never writes."""
    day = str(getdate(date or nowdate()))
    rights = _rights(farm, team)
    farm_doc = frappe.get_cached_doc("Farm", farm)
    name = frappe.db.get_value(REPORT, {"farm": farm, "work_team": team, "report_date": day})
    blocks = _crew_blocks(farm, rights)
    cycles = _cycles(blocks)
    tags = _tags(farm, day)
    lines = _lines(name) if name else []
    assignments = _assignments(farm, team, day)
    wanted = {a.farm_block for a in assignments} | {l.farm_block for l in lines}
    colours = _colours(_ledger_rows(blocks), tags)
    lots = []
    for block_name in sorted(blocks, key=lambda b: (blocks[b]["zone"], len(blocks[b]["block_code"] or ""), blocks[b]["block_code"] or "")):
        b = blocks[block_name]
        lots.append({"block": block_name, "code": b["block_code"], "zone": b["zone"], "area_ha": flt(b.get("area_ha")), "trees": b["trees"],
                     "cycle": cint(cycles.get(block_name)), "quarantine_until": b.get("quarantine_until"), "active": block_name in wanted,
                     "assignments": [a for a in assignments if a.farm_block == block_name],
                     "lines": [l for l in lines if l.farm_block == block_name], "colours": colours.get(block_name, [])})
    ribbon = field.ribbon(farm, day)
    crew_teams = _crew_teams(farm, rights.team.lotus_parent_team, team)
    return {"date": day, "farm": farm, "team": team, "team_name": rights.team.team_name, "crew": rights.team.lotus_parent_team,
            "report": _report_row(name) if name else None, "lots": lots,
            "blocks": [{"block": n, "code": b["block_code"], "zone": b["zone"]} for n, b in blocks.items()],
            "works": _work_rows(lot_ledger.works(farm)),
            "paper": _paper(name),
            "ribbon": ribbon and {"name": ribbon.name, "label": ribbon.color_label or ribbon.display_name, "code": ribbon.color_code,
                                  "week": ribbon.week_number},
            "reasons": _reasons(), "diseases": _diseases(), "severities": list(rules.SEVERITIES),
            "present": _present(farm_doc.company, day, team, crew_teams),
            "rights": {"write": rights.write and getdate(day) <= getdate(nowdate()), "confirm": rights.confirm, "manager": rights.manager,
                       "user": frappe.session.user}}


# ---------------------------------------------------------------- save one lô

def _clean_items(materials):
    result = []
    for m in materials:
        item = frappe.db.get_value("Item", m["item_code"], ["name", "stock_uom", "disabled", "lotus_phi_days"], as_dict=True)
        if not item or item.disabled:
            raise rules.LineError("Vật tư không có trong danh mục kho.")
        if m.get("stock_entry") and not frappe.db.exists("Stock Entry", {"name": m["stock_entry"], "docstatus": 1}):
            raise rules.LineError("Phiếu xuất kho không tồn tại hoặc chưa ghi sổ.")
        result.append(dict(m, item_code=item.name, uom=item.stock_uom, phi_days=cint(item.lotus_phi_days)))
    return result


def _crew_teams(farm, crew, team):
    return {t.name for t in field._teams(farm) if t.lotus_parent_team == crew} | {team}


def _check_people(people, here, names, crew_teams):
    """Only people of the đội's tổ, and only the buổi the clock shows them present."""
    for employee, flags in people.items():
        if employee not in names:
            raise rules.LineError("Có người không có trong danh sách nhân sự.")
        seen = here.get(employee) or {}
        if seen.get("team") not in crew_teams:
            raise rules.LineError(f"{names[employee]} không thuộc tổ nào của đội này.")
        for session, label in (("morning", "sáng"), ("afternoon", "chiều")):
            if flags[session] and not seen.get(session):
                raise rules.LineError(f"{names[employee]}: máy chấm công không có lượt buổi {label}.")


def _free_key(key):
    """A voided line keeps its key, so a new line for the same lô, việc and colour needs its own."""
    candidate, n = key, 1
    while frappe.db.exists(ENTRY, {"source_key": candidate}):
        n += 1
        candidate = f"{key}:{n}"
    return candidate


def pay_mode(work, given):
    """A line on a phiếu giao is paid the way the phiếu was given (it keeps the mode of the day it was given);
    otherwise the way the catalogue says today."""
    return (given.pay_mode if given and given.pay_mode else work.pay_mode)


def _write_line(doc, report, block, clean, existing, cycle, rounds, standing, names, review_flags=None):
    """Write one Draft line of a lô in the tổ's report (new, or replacing the unsent line with the same key).
    rounds: {việc: the open Round of this tổ on this lô}."""
    line = frappe.get_doc(ENTRY, existing.name, for_update=True) if existing else frappe.new_doc(ENTRY)
    work = clean["work"]
    stage = clean["stage"] or None
    line_cycle = cycle
    if stage == rules.SUCKER:
        bud = frappe.db.exists(ENTRY, {"farm_block": block, "cycle_no": cycle, "state": ["!=", rules.VOIDED], "stage": ["in", [rules.INJECT, rules.CUT]]})
        line_cycle = rules.sucker_cycle(cycle, bool(bud))
    given = rounds.get(work.name)
    line.update({"daily_report": report, "farm": doc.farm, "company": doc.company, "crew": doc.crew, "work_team": doc.work_team,
                 "farm_block": block, "work_type": work.name, "stage": stage, "pay_mode": pay_mode(work, given), "cycle_no": line_cycle,
                 "posting_date": getdate(doc.report_date), "qty": clean["qty"], "uom": work.uom, "area_ha": clean["area_ha"], "bunch_tag": clean["bunch_tag"],
                 "reject_stage": clean["reject_stage"], "reason": clean["reason"], "weight_kg": clean["weight_kg"],
                 "disease": clean["disease"], "severity": clean["severity"], "done": clean["done"], "notes": clean["notes"],
                 "state": rules.DRAFT, "source_type": rules.PHOTO if clean["machine_read"] else rules.DAILY,
                 "source_key": existing.source_key if existing else _free_key(clean["key"]), "machine_read": clean["machine_read"],
                 "review_flags": review_flags or None, "entered_by": frappe.session.user,
                 "assignment": given.name if given else (standing if work.group == rules.BUNCH_GROUP else None),
                 "morning_people": sum(f["morning"] for f in clean["people"].values()),
                 "afternoon_people": sum(f["afternoon"] for f in clean["people"].values())})
    line.set("people", [{"employee": e, "employee_name": names.get(e, e), **f} for e, f in clean["people"].items()])
    line.set("materials", [{k: m[k] for k in ("item_code", "qty", "uom", "dose", "stock_entry", "phi_days")} for m in clean["materials"]])
    _store(line)
    return line


@frappe.whitelist(methods=["POST"])
def save_lot(report, block, lines=None, expected_modified=None):
    """Replace the tổ's unsent lines of one lô in the report. All or nothing: any bad line stops the save and is reported."""
    doc, rights = _load(report, for_update=True)
    if not rights.write:
        frappe.throw("Bạn chỉ nhập cho tổ của mình.", frappe.PermissionError)
    if not rules.can_edit(doc.state):
        frappe.throw("Báo cáo đã gửi. Nhờ đội trưởng mở lại nếu cần sửa.")
    if expected_modified and str(doc.modified) != str(expected_modified):
        frappe.throw("Báo cáo vừa được người khác sửa. Tải lại rồi nhập tiếp.", frappe.TimestampMismatchError)
    day = getdate(doc.report_date)
    if day > getdate(nowdate()):
        frappe.throw("Không nhập cho ngày tương lai.")
    field._closed(doc.company, day)
    lock("Farm", doc.farm)
    blocks = _crew_blocks(doc.farm, rights)
    lot = blocks.get(block)
    if not lot:
        frappe.throw("Lô không thuộc đội này.")
    raw_lines = frappe.parse_json(lines) if isinstance(lines, str) else (lines or [])
    if not isinstance(raw_lines, list) or len(raw_lines) > MAX_LINES:
        frappe.throw(f"Mỗi lô tối đa {MAX_LINES} dòng.")
    works = lot_ledger.works(doc.farm)
    ribbon = field.ribbon(doc.farm, str(day))
    tags = _tags(doc.farm, str(day))
    reasons = {r.name for r in _reasons()}
    diseases = {d.name for d in _diseases()}
    here = field.presence(doc.company, day)
    crew_teams = _crew_teams(doc.farm, doc.crew, doc.work_team)
    cycle = cint(_cycles([block]).get(block))
    given = [a for a in _assignments(doc.farm, doc.work_team, str(day)) if a.farm_block == block]
    rounds = {a.work_type: a for a in given if a.kind == field.rules.ROUND}
    standing = next((a.name for a in given if a.kind != field.rules.ROUND), None)
    live = {l.source_key: l for l in _lines(report, block)}
    all_people = {}
    for raw in raw_lines:
        all_people.update(rules.clean_people(raw.get("people") if isinstance(raw, dict) else None))
    names = {e.name: e.employee_name for e in frappe.get_all("Employee", filters={"name": ["in", list(all_people) or [""]]},
                                                             fields=["name", "employee_name"])}
    wanted, errors = {}, []
    for index, raw in enumerate(raw_lines):
        try:
            if not isinstance(raw, dict):
                raise rules.LineError("Dòng không hợp lệ.")
            work = works.get(raw.get("work_type"))
            if not work:
                raise rules.LineError("Việc không có trong danh mục việc của vườn.")
            clean = rules.clean_line(raw, work, ribbon.name if ribbon else None)
            tag = clean["bunch_tag"]
            if tag and clean["stage"] != rules.CUT and tag not in tags:
                raise rules.LineError("Màu dây không có trong lịch cắt bắp các tuần gần đây.")
            if clean["reason"] and clean["reason"] not in reasons:
                raise rules.LineError("Lý do không có trong danh mục.")
            if clean["disease"] and clean["disease"] not in diseases:
                raise rules.LineError("Bệnh không có trong danh mục.")
            if clean["stage"] == rules.HARVEST:
                held = lot_ledger.harvest_hold(block, day)
                if held:
                    raise rules.LineError(f"Lô đang cách ly thuốc đến hết {held[1].strftime('%d/%m/%Y')}, chưa được thu hoạch.")
            clean["materials"] = _clean_items(clean["materials"])
            clean["people"] = rules.clean_people(raw.get("people"))
            _check_people(clean["people"], here, names, crew_teams)
            mode = pay_mode(work, rounds.get(work.name))
            if mode == rules.PAY_LOT and work.name not in rounds:
                raise rules.LineError(f'"{work.label}" trả khoán lô nhưng lô này chưa giao cho tổ. Nhờ đội trưởng giao ở Giao việc rồi nhập.')
            over = rules.line_cap(mode, work.cap_basis, clean["stage"], clean["qty"], lot["trees"])
            if over:
                raise rules.LineError(over)
            if clean["stage"] == rules.SUCKER:
                clean["qty"] = rules.sucker_estimate(lot["trees"], clean["area_ha"], lot.get("area_ha"))
                if not clean["qty"]:
                    raise rules.LineError("Lô chưa có số cây hoặc diện tích nên chưa ước tính được số chồi.")
            clean["machine_read"] = 1 if raw.get("machine_read") else 0
            key = rules.line_key(report, block, work.name, tag, clean["reason"] or clean["disease"])
            if key in wanted:
                raise rules.LineError("Trùng dòng: cùng việc, cùng màu, cùng lý do; gộp số vào một dòng.")
            existing = live.get(key)
            if existing and existing.state == rules.CONFIRMED:
                raise rules.LineError("Dòng này đã xác nhận; nhờ đội trưởng sửa có lý do.")
            clean.update(work=work, key=key)
            wanted[key] = clean
        except rules.LineError as e:
            errors.append({"index": index, "message": str(e)})
    if not errors:
        errors = _cap_errors(doc, block, lot, cycle, wanted, live)
    if errors:
        return {"saved": 0, "removed": 0, "errors": errors}
    saved = removed = 0
    for key, clean in wanted.items():
        _write_line(doc, report, block, clean, live.get(key), cycle, rounds, standing, names)
        saved += 1
    for key, existing in live.items():
        if existing.state == rules.DRAFT and key not in wanted:
            frappe.delete_doc(ENTRY, existing.name, ignore_permissions=True, force=True)
            removed += 1
    doc.entered_by = frappe.session.user
    doc.on_behalf = 0 if rights.team.lotus_leader == frappe.session.user else 1
    if doc.on_behalf and doc.source == "Phone":
        doc.source = "Paper"
    _store(doc)
    return {"saved": saved, "removed": removed, "errors": [], "lines": _lines(report, block), "modified": str(frappe.db.get_value(REPORT, report, "modified"))}


def _cap_errors(doc, block, lot, cycle, wanted, live):
    """Would the lô, once saved, have more bagged, harvested or rejected than cut of a colour, or more chích, tỉa,
    chống đổ in the vụ than trees? Lines of this lô in this report are replaced by the new ones."""
    replaced = {l.name for l in live.values() if l.state == rules.DRAFT}
    rows = [r for r in _ledger_rows([block]) if r.name not in replaced]
    rows += [dict(farm_block=block, bunch_tag=c["bunch_tag"], stage=c["stage"], reject_stage=c["reject_stage"], qty=c["qty"], cycle_no=cycle)
             for c in wanted.values() if c["stage"]]
    errors = []
    tags = {t.name: t.color_label or t.name for t in frappe.get_all("Bunch Tag", filters={"farm": doc.farm}, fields=["name", "color_label"],
                                                                     limit_page_length=0)}
    touched = {(block, c["bunch_tag"]) for c in wanted.values() if c["bunch_tag"]}
    for key, balance in rules.over_cut(rows).items():
        if key in touched:
            errors.append({"index": None, "message": rules.cap_message(lot["block_code"], tags.get(key[1], key[1]), balance)})
    for (b, stage), (total, trees) in rules.over_trees(rows, {block: lot["trees"]}, {block: cycle}).items():
        if any(c["stage"] == stage for c in wanted.values()):
            errors.append({"index": None, "message": f"{lot['block_code']}: {rules.LABELS[stage].lower()} lũy kế {total} vượt số cây {trees} của lô."})
    return errors


def write_sessions(company, day):
    """Rewrite the buổi of everyone on a day's confirmed lines: one buổi of one person, shared by the lines they were on.
    Unsent and unconfirmed lines hold nobody, so a draft of one tổ never changes what another tổ's confirmed line pays."""
    names = frappe.get_all(ENTRY, filters={"company": company, "posting_date": day, "state": rules.CONFIRMED}, pluck="name")
    people = frappe.get_all(PERSON, filters={"parenttype": ENTRY, "parent": ["in", names or [""]]},
                            fields=["parent", "employee", "morning", "afternoon"], limit_page_length=0)
    if not names:
        frappe.db.delete(SESSION, {"company": company, "posting_date": day})
        return
    lines = {n.name: n for n in frappe.get_all(ENTRY, filters={"name": ["in", names]},
                                               fields=["name", "work_type", "qty", "area_ha", "farm", "farm_block", "assignment", "pay_mode"],
                                               limit_page_length=0)}
    held = {}
    for p in people:
        held.setdefault(p.parent, {})[p.employee] = {"morning": p.morning, "afternoon": p.afternoon}
    weights = rules.session_weights([{"key": n, "work_type": lines[n].work_type, "qty": flt(lines[n].qty) or flt(lines[n].area_ha),
                                      "people": held.get(n, {})} for n in names])
    frappe.db.delete(SESSION, {"company": company, "posting_date": day})
    token = field._writing.set(True)
    try:
        for (entry, employee, session), weight in weights.items():
            if weight <= 0:
                continue
            line = lines[entry]
            frappe.get_doc({"doctype": SESSION, "employee": employee, "posting_date": day, "session": session, "weight": weight, "entry": entry,
                            "assignment": line.assignment, "pay_mode": line.pay_mode, "farm": line.farm, "company": company,
                            "farm_block": line.farm_block, "work_type": line.work_type}).insert(ignore_permissions=True)
    finally:
        field._writing.reset(token)


# ---------------------------------------------------------------- send, confirm, amend, reopen

def _nobody(lines, block_map):
    """Codes of the lô with a khoán line that names nobody: its money would reach no one."""
    return sorted({block_map.get(l.farm_block, {}).get("block_code", l.farm_block) for l in lines
                   if l.pay_mode in (rules.PAY_COUNT, rules.PAY_LOT) and not l.people}, key=lambda c: (len(c), c))


@frappe.whitelist(methods=["POST"])
def send(report, expected_modified=None):
    doc, rights = _load(report, for_update=True)
    if not rights.write:
        frappe.throw("Bạn chỉ gửi báo cáo của tổ mình.", frappe.PermissionError)
    if expected_modified and str(doc.modified) != str(expected_modified):
        frappe.throw("Báo cáo vừa được người khác sửa. Tải lại rồi gửi.", frappe.TimestampMismatchError)
    try:
        state = rules.next_report_state(doc.state, "send")
    except ValueError:
        frappe.throw("Báo cáo đã gửi rồi.")
    unchecked = frappe.get_all(ENTRY, filters={"daily_report": report, "state": rules.DRAFT, "machine_read": 1, "review_flags": ["is", "set"]},
                               pluck="farm_block")
    if unchecked:
        codes = sorted({frappe.db.get_value("Farm Block", b, "block_code") or b for b in unchecked})
        frappe.throw("Còn dòng máy đọc chưa kiểm ở lô " + ", ".join(codes) + ". Mở từng lô, kiểm lại rồi lưu.")
    nobody = _nobody(_lines(report, state=rules.DRAFT), field._block_map(doc.farm))
    if nobody:
        frappe.throw("Việc khoán phải ghi người làm theo buổi để chia tiền. Còn thiếu ở lô " + ", ".join(nobody) + ".")
    for name in frappe.get_all(ENTRY, filters={"daily_report": report, "state": rules.DRAFT}, pluck="name"):
        line = frappe.get_doc(ENTRY, name, for_update=True)
        line.state = rules.SENT
        _store(line)
    doc.update({"state": state, "sent_at": now_datetime()})
    _store(doc)
    return _report_row(report)


@frappe.whitelist(methods=["POST"])
def confirm(report, expected_modified=None):
    """The đội trưởng confirms a tổ's day. All or nothing: a line the confirmer entered, or a cap broken by the day,
    stops the whole report and is reported."""
    doc, rights = _load(report, for_update=True)
    if not rights.confirm:
        frappe.throw("Chỉ đội trưởng của đội (hoặc quản lý vườn) xác nhận.", frappe.PermissionError)
    if expected_modified and str(doc.modified) != str(expected_modified):
        frappe.throw("Báo cáo vừa được sửa. Tải lại trước khi xác nhận.", frappe.TimestampMismatchError)
    try:
        state = rules.next_report_state(doc.state, "confirm")
    except ValueError:
        frappe.throw("Báo cáo chưa gửi hoặc đã xác nhận.")
    field._closed(doc.company, getdate(doc.report_date))
    lock("Farm", doc.farm)
    user = frappe.session.user
    lines = _lines(report, state=rules.SENT)
    errors = []
    own = [l for l in lines if not rules.can_confirm(l.entered_by, user)]
    if own:
        errors.append("Bạn đã tự nhập " + str(len(own)) + " dòng của báo cáo này; cần người khác (quản lý vườn) xác nhận.")
    blocks = {l.farm_block for l in lines}
    block_map = field._block_map(doc.farm)
    nobody = _nobody(lines, block_map)
    if nobody:
        errors.append("Dòng khoán chưa ghi người làm ở lô " + ", ".join(nobody) + ". Mở lại báo cáo để tổ ghi người làm rồi gửi lại.")
    tags = {t.name: t.color_label or t.name for t in frappe.get_all("Bunch Tag", filters={"farm": doc.farm}, fields=["name", "color_label"], limit_page_length=0)}
    confirmed_rows = [r for r in _ledger_rows(blocks) if r.state == rules.CONFIRMED] + [dict(l, cycle_no=l.cycle_no) for l in lines if l.stage]
    for key, balance in rules.over_cut(confirmed_rows).items():
        if any((l.farm_block, l.bunch_tag) == key for l in lines):
            errors.append(rules.cap_message(block_map.get(key[0], {}).get("block_code", key[0]), tags.get(key[1], key[1]), balance))
    for l in lines:
        if l.stage == rules.HARVEST and lot_ledger.harvest_hold(l.farm_block, getdate(l.posting_date)):
            errors.append(f"{block_map.get(l.farm_block, {}).get('block_code', l.farm_block)}: lô đang cách ly thuốc, chưa được thu hoạch.")
    rates = field._rates(doc.farm)
    works = lot_ledger.works(doc.farm)
    for work_type in sorted({l.work_type for l in lines if l.pay_mode == rules.PAY_COUNT}):
        if not field.rules.rate_for(rates, work_type, doc.report_date):
            errors.append(f"Việc \"{works[work_type].label if work_type in works else work_type}\" khoán số lượng nhưng chưa có giá khoán "
                          "áp dụng cho ngày này. Quản lý vườn thêm giá ở Bảng giá khoán.")
    if errors:
        frappe.throw("<br>".join(errors))
    now = now_datetime()
    done_rounds = {}
    for l in lines:
        line = frappe.get_doc(ENTRY, l.name, for_update=True)
        rate = field.rules.rate_for(rates, line.work_type, line.posting_date)
        line.rate = flt(rate.rate) if rate and line.pay_mode == rules.PAY_COUNT else 0
        line.amount = rules.line_amount(line.pay_mode, line.qty, line.rate)
        line.update({"state": rules.CONFIRMED, "confirmed_by": user, "confirmed_at": now})
        _store(line)
        if line.done and line.assignment:
            done_rounds[line.assignment] = line
    write_sessions(doc.company, getdate(doc.report_date))
    for name, line in done_rounds.items():
        _finish_round(name, user, now, line)
    doc.update({"state": state, "confirmed_by": user, "confirmed_at": now})
    _store(doc)
    return _report_row(report)


def _finish_round(name, user, now, line=None):
    """A lô reported finished on a confirmed day: the Round goes to Reported, then is approved by this confirmation.
    Khoán lô then waits for the inspection; other pay modes close here (their money, if any, is on the lines)."""
    task = frappe.get_doc(field.ASSIGNMENT, name, for_update=True)
    if task.kind != field.rules.ROUND or task.state not in (field.rules.OPEN, field.rules.FAILED):
        return
    task.qty_total = sum(flt(q) for q in frappe.get_all(ENTRY, filters={"assignment": name, "state": rules.CONFIRMED}, pluck="qty"))
    if line:
        task.done_report, task.done_line, task.done_date = line.daily_report, line.name, line.posting_date
    task.state = field.rules.next_state(task.state, "report")
    task.reported_by, task.reported_at = user, now
    task.state = field.rules.next_state(task.state, "approve", task.pay_mode)
    task.approved_by, task.approved_at = user, now
    if task.state == field.rules.PASSED:
        task.amount = 0
        task.state = field.rules.LOCKED
        task.locked_at = now
    field._store(task)


@frappe.whitelist(methods=["POST"])
def amend(entry, values=None, reason=None):
    """Correct a confirmed line: void it with a reason and, unless the new number is 0, write the corrected line."""
    old = frappe.get_doc(ENTRY, entry, for_update=True)
    report = old.daily_report
    if not report:
        frappe.throw("Dòng này không thuộc báo cáo ngày nào nên không sửa ở đây.")
    doc, rights = _load(report)
    if not rights.confirm:
        frappe.throw("Chỉ đội trưởng của đội (hoặc quản lý vườn) sửa số đã xác nhận.", frappe.PermissionError)
    reason = str(reason or "").strip()
    if not reason:
        frappe.throw("Sửa số đã xác nhận phải ghi lý do.")
    if old.state != rules.CONFIRMED:
        frappe.throw("Chỉ sửa được dòng đã xác nhận; dòng chưa gửi sửa ngay trong hộp nhập.")
    field._closed(old.company, getdate(old.posting_date))
    lock("Farm", old.farm)
    values = frappe.parse_json(values) if isinstance(values, str) else (values or {})
    remove = str(values.get("qty")) == "0" and old.stage != rules.SUCKER
    work = lot_ledger.works(old.farm).get(old.work_type)
    clean = None
    lot = field._block_map(old.farm).get(old.farm_block, {})
    code = lot.get("block_code") or old.farm_block
    others = [r for r in _ledger_rows([old.farm_block]) if r.name != old.name and r.state == rules.CONFIRMED]
    before = rules.over_cut(others + [dict(farm_block=old.farm_block, bunch_tag=old.bunch_tag, stage=old.stage, reject_stage=old.reject_stage,
                                           qty=old.qty, cycle_no=old.cycle_no)])
    rows = list(others)
    if not remove:
        merged = {"qty": old.qty, "area_ha": old.area_ha, "bunch_tag": old.bunch_tag, "reason": old.reason, "reject_stage": old.reject_stage,
                  "weight_kg": old.weight_kg, "disease": old.disease, "severity": old.severity, "done": old.done, "notes": old.notes,
                  "materials": [m.as_dict() for m in old.get("materials")]}
        merged.update({k: values[k] for k in ("qty", "area_ha", "bunch_tag", "reason", "reject_stage", "weight_kg", "disease", "severity", "done")
                       if k in values})
        try:
            clean = rules.clean_line(merged, work, old.bunch_tag)
        except rules.LineError as e:
            frappe.throw(str(e))
        if old.stage == rules.SUCKER:
            clean["qty"] = rules.sucker_estimate(lot.get("trees"), clean["area_ha"], lot.get("area_ha"))
        rows.append(dict(farm_block=old.farm_block, bunch_tag=clean["bunch_tag"], stage=old.stage, reject_stage=clean["reject_stage"],
                         qty=clean["qty"], cycle_no=old.cycle_no))
        if old.stage == rules.HARVEST and lot_ledger.harvest_hold(old.farm_block, getdate(old.posting_date)):
            frappe.throw("Lô đang cách ly thuốc ở ngày thu này, không sửa thành thu hoạch được.")
        if flt(clean["qty"]) > flt(old.qty):
            cycle = cint(_cycles([old.farm_block]).get(old.farm_block))
            for (_, stage), (total, trees) in rules.over_trees(rows, {old.farm_block: lot.get("trees")}, {old.farm_block: cycle}).items():
                if stage == old.stage:
                    frappe.throw(f"{code}: {rules.LABELS[stage].lower()} lũy kế {total} vượt số cây {trees} của lô.")
            over = rules.line_cap(old.pay_mode, work.cap_basis if work else "None", old.stage, clean["qty"], lot.get("trees"))
            if over:
                frappe.throw(f"{code}: {over}")
    if old.stage == rules.HARVEST and old.bunch_tag:
        # Buồng already taken into a packhouse shift stay harvested: the shift (and its stock receipt) counts them.
        from lotus_farm import shift as packhouse
        key = (old.farm_block, old.bunch_tag)
        kept = cint(clean["qty"]) if clean and clean["bunch_tag"] == old.bunch_tag else 0
        taken = packhouse._received_elsewhere({key}).get(key, 0)
        left = packhouse._harvested({key}).get(key, 0) - cint(old.qty) + kept
        if taken > left:
            frappe.throw(f"{code}: xưởng đã nhận {taken} buồng của màu này vào ca đóng gói, sau khi sửa chỉ còn {left} buồng đã thu. "
                         "Sửa hoặc hủy ca đóng gói trước.")
    # The colour may not end further beyond its cắt bắp than it was: lowering or removing a cắt bắp line with buồng
    # already bagged or harvested against it is refused the same way as raising a bao or thu line.
    touched = {old.bunch_tag, clean["bunch_tag"] if clean else None} - {None}
    for key, balance in rules.over_cut(rows).items():
        if key[1] in touched and (key not in before or rules.overage(balance) > rules.overage(before[key])):
            frappe.throw(rules.cap_message(code, frappe.db.get_value("Bunch Tag", key[1], "color_label") or key[1], balance))
    now = now_datetime()
    old.update({"state": rules.VOIDED, "void_reason": reason[:140], "voided_at": now})
    _store(old)
    new = None
    if not remove:
        new = frappe.new_doc(ENTRY)
        copied = {k: old.get(k) for k in ("daily_report", "assignment", "farm", "company", "crew", "work_team", "farm_block", "work_type", "stage",
                                          "pay_mode", "cycle_no", "posting_date", "uom", "source_type", "source_name", "entered_by")}
        new.update(dict(copied, qty=clean["qty"], area_ha=clean["area_ha"], bunch_tag=clean["bunch_tag"], reject_stage=clean["reject_stage"],
                        reason=clean["reason"], weight_kg=clean["weight_kg"], disease=clean["disease"], severity=clean["severity"],
                        done=clean["done"], notes=("Sửa: " + reason[:120]), state=rules.CONFIRMED, confirmed_by=frappe.session.user,
                        confirmed_at=now, replaces=old.name, rate=old.rate,
                        amount=rules.line_amount(old.pay_mode, clean["qty"], old.rate),
                        source_key=_free_key("amend:" + old.name), morning_people=old.morning_people, afternoon_people=old.afternoon_people))
        new.set("people", [{k: p.get(k) for k in ("employee", "employee_name", "morning", "afternoon")} for p in old.get("people")])
        new.set("materials", [{k: m.get(k) for k in ("item_code", "qty", "uom", "dose", "stock_entry", "phi_days")} for m in old.get("materials")])
        _store(new)
    write_sessions(old.company, getdate(old.posting_date))
    return {"voided": old.name, "entry": new.name if new else None}


@frappe.whitelist(methods=["POST"])
def reopen(report, reason=None):
    doc, rights = _load(report, for_update=True)
    if not rights.confirm:
        frappe.throw("Chỉ đội trưởng của đội (hoặc quản lý vườn) mở lại báo cáo.", frappe.PermissionError)
    reason = str(reason or "").strip()
    if not reason:
        frappe.throw("Mở lại báo cáo phải ghi lý do.")
    try:
        state = rules.next_report_state(doc.state, "reopen")
    except ValueError:
        frappe.throw("Báo cáo chưa gửi nên không cần mở lại.")
    for name in frappe.get_all(ENTRY, filters={"daily_report": report, "state": rules.SENT}, pluck="name"):
        line = frappe.get_doc(ENTRY, name, for_update=True)
        line.state = rules.DRAFT
        _store(line)
    doc.update({"state": state, "reopen_reason": reason[:500]})
    _store(doc)
    return _report_row(report)


# ---------------------------------------------------------------- the đội trưởng's morning and the tổ's money

@frappe.whitelist()
def status(farm, crew, date=None):
    """For the đội trưởng: each tổ's report of a day (not sent, waiting, confirmed), and numbers that look wrong."""
    day = str(getdate(date or add_days(nowdate(), -1)))
    field.require_farm(farm)
    rights = field.access(farm, crew)
    if not rights.supervisor:
        frappe.throw("Chỉ đội trưởng của đội (hoặc quản lý vườn) xem danh sách này.", frappe.PermissionError)
    names = {t.name: t.team_name for t in field._teams(farm)}
    reports = {r.work_team: r for r in frappe.get_all(REPORT, filters={"farm": farm, "crew": crew, "report_date": day},
                                                      fields=["name", "work_team", "state"], limit_page_length=0)}
    teams = []
    for team in sorted(rights.members, key=lambda t: names.get(t, t)):
        r = reports.get(team)
        lines = frappe.db.count(ENTRY, {"daily_report": r.name, "state": ["!=", rules.VOIDED]}) if r else 0
        teams.append({"team": team, "team_name": names.get(team, team), "report": r.name if r else None,
                      "state": r.state if r else None, "lines": lines})
    blocks = _crew_blocks(farm, rights)
    anomalies = _anomalies(blocks, day)
    overdue = frappe.get_all(field.ASSIGNMENT, filters={"farm": farm, "crew": crew, "kind": field.rules.ROUND, "state": ["in", [field.rules.OPEN, field.rules.FAILED]],
                                                        "due_date": ["<", day]}, fields=["farm_block", "work_type", "work_team", "due_date"], limit_page_length=0)
    return {"date": day, "teams": teams, "anomalies": anomalies, "overdue": len(overdue)}


def _anomalies(blocks, day):
    rows = _ledger_rows(blocks)
    cycles = _cycles(blocks)
    flowers = dict(frappe.get_all("Farm Block", filters={"name": ["in", list(blocks) or [""]]}, fields=["name", "lotus_estimated_flowering_date"], as_list=True))
    totals = {}
    for r in rows:
        if cint(r.cycle_no) != cint(cycles.get(r.farm_block)):
            continue
        slot = totals.setdefault(r.farm_block, {"inject": 0, "cut": 0, "used": 0})
        if r.stage == rules.INJECT:
            slot["inject"] += cint(r.qty)
        elif r.stage == rules.CUT:
            slot["cut"] += cint(r.qty)
        elif r.stage == rules.HARVEST or (r.stage == rules.REJECT and r.reject_stage == rules.AFTER_CUT):
            slot["used"] += cint(r.qty)
    return rules.anomalies([dict(totals.get(name, {}), code=b["block_code"], trees=b["trees"],
                                 flower_date=getdate(flowers[name]) if flowers.get(name) else None) for name, b in blocks.items()], getdate(day))


@frappe.whitelist()
def my_pay(farm, month=None):
    """Khoán money so far this month, from confirmed lines and finished khoán lô, for the tổ the user leads or supervises."""
    field.require_farm(farm)
    first = get_first_day(getdate(month + "-01") if month else getdate(nowdate()))
    last = get_last_day(first)
    teams = field._teams(farm)
    user = frappe.session.user
    manager = field.is_manager()
    supervised = {t.name for t in teams if t.lotus_team_level == field.CREW and t.lotus_leader == user}
    mine = [t for t in teams if t.lotus_team_level == field.TEAM and (manager or t.lotus_leader == user or t.lotus_parent_team in supervised)]
    pieces = field.month_piece(frappe.db.get_value("Farm", farm, "company"), first, last, teams=[t.name for t in mine])
    people = {e.name: e for e in frappe.get_all("Employee", filters={"name": ["in", list(pieces) or [""]]},
                                                fields=["name", "employee_name", "lotus_work_team"], limit_page_length=0)}
    result = []
    for t in mine:
        rows = [{"employee": e, "employee_name": people[e].employee_name if e in people else e, "amount": round(p["piece"]),
                 "sessions": round(p["piece_sessions"], 2)} for e, p in pieces.items() if p.get("teams", {}).get(t.name)]
        rows.sort(key=lambda r: -r["amount"])
        result.append({"team": t.name, "team_name": t.team_name, "total": sum(r["amount"] for r in rows), "people": rows})
    return {"month": str(first)[:7], "teams": result}
