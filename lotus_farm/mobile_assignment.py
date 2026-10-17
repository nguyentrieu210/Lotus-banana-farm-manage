"""Phone assignment at Farm Block (Lô lớn) level.

No splitting work quantities across small plots. Existing historical plot links
remain in the database and are not modified by this endpoint.
"""
import frappe
from frappe.utils import getdate, nowdate

from lotus_farm.controls import require_role, lock
from lotus_farm.rules import RuleError, quantity


def permitted_farm(farm):
    require_role("Lotus Farm Manager", "Lotus Field Supervisor")
    if not farm:
        frappe.throw("Chọn vườn trước.")
    doc = frappe.get_doc("Farm", farm)
    doc.check_permission("read")
    if not doc.active:
        frappe.throw("Vườn không còn hoạt động.")
    return doc


@frappe.whitelist()
def options(farm):
    """Only active large blocks, teams, and work types are shown."""
    permitted_farm(farm)
    return dict(
        farm=farm,
        blocks=frappe.get_list(
            "Farm Block", filters={"farm": farm, "active": 1},
            fields=["name", "block_code", "block_name", "area_ha"],
            order_by="block_code asc", limit_page_length=1000),
        teams=frappe.get_list(
            "Work Team", filters={"farm": farm, "active": 1},
            fields=["name", "team_code", "team_name"],
            order_by="team_code asc", limit_page_length=1000),
        works=frappe.get_list(
            "Work Type", filters={"active": 1},
            fields=["name", "work_code", "work_name", "uom", "productivity_per_workday",
                    "piecework_rate", "allow_daywork", "allow_piecework"],
            order_by="work_name asc", limit_page_length=1000),
    )


def _approved_material_norm(farm, work_type, posting_date):
    from lotus_farm.daily_operations import applicable_norm
    matches = frappe.get_list(
        "Material Norm Profile",
        filters={"farm": farm, "work_type": work_type, "approval_state": "Approved",
                 "valid_from": ["<=", posting_date], "valid_to": [">=", posting_date]},
        fields=["name"], limit_page_length=2)
    if len(matches) > 1:
        frappe.throw("Nhiều định mức vật tư cùng hiệu lực. Cần kiểm tra trước khi giao việc.")
    return applicable_norm(matches[0].name, farm, work_type, posting_date) if matches else None


def _planned_lines(farm, team, items, posting_date=None):
    if isinstance(items, str):
        items = frappe.parse_json(items)
    if not isinstance(items, list) or not 1 <= len(items) <= 50:
        frappe.throw("Nhập từ 1 đến 50 công việc.")
    from lotus_farm.mobile_access import require_team
    require_team(farm, team)
    team_doc = frappe.get_doc("Work Team", team)
    team_doc.check_permission("read")
    if team_doc.farm != farm or not team_doc.active:
        frappe.throw("Tổ được giao phải đang hoạt động trong vườn.")

    work_cache = {}
    block_cache = {}
    norm_cache = {}
    gathered = {}
    posting_date = getdate(posting_date or nowdate())
    from lotus_farm.labor_pricing import labor_settings, planned_labor
    from lotus_farm.rate_approval import resolve_rate

    for item in items:
        if not isinstance(item, dict) or set(item) - {
            "location", "work_type", "qty", "payment_mode", "piecework_rate"
        }:
            frappe.throw("Dòng giao việc có trường không hợp lệ.")
        location = item.get("location")
        if not isinstance(location, str) or not location.startswith("block:"):
            frappe.throw("Chỉ được giao việc theo Lô lớn, không chọn thửa nhỏ.")
        target = location[6:]
        if not target:
            frappe.throw("Chọn Lô lớn.")
        if target not in block_cache:
            block = frappe.get_doc("Farm Block", target)
            block.check_permission("read")
            if block.farm != farm or not block.active:
                frappe.throw("Lô không thuộc vườn đang chọn hoặc đã ngừng hoạt động.")
            block_cache[target] = block
        block = block_cache[target]

        work_name = item.get("work_type")
        if not work_name:
            frappe.throw("Chọn công việc.")
        if work_name not in work_cache:
            work = frappe.get_doc("Work Type", work_name)
            work.check_permission("read")
            if not work.active:
                frappe.throw("Công việc đã ngừng áp dụng.")
            work_cache[work_name] = work
        work = work_cache[work_name]
        if work_name not in norm_cache:
            norm_cache[work_name] = _approved_material_norm(farm, work_name, posting_date)

        try:
            payment = labor_settings(
                work.allow_daywork, work.allow_piecework,
                work.productivity_per_workday, work.piecework_rate,
                item.get("payment_mode"))
            price = resolve_rate(
                work.piecework_rate, item.get("piecework_rate"), payment["mode"])
            payment["piecework_rate"] = price["rate"]
            total = quantity(item.get("qty"), "Khối lượng giao", positive=True)
        except (RuleError, ValueError) as exc:
            frappe.throw(str(exc))
        if total > 1000000:
            frappe.throw("Khối lượng quá lớn; hãy chia thành nhiều lần giao.")
        if work.uom in ("Bunch", "Tree", "Nos") and total != total.to_integral_value():
            frappe.throw("Công việc tính bằng buồng/cây phải giao số nguyên.")

        key = (block.name, work.name, payment["mode"])
        if key not in gathered:
            gathered[key] = dict(
                farm=farm, farm_block=block.name,
                farm_plot=None, crop_cycle=None, sucker_selection_batch=None,
                block_code=block.block_code, work_type=work.name,
                work_name=work.work_name, uom=work.uom,
                productivity_per_workday=payment["productivity"],
                piecework_rate=payment["piecework_rate"],
                payment_mode=payment["mode"],
                list_piecework_rate=price["list_rate"],
                requested_piecework_rate=price["rate"],
                requires_approval=price["requires_approval"],
                planned_qty=0.0, work_team=team_doc.name)
        if gathered[key]["requested_piecework_rate"] != price["rate"]:
            frappe.throw("Cùng công việc và Lô lớn không được có hai đơn giá trong một phiếu.")
        gathered[key]["planned_qty"] += float(total)

    from lotus_farm.operations_rules import material_needed
    for row in gathered.values():
        row.update(planned_labor(
            row["planned_qty"],
            dict(productivity=row["productivity_per_workday"],
                 piecework_rate=row["piecework_rate"])))
        norm = norm_cache[row["work_type"]]
        row["norm_profile"] = norm.name if norm else None
        row["norm_version"] = norm.version if norm else 0
        row["materials"] = (
            [dict(item=source.item, uom=source.uom,
                  required_qty=material_needed(
                      row["planned_qty"], source.norm_qty,
                      source.basis_qty, source.frequency, source.conversion_factor))
             for source in norm.lines]
            if norm else [])
    return list(gathered.values())


@frappe.whitelist(methods=["POST"])
def preview(farm, work_team, items, posting_date=None):
    permitted_farm(farm)
    lines = _planned_lines(farm, work_team, items, posting_date)
    materials = {}
    missing = set()
    for line in lines:
        if not line["norm_profile"]:
            missing.add(line["work_name"])
        for material in line["materials"]:
            key = (material["item"], material["uom"])
            materials[key] = materials.get(key, 0) + material["required_qty"]
    return dict(
        lines=lines, approval_required=any(row["requires_approval"] for row in lines),
        materials=[dict(item=key[0], uom=key[1], required_qty=round(qty, 6))
                   for key, qty in sorted(materials.items())],
        missing_norms=sorted(missing),
        note="Một dòng công việc ứng với một Lô lớn, không chia xuống thửa.")


@frappe.whitelist(methods=["POST"])
def create(farm, posting_date, work_team, items, rate_request_reason=None):
    farm_doc = permitted_farm(farm)
    date = getdate(posting_date)
    if not date:
        frappe.throw("Chọn ngày giao việc.")
    lock("Farm", farm)
    lines = _planned_lines(farm, work_team, items, date)
    existing = frappe.get_all(
        "Daily Work Plan",
        filters={"farm": farm, "posting_date": date, "docstatus": 1},
        fields=["name"], limit_page_length=10000)
    requested = {
        (row["farm_block"], row["work_type"], row["work_team"], row["payment_mode"])
        for row in lines
    }
    for item in existing:
        doc = frappe.get_doc("Daily Work Plan", item.name)
        for line in doc.lines:
            key = (line.farm_block, line.work_type, line.work_team, line.payment_mode)
            if key in requested:
                code = frappe.db.get_value("Farm Block", line.farm_block, "block_code") or line.farm_block
                frappe.throw("Việc đã được giao trong ngày tại Lô " + str(code) + ". Mở phiếu cũ để xem.")
    pending = any(row["requires_approval"] for row in lines)
    reason = str(rate_request_reason or "").strip()
    if pending and not reason:
        frappe.throw("Nhập lý do đề nghị đơn giá khoán cao hơn niêm yết.")
    if len(reason) > 500:
        frappe.throw("Lý do đề nghị tối đa 500 ký tự.")
    doc = frappe.get_doc(dict(
        doctype="Daily Work Plan", farm=farm, company=farm_doc.company,
        posting_date=date, rate_approval_state="Pending" if pending else "Not Required",
        rate_requested_by=frappe.session.user,
        rate_request_reason=reason if pending else "",
        lines=[
            {key: value for key, value in row.items()
             if key not in ("block_code", "work_name", "productivity_per_workday",
                            "piecework_rate", "required_workdays",
                            "estimated_piecework_amount", "materials", "requires_approval")}
            for row in lines]))
    from lotus_farm.mobile_access import is_manager
    if not is_manager():
        # Only this verified, team-scoped endpoint can create for a supervisor.
        doc.flags.ignore_permissions = True
    doc.insert(ignore_permissions=not is_manager())
    if not pending:
        doc.submit()
    return dict(
        plan=doc.name, count=len(lines), farm=farm, posting_date=str(date),
        status="Pending" if pending else "Submitted")
