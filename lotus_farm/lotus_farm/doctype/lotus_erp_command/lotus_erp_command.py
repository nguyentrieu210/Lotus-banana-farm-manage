import frappe
from frappe.model.document import Document


class LotusERPCommand(Document):
    def validate(self):
        if not self.flags.get('erp_command'):
            frappe.throw('Lệnh lưu chứng từ ERP chỉ được ghi bởi thao tác chứng từ hợp lệ.', frappe.PermissionError)
