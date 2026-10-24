import frappe
from frappe.model.document import Document


class LotusERPCommand(Document):
    def validate(self):
        if not self.flags.get('erp_command'):
            frappe.throw('ERP commands can only be recorded by the authorized document action.', frappe.PermissionError)
