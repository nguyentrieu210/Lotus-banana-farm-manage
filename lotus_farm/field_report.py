"""Đội daily report (báo cáo ngày) and lot assignment (giao lô).

Lots belong to a đội through their khu (Work Team lotus_zones). Tổ trưởng (lotus_leader of a tổ) enter and fix the
lines of their own tổ; the đội trưởng (lotus_leader of the đội) edits every line, records the weather and confirms the
day once; quản lý vườn reads everything and may reopen. Confirmed công khoán (CK) lines are the money owed to each tổ:
hr_period adds them to "Phải trả đội khoán". Công nhật (CN) lines only record workdays; wages come from attendance.
Rules that need no database live in field_report_rules.
"""
from contextvars import ContextVar

import frappe
from frappe.utils import cint, flt, getdate, now_datetime, nowdate

from lotus_farm import field_report_rules as rules
from lotus_farm.controls import farm_allowed, lock, query_condition

MANAGER, SUPERVISOR, LEADER = "Lotus Farm Manager", "Lotus Field Supervisor", "Lotus Team Leader"
CREW, TEAM = "Crew", "Team"
MAX_LINES, MAX_MATERIALS = 300, 4
_writing = ContextVar("lotus_field_report_write", default=False)
LINE_KEYS = {"line_id", "work_type", "pay_kind", "work_team", "location", "farm_block", "blocks", "zone",
             "workdays_am", "workdays_pm", "qty", "whole_lot", "under_norm_reason", "comment", "proposal", "note",
             "materials"}


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
            "works": works, "rates": rates, "my_crews": my_crews, "my_teams": my_teams, "manager": manager,
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
        row = {k: r.get(k) for k in ("line_id", "section", "work_type", "pay_kind", "work_team", "location", "farm_block",
                                      "blocks", "zone", "workdays_am", "workdays_pm", "workdays", "qty", "uom", "whole_lot",
                                      "lot_area_ha", "lot_trees", "piece_rate", "rate", "amount", "under_norm",
                                      "under_norm_reason", "bunch_tag", "comment", "proposal", "note", "entered_by")}
        row["entered_by_name"] = names.get(r.entered_by, r.entered_by)
        row["ribbon"] = tags.get(r.bunch_tag)
        row["materials"] = materials.get(r.line_id, [])
        row["editable"] = doc.state != "Confirmed" and (rights.supervisor or r.work_team in rights.teams)
        lines.append(row)
    return {"name": doc.name, "farm": doc.farm, "crew": doc.crew, "date": str(doc.posting_date), "weather": doc.weather or "",
            "state": doc.state, "return_reason": doc.return_reason or "", "confirmed_by": doc.confirmed_by,
            "confirmed_by_name": names.get(doc.confirmed_by, doc.confirmed_by), "confirmed_at": str(doc.confirmed_at or ""),
            "modified": str(doc.modified), "lines": lines, "ribbon": _ribbon_view(doc.farm, str(doc.posting_date)),
            "overdue": rules.overdue(doc.posting_date, now_datetime(), doc.state),
            "totals": _totals(doc.get("lines"))}


def _ribbon_view(farm, day):
    tag = ribbon(farm, day)
    return tag and {"label": tag.color_label or tag.display_name, "code": tag.color_code, "week": tag.week_number}


def _totals(lines):
    return {"workdays": round(sum(flt(r.get("workdays")) for r in lines), 2),
            "piece_amount": round(sum(flt(r.get("amount")) for r in lines)),
            "lines": len(lines), "under_norm": sum(1 for r in lines if r.get("under_norm"))}


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
                "totals": _totals([])}
    return {**base, **_view(frappe.get_doc("Lotus Field Report", name), rights)}


def _clean_line(raw, i, ctx, previous):
    prefix = f"Dòng {i}: "
    if not isinstance(raw, dict) or set(raw) - LINE_KEYS:
        frappe.throw(prefix + "dữ liệu có trường không được phép.")
    line_id = str(raw.get("line_id") or "")
    if not (8 <= len(line_id) <= 64) or not line_id.replace("-", "").isalnum():
        frappe.throw(prefix + "mã dòng không hợp lệ.")
    work = ctx["works"].get(raw.get("work_type"))
    if not work:
        frappe.throw(prefix + "chọn công việc trong danh mục của vườn.")
    rights = ctx["rights"]
    team = raw.get("work_team") or (next(iter(rights.teams)) if len(rights.teams) == 1 and not rights.supervisor else None)
    if team and team not in rights.members:
        frappe.throw(prefix + "tổ không thuộc đội này.")
    if not rights.supervisor and team not in rights.teams:
        frappe.throw(prefix + "tổ trưởng chỉ nhập dòng của tổ mình.", frappe.PermissionError)
    try:
        nums = rules.check_line(raw, prefix)
    except ValueError as e:
        frappe.throw(str(e))
    if raw.get("pay_kind") == rules.PIECE and not team:
        frappe.throw(prefix + "công khoán phải chọn tổ làm.")
    block = None
    blocks, zone = "", ""
    if nums["location"] == rules.BLOCK:
        block = ctx["blocks"].get(raw.get("farm_block"))
        if not block or block["zone"] not in ctx["rights"].zones:
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
    price = rules.rate_for(ctx["rates"], work.name, ctx["day"])
    if raw.get("pay_kind") == rules.PIECE and not price:
        frappe.throw(prefix + f"chưa có giá khoán cho \"{work.work_name}\" vào ngày này.")
    qty, whole = nums["qty"], bool(cint(raw.get("whole_lot")))
    area = trees = 0
    if block:
        same = previous and previous.farm_block == block["name"]
        area = flt(previous.lot_area_ha) if same else flt(block["area_ha"])
        trees = cint(previous.lot_trees) if same else cint(block["trees"])
        default = rules.whole_lot_qty(price and price.basis, area, trees)
        if default is not None and (whole or not qty):
            qty, whole = default, True
        elif default is None:
            whole = False
    rate = flt(price.rate) if price and raw.get("pay_kind") == rules.PIECE else 0
    low = rules.under_norm(qty, nums["workdays"], price and price.norm_min)
    reason = str(raw.get("under_norm_reason") or "").strip()[:500]
    if low and not reason:
        frappe.throw(prefix + "chưa đạt ngày công so với định mức, ghi lý do.")
    stage = work.lotus_bunch_stage or ""
    tag = ctx["ribbon"].name if stage == "Cut Bud" and ctx["ribbon"] else None
    return {"line_id": line_id, "section": "Bunch" if stage else "Field", "work_type": work.name,
            "pay_kind": raw.get("pay_kind"), "work_team": team, "location": nums["location"],
            "farm_block": block and block["name"], "blocks": blocks, "zone": zone,
            "workdays_am": nums["workdays_am"], "workdays_pm": nums["workdays_pm"], "workdays": nums["workdays"],
            "qty": qty, "uom": (price and price.uom) or work.uom, "whole_lot": 1 if whole else 0,
            "lot_area_ha": area, "lot_trees": trees, "piece_rate": price and price.name, "rate": rate,
            "amount": rules.amount(raw.get("pay_kind"), qty, rate), "under_norm": 1 if low else 0,
            "under_norm_reason": reason if low else "", "bunch_tag": tag,
            "basis": price and price.basis,
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
    ctx = {"rights": rights, "day": day, "rates": _rates(farm), "ribbon": ribbon(farm, day),
           "works": {w.name: w for w in _works(farm)}, "blocks": {b["name"]: b for b in
           [dict(b, zone=str(b.farm_zone or "").upper(), trees=cint(b.lotus_tree_count)) for b in _blocks(farm)]}}
    # Tổ trưởng send only their own tổ's lines; everyone else's lines stay as they are.
    kept = [] if rights.supervisor else [r for r in doc.get("lines") if r.work_team not in rights.teams]
    kept_ids = {r.line_id for r in kept}
    cleaned, materials, seen = [], [], set(kept_ids)
    for i, raw in enumerate(lines, 1):
        line_id = str((raw or {}).get("line_id") or "") if isinstance(raw, dict) else ""
        if line_id in seen:
            frappe.throw(f"Dòng {i}: mã dòng trùng hoặc thuộc tổ khác.")
        seen.add(line_id)
        row = _clean_line(raw, i, ctx, previous.get(line_id))
        cleaned.append(row)
        materials += [dict(m, line_id=line_id) for m in _clean_materials(raw.get("materials"), f"Dòng {i}: ")]
    if not cleaned and not kept and not name:
        frappe.throw("Thêm ít nhất một dòng công việc.")
    bases = {r.name: r.basis for r in ctx["rates"]}
    excess = rules.over_whole_lot([{**{k: r.get(k) for k in ("pay_kind", "work_type", "farm_block", "qty", "lot_area_ha", "lot_trees")},
                                    "basis": bases.get(r.get("piece_rate"))} for r in kept] + cleaned)
    if excess:
        work, block, total, whole = excess
        label = ctx["works"][work].work_name if work in ctx["works"] else work
        code = ctx["blocks"][block]["block_code"] if block in ctx["blocks"] else block
        frappe.throw(f"\"{label}\" ở lô {code}: tổng khối lượng trong ngày "
                     f"{total:g} vượt cả lô ({whole:g}). Nếu nhiều tổ cùng làm, ghi phần từng tổ.")
    for row in cleaned:
        row.pop("basis", None)
    doc.farm, doc.crew, doc.posting_date, doc.company = farm, crew, day, farm_doc.company
    if rights.supervisor and weather is not None:
        doc.weather = str(weather).strip()[:200]
    keep_rows = [{k: r.get(k) for k in LINE_KEYS - {"materials"} | {"section", "workdays", "uom", "lot_area_ha", "lot_trees",
                  "piece_rate", "rate", "amount", "under_norm", "bunch_tag", "entered_by"}} for r in kept]
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


def _store(doc):
    token = _writing.set(True)
    try:
        doc.save(ignore_permissions=True)
    finally:
        _writing.reset(token)


def _load(name, expected_modified):
    doc = frappe.get_doc("Lotus Field Report", name, for_update=True)
    require_farm(doc.farm)
    if str(doc.modified) != str(expected_modified or ""):
        frappe.throw("Báo cáo vừa được người khác sửa. Tải lại trước khi thao tác.", frappe.TimestampMismatchError)
    rights = access(doc.farm, doc.crew)
    if not rights.supervisor:
        frappe.throw("Chỉ đội trưởng của đội (hoặc quản lý vườn) làm việc này.", frappe.PermissionError)
    _closed(doc.company, doc.posting_date)
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
    doc.state, doc.confirmed_by, doc.confirmed_at, doc.return_reason = "Confirmed", frappe.session.user, now_datetime(), ""
    _store(doc)
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
                          fields=["parent", "line_id", "section", "work_type", "pay_kind", "work_team", "location", "farm_block",
                                  "blocks", "zone", "workdays", "qty", "uom", "rate", "amount", "under_norm", "under_norm_reason",
                                  "bunch_tag", "comment", "note"], limit_page_length=0)
    tags = {t.name: t.color_label or t.display_name for t in frappe.get_all("Bunch Tag", filters={"name": ["in", list({r.bunch_tag for r in rows if r.bunch_tag}) or [""]]},
                                                                            fields=["name", "color_label", "display_name"])}
    for r in rows:
        p = parents[r.parent]
        r.update(date=str(p.posting_date), crew=p.crew, state=p.state, ribbon=tags.get(r.bunch_tag))
    rows.sort(key=lambda r: (r["date"], r.parent), reverse=True)
    return rows


def confirmed_piece_lines(company, begin, end):
    """Confirmed công khoán lines in a period, for "Phải trả đội khoán" (hr_period)."""
    parents = frappe.get_all("Lotus Field Report", filters={"company": company, "state": "Confirmed",
                             "posting_date": ["between", [begin, end]]}, pluck="name", limit_page_length=0)
    if not parents:
        return []
    return frappe.get_all("Lotus Field Report Line", filters={"parent": ["in", parents], "parenttype": "Lotus Field Report",
                          "pay_kind": rules.PIECE}, fields=["work_team", "work_type", "uom", "rate", "qty", "workdays", "amount", "farm_block"],
                          limit_page_length=0)


@frappe.whitelist()
def payable(farm, month):
    farm_doc = require_farm(farm)
    if not is_manager() and not _visible_crews(farm):
        frappe.throw("Không có quyền xem tiền khoán.", frappe.PermissionError)
    begin = getdate(str(month)[:7] + "-01")
    from frappe.utils import get_last_day
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
