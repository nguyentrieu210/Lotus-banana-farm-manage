"""Xóa nhiều phiếu nháp đã tick trong một bảng.

Mỗi phiếu đi qua đúng hàm xóa của màn của nó (quyền, trạng thái, người lập giữ nguyên); phiếu nào bị từ chối thì ghi lý
do và các phiếu khác vẫn được xóa. Không xóa phiếu đã ghi sổ, đã ký hay đã hủy: những phiếu đó dùng Hủy có lý do.
"""
import uuid

import frappe

LIMIT = 200


def _handler(doctype, name):
    """The guarded delete of the screen that owns this document, as fn(name, modified)."""
    if doctype in ("Stock Entry", "Stock Reconciliation"):
        from lotus_farm import warehouse
        return lambda n, m: warehouse.delete_draft(doctype, n, m)
    if doctype == "Purchase Receipt":
        from lotus_farm import warehouse_planning
        return lambda n, m: warehouse_planning.receipt_action(n, m, "delete")
    if doctype == "Purchase Order":
        from lotus_farm import warehouse_buying_lite
        return warehouse_buying_lite.delete_draft
    if doctype == "Material Request":
        if frappe.db.get_value("Material Request", name, "material_request_type") == "Material Issue":
            from lotus_farm import issue_request
            return lambda n, m: issue_request.delete_draft(n, m, "bulk-" + uuid.uuid4().hex)
        from lotus_farm import purchase_proposal
        return purchase_proposal.delete_proposal
    return None


def _message(exc):
    text = str(exc) or exc.__class__.__name__
    return frappe.utils.strip_html(text)[:300]


@frappe.whitelist(methods=["POST"])
def drafts(items):
    """items: [{doctype, name}] (JSON). Returns {deleted: [{doctype, name}], failed: [{doctype, name, message}]}."""
    items = frappe.parse_json(items) or []
    if not isinstance(items, list) or len(items) > LIMIT:
        frappe.throw(f"Mỗi lần xóa tối đa {LIMIT} phiếu.")
    deleted, failed, seen = [], [], set()
    for item in items:
        doctype, name = str((item or {}).get("doctype") or ""), str((item or {}).get("name") or "")
        if not doctype or not name or (doctype, name) in seen:
            continue
        seen.add((doctype, name))
        modified = frappe.db.get_value(doctype, name, "modified") if frappe.db.exists("DocType", doctype) else None
        if not modified:
            failed.append(dict(doctype=doctype, name=name, message="Không còn phiếu này."))
            continue
        handler = _handler(doctype, name)
        if not handler:
            failed.append(dict(doctype=doctype, name=name, message="Loại chứng từ này không xóa hàng loạt được."))
            continue
        frappe.db.savepoint("bulk_delete")
        try:
            handler(name, str(modified))
        except Exception as exc:  # each document keeps its own rule; one refusal does not stop the rest
            frappe.db.rollback(save_point="bulk_delete")
            frappe.clear_messages()
            failed.append(dict(doctype=doctype, name=name, message=_message(exc)))
            continue
        deleted.append(dict(doctype=doctype, name=name))
    return dict(deleted=deleted, failed=failed)
