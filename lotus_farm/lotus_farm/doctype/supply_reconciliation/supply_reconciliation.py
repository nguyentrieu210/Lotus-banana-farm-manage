import frappe
from frappe.model.document import Document

from lotus_farm.reconciliation import approve


class SupplyReconciliation(Document):
    def validate(self):
        if not (self.reason or "").strip():
            frappe.throw("Reason is required.")
        if self.reconciliation_type == "Stock Entry Reversal":
            if not self.stock_entry or self.stock_reservation:
                frappe.throw("Select exactly one Stock Entry for reversal.")
        elif self.reconciliation_type == "Stock Reservation Cancellation":
            if not self.stock_reservation or self.stock_entry:
                frappe.throw("Select exactly one Stock Reservation Entry for cancellation.")
        else:
            frappe.throw("Select a supported reconciliation type.")
        if self.docstatus == 0:
            self.state = "Draft"

    def before_submit(self):
        approve(self)

    def before_cancel(self):
        frappe.throw("Submitted reconciliation records are immutable audit evidence.")
