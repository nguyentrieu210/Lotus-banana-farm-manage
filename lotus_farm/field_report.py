"""Đội daily report (báo cáo ngày), giao việc theo lô and giao lô.

Lots belong to a đội through their khu (Work Team lotus_zones). The đội trưởng (lotus_leader of the đội) gives work
lot by lot (phiếu giao, Lotus Work Assignment kind Round: lô, việc, tổ, hạn) and gives each lô to a tổ chăm buồng
(kind Bunch, standing until changed). Tổ trưởng (lotus_leader of a tổ) report on the phiếu of their own tổ, which the
report lists ready to fill: công sáng/chiều, khối lượng and Xong. The đội trưởng edits every line, records the weather
and confirms the day once; that confirmation also closes the phiếu ticked Xong. Quản lý vườn reads everything and may
reopen. Confirmed công khoán (CK) lines are the money owed to each tổ: hr_period adds them to "Phải trả đội khoán".
Công nhật (CN) lines only record workdays; wages come from attendance. Rules that need no database live in
field_report_rules.
"""
from contextvars import ContextVar

import frappe
from frappe.utils import add_days, cint, flt, get_last_day, getdate, now_datetime, nowdate

from lotus_farm import field_report_rules as rules
from lotus_farm.controls import farm_allowed, lock, query_condition

MANAGER, SUPERVISOR, LEADER = "Lotus Farm Manager", "Lotus Field Supervisor", "Lotus Team Leader"
CREW, TEAM = "Crew", "Team"
MAX_LINES, MAX_MATERIALS, MAX_ASSIGN = 300, 4, 200
ASSIGNMENT = "Lotus Work Assignment"
_writing = ContextVar("lotus_field_report_write", default=False)
LINE_KEYS = {"line_id", "work_type", "pay_kind", "work_team", "location", "farm_block", "blocks", "zone",
             "workdays_am", "workdays_pm", "qty", "whole_lot", "under_norm_reason", "comment", "proposal", "note",
             "materials", "assignment", "done", "bunch_tag"}
ASSIGN_FIELDS = ["name", "kind", "crew", "work_team", "farm_block", "work_type", "assigned_on", "due_date", "state",
                 "ended_on", "done_report", "done_date", "cancel_reason", "assigned_by", "modified"]
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
                 options="\nBud Injection\nCut Bud\nBag\nCare\nProp", insert_after="lotus_farm"),
        ],
    }, update=True, ignore_validate=True)


# ---------------------------------------------------------------- access

def _roles(user=None):
    user = user or frappe.session.user
    return set(frappe.get_roles(user)) if user != "Guest" else set()


def is_manager(user=None):
    user = user or frappe.session.user
    return user == "Administrator" or MANAGER in _roles(user)


def require_farm(farm):
    if frappe.session.user == "Guest" or not farm or not farm_allowed(farm):
        frappe.throw("Bạn không có quyền với vườn này.", frappe.PermissionError)
    if not ({MANAGER, SUPERVISOR, LEADER} & _roles() or frappe.session.user == "Administrator"):
        frappe.throw("Tài khoản chưa có vai trò quản lý vườn, đội trưởng hoặc tổ trưởng.", frappe.PermissionError)
    return frappe.get_cached_doc("Farm", farm)


def _teams(farm):
    return frappe.get_all("Work Team", filters={"farm": farm},
                          fields=["name", "team_code", "team_name", "active", "lotus_team_level", "lotus_parent_team",
                                  "lotus_zones", "lotus_leader"], order_by="team_name asc", limit_page_length=0)


def access(farm, crew, user=None):
    """What this user may do in one đội's report. Never trusts a client-sent list of teams."""
    user = user or frappe.session.user
    teams = {t.name: t for t in _teams(farm)}
    head = teams.get(crew)
    if not head or head.lotus_team_level != CREW:
        frappe.throw("Chọn đội thuộc vườn.")
    members = {name for name, t in teams.items() if t.lotus_parent_team == crew and t.lotus_team_level == TEAM}
    manager = is_manager(user)
    supervisor = manager or head.lotus_leader == user
    led = members if supervisor else {name for name in members if teams[name].lotus_leader == user}
    return frappe._dict(manager=manager, supervisor=supervisor, teams=led, members=members, crew=head,
                        zones=rules.crew_zones(head.lotus_zones), read=supervisor or bool(led) or manager)


def permission(doc, user=None, permission_type=None):
    user = user or frappe.session.user
    if user == "Guest" or not farm_allowed(doc.get("farm"), user):
        return False
    if permission_type in ("write", "create", "delete", "submit", "cancel", "amend"):
        return _writing.get()
    return True


def report_query(user=None):
    return "1=0" if (user or frappe.session.user) == "Guest" else query_condition("Lotus Field Report", user)


def assignment_query(user=None):
    return "1=0" if (user or frappe.session.user) == "Guest" else query_condition(ASSIGNMENT, user)


def validate_document(doc):
    if not _writing.get():
        frappe.throw("Hãy lưu qua màn Báo cáo ngày.", frappe.PermissionError)


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
    # Serialize the new crew-pay source with the final HR period signature.
    lock("Company", company)
    if is_closed(company, day):
        frappe.throw("Tháng công đã khóa sổ, không sửa báo cáo ngày này.")


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
                          fields=["name", "block_code", "farm_zone", "area_ha", "lotus_tree_count"], limit_page_length=0)
    rows.sort(key=lambda r: (str(r.farm_zone or ""), len(str(r.block_code or "")), str(r.block_code or "")))
    return rows


def _block_map(farm):
    return {b.name: dict(b, zone=str(b.farm_zone or "").upper(), trees=cint(b.lotus_tree_count)) for b in _blocks(farm)}


def _rates(farm):
    return frappe.get_all("Lotus Piece Rate", filters={"farm": farm},
                          fields=["name", "work_type", "basis", "rate", "uom", "norm_min", "norm_max", "valid_from", "valid_to", "notes"],
                          order_by="valid_from desc", limit_page_length=0)


def _works(farm):
    priced = set(frappe.get_all("Lotus Piece Rate", filters={"farm": farm}, pluck="work_type"))
    rows = frappe.get_all("Work Type", filters={"active": 1},
                          fields=["name", "work_code", "work_name", "uom", "lotus_farm", "lotus_bunch_stage", "productivity_per_workday"],
                          order_by="work_code asc", limit_page_length=0)
    return [w for w in rows if w.lotus_farm == farm or w.name in priced]


def ribbon(farm, day):
    """The cắt bắp ribbon colour in force on a day, or None."""
    rows = frappe.get_all("Bunch Tag", filters={"farm": farm, "enabled": 1, "period_basis": "Cut Bud",
                                                "valid_from": ["<=", day], "valid_to": [">=", day]},
                          fields=["name", "color_label", "display_name", "color_code", "week_number", "week_year"], order_by="valid_from desc", limit=1)
    return rows[0] if rows else None


def _user_names(users):
    users = [u for u in set(users) if u]
    return {u.name: u.full_name or u.name for u in frappe.get_all("User", filters={"name": ["in", users or [""]]}, fields=["name", "full_name"])}


@frappe.whitelist()
def bootstrap():
    if frappe.session.user == "Guest":
        frappe.throw("Vui lòng đăng nhập.", frappe.AuthenticationError)
    from frappe.sessions import get_csrf_token
    roles = _roles()
    return {"user": frappe.session.user, "today": nowdate(), "csrf_token": get_csrf_token(),
            "farms": frappe.get_all("Farm", filters={"name": ["in", farm_names() or [""]]}, fields=["name", "farm_name", "company"]),
            "manager": is_manager(), "supervisor": SUPERVISOR in roles, "leader": LEADER in roles}


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
    blocks = [dict(b, zone=str(b.farm_zone or "").upper(), trees=cint(b.lotus_tree_count),
                   crew=zone_crew.get(str(b.farm_zone or "").upper())) for b in _blocks(farm)]
    today = nowdate()
    rates = _rates(farm)
    works = []
    for w in _works(farm):
        current = rules.rate_for(rates, w.name, today)
        works.append(dict(w, section="Bunch" if w.lotus_bunch_stage else "Field", rate=current and current.rate,
                          basis=current and current.basis, norm_min=current and current.norm_min,
                          norm_max=current and current.norm_max, rate_uom=current and current.uom))
    my_crews = [c.name for c in crews if manager or c.lotus_leader == user]
    my_teams = [t.name for t in teams if t.lotus_team_level == TEAM and (t.lotus_leader == user or t.lotus_parent_team in my_crews)]
    for c in crews:
        if c.name not in my_crews and any(t.lotus_parent_team == c.name and t.lotus_leader == user for t in teams):
            my_crews.append(c.name)
    return {"farm": farm, "crews": crews, "teams": [t for t in teams if t.lotus_team_level != CREW], "blocks": blocks,
            "works": works, "rates": rates, "my_crews": my_crews, "my_teams": my_teams, "manager": manager, "today": today,
            "supervised_crews": [c.name for c in crews if manager or c.lotus_leader == user],
            "zones": sorted({b["zone"] for b in blocks if b["zone"]})}


@frappe.whitelist()
def item_options(search=None):
    if frappe.session.user == "Guest":
        frappe.throw("Vui lòng đăng nhập.", frappe.AuthenticationError)
    filters = {"disabled": 0, "is_stock_item": 1}
    or_filters = {"item_code": ["like", f"%{search}%"], "item_name": ["like", f"%{search}%"]} if search else None
    return frappe.get_all("Item", filters=filters, or_filters=or_filters, fields=["name", "item_name", "stock_uom"],
                          order_by="item_name asc", limit=30, ignore_permissions=True)


# ---------------------------------------------------------------- the report

def _find(farm, crew, day):
    return frappe.db.get_value("Lotus Field Report", {"farm": farm, "crew": crew, "posting_date": day})


def _view(doc, rights):
    materials = {}
    for m in doc.get("materials"):
        materials.setdefault(m.line_id, []).append({"item_code": m.item_code, "qty": m.qty, "uom": m.uom})
    names = _user_names([doc.confirmed_by] + [r.entered_by for r in doc.get("lines")])
    tags = {t.name: t.color_label or t.display_name for t in frappe.get_all("Bunch Tag", filters={"name": ["in", [r.bunch_tag for r in doc.get("lines") if r.bunch_tag] or [""]]},
                                                                            fields=["name", "color_label", "display_name"])}
    lines = []
    for r in doc.get("lines"):
        row = {k: r.get(k) for k in ("line_id", "section", "assignment", "work_type", "pay_kind", "work_team", "location",
                                      "farm_block", "blocks", "zone", "workdays_am", "workdays_pm", "workdays", "qty", "done",
                                      "uom", "whole_lot", "lot_area_ha", "lot_trees", "piece_rate", "rate", "amount",
                                      "paid_qty", "under_norm", "under_norm_reason", "bunch_tag", "over_cut", "comment",
                                      "proposal", "note", "entered_by")}
        row["entered_by_name"] = names.get(r.entered_by, r.entered_by)
        row["ribbon"] = tags.get(r.bunch_tag)
        row["materials"] = materials.get(r.line_id, [])
        row["editable"] = bool(rights.supervisor or r.work_team in rights.teams)
        lines.append(row)
    day = str(doc.posting_date)
    return {"name": doc.name, "farm": doc.farm, "crew": doc.crew, "date": day, "weather": doc.weather or "",
            "state": doc.state, "return_reason": doc.return_reason or "", "confirmed_by": doc.confirmed_by,
            "confirmed_by_name": names.get(doc.confirmed_by, doc.confirmed_by), "confirmed_at": str(doc.confirmed_at or ""),
            "modified": str(doc.modified), "lines": lines, "ribbon": _ribbon_view(doc.farm, day),
            "overdue": rules.overdue(doc.posting_date, now_datetime(), doc.state),
            "totals": _totals(doc.get("lines")),
            **_context(doc.farm, doc.crew, day, rights, doc.name, [r.assignment for r in doc.get("lines") if r.assignment])}


def _ribbon_view(farm, day):
    tag = ribbon(farm, day)
    return tag and {"name": tag.name, "label": tag.color_label or tag.display_name, "code": tag.color_code, "week": tag.week_number}


def _totals(lines):
    return {"workdays": round(sum(flt(r.get("workdays")) for r in lines), 2),
            "piece_amount": round(sum(flt(r.get("amount")) for r in lines)),
            "lines": len(lines), "under_norm": sum(1 for r in lines if r.get("under_norm")),
            "done": sum(1 for r in lines if r.get("done")), "over_cut": sum(1 for r in lines if r.get("over_cut"))}


# ---------------------------------------------------------------- phiếu giao: what a report can be written on

def _progress(names, exclude=None):
    """Per phiếu: workdays and khối lượng reported so far, the days reported and a Xong waiting for confirmation."""
    names = [n for n in set(names) if n]
    if not names:
        return {}
    rows = frappe.db.sql("""select l.assignment, l.workdays, l.qty, l.done, r.name as report, r.state, r.posting_date
        from `tabLotus Field Report Line` l join `tabLotus Field Report` r on r.name = l.parent
        where l.parenttype = 'Lotus Field Report' and l.assignment in %(names)s and r.name != %(exclude)s""",
                         {"names": tuple(names), "exclude": exclude or ""}, as_dict=True)
    result = {}
    for r in rows:
        g = result.setdefault(r.assignment, {"workdays": 0.0, "qty": 0.0, "days": 0, "reported_done": None, "last_day": None})
        g["workdays"] = round(g["workdays"] + flt(r.workdays), 2)
        g["qty"] = round(g["qty"] + flt(r.qty), 4)
        g["days"] += 1
        g["last_day"] = max(filter(None, [g["last_day"], str(r.posting_date)]))
        if r.done and r.state != "Confirmed":
            g["reported_done"] = {"report": r.report, "date": str(r.posting_date)}
    return result


def _assignment_rows(rows, today=None, exclude=None):
    today = today or nowdate()
    progress = _progress([r.name for r in rows], exclude)
    for r in rows:
        p = progress.get(r.name) or {"workdays": 0.0, "qty": 0.0, "days": 0, "reported_done": None, "last_day": None}
        r.update(progress=p, assigned_on=str(r.assigned_on or ""), due_date=str(r.due_date or "") or None,
                 done_date=str(r.done_date or "") or None, ended_on=str(r.ended_on or "") or None, modified=str(r.modified),
                 display=rules.display_state(r.state, r.due_date, today, bool(p["days"]), bool(p["reported_done"])))
    return rows


def _open_rounds(farm, crew, teams=None, day=None):
    filters = {"farm": farm, "crew": crew, "kind": rules.ROUND, "state": rules.OPEN}
    if day:
        filters["assigned_on"] = ["<=", day]
    if teams is not None:
        filters["work_team"] = ["in", list(teams) or [""]]
    return frappe.get_all(ASSIGNMENT, filters=filters, fields=ASSIGN_FIELDS, order_by="due_date asc, assigned_on asc",
                          limit_page_length=0)


def _bunch_lots(farm, day, crew=None):
    """Standing chăm buồng assignments in force on a day: {farm_block: assignment}."""
    filters = {"farm": farm, "kind": rules.BUNCH, "assigned_on": ["<=", day], "state": ["in", [rules.OPEN, rules.ENDED]]}
    if crew:
        filters["crew"] = crew
    rows = frappe.get_all(ASSIGNMENT, filters=filters, fields=ASSIGN_FIELDS, order_by="assigned_on asc", limit_page_length=0)
    return {r.farm_block: r for r in rows if r.state == rules.OPEN or (r.ended_on and getdate(r.ended_on) >= getdate(day))}


def _stages(farm):
    return {w.name: w.lotus_bunch_stage for w in _works(farm) if w.lotus_bunch_stage}


def _ribbon_tags(farm, day):
    """Cắt bắp colours of the last weeks: what bao buồng / tỉa / chống đổ on a day can belong to."""
    return frappe.get_all("Bunch Tag", filters={"farm": farm, "enabled": 1, "period_basis": "Cut Bud", "valid_from": ["<=", day],
                                                "valid_to": [">=", add_days(day, -7 * RIBBON_WEEKS)]},
                          fields=["name", "color_label", "display_name", "color_code", "week_number", "week_year"],
                          order_by="valid_from desc", limit_page_length=0)


def _bunch_counts(farm, tags, exclude=None):
    """Bunches per (lô, màu) cut at cắt bắp and per (lô, màu, công đoạn) after it, over the reports of the farm."""
    cut, done = {}, {}
    tags = [t for t in set(tags) if t]
    if not tags:
        return cut, done
    stages = _stages(farm)
    rows = frappe.db.sql("""select l.farm_block, l.bunch_tag, l.work_type, l.qty
        from `tabLotus Field Report Line` l join `tabLotus Field Report` r on r.name = l.parent
        where l.parenttype = 'Lotus Field Report' and r.farm = %(farm)s and l.bunch_tag in %(tags)s and r.name != %(exclude)s""",
                         {"farm": farm, "tags": tuple(tags), "exclude": exclude or ""}, as_dict=True)
    for r in rows:
        stage = stages.get(r.work_type)
        if stage == rules.CUT_BUD:
            cut[(r.farm_block, r.bunch_tag)] = cut.get((r.farm_block, r.bunch_tag), 0) + flt(r.qty)
        elif stage in rules.COLOUR_STAGES:
            key = (r.farm_block, r.bunch_tag, stage)
            done[key] = done.get(key, 0) + flt(r.qty)
    return cut, done


def _context(farm, crew, day, rights, report=None, referenced=()):
    """What the day editor needs besides the saved lines: the open phiếu of the tổ it may report for, the lots each tổ
    chăm buồng holds that day, and the ribbon colours with the bunches already counted in the other reports."""
    teams = None if rights.supervisor else rights.teams
    rows = {r.name: r for r in _open_rounds(farm, crew, teams, day)}
    missing = [n for n in referenced if n not in rows]
    if missing:
        rows.update({r.name: r for r in frappe.get_all(ASSIGNMENT, filters={"name": ["in", missing]}, fields=ASSIGN_FIELDS)})
    tags = _ribbon_tags(farm, day)
    cut, done = _bunch_counts(farm, [t.name for t in tags], report)
    lots = _bunch_lots(farm, day, crew)
    return {"assignments": _assignment_rows(list(rows.values()), exclude=report),
            "bunch_lots": {b: a.work_team for b, a in lots.items()},
            "ribbon_options": [{"name": t.name, "label": t.color_label or t.display_name, "code": t.color_code,
                                "week": t.week_number, "year": t.week_year} for t in tags],
            "bunch_cut": {f"{b}|{t}": n for (b, t), n in cut.items()},
            "bunch_done": {f"{b}|{t}|{s}": n for (b, t, s), n in done.items()},
            "cap_blocks": rules.cap_blocks(day)}


def _rights_view(rights):
    return {"supervisor": rights.supervisor, "manager": rights.manager, "teams": sorted(rights.teams),
            "can_confirm": rights.supervisor, "can_reopen": rights.supervisor}


@frappe.whitelist()
def get(farm, crew, date):
    require_farm(farm)
    day = str(getdate(date))
    rights = access(farm, crew)
    if not rights.read:
        frappe.throw("Bạn không thuộc đội này.", frappe.PermissionError)
    name = _find(farm, crew, day)
    base = {"ribbon": _ribbon_view(farm, day), "rights": _rights_view(rights)}
    if not name:
        return {**base, "name": None, "farm": farm, "crew": crew, "date": day, "weather": "", "state": "Draft",
                "lines": [], "modified": None, "overdue": rules.overdue(day, now_datetime(), "Draft"),
                "totals": _totals([]), **_context(farm, crew, day, rights)}
    return {**base, **_view(frappe.get_doc("Lotus Field Report", name), rights)}


def _clean_line(raw, i, ctx, previous):
    prefix = f"Dòng {i}: "
    if not isinstance(raw, dict) or set(raw) - LINE_KEYS:
        frappe.throw(prefix + "dữ liệu có trường không được phép.")
    line_id = str(raw.get("line_id") or "")
    if not (8 <= len(line_id) <= 64) or not line_id.replace("-", "").isalnum():
        frappe.throw(prefix + "mã dòng không hợp lệ.")
    rights = ctx["rights"]
    task = None
    if raw.get("assignment"):
        # A line on a phiếu giao takes its việc, lô and tổ from the phiếu, never from what the client sent.
        task = ctx["assignments"].get(raw["assignment"])
        kept = bool(previous and previous.assignment == raw["assignment"])
        if not task or task.kind != rules.ROUND or task.crew != rights.crew.name:
            frappe.throw(prefix + "phiếu giao không thuộc đội này.")
        if task.state != rules.OPEN and not kept:
            frappe.throw(prefix + "phiếu giao đã " + ("xong" if task.state == rules.DONE else "huỷ") + ", không báo thêm.")
        if getdate(task.assigned_on) > getdate(ctx["day"]) and not kept:
            frappe.throw(prefix + f"phiếu giao từ ngày {task.assigned_on}, không báo cho ngày trước đó.")
        raw = dict(raw, work_type=task.work_type, farm_block=task.farm_block, location=rules.BLOCK,
                   work_team=previous.work_team if kept else task.work_team)
    work = ctx["works"].get(raw.get("work_type"))
    if not work:
        frappe.throw(prefix + "chọn công việc trong danh mục của vườn.")
    stage = work.lotus_bunch_stage or ""
    team = raw.get("work_team") or (next(iter(rights.teams)) if len(rights.teams) == 1 and not rights.supervisor else None)
    if team and team not in rights.members:
        frappe.throw(prefix + "tổ không thuộc đội này.")
    if not rights.supervisor and team not in rights.teams:
        frappe.throw(prefix + "tổ trưởng chỉ nhập dòng của tổ mình.", frappe.PermissionError)
    try:
        nums = rules.check_line(raw, prefix)
    except ValueError as e:
        frappe.throw(str(e))
    piece = raw.get("pay_kind") == rules.PIECE
    if piece and not team:
        frappe.throw(prefix + "công khoán phải chọn tổ làm.")
    if piece and not stage and not task:
        frappe.throw(prefix + "công khoán việc vườn phải báo trên phiếu giao. Đội trưởng giao lô trước, hoặc ghi công nhật.")
    done = bool(cint(raw.get("done")))
    if done and not task:
        frappe.throw(prefix + "chỉ đánh dấu Xong trên phiếu giao.")
    if stage in rules.COLOUR_STAGES + (rules.CUT_BUD,) and nums["location"] != rules.BLOCK:
        frappe.throw(prefix + "công đoạn buồng ghi theo từng lô.")
    block = None
    blocks, zone = "", ""
    if nums["location"] == rules.BLOCK:
        block = ctx["blocks"].get(raw.get("farm_block"))
        if not block or block["zone"] not in rights.zones:
            frappe.throw(prefix + "lô không thuộc khu của đội.")
    elif nums["location"] == rules.BLOCKS:
        picked = [b.strip() for b in str(raw.get("blocks")).split(",") if b.strip()]
        if any(b not in ctx["blocks"] or ctx["blocks"][b]["zone"] not in rights.zones for b in picked):
            frappe.throw(prefix + "có lô không thuộc khu của đội.")
        blocks = ",".join(dict.fromkeys(picked))
    else:
        zone = str(raw.get("zone") or "").upper()
        if zone not in rights.zones:
            frappe.throw(prefix + "khu không thuộc đội.")
    if stage and piece and ctx["bunch_lots"].get(block["name"]) != team:
        frappe.throw(prefix + f"lô {block['block_code']} không giao chăm buồng cho tổ này vào ngày báo cáo.")
    price = rules.rate_for(ctx["rates"], work.name, ctx["day"])
    if piece and not price:
        frappe.throw(prefix + f"chưa có giá khoán cho \"{work.work_name}\" vào ngày này.")
    basis = price and price.basis
    qty = nums["qty"]
    area = trees = 0
    whole = None
    if block:
        same = previous and previous.farm_block == block["name"]
        area = flt(previous.lot_area_ha) if same else flt(block["area_ha"])
        trees = cint(previous.lot_trees) if same else cint(block["trees"])
        whole = rules.whole_lot_qty(basis, area, trees)
    rate = flt(price.rate) if price and piece else 0
    if not piece:
        money, paid = 0, 0.0
    elif task:
        money, paid = rules.round_amount(basis, done, qty, whole, rate), rules.paid_qty(basis, done, qty, whole)
    else:
        money, paid = rules.amount(rules.PIECE, qty, rate), qty
    low = rules.under_norm(qty, nums["workdays"], price and price.norm_min)
    reason = str(raw.get("under_norm_reason") or "").strip()[:500]
    if low and not reason:
        frappe.throw(prefix + "chưa đạt ngày công so với định mức, ghi lý do.")
    tag = None
    if stage == rules.CUT_BUD:
        tag = ctx["ribbon"].name if ctx["ribbon"] else None
    elif stage in rules.COLOUR_STAGES:
        tag = raw.get("bunch_tag")
        if not tag:
            frappe.throw(prefix + "chọn màu dây của lứa buồng đang làm.")
        if tag not in ctx["tags"] and not (previous and previous.bunch_tag == tag):
            frappe.throw(prefix + "màu dây không có trong lịch cắt bắp các tuần gần đây.")
    return {"line_id": line_id, "section": "Bunch" if stage else "Field", "assignment": task and task.name,
            "work_type": work.name, "pay_kind": raw.get("pay_kind"), "work_team": team, "location": nums["location"],
            "farm_block": block and block["name"], "blocks": blocks, "zone": zone,
            "workdays_am": nums["workdays_am"], "workdays_pm": nums["workdays_pm"], "workdays": nums["workdays"],
            "qty": qty, "done": 1 if done else 0, "uom": (price and price.uom) or work.uom,
            "whole_lot": 1 if done and whole is not None else 0, "lot_area_ha": area, "lot_trees": trees,
            "piece_rate": price and price.name, "rate": rate, "amount": money, "paid_qty": paid,
            "under_norm": 1 if low else 0, "under_norm_reason": reason if low else "", "bunch_tag": tag, "over_cut": 0,
            "stage": stage,
            "comment": str(raw.get("comment") or "")[:500], "proposal": str(raw.get("proposal") or "")[:500],
            "note": str(raw.get("note") or "")[:500],
            "entered_by": previous.entered_by if previous else frappe.session.user}


def _clean_materials(raw, prefix):
    items = raw or []
    if not isinstance(items, list) or len(items) > MAX_MATERIALS:
        frappe.throw(prefix + f"tối đa {MAX_MATERIALS} vật tư mỗi dòng.")
    result = []
    for m in items:
        if not isinstance(m, dict) or not m.get("item_code"):
            continue
        item = frappe.db.get_value("Item", m["item_code"], ["name", "stock_uom", "disabled"], as_dict=True)
        if not item or item.disabled:
            frappe.throw(prefix + "vật tư không có trong danh mục kho.")
        try:
            qty = rules.number(m.get("qty"), prefix + "Số lượng vật tư")
        except ValueError as e:
            frappe.throw(str(e))
        if qty <= 0:
            frappe.throw(prefix + "nhập số lượng vật tư lớn hơn 0.")
        result.append({"item_code": item.name, "qty": qty, "uom": item.stock_uom})
    return result


@frappe.whitelist(methods=["POST"])
def save(farm, crew, date, lines, weather=None, expected_modified=None):
    farm_doc = require_farm(farm)
    day = str(getdate(date))
    if getdate(day) > getdate(nowdate()):
        frappe.throw("Không báo cáo cho ngày tương lai.")
    _closed(farm_doc.company, day)
    rights = access(farm, crew)
    if not rights.read:
        frappe.throw("Bạn không thuộc đội này.", frappe.PermissionError)
    lines = frappe.parse_json(lines)
    if not isinstance(lines, list) or len(lines) > MAX_LINES:
        frappe.throw(f"Báo cáo cần là danh sách, tối đa {MAX_LINES} dòng.")
    lock("Farm", farm)
    name = _find(farm, crew, day)
    doc = frappe.get_doc("Lotus Field Report", name, for_update=True) if name else frappe.new_doc("Lotus Field Report")
    if name and str(doc.modified) != str(expected_modified or ""):
        frappe.throw("Báo cáo vừa được người khác sửa. Tải lại để xem bản mới rồi nhập tiếp.", frappe.TimestampMismatchError)
    if doc.state == "Confirmed":
        frappe.throw("Báo cáo đã xác nhận. Đội trưởng mở lại (ghi lý do) rồi mới sửa.")
    previous = {r.line_id: r for r in doc.get("lines")}
    old_materials = {}
    for m in doc.get("materials"):
        old_materials.setdefault(m.line_id, []).append(m)
    wanted = {str(l.get("assignment")) for l in lines if isinstance(l, dict) and l.get("assignment")}
    wanted |= {r.assignment for r in doc.get("lines") if r.assignment}
    ctx = {"rights": rights, "day": day, "rates": _rates(farm), "ribbon": ribbon(farm, day),
           "works": {w.name: w for w in _works(farm)}, "blocks": _block_map(farm),
           "assignments": {r.name: r for r in frappe.get_all(ASSIGNMENT, filters={"farm": farm, "name": ["in", list(wanted) or [""]]},
                                                            fields=ASSIGN_FIELDS)},
           "bunch_lots": {b: a.work_team for b, a in _bunch_lots(farm, day).items()},
           "tags": {t.name for t in _ribbon_tags(farm, day)}}
    # Tổ trưởng send only their own tổ's lines; everyone else's lines stay as they are.
    kept = [] if rights.supervisor else [r for r in doc.get("lines") if r.work_team not in rights.teams]
    kept_ids = {r.line_id for r in kept}
    cleaned, materials, seen = [], [], set(kept_ids)
    on_task = {r.assignment for r in kept if r.assignment}
    for i, raw in enumerate(lines, 1):
        line_id = str((raw or {}).get("line_id") or "") if isinstance(raw, dict) else ""
        if line_id in seen:
            frappe.throw(f"Dòng {i}: mã dòng trùng hoặc thuộc tổ khác.")
        seen.add(line_id)
        row = _clean_line(raw, i, ctx, previous.get(line_id))
        if row["assignment"]:
            if row["assignment"] in on_task:
                frappe.throw(f"Dòng {i}: phiếu giao này đã có dòng khác trong báo cáo; mỗi phiếu ghi một dòng mỗi ngày.")
            on_task.add(row["assignment"])
        cleaned.append(row)
        materials += [dict(m, line_id=line_id) for m in _clean_materials(raw.get("materials"), f"Dòng {i}: ")]
    if not cleaned and not kept and not name:
        frappe.throw("Thêm ít nhất một dòng công việc.")
    finished = [r["assignment"] for r in cleaned if r["done"]]
    if finished:
        other = frappe.db.sql("""select l.assignment, r.posting_date from `tabLotus Field Report Line` l
            join `tabLotus Field Report` r on r.name = l.parent where l.parenttype = 'Lotus Field Report' and l.done = 1
            and l.assignment in %(names)s and r.name != %(me)s""", {"names": tuple(finished), "me": doc.name or ""}, as_dict=True)
        if other:
            block = ctx["assignments"][other[0].assignment].farm_block
            frappe.throw(f"Phiếu giao lô {_block_code(ctx, block)} đã báo Xong ngày {other[0].posting_date}. "
                         "Bỏ dấu Xong ở báo cáo đó trước.")
    _check_ribbon(farm, day, doc.name, kept, cleaned, ctx)
    for row in cleaned:
        row.pop("stage", None)
    doc.farm, doc.crew, doc.posting_date, doc.company = farm, crew, day, farm_doc.company
    if rights.supervisor and weather is not None:
        doc.weather = str(weather).strip()[:200]
    keep_rows = [{k: r.get(k) for k in LINE_KEYS - {"materials"} | {"section", "workdays", "uom", "lot_area_ha", "lot_trees",
                  "piece_rate", "rate", "amount", "paid_qty", "under_norm", "over_cut", "entered_by"}} for r in kept]
    doc.set("lines", [])
    for row in keep_rows + cleaned:
        doc.append("lines", {**row, "name": previous[row["line_id"]].name if row["line_id"] in previous else None})
    doc.set("materials", [])
    for line_id in kept_ids:
        for m in old_materials.get(line_id, []):
            doc.append("materials", {"line_id": line_id, "item_code": m.item_code, "qty": m.qty, "uom": m.uom})
    for m in materials:
        doc.append("materials", m)
    if doc.state == "Returned":
        doc.state = "Draft"
    _store(doc)
    return {**_view(doc, rights), "rights": _rights_view(rights)}


def _block_code(ctx, block):
    return ctx["blocks"][block]["block_code"] if block in ctx["blocks"] else block


def _check_ribbon(farm, day, report, kept, cleaned, ctx):
    """Bao buồng, tỉa trái and chống đổ of one colour may not count more bunches than were cut of that colour in that
    lô. Before rules.BUNCH_CAP_FROM the lines are only flagged over_cut; from then on the save is refused."""
    stages = _stages(farm)
    rows = [dict(farm_block=r.farm_block, bunch_tag=r.bunch_tag, stage=stages.get(r.work_type), qty=r.qty, row=None) for r in kept]
    rows += [dict(farm_block=r["farm_block"], bunch_tag=r["bunch_tag"], stage=r["stage"], qty=r["qty"], row=r) for r in cleaned]
    tags = {r["bunch_tag"] for r in rows if r["bunch_tag"]}
    if not tags:
        return
    cut, done = _bunch_counts(farm, tags, report)
    for r in rows:
        if r["stage"] == rules.CUT_BUD and r["bunch_tag"]:
            cut[(r["farm_block"], r["bunch_tag"])] = cut.get((r["farm_block"], r["bunch_tag"]), 0) + flt(r["qty"])
    over = rules.bunch_over_cut(cut, done, rows)
    if over and rules.cap_blocks(day):
        (block, tag, _), (total, limit) = next(iter(over.items()))
        tag_doc = frappe.db.get_value("Bunch Tag", tag, ["color_label", "display_name"], as_dict=True) or {}
        label = tag_doc.get("color_label") or tag_doc.get("display_name") or tag
        frappe.throw(f"Lô {_block_code(ctx, block)}, màu {label}: cộng dồn {total:g} buồng, vượt số đã cắt bắp ({limit:g}).")
    for r in rows:
        if r["row"] is not None:
            r["row"]["over_cut"] = 1 if (r["farm_block"], r["bunch_tag"], r["stage"]) in over else 0


def _store(doc):
    token = _writing.set(True)
    try:
        doc.save(ignore_permissions=True)
    finally:
        _writing.reset(token)


def _load(name, expected_modified):
    source = frappe.db.get_value("Lotus Field Report", name, ["company", "posting_date"], as_dict=True)
    if not source:
        frappe.throw("Không tìm thấy báo cáo ngày.", frappe.DoesNotExistError)
    _closed(source.company, source.posting_date)
    doc = frappe.get_doc("Lotus Field Report", name, for_update=True)
    require_farm(doc.farm)
    if str(doc.modified) != str(expected_modified or ""):
        frappe.throw("Báo cáo vừa được người khác sửa. Tải lại trước khi thao tác.", frappe.TimestampMismatchError)
    rights = access(doc.farm, doc.crew)
    if not rights.supervisor:
        frappe.throw("Chỉ đội trưởng của đội (hoặc quản lý vườn) làm việc này.", frappe.PermissionError)
    return doc, rights


@frappe.whitelist(methods=["POST"])
def confirm(name, expected_modified=None):
    doc, rights = _load(name, expected_modified)
    if doc.state == "Confirmed":
        return {**_view(doc, rights), "rights": _rights_view(rights)}
    if not doc.get("lines"):
        frappe.throw("Báo cáo chưa có dòng nào.")
    missing = [i for i, r in enumerate(doc.get("lines"), 1) if r.under_norm and not str(r.under_norm_reason or "").strip()]
    if missing:
        frappe.throw("Dòng " + ", ".join(map(str, missing)) + " chưa đạt ngày công nhưng chưa ghi lý do.")
    # Confirming the day also confirms every phiếu ticked Xong in it.
    for r in doc.get("lines"):
        if not (r.done and r.assignment):
            continue
        task = frappe.get_doc(ASSIGNMENT, r.assignment, for_update=True)
        if task.state != rules.OPEN:
            frappe.throw(f"Phiếu giao lô {frappe.db.get_value('Farm Block', task.farm_block, 'block_code')} đã "
                         + ("xong ở báo cáo khác." if task.state == rules.DONE else "huỷ; bỏ dấu Xong rồi xác nhận."))
        task.state, task.done_report, task.done_line, task.done_date = rules.DONE, doc.name, r.line_id, doc.posting_date
        _store(task)
    doc.state, doc.confirmed_by, doc.confirmed_at, doc.return_reason = "Confirmed", frappe.session.user, now_datetime(), ""
    _store(doc)
    over = sum(1 for r in doc.get("lines") if r.over_cut)
    if over:
        doc.add_comment("Comment", f"Xác nhận dù {over} dòng chăm buồng vượt số đã cắt bắp cùng màu.")
    return {**_view(doc, rights), "rights": _rights_view(rights)}


@frappe.whitelist(methods=["POST"])
def return_report(name, reason, expected_modified=None):
    doc, rights = _load(name, expected_modified)
    reason = str(reason or "").strip()
    if not reason:
        frappe.throw("Ghi lý do trả lại cho tổ trưởng.")
    if doc.state == "Confirmed":
        frappe.throw("Báo cáo đã xác nhận; mở lại trước.")
    doc.state, doc.return_reason = "Returned", reason[:500]
    _store(doc)
    return {**_view(doc, rights), "rights": _rights_view(rights)}


@frappe.whitelist(methods=["POST"])
def reopen(name, reason, expected_modified=None):
    doc, rights = _load(name, expected_modified)
    reason = str(reason or "").strip()
    if not reason:
        frappe.throw("Ghi lý do mở lại báo cáo đã xác nhận.")
    if doc.state != "Confirmed":
        frappe.throw("Báo cáo chưa xác nhận, không cần mở lại.")
    doc.state, doc.reopen_reason, doc.confirmed_by, doc.confirmed_at = "Draft", reason[:500], None, None
    for task_name in frappe.get_all(ASSIGNMENT, filters={"done_report": doc.name, "state": rules.DONE}, pluck="name"):
        task = frappe.get_doc(ASSIGNMENT, task_name, for_update=True)
        task.state, task.done_report, task.done_line, task.done_date = rules.OPEN, None, None, None
        _store(task)
    _store(doc)
    return {**_view(doc, rights), "rights": _rights_view(rights)}


def _range(farm, from_date, to_date):
    require_farm(farm)
    start, end = getdate(from_date), getdate(to_date)
    if start > end:
        frappe.throw("Từ ngày phải trước hoặc bằng đến ngày.")
    if (end - start).days > 400:
        frappe.throw("Chọn khoảng tối đa 400 ngày.")
    return str(start), str(end)


def _visible_crews(farm):
    teams = _teams(farm)
    user = frappe.session.user
    if is_manager():
        return {t.name for t in teams if t.lotus_team_level == CREW}
    crews = {t.name for t in teams if t.lotus_team_level == CREW and t.lotus_leader == user}
    crews |= {t.lotus_parent_team for t in teams if t.lotus_team_level == TEAM and t.lotus_leader == user and t.lotus_parent_team}
    return crews


@frappe.whitelist()
def reports(farm, from_date, to_date, crew=None):
    start, end = _range(farm, from_date, to_date)
    crews = _visible_crews(farm)
    if crew:
        crews &= {crew}
    docs = frappe.get_all("Lotus Field Report", filters={"farm": farm, "crew": ["in", list(crews) or [""]],
                          "posting_date": ["between", [start, end]]},
                          fields=["name", "crew", "posting_date", "state", "weather", "confirmed_by", "confirmed_at", "modified"],
                          order_by="posting_date desc", limit_page_length=0)
    lines = frappe.get_all("Lotus Field Report Line", filters={"parent": ["in", [d.name for d in docs] or [""]],
                           "parenttype": "Lotus Field Report"},
                           fields=["parent", "workdays", "amount", "under_norm"], limit_page_length=0)
    by = {}
    for r in lines:
        by.setdefault(r.parent, []).append(r)
    now = now_datetime()
    for d in docs:
        d.update(_totals(by.get(d.name, [])), date=str(d.posting_date), overdue=rules.overdue(d.posting_date, now, d.state))
    return docs


@frappe.whitelist()
def report_lines(farm, from_date, to_date, crew=None, section=None):
    start, end = _range(farm, from_date, to_date)
    crews = _visible_crews(farm)
    if crew:
        crews &= {crew}
    parents = {d.name: d for d in frappe.get_all("Lotus Field Report", filters={"farm": farm, "crew": ["in", list(crews) or [""]],
               "posting_date": ["between", [start, end]]}, fields=["name", "crew", "posting_date", "state"], limit_page_length=0)}
    filters = {"parent": ["in", list(parents) or [""]], "parenttype": "Lotus Field Report"}
    if section:
        filters["section"] = section
    rows = frappe.get_all("Lotus Field Report Line", filters=filters,
                          fields=["parent", "line_id", "section", "assignment", "work_type", "pay_kind", "work_team", "location",
                                  "farm_block", "blocks", "zone", "workdays", "qty", "done", "uom", "rate", "amount", "under_norm",
                                  "under_norm_reason", "bunch_tag", "over_cut", "comment", "note"], limit_page_length=0)
    tags = {t.name: t.color_label or t.display_name for t in frappe.get_all("Bunch Tag", filters={"name": ["in", list({r.bunch_tag for r in rows if r.bunch_tag}) or [""]]},
                                                                            fields=["name", "color_label", "display_name"])}
    for r in rows:
        p = parents[r.parent]
        r.update(date=str(p.posting_date), crew=p.crew, state=p.state, ribbon=tags.get(r.bunch_tag))
    rows.sort(key=lambda r: (r["date"], r.parent), reverse=True)
    return rows


def confirmed_piece_lines(company, begin, end):
    """Confirmed công khoán lines in a period, for "Phải trả đội khoán" (hr_period). qty is the paid quantity: the whole
    lot on the day a phiếu was ticked Xong, nothing on the days before it, the counted quantity for counted work."""
    parents = frappe.get_all("Lotus Field Report", filters={"company": company, "state": "Confirmed",
                             "posting_date": ["between", [begin, end]]}, pluck="name", limit_page_length=0)
    if not parents:
        return []
    return frappe.get_all("Lotus Field Report Line", filters={"parent": ["in", parents], "parenttype": "Lotus Field Report",
                          "pay_kind": rules.PIECE}, fields=["work_team", "work_type", "uom", "rate", "paid_qty as qty", "workdays",
                                                            "amount", "farm_block"],
                          limit_page_length=0)


@frappe.whitelist()
def payable(farm, month):
    farm_doc = require_farm(farm)
    if not is_manager() and not _visible_crews(farm):
        frappe.throw("Không có quyền xem tiền khoán.", frappe.PermissionError)
    begin = getdate(str(month)[:7] + "-01")
    end = get_last_day(begin)
    visible = None if is_manager() else {t.name for t in _teams(farm) if t.lotus_parent_team in _visible_crews(farm)}
    groups = {}
    for r in confirmed_piece_lines(farm_doc.company, begin, end):
        if visible is not None and r.work_team not in visible:
            continue
        key = (r.work_team, r.work_type, r.uom, flt(r.rate))
        g = groups.setdefault(key, {"work_team": r.work_team, "work_type": r.work_type, "uom": r.uom, "rate": flt(r.rate),
                                    "qty": 0.0, "workdays": 0.0, "amount": 0.0})
        g["qty"] += flt(r.qty)
        g["workdays"] += flt(r.workdays)
        g["amount"] += flt(r.amount)
    return sorted(groups.values(), key=lambda g: (str(g["work_team"]), str(g["work_type"])))


# ---------------------------------------------------------------- giao việc theo lô, giao chăm buồng

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


def _decorate(farm, rows):
    blocks, works = _block_map(farm), {w.name: w for w in _works(farm)}
    teams = {t.name: t.team_name for t in _teams(farm)}
    for r in rows:
        b = blocks.get(r.farm_block) or {}
        r.update(block_code=b.get("block_code") or r.farm_block, area_ha=flt(b.get("area_ha")), trees=cint(b.get("trees")),
                 work_name=works[r.work_type].work_name if r.work_type in works else (r.work_type or ""),
                 team_name=teams.get(r.work_team, r.work_team))
    return rows


@frappe.whitelist()
def assignments(farm, crew=None, kind=rules.ROUND, state=None, team=None, from_date=None):
    """Phiếu giao of the đội this user sees. Tổ trưởng see only their tổ. Closed phiếu are listed from from_date
    (default 60 days back); open phiếu always."""
    require_farm(farm)
    crews = _visible_crews(farm)
    if crew:
        crews &= {crew}
    filters = {"farm": farm, "kind": kind, "crew": ["in", list(crews) or [""]]}
    if team:
        filters["work_team"] = team
    if state:
        filters["state"] = state
    rows = frappe.get_all(ASSIGNMENT, filters=filters, fields=ASSIGN_FIELDS, order_by="assigned_on desc, modified desc",
                          limit_page_length=0)
    since = getdate(from_date or add_days(nowdate(), -60))
    allowed = {}
    for c in crews:
        rights = access(farm, c)
        allowed[c] = None if rights.supervisor else rights.teams
    rows = [r for r in rows if (allowed.get(r.crew) is None or r.work_team in allowed[r.crew])
            and (r.state == rules.OPEN or getdate(r.modified) >= since)]
    return _decorate(farm, _assignment_rows(rows))


@frappe.whitelist(methods=["POST"])
def assign(farm, crew, work_type, team, blocks, due_date=None, assigned_on=None):
    """Giao one việc vườn on several lô to one tổ: one phiếu per lô."""
    farm_doc = require_farm(farm)
    rights = _supervise(farm, crew)
    work = {w.name: w for w in _works(farm)}.get(work_type)
    if not work or work.lotus_bunch_stage:
        frappe.throw("Chọn việc vườn trong danh mục. Chăm sóc buồng giao ở mục Giao chăm buồng.")
    if team not in rights.members:
        frappe.throw("Chọn tổ thuộc đội.")
    picked = _picked(blocks)
    known = _crew_blocks(farm, rights, picked)
    day = getdate(assigned_on or nowdate())
    due = getdate(due_date) if due_date else None
    if due and due < day:
        frappe.throw("Hạn xong không được trước ngày giao.")
    lock("Farm", farm)
    taken = frappe.get_all(ASSIGNMENT, filters={"farm": farm, "kind": rules.ROUND, "state": rules.OPEN, "work_type": work_type,
                                                "farm_block": ["in", picked]}, fields=["farm_block", "work_team"])
    if taken:
        teams = {t.name: t.team_name for t in _teams(farm)}
        frappe.throw(f"\"{work.work_name}\" đang giao, chưa xong ở lô "
                     + ", ".join(f"{known[t.farm_block]['block_code']} ({teams.get(t.work_team, t.work_team)})" for t in taken)
                     + ". Báo xong hoặc huỷ phiếu cũ trước.")
    made = []
    for block in picked:
        doc = frappe.new_doc(ASSIGNMENT)
        doc.update({"kind": rules.ROUND, "company": farm_doc.company, "farm": farm, "crew": crew, "work_team": team,
                    "farm_block": block, "work_type": work_type, "assigned_on": day, "due_date": due, "state": rules.OPEN,
                    "assigned_by": frappe.session.user})
        _store(doc)
        made.append(doc.name)
    return {"created": made}


def _load_task(name, expected_modified=None):
    task = frappe.get_doc(ASSIGNMENT, name, for_update=True)
    require_farm(task.farm)
    if expected_modified and str(task.modified) != str(expected_modified):
        frappe.throw("Phiếu giao vừa được người khác sửa. Tải lại trước khi thao tác.", frappe.TimestampMismatchError)
    return task, _supervise(task.farm, task.crew)


def _reason(text, label):
    text = str(text or "").strip()
    if not text:
        frappe.throw(f"Ghi lý do {label}.")
    return text[:500]


@frappe.whitelist(methods=["POST"])
def reassign(name, team, reason, expected_modified=None):
    task, rights = _load_task(name, expected_modified)
    reason = _reason(reason, "đổi tổ")
    if task.kind != rules.ROUND or task.state != rules.OPEN:
        frappe.throw("Chỉ đổi tổ cho phiếu đang giao.")
    if team not in rights.members:
        frappe.throw("Chọn tổ thuộc đội.")
    if team == task.work_team:
        return name
    if (_progress([name]).get(name) or {}).get("reported_done"):
        frappe.throw("Tổ đã báo Xong phiếu này, chờ đội trưởng xác nhận; không đổi tổ.")
    teams = {t.name: t.team_name for t in _teams(task.farm)}
    old = task.work_team
    task.work_team = team
    _store(task)
    task.add_comment("Comment", f"Đổi tổ {teams.get(old, old)} → {teams.get(team, team)}: {reason}")
    return name


@frappe.whitelist(methods=["POST"])
def cancel_assignment(name, reason, expected_modified=None):
    task, _ = _load_task(name, expected_modified)
    reason = _reason(reason, "huỷ phiếu")
    if task.kind != rules.ROUND or task.state != rules.OPEN:
        frappe.throw("Chỉ huỷ phiếu đang giao.")
    if (_progress([name]).get(name) or {}).get("reported_done"):
        frappe.throw("Tổ đã báo Xong phiếu này. Bỏ dấu Xong trong báo cáo ngày trước khi huỷ.")
    task.state, task.cancel_reason = rules.CANCELLED, reason
    _store(task)
    return name


@frappe.whitelist(methods=["POST"])
def bunch_assign(farm, crew, blocks, team=None, from_date=None, reason=None):
    """Giao lô chăm buồng cho tổ, from a day until changed. A lô held by another tổ is handed over (reason required);
    no team ends the assignment."""
    farm_doc = require_farm(farm)
    rights = _supervise(farm, crew)
    if team and team not in rights.members:
        frappe.throw("Chọn tổ thuộc đội.")
    picked = _picked(blocks)
    known = _crew_blocks(farm, rights, picked)
    start = getdate(from_date or nowdate())
    lock("Farm", farm)
    current = {r.farm_block: r for r in frappe.get_all(ASSIGNMENT, filters={"farm": farm, "kind": rules.BUNCH, "state": rules.OPEN,
                                                                            "farm_block": ["in", picked]}, fields=ASSIGN_FIELDS)}
    moving = [b for b in picked if b in current and current[b].work_team != team]
    text = str(reason or "").strip()[:500]
    if moving and not text:
        frappe.throw("Lô " + ", ".join(known[b]["block_code"] for b in moving) + " đang giao cho tổ khác. Ghi lý do đổi.")
    changed = 0
    for block in picked:
        held = current.get(block)
        if held and held.work_team == team:
            continue
        if held:
            if getdate(held.assigned_on) > start:
                frappe.throw(f"Lô {known[block]['block_code']} mới giao từ {held.assigned_on}; chọn ngày đổi sau ngày đó.")
            doc = frappe.get_doc(ASSIGNMENT, held.name, for_update=True)
            doc.state, doc.ended_on, doc.cancel_reason = rules.ENDED, add_days(start, -1), text
            _store(doc)
        if team:
            doc = frappe.new_doc(ASSIGNMENT)
            doc.update({"kind": rules.BUNCH, "company": farm_doc.company, "farm": farm, "crew": crew, "work_team": team,
                        "farm_block": block, "assigned_on": start, "state": rules.OPEN, "assigned_by": frappe.session.user})
            _store(doc)
        changed += 1
    return {"changed": changed}


@frappe.whitelist()
def board(farm, crew, month):
    """Lô × việc for one month: every lô of the đội, every việc given in the month, and per cell the phiếu with their state."""
    require_farm(farm)
    rights = access(farm, crew)
    if not rights.read:
        frappe.throw("Bạn không thuộc đội này.", frappe.PermissionError)
    begin = getdate(str(month)[:7] + "-01")
    end = get_last_day(begin)
    rows = frappe.get_all(ASSIGNMENT, filters={"farm": farm, "crew": crew, "kind": rules.ROUND, "assigned_on": ["<=", end],
                                               "state": ["!=", rules.CANCELLED]}, fields=ASSIGN_FIELDS, limit_page_length=0)
    rows = [r for r in rows if r.state == rules.OPEN or getdate(r.done_date or r.modified) >= begin]
    rows = _decorate(farm, _assignment_rows(rows))
    blocks = [{"name": b["name"], "block_code": b["block_code"], "area_ha": flt(b["area_ha"]), "trees": b["trees"]}
              for b in _block_map(farm).values() if b["zone"] in rights.zones]
    works = sorted({(r.work_type, r.work_name) for r in rows}, key=lambda w: w[1])
    return {"month": str(begin)[:7], "blocks": blocks, "works": [{"name": n, "work_name": label} for n, label in works],
            "cells": [{k: r.get(k) for k in ("name", "farm_block", "work_type", "work_team", "team_name", "display", "state",
                                             "assigned_on", "due_date", "done_date", "progress")} for r in rows]}


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
    if name and frappe.db.exists("Lotus Field Report Line", {"piece_rate": name}):
        frappe.throw("Giá này đã dùng trong báo cáo. Tạo giá mới với ngày áp dụng mới thay vì sửa.")
    doc = frappe.get_doc("Lotus Piece Rate", name) if name else frappe.new_doc("Lotus Piece Rate")
    doc.update({"farm": farm, "work_type": work_type, "rate": flt(rate), "valid_from": valid_from, "basis": basis,
                "uom": uom or frappe.db.get_value("Work Type", work_type, "uom"), "norm_min": flt(norm_min),
                "norm_max": flt(norm_max), "valid_to": valid_to or None, "notes": notes})
    doc.save()
    return doc.name
