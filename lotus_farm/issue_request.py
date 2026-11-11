"""Yêu cầu cấp vật tư từ vườn đến Kho (spec 005).

A request is an ERPNext Material Request of type Material Issue: no DocType of its own. The đội trưởng of a đội (or a
quản lý vườn) enters it in Công việc or /work — one việc, one kho, one ngày cần, several lô, one line per vật tư × lô —
and approves it (chủ vườn, 11/11/2026: "đội trưởng duyệt, không cần tổ trưởng, đội trưởng nhập luôn"). Approving is the
submit of the Material Request and happens only in approve() here; the document hooks below refuse every other submit,
cancel, stop or reopen of a Material Issue request (Desk, REST, scripts). Kho then issues against it with the issue form
it already has ("Theo yêu cầu đã duyệt"); lotus_farm.warehouse_issue copies the lô and việc of each request line onto the
stock issue so the 621 cost lands on that lô and việc.

Field roles have no Material Request permission: every read and write goes through this module, which checks the farm
and the đội itself (lotus_farm.field_report.access) and writes with ignore_permissions while _writing is set.
Rules without Frappe are in lotus_farm.issue_request_rules.
"""
import json
from contextvars import ContextVar

import frappe
from frappe.utils import add_days, cint, flt, getdate, now_datetime, nowdate

from lotus_farm import issue_request_rules as rules
from lotus_farm.controls import command, command_allowed, lock

DT, ITEM_DT, TYPE = "Material Request", "Material Request Item", "Material Issue"
MANAGER = "Lotus Farm Manager"
WAREHOUSE_MANAGERS = ("Lotus Warehouse Manager", "Stock Manager")
WAREHOUSE_ROLES = ("Lotus Warehouse Operator", "Lotus Warehouse Manager", "Stock User", "Stock Manager")
STOPPED = ("Stopped", "Closed")
CLOSED_DAYS, RECENT_DAYS = 60, 7
_writing = ContextVar("lotus_issue_request_write", default=False)


# ---------------------------------------------------------------- fields

def install_fields():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    shown = "eval:doc.material_request_type=='Material Issue'"
    head = [
        dict(fieldname="lotus_crew", label="Lotus · Đội", fieldtype="Link", options="Work Team", read_only=1,
             depends_on=shown, insert_after="schedule_date"),
        dict(fieldname="lotus_work_team", label="Lotus · Tổ nhận", fieldtype="Link", options="Work Team", read_only=1,
             depends_on=shown, insert_after="lotus_crew"),
        dict(fieldname="lotus_issue_receiver", label="Lotus · Người nhận vật tư", fieldtype="Link", options="Employee",
             read_only=1, depends_on=shown, insert_after="lotus_work_team"),
        dict(fieldname="lotus_issue_approver", label="Lotus · Người duyệt dự kiến", fieldtype="Link", options="User",
             read_only=1, no_copy=1, depends_on=shown, insert_after="lotus_issue_receiver"),
        dict(fieldname="lotus_issue_sent_at", label="Lotus · Gửi duyệt lúc", fieldtype="Datetime", read_only=1, no_copy=1,
             depends_on=shown, insert_after="lotus_issue_approver"),
        dict(fieldname="lotus_issue_approved_by", label="Lotus · Người duyệt", fieldtype="Link", options="User", read_only=1,
             no_copy=1, depends_on=shown, insert_after="lotus_issue_sent_at"),
        dict(fieldname="lotus_issue_approved_at", label="Lotus · Duyệt lúc", fieldtype="Datetime", read_only=1, no_copy=1,
             depends_on=shown, insert_after="lotus_issue_approved_by"),
        dict(fieldname="lotus_issue_return_reason", label="Lotus · Lý do trả lại", fieldtype="Small Text", read_only=1,
             no_copy=1, depends_on=shown, insert_after="lotus_issue_approved_at"),
        dict(fieldname="lotus_issue_close_reason", label="Lotus · Lý do đóng", fieldtype="Small Text", read_only=1,
             no_copy=1, allow_on_submit=1, depends_on=shown, insert_after="lotus_issue_return_reason"),
    ]
    create_custom_fields({
        DT: head,
        ITEM_DT: [dict(fieldname="lotus_work_assignment", label="Lotus · Phiếu giao việc", fieldtype="Link",
                       options="Lotus Work Assignment", read_only=1, no_copy=1, insert_after="lotus_usage_area")],
    }, update=True)
    _reference_read()


# ERPNext reads the item (and its unit and warehouse) with the user's own rights while it fills a request line, so the
# people who make requests need read on them. Read only; nothing else is granted.
REQUESTERS = ("Lotus Field Supervisor", MANAGER)
REFERENCE = ("Item", "UOM", "Warehouse", "Item Group")


def _reference_read():
    from frappe.permissions import add_permission, update_permission_property
    for doctype in REFERENCE:
        for role in REQUESTERS:
            if not frappe.db.exists("Role", role):
                continue
            current = frappe.db.get_value("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0}, ["read", "select"], as_dict=True)
            if current is None:
                add_permission(doctype, role)
                current = frappe.db.get_value("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0}, ["read", "select"], as_dict=True) or {}
            for operation in ("read", "select"):
                if not int(current.get(operation) or 0):
                    update_permission_property(doctype, role, 0, operation, 1)


# ---------------------------------------------------------------- document hooks (Material Request, Stock Entry)

def _ours(doc):
    return doc.get("material_request_type") == TYPE


def _lines_key(doc):
    return sorted((str(r.get("item_code") or ""), str(r.get("lotus_farm_block") or ""), round(flt(r.get("qty")), 6),
                   str(r.get("warehouse") or "")) for r in (doc.get("items") or []))


def validate(doc, method=None):
    """A request made in Lotus (it has a đội) is written only through this module; while it waits for approval its lines
    change only in the approval itself (lowering)."""
    if not _ours(doc):
        return
    before = None if doc.is_new() else doc.get_doc_before_save()
    lotus = bool(doc.get("lotus_crew") or (before and before.get("lotus_crew")))
    if lotus and not _writing.get():
        frappe.throw("Yêu cầu cấp vật tư chỉ sửa trong màn Công việc của Lotus.", frappe.PermissionError)
    if before and before.get("lotus_issue_sent_at") and _lines_key(before) != _lines_key(doc) \
            and not command_allowed(doc, "issue-approve"):
        frappe.throw("Yêu cầu đang chờ duyệt: không sửa dòng. Rút lại hoặc trả lại trước.")
    if lotus:
        problems = rules.line_issues([dict(item_code=r.get("item_code"), farm_block=r.get("lotus_farm_block"), qty=r.get("qty"),
                                           work_type=r.get("lotus_work_type")) for r in doc.get("items") or []])
        if problems:
            frappe.throw("<br>".join(problems))


def _approver_allowed(doc, user):
    if not user:
        return False
    if user == "Administrator" or MANAGER in frappe.get_roles(user):
        return True
    crew = doc.get("lotus_crew")
    return bool(crew) and frappe.db.get_value("Work Team", crew, "lotus_leader") == user


def before_submit(doc, method=None):
    if not _ours(doc):
        return
    if not (getattr(doc.flags, "lotus_issue_approval", False) and command_allowed(doc, "issue-approve")):
        frappe.throw("Yêu cầu cấp vật tư chỉ được duyệt trong Lotus (Công việc › Yêu cầu cấp vật tư).", frappe.PermissionError)
    if not _approver_allowed(doc, doc.get("lotus_issue_approved_by")):
        frappe.throw("Chỉ đội trưởng của đội hoặc quản lý vườn duyệt yêu cầu cấp vật tư.", frappe.PermissionError)


def before_cancel(doc, method=None):
    if _ours(doc) and not command_allowed(doc, "issue-cancel"):
        frappe.throw("Hủy yêu cầu cấp vật tư trong Lotus, có lý do.", frappe.PermissionError)


def before_update_after_submit(doc, method=None):
    if _ours(doc) and doc.get("lotus_crew") and not _writing.get():
        frappe.throw("Yêu cầu cấp vật tư đã duyệt không sửa được.", frappe.PermissionError)


def on_trash(doc, method=None):
    if _ours(doc) and doc.get("lotus_crew") and not _writing.get():
        frappe.throw("Xóa yêu cầu nháp trong màn Công việc của Lotus.", frappe.PermissionError)


def on_change(doc, method=None):
    """Stop (Đã đóng) and reopen only through close()/reopen(). ERPNext's own status changes when Kho posts or cancels an
    issue (Pending, Partially Ordered, Issued) pass."""
    if not _ours(doc):
        return
    before = doc.get_doc_before_save()
    old, new = (before.get("status") if before else None), doc.get("status")
    if old == new:
        return
    if new in STOPPED and not command_allowed(doc, "issue-close"):
        frappe.throw("Đóng yêu cầu cấp vật tư trong Lotus, có lý do.", frappe.PermissionError)
    if old in STOPPED and new not in (*STOPPED, "Cancelled") and not command_allowed(doc, "issue-reopen"):
        frappe.throw("Mở lại yêu cầu cấp vật tư trong Lotus, có lý do.", frappe.PermissionError)


def issue_posted(doc, method=None):
    """Stock Entry on_submit / on_cancel: tell the requester and the approver what Kho issued. Never blocks the posting."""
    if doc.get("stock_entry_type") != "Material Issue":
        return
    names = sorted({r.get("material_request") for r in doc.get("items") or [] if r.get("material_request")})
    if not names:
        return
    cancelled = method == "on_cancel" or doc.docstatus == 2
    for name in names:
        head = frappe.db.get_value(DT, name, ["name", "owner", "lotus_crew", "lotus_issue_approved_by", "title",
                                              "material_request_type"], as_dict=True)
        if not head or head.material_request_type != TYPE or not head.lotus_crew:
            continue
        title = ("Kho hủy phiếu xuất " if cancelled else "Kho đã cấp vật tư · ") + doc.name
        _notify([head.owner, head.lotus_issue_approved_by], title, head.title or name, name,
                key=f"issued:{doc.name}:{'cancel' if cancelled else 'post'}")


# ---------------------------------------------------------------- notifications

def _notify(users, title, body, name, key, app="work", url=None):
    """In-app alert and push. A failure to notify never undoes the action (same as signing._notify)."""
    users = sorted({u for u in users if u and u not in ("Guest",)})
    if not users:
        return
    frappe.db.savepoint("lotus_issue_notify")
    try:
        from lotus_farm.push_notifications import _add_alert
        link = url or ("/work?request=" + name if app == "work" else "/warehouse?issue_request=" + name)
        for user in users:
            if not frappe.db.get_value("User", user, "enabled"):
                continue
            alert = _add_alert(user, app, title, body or name, link, DT, name, key=f"issue:{name}:{key}:{user}")
            if alert:
                frappe.enqueue("lotus_farm.push_notifications._send_alert", queue="short", enqueue_after_commit=True,
                               alert_name=alert)
    except Exception:
        frappe.db.rollback(save_point="lotus_issue_notify")
        frappe.log_error(frappe.get_traceback(), "Lotus: thông báo yêu cầu cấp vật tư")


def _farm_managers(farm):
    users = frappe.get_all("Has Role", filters={"role": MANAGER, "parenttype": "User"}, pluck="parent", limit_page_length=0)
    granted = set(frappe.get_all("User Permission", filters={"allow": "Farm", "for_value": farm}, pluck="user", limit_page_length=0))
    return [u for u in set(users) if u in granted]


def _warehouse_users(warehouse, managers_only=False):
    roles = WAREHOUSE_MANAGERS if managers_only else WAREHOUSE_ROLES
    users = set(frappe.get_all("Has Role", filters={"role": ["in", list(roles)], "parenttype": "User"}, pluck="parent",
                               limit_page_length=0))
    found = []
    for user in sorted(users):
        if user in ("Administrator", "Guest") or not frappe.db.get_value("User", user, "enabled"):
            continue
        try:
            if frappe.has_permission("Stock Entry", "create", user=user) and \
                    frappe.has_permission("Warehouse", "read", doc=warehouse, user=user):
                found.append(user)
        except Exception:
            continue
    return found


# ---------------------------------------------------------------- scope

def _field():
    from lotus_farm import field_report
    return field_report


def _crew_farm(crew):
    farm = frappe.db.get_value("Work Team", crew, "farm") if crew else None
    if not farm:
        frappe.throw("Yêu cầu không thuộc đội nào của vườn.")
    return farm


def _read_rights(doc):
    field = _field()
    farm = _crew_farm(doc.get("lotus_crew"))
    field.require_farm(farm)
    rights = field.access(farm, doc.lotus_crew)
    if not (rights.supervisor or rights.inspector or rights.manager or (doc.get("lotus_work_team") in rights.teams)):
        frappe.throw("Bạn không xem được yêu cầu này.", frappe.PermissionError)
    return farm, rights


def _get(name):
    doc = frappe.get_doc(DT, name)
    if doc.material_request_type != TYPE or not doc.get("lotus_crew"):
        frappe.throw("Không phải yêu cầu cấp vật tư lập trong Lotus.")
    return doc


def _load(name, modified):
    """The request locked for a write, refused when the screen shows an older version."""
    lock(DT, name)
    doc = _get(name)
    if not modified or str(doc.modified) != str(modified):
        frappe.throw("Yêu cầu vừa thay đổi. Mở lại.", frappe.TimestampMismatchError)
    return doc


def _warehouse_manager(warehouse, user=None):
    user = user or frappe.session.user
    if not set(WAREHOUSE_MANAGERS) & set(frappe.get_roles(user)):
        return False
    try:
        return bool(frappe.has_permission("Warehouse", "read", doc=warehouse, user=user))
    except Exception:
        return False


def _store(doc):
    token = _writing.set(True)
    doc.flags.ignore_permissions = True
    try:
        if doc.is_new():
            doc.insert()
        else:
            doc.save()
    finally:
        _writing.reset(token)
    return doc


def _note(doc, text):
    doc.add_comment("Comment", text[:1000])


def _reason(text, label):
    text = str(text or "").strip()
    if not text:
        frappe.throw(f"Ghi lý do {label}.")
    return text[:500]


def _run(client_event_id, action, name, payload, operation):
    from lotus_farm.erp_workbench import _command
    return _command(client_event_id, dict(doctype=DT, action="issue-" + action, name=name, **payload), operation)


# ---------------------------------------------------------------- reference data

def _codes(blocks):
    blocks = [b for b in set(blocks) if b]
    return {b.name: b.block_code for b in frappe.get_all("Farm Block", filters={"name": ["in", blocks or [""]]},
                                                        fields=["name", "block_code"], limit_page_length=0)}


def _whole(uoms):
    uoms = [u for u in set(uoms) if u]
    return set(frappe.get_all("UOM", filters={"name": ["in", uoms or [""]], "must_be_whole_number": 1}, pluck="name"))


def _zone_blocks(farm, rights):
    return {n: b for n, b in _field()._block_map(farm).items() if b["zone"] in rights.zones}


def _employee_of(user, company):
    return frappe.db.get_value("Employee", {"user_id": user, "company": company, "status": "Active"}, "name")


@frappe.whitelist()
def form_data(farm, crew):
    """What the form needs for one đội: tổ, lô of its khu, việc, kho, người nhận, who approves, and (US4) the phiếu giao
    still open, the lô due by the vòng chăm sóc and the last approved request per việc."""
    field = _field()
    farm_doc = field.require_farm(farm)
    rights = field.access(farm, crew)
    if not rights.supervisor:
        frappe.throw("Chỉ đội trưởng của đội hoặc quản lý vườn lập yêu cầu cấp vật tư.", frappe.PermissionError)
    teams = {t.name: t for t in field._teams(farm)}
    blocks = _zone_blocks(farm, rights)
    works = sorted(field._works(farm), key=lambda w: (0 if cint(w.lotus_requires_material) else 1, w.work_code or ""))
    warehouses = frappe.get_all("Warehouse", filters={"company": farm_doc.company, "is_group": 0, "disabled": 0},
                                fields=["name", "warehouse_name"], order_by="warehouse_name asc", limit_page_length=0)
    mapped = frappe.get_all("Warehouse Mapping", filters={"farm": farm, "enabled": 1, "warehouse_role": ["in", ["Input", "Field Store"]]},
                            pluck="warehouse", limit_page_length=0)
    known = {w.name for w in warehouses}
    suggested = next((w for w in mapped if w in known), None)
    members = sorted(rights.members, key=lambda n: teams[n].team_name)
    people = frappe.get_all("Employee", filters={"company": farm_doc.company, "status": "Active",
                                                 "lotus_work_team": ["in", members + [crew]]},
                            fields=["name", "employee_name", "lotus_work_team"], order_by="employee_name asc", limit_page_length=0)
    mine = _employee_of(frappe.session.user, farm_doc.company)
    if mine and mine not in {p.name for p in people}:
        people.insert(0, frappe.db.get_value("Employee", mine, ["name", "employee_name", "lotus_work_team"], as_dict=True))
    leader = rights.crew.lotus_leader
    names = field._user_names([leader])
    open_tickets = frappe.get_all(field.ASSIGNMENT, filters={"farm": farm, "crew": crew, "kind": field.rules.ROUND,
                                                             "state": ["in", list(field.OPEN_STATES)]},
                                  fields=["name", "farm_block", "work_type", "work_team", "assigned_on", "due_date"],
                                  order_by="assigned_on desc", limit_page_length=0)
    for t in open_tickets:
        t["block_code"] = blocks.get(t.farm_block, {}).get("block_code") or t.farm_block
        t["team_name"] = teams[t.work_team].team_name if t.work_team in teams else t.work_team
    try:
        from lotus_farm import care_cycle
        due = [dict(farm_block=r["farm_block"], block_code=r["code"], work_type=r["work_type"], due_date=str(r["due_date"]),
                    status=r["status"]) for r in care_cycle.due(farm, crew)["rows"] if r["status"] != "later"]
    except (frappe.ValidationError, frappe.PermissionError):
        frappe.clear_messages()
        due = []
    return {
        "farm": farm, "crew": crew, "crew_name": rights.crew.team_name, "company": farm_doc.company, "today": nowdate(),
        "teams": [{"name": n, "team_name": teams[n].team_name} for n in members],
        "blocks": [dict(name=n, block_code=b["block_code"], zone=b["zone"], area_ha=flt(b["area_ha"]), trees=b["trees"],
                        quarantine_until=b["quarantine_until"]) for n, b in blocks.items()],
        "works": [dict(name=w.name, work_name=w.work_name, work_code=w.work_code, requires_material=cint(w.lotus_requires_material))
                  for w in works],
        "warehouses": warehouses, "warehouse": suggested,
        "receivers": [dict(name=p.name, employee_name=p.employee_name, team=p.lotus_work_team) for p in people if p],
        "receiver": mine,
        "approver": leader or None,
        "approver_label": ("Đội trưởng " + names.get(leader, leader)) if leader else "Quản lý vườn",
        "can_approve": rules.may_approve(frappe.session.user, leader, rights.manager),
        "open_assignments": open_tickets, "due_blocks": due, "last": _last_requests(crew, blocks),
    }


def _last_requests(crew, blocks):
    """The last approved request of the đội per việc, with the dose per ha of each vật tư (source named on the screen)."""
    heads = frappe.get_all(DT, filters={"material_request_type": TYPE, "lotus_crew": crew, "docstatus": 1},
                           fields=["name", "lotus_issue_approved_at", "transaction_date"], order_by="lotus_issue_approved_at desc",
                           limit_page_length=40)
    if not heads:
        return []
    lines = frappe.get_all(ITEM_DT, filters={"parent": ["in", [h.name for h in heads]]},
                           fields=["parent", "item_code", "item_name", "stock_uom", "qty", "lotus_farm_block", "lotus_work_type",
                                   "lotus_notes"], limit_page_length=0)
    areas = {n: flt(b["area_ha"]) for n, b in blocks.items()}
    if any(l.lotus_farm_block not in areas for l in lines):
        areas.update({b.name: flt(b.area_ha) for b in frappe.get_all("Farm Block", filters={"name": ["in", list({l.lotus_farm_block for l in lines if l.lotus_farm_block}) or [""]]},
                                                                      fields=["name", "area_ha"], limit_page_length=0)})
    result = {}
    for head in heads:
        own = [l for l in lines if l.parent == head.name]
        work = next((l.lotus_work_type for l in own if l.lotus_work_type), None)
        if not work or work in result:
            continue
        per_item = {}
        for l in own:
            g = per_item.setdefault(l.item_code, dict(item_code=l.item_code, item_name=l.item_name, uom=l.stock_uom, qty=0.0, area=0.0,
                                                      blocks=0, notes=l.lotus_notes or ""))
            g["qty"] += flt(l.qty)
            g["blocks"] += 1
            g["area"] += areas.get(l.lotus_farm_block, 0)
        items = []
        for g in per_item.values():
            g["per_block"] = round(g["qty"] / g["blocks"], 3) if g["blocks"] else None
            g["per_ha"] = round(g["qty"] / g["area"], 3) if g["area"] else None
            items.append(g)
        result[work] = dict(work_type=work, request=head.name,
                            date=str(head.lotus_issue_approved_at or head.transaction_date or "")[:10], items=items)
    return list(result.values())


@frappe.whitelist()
def item_options(search=None):
    """Vật tư that can be requested: active, kept in stock, not managed by batch or serial; with their packing unit."""
    if frappe.session.user == "Guest":
        frappe.throw("Vui lòng đăng nhập.", frappe.AuthenticationError)
    filters = {"disabled": 0, "is_stock_item": 1, "has_batch_no": 0, "has_serial_no": 0}
    text = str(search or "").strip()[:80]
    or_filters = {"item_code": ["like", f"%{text}%"], "item_name": ["like", f"%{text}%"]} if text else None
    rows = frappe.get_all("Item", filters=filters, or_filters=or_filters, fields=["name", "item_name", "stock_uom", "lotus_phi_days"],
                          order_by="item_name asc", limit=30, ignore_permissions=True)
    packs = {}
    for r in frappe.get_all("UOM Conversion Detail", filters={"parent": ["in", [r.name for r in rows] or [""]], "parenttype": "Item"},
                            fields=["parent", "uom", "conversion_factor"], ignore_permissions=True, limit_page_length=0):
        packs.setdefault(r.parent, []).append(r)
    whole = _whole([r.stock_uom for r in rows])
    for r in rows:
        pack = next((p for p in packs.get(r.name, []) if p.uom != r.stock_uom and flt(p.conversion_factor) > 0), None)
        r.update(pack_uom=pack.uom if pack else "", pack_factor=flt(pack.conversion_factor) if pack else 0,
                 whole=1 if r.stock_uom in whole else 0)
    return rows


def _availability(items, warehouse, exclude=None):
    """Per vật tư at one kho: what can be issued now (Bin less reservations and draft issues, as check_outbound_stock
    reads it) and what other approved requests still wait for. Quantities only, never money."""
    items = [i for i in dict.fromkeys(items) if i]
    if not items or not warehouse:
        return {}
    bins = {b.item_code: b for b in frappe.get_all("Bin", filters={"warehouse": warehouse, "item_code": ["in", items]},
                                                 fields=["item_code", "actual_qty", "reserved_stock"], limit_page_length=0)}
    held = dict(frappe.db.sql("""select d.item_code, coalesce(sum(d.qty * d.conversion_factor), 0) from `tabStock Entry Detail` d
        join `tabStock Entry` p on p.name = d.parent where p.docstatus = 0 and d.s_warehouse = %(w)s and d.item_code in %(items)s
        group by d.item_code""", dict(w=warehouse, items=tuple(items))))
    waiting = dict(frappe.db.sql("""select i.item_code, coalesce(sum(greatest(i.stock_qty - i.ordered_qty, 0)), 0)
        from `tabMaterial Request Item` i join `tabMaterial Request` m on m.name = i.parent
        where m.docstatus = 1 and m.material_request_type = 'Material Issue' and m.status not in ('Stopped', 'Closed', 'Issued')
        and i.warehouse = %(w)s and i.item_code in %(items)s and m.name != %(exclude)s group by i.item_code""",
                                 dict(w=warehouse, items=tuple(items), exclude=exclude or "")))
    uoms = dict(frappe.get_all("Item", filters={"name": ["in", items]}, fields=["name", "stock_uom"], as_list=True))
    result = {}
    for item in items:
        b = bins.get(item)
        actual = flt(b.actual_qty) if b else 0
        reserved = flt(b.reserved_stock) if b else 0
        result[item] = dict(item_code=item, uom=uoms.get(item), available=round(actual - reserved - flt(held.get(item)), 6),
                            approved_waiting=round(flt(waiting.get(item)), 6))
    return result


@frappe.whitelist()
def stock(farm, items, warehouse):
    _field().require_farm(farm)
    items = frappe.parse_json(items) if isinstance(items, str) and items.strip().startswith("[") else items
    if isinstance(items, str):
        items = items.split(",")
    company = frappe.db.get_value("Farm", farm, "company")
    if frappe.db.get_value("Warehouse", warehouse, "company") != company:
        frappe.throw("Kho không thuộc công ty của vườn.")
    return _availability([str(i).strip() for i in (items or [])][:100], warehouse)


# ---------------------------------------------------------------- reading requests

def _progress(names):
    """Every line of these requests with what is issued and held, in one query."""
    if not names:
        return {}
    rows = frappe.db.sql("""select i.parent, i.name, i.idx, i.item_code, i.item_name, i.stock_uom, i.stock_qty, i.qty,
            i.lotus_farm_block, i.lotus_usage_area, i.lotus_work_type, i.lotus_notes, i.lotus_work_assignment,
            coalesce(sum(case when p.docstatus = 1 then d.qty * d.conversion_factor end), 0) as posted,
            coalesce(sum(case when p.docstatus = 0 then d.qty * d.conversion_factor end), 0) as draft
        from `tabMaterial Request Item` i
        left join `tabStock Entry Detail` d on d.material_request = i.parent and d.material_request_item = i.name
        left join `tabStock Entry` p on p.name = d.parent and p.docstatus < 2 and p.stock_entry_type = 'Material Issue'
        where i.parent in %(names)s group by i.name order by i.parent, i.idx""", dict(names=tuple(names)), as_dict=True)
    result = {}
    for r in rows:
        r.update(rules.progress(r.stock_qty, r.posted, r.draft))
        result.setdefault(r.parent, []).append(r)
    return result


def _totals(lines):
    return dict(required=sum(flt(l.stock_qty) for l in lines), posted=sum(flt(l.posted) for l in lines),
                draft=sum(flt(l.draft) for l in lines))


HEAD_FIELDS = ["name", "title", "owner", "docstatus", "status", "transaction_date", "schedule_date", "set_warehouse", "company",
               "lotus_crew", "lotus_work_team", "lotus_issue_receiver", "lotus_issue_approver", "lotus_issue_sent_at",
               "lotus_issue_approved_by", "lotus_issue_approved_at", "lotus_issue_return_reason", "lotus_issue_close_reason",
               "lotus_request_note", "modified", "creation"]


def _card(head, lines, teams, works, codes, people, today, user, crew_leaders, manager):
    totals = _totals(lines)
    current = rules.state(head.docstatus, head.status, head.lotus_issue_sent_at, head.lotus_issue_return_reason, totals)
    work = next((l.lotus_work_type for l in lines if l.lotus_work_type), None)
    leader = crew_leaders.get(head.lotus_crew)
    return dict(
        name=head.name, title=head.title or head.name, state=current, state_code=rules.CODES[current],
        overdue=rules.overdue(current, head.schedule_date, today), docstatus=head.docstatus, status=head.status,
        crew=head.lotus_crew, crew_name=teams.get(head.lotus_crew, head.lotus_crew),
        team=head.lotus_work_team, team_name=teams.get(head.lotus_work_team, "") if head.lotus_work_team else "",
        work_type=work, work_name=works.get(work, work or ""),
        blocks=list(dict.fromkeys(codes.get(l.lotus_farm_block, l.lotus_farm_block) for l in lines if l.lotus_farm_block)),
        needed=str(head.schedule_date or ""), date=str(head.transaction_date or ""), warehouse=head.set_warehouse,
        lines=len(lines), open_lines=sum(1 for l in lines if l.remaining > 0), totals=totals,
        owner=head.owner, owner_name=people.get(head.owner, head.owner),
        approver=head.lotus_issue_approver or leader, approver_name=people.get(head.lotus_issue_approver or leader, "Quản lý vườn")
        if (head.lotus_issue_approver or leader) else "Quản lý vườn",
        approved_by=head.lotus_issue_approved_by, approved_by_name=people.get(head.lotus_issue_approved_by, head.lotus_issue_approved_by or ""),
        approved_at=str(head.lotus_issue_approved_at or "") or None, sent_at=str(head.lotus_issue_sent_at or "") or None,
        note=head.lotus_request_note or "", modified=str(head.modified),
        can_approve=current == rules.SENT and rules.may_approve(user, leader, manager),
    )


@frappe.whitelist()
def requests(farm, crew=None, team=None, view="open", assignment=None, from_date=None, to_date=None, search=None):
    """Cards of the requests this user sees, and counts by state. view: open (not finished, plus finished in the last 7
    days), approve (waiting for this user), mine, all (also finished ones since from_date, 60 days back by default).
    from_date/to_date filter the ngày cần."""
    field = _field()
    field.require_farm(farm)
    user = frappe.session.user
    crews = field._visible_crews(farm)
    if crew:
        crews &= {crew}
    if not crews:
        return dict(rows=[], counts={})
    allowed, leaders, manager = {}, {}, field.is_manager()
    for c in crews:
        rights = field.access(farm, c)
        allowed[c] = None if (rights.supervisor or rights.inspector or rights.manager) else rights.teams
        leaders[c] = rights.crew.lotus_leader
    base = {"material_request_type": TYPE, "lotus_crew": ["in", list(crews)], "docstatus": ["<", 2]}
    if team:
        base["lotus_work_team"] = team
    if view == "mine":
        base["owner"] = user
    open_rows = frappe.get_all(DT, filters=dict(base, status=["not in", ["Stopped", "Closed", "Issued"]]), fields=HEAD_FIELDS,
                               limit_page_length=0)
    since = getdate(from_date) if (view == "all" and from_date) else getdate(add_days(nowdate(), -(CLOSED_DAYS if view == "all" else RECENT_DAYS)))
    done_filters = dict(base, status=["in", ["Stopped", "Closed", "Issued"]], modified=[">=", str(since)])
    if view == "all":
        done_filters.pop("docstatus")
        done_filters.pop("status")
        done_filters["modified"] = [">=", str(since)]
    finished = frappe.get_all(DT, filters=done_filters, fields=HEAD_FIELDS, limit_page_length=0)
    heads = {h.name: h for h in open_rows + finished}
    heads = {n: h for n, h in heads.items() if allowed.get(h.lotus_crew) is None or h.lotus_work_team in allowed[h.lotus_crew]}
    if view == "all" and from_date:
        heads = {n: h for n, h in heads.items() if h.schedule_date and getdate(h.schedule_date) >= getdate(from_date)
                 or h.name in {r.name for r in open_rows}}
    if to_date:
        heads = {n: h for n, h in heads.items() if not h.schedule_date or getdate(h.schedule_date) <= getdate(to_date)}
    lines = _progress(list(heads))
    if assignment:
        heads = {n: h for n, h in heads.items() if any(l.lotus_work_assignment == assignment for l in lines.get(n, []))}
    teams = {t.name: t.team_name for t in field._teams(farm)}
    works = {w.name: w.work_name for w in frappe.get_all("Work Type", fields=["name", "work_name"], limit_page_length=0)}
    codes = _codes([l.lotus_farm_block for ls in lines.values() for l in ls])
    people = field._user_names([u for h in heads.values() for u in (h.owner, h.lotus_issue_approver, h.lotus_issue_approved_by)]
                               + list(leaders.values()))
    today = nowdate()
    cards = [_card(h, lines.get(n, []), teams, works, codes, people, today, user, leaders, manager) for n, h in heads.items()]
    text = str(search or "").strip().lower()
    if text:
        cards = [c for c in cards if text in " ".join([c["name"], c["title"], c["work_name"], c["team_name"], " ".join(c["blocks"]),
                                                       c["owner_name"], c["note"]]).lower()]
    counts = {code: 0 for code in rules.CODES.values()}
    for c in cards:
        counts[c["state_code"]] += 1
    counts["approve"] = sum(1 for c in cards if c["can_approve"])
    counts["overdue"] = sum(1 for c in cards if c["overdue"])
    if view == "approve":
        cards = [c for c in cards if c["can_approve"]]
    order = {s: i for i, s in enumerate((rules.SENT, rules.RETURNED, rules.DRAFT, rules.WAITING, rules.PICKING, rules.PARTIAL,
                                         rules.DONE, rules.CLOSED, rules.CANCELLED))}
    cards.sort(key=lambda c: (order[c["state"]], c["needed"] or "9999", c["name"]))
    return dict(rows=cards, counts=counts)


def _issues(name):
    rows = frappe.db.sql("""select p.name, p.posting_date, p.docstatus, p.lotus_receiver, p.owner,
            sum(d.qty * d.conversion_factor) as qty, count(d.name) as `lines`
        from `tabStock Entry` p join `tabStock Entry Detail` d on d.parent = p.name
        where d.material_request = %s and p.docstatus < 2 and p.stock_entry_type = 'Material Issue'
        group by p.name order by p.posting_date, p.name""", (name,), as_dict=True)
    lines = frappe.db.sql("""select p.name as stock_entry, d.material_request_item, d.qty * d.conversion_factor as qty, p.docstatus
        from `tabStock Entry` p join `tabStock Entry Detail` d on d.parent = p.name
        where d.material_request = %s and p.docstatus < 2 and p.stock_entry_type = 'Material Issue'""", (name,), as_dict=True)
    return [dict(r, posting_date=str(r.posting_date), qty=flt(r.qty), draft=r.docstatus == 0) for r in rows], lines


def _history(name):
    return [dict(at=str(c.creation), by=c.owner, text=c.content) for c in
            frappe.get_all("Comment", filters={"reference_doctype": DT, "reference_name": name, "comment_type": ["in", ["Comment", "Label"]]},
                           fields=["creation", "owner", "content"], order_by="creation asc", limit_page_length=200)]


def _warnings(doc, farm, lines=None):
    """Things the requester and the approver should know; none of them blocks (FR-007)."""
    lines = lines if lines is not None else doc.items
    found = []
    blocks = list({l.lotus_farm_block for l in lines if l.lotus_farm_block})
    items = list({l.item_code for l in lines})
    if blocks and items:
        others = frappe.db.sql("""select m.name as request, i.item_code, i.lotus_farm_block as farm_block from `tabMaterial Request Item` i
            join `tabMaterial Request` m on m.name = i.parent where m.material_request_type = 'Material Issue' and m.name != %(name)s
            and m.docstatus < 2 and m.status not in ('Stopped', 'Closed', 'Issued') and i.lotus_farm_block in %(blocks)s
            and i.item_code in %(items)s""", dict(name=doc.name or "", blocks=tuple(blocks), items=tuple(items)), as_dict=True)
        mine = [dict(item_code=l.item_code, farm_block=l.lotus_farm_block) for l in lines]
        codes = _codes(blocks)
        for o in rules.duplicates(mine, others):
            found.append(dict(kind="duplicate", request=o["request"], item_code=o["item_code"], farm_block=o["farm_block"],
                              message=f"{o['item_code']} ở lô {codes.get(o['farm_block'], o['farm_block'])} đã có trong yêu cầu {o['request']} còn mở."))
        today = getdate(nowdate())
        for b in frappe.get_all("Farm Block", filters={"name": ["in", blocks]}, fields=["name", "block_code", "lotus_quarantine_until"]):
            if b.lotus_quarantine_until and getdate(b.lotus_quarantine_until) >= today:
                found.append(dict(kind="quarantine", farm_block=b.name, until=str(b.lotus_quarantine_until),
                                  message=f"Lô {b.block_code} đang cách ly đến {getdate(b.lotus_quarantine_until).strftime('%d/%m')}."))
    if doc.docstatus == 0 and doc.get("set_warehouse"):
        need = {}
        for l in lines:
            need[l.item_code] = need.get(l.item_code, 0) + flt(l.get("stock_qty") or l.qty)
        for item, info in _availability(list(need), doc.set_warehouse, exclude=doc.name).items():
            if need[item] > info["available"] + rules.EPSILON:
                found.append(dict(kind="stock", item_code=item, available=info["available"], needed=need[item],
                                  message=f"Kho còn {info['available']:g} {info['uom'] or ''} {item}, yêu cầu {need[item]:g}."))
    return found


@frappe.whitelist()
def detail(name):
    """One request: head, every line with its progress, the stock issues, stock at the kho, history, warnings and what this
    user may do."""
    doc = _get(name)
    farm, rights = _read_rights(doc)
    field = _field()
    user = frappe.session.user
    lines = _progress([doc.name]).get(doc.name, [])
    leader = rights.crew.lotus_leader
    teams = {t.name: t.team_name for t in field._teams(farm)}
    work = next((l.lotus_work_type for l in lines if l.lotus_work_type), None)
    works = {w.name: w.work_name for w in frappe.get_all("Work Type", filters={"name": ["in", [work or ""]]}, fields=["name", "work_name"])}
    codes = _codes([l.lotus_farm_block for l in lines])
    people = field._user_names([doc.owner, doc.get("lotus_issue_approver"), doc.get("lotus_issue_approved_by"), leader])
    card = _card(frappe._dict({f: doc.get(f) for f in HEAD_FIELDS}), lines, teams, works, codes, people, nowdate(), user,
                 {doc.lotus_crew: leader}, rights.manager)
    issues, issue_lines = _issues(doc.name)
    by_line = {}
    for r in issue_lines:
        by_line.setdefault(r.material_request_item, []).append(dict(stock_entry=r.stock_entry, qty=flt(r.qty), draft=r.docstatus == 0))
    whole = _whole([l.stock_uom for l in lines])
    out_lines = [dict(name=l.name, idx=l.idx, item_code=l.item_code, item_name=l.item_name, uom=l.stock_uom, whole=1 if l.stock_uom in whole else 0,
                      farm_block=l.lotus_farm_block, block_code=codes.get(l.lotus_farm_block, l.lotus_farm_block), qty=flt(l.stock_qty),
                      notes=l.lotus_notes or "", assignment=l.lotus_work_assignment, required=l.required, posted=l.posted,
                      draft=l.draft, remaining=l.remaining, issues=by_line.get(l.name, [])) for l in lines]
    can_approve = rules.may_approve(user, leader, rights.manager)
    may_print = bool(frappe.has_permission(DT, "print"))
    current = card["state"]
    actions = rules.actions(current, user, doc.owner, can_approve=can_approve, is_manager=rights.manager,
                            warehouse_manager=_warehouse_manager(doc.set_warehouse) if doc.set_warehouse else False,
                            approved_by=doc.get("lotus_issue_approved_by"), has_issues=bool(issues),
                            has_drafts=any(i["draft"] for i in issues), can_request=rights.supervisor, can_print=may_print)
    receiver = doc.get("lotus_issue_receiver")
    return dict(card, doc=dict(name=doc.name, modified=str(doc.modified), docstatus=doc.docstatus, status=doc.status),
                farm=farm, company=doc.company, receiver=receiver,
                receiver_name=frappe.db.get_value("Employee", receiver, "employee_name") if receiver else "",
                return_reason=doc.get("lotus_issue_return_reason") or "", close_reason=doc.get("lotus_issue_close_reason") or "",
                items=out_lines, issues=issues,
                stock=_availability([l.item_code for l in lines], doc.set_warehouse, exclude=doc.name) if current in (
                    rules.DRAFT, rules.SENT, rules.RETURNED, rules.WAITING, rules.PICKING, rules.PARTIAL) else {},
                history=_history(doc.name), warnings=_warnings(doc, farm) if doc.docstatus == 0 else [],
                actions=actions, print_url=("/lotus/in-de-xuat?name=" + doc.name) if may_print else None,
                timeline=dict(created=str(doc.creation), sent=card["sent_at"], approved=card["approved_at"],
                              returned=bool(doc.get("lotus_issue_return_reason")),
                              first_issue=next((i["posting_date"] for i in issues if not i["draft"]), None),
                              closed=doc.status in STOPPED))


# ---------------------------------------------------------------- writing

def _values(values):
    values = frappe.parse_json(values) if isinstance(values, str) else (values or {})
    if not isinstance(values, dict):
        frappe.throw("Nội dung yêu cầu không hợp lệ.")
    return values


def _fill(doc, farm_doc, rights, values):
    """Head and lines from what the screen sent, every value checked and the lô/việc columns filled by the server."""
    field = _field()
    farm = farm_doc.name
    team = values.get("team") or None
    problem = rules.may_request(team, rights.members, rights.supervisor)
    if problem:
        frappe.throw(problem, frappe.PermissionError)
    works = {w.name: w for w in field._works(farm)}
    work = works.get(values.get("work_type"))
    if not work:
        frappe.throw("Chọn việc trong danh mục của vườn.")
    if not values.get("needed"):
        frappe.throw("Chọn ngày cần.")
    needed = getdate(values.get("needed"))
    warehouse = values.get("warehouse")
    w = frappe.db.get_value("Warehouse", warehouse, ["company", "is_group", "disabled"], as_dict=True) if warehouse else None
    if not w or w.company != farm_doc.company or w.is_group or w.disabled:
        frappe.throw("Kho cấp phải là kho đang hoạt động (không phải nhóm) của công ty.")
    receiver = values.get("receiver") or None
    if receiver:
        from lotus_farm.warehouse_masters import employee_contact
        employee_contact(farm_doc.company, receiver)
    blocks = _zone_blocks(farm, rights)
    raw = values.get("lines") or []
    if not isinstance(raw, list):
        frappe.throw("Dòng vật tư không hợp lệ.")
    lines = [dict(item_code=str(l.get("item_code") or "").strip(), farm_block=l.get("farm_block"), qty=l.get("qty"),
                  block_code=blocks.get(l.get("farm_block"), {}).get("block_code"), work_type=work.name) for l in raw if isinstance(l, dict)]
    problems = rules.line_issues(lines, set(blocks), nowdate(), needed)
    if problems:
        frappe.throw("<br>".join(problems))
    items = {i.name: i for i in frappe.get_all("Item", filters={"name": ["in", list({l["item_code"] for l in lines})]},
                                              fields=["name", "item_name", "stock_uom", "disabled", "is_stock_item", "has_batch_no", "has_serial_no"])}
    whole = _whole([i.stock_uom for i in items.values()])
    teams = {t.name: t.team_name for t in field._teams(farm)}
    doc.set("items", [])
    for src, line in zip([l for l in raw if isinstance(l, dict)], lines):
        item = items.get(line["item_code"])
        if not item or item.disabled or not item.is_stock_item:
            frappe.throw(f"Vật tư {line['item_code']} không dùng được: đã tắt hoặc không quản lý tồn kho.")
        if item.has_batch_no or item.has_serial_no:
            frappe.throw(f"{item.item_name} quản lý theo lô/serial: nhờ Kho xuất trong ERPNext.")
        qty = flt(line["qty"], 6)
        if item.stock_uom in whole and abs(qty - round(qty)) > rules.EPSILON:
            frappe.throw(f"{item.item_name} tính theo {item.stock_uom}: nhập số nguyên.")
        assignment = src.get("assignment") or None
        if assignment:
            t = frappe.db.get_value(field.ASSIGNMENT, assignment, ["farm", "crew", "farm_block", "work_type", "work_team", "state"], as_dict=True)
            if not t or t.farm != farm or t.crew != rights.crew.name or t.farm_block != line["farm_block"] \
                    or t.work_type != work.name or (team and t.work_team != team) or t.state not in field.OPEN_STATES:
                frappe.throw(f"Phiếu giao việc {assignment} không khớp lô, việc, tổ hoặc đã đóng.")
        doc.append("items", dict(item_code=item.name, qty=qty, stock_qty=qty, uom=item.stock_uom, stock_uom=item.stock_uom, conversion_factor=1,
                                 warehouse=warehouse, schedule_date=needed, lotus_farm_block=line["farm_block"], lotus_farm=farm,
                                 lotus_work_type=work.name, lotus_usage_area=line["block_code"], lotus_purpose=work.work_name,
                                 lotus_notes=str(src.get("notes") or "").strip()[:500], lotus_work_assignment=assignment))
    codes = [l["block_code"] for l in lines]
    doc.update(dict(material_request_type=TYPE, company=farm_doc.company, transaction_date=nowdate(), schedule_date=needed,
                    set_warehouse=warehouse, lotus_crew=rights.crew.name, lotus_work_team=team, lotus_issue_receiver=receiver,
                    title=rules.title(work.work_name, teams.get(team) if team else rights.crew.team_name, codes),
                    lotus_request_note=str(values.get("note") or "").strip()[:1000],
                    lotus_department=rights.crew.team_name + (" · " + teams.get(team, team) if team else "")))


def _send(doc):
    leader = frappe.db.get_value("Work Team", doc.lotus_crew, "lotus_leader")
    doc.lotus_issue_approver = rules.approver_for(leader)
    doc.lotus_issue_sent_at = now_datetime()
    doc.lotus_issue_return_reason = None
    _store(doc)
    _note(doc, "Gửi duyệt.")
    farm = _crew_farm(doc.lotus_crew)
    users = [doc.lotus_issue_approver] if doc.lotus_issue_approver else _farm_managers(farm)
    _notify([u for u in users if u != frappe.session.user], "Yêu cầu vật tư chờ bạn duyệt", doc.title, doc.name, "sent:" + str(doc.lotus_issue_sent_at))


def _approve(doc, approver, changes=None, reason=None):
    """Submit the request as approved by `approver`. The checks of who may approve are made by the caller; the
    before_submit hook checks again that the approver is the đội trưởng of the đội or a quản lý vườn."""
    when = now_datetime()
    if not doc.get("lotus_issue_sent_at"):
        doc.lotus_issue_sent_at = when
    doc.lotus_issue_approver = doc.get("lotus_issue_approver") or approver
    doc.lotus_issue_approved_by, doc.lotus_issue_approved_at = approver, when
    doc.lotus_issue_return_reason = None
    doc.flags.lotus_issue_approval = True
    doc.flags.ignore_permissions = True
    token = _writing.set(True)
    try:
        with command(doc, "issue-approve"):
            doc.submit()
    finally:
        _writing.reset(token)
    from lotus_farm.digital_signature import _event
    _event(doc, "APPROVE", approver, when, signature_type="NAME", details=reason or "")
    if changes:
        _note(doc, "Giảm số khi duyệt: " + "; ".join(changes) + (". Lý do: " + reason if reason else ""))
    _note(doc, "Duyệt." if approver == doc.owner else "Duyệt bởi " + approver + ".")
    if approver != doc.owner:
        _notify([doc.owner], "Yêu cầu vật tư đã được duyệt", doc.title, doc.name, "approved")
    users = _warehouse_users(doc.set_warehouse)
    _notify(users, "Cấp vật tư theo yêu cầu " + doc.name, doc.title, doc.name, "approved-kho", app="warehouse")


@frappe.whitelist(methods=["POST"])
def save(farm, crew, values, name=None, modified=None, client_event_id=None, send=0, approve=0):
    """Lưu nháp (send=0), Gửi duyệt (send=1) or Lưu và duyệt (approve=1, the đội trưởng or quản lý vườn approving their own
    request at once). Returns detail() plus warnings."""
    field = _field()
    farm_doc = field.require_farm(farm)
    rights = field.access(farm, crew)
    if not rights.supervisor:
        frappe.throw("Chỉ đội trưởng của đội hoặc quản lý vườn lập yêu cầu cấp vật tư.", frappe.PermissionError)
    values = _values(values)
    user = frappe.session.user
    if cint(approve) and not rules.may_approve(user, rights.crew.lotus_leader, rights.manager):
        frappe.throw("Bạn không duyệt được yêu cầu của đội này.", frappe.PermissionError)

    def operation():
        if name:
            doc = _load(name, modified)
            if doc.owner != user or doc.lotus_crew != crew:
                frappe.throw("Chỉ người lập sửa yêu cầu.", frappe.PermissionError)
            current = rules.state(doc.docstatus, doc.status, doc.get("lotus_issue_sent_at"), doc.get("lotus_issue_return_reason"))
            if current not in rules.EDITABLE:
                frappe.throw("Chỉ sửa yêu cầu nháp hoặc bị trả lại. Đang chờ duyệt thì rút lại trước.")
        else:
            doc = frappe.new_doc(DT)
        _fill(doc, farm_doc, rights, values)
        _store(doc)
        if cint(approve):
            _approve(doc, user)
        elif cint(send):
            _send(doc)
        return doc

    result = _run(client_event_id, "save", name, dict(farm=farm, crew=crew, values=values, modified=modified, send=cint(send),
                                                     approve=cint(approve)), operation)
    out = detail(result["name"])
    out["warnings"] = out.get("warnings") or (_warnings(_get(result["name"]), farm) if out["docstatus"] == 1 else [])
    return out


@frappe.whitelist(methods=["POST"])
def send(name, modified, client_event_id=None):
    def operation():
        doc = _load(name, modified)
        _read_rights(doc)
        if doc.owner != frappe.session.user:
            frappe.throw("Chỉ người lập gửi duyệt.", frappe.PermissionError)
        if rules.state(doc.docstatus, doc.status, doc.get("lotus_issue_sent_at"), doc.get("lotus_issue_return_reason")) not in rules.EDITABLE:
            frappe.throw("Yêu cầu không ở trạng thái nháp hoặc trả lại.")
        if doc.schedule_date and getdate(doc.schedule_date) < getdate(nowdate()):
            frappe.throw("Ngày cần đã qua. Sửa ngày cần trước khi gửi.")
        _send(doc)
        return doc
    return detail(_run(client_event_id, "send", name, dict(modified=modified), operation)["name"])


@frappe.whitelist(methods=["POST"])
def withdraw(name, modified, client_event_id=None):
    def operation():
        doc = _load(name, modified)
        _read_rights(doc)
        if doc.owner != frappe.session.user or doc.docstatus != 0 or not doc.get("lotus_issue_sent_at"):
            frappe.throw("Chỉ người lập rút lại yêu cầu đang chờ duyệt.", frappe.PermissionError)
        doc.lotus_issue_sent_at = None
        _store(doc)
        _note(doc, "Rút lại để sửa.")
        return doc
    return detail(_run(client_event_id, "withdraw", name, dict(modified=modified), operation)["name"])


def _lowered_lines(doc, lines):
    lines = frappe.parse_json(lines) if isinstance(lines, str) else lines
    if isinstance(lines, list):
        lines = {str(l.get("name")): l.get("qty") for l in lines if isinstance(l, dict)}
    if not isinstance(lines, dict):
        frappe.throw("Số giảm không hợp lệ.")
    old = {r.name: flt(r.qty) for r in doc.items}
    try:
        changes = rules.lowered(old, {k: flt(v) for k, v in lines.items()})
    except ValueError as e:
        frappe.throw(str(e))
    return changes


@frappe.whitelist(methods=["POST"])
def approve(name, modified, client_event_id=None, lines=None, reason=None):
    """Duyệt; with lines ({line name: qty} or [{name, qty}]) Giảm số rồi duyệt — only lower or drop, with a reason.
    The đội trưởng of the đội or a quản lý vườn, their own request included (chủ vườn, 11/11/2026)."""
    payload = dict(modified=modified, lines=lines, reason=reason)

    def operation():
        doc = _load(name, modified)
        farm, rights = _read_rights(doc)
        user = frappe.session.user
        if not rules.may_approve(user, rights.crew.lotus_leader, rights.manager):
            frappe.throw("Chỉ đội trưởng của đội hoặc quản lý vườn duyệt yêu cầu này.", frappe.PermissionError)
        current = rules.state(doc.docstatus, doc.status, doc.get("lotus_issue_sent_at"), doc.get("lotus_issue_return_reason"))
        if not (current == rules.SENT or (current in rules.EDITABLE and doc.owner == user)):
            frappe.throw("Yêu cầu không ở trạng thái chờ duyệt.")
        if doc.schedule_date and getdate(doc.schedule_date) < getdate(nowdate()):
            frappe.throw("Ngày cần đã qua. Trả lại để người lập đổi ngày cần.")
        notes = []
        why = None
        if lines not in (None, "", "null"):
            changes = _lowered_lines(doc, lines)
            if changes:
                why = _reason(reason, "giảm số")
                codes = _codes([r.lotus_farm_block for r in doc.items])
                by_name = {r.name: r for r in doc.items}
                for key, before, after in changes:
                    row = by_name[key]
                    notes.append(f"{row.item_code} lô {codes.get(row.lotus_farm_block, row.lotus_farm_block)} {before:g} → {after:g}")
                    if after <= rules.EPSILON:
                        doc.remove(row)
                    else:
                        row.qty = row.stock_qty = after
                for i, row in enumerate(doc.items, 1):
                    row.idx = i
        _approve(doc, user, notes, why)
        return doc
    return detail(_run(client_event_id, "approve", name, payload, operation)["name"])


@frappe.whitelist(methods=["POST"])
def return_request(name, modified, reason, client_event_id=None):
    def operation():
        doc = _load(name, modified)
        farm, rights = _read_rights(doc)
        user = frappe.session.user
        if doc.docstatus != 0 or not doc.get("lotus_issue_sent_at"):
            frappe.throw("Chỉ trả lại yêu cầu đang chờ duyệt.")
        if user == doc.owner or not rules.may_approve(user, rights.crew.lotus_leader, rights.manager):
            frappe.throw("Chỉ người duyệt trả lại yêu cầu của người khác.", frappe.PermissionError)
        why = _reason(reason, "trả lại")
        doc.lotus_issue_sent_at, doc.lotus_issue_return_reason = None, why
        _store(doc)
        _note(doc, "Trả lại: " + why)
        _notify([doc.owner], "Yêu cầu vật tư bị trả lại", why, doc.name, "returned:" + str(doc.modified))
        return doc
    return detail(_run(client_event_id, "return", name, dict(modified=modified, reason=reason), operation)["name"])


def _drafts(name):
    return [r[0] for r in frappe.db.sql("""select distinct p.name from `tabStock Entry` p join `tabStock Entry Detail` d on d.parent = p.name
        where d.material_request = %s and p.docstatus = 0""", (name,))]


def _after_approval(doc):
    lines = _progress([doc.name]).get(doc.name, [])
    return rules.state(doc.docstatus, doc.status, doc.get("lotus_issue_sent_at"), doc.get("lotus_issue_return_reason"), _totals(lines))


@frappe.whitelist(methods=["POST"])
def close(name, modified, reason, client_event_id=None):
    """Đóng phần còn lại: the requester, the approver, a quản lý vườn, or Quản lý kho of that kho (no stock). Refused while a
    draft stock issue still holds part of it."""
    def operation():
        doc = _load(name, modified)
        user = frappe.session.user
        stock_side = _warehouse_manager(doc.set_warehouse) if doc.set_warehouse else False
        manager = False
        if not stock_side:
            _, rights = _read_rights(doc)
            manager = rights.manager
        if not (stock_side or manager or user in (doc.owner, doc.get("lotus_issue_approved_by"))):
            frappe.throw("Bạn không đóng được yêu cầu này.", frappe.PermissionError)
        if _after_approval(doc) not in (rules.WAITING, rules.PARTIAL, rules.PICKING):
            frappe.throw("Chỉ đóng yêu cầu đã duyệt còn số chưa cấp.")
        drafts = _drafts(doc.name)
        if drafts:
            frappe.throw("Kho còn phiếu xuất nháp giữ số của yêu cầu: " + ", ".join(drafts) + ". Kho xóa hoặc ghi sổ phiếu trước.")
        why = _reason(reason, "đóng")
        with command(doc, "issue-close"):
            doc.db_set("lotus_issue_close_reason", why)
            doc.update_status("Stopped")
        _note(doc, "Đóng phần còn lại: " + why)
        _notify([doc.owner, doc.get("lotus_issue_approved_by")], "Yêu cầu vật tư đã đóng", why, doc.name, "closed:" + str(doc.modified))
        _notify(_warehouse_users(doc.set_warehouse), "Yêu cầu " + doc.name + " đã đóng", why, doc.name, "closed-kho:" + str(doc.modified),
                app="warehouse")
        return doc
    result = _run(client_event_id, "close", name, dict(modified=modified, reason=reason), operation)
    try:
        return detail(result["name"])
    except frappe.PermissionError:
        frappe.clear_messages()
        return dict(name=result["name"], state=rules.CLOSED, state_code=rules.CODES[rules.CLOSED])


@frappe.whitelist(methods=["POST"])
def reopen(name, modified, reason, client_event_id=None):
    def operation():
        doc = _load(name, modified)
        _, rights = _read_rights(doc)
        if not (rights.manager or frappe.session.user == doc.get("lotus_issue_approved_by")):
            frappe.throw("Chỉ người đã duyệt hoặc quản lý vườn mở lại.", frappe.PermissionError)
        if doc.docstatus != 1 or doc.status not in STOPPED:
            frappe.throw("Yêu cầu không ở trạng thái đã đóng.")
        why = _reason(reason, "mở lại")
        with command(doc, "issue-reopen"):
            doc.update_status("Submitted")
            doc.db_set("lotus_issue_close_reason", None)
        _note(doc, "Mở lại: " + why)
        _notify([doc.owner, doc.get("lotus_issue_approved_by")], "Yêu cầu vật tư được mở lại", why, doc.name, "reopened:" + str(doc.modified))
        _notify(_warehouse_users(doc.set_warehouse), "Yêu cầu " + doc.name + " mở lại", why, doc.name, "reopened-kho:" + str(doc.modified),
                app="warehouse")
        return doc
    return detail(_run(client_event_id, "reopen", name, dict(modified=modified, reason=reason), operation)["name"])


@frappe.whitelist(methods=["POST"])
def cancel(name, modified, reason, client_event_id=None):
    """Hủy a request approved and not issued at all (no draft nor posted stock issue)."""
    def operation():
        doc = _load(name, modified)
        _, rights = _read_rights(doc)
        if not (rights.manager or frappe.session.user in (doc.owner, doc.get("lotus_issue_approved_by"))):
            frappe.throw("Chỉ người lập, người duyệt hoặc quản lý vườn hủy.", frappe.PermissionError)
        if doc.docstatus != 1 or doc.status in STOPPED:
            frappe.throw("Chỉ hủy yêu cầu đã duyệt đang chờ cấp. Yêu cầu đã đóng thì mở lại trước.")
        if _issues(doc.name)[0]:
            frappe.throw("Yêu cầu đã có phiếu xuất (nháp hoặc đã ghi sổ): không hủy được. Đóng phần còn lại thay vì hủy.")
        why = _reason(reason, "hủy")
        doc.flags.ignore_permissions = True
        with command(doc, "issue-cancel"):
            doc.cancel()
        _note(doc, "Hủy: " + why)
        _notify([doc.owner, doc.get("lotus_issue_approved_by")], "Yêu cầu vật tư đã hủy", why, doc.name, "cancelled")
        return doc
    return detail(_run(client_event_id, "cancel", name, dict(modified=modified, reason=reason), operation)["name"])


class _Gone:
    doctype, name = DT, ""


@frappe.whitelist(methods=["POST"])
def delete_draft(name, modified, client_event_id=None):
    def operation():
        doc = _load(name, modified)
        _read_rights(doc)
        if doc.owner != frappe.session.user:
            frappe.throw("Chỉ người lập xóa yêu cầu nháp.", frappe.PermissionError)
        if rules.state(doc.docstatus, doc.status, doc.get("lotus_issue_sent_at"), doc.get("lotus_issue_return_reason")) not in rules.EDITABLE:
            frappe.throw("Chỉ xóa yêu cầu nháp hoặc bị trả lại.")
        # The double-click guard rows of earlier saves point at the draft; keep them (their result stays) but unlink them,
        # otherwise Frappe refuses the delete as a linked document.
        frappe.db.sql("update `tabLotus ERP Command` set reference_name=null where reference_doctype=%s and reference_name=%s", (DT, doc.name))
        token = _writing.set(True)
        try:
            frappe.delete_doc(DT, doc.name, ignore_permissions=True)
        finally:
            _writing.reset(token)
        return _Gone()
    _run(client_event_id, "delete", name, dict(modified=modified), operation)
    return dict(deleted=name)
