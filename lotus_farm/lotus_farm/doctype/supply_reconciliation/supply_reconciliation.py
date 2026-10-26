import frappe
from frappe.model.document import Document

from lotus_farm.reconciliation import approve


class SupplyReconciliation(Document):
    def validate(self):
        if not (self.reason or "").strip():
            frappe.throw("Phải nhập lý do.")
        if self.reconciliation_type == "Stock Entry Reversal":
            if not self.stock_entry or self.stock_reservation:
                frappe.throw("Chọn đúng một phiếu kho để đảo.")
        elif self.reconciliation_type == "Stock Reservation Cancellation":
            if not self.stock_reservation or self.stock_entry:
                frappe.throw("Chọn đúng một phiếu giữ hàng để hủy.")
            if self.reservation_disposition not in (
                "Restore Future Reservation",
                "Release Commitment",
            ):
                frappe.throw("Chọn khôi phục hay giải phóng cam kết với khách hàng.")
        else:
            frappe.throw("Chọn loại đối soát được hỗ trợ.")
        if self.docstatus == 0:
            self.state = "Draft"

    def before_submit(self):
        approve(self)

    def before_cancel(self):
        frappe.throw("Phiếu đối soát đã duyệt là bằng chứng kiểm toán, không được sửa.")
