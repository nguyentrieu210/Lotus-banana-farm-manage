"""Role and work-team scope. No implicit team access.

A role answers which actions are allowed; User Permission for Farm/Work Team
answers where.
"""
import frappe

LEADER = "Lotus Team Leader"
SUPERVISOR = "Lotus Field Supervisor"
MANAGER = "Lotus Farm Manager"
AUDITOR = "Lotus Auditor"
PRICE = "Lotus Price Approver"


def roles(user=None):
    user = user or frappe.session.user
    return set(frappe.get_roles(user)) if user != "Guest" else set()


def is_manager(user=None):
    user = user or frappe.session.user
    return user == "Administrator" or MANAGER in roles(user)


def can_review_all(user=None):
    user = user or frappe.session.user
    return user == "Administrator" or bool({MANAGER, AUDITOR, PRICE} & roles(user))


def require_farm(farm, user=None):
    from lotus_farm.controls import farm_allowed
    if not farm or not farm_allowed(farm, user):
        frappe.throw("Bạn không được cấp quyền vườn này.", frappe.PermissionError)


def allowed_teams(farm, user=None):
    """Return team IDs, never trusting a client-supplied team list."""
    user = user or frappe.session.user
    require_farm(farm, user)
    if can_review_all(user):
        return set(frappe.get_all("Work Team", filters={"farm": farm, "active": 1}, pluck="name"))
    if not {LEADER, SUPERVISOR}.intersection(roles(user)):
        return set()
    grants = frappe.get_all("User Permission", filters={"user": user, "allow": "Work Team"}, pluck="for_value")
    if not grants:
        return set()
    return set(frappe.get_all("Work Team", filters={"farm": farm, "active": 1, "name": ["in", grants]}, pluck="name"))
