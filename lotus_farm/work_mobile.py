"""Mobile work lists: read-only, permission-scoped view of existing plans/results.

All writes intentionally use mobile_assignment, console.work_state and field.capture.
"""
import frappe
from frappe.utils import getdate, add_days
from lotus_farm.daily_api import daily_overview


def _farm(farm):
    if not farm:
        frappe.throw("Chọn vườn.")
    record = frappe.get_doc("Farm", farm)
    record.check_permission("read")
    return record


@frappe.whitelist()
def day(farm, posting_date):
    record = _farm(farm)
    date = getdate(posting_date)
    if not date:
        frappe.throw("Chọn ngày làm việc.")
    overview = daily_overview(farm, date) if frappe.has_permission("Daily Work Plan", "read") else {"tasks": []}
    # Display human-friendly team names in the phone UI, not internal link IDs.
    if frappe.has_permission("Work Team", "read"):
        teams = {t.name: t.team_name for t in frappe.get_list(
            "Work Team", filters={"farm": farm}, fields=["name", "team_name"], limit_page_length=2000)}
        for task in overview.get("tasks", []):
            task["team_label"] = teams.get(task.get("work_team"), task.get("work_team"))
    plans = frappe.get_list(
        "Daily Work Plan",
        filters={"farm": farm, "posting_date": date},
        fields=["name", "posting_date", "docstatus", "owner", "rate_approval_state",
                "rate_request_reason", "modified"],
        limit_page_length=500, order_by="modified desc"
    ) if frappe.has_permission("Daily Work Plan", "read") else []
    return {
        "farm": farm, "farm_name": record.farm_name,
        "posting_date": str(date), "tasks": overview.get("tasks", []),
        "plans": plans
    }


@frappe.whitelist()
def history(farm, to_date, days=14):
    record = _farm(farm)
    end = getdate(to_date)
    if not end:
        frappe.throw("Chọn ngày kết thúc.")
    try:
        window = max(1, min(int(days), 31))
    except (ValueError, TypeError):
        window = 14
    start = add_days(end, 1 - window)
    if not frappe.has_permission("Daily Work Result", "read"):
        return {"farm": farm, "farm_name": record.farm_name, "rows": [], "from_date": str(start), "to_date": str(end)}
    rows = frappe.get_list("Daily Work Result", filters={
        "farm": farm, "docstatus": 1, "posting_date": ["between", [start, end]]
    }, fields=["name", "posting_date", "farm_block", "farm_plot", "work_plan", "work_plan_line",
               "completed_qty", "actual_workdays", "unfinished_reason", "modified"],
        order_by="posting_date desc", limit_page_length=300)
    plans = {}
    for row in rows:
        if row.work_plan not in plans:
            try:
                plan = frappe.get_doc("Daily Work Plan", row.work_plan)
                plan.check_permission("read")
                plans[row.work_plan] = {line.name: line.work_type for line in plan.lines}
            except (frappe.PermissionError, frappe.DoesNotExistError):
                plans[row.work_plan] = {}
        work_type = plans[row.work_plan].get(row.work_plan_line)
        row["work_name"] = frappe.db.get_value("Work Type", work_type, "work_name") if work_type else "Công việc"
        row["block_code"] = frappe.db.get_value("Farm Block", row.farm_block, "block_code") or row.farm_block
        row["plot_code"] = frappe.db.get_value("Farm Plot", row.farm_plot, "plot_code") if row.farm_plot else None
    return {"farm": farm, "farm_name": record.farm_name, "rows": rows,
            "from_date": str(start), "to_date": str(end)}
