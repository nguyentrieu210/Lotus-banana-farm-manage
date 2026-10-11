"""Minimal phone task assignment. One location picker: Block OR Plot."""
import frappe
from frappe.utils import getdate, nowdate
from lotus_farm.controls import require_role, lock
from lotus_farm.mobile_assignment_rules import split_quantity
from lotus_farm.rules import RuleError, quantity


def permitted_farm(farm):
    require_role("Lotus Farm Manager")
    if not farm:
        frappe.throw("Chọn nông trường trước.")
    doc = frappe.get_doc("Farm", farm)
    doc.check_permission("read")
    if not doc.active:
        frappe.throw("Nông trường không còn hoạt động.")
    return doc


@frappe.whitelist()
def options(farm):
    """Show real, farm-scoped masters only, not demo defaults."""
    permitted_farm(farm)
    return dict(
        farm=farm,
        blocks=frappe.get_list("Farm Block", filters={"farm": farm, "active": 1},
                               fields=["name", "block_code", "block_name"], limit_page_length=1000,
                               order_by="block_code asc"),
        plots=frappe.get_list("Farm Plot", filters={"farm": farm, "active": 1},
                              fields=["name", "farm_block", "plot_code", "plot_name", "area_ha"],
                              limit_page_length=1000, order_by="plot_code asc"),
        teams=frappe.get_list("Work Team", filters={"farm": farm, "active": 1},
                              fields=["name", "team_code", "team_name"], limit_page_length=1000,
                              order_by="team_code asc"),
        works=frappe.get_list("Work Type", filters={"active": 1},
                              fields=["name", "work_code", "work_name", "uom", "productivity_per_workday"],
                              limit_page_length=1000, order_by="work_name asc"),
    )


def _planned_lines(farm, team, items):
    if isinstance(items, str):
        items = frappe.parse_json(items)
    if not isinstance(items, list) or not 1 <= len(items) <= 50:
        frappe.throw("Nhập từ 1 đến 50 nhóm công việc.")
    team_doc = frappe.get_doc("Work Team", team)
    team_doc.check_permission("read")
    if team_doc.farm != farm or not team_doc.active:
        frappe.throw("Tổ được giao phải đang hoạt động trong nông trường.")

    work_cache = {}
    gathered = {}
    for item in items:
        if not isinstance(item, dict) or set(item) - {"location", "work_type", "qty"}:
            frappe.throw("Dòng giao việc có trường không hợp lệ.")
        location, work_name = item.get("location"), item.get("work_type")
        if not isinstance(location, str) or ":" not in location:
            frappe.throw("Chọn lô hoặc thửa cho mỗi công việc.")
        level, target = location.split(":", 1)
        if level not in ("block", "plot") or not target:
            frappe.throw("Vị trí phải là một lô hoặc một thửa.")
        if not work_name:
            frappe.throw("Chọn loại công việc.")
        if work_name not in work_cache:
            work = frappe.get_doc("Work Type", work_name)
            work.check_permission("read")
            if not work.active:
                frappe.throw("Loại công việc đã ngừng áp dụng.")
            if not work.productivity_per_workday or work.productivity_per_workday <= 0:
                frappe.throw("Chưa có định mức năng suất cho " + work.work_name)
            work_cache[work_name] = work
        work = work_cache[work_name]
        try:
            total = quantity(item.get("qty"), "Khối lượng giao", positive=True)
        except RuleError as exc:
            frappe.throw(str(exc))
        if total > 1000000:
            frappe.throw("Khối lượng quá lớn; hãy chia thành nhiều lần giao.")
        if level == "block":
            block = frappe.get_doc("Farm Block", target)
            block.check_permission("read")
            if block.farm != farm or not block.active:
                frappe.throw("Lô không thuộc nông trường đang chọn.")
            plots = frappe.get_list("Farm Plot", filters={"farm": farm, "farm_block": target, "active": 1},
                                    fields=["name", "farm_block", "plot_code", "area_ha"],
                                    limit_page_length=1000, order_by="plot_code asc")
            try:
                portions = split_quantity(total, [p.area_ha for p in plots],
                                         whole=work.uom in ("Bunch", "Tree", "Nos"))
            except RuleError as exc:
                frappe.throw(str(exc))
        else:
            plot = frappe.get_doc("Farm Plot", target)
            plot.check_permission("read")
            if plot.farm != farm or not plot.active:
                frappe.throw("Thửa không thuộc nông trường đang chọn.")
            plots = [frappe._dict(name=plot.name, farm_block=plot.farm_block,
                                  plot_code=plot.plot_code, area_ha=plot.area_ha)]
            portions = [float(total)]
            if work.uom in ("Bunch", "Tree", "Nos") and total != total.to_integral_value():
                frappe.throw("Công việc tính bằng buồng/cây phải giao số nguyên.")
        for plot, planned in zip(plots, portions):
            if planned <= 0:
                continue
            cycles = frappe.get_list("Crop Cycle", filters={
                "farm": farm, "farm_plot": plot.name, "status": ["in", ["Active", "Harvesting"]]
            }, fields=["name", "cycle_type"], limit_page_length=3)
            if len(cycles) != 1:
                frappe.throw("Thửa " + plot.plot_code + " cần đúng 1 vụ đang hoạt động để giao nhanh.")
            cohort = None
            if cycles[0].cycle_type == "Ratoon":
                cohorts = frappe.get_list("Sucker Selection Batch", filters={
                    "farm": farm, "crop_cycle": cycles[0].name,
                    "status": ["in", ["Open", "In Production", "Harvesting"]]
                }, fields=["name"], limit_page_length=3)
                if len(cohorts) != 1:
                    frappe.throw("Thửa " + plot.plot_code + " có nhiều/không có đợt chồi phù hợp.")
                cohort = cohorts[0].name
            key = (plot.name, cycles[0].name, cohort, work.name)
            if key not in gathered:
                gathered[key] = dict(farm=farm, farm_block=plot.farm_block,
                    farm_plot=plot.name, plot_code=plot.plot_code,
                    crop_cycle=cycles[0].name, sucker_selection_batch=cohort,
                    work_type=work.name, work_name=work.work_name, uom=work.uom,
                    productivity_per_workday=work.productivity_per_workday,
                    planned_qty=0.0, work_team=team_doc.name)
            gathered[key]["planned_qty"] += float(planned)
    if len(gathered) > 200:
        frappe.throw("Quá nhiều thửa; hãy chia kế hoạch.")
    return list(gathered.values())


@frappe.whitelist(methods=["POST"])
def preview(farm, work_team, items):
    permitted_farm(farm)
    return dict(lines=_planned_lines(farm, work_team, items),
                note="Chọn lô sẽ chia chỉ tiêu theo diện tích các thửa; xem lại trước khi giao.")


@frappe.whitelist(methods=["POST"])
def create(farm, posting_date, work_team, items):
    farm_doc = permitted_farm(farm)
    date = getdate(posting_date)
    if not date:
        frappe.throw("Chọn ngày giao việc.")
    # Farm lock serializes concurrent quick submissions and protects duplicate checks.
    lock("Farm", farm)
    lines = _planned_lines(farm, work_team, items)
    existing = frappe.get_list("Daily Work Plan", filters={
        "farm": farm, "posting_date": date, "docstatus": 1
    }, fields=["name"], limit_page_length=10000)
    requested = {(r["farm_plot"], r["crop_cycle"], r["sucker_selection_batch"] or "",
                  r["work_type"], r["work_team"]) for r in lines}
    for row in existing:
        plan = frappe.get_doc("Daily Work Plan", row.name)
        for line in plan.lines:
            key = (line.farm_plot, line.crop_cycle, line.sucker_selection_batch or "",
                   line.work_type, line.work_team)
            if key in requested:
                frappe.throw("Việc đã được giao trong ngày tại thửa " +
                             (line.farm_plot or "") + ". Mở kế hoạch cũ để xem.")
    doc = frappe.get_doc(dict(doctype="Daily Work Plan", farm=farm,
        company=farm_doc.company, posting_date=date,
        lines=[{k: v for k, v in row.items() if k not in (
            "plot_code", "work_name", "productivity_per_workday")} for row in lines]))
    doc.insert()
    doc.submit()
    return dict(plan=doc.name, count=len(lines),
                farm=farm, posting_date=str(date), status="Submitted")
