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
                              fields=["name", "work_code", "work_name", "uom", "productivity_per_workday", "piecework_rate", "allow_daywork", "allow_piecework"],
                              limit_page_length=1000, order_by="work_name asc"),
    )


def _approved_material_norm(farm, work_type, posting_date):
    """Pick only the approved version valid on the work date, not a draft or expired norm."""
    from lotus_farm.daily_operations import applicable_norm

    matches = frappe.get_list("Material Norm Profile", filters={
        "farm": farm, "work_type": work_type, "approval_state": "Approved",
        "valid_from": ["<=", posting_date], "valid_to": [">=", posting_date],
    }, fields=["name"], limit_page_length=2)
    if len(matches) > 1:
        frappe.throw("Nhiều định mức vật tư cùng hiệu lực. Cần kiểm tra trước khi giao việc.")
    return applicable_norm(matches[0].name, farm, work_type, posting_date) if matches else None


def _planned_lines(farm, team, items, posting_date=None):
    if isinstance(items, str):
        items = frappe.parse_json(items)
    if not isinstance(items, list) or not 1 <= len(items) <= 50:
        frappe.throw("Nhập từ 1 đến 50 nhóm công việc.")
    team_doc = frappe.get_doc("Work Team", team)
    team_doc.check_permission("read")
    if team_doc.farm != farm or not team_doc.active:
        frappe.throw("Tổ được giao phải đang hoạt động trong nông trường.")

    work_cache = {}
    norm_cache = {}
    posting_date = getdate(posting_date or nowdate())
    gathered = {}
    for item in items:
        if not isinstance(item, dict) or set(item) - {"location", "work_type", "qty", "payment_mode", "piecework_rate"}:
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
            work_cache[work_name] = work
        work = work_cache[work_name]
        if work_name not in norm_cache:
            norm_cache[work_name] = _approved_material_norm(farm, work_name, posting_date)
        from lotus_farm.labor_pricing import labor_settings, planned_labor
        from lotus_farm.rate_approval import resolve_rate
        try:
            payment = labor_settings(work.allow_daywork, work.allow_piecework,
                work.productivity_per_workday, work.piecework_rate, item.get('payment_mode'))
            price = resolve_rate(work.piecework_rate, item.get("piecework_rate"), payment["mode"])
            payment["piecework_rate"] = price["rate"]
        except ValueError as exc:
            frappe.throw(str(exc))
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
            key = (plot.name, cycles[0].name, cohort, work.name, payment['mode'])
            if key not in gathered:
                gathered[key] = dict(farm=farm, farm_block=plot.farm_block,
                    farm_plot=plot.name, plot_code=plot.plot_code,
                    crop_cycle=cycles[0].name, sucker_selection_batch=cohort,
                    work_type=work.name, work_name=work.work_name, uom=work.uom,
                    productivity_per_workday=payment['productivity'],
                    piecework_rate=payment['piecework_rate'],payment_mode=payment['mode'],
                    list_piecework_rate=price["list_rate"],
                    requested_piecework_rate=price["rate"],
                    requires_approval=price["requires_approval"],
                    planned_qty=0.0, work_team=team_doc.name)
            if gathered[key]["requested_piecework_rate"] != price["rate"]:
                frappe.throw("Cùng công việc và thửa không được giao hai giá khác nhau trong một phiếu.")
            gathered[key]["planned_qty"] += float(planned)
    for row in gathered.values():
        row.update(planned_labor(row['planned_qty'], dict(productivity=row['productivity_per_workday'], piecework_rate=row['piecework_rate'])))
    from lotus_farm.operations_rules import material_needed
    for row in gathered.values():
        norm = norm_cache[row['work_type']]
        row['norm_profile'] = norm.name if norm else None
        row['norm_version'] = norm.version if norm else 0
        row['materials'] = ([dict(item=source.item, uom=source.uom,
            required_qty=material_needed(row['planned_qty'], source.norm_qty,
                source.basis_qty, source.frequency, source.conversion_factor))
            for source in norm.lines] if norm else [])
    if len(gathered) > 200:
        frappe.throw("Quá nhiều thửa; hãy chia kế hoạch.")
    return list(gathered.values())


@frappe.whitelist(methods=["POST"])
def preview(farm, work_team, items, posting_date=None):
    permitted_farm(farm)
    lines = _planned_lines(farm, work_team, items, posting_date)
    materials = {}
    missing = set()
    for line in lines:
        if not line['norm_profile']:
            missing.add(line['work_name'])
        for material in line['materials']:
            key = (material['item'], material['uom'])
            materials[key] = materials.get(key, 0) + material['required_qty']
    return dict(lines=lines,
                approval_required=any(line["requires_approval"] for line in lines),
                materials=[dict(item=k[0], uom=k[1], required_qty=round(qty, 6)) for k, qty in sorted(materials.items())],
                missing_norms=sorted(missing),
                note="Chọn lô sẽ chia chỉ tiêu theo diện tích các thửa; xem lại trước khi giao.")


@frappe.whitelist(methods=["POST"])
def create(farm, posting_date, work_team, items, rate_request_reason=None):
    farm_doc = permitted_farm(farm)
    date = getdate(posting_date)
    if not date:
        frappe.throw("Chọn ngày giao việc.")
    # Farm lock serializes concurrent quick submissions and protects duplicate checks.
    lock("Farm", farm)
    lines = _planned_lines(farm, work_team, items, date)
    existing = frappe.get_list("Daily Work Plan", filters={
        "farm": farm, "posting_date": date, "docstatus": 1
    }, fields=["name"], limit_page_length=10000)
    requested = {(r["farm_plot"], r["crop_cycle"], r["sucker_selection_batch"] or "",
                  r["work_type"], r["work_team"], r["payment_mode"]) for r in lines}
    for row in existing:
        plan = frappe.get_doc("Daily Work Plan", row.name)
        for line in plan.lines:
            key = (line.farm_plot, line.crop_cycle, line.sucker_selection_batch or "",
                   line.work_type, line.work_team, line.payment_mode)
            if key in requested:
                frappe.throw("Việc đã được giao trong ngày tại thửa " +
                             (line.farm_plot or "") + ". Mở kế hoạch cũ để xem.")
    pending_approval = any(row["requires_approval"] for row in lines)
    reason = str(rate_request_reason or "").strip()
    if pending_approval and not reason:
        frappe.throw("Nhập lý do đề nghị giá khoán cao hơn niêm yết.")
    if len(reason) > 500:
        frappe.throw("Lý do đề nghị tối đa 500 ký tự.")
    doc = frappe.get_doc(dict(doctype="Daily Work Plan", farm=farm,
        company=farm_doc.company, posting_date=date,
        rate_approval_state="Pending" if pending_approval else "Not Required",
        rate_requested_by=frappe.session.user,
        rate_request_reason=reason if pending_approval else "",
        lines=[{k: v for k, v in row.items() if k not in (
            "plot_code", "work_name", "productivity_per_workday", "piecework_rate", "required_workdays", "estimated_piecework_amount", "materials", "requires_approval")} for row in lines]))
    doc.insert()
    if not pending_approval:
        doc.submit()
    return dict(plan=doc.name, count=len(lines),
                farm=farm, posting_date=str(date),
                status="Pending" if pending_approval else "Submitted")