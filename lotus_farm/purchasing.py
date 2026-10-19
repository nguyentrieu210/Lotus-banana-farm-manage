"""Lotus purchasing PWA: suppliers, purchase requests, approval and delivery tracking.

All approved orders use ERPNext Purchase Order, not a second stock ledger.
"""
import frappe
from frappe.utils import flt, nowdate, now_datetime, getdate
from lotus_farm.warehouse import _company, _warehouse, _number
from lotus_farm.warehouse_buying_lite import _po, _lines, _payload, _state, _summary

PENDING = "Chờ duyệt"
DRAFT = "Nháp"
REJECTED = "Từ chối"


def access():
    if frappe.session.user == "Guest":
        frappe.throw("Vui lòng đăng nhập.", frappe.AuthenticationError)
    for doctype in ("Company", "Warehouse", "Item"):
        if not frappe.has_permission(doctype, "read"):
            frappe.throw("Không có quyền xem " + doctype, frappe.PermissionError)
    if not any(frappe.has_permission(dt, "read") for dt in ("Purchase Order", "Material Request")):
        frappe.throw("Không có quyền sử dụng Mua hàng.", frappe.PermissionError)


def _approver():
    roles = set(frappe.get_roles(frappe.session.user))
    return "Lotus Purchase Approver" in roles or frappe.session.user == "Administrator"


def can_approve(doc):
    return bool(doc.docstatus == 0 and doc.get("lotus_approval_status") == PENDING
                and doc.owner != frappe.session.user
                and doc.get("lotus_requested_by") != frappe.session.user
                and _approver()
                and doc.has_permission("submit"))


def _ensure_version(doc, modified):
    if not modified or str(doc.modified) != str(modified) or doc.docstatus != 0:
        frappe.throw("Đơn đã thay đổi. Tải lại đơn trước khi thao tác.")


def check_submission(doc, method=None):
    """Protect Lotus purchase orders even if users call Frappe's generic submit endpoint."""
    saved_state = frappe.db.get_value("Purchase Order", doc.name, "lotus_approval_status") if doc.name else None
    if saved_state or doc.get("lotus_approval_status") or doc.get("lotus_purchase_mode"):
        if saved_state != PENDING or doc.get("lotus_approval_status") != PENDING:
            frappe.throw("Đơn mua phải được gửi duyệt trước khi xác nhận.")
        if doc.owner == frappe.session.user or doc.get("lotus_requested_by") == frappe.session.user:
            frappe.throw("Người lập hoặc trình đơn không được tự duyệt.", frappe.PermissionError)
        if not _approver():
            frappe.throw("Chỉ người có quyền duyệt mua mới được xác nhận.", frappe.PermissionError)


@frappe.whitelist()
def bootstrap():
    access()
    from frappe.sessions import get_csrf_token
    return dict(user=frappe.session.user, csrf_token=get_csrf_token(), today=nowdate(),
                companies=frappe.get_list("Company", fields=["name"], limit_page_length=1000),
                can_create=frappe.has_permission("Purchase Order", "create"),
                can_approve=_approver() and frappe.has_permission("Purchase Order", "submit"),
                can_supplier=frappe.has_permission("Supplier", "create"),
                can_request=frappe.has_permission("Material Request", "create"))


@frappe.whitelist()
def catalog(company):
    access()
    _company(company)
    from lotus_farm.warehouse_buying_lite import setup
    return setup(company)


@frappe.whitelist()
def requests(company):
    access()
    _company(company)
    if not frappe.has_permission("Material Request", "read"):
        return []
    found = frappe.get_list("Material Request",
        filters={"company": company, "material_request_type": "Purchase", "docstatus": 1,
                 "status": ["not in", ["Stopped", "Closed", "Cancelled"]]},
        fields=["name", "transaction_date", "schedule_date", "owner"],
        order_by="modified desc", limit_page_length=200)
    result = []
    for x in found:
        doc = frappe.get_doc("Material Request", x.name)
        doc.check_permission("read")
        waiting = []
        for row in doc.items:
            remaining = max(0, flt(row.stock_qty) - flt(row.ordered_qty))
            if remaining > 0.000001 and row.warehouse:
                waiting.append(dict(item=row.item_code, item_name=row.item_name, warehouse=row.warehouse,
                                    qty=remaining / (flt(row.conversion_factor) or 1),
                                    uom=row.uom, material_request=doc.name, material_request_item=row.name))
        if waiting:
            result.append(dict(name=doc.name, date=str(doc.transaction_date),
                               expected_date=str(doc.schedule_date), owner=doc.owner, items=waiting))
    return result


@frappe.whitelist(methods=["POST"])
def create_request(company, warehouse, expected_date, items, notes=""):
    """Stock staff request goods; this does not create or approve a Purchase Order."""
    access()
    _company(company)
    _warehouse(warehouse, company)
    if not frappe.has_permission("Material Request", "create") or not frappe.has_permission("Material Request", "submit"):
        frappe.throw("Tài khoản chưa có quyền gửi đề nghị mua.", frappe.PermissionError)
    from lotus_farm.warehouse_buying_lite import _date
    expected = _date(expected_date, "ngày giao dự kiến")
    if isinstance(items, str):
        items = frappe.parse_json(items)
    if not isinstance(items, list) or not 1 <= len(items) <= 100:
        frappe.throw("Chọn từ 1 đến 100 mặt hàng.")
    lines = []
    for row in items:
        if not isinstance(row, dict):
            frappe.throw("Mặt hàng không hợp lệ.")
        item = frappe.get_doc("Item", row.get("item"))
        item.check_permission("read")
        if item.disabled or not item.is_stock_item:
            frappe.throw("Mặt hàng không còn sử dụng.")
        qty = _number(row.get("qty"), "Số lượng")
        uom = row.get("uom") or item.stock_uom
        conversion = next((u for u in item.uoms if u.uom == uom), None)
        factor = 1 if uom == item.stock_uom else flt(conversion.conversion_factor) if conversion else 0
        if factor <= 0:
            frappe.throw("Đơn vị chưa có quy đổi: " + item.item_name)
        lines.append(dict(item_code=item.name, qty=qty, uom=uom, stock_uom=item.stock_uom,
                          conversion_factor=factor, warehouse=warehouse,
                          schedule_date=expected))
    doc = frappe.get_doc(dict(doctype="Material Request", material_request_type="Purchase",
                              company=company, transaction_date=nowdate(), schedule_date=expected,
                              items=lines))
    doc.insert()
    doc.submit()  # Submitted MR is a request only; never an approved PO.
    if notes and frappe.get_meta("Material Request").has_field("lotus_request_note"):
        doc.db_set("lotus_request_note", str(notes)[:500])
    return dict(name=doc.name, docstatus=doc.docstatus)


@frappe.whitelist(methods=["POST"])
def request_approval(name, modified):
    access()
    doc = _po(name)
    doc.check_permission("write")
    _ensure_version(doc, modified)
    if doc.get("lotus_approval_status") not in (None, "", DRAFT, REJECTED):
        frappe.throw("Đơn đã được gửi duyệt.")
    if not doc.items or any(flt(r.qty) <= 0 or flt(r.rate) <= 0 for r in doc.items):
        frappe.throw("Cần có số lượng và đơn giá hợp lệ trước khi gửi duyệt.")
    doc.lotus_approval_status = PENDING
    doc.lotus_requested_by = frappe.session.user
    doc.lotus_requested_at = now_datetime()
    doc.lotus_reject_reason = ""
    doc.save()
    return dict(name=doc.name, status=PENDING, modified=str(doc.modified))


@frappe.whitelist(methods=["POST"])
def approve_order(name, modified):
    access()
    from lotus_farm.controls import lock
    doc = _po(name)
    lock("Purchase Order", name)
    doc.reload()
    _ensure_version(doc, modified)
    if not can_approve(doc):
        frappe.throw("Không được duyệt đơn này. Kiểm tra quyền và người lập đơn.", frappe.PermissionError)
    doc.lotus_approved_by = frappe.session.user
    doc.lotus_approved_at = now_datetime()
    doc.submit()
    from lotus_farm.digital_signature import archive_approved_purchase_pdf
    archive_approved_purchase_pdf(doc)
    return dict(name=doc.name, status=_state(doc), docstatus=doc.docstatus)


@frappe.whitelist(methods=["POST"])
def reject_order(name, modified, reason):
    access()
    from lotus_farm.controls import lock
    reason = str(reason or "").strip()
    if not 3 <= len(reason) <= 500:
        frappe.throw("Cần ghi lý do từ chối (3–500 ký tự).")
    doc = _po(name)
    lock("Purchase Order", name)
    doc.reload()
    _ensure_version(doc, modified)
    if not can_approve(doc):
        frappe.throw("Không được từ chối đơn này.", frappe.PermissionError)
    doc.check_permission("write")
    doc.lotus_approval_status = REJECTED
    doc.lotus_reject_reason = reason
    doc.save()
    return dict(name=doc.name, status=REJECTED, modified=str(doc.modified))


@frappe.whitelist()
def orders(company, status=None, search=None):
    access()
    _company(company)
    if not frappe.has_permission("Purchase Order", "read"):
        return []
    found = frappe.get_list("Purchase Order", filters={"company": company},
        fields=["name"], order_by="modified desc", limit_page_length=500)
    result = []
    for row in found:
        doc = _po(row.name, company)
        out = _summary(doc)
        out.update(approval_status="Đã hủy" if doc.docstatus == 2 else
                   ((doc.get("lotus_approval_status") or DRAFT) if doc.docstatus == 0 else "Đã duyệt"),
                   owner=doc.owner, amount=flt(doc.grand_total), can_approve=can_approve(doc))
        if status and status != "Tất cả" and out["approval_status"] != status:
            continue
        if search and str(search).casefold() not in (out["name"] + " " + out["supplier_name"]).casefold():
            continue
        result.append(out)
    return result


@frappe.whitelist()
def detail(name):
    access()
    from lotus_farm.warehouse_buying_lite import order_detail
    doc = _po(name)
    out = order_detail(name)
    out.update(owner=doc.owner, requested_by=doc.get("lotus_requested_by"),
               requested_at=str(doc.get("lotus_requested_at") or ""),
               approved_by=doc.get("lotus_approved_by"),
               approval_status="Đã hủy" if doc.docstatus == 2 else
                   ((doc.get("lotus_approval_status") or DRAFT) if doc.docstatus == 0 else "Đã duyệt"),
               reject_reason=doc.get("lotus_reject_reason") or "",
               sent_at=str(doc.get("lotus_sent_at") or ""), sent_by=doc.get("lotus_sent_by") or "",
               supplier_confirmed_at=str(doc.get("lotus_supplier_confirmed_at") or ""),
               supplier_confirmed_by=doc.get("lotus_supplier_confirmed_by") or "",
               revised_delivery_date=str(doc.get("lotus_revised_delivery_date") or ""),
               revised_delivery_reason=doc.get("lotus_revised_delivery_reason") or "",
               close_reason=doc.get("lotus_close_reason") or "",
               cancel_reason=doc.get("lotus_cancel_reason") or "",
               can_print=doc.docstatus == 1 and doc.has_permission("print"),
               can_manage=doc.docstatus == 1 and doc.status not in ("Closed", "Stopped", "Cancelled", "Completed")
                   and doc.has_permission("write"),
               can_close=doc.docstatus == 1 and doc.status not in ("Closed", "Stopped", "Cancelled", "Completed")
                   and _approver() and doc.has_permission("submit")
                   and any(flt(row.qty)-flt(row.received_qty)>0.000001 for row in doc.items),
               can_cancel=doc.docstatus == 1 and doc.status not in ("Closed", "Stopped", "Cancelled", "Completed")
                   and _approver() and doc.has_permission("cancel"),
               amount=flt(doc.grand_total), can_approve=can_approve(doc),
               can_request_approval=doc.docstatus == 0
                and (doc.get("lotus_approval_status") or DRAFT) in (DRAFT, REJECTED)
                and doc.has_permission("write"))
    return out


@frappe.whitelist()
def suppliers(search=None):
    access()
    if not frappe.has_permission("Supplier", "read"):
        return []
    rows = frappe.get_list("Supplier", fields=["name", "supplier_name", "disabled",
                          "lotus_supplier_phone", "lotus_supplier_contact", "lotus_supplier_note"],
                          order_by="supplier_name asc", limit_page_length=1000)
    if search:
        s = str(search).casefold()
        rows = [row for row in rows if s in (row.supplier_name + " " + (row.lotus_supplier_phone or "")).casefold()]
    return rows


@frappe.whitelist(methods=["POST"])
def save_supplier(name, phone="", contact="", notes="", supplier_id=None):
    access()
    fields = dict(lotus_supplier_phone=str(phone or "").strip()[:60],
                  lotus_supplier_contact=str(contact or "").strip()[:140],
                  lotus_supplier_note=str(notes or "").strip()[:500])
    if supplier_id:
        doc = frappe.get_doc("Supplier", supplier_id)
        doc.check_permission("write")
        if name and name.strip() != doc.supplier_name:
            frappe.throw("Không đổi tên nhà cung cấp tại đây.")
        for k, v in fields.items():
            doc.set(k, v)
        doc.save()
    else:
        if not frappe.has_permission("Supplier", "create"):
            frappe.throw("Không có quyền tạo nhà cung cấp.", frappe.PermissionError)
        name = str(name or "").strip()
        if not 1 <= len(name) <= 140:
            frappe.throw("Nhập tên nhà cung cấp.")
        existing = frappe.db.get_value("Supplier", {"supplier_name": name}, "name")
        if existing:
            frappe.throw("Nhà cung cấp này đã tồn tại.")
        group = frappe.db.get_value("Supplier Group", {"name": "Local", "is_group": 0}, "name") or frappe.db.get_value("Supplier Group", {"is_group": 0}, "name")
        if not group:
            frappe.throw("Cần tạo Nhóm nhà cung cấp trong ERPNext.")
        doc = frappe.get_doc(dict(doctype="Supplier", supplier_name=name, supplier_group=group,
                                  supplier_type="Company", **fields))
        doc.insert()
    return dict(name=doc.name, supplier_name=doc.supplier_name)

def _submitted_order(name, modified, permission="write"):
    """Reload under a lock; submitted purchase orders cannot be silently changed."""
    from lotus_farm.controls import lock
    doc = _po(name)
    lock("Purchase Order", name)
    doc.reload()
    if not modified or str(doc.modified) != str(modified):
        frappe.throw("Đơn đã thay đổi. Tải lại trước khi thao tác.")
    if doc.docstatus != 1 or doc.status in ("Closed", "Stopped", "Cancelled", "Completed"):
        frappe.throw("Chỉ xử lý đơn đã duyệt và chưa kết thúc.")
    doc.check_permission(permission)
    return doc


def _reason(value, label="Lý do"):
    value = str(value or "").strip()
    if not 3 <= len(value) <= 500:
        frappe.throw(label + " phải có từ 3 đến 500 ký tự.")
    return value


@frappe.whitelist(methods=["POST"])
def mark_order_sent(name, modified):
    """Only record an actual external send; downloading a PDF is not a send."""
    doc = _submitted_order(name, modified)
    if doc.get("lotus_sent_at"):
        frappe.throw("Đơn đã ghi nhận gửi nhà cung cấp.")
    frappe.db.set_value("Purchase Order", doc.name, {
        "lotus_sent_at": now_datetime(), "lotus_sent_by": frappe.session.user})
    doc.add_comment("Comment", "Đã gửi đơn cho nhà cung cấp (xác nhận thủ công).")
    return dict(name=doc.name, status="Đã gửi NCC")


@frappe.whitelist(methods=["POST"])
def confirm_supplier_order(name, modified):
    """Manual acknowledgement from supplier; not an automatic delivery receipt."""
    doc = _submitted_order(name, modified)
    if not doc.get("lotus_sent_at"):
        frappe.throw("Cần đánh dấu đã gửi đơn cho nhà cung cấp trước.")
    if doc.get("lotus_supplier_confirmed_at"):
        frappe.throw("Đơn đã ghi nhận nhà cung cấp xác nhận.")
    frappe.db.set_value("Purchase Order", doc.name, {
        "lotus_supplier_confirmed_at": now_datetime(),
        "lotus_supplier_confirmed_by": frappe.session.user})
    doc.add_comment("Comment", "Nhà cung cấp đã xác nhận nhận đơn (ghi nhận thủ công).")
    return dict(name=doc.name, status="NCC đã xác nhận")


@frappe.whitelist(methods=["POST"])
def reschedule_order(name, modified, expected_date, reason):
    doc = _submitted_order(name, modified)
    date = getdate(expected_date)
    if not expected_date or date < getdate(nowdate()):
        frappe.throw("Ngày giao mới không được trước hôm nay.")
    note = _reason(reason, "Lý do đổi ngày giao")
    if not any(flt(row.qty) - flt(row.received_qty) > 0.000001 for row in doc.items):
        frappe.throw("Đơn đã nhận đủ, không còn hàng chờ.")
    frappe.db.set_value("Purchase Order", doc.name, {
        "lotus_revised_delivery_date": date,
        "lotus_revised_delivery_reason": note})
    doc.add_comment("Comment", f"Nhà cung cấp hẹn giao lại ngày {date}: {note}")
    return dict(name=doc.name, expected_date=str(date))


@frappe.whitelist(methods=["POST"])
def close_order(name, modified, reason):
    """End the unfulfilled remainder with ERPNext's native Close state."""
    if not _approver():
        frappe.throw("Chỉ người duyệt mua được đóng đơn.", frappe.PermissionError)
    doc = _submitted_order(name, modified, permission="submit")
    note = _reason(reason, "Lý do đóng đơn")
    if not any(flt(row.qty) - flt(row.received_qty) > 0.000001 for row in doc.items):
        frappe.throw("Đơn đã nhận đủ, không có phần còn lại để đóng.")
    doc.update_status("Closed")
    frappe.db.set_value("Purchase Order", doc.name, "lotus_close_reason", note)
    doc.add_comment("Comment", "Đóng phần hàng chưa giao: " + note)
    return dict(name=doc.name, status="Đã đóng")


@frappe.whitelist(methods=["POST"])
def cancel_order(name, modified, reason):
    """ERPNext blocks cancellation when linked receipts/invoices prevent it."""
    if not _approver():
        frappe.throw("Chỉ người có quyền duyệt và hủy đơn mới được hủy.", frappe.PermissionError)
    doc = _submitted_order(name, modified, permission="cancel")
    note = _reason(reason, "Lý do hủy đơn")
    if any(flt(row.received_qty) > 0.000001 for row in doc.items):
        frappe.throw("Đơn đã nhận hàng. Hãy xử lý phiếu nhập liên quan trước hoặc đóng phần chưa giao.")
    doc.cancel()
    frappe.db.set_value("Purchase Order", doc.name, "lotus_cancel_reason", note)
    doc.add_comment("Comment", "Hủy đơn mua: " + note)
    return dict(name=doc.name, status="Đã hủy")