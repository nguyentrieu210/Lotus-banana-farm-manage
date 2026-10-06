import frappe
from frappe.model.document import Document
from lotus_farm.controls import command_allowed


class IntegrationEvent(Document):
    def validate(self):
        if self.is_new() and not command_allowed(self, "integration_event"):
            frappe.throw("Integration results can only be recorded by the server command.")
        if not self.is_new():
            frappe.throw("Integration results are immutable.")

    def on_trash(self):
        frappe.throw("Integration results cannot be deleted.")
