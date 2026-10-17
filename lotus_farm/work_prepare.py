"""Single-tap field preparation. No stock movement happens here.

The aggregate labor allocation is a planning figure for the TEAM, not individual
attendance or payroll. Real stock issues remain in the Warehouse application.
"""
import frappe
from frappe.utils import flt

from lotus_farm.controls import require_role, lock


@frappe.whitelist(methods=["POST"])
def prepare(plan, line):
    require_role("Lotus Farm Manager")
    work_plan = frappe.get_doc("Daily Work Plan", plan)
    work_plan.check_permission("read")
    lock("Farm", work_plan.farm)
    lock("Daily Work Plan", work_plan.name)
    work_plan.reload()
    if work_plan.docstatus != 1:
        frappe.throw("Kế hoạch phải được giao và duyệt đơn giá trước khi chuẩn bị.")
    task = next((row for row in work_plan.lines if row.name == line), None)
    if not task:
        frappe.throw("Công việc không thuộc kế hoạch.")
    if not task.work_team:
        frappe.throw("Phải giao cho tổ trước khi phân công.")
    if frappe.db.exists("Daily Work Result", {"work_plan_line": line, "docstatus": 1}):
        frappe.throw("Công việc đã có kết quả chính thức, không thể chuẩn bị lại.")
    from lotus_farm.daily_operations import day_guard
    day_guard(work_plan)
    values = {name: task.get(name) for name in
              ("farm_block", "farm_plot", "crop_cycle", "sucker_selection_batch")}
    allocated = sum(flt(row) for row in frappe.get_all(
        "Labor Allocation", filters={"work_plan_line": line, "docstatus": 1},
        pluck="allocated_workdays"))
    remaining = max(0, flt(task.required_workdays) - allocated)
    labor_created = None
    if remaining > 0.000001:
        allocation = frappe.get_doc({
            "doctype": "Labor Allocation", "farm": work_plan.farm,
            "posting_date": work_plan.posting_date,
            "work_plan": work_plan.name, "work_plan_line": line,
            "work_team": task.work_team, **values,
            "allocated_workdays": round(remaining, 6),
            "allocation_note": "Phân tổng công dự kiến theo tổ từ app Công việc ngoài vườn; không phải chấm công cá nhân.",
        })
        allocation.insert()
        allocation.submit()
        labor_created = allocation.name

    requirement = None
    if task.norm_profile:
        existing = frappe.get_all(
            "Material Requirement",
            filters={"work_plan_line": line, "docstatus": ["<", 2]},
            fields=["name", "docstatus"], order_by="creation asc",
            limit_page_length=2,
        )
        if len(existing) > 1:
            frappe.throw("Công việc có nhiều phiếu nhu cầu vật tư, cần kiểm tra trước.")
        if existing:
            req = frappe.get_doc("Material Requirement", existing[0].name)
            req.check_permission("read")
        else:
            req = frappe.get_doc({
                "doctype": "Material Requirement", "farm": work_plan.farm,
                "posting_date": work_plan.posting_date,
                "work_plan": work_plan.name, "work_plan_line": line, **values,
            })
            req.insert()
        if req.docstatus == 0:
            req.submit()
        requirement = req.name

    return {
        "plan": work_plan.name, "line": line, "labor_created": labor_created,
        "total_allocated_workdays": round(allocated + remaining, 6),
        "material_requirement": requirement,
        "note": "Đã chuẩn bị công dự kiến và nhu cầu vật tư; xuất/cấp vật tư thực tế tại app Kho.",
    }
