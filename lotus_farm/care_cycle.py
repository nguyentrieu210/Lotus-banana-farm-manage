"""Vòng chăm sóc: which lô are due or late for which việc vườn, and giao theo vòng.

The cycle of a việc is a Work Schedule Rule (care_cycle_rules says which one applies). A lô is done with a việc on the
day a confirmed line of the sổ lô says the whole lô is done. Giao reuses the phiếu Round of field_report (its pay mode
and price are fixed on the phiếu); the phiếu keeps the cycle it was given for. Only the quản lý vườn sets cycles.
"""
import frappe
from frappe.utils import add_days, cint, getdate, nowdate

from lotus_farm import care_cycle_rules as rules
from lotus_farm import field_report as field
from lotus_farm.controls import lock
from lotus_farm.lot_ledger import ENTRY

RULE = "Work Schedule Rule"
RULE_FIELDS = ["name", "rule_name", "work_type", "farm_zone", "repeat_days", "valid_from", "valid_to", "version", "approval_state", "notes",
               "owner", "modified"]
MAX_DAYS_AHEAD = 62


def _rules(farm):
    return frappe.get_all(RULE, filters={"farm": farm}, fields=RULE_FIELDS, order_by="rule_name asc, version desc", limit_page_length=0)


def _last_done(blocks, works):
    if not blocks or not works:
        return {}
    rows = frappe.db.sql(f"""select farm_block, work_type, max(posting_date) as posting_date from `tab{ENTRY}`
                             where state = 'Confirmed' and done = 1 and farm_block in %(blocks)s and work_type in %(works)s
                             group by farm_block, work_type""", {"blocks": list(blocks), "works": list(works)}, as_dict=True)
    return rules.last_done([dict(r, done=1) for r in rows])


def _open_rounds(farm, blocks):
    rows = frappe.get_all(field.ASSIGNMENT, filters={"farm": farm, "kind": field.rules.ROUND, "state": ["in", list(field.OPEN_STATES)],
                                                     "farm_block": ["in", list(blocks) or [""]]},
                          fields=["name", "farm_block", "work_type", "work_team", "assigned_on", "due_date", "state"], limit_page_length=0)
    return {(r.farm_block, r.work_type): r for r in rows}


def _scope(farm, crew):
    """The lô this user may look at: those of the đội's khu, or every lô for the quản lý vườn."""
    field.require_farm(farm)
    known = field._block_map(farm)
    if crew:
        rights = field.access(farm, crew)
        if not rights.read:
            frappe.throw("Bạn không thuộc đội này.", frappe.PermissionError)
        return {name: b for name, b in known.items() if b["zone"] in rights.zones}, rights
    if not field.is_manager():
        frappe.throw("Chọn đội.", frappe.PermissionError)
    return known, None


@frappe.whitelist()
def due(farm, crew=None, to_date=None):
    """Every lô × việc with a cycle in force: last done, due day, days late, the tổ it is given to; plus a count per việc.
    What falls due by to_date (the end of this week by default) is due; anything before today is late."""
    blocks, rights = _scope(farm, crew)
    today = getdate(nowdate())
    until = getdate(to_date) if to_date else add_days(today, 6 - today.weekday())
    if until < today or (until - today).days > MAX_DAYS_AHEAD:
        frappe.throw(f"Chọn khoảng từ hôm nay đến tối đa {MAX_DAYS_AHEAD} ngày sau.")
    all_rules = _rules(farm)
    works = sorted({r.work_type for r in rules.in_force(all_rules, today)})
    rows = rules.due_cells({n: {"code": b["block_code"], "zone": b["zone"]} for n, b in blocks.items()}, works, all_rules,
                           _last_done(blocks, works), _open_rounds(farm, blocks), today, until)
    labels = {w.name: w.work_name for w in frappe.get_all("Work Type", filters={"name": ["in", works or [""]]}, fields=["name", "work_name"])}
    teams = {t.name: t for t in field._teams(farm)}
    for r in rows:
        r["work_name"] = labels.get(r["work_type"], r["work_type"])
        r["team_name"] = teams[r["work_team"]].team_name if r["work_team"] in teams else ""
        r["area_ha"] = blocks[r["farm_block"]]["area_ha"]
    summary = rules.summary(rows)
    for s in summary:
        s["work_name"] = labels.get(s["work_type"], s["work_type"])
    members = sorted(rights.members if rights else [], key=lambda n: teams[n].team_name)
    return {"today": str(today), "until": str(until), "rows": rows, "summary": summary,
            "teams": [{"name": n, "team_name": teams[n].team_name} for n in members],
            "can_assign": bool(rights and rights.supervisor), "has_rules": bool(all_rules)}


@frappe.whitelist(methods=["POST"])
def assign(farm, work_type, blocks, team, due_date=None, crew=None):
    """Give one việc on several lô to one tổ (one phiếu Round per lô), keeping the cycle each lô was due under. A lô that
    already has an open phiếu for this việc is named and nothing is created."""
    crew = crew or frappe.db.get_value("Work Team", team, "lotus_parent_team")
    if not crew:
        frappe.throw("Chọn tổ thuộc một đội.")
    result = field.assign(farm, crew, work_type, team, blocks, due_date=due_date)
    today = getdate(nowdate())
    all_rules = _rules(farm)
    known = field._block_map(farm)
    for name in result["created"]:
        block = frappe.db.get_value(field.ASSIGNMENT, name, "farm_block")
        rule = rules.rule_for(all_rules, known.get(block, {}).get("zone"), work_type, today)
        if rule:
            frappe.db.set_value(field.ASSIGNMENT, name, "cycle_rule", rule["name"], update_modified=False)
    return result


@frappe.whitelist(methods=["POST"])
def reassign(assignment, team, reason, expected_modified=None):
    return field.reassign(assignment, team, reason, expected_modified)


@frappe.whitelist(methods=["POST"])
def cancel(assignment, reason, expected_modified=None):
    return field.cancel_assignment(assignment, reason, expected_modified)


def _require_manager(farm):
    field.require_farm(farm)
    if not field.is_manager():
        frappe.throw("Chỉ quản lý vườn đặt vòng chăm sóc.", frappe.PermissionError)


@frappe.whitelist()
def rule_list(farm):
    """Every cycle and its versions, the việc that can take one (việc vườn and phun bón, not the bunch stages) and the khu."""
    field.require_farm(farm)
    works = [{"name": w.name, "work_name": w.work_name, "uom": w.uom, "group": w.lotus_work_group}
             for w in field._works(farm) if not w.lotus_bunch_stage]
    today = getdate(nowdate())
    current = {r.name for r in rules.in_force(_rules(farm), today)}
    rows = [dict(r, in_force=r.name in current) for r in _rules(farm)]
    zones = sorted({b["zone"] for b in field._block_map(farm).values() if b["zone"]})
    return {"rules": rows, "works": works, "zones": zones, "can_edit": field.is_manager()}


@frappe.whitelist(methods=["POST"])
def save_rule(farm, work_type, repeat_days, valid_from, valid_to=None, farm_zone=None, rule_name=None, notes=None):
    """A new version of a cycle, waiting for approval. The same name and khu continue an existing cycle."""
    _require_manager(farm)
    zone = rules.zone_of(farm_zone)
    errors = rules.check_rule({"work_type": work_type, "repeat_days": repeat_days, "valid_from": valid_from, "valid_to": valid_to})
    if errors:
        frappe.throw("<br>".join(errors))
    if not rule_name:
        label = frappe.db.get_value("Work Type", work_type, "work_name") or work_type
        rule_name = label + (f" khu {zone}" if zone else "")
    rule_name = str(rule_name).strip()[:140]
    lock("Farm", farm)
    same = frappe.get_all(RULE, filters={"farm": farm, "rule_name": rule_name}, fields=["name", "work_type", "version", "approval_state"],
                          limit_page_length=0)
    if any(s.work_type != work_type for s in same):
        frappe.throw(f"Tên vòng \"{rule_name}\" đang dùng cho việc khác.")
    drafts = [s.name for s in same if s.approval_state != rules.APPROVED]
    if drafts:
        frappe.throw(f"Vòng \"{rule_name}\" đang có phiên bản chờ duyệt. Duyệt hoặc xóa bản đó trước.")
    doc = frappe.new_doc(RULE)
    doc.update({"farm": farm, "rule_name": rule_name, "work_type": work_type, "farm_zone": zone or None, "repeat_days": cint(repeat_days),
                "valid_from": getdate(valid_from), "valid_to": getdate(valid_to) if valid_to else None,
                "version": max([cint(s.version) for s in same] or [0]) + 1, "approval_state": "Draft", "notes": (notes or "").strip()[:500]})
    doc.insert()
    return doc.as_dict()


@frappe.whitelist(methods=["POST"])
def approve_rule(name):
    doc = frappe.get_doc(RULE, name)
    _require_manager(doc.farm)
    if doc.approval_state == rules.APPROVED:
        return doc.as_dict()
    doc.approval_state = rules.APPROVED
    doc.save()
    return doc.as_dict()


@frappe.whitelist(methods=["POST"])
def delete_rule(name):
    doc = frappe.get_doc(RULE, name)
    _require_manager(doc.farm)
    doc.delete(ignore_permissions=True)
    return {"deleted": name}
