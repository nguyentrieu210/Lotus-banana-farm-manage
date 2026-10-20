"""Print material purchase/issue proposals using Lotus farm's Excel-approved layout.

A Material Request is a *proposal*, not an approved Purchase Order or a Stock Entry.
Only fields stored on that request, or live inventory visibly marked as such, are shown.
"""
from base64 import b64encode
import json
from pathlib import Path
import re
from urllib.parse import urlencode

import frappe
from frappe.utils import flt, getdate, strip_html

no_cache = 1


def _number(value):
    return format(flt(value, 3), ",.3f").rstrip("0").rstrip(".").replace(",", "_").replace(".", ",").replace("_", ".")


def _money_words_vn(value):
    """Whole-VND amount in words; never estimate when any price is missing."""
    amount = int(round(flt(value)))
    if amount == 0:
        return "Không đồng"
    digits = "không một hai ba bốn năm sáu bảy tám chín".split()

    def group_text(n, full=False):
        hundreds, tens, units = n // 100, (n // 10) % 10, n % 10
        pieces = []
        if hundreds or full:
            pieces.extend((digits[hundreds], "trăm"))
        if tens >= 2:
            pieces.extend((digits[tens], "mươi"))
        elif tens == 1:
            pieces.append("mười")
        elif units and (hundreds or full):
            pieces.append("linh")
        if units:
            if tens >= 2 and units == 1:
                pieces.append("mốt")
            elif tens >= 1 and units == 5:
                pieces.append("lăm")
            else:
                pieces.append(digits[units])
        return " ".join(pieces)

    groups = []
    while amount:
        groups.append(amount % 1000)
        amount //= 1000
    suffix = ("", "nghìn", "triệu", "tỷ", "nghìn tỷ", "triệu tỷ")
    parts = []
    for i in reversed(range(len(groups))):
        if groups[i]:
            parts.append(" ".join(x for x in (group_text(groups[i], bool(parts)), suffix[i]) if x))
    words = " ".join(parts)
    return words[0].upper() + words[1:] + " đồng"


def _user_name(user):
    return frappe.db.get_value("User", user, "full_name") or user or ""


def _safe_signature(doc):
    """Use only an actual, immutable signature event attached to this request."""
    events = frappe.get_all(
        "Lotus Signature Event",
        filters={"document_type": doc.doctype, "document_name": doc.name, "action": "APPROVE"},
        fields=["actor", "signed_at", "details"],
        order_by="signed_at desc", limit_page_length=1,
    )
    if not events:
        return {"name": "", "time": "", "image": ""}
    event = events[0]
    try:
        file_name = (json.loads(event.details or "{}") or {}).get("signature_file")
    except (TypeError, ValueError):
        file_name = None
    result = {"name": _user_name(event.actor), "time": str(event.signed_at or ""), "image": ""}
    if file_name:
        file = frappe.get_doc("File", file_name)
        if (file.is_private and file.attached_to_doctype == doc.doctype
                and file.attached_to_name == doc.name):
            result["image"] = "data:image/png;base64," + b64encode(
                file.get_content(encodings=[])
            ).decode("ascii")
    return result


def _farm_requirement_context(context, name):
    """Lotus planning requirement: proposed issue quantities, never proof of stock issue."""
    doc = frappe.get_doc("Material Requirement", name)
    doc.check_permission("read")
    doc.check_permission("print")
    farm = frappe.get_doc("Farm", doc.farm)
    farm.check_permission("read")
    context.farm_label = farm.get("farm_name") or farm.name
    context.company_label = frappe.get_cached_value("Company", doc.company, "company_name") or doc.company
    context.purchase = False
    context.title = "PHIẾU ĐỀ XUẤT CẤP VẬT TƯ"
    context.document = doc
    context.created_at = getdate(doc.get("posting_date") or doc.creation).strftime("%d/%m/%Y")
    context.created_by = _user_name(doc.owner)
    context.department = frappe.db.get_value(
        "Employee", {"user_id": doc.owner, "company": doc.company, "status": "Active"}, "department"
    ) or ""
    plan_row = frappe.db.get_value(
        "Daily Work Plan Line", doc.work_plan_line,
        ["work_type", "planned_qty", "uom"], as_dict=True,
    ) if doc.work_plan_line else None
    work_name = frappe.db.get_value("Work Type", plan_row.work_type, "work_name") if plan_row and plan_row.work_type else ""
    context.reason = ("Vật tư cho công việc: " + work_name) if work_name else "Vật tư theo kế hoạch sản xuất"
    context.warehouse = "Chưa xác định kho cấp trên phiếu nhu cầu"
    block = frappe.db.get_value("Farm Block", doc.farm_block, "block_code") if doc.farm_block else ""
    scale = (f"{_number(plan_row.planned_qty)} {plan_row.uom or ''}" if plan_row else "")
    context.rows = []
    for line in doc.lines:
        item = frappe.get_doc("Item", line.item)
        item.check_permission("read")
        context.rows.append(frappe._dict(
            item_name=item.item_name or line.item,
            specification=strip_html(item.get("description") or "").strip(),
            item_code=line.item,
            uom={"Nos": "Cái", "Litre": "Lít", "Tonne": "Tấn", "Kg": "kg"}.get(line.uom, line.uom),
            stock=None,  # No source warehouse is selected for this planning requirement.
            qty=flt(line.required_qty),
            norm=flt(line.norm_qty),
            issued_qty=None,
            needed_date=context.created_at,
            warehouse="",
            area=block,
            scale=scale,
            purpose=work_name,
            notes="",
            supplier="",
            price=None,
            amount=None,
        ))
    context.number = _number
    context.total = 0
    context.all_priced = False
    context.amount_words = ""
    context.approval = _safe_signature(doc) if doc.docstatus == 1 else {"name": "", "time": "", "image": ""}
    context.state = "Đã lập nhu cầu vật tư" if doc.docstatus == 1 else "Bản nháp"
    context.logo_data = "data:image/png;base64," + b64encode(
        Path(frappe.get_app_path("lotus_farm", "public", "images", "lotus-agritech-header-v2.png")).read_bytes()
    ).decode("ascii")
    context.pdf_url = "/api/method/lotus_farm.www.lotus_material_proposal_print.download_pdf?" + urlencode(
        {"doctype": doc.doctype, "name": doc.name}
    )
    context.no_cache = 1


def get_context(context, name=None, doctype=None):
    if frappe.session.user == "Guest":
        frappe.throw("Vui lòng đăng nhập để in phiếu đề xuất vật tư.", frappe.PermissionError)
    name = name or frappe.form_dict.get("name")
    if not name:
        frappe.throw("Cần chọn số phiếu đề xuất vật tư.")
    doctype = doctype or frappe.form_dict.get("doctype") or "Material Request"
    if doctype == "Material Requirement":
        return _farm_requirement_context(context, name)
    if doctype != "Material Request":
        frappe.throw("Chỉ hỗ trợ phiếu đề xuất vật tư.", frappe.PermissionError)
    doc = frappe.get_doc("Material Request", name)
    doc.check_permission("read")
    doc.check_permission("print")
    if doc.material_request_type not in ("Purchase", "Material Issue"):
        frappe.throw("Chỉ in phiếu đề xuất mua hoặc cấp vật tư.", frappe.PermissionError)

    purchase = doc.material_request_type == "Purchase"
    farm = frappe.get_cached_value("Company", doc.company, "lotus_print_farm") or ""
    project = frappe.get_cached_value("Company", doc.company, "lotus_print_project") or ""
    label = farm or re.sub(r"^\s*dự\s+án\s+chuối\b", "Vườn chuối", project, flags=re.I)
    context.farm_label = label or frappe.get_cached_value("Company", doc.company, "company_name") or doc.company
    context.company_label = frappe.get_cached_value("Company", doc.company, "company_name") or doc.company
    context.purchase = purchase
    context.title = "PHIẾU ĐỀ XUẤT MUA VẬT TƯ" if purchase else "PHIẾU ĐỀ XUẤT CẤP VẬT TƯ"
    context.document = doc
    context.created_at = getdate(doc.get("transaction_date") or doc.creation).strftime("%d/%m/%Y")
    context.created_by = _user_name(doc.owner)
    context.department = frappe.db.get_value(
        "Employee", {"user_id": doc.owner, "company": doc.company, "status": "Active"}, "department"
    ) or doc.get("department") or ""
    context.reason = strip_html(doc.get("lotus_request_note") or doc.get("remarks") or "").strip()
    context.warehouse = ", ".join(sorted({
        r.warehouse for r in doc.items if r.warehouse
    }))
    context.rows = []
    total = 0
    all_priced = True
    for item_row in doc.items:
        item = frappe.get_doc("Item", item_row.item_code)
        item.check_permission("read")
        if item_row.warehouse:
            frappe.get_doc("Warehouse", item_row.warehouse).check_permission("read")
        stock = None
        if item_row.warehouse:
            stock_raw = frappe.db.get_value(
                "Bin", {"item_code": item_row.item_code, "warehouse": item_row.warehouse},
                "actual_qty",
            )
            if stock_raw is not None:
                stock = flt(stock_raw) / (flt(item_row.conversion_factor) or 1)
        unit_price = flt(item_row.get("rate"))
        if unit_price <= 0:
            unit_price = None
            all_priced = False
        amount = flt(item_row.qty) * unit_price if unit_price is not None else None
        if amount is not None:
            total += amount
        context.rows.append(frappe._dict(
            item_name=item_row.item_name or item.item_name,
            specification=strip_html(item_row.get("description") or "").strip(),
            item_code=item_row.item_code,
            uom={"Nos": "Cái", "Litre": "Lít", "Tonne": "Tấn", "Kg": "kg", "Millilitre": "ml"}.get(item_row.uom, item_row.uom),
            stock=stock,
            qty=flt(item_row.qty),
            norm=item_row.get("lotus_norm_qty"),
            issued_qty=None,  # Material Request does not prove the warehouse has issued goods.
            needed_date=getdate(item_row.schedule_date or doc.schedule_date).strftime("%d/%m/%Y"),
            warehouse=item_row.warehouse or "",
            area=item_row.get("lotus_farm_block") or "",
            scale=item_row.get("lotus_work_scope") or "",
            purpose=strip_html(item_row.get("lotus_purpose") or "").strip(),
            notes=strip_html(item_row.get("lotus_notes") or "").strip(),
            supplier=item_row.get("supplier") or "",
            price=unit_price,
            amount=amount,
        ))
    context.number = _number
    context.total = total
    context.all_priced = bool(context.rows and all_priced)
    context.amount_words = _money_words_vn(total) if context.all_priced else ''
    context.approval = _safe_signature(doc) if doc.docstatus == 1 else {"name": "", "time": "", "image": ""}
    context.state = "Đã gửi đề xuất" if doc.docstatus == 1 else "Bản nháp"
    from pathlib import Path
    context.logo_data = "data:image/png;base64," + b64encode(
        Path(frappe.get_app_path("lotus_farm", "public", "images", "lotus-agritech-header-v2.png")).read_bytes()
    ).decode("ascii")
    context.pdf_url = "/api/method/lotus_farm.www.lotus_material_proposal_print.download_pdf?" + urlencode({"name": doc.name})
    context.no_cache = 1


@frappe.whitelist()
def download_pdf(name, doctype=None):
    from frappe.utils.pdf import get_pdf
    context = frappe._dict()
    get_context(context, name=name, doctype=doctype)
    html = frappe.render_template("lotus_farm/www/lotus_material_proposal_print.html", context)
    content = get_pdf(html, options={"page-size": "A4", "orientation": "Landscape", "print-media-type": None})
    prefix = "de-xuat-mua-" if context.purchase else "de-xuat-cap-"
    frappe.local.response.filename = prefix + re.sub(r"[^A-Za-z0-9._-]+", "_", name)[:80] + ".pdf"
    frappe.local.response.filecontent = content
    frappe.local.response.type = "pdf"
    frappe.local.response.display_content_as = "attachment"