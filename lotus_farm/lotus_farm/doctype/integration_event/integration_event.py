import frappe
from frappe.model.document import Document


class IntegrationEvent(Document):
    def validate(self):
        if not self.is_new():
            frappe.throw("Integration results are immutable.")

    def on_trash(self):
        frappe.throw("Integration results cannot be deleted.")
