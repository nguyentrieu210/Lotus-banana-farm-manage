"""Spec 005: approved yêu cầu cấp vật tư for integration tests, made the way Lotus makes them.

Since spec 005 a Material Request of type Material Issue is submitted only by its approval in lotus_farm.issue_request
(the hooks refuse doc.submit(), Desk and REST). Tests that need an approved request either:
  - approve_native(doc): approve a request built directly (Desk style, no đội) through the same approval code, as a
    quản lý vườn (Administrator by default); used by the older warehouse scripts, which call issue_request._approve inline;
  - people(...) + request(...): make one through issue_request.save / send / approve with temporary users, as
    verify_issue_request.py does.
Everything is meant to run inside the caller's transaction, which the caller rolls back.
"""
import frappe

from lotus_farm import field_report as field
from lotus_farm import issue_request


def approve_native(doc, approver="Administrator"):
    issue_request._approve(doc, approver)
    return doc


def user(farm, tag, roles):
    email = f"issue-{tag}-{frappe.generate_hash(length=6)}@lotus.test".lower()
    doc = frappe.get_doc(dict(doctype="User", email=email, first_name="Thử " + tag, send_welcome_email=0, user_type="System User"))
    doc.flags.no_welcome_mail = True
    doc.insert(ignore_permissions=True)
    doc.add_roles(*roles)
    frappe.get_doc(dict(doctype="User Permission", user=email, allow="Farm", for_value=farm, apply_to_all_doctypes=1)).insert(
        ignore_permissions=True)
    return email


def crew_with_teams(farm, skip=()):
    """A đội of the farm with a khu, at least one tổ and at least two active lô."""
    teams = field._teams(farm)
    blocks = field._block_map(farm)
    for crew in teams:
        if crew.lotus_team_level != field.CREW or crew.name in skip:
            continue
        zones = field.rules.crew_zones(crew.lotus_zones)
        members = [t.name for t in teams if t.lotus_parent_team == crew.name and t.lotus_team_level == field.TEAM]
        lots = [n for n, b in blocks.items() if b["zone"] in zones]
        if members and len(lots) >= 2:
            return crew, members, lots
    raise AssertionError("Vườn cần một đội có tổ và ít nhất hai lô đang hoạt động")


def people(farm, crew, team):
    """Temporary đội trưởng (made leader of `crew`), tổ trưởng (of `team`) and quản lý vườn."""
    leader = user(farm, "doi", ["Lotus Field Supervisor"])
    team_leader = user(farm, "to", ["Lotus Team Leader"])
    manager = user(farm, "ql", ["Lotus Farm Manager"])
    frappe.db.set_value("Work Team", crew, "lotus_leader", leader, update_modified=False)
    frappe.db.set_value("Work Team", team, "lotus_leader", team_leader, update_modified=False)
    frappe.clear_cache()
    return frappe._dict(leader=leader, team_leader=team_leader, manager=manager)


def as_user(user, fn, *args, **kwargs):
    frappe.set_user(user)
    try:
        return fn(*args, **kwargs)
    finally:
        frappe.set_user("Administrator")


def request(farm, crew, values, by, send=0, approve=0, event=None):
    return as_user(by, issue_request.save, farm, crew, values, client_event_id=event or frappe.generate_hash(length=20),
                   send=send, approve=approve)
