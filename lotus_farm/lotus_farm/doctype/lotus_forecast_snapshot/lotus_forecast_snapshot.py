import frappe
from frappe.model.document import Document


class LotusForecastSnapshot(Document):
    def validate(self):
        if not self.is_new():
            frappe.throw("Bản dự thu đã chốt không được sửa.")

    def on_trash(self):
        frappe.throw("Không xóa bản dự thu đã chốt.")
