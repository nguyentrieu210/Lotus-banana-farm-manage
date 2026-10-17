"""Permission-scoped mobile views: never return a whole mixed-team plan to team users."""
import frappe
from frappe.utils import getdate, add_days, flt
from lotus_farm.mobile_access import (
    allowed_teams, can_review_all, is_field_user, require_farm,
)
from lotus_farm.daily_api import daily_overview


def _farm(farm):
    if not farm:
        frappe.throw("Chọn vườn.")
    require_farm(farm)
    record = frappe.get_doc("Farm", farm)
    record.check_permission("read")
    if not is_field_user():
        frappe.throw("Tài khoản chưa có quyền công việc ngoài vườn.", frappe.PermissionError)
    return record


def _own_tasks(farm, posting_date):
    """Inspect only submitted plans in granted Farm; emit allowed child lines."""
    teams = allowed_teams(farm)
    if not teams:
        return []
    names = frappe.get_all(
        "Daily Work Plan", filters={"farm": farm, "posting_date": posting_date, "docstatus": 1},
        pluck="name", limit_page_length=10000)
    team_labels = {r.name: r.team_name for r in frappe.get_all(
        "Work Team", filters={"name": ["in", list(teams)]},
        fields=["name", "team_name"], limit_page_length=2000)}
    tasks = []
    for name in names:
        plan = frappe.get_doc("Daily Work Plan", name)
        for line in plan.lines:
            if line.work_team not in teams:
                continue
            result = frappe.get_all(
                "Daily Work Result", filters={"work_plan_line": line.name, "docstatus": 1},
                fields=["name", "completed_qty", "actual_workdays", "unfinished_reason"],
                limit_page_length=1)
            done = result[0] if result else {}
            tasks.append({
                "plan": plan.name, "line": line.name, "posting_date": str(posting_date),
                "farm_block": line.farm_block, "farm_plot": line.farm_plot,
                "crop_cycle": line.crop_cycle, "cohort": line.sucker_selection_batch,
                "work_team": line.work_team, "team_label": team_labels.get(line.work_team, line.work_team),
                "work_type": line.work_type,
                "work_name": frappe.db.get_value("Work Type", line.work_type, "work_name"),
                "block_code": frappe.db.get_value("Farm Block", line.farm_block, "block_code"),
                "planned_qty": flt(line.planned_qty), "completed_qty": flt(done.get("completed_qty")),
                "actual_workdays": flt(done.get("actual_workdays")),
                "required_workdays": flt(line.required_workdays), "uom": line.uom,
                "result": done.get("name"), "unfinished_reason": done.get("unfinished_reason"),
                "status": "Completed" if done else (line.execution_state or "Planned"),
                "blocked_reason": line.blocked_reason,
                "start_at": line.start_at, "due_at": line.due_at,
            })
    return tasks


@frappe.whitelist()
def day(farm, posting_date):
    record = _farm(farm)
    date = getdate(posting_date)
    if not date:
        frappe.throw("Chọn ngày làm việc.")
    if can_review_all():
        overview = daily_overview(farm, date) if frappe.has_permission("Daily Work Plan", "read") else {"tasks": []}
        tasks = overview.get("tasks", [])
        teams = {t.name: t.team_name for t in frappe.get_list(
            "Work Team", filters={"farm": farm}, fields=["name", "team_name"],
            limit_page_length=2000)} if frappe.has_permission("Work Team", "read") else {}
        for task in tasks:
            task["team_label"] = teams.get(task.get("work_team"), task.get("work_team"))
        plans = frappe.get_list(
            "Daily Work Plan", filters={"farm": farm, "posting_date": date},
            fields=["name", "posting_date", "docstatus", "owner", "rate_approval_state",
                    "rate_request_reason", "modified"], limit_page_length=500,
            order_by="modified desc") if frappe.has_permission("Daily Work Plan", "read") else []
    else:
        tasks, plans = _own_tasks(farm, date), []
    return {
        "farm": farm, "farm_name": record.farm_name,
        "posting_date": str(date), "tasks": tasks, "plans": plans,
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
    all_access = can_review_all()
    teams = allowed_teams(farm) if not all_access else None
    if all_access and not frappe.has_permission("Daily Work Result", "read"):
        rows = []
    elif not all_access and not teams:
        rows = []
    else:
        query = frappe.get_list if all_access else frappe.get_all
        raw = query("Daily Work Result", filters={
            "farm": farm, "docstatus": 1, "posting_date": ["between", [start, end]]},
            fields=["name", "posting_date", "farm_block", "farm_plot", "work_plan",
                    "work_plan_line", "completed_qty", "actual_workdays",
                    "unfinished_reason", "modified"],
            order_by="posting_date desc", limit_page_length=300 if all_access else 3000)
        rows = []
        for row in raw:
            line = frappe.db.get_value("Daily Work Plan Line", row.work_plan_line,
                                       ["parent", "work_team", "work_type"], as_dict=True)
            if not line or line.parent != row.work_plan:
                continue
            if not all_access and line.work_team not in teams:
                continue
            row["work_name"] = frappe.db.get_value("Work Type", line.work_type, "work_name") if line.work_type else "Công việc"
            row["block_code"] = frappe.db.get_value("Farm Block", row.farm_block, "block_code") or row.farm_block
            row["plot_code"] = frappe.db.get_value("Farm Plot", row.farm_plot, "plot_code") if row.farm_plot else None
            rows.append(row)
            if len(rows) >= 300:
                break
    return {
        "farm": farm, "farm_name": record.farm_name, "rows": rows,
        "from_date": str(start), "to_date": str(end),
    }
