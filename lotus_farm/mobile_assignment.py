"""Minimal phone task assignment. One location picker: Block OR Plot."""
import frappe
from frappe.utils import getdate, nowdate
from lotus_farm.controls import require_role, lock, command
from lotus_farm.assignment_pay import price_for
from lotus_farm.piece_pay import terms
from lotus_farm.mobile_assignment_rules import split_quantity
from lotus_farm.rules import RuleError, quantity
from lotus_farm.operations_rules import material_needed


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
                              fields=["name", "work_code", "work_name", "uom", "productivity_per_workday", "payment_basis"],
                              limit_page_length=1000, order_by="work_name asc"),
    )


def _planned_lines(farm, team, items, posting_date=None):
    posting_date = getdate(posting_date or nowdate())
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
        if not isinstance(item, dict) or set(item) - {"location", "work_type", "qty", "payment_basis", "agreed_unit_price", "acceptance_criteria", "price_reason"}:
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
        basis = item.get('payment_basis') or work.get('payment_basis') or 'Daywork'
        if basis not in ('Piece', 'Daywork'):
            frappe.throw('Chọn công nhật hoặc khoán sản lượng.')
        pay = dict(payment_basis=basis, acceptance_criteria=(item.get('acceptance_criteria') or '').strip(),
                   price_reason=(item.get('price_reason') or '').strip())
        if basis == 'Piece':
            if not pay['acceptance_criteria']:
                frappe.throw('Ghi tiêu chuẩn đạt cho việc khoán.')
            rate = price_for(farm, work.name, work.uom, posting_date)
            try:
                pay.update(terms(rate.unit_price, item.get('agreed_unit_price'), item.get('qty'), pay['price_reason']))
            except RuleError as exc:
                frappe.throw(str(exc))
            pay['piece_rate'] = rate.name
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
                    planned_qty=0.0, work_team=team_doc.name, **pay)
            elif any(gathered[key].get(f) != pay.get(f) for f in ("payment_basis", "agreed_unit_price", "acceptance_criteria", "price_reason")):
                frappe.throw("Cùng thửa và công việc phải dùng cùng giá, cách trả công và tiêu chuẩn.")
            gathered[key]["planned_qty"] += float(planned)
    if len(gathered) > 200:
        frappe.throw("Quá nhiều thửa; hãy chia kế hoạch.")
    for row in gathered.values():
        profiles = frappe.get_list('Material Norm Profile', filters={'farm': farm,
            'work_type': row['work_type'], 'approval_state': 'Approved',
            'valid_from': ['<=', posting_date], 'valid_to': ['>=', posting_date]},
            pluck='name', limit_page_length=2)
        if len(profiles) > 1:
            frappe.throw('Có nhiều định mức vật tư cùng hiệu lực; cần kiểm tra danh mục.')
        row['norm_profile'] = profiles[0] if profiles else None
        if row['payment_basis'] == 'Piece':
            row['estimated_amount'] = terms(row['listed_unit_price'], row['agreed_unit_price'], row['planned_qty'], row['price_reason'])['estimated_amount']
    return list(gathered.values())


@frappe.whitelist(methods=["POST"])
def preview(farm, work_team, items, posting_date=None):
    permitted_farm(farm)
    lines = _planned_lines(farm, work_team, items, posting_date)
    materials = {}
    for row in lines:
        if not row['norm_profile']:
            continue
        profile = frappe.get_doc('Material Norm Profile', row['norm_profile'])
        profile.check_permission('read')
        for material in profile.lines:
            key = (material.item, material.uom)
            materials[key] = materials.get(key, 0) + material_needed(row['planned_qty'],
                material.norm_qty, material.basis_qty, material.frequency, material.conversion_factor)
    return dict(lines=lines,
                required_workdays=sum(r['planned_qty']/r['productivity_per_workday'] for r in lines),
                materials=[dict(item=k[0],uom=k[1],qty=v) for k,v in materials.items()],
                missing_norms=sorted({r['work_name'] for r in lines if not r['norm_profile']}),
                note="Chọn lô sẽ chia chỉ tiêu theo diện tích các thửa; xem lại trước khi giao.")


@frappe.whitelist(methods=["POST"])
def create(farm, posting_date, work_team, items):
    farm_doc = permitted_farm(farm)
    date = getdate(posting_date)
    if not date:
        frappe.throw("Chọn ngày giao việc.")
    # Farm lock serializes concurrent quick submissions and protects duplicate checks.
    lock("Farm", farm)
    lines = _planned_lines(farm, work_team, items, date)
    existing = frappe.get_list("Daily Work Plan", filters={
        "farm": farm, "posting_date": date, "docstatus": ["<", 2]
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
    if doc.price_approval_state != "Pending":
        doc.submit()
    return dict(plan=doc.name, count=len(lines),
                farm=farm, posting_date=str(date), status="Pending" if doc.docstatus == 0 else "Submitted")



@frappe.whitelist()
def quote(farm, work_type, posting_date):
    permitted_farm(farm)
    work = frappe.get_doc('Work Type', work_type)
    work.check_permission('read')
    rate = price_for(farm, work_type, work.uom, getdate(posting_date))
    return dict(piece_rate=rate.name, listed_unit_price=rate.unit_price, uom=rate.uom)


@frappe.whitelist()
def pending_prices(farm):
    permitted_farm(farm)
    return frappe.get_list('Daily Work Plan', filters={'farm': farm, 'docstatus': 0,
        'price_approval_state': 'Pending'}, fields=['name', 'posting_date', 'owner'],
        order_by='creation desc', limit_page_length=100)


@frappe.whitelist(methods=['POST'])
def approve_price(plan):
    doc = frappe.get_doc('Daily Work Plan', plan)
    permitted_farm(doc.farm)
    lock('Farm', doc.farm)
    lock('Daily Work Plan', plan)
    doc.reload()
    doc.check_permission('write')
    doc.check_permission('submit')
    if doc.docstatus != 0 or doc.price_approval_state != 'Pending':
        frappe.throw('Kế hoạch không còn chờ duyệt giá.')
    if frappe.session.user in (doc.owner, doc.modified_by):
        frappe.throw('Quản lý khác người lập/sửa gần nhất phải duyệt giá vượt niêm yết.')
    for name in frappe.get_all('Daily Work Plan', filters={'farm': doc.farm,
            'posting_date': doc.posting_date, 'docstatus': 1}, pluck='name'):
        other = frappe.get_doc('Daily Work Plan', name)
        keys = {(r.farm_plot, r.crop_cycle, r.sucker_selection_batch or '', r.work_type, r.work_team) for r in other.lines}
        if any((r.farm_plot, r.crop_cycle, r.sucker_selection_batch or '', r.work_type, r.work_team) in keys for r in doc.lines):
            frappe.throw('Việc đã được giao trong kế hoạch khác. Kiểm tra trước khi duyệt.')
    with command(doc, 'approve_assignment_price'):
        doc.submit()
    return dict(plan=doc.name, status='Submitted')
