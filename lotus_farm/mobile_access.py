"""Role and work-team scope for Lotus mobile. No implicit team access.

A role answers which actions are allowed; User Permission for Farm/Work Team
answers where. Full plan documents can contain multiple teams and must never
be served to a team-scoped account through the mobile APIs.
"""
import frappe
from frappe.utils import flt, getdate
from math import isfinite
from contextvars import ContextVar
from contextlib import contextmanager

_CAPTURE = ContextVar("lotus_mobile_scoped_capture", default=None)


@contextmanager
def scoped_result_capture(plan, line):
    token = _CAPTURE.set((frappe.session.user, plan, line))
    try:
        yield
    finally:
        _CAPTURE.reset(token)


def can_skip_plan_read(doc):
    return doc.doctype == "Daily Work Result" and _CAPTURE.get() == (
        frappe.session.user, doc.work_plan, doc.work_plan_line)

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


def is_field_user(user=None):
    user = user or frappe.session.user
    return user != "Guest" and bool({LEADER, SUPERVISOR, MANAGER, AUDITOR, PRICE} & roles(user) or user == "Administrator")


def can_assign(user=None):
    user = user or frappe.session.user
    return user == "Administrator" or bool({MANAGER, SUPERVISOR} & roles(user))


def can_capture(user=None):
    user = user or frappe.session.user
    return user == "Administrator" or bool({MANAGER, SUPERVISOR, LEADER} & roles(user))


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


def require_team(farm, team, user=None):
    if not team or team not in allowed_teams(farm, user):
        frappe.throw("Bạn không được phân công tổ này.", frappe.PermissionError)


def abilities(user=None):
    user = user or frappe.session.user
    return {
        "work.task.read": is_field_user(user),
        "work.assign": can_assign(user),
        "work.result.capture": can_capture(user),
        "work.block.report": can_capture(user),
        "work.rate.approve": user == "Administrator" or PRICE in roles(user),
        "work.summary.all": can_review_all(user),
    }


def validate_capture(farm, values):
    """Reject spoofed scope/fields before creating a team leader's result."""
    if not isinstance(values, dict):
        frappe.throw("Dữ liệu báo cáo không hợp lệ.")
    required = {"work_plan", "work_plan_line", "posting_date", "farm_block", "completed_qty", "actual_workdays"}
    allowed = required | {"farm_plot", "crop_cycle", "sucker_selection_batch", "unfinished_reason"}
    if not required.issubset(values) or set(values) - allowed:
        frappe.throw("Báo cáo có trường ngoài phạm vi cho phép.", frappe.PermissionError)
    plan = frappe.get_doc("Daily Work Plan", values["work_plan"])
    if plan.docstatus != 1 or plan.farm != farm:
        frappe.throw("Kế hoạch không thuộc vườn hoặc chưa giao.")
    line = next((line for line in plan.lines if line.name == values["work_plan_line"]), None)
    if not line:
        frappe.throw("Công việc không thuộc kế hoạch.")
    require_team(farm, line.work_team)
    if getdate(values["posting_date"]) != getdate(plan.posting_date):
        frappe.throw("Ngày báo cáo khác ngày kế hoạch.")
    for field in ("farm_block", "farm_plot", "crop_cycle", "sucker_selection_batch"):
        if (values.get(field) or "") != (line.get(field) or ""):
            frappe.throw("Lô và phạm vi báo cáo không khớp công việc.", frappe.PermissionError)
    try:
        completed = float(values["completed_qty"])
        days = float(values["actual_workdays"])
    except (ValueError, TypeError):
        frappe.throw("Số lượng hoặc số công không hợp lệ.")
    if not isfinite(completed) or not isfinite(days) or completed < 0 or completed > flt(line.planned_qty) + 0.000001 or days < 0:
        frappe.throw("Số lượng hoặc số công không hợp lệ.")
    if completed < flt(line.planned_qty) and not str(values.get("unfinished_reason") or "").strip():
        frappe.throw("Chưa đạt kế hoạch phải ghi lý do.")
    return plan, line
