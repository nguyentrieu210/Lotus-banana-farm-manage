import frappe
from frappe.model.document import Document
from lotus_farm.controls import command_allowed


class IntegrationEvent(Document):
    def validate(self):
        if self.is_new() and not command_allowed(self, "integration_event"):
            frappe.throw("Kết quả đồng bộ chỉ được ghi bằng lệnh của máy chủ.")
        if not self.is_new():
            frappe.throw("Kết quả đồng bộ không được sửa.")

    def on_trash(self):
        frappe.throw("Không được xóa kết quả đồng bộ.")
