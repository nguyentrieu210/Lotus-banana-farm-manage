"""Công việc ngoài vườn: phiếu giao việc theo lô, báo cáo trên phiếu, duyệt, nghiệm thu và tiền khoán theo người.

Lots belong to a đội through their khu (Work Team lotus_zones); tổ are groups inside the đội. The đội trưởng (lotus_leader
of the đội) gives work lô by lô: one phiếu (Lotus Work Assignment) per lô × việc × tổ × lượt. How a việc is paid comes
from the catalogue (Work Type lotus_pay_mode), never from the person giving the work, and is copied onto the phiếu with
its price when it is given (field_report_rules has the meaning of each mode).

The tổ trưởng reports on the phiếu of their tổ (Lotus Work Entry, one per phiếu and day): who worked which buổi, how
much, the ribbon colour for bunch work, the materials for spraying and fertilising, and Xong when the lô is finished.
Three hard rules hold every report:
  1. one buổi of one person belongs to one phiếu only (Lotus Work Session, unique per employee, day and buổi);
  2. a person can only be put on a buổi the time clock shows them present for;
  3. the quantity never exceeds the lô's cap (its trees or area, or the bunches cut of that colour).
Báo xong → the đội trưởng approves → khoán lô waits for an inspection by a Kỹ thuật vườn outside the đội (Lotus Work
Inspection); counted and công nhật phiếu need none → the phiếu is locked and its khoán money is split over the people
by buổi. A buổi on a khoán phiếu is not paid as công nhật (hr_period). Spraying with a product that has a pre-harvest
interval holds the lô from harvest until it ends.
"""
import random
from contextvars import ContextVar

import frappe
from frappe.utils import add_days, cint, flt, get_last_day, getdate, now_datetime, nowdate

from lotus_farm import field_report_rules as rules
from lotus_farm.controls import farm_allowed, lock, query_condition

MANAGER, SUPERVISOR, LEADER, INSPECTOR = "Lotus Farm Manager", "Lotus Field Supervisor", "Lotus Team Leader", "Lotus Field Inspector"
CREW, TEAM = "Crew", "Team"
MAX_PEOPLE, MAX_MATERIALS, MAX_ASSIGN = 120, 6, 200
ASSIGNMENT, ENTRY, SESSION, INSPECTION = "Lotus Work Assignment", "Lotus Work Entry", "Lotus Work Session", "Lotus Work Inspection"
_writing = ContextVar("lotus_field_report_write", default=False)
ASSIGN_FIELDS = ["name", "kind", "crew", "work_team", "farm_block", "work_type", "assigned_on", "due_date", "state",
                 "cancel_reason", "assigned_by", "modified", "work_group", "pay_mode", "cap_basis", "rate", "uom", "basis",
                 "norm_min", "lot_area_ha", "lot_trees", "qty_total", "amount", "reported_at", "approved_at", "locked_at",
                 "inspection", "return_reason", "company", "farm"]
OPEN_STATES = (rules.OPEN, rules.REPORTED, rules.APPROVED, rules.FAILED)
RIBBON_WEEKS = 16


def install_fields():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    create_custom_fields({
        "Work Team": [
            dict(fieldname="lotus_team_level", label="Cấp", fieldtype="Select", options="\nCrew\nTeam", insert_after="team_name"),
            dict(fieldname="lotus_parent_team", label="Thuộc đội", fieldtype="Link", options="Work Team", insert_after="lotus_team_level"),
            dict(fieldname="lotus_zones", label="Khu phụ trách", fieldtype="Data", insert_after="lotus_parent_team"),
            dict(fieldname="lotus_leader", label="Đội trưởng / tổ trưởng", fieldtype="Link", options="User", insert_after="lotus_zones"),
        ],
        "Work Type": [
            dict(fieldname="lotus_farm", label="Vườn dùng", fieldtype="Link", options="Farm", insert_after="work_name"),
            dict(fieldname="lotus_bunch_stage", label="Công đoạn buồng", fieldtype="Select",
                 options="\nSucker Select\nBud Injection\nCut Bud\nBag\nCare\nProp\nReject\nHarvest", insert_after="lotus_farm"),
            dict(fieldname="lotus_work_group", label="Nhóm việc", fieldtype="Select", options="\nBunch\nField\nProtection",
                 insert_after="lotus_bunch_stage"),
            dict(fieldname="lotus_pay_mode", label="Cách trả", fieldtype="Select", options="\nCount\nLot\nDaywork",
                 insert_after="lotus_work_group"),
            dict(fieldname="lotus_cap_basis", label="Trần theo", fieldtype="Select", options="\nCutBud\nLotTrees\nLotArea\nNone",
                 insert_after="lotus_pay_mode"),
            dict(fieldname="lotus_requires_material", label="Bắt buộc ghi vật tư", fieldtype="Check", insert_after="lotus_cap_basis"),
            dict(fieldname="lotus_records_disease", label="Ghi sâu bệnh (bệnh, số cây, mức độ)", fieldtype="Check",
                 insert_after="lotus_requires_material"),
        ],
        "Item": [
            dict(fieldname="lotus_phi_days", label="Lotus · Thời gian cách ly trước thu hoạch (ngày)", fieldtype="Int",
                 insert_after="stock_uom"),
        ],
        "Farm Block": [
            dict(fieldname="lotus_quarantine_until", label="Đang cách ly thu hoạch đến", fieldtype="Date", read_only=1),
            dict(fieldname="lotus_current_cycle_no", label="Vụ hiện tại", fieldtype="Int", insert_after="lotus_quarantine_until",
                 description="Vụ 1 là vụ trồng mới. Quản lý vườn chốt khi lô chuyển vụ."),
        ],
    }, update=True, ignore_validate=True)
    if frappe.db.table_exists(SESSION):
        # One buổi of one person may be shared between several lines of the sổ lô (weights add up to 1), but appears
        # once per line: held by the database, not only by the API.
        if frappe.db.has_index(f"tab{SESSION}", "lotus_work_session_once"):
            frappe.db.sql_ddl(f"alter table `tab{SESSION}` drop index lotus_work_session_once")
        frappe.db.add_unique(SESSION, ["employee", "posting_date", "session", "entry"], "lotus_work_session_line")
    if frappe.db.table_exists("Lotus Daily Report"):
        frappe.db.add_unique("Lotus Daily Report", ["farm", "work_team", "report_date"], "lotus_daily_report_once")


# ---------------------------------------------------------------- access

def _roles(user=None):
    user = user or frappe.session.user
    return set(frappe.get_roles(user)) if user != "Guest" else set()


def is_manager(user=None):
    user = user or frappe.session.user
    return user == "Administrator" or MANAGER in _roles(user)


def is_inspector(user=None):
    return is_manager(user) or INSPECTOR in _roles(user)


def require_farm(farm):
    if frappe.session.user == "Guest" or not farm or not farm_allowed(farm):
        frappe.throw("Bạn không có quyền với vườn này.", frappe.PermissionError)
    if not ({MANAGER, SUPERVISOR, LEADER, INSPECTOR} & _roles() or frappe.session.user == "Administrator"):
        frappe.throw("Tài khoản chưa có vai trò quản lý vườn, đội trưởng, tổ trưởng hoặc kỹ thuật vườn.", frappe.PermissionError)
    return frappe.get_cached_doc("Farm", farm)


def _teams(farm):
    return frappe.get_all("Work Team", filters={"farm": farm},
                          fields=["name", "team_code", "team_name", "active", "lotus_team_level", "lotus_parent_team",
                                  "lotus_zones", "lotus_leader"], order_by="team_name asc", limit_page_length=0)


def access(farm, crew, user=None):
    """What this user may do in one đội. Never trusts a client-sent list of teams."""
    user = user or frappe.session.user
    teams = {t.name: t for t in _teams(farm)}
    head = teams.get(crew)
    if not head or head.lotus_team_level != CREW:
        frappe.throw("Chọn đội thuộc vườn.")
    members = {name for name, t in teams.items() if t.lotus_parent_team == crew and t.lotus_team_level == TEAM}
    manager = is_manager(user)
    supervisor = manager or head.lotus_leader == user
    led = members if supervisor else {name for name in members if teams[name].lotus_leader == user}
    inspector = is_inspector(user)
    return frappe._dict(manager=manager, supervisor=supervisor, teams=led, members=members, crew=head, inspector=inspector,
                        own_crew=head.lotus_leader == user, zones=rules.crew_zones(head.lotus_zones),
                        read=supervisor or bool(led) or manager or inspector)


def permission(doc, user=None, permission_type=None):
    user = user or frappe.session.user
    if user == "Guest" or not farm_allowed(doc.get("farm"), user):
        return False
    if permission_type in ("write", "create", "delete", "submit", "cancel", "amend"):
        return _writing.get()
    return True


def farm_query(doctype):
    def query(user=None):
        return "1=0" if (user or frappe.session.user) == "Guest" else query_condition(doctype, user)
    return query


assignment_query = farm_query(ASSIGNMENT)
entry_query = farm_query(ENTRY)
session_query = farm_query(SESSION)
daily_report_query = farm_query("Lotus Daily Report")
forecast_snapshot_query = farm_query("Lotus Forecast Snapshot")
inspection_query = farm_query(INSPECTION)


def validate_document(doc):
    if not _writing.get():
        frappe.throw("Hãy lưu qua màn Công việc ngoài vườn.", frappe.PermissionError)


def validate_rate(doc):
    require_farm(doc.farm)
    if not is_manager():
        frappe.throw("Chỉ quản lý vườn sửa bảng giá khoán.", frappe.PermissionError)
    if doc.valid_to and getdate(doc.valid_to) < getdate(doc.valid_from):
        frappe.throw("Ngày kết thúc không được trước ngày áp dụng.")
    if flt(doc.rate) <= 0:
        frappe.throw("Đơn giá khoán phải lớn hơn 0.")
    if flt(doc.norm_max) and flt(doc.norm_min) > flt(doc.norm_max):
        frappe.throw("Năng suất tối thiểu không được lớn hơn tối đa.")
    clash = frappe.get_all("Lotus Piece Rate", filters={"farm": doc.farm, "work_type": doc.work_type,
                           "valid_from": doc.valid_from, "name": ["!=", doc.name or ""]}, limit=1)
    if clash:
        frappe.throw("Công việc này đã có giá áp dụng từ cùng ngày.")


def _closed(company, day):
    from lotus_farm.hr_period import is_closed
    # Serialize field pay with the final HR period signature.
    lock("Company", company)
    if is_closed(company, day):
        frappe.throw("Tháng công đã khóa sổ, không sửa báo cáo ngày này.")


def _store(doc):
    token = _writing.set(True)
    try:
        doc.save(ignore_permissions=True)
    finally:
        _writing.reset(token)


# ---------------------------------------------------------------- reference data

def farm_names(user=None):
    user = user or frappe.session.user
    if user == "Guest":
        return []
    if user == "Administrator":
        return frappe.get_all("Farm", pluck="name")
    return frappe.get_all("User Permission", filters={"user": user, "allow": "Farm"}, pluck="for_value")


def _blocks(farm):
    rows = frappe.get_all("Farm Block", filters={"farm": farm, "active": 1},
                          fields=["name", "block_code", "farm_zone", "area_ha", "lotus_tree_count", "lotus_quarantine_until"],
                          limit_page_length=0)
    rows.sort(key=lambda r: (str(r.farm_zone or ""), len(str(r.block_code or "")), str(r.block_code or "")))
    return rows


def _block_map(farm):
    return {b.name: dict(b, zone=str(b.farm_zone or "").upper(), trees=cint(b.lotus_tree_count),
                         quarantine_until=str(b.lotus_quarantine_until or "") or None) for b in _blocks(farm)}


def _rates(farm):
    return frappe.get_all("Lotus Piece Rate", filters={"farm": farm},
                          fields=["name", "work_type", "basis", "rate", "uom", "norm_min", "norm_max", "valid_from", "valid_to", "notes"],
                          order_by="valid_from desc", limit_page_length=0)


def _works(farm):
    priced = set(frappe.get_all("Lotus Piece Rate", filters={"farm": farm}, pluck="work_type"))
    rows = frappe.get_all("Work Type", filters={"active": 1},
                          fields=["name", "work_code", "work_name", "uom", "lotus_farm", "lotus_bunch_stage", "productivity_per_workday",
                                  "lotus_work_group", "lotus_pay_mode", "lotus_cap_basis", "lotus_requires_material",
                                  "lotus_records_disease"],
                          order_by="work_code asc", limit_page_length=0)
    return [w for w in rows if (w.lotus_farm == farm or w.name in priced) and w.lotus_pay_mode]


def ribbon(farm, day):
    """The cắt bắp ribbon colour in force on a day, or None."""
    rows = frappe.get_all("Bunch Tag", filters={"farm": farm, "enabled": 1, "period_basis": "Cut Bud",
                                                "valid_from": ["<=", day], "valid_to": [">=", day]},
                          fields=["name", "color_label", "display_name", "color_code", "week_number", "week_year"], order_by="valid_from desc", limit=1)
    return rows[0] if rows else None


def _ribbon_tags(farm, day):
    """Cắt bắp colours of the last weeks: what bao buồng / tỉa / chống đổ on a day can belong to."""
    return frappe.get_all("Bunch Tag", filters={"farm": farm, "enabled": 1, "period_basis": "Cut Bud", "valid_from": ["<=", day],
                                                "valid_to": [">=", add_days(day, -7 * RIBBON_WEEKS)]},
                          fields=["name", "color_label", "display_name", "color_code", "week_number", "week_year"],
                          order_by="valid_from desc", limit_page_length=0)


def _user_names(users):
    users = [u for u in set(users) if u]
    return {u.name: u.full_name or u.name for u in frappe.get_all("User", filters={"name": ["in", users or [""]]}, fields=["name", "full_name"])}


@frappe.whitelist()
def bootstrap():
    if frappe.session.user == "Guest":
        frappe.throw("Vui lòng đăng nhập.", frappe.AuthenticationError)
    from frappe.sessions import get_csrf_token
    from lotus_farm.forecast_snapshot import queue_missing_weeks
    queue_missing_weeks()
    roles = _roles()
    from lotus_farm.shift import can_open as packhouse
    return {"user": frappe.session.user, "today": nowdate(), "csrf_token": get_csrf_token(), "packhouse": packhouse(),
            "farms": frappe.get_all("Farm", filters={"name": ["in", farm_names() or [""]]}, fields=["name", "farm_name", "company"]),
            "manager": is_manager(), "supervisor": SUPERVISOR in roles, "leader": LEADER in roles, "inspector": is_inspector()}


@frappe.whitelist()
def setup(farm):
    require_farm(farm)
    teams = _teams(farm)
    names = _user_names([t.lotus_leader for t in teams])
    crews = [t for t in teams if t.lotus_team_level == CREW]
    zone_crew = {z: c.name for c in crews for z in rules.crew_zones(c.lotus_zones)}
    user = frappe.session.user
    manager = is_manager()
    for t in teams:
        t["leader_name"] = names.get(t.lotus_leader, t.lotus_leader or "")
        t["zones"] = rules.crew_zones(t.lotus_zones)
    blocks = [dict(b, crew=zone_crew.get(b["zone"])) for b in _block_map(farm).values()]
    today = nowdate()
    rates = _rates(farm)
    works = []
    for w in _works(farm):
        current = rules.rate_for(rates, w.name, today)
        works.append(dict(w, group=w.lotus_work_group or rules.FIELD_GROUP, pay_mode=w.lotus_pay_mode,
                          cap_basis=w.lotus_cap_basis or rules.CAP_NONE, requires_material=cint(w.lotus_requires_material),
                          rate=current and current.rate, basis=current and current.basis, norm_min=current and current.norm_min,
                          norm_max=current and current.norm_max, rate_uom=current and current.uom))
    my_crews = [c.name for c in crews if manager or c.lotus_leader == user]
    my_teams = [t.name for t in teams if t.lotus_team_level == TEAM and (t.lotus_leader == user or t.lotus_parent_team in my_crews)]
    for c in crews:
        if c.name not in my_crews and any(t.lotus_parent_team == c.name and t.lotus_leader == user for t in teams):
            my_crews.append(c.name)
    if is_inspector():
        my_crews += [c.name for c in crews if c.name not in my_crews]
    return {"farm": farm, "crews": crews, "teams": [t for t in teams if t.lotus_team_level != CREW], "blocks": blocks,
            "works": works, "rates": rates, "my_crews": my_crews, "my_teams": my_teams, "manager": manager, "today": today,
            "supervised_crews": [c.name for c in crews if manager or c.lotus_leader == user], "inspector": is_inspector(),
            "pass_marks": rules.PASS_MARK, "zones": sorted({b["zone"] for b in blocks if b["zone"]})}


@frappe.whitelist()
def item_options(search=None):
    if frappe.session.user == "Guest":
        frappe.throw("Vui lòng đăng nhập.", frappe.AuthenticationError)
    filters = {"disabled": 0, "is_stock_item": 1}
    or_filters = {"item_code": ["like", f"%{search}%"], "item_name": ["like", f"%{search}%"]} if search else None
    return frappe.get_all("Item", filters=filters, or_filters=or_filters, fields=["name", "item_name", "stock_uom", "lotus_phi_days"],
                          order_by="item_name asc", limit=30, ignore_permissions=True)


def _visible_crews(farm):
    teams = _teams(farm)
    user = frappe.session.user
    if is_manager() or is_inspector():
        return {t.name for t in teams if t.lotus_team_level == CREW}
    crews = {t.name for t in teams if t.lotus_team_level == CREW and t.lotus_leader == user}
    crews |= {t.lotus_parent_team for t in teams if t.lotus_team_level == TEAM and t.lotus_leader == user and t.lotus_parent_team}
    return crews


# ---------------------------------------------------------------- presence from the time clock

def presence(company, day):
    """Who the clock shows present on a day, by buổi: the saved attendance day if any, else the machine punches (the
    same reading as the timekeeping board). {employee: {employee_name, team, morning, afternoon}}"""
    from lotus_farm import daily_attendance as daily
    from lotus_farm.presence_rules import presence_status
    from datetime import datetime, time
    day = getdate(day)
    people = {p.name: p for p in frappe.get_all("Employee", filters={"company": company, "status": "Active"},
                                                fields=["name", "employee_name", "lotus_work_team"], limit_page_length=0)}
    result = {}
    records = {}
    for r in frappe.get_all("Attendance", filters={"company": company, "attendance_date": day, "docstatus": ["<", 2]},
                            fields=daily.FIELDS + ["attendance_date"], limit_page_length=0):
        records.setdefault(r.employee, []).append(r)
    punches = {}
    for p in frappe.get_all("Employee Checkin", filters={"employee": ["in", list(people) or [""]],
                                                         "time": ["between", [datetime.combine(day, time.min), datetime.combine(day, time.max)]]},
                            fields=["name", "employee", "time", "log_type"], order_by="time asc", limit_page_length=0):
        punches.setdefault(p.employee, []).append(p)
    for name, person in people.items():
        flags = {"morning": False, "afternoon": False}
        for record in records.get(name, []):
            saved = daily.saved_presence(record)
            flags["morning"] |= bool(saved["morning_present"])
            flags["afternoon"] |= bool(saved["afternoon_present"])
        if punches.get(name):
            machine = presence_status(day, punches[name])
            flags["morning"] |= bool(machine.get("morning_present"))
            flags["afternoon"] |= bool(machine.get("afternoon_present"))
        if flags["morning"] or flags["afternoon"]:
            result[name] = dict(employee=name, employee_name=person.employee_name, team=person.lotus_work_team, **flags)
    return result


# ---------------------------------------------------------------- phiếu: progress, caps, views

def _entries(names, day=None):
    filters = {"assignment": ["in", list(names) or [""]], "state": ["!=", "Voided"]}
    if day:
        filters["posting_date"] = day
    return frappe.get_all(ENTRY, filters=filters, fields=["name", "assignment", "posting_date", "qty", "bunch_tag", "done",
                                                          "morning_people", "afternoon_people", "under_norm", "state", "modified"],
                          order_by="posting_date asc", limit_page_length=0)


def _progress(names):
    result = {}
    for e in _entries(names):
        g = result.setdefault(e.assignment, {"qty": 0.0, "days": 0, "sessions": 0, "last_day": None})
        g["qty"] = round(g["qty"] + flt(e.qty), 4)
        g["days"] += 1
        g["sessions"] += cint(e.morning_people) + cint(e.afternoon_people)
        g["last_day"] = str(e.posting_date)
    return result


def _ticket_rows(rows, today=None):
    today = today or nowdate()
    progress = _progress([r.name for r in rows])
    for r in rows:
        p = progress.get(r.name) or {"qty": 0.0, "days": 0, "sessions": 0, "last_day": None}
        r.update(progress=p, assigned_on=str(r.assigned_on or ""), due_date=str(r.due_date or "") or None,
                 modified=str(r.modified), reported_at=str(r.reported_at or "") or None,
                 approved_at=str(r.approved_at or "") or None, locked_at=str(r.locked_at or "") or None,
                 display=rules.display_state(r.state, r.due_date, today, bool(p["days"])))
    return rows


def _stages(farm):
    return {w.name: w.lotus_bunch_stage for w in _works(farm) if w.lotus_bunch_stage}


def _bunch_counts(farm, tags, exclude_entry=None):
    """Bunches per (lô, màu) cut at cắt bắp and per (lô, màu, công đoạn) after it, over the reports of the farm."""
    cut, done = {}, {}
    tags = [t for t in set(tags) if t]
    if not tags:
        return cut, done
    # Every line of the sổ lô carries its stage: cắt bắp from daily reports and the opening book alike.
    rows = frappe.get_all(ENTRY, filters={"farm": farm, "bunch_tag": ["in", tags], "name": ["!=", exclude_entry or ""],
                                          "state": ["!=", "Voided"]},
                          fields=["farm_block", "bunch_tag", "stage", "qty"], limit_page_length=0)
    for r in rows:
        if r.stage == rules.CUT_BUD:
            cut[(r.farm_block, r.bunch_tag)] = cut.get((r.farm_block, r.bunch_tag), 0) + flt(r.qty)
        elif r.stage in rules.COLOUR_STAGES:
            key = (r.farm_block, r.bunch_tag, r.stage)
            done[key] = done.get(key, 0) + flt(r.qty)
    return cut, done


def _decorate(farm, rows):
    blocks, works = _block_map(farm), {w.name: w for w in _works(farm)}
    teams = {t.name: t.team_name for t in _teams(farm)}
    for r in rows:
        b = blocks.get(r.farm_block) or {}
        r.update(block_code=b.get("block_code") or r.farm_block, area_ha=flt(b.get("area_ha")), trees=cint(b.get("trees")),
                 quarantine_until=b.get("quarantine_until"),
                 work_name=works[r.work_type].work_name if r.work_type in works else (r.work_type or ""),
                 work_stage=works[r.work_type].lotus_bunch_stage if r.work_type in works else None,
                 requires_material=cint(works[r.work_type].lotus_requires_material) if r.work_type in works else 0,
                 team_name=teams.get(r.work_team, r.work_team))
    return rows


def _entry_view(name):
    doc = frappe.get_doc(ENTRY, name)
    tag = doc.bunch_tag and frappe.db.get_value("Bunch Tag", doc.bunch_tag, ["color_label", "display_name"], as_dict=True)
    return {"name": doc.name, "posting_date": str(doc.posting_date), "qty": doc.qty, "bunch_tag": doc.bunch_tag,
            "ribbon": tag and (tag.color_label or tag.display_name), "done": doc.done, "notes": doc.notes or "",
            "state": doc.state, "stage": doc.stage, "farm_block": doc.farm_block, "work_type": doc.work_type,
            "under_norm": doc.under_norm, "modified": str(doc.modified),
            "people": [{"employee": p.employee, "employee_name": p.employee_name, "morning": p.morning, "afternoon": p.afternoon}
                       for p in doc.get("people")],
            "materials": [{"item_code": m.item_code, "qty": m.qty, "uom": m.uom, "dose": m.dose or "", "stock_entry": m.stock_entry,
                           "phi_days": m.phi_days} for m in doc.get("materials")]}


@frappe.whitelist()
def ticket(name):
    """One phiếu with all its reports, its inspection and what this user may do with it."""
    task = frappe.get_doc(ASSIGNMENT, name)
    require_farm(task.farm)
    rights = access(task.farm, task.crew)
    if not (rights.read and (rights.supervisor or rights.inspector or task.work_team in rights.teams)):
        frappe.throw("Bạn không xem được phiếu này.", frappe.PermissionError)
    row = _decorate(task.farm, _ticket_rows([frappe._dict({k: task.get(k) for k in ASSIGN_FIELDS})]))[0]
    row["entries"] = [_entry_view(e.name) for e in _entries([task.name])]
    row["inspection_doc"] = frappe.db.get_value(INSPECTION, task.inspection, ["name", "inspector", "inspected_on", "sample_size",
                                                "passed_count", "score", "pass_mark", "result", "notes", "photo", "sample_rows"],
                                                as_dict=True) if task.inspection else None
    shares = _shares(task) if task.state == rules.LOCKED else {}
    names = {e.name: e.employee_name for e in frappe.get_all("Employee", filters={"name": ["in", list(shares) or [""]]},
                                                             fields=["name", "employee_name"])}
    row["shares"] = [{"employee": e, "employee_name": names.get(e, e), "amount": a} for e, a in shares.items()]
    leader_of_crew = rights.own_crew and not rights.manager
    row["actions"] = {
        "approve": task.state == rules.REPORTED and rights.supervisor,
        "return": task.state in (rules.REPORTED, rules.APPROVED) and rights.supervisor,
        "inspect": task.state == rules.APPROVED and task.pay_mode == rules.PAY_LOT and rights.inspector and not leader_of_crew,
        "cancel": task.state in (rules.OPEN, rules.REPORTED, rules.FAILED) and rights.supervisor,
    }
    return row


def _load_task(name, expected_modified=None):
    task = frappe.get_doc(ASSIGNMENT, name, for_update=True)
    require_farm(task.farm)
    if expected_modified and str(task.modified) != str(expected_modified):
        frappe.throw("Phiếu vừa được người khác sửa. Tải lại trước khi thao tác.", frappe.TimestampMismatchError)
    return task, access(task.farm, task.crew)


def _move(task, action):
    try:
        task.state = rules.next_state(task.state, action, task.pay_mode)
    except ValueError as e:
        frappe.throw(str(e))


@frappe.whitelist(methods=["POST"])
def approve(name, expected_modified=None):
    """Đội trưởng duyệt a phiếu báo xong. Counted and công nhật phiếu are then locked and paid; khoán lô waits for an
    inspection."""
    task, rights = _load_task(name, expected_modified)
    if not rights.supervisor:
        frappe.throw("Chỉ đội trưởng của đội (hoặc quản lý vườn) duyệt phiếu.", frappe.PermissionError)
    _closed(task.company, nowdate())
    _move(task, "approve")
    task.approved_by, task.approved_at = frappe.session.user, now_datetime()
    if task.state == rules.PASSED:
        _lock(task)
    _store(task)
    return ticket(task.name)


@frappe.whitelist(methods=["POST"])
def return_ticket(name, reason, expected_modified=None):
    task, rights = _load_task(name, expected_modified)
    if not rights.supervisor:
        frappe.throw("Chỉ đội trưởng của đội (hoặc quản lý vườn) trả lại phiếu.", frappe.PermissionError)
    reason = _reason(reason, "trả lại")
    _move(task, "return")
    task.return_reason, task.reported_at, task.approved_at = reason, None, None
    _store(task)
    task.add_comment("Comment", "Trả lại: " + reason)
    return ticket(task.name)


def _sample_plan(task):
    """The rows and trees the inspector checks, drawn by the system (not chosen by the inspector)."""
    rng = random.Random(f"{task.name}-{nowdate()}")
    start = rng.randint(1, 8)
    step = rng.choice((4, 5, 6))
    return f"Bắt đầu từ hàng {start}, cứ cách {step} hàng kiểm 4 cây liên tiếp, đủ số cây mẫu thì dừng."


@frappe.whitelist()
def inspection_plan(name):
    task, rights = _load_task(name)
    if not rights.inspector:
        frappe.throw("Chỉ kỹ thuật vườn hoặc quản lý vườn nghiệm thu.", frappe.PermissionError)
    group = task.work_group or rules.FIELD_GROUP
    return {"plan": _sample_plan(task), "pass_mark": rules.PASS_MARK.get(group, 90), "sample_size": 20 if group == rules.BUNCH_GROUP else 30}


@frappe.whitelist(methods=["POST"])
def inspect(name, sample_size, passed_count, notes=None, photo=None, expected_modified=None):
    """Kỹ thuật vườn nghiệm thu a khoán lô phiếu. The đội's own leader may not inspect it. Pass locks and pays the whole lô;
    Fail sends it back to the tổ to redo."""
    task, rights = _load_task(name, expected_modified)
    if not rights.inspector:
        frappe.throw("Chỉ kỹ thuật vườn hoặc quản lý vườn nghiệm thu.", frappe.PermissionError)
    if rights.own_crew and not rights.manager:
        frappe.throw("Đội trưởng không nghiệm thu việc của đội mình.", frappe.PermissionError)
    if task.pay_mode != rules.PAY_LOT:
        frappe.throw("Chỉ phiếu khoán lô cần nghiệm thu.")
    group = task.work_group or rules.FIELD_GROUP
    mark = rules.PASS_MARK.get(group, 90)
    try:
        score, result = rules.inspection_result(sample_size, passed_count, mark)
    except ValueError as e:
        frappe.throw(str(e))
    _move(task, "pass" if result == "Pass" else "fail")
    doc = frappe.new_doc(INSPECTION)
    doc.update({"assignment": task.name, "farm": task.farm, "farm_block": task.farm_block, "work_type": task.work_type,
                "inspector": frappe.session.user, "inspected_on": nowdate(), "sample_size": cint(sample_size),
                "passed_count": cint(passed_count), "score": score, "pass_mark": mark, "result": result,
                "sample_rows": _sample_plan(task), "notes": str(notes or "")[:1000], "photo": photo or None})
    _store(doc)
    task.inspection = doc.name
    if task.state == rules.PASSED:
        _lock(task)
    _store(task)
    return ticket(task.name)


def _lock(task):
    whole = rules.whole_lot_qty(task.basis, task.lot_area_ha, task.lot_trees)
    task.amount = rules.pay_amount(task.pay_mode, task.qty_total, whole, task.rate, passed=True)
    task.state = rules.next_state(task.state, "lock")
    task.locked_at = now_datetime()


def _weights(filters):
    """{key: {employee: weight}} over the buổi of confirmed sổ lô lines (a voided or unsent line pays nothing)."""
    key = filters.pop("_by")
    rows = frappe.db.sql(f"""select s.{key} as k, s.employee, sum(s.weight) as weight from `tab{SESSION}` s
        join `tab{ENTRY}` e on e.name = s.entry and e.state = 'Confirmed'
        where s.{key} in %(names)s group by s.{key}, s.employee""", {"names": tuple(filters["names"]) or ("",)}, as_dict=True)
    result = {}
    for r in rows:
        result.setdefault(r.k, {})[r.employee] = flt(r.weight)
    return result


def _sessions_by_employee(names):
    return _weights({"_by": "assignment", "names": list(names)})


def _shares(task):
    return rules.split_by_sessions(flt(task.amount), _sessions_by_employee([task.name]).get(task.name, {}))


@frappe.whitelist()
def inspections_due(farm):
    require_farm(farm)
    if not is_inspector():
        frappe.throw("Chỉ kỹ thuật vườn hoặc quản lý vườn nghiệm thu.", frappe.PermissionError)
    own = {t.name for t in _teams(farm) if t.lotus_team_level == CREW and t.lotus_leader == frappe.session.user}
    rows = frappe.get_all(ASSIGNMENT, filters={"farm": farm, "state": rules.APPROVED, "pay_mode": rules.PAY_LOT},
                          fields=ASSIGN_FIELDS, order_by="approved_at asc", limit_page_length=0)
    rows = [r for r in rows if is_manager() or r.crew not in own]
    return _decorate(farm, _ticket_rows(rows))


def month_piece(company, begin, end, teams=None):
    """Khoán money per employee for a month, from the sổ lô: every confirmed khoán-số-lượng line worked in [begin, end]
    (its amount split by the buổi weights on that line), and every khoán lô finished (locked) in the month (split by the
    buổi on the lines of that lô). Also the buổi worked on khoán lines in the month, which are not paid as công nhật.
    teams: only lines and lô of these tổ (for a tổ's own view); per person, `teams` holds the money by tổ."""
    result = {}

    def slot(employee):
        return result.setdefault(employee, dict(piece=0.0, piece_sessions=0.0, khoan_sessions=0.0, teams={}))

    filters = {"company": company, "state": "Confirmed", "pay_mode": rules.PAY_COUNT, "posting_date": ["between", [begin, end]], "amount": [">", 0]}
    if teams is not None:
        filters["work_team"] = ["in", list(teams) or [""]]
    lines = frappe.get_all(ENTRY, filters=filters, fields=["name", "amount", "work_team"], limit_page_length=0)
    weights = _weights({"_by": "entry", "names": [l.name for l in lines]})
    for line in lines:
        counts = weights.get(line.name, {})
        for employee, share in rules.split_by_sessions(flt(line.amount), counts).items():
            item = slot(employee)
            item["piece"] += share
            item["piece_sessions"] += counts.get(employee, 0)
            item["teams"][line.work_team] = item["teams"].get(line.work_team, 0) + share
    task_filters = {"company": company, "state": rules.LOCKED, "pay_mode": rules.PAY_LOT,
                    "locked_at": ["between", [str(begin) + " 00:00:00", str(end) + " 23:59:59"]]}
    if teams is not None:
        task_filters["work_team"] = ["in", list(teams) or [""]]
    locked = frappe.get_all(ASSIGNMENT, filters=task_filters, fields=["name", "amount", "work_team"], limit_page_length=0)
    by_task = _sessions_by_employee([t.name for t in locked])
    for task in locked:
        counts = by_task.get(task.name, {})
        for employee, share in rules.split_by_sessions(flt(task.amount), counts).items():
            item = slot(employee)
            item["piece"] += share
            item["piece_sessions"] += counts.get(employee, 0)
            item["teams"][task.work_team] = item["teams"].get(task.work_team, 0) + share
    # A khoán-lô buổi is paid by its Round: without one, or once it is cancelled, the buổi stays công nhật.
    for s in frappe.db.sql(f"""select s.employee, sum(s.weight) as weight from `tab{SESSION}` s
            join `tab{ENTRY}` e on e.name = s.entry and e.state = 'Confirmed'
            left join `tab{ASSIGNMENT}` a on a.name = s.assignment
            where s.company = %s and s.posting_date between %s and %s
              and (s.pay_mode = %s or (s.pay_mode = %s and a.kind = %s and a.state != %s)) group by s.employee""",
                           (company, begin, end, rules.PAY_COUNT, rules.PAY_LOT, rules.ROUND, rules.CANCELLED), as_dict=True):
        slot(s.employee)["khoan_sessions"] += flt(s.weight)
    return result


def work_rows(company, begin, end):
    """Workdays per employee, farm, lô and việc from the buổi on confirmed sổ lô lines (a whole buổi is 0,5 công), for
    labour cost by lô."""
    rows = frappe.db.sql(f"""select s.employee, sum(s.weight) / 2 as workdays, s.farm as lotus_farm, s.farm_block as lotus_farm_block,
            s.work_type as lotus_work_type from `tab{SESSION}` s join `tab{ENTRY}` e on e.name = s.entry and e.state = 'Confirmed'
        where s.company = %s and s.posting_date between %s and %s group by s.employee, s.farm, s.farm_block, s.work_type""",
                         (company, begin, end), as_dict=True)
    return [dict(r, workdays=flt(r.workdays)) for r in rows]


def pay_scope(farm):
    """Whose khoán money this user may see: {đội: None (every tổ) | the tổ they lead}. The manager sees every đội, a đội
    trưởng their đội, a tổ trưởng their tổ. Kỹ thuật vườn nghiệm thu but does not see money."""
    teams = _teams(farm)
    user = frappe.session.user
    if is_manager():
        return {t.name: None for t in teams if t.lotus_team_level == CREW}
    scope = {t.name: None for t in teams if t.lotus_team_level == CREW and t.lotus_leader == user}
    for t in teams:
        if t.lotus_team_level == TEAM and t.lotus_leader == user and t.lotus_parent_team and scope.get(t.lotus_parent_team, set()) is not None:
            scope.setdefault(t.lotus_parent_team, set()).add(t.name)
    return scope


@frappe.whitelist()
def payable(farm, month):
    """Tiền khoán của tháng theo người: dòng khoán số lượng đã xác nhận và lô khoán đã nghiệm thu, chia theo buổi."""
    require_farm(farm)
    allowed = pay_scope(farm)
    if not allowed:
        frappe.throw("Không có quyền xem tiền khoán.", frappe.PermissionError)
    begin = getdate(str(month)[:7] + "-01")
    end = get_last_day(begin)
    crews = list(allowed)
    lines = frappe.get_all(ENTRY, filters={"farm": farm, "crew": ["in", crews], "state": "Confirmed", "pay_mode": rules.PAY_COUNT,
                                           "posting_date": ["between", [begin, end]], "amount": [">", 0]},
                           fields=["name", "farm_block", "work_type", "work_team", "crew", "amount", "posting_date", "pay_mode"], limit_page_length=0)
    tickets = frappe.get_all(ASSIGNMENT, filters={"farm": farm, "crew": ["in", crews], "state": rules.LOCKED, "pay_mode": rules.PAY_LOT,
                                                  "locked_at": ["between", [str(begin) + " 00:00:00", str(end) + " 23:59:59"]]},
                             fields=ASSIGN_FIELDS, limit_page_length=0)
    lines = [l for l in lines if allowed[l.crew] is None or l.work_team in allowed[l.crew]]
    tickets = [t for t in tickets if allowed[t.crew] is None or t.work_team in allowed[t.crew]]
    _decorate(farm, lines)
    _decorate(farm, tickets)
    by_line = _weights({"_by": "entry", "names": [l.name for l in lines]})
    by_task = _sessions_by_employee([t.name for t in tickets])
    people = {e for group in (by_line, by_task) for counts in group.values() for e in counts}
    names = {e.name: e.employee_name for e in frappe.get_all("Employee", filters={"name": ["in", list(people) or [""]]}, fields=["name", "employee_name"])}
    rows = []
    for source, amount, counts, day in ([(l, l.amount, by_line.get(l.name, {}), str(l.posting_date)) for l in lines] +
                                        [(t, t.amount, by_task.get(t.name, {}), str(t.locked_at)[:10]) for t in tickets]):
        for employee, share in rules.split_by_sessions(flt(amount), counts).items():
            rows.append({"key": source.name + "|" + employee, "employee": employee, "employee_name": names.get(employee, employee),
                         "assignment": source.name, "block_code": source.block_code, "work_name": source.work_name, "team_name": source.team_name,
                         "pay_mode": source.pay_mode, "sessions": round(counts.get(employee, 0), 2), "amount": share,
                         "ticket_amount": flt(amount), "locked_at": day})
    rows.sort(key=lambda r: (r["employee_name"] or "", r["locked_at"]))
    return rows


# ---------------------------------------------------------------- giao việc theo lô

def _picked(blocks):
    picked = frappe.parse_json(blocks) if isinstance(blocks, str) and blocks.strip().startswith("[") else blocks
    if isinstance(picked, str):
        picked = picked.split(",")
    picked = list(dict.fromkeys(str(b).strip() for b in (picked or []) if str(b).strip()))
    if not picked or len(picked) > MAX_ASSIGN:
        frappe.throw(f"Chọn từ 1 đến {MAX_ASSIGN} lô.")
    return picked


def _crew_blocks(farm, rights, picked):
    known = _block_map(farm)
    bad = [b for b in picked if b not in known or known[b]["zone"] not in rights.zones]
    if bad:
        frappe.throw("Lô không thuộc khu của đội: " + ", ".join(known[b]["block_code"] if b in known else b for b in bad))
    return known


def _supervise(farm, crew):
    rights = access(farm, crew)
    if not rights.supervisor:
        frappe.throw("Chỉ đội trưởng của đội (hoặc quản lý vườn) giao việc.", frappe.PermissionError)
    return rights


@frappe.whitelist()
def assignments(farm, crew=None, state=None, team=None, from_date=None):
    """Phiếu giao of the đội this user sees. Tổ trưởng see only their tổ. Closed phiếu are listed from from_date
    (default 60 days back); open phiếu always."""
    require_farm(farm)
    crews = _visible_crews(farm)
    if crew:
        crews &= {crew}
    filters = {"farm": farm, "kind": rules.ROUND, "crew": ["in", list(crews) or [""]]}
    if team:
        filters["work_team"] = team
    if state == "open":
        filters["state"] = ["in", list(OPEN_STATES)]
    elif state:
        filters["state"] = state
    rows = frappe.get_all(ASSIGNMENT, filters=filters, fields=ASSIGN_FIELDS, order_by="assigned_on desc, modified desc",
                          limit_page_length=0)
    since = getdate(from_date or add_days(nowdate(), -60))
    allowed = {}
    for c in crews:
        rights = access(farm, c)
        allowed[c] = None if (rights.supervisor or rights.inspector) else rights.teams
    rows = [r for r in rows if (allowed.get(r.crew) is None or r.work_team in allowed[r.crew])
            and (r.state in OPEN_STATES or getdate(r.modified) >= since)]
    return _decorate(farm, _ticket_rows(rows))


@frappe.whitelist(methods=["POST"])
def assign(farm, crew, work_type, team, blocks, due_date=None, assigned_on=None):
    """Giao one việc on several lô to one tổ: one phiếu per lô. How it is paid, its price and its cap come from the
    catalogue and the price list of the day, and are fixed on the phiếu."""
    farm_doc = require_farm(farm)
    rights = _supervise(farm, crew)
    work = {w.name: w for w in _works(farm)}.get(work_type)
    if not work:
        frappe.throw("Chọn việc trong danh mục (việc đã có cách trả).")
    if team not in rights.members:
        frappe.throw("Chọn tổ thuộc đội.")
    picked = _picked(blocks)
    known = _crew_blocks(farm, rights, picked)
    day = getdate(assigned_on or nowdate())
    due = getdate(due_date) if due_date else None
    if due and due < day:
        frappe.throw("Hạn xong không được trước ngày giao.")
    price = rules.rate_for(_rates(farm), work_type, day)
    if work.lotus_pay_mode in rules.KHOAN and not price:
        frappe.throw(f"\"{work.work_name}\" là việc khoán nhưng chưa có giá áp dụng ngày {day.strftime('%d/%m/%Y')}.")
    lock("Farm", farm)
    taken = frappe.get_all(ASSIGNMENT, filters={"farm": farm, "kind": rules.ROUND, "state": ["in", list(OPEN_STATES)],
                                                "work_type": work_type, "farm_block": ["in", picked]}, fields=["farm_block", "work_team"])
    if taken:
        teams = {t.name: t.team_name for t in _teams(farm)}
        frappe.throw(f"\"{work.work_name}\" đang giao, chưa xong ở lô "
                     + ", ".join(f"{known[t.farm_block]['block_code']} ({teams.get(t.work_team, t.work_team)})" for t in taken)
                     + ". Làm xong hoặc huỷ phiếu cũ trước.")
    made = []
    for block in picked:
        b = known[block]
        doc = frappe.new_doc(ASSIGNMENT)
        doc.update({"kind": rules.ROUND, "company": farm_doc.company, "farm": farm, "crew": crew, "work_team": team,
                    "farm_block": block, "work_type": work_type, "assigned_on": day, "due_date": due, "state": rules.OPEN,
                    "assigned_by": frappe.session.user, "work_group": work.lotus_work_group or rules.FIELD_GROUP,
                    "pay_mode": work.lotus_pay_mode, "cap_basis": work.lotus_cap_basis or rules.CAP_NONE,
                    "piece_rate": price and price.name, "rate": flt(price.rate) if price and work.lotus_pay_mode in rules.KHOAN else 0,
                    "uom": (price and price.uom) or work.uom, "basis": price and price.basis, "norm_min": price and flt(price.norm_min),
                    "lot_area_ha": flt(b["area_ha"]), "lot_trees": cint(b["trees"])})
        _store(doc)
        made.append(doc.name)
    return {"created": made}


def _reason(text, label):
    text = str(text or "").strip()
    if not text:
        frappe.throw(f"Ghi lý do {label}.")
    return text[:500]


@frappe.whitelist(methods=["POST"])
def reassign(name, team, reason, expected_modified=None):
    task, rights = _load_task(name, expected_modified)
    if not rights.supervisor:
        frappe.throw("Chỉ đội trưởng của đội (hoặc quản lý vườn) đổi tổ.", frappe.PermissionError)
    reason = _reason(reason, "đổi tổ")
    if task.state not in (rules.OPEN, rules.FAILED):
        frappe.throw("Chỉ đổi tổ cho phiếu đang làm (chưa báo xong).")
    if team not in rights.members:
        frappe.throw("Chọn tổ thuộc đội.")
    if team == task.work_team:
        return ticket(name)
    teams = {t.name: t.team_name for t in _teams(task.farm)}
    old = task.work_team
    task.work_team = team
    _store(task)
    task.add_comment("Comment", f"Đổi tổ {teams.get(old, old)} → {teams.get(team, team)}: {reason}")
    return ticket(name)


@frappe.whitelist(methods=["POST"])
def cancel_assignment(name, reason, expected_modified=None):
    task, rights = _load_task(name, expected_modified)
    if not rights.supervisor:
        frappe.throw("Chỉ đội trưởng của đội (hoặc quản lý vườn) huỷ phiếu.", frappe.PermissionError)
    reason = _reason(reason, "huỷ phiếu")
    _move(task, "cancel")
    task.cancel_reason = reason
    _store(task)
    return ticket(name)


def harvest_guard(doc, method=None):
    """Harvest Actual validate: a lô sprayed with a product that has a pre-harvest interval cannot be harvested before it ends."""
    if not doc.get("farm_block") or not doc.get("harvest_date"):
        return
    until = frappe.db.get_value("Farm Block", doc.farm_block, "lotus_quarantine_until")
    if until and getdate(doc.harvest_date) <= getdate(until):
        frappe.throw(f"Lô đang trong thời gian cách ly thuốc BVTV đến {getdate(until).strftime('%d/%m/%Y')}; chưa được thu hoạch.")


# ---------------------------------------------------------------- giao lô: đội, tổ, bảng giá

@frappe.whitelist(methods=["POST"])
def save_crew(farm, team_name, zones, leader=None, name=None):
    require_farm(farm)
    if not is_manager():
        frappe.throw("Chỉ quản lý vườn tạo hoặc sửa đội.", frappe.PermissionError)
    zones = rules.crew_zones(zones)
    if not zones or not str(team_name or "").strip():
        frappe.throw("Nhập tên đội và ít nhất một khu.")
    known = {str(z).upper() for z in frappe.get_all("Farm Block", filters={"farm": farm}, pluck="farm_zone") if z}
    if set(zones) - known:
        frappe.throw("Khu không có trong vườn: " + ", ".join(sorted(set(zones) - known)))
    for other in _teams(farm):
        if other.lotus_team_level == CREW and other.name != name and set(zones) & set(rules.crew_zones(other.lotus_zones)):
            frappe.throw(f"Khu {', '.join(sorted(set(zones) & set(rules.crew_zones(other.lotus_zones))))} đã thuộc {other.team_name}.")
    _check_user(leader, farm)
    doc = frappe.get_doc("Work Team", name) if name else frappe.new_doc("Work Team")
    if name and doc.farm != farm:
        frappe.throw("Đội không thuộc vườn.")
    doc.update({"farm": farm, "team_name": str(team_name).strip(), "active": 1, "lotus_team_level": CREW,
                "lotus_zones": ", ".join(zones), "lotus_leader": leader or None, "lotus_parent_team": None})
    if not doc.team_code:
        doc.team_code = "DOI-" + "".join(zones)
    doc.save()
    return doc.name


@frappe.whitelist(methods=["POST"])
def save_team(farm, name, crew=None, leader=None):
    """Đặt tổ vào đội và chọn tổ trưởng. Quản lý vườn: mọi tổ; đội trưởng: tổ chưa thuộc đội nào hoặc tổ của mình."""
    require_farm(farm)
    doc = frappe.get_doc("Work Team", name)
    if doc.farm != farm or doc.get("lotus_team_level") == CREW:
        frappe.throw("Chọn tổ thuộc vườn.")
    crews = {t.name: t for t in _teams(farm) if t.lotus_team_level == CREW}
    if crew and crew not in crews:
        frappe.throw("Chọn đội thuộc vườn.")
    if not is_manager():
        mine = {c for c, t in crews.items() if t.lotus_leader == frappe.session.user}
        if (doc.lotus_parent_team and doc.lotus_parent_team not in mine) or (crew and crew not in mine):
            frappe.throw("Đội trưởng chỉ sắp xếp tổ của đội mình.", frappe.PermissionError)
    _check_user(leader, farm)
    doc.lotus_team_level, doc.lotus_parent_team, doc.lotus_leader = TEAM, crew or None, leader or None
    doc.flags.ignore_permissions = True
    doc.save()
    return doc.name


def _check_user(user, farm):
    if not user:
        return
    if not frappe.db.get_value("User", {"name": user, "enabled": 1}):
        frappe.throw("Tài khoản không tồn tại hoặc đã khóa.")
    if user != "Administrator" and not farm_allowed(farm, user):
        frappe.throw("Tài khoản này chưa được cấp quyền vườn. Cấp quyền ở Người dùng & phân quyền trước.")


@frappe.whitelist()
def user_options(farm):
    require_farm(farm)
    users = frappe.get_all("User Permission", filters={"allow": "Farm", "for_value": farm}, pluck="user")
    return frappe.get_all("User", filters={"name": ["in", users or [""]], "enabled": 1}, fields=["name", "full_name"],
                          order_by="full_name asc", limit_page_length=0)


@frappe.whitelist(methods=["POST"])
def save_rate(farm, work_type, rate, valid_from, basis="Count", uom=None, norm_min=None, norm_max=None, valid_to=None, notes=None, name=None):
    require_farm(farm)
    if name and frappe.db.exists(ASSIGNMENT, {"piece_rate": name}):
        frappe.throw("Giá này đã dùng trên phiếu giao. Tạo giá mới với ngày áp dụng mới thay vì sửa.")
    doc = frappe.get_doc("Lotus Piece Rate", name) if name else frappe.new_doc("Lotus Piece Rate")
    doc.update({"farm": farm, "work_type": work_type, "rate": flt(rate), "valid_from": valid_from, "basis": basis,
                "uom": uom or frappe.db.get_value("Work Type", work_type, "uom"), "norm_min": flt(norm_min),
                "norm_max": flt(norm_max), "valid_to": valid_to or None, "notes": notes})
    doc.save()
    return doc.name


@frappe.whitelist(methods=["POST"])
def save_work_mode(farm, work_type, group, pay_mode, cap_basis=None, requires_material=0):
    """Quản lý vườn đặt nhóm và cách trả của một việc trong danh mục. Phiếu đã giao giữ cách trả lúc giao."""
    require_farm(farm)
    if not is_manager():
        frappe.throw("Chỉ quản lý vườn đặt cách trả của việc.", frappe.PermissionError)
    if group not in rules.GROUPS or pay_mode not in rules.PAY_MODES:
        frappe.throw("Chọn nhóm việc và cách trả.")
    if (cap_basis or rules.CAP_NONE) not in (rules.CAP_CUT_BUD, rules.CAP_TREES, rules.CAP_AREA, rules.CAP_NONE):
        frappe.throw("Chọn trần hợp lệ.")
    doc = frappe.get_doc("Work Type", work_type)
    doc.update({"lotus_farm": doc.lotus_farm or farm, "lotus_work_group": group, "lotus_pay_mode": pay_mode,
                "lotus_cap_basis": cap_basis or rules.CAP_NONE, "lotus_requires_material": 1 if cint(requires_material) else 0})
    doc.flags.ignore_permissions = True
    doc.save()
    return doc.name
