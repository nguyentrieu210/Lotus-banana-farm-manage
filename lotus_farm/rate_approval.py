"""Approval for piecework rates above the Work Type price list.

Approvals are signed against the exact draft plan, so neither a manager nor a
regular Frappe write/submit can forge approval by editing a Select field.
"""
import hashlib
import hmac
import json

import frappe
from frappe.utils import now_datetime

from lotus_farm.controls import lock, require_role
from lotus_farm.labor_pricing import positive_number


def resolve_rate(list_rate, proposed, mode):
    if mode not in ("Piece", "Both"):
        if proposed not in (None, ""):
            raise ValueError("Công nhật không có đơn giá khoán.")
        return dict(list_rate=0, rate=0, requires_approval=False)
    listed = positive_number(list_rate, "Đơn giá niêm yết")
    rate = positive_number(listed if proposed in (None, "") else proposed, "Đơn giá đề xuất")
    return dict(
        list_rate=listed,
        rate=rate,
        requires_approval=round(rate, 2) > round(listed, 2),
    )


def needs_approval(doc):
    return any(
        row.payment_mode in ("Piece", "Both")
        and round(float(row.requested_piecework_rate or 0), 2)
            > round(float(row.list_piecework_rate or 0), 2)
        for row in doc.lines
    )


def _signature(doc):
    secret = frappe.conf.get("encryption_key")
    if not secret:
        frappe.throw("Chưa có khóa bảo vệ phiếu duyệt giá.")
    payload = {
        "plan": doc.name, "owner": doc.owner, "farm": doc.farm,
        "date": str(doc.posting_date), "reason": doc.get("rate_request_reason") or "",
        "approved_by": doc.rate_approved_by,
        "approved_at": str(doc.rate_approved_at),
        "lines": [
            {
                "name": row.name, "block": row.farm_block, "plot": row.farm_plot,
                "cycle": row.crop_cycle, "batch": row.sucker_selection_batch,
                "work": row.work_type, "team": row.work_team,
                "mode": row.payment_mode, "qty": str(row.planned_qty),
                "listed": str(row.list_piecework_rate or 0),
                "proposed": str(row.requested_piecework_rate or 0),
            } for row in doc.lines
        ],
    }
    message = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hmac.new(str(secret).encode(), message.encode(), hashlib.sha256).hexdigest()


def validate_plan(doc):
    over = needs_approval(doc)
    state = doc.get("rate_approval_state") or ""
    if over:
        if not (doc.get("rate_request_reason") or "").strip():
            frappe.throw("Phải ghi lý do đề xuất tăng đơn giá khoán.")
        if state == "Approved":
            expected = _signature(doc)
            if not (
                doc.rate_approved_by and doc.rate_approved_at
                and doc.rate_approval_signature
                and hmac.compare_digest(str(doc.rate_approval_signature), expected)
                and doc.rate_approved_by != doc.owner
            ):
                frappe.throw("Duyệt giá không hợp lệ hoặc nội dung đã đổi. Phải tạo phiếu duyệt mới.")
        elif state not in ("Pending", "Rejected"):
            frappe.throw("Giá khoán cao hơn niêm yết cần gửi duyệt trước.")
        if doc.docstatus == 1 and state != "Approved":
            frappe.throw("Chưa duyệt giá khoán vượt niêm yết; không được giao việc.")
    elif state in ("Pending", "Approved"):
        frappe.throw("Phiếu không có giá vượt niêm yết, không được gắn trạng thái chờ/đã duyệt.")
    before = doc.get_doc_before_save()
    if before and before.get("rate_approval_state") == "Approved":
        if (state != "Approved" or
                not hmac.compare_digest(str(before.get("rate_approval_signature") or ""),
                                        str(doc.get("rate_approval_signature") or ""))):
            frappe.throw("Phiếu đã duyệt không thể sửa thông tin duyệt.")


@frappe.whitelist()
def pending(farm, posting_date=None):
    require_role("Lotus Price Approver")
    record = frappe.get_doc("Farm", farm)
    record.check_permission("read")
    filters = {"farm": farm, "docstatus": 0, "rate_approval_state": "Pending"}
    if posting_date:
        filters["posting_date"] = posting_date
    return frappe.get_list("Daily Work Plan", filters=filters,
                           fields=["name", "posting_date", "owner", "rate_requested_by"],
                           order_by="creation desc", limit_page_length=100)


@frappe.whitelist(methods=["POST"])
def decide(plan, decision, reason=None):
    require_role("Lotus Price Approver")
    if decision not in ("Approve", "Reject"):
        frappe.throw("Chỉ được duyệt hoặc từ chối.")
    farm = frappe.db.get_value("Daily Work Plan", plan, "farm")
    if not farm:
        frappe.throw("Không tìm thấy phiếu.")
    frappe.get_doc("Farm", farm).check_permission("read")
    lock("Farm", farm)
    doc = frappe.get_doc("Daily Work Plan", plan, for_update=True)
    doc.check_permission("read")
    if doc.docstatus != 0 or doc.rate_approval_state != "Pending" or not needs_approval(doc):
        frappe.throw("Phiếu này không còn ở trạng thái chờ duyệt.")
    if doc.owner == frappe.session.user:
        frappe.throw("Người lập phiếu không được tự duyệt.")
    if decision == "Reject" and not (reason or "").strip():
        frappe.throw("Cần ghi lý do từ chối.")
    doc.rate_approval_note = (reason or "").strip()[:500]
    doc.rate_approved_by = frappe.session.user
    doc.rate_approved_at = now_datetime().replace(microsecond=0)
    if decision == "Reject":
        doc.rate_approval_state = "Rejected"
        doc.rate_approval_signature = ""
        doc.flags.ignore_permissions = True
        doc.save()
        return {"plan": doc.name, "status": "Rejected"}

    doc.rate_approval_state = "Approved"
    doc.rate_approval_signature = _signature(doc)
    doc.flags.ignore_permissions = True
    doc.save()     # verify signature and exact proposed vs listed prices
    doc.submit()   # only this endpoint may submit an above-list plan
    return {"plan": doc.name, "status": "Submitted", "approved_by": frappe.session.user}
