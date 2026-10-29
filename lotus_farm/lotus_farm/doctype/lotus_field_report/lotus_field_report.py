from frappe.model.document import Document
from lotus_farm.field_report import validate_document


class LotusFieldReport(Document):
    def validate(self):
        validate_document(self)

    def on_trash(self):
        import frappe
        frappe.throw("Không xóa báo cáo ngày; mở lại và sửa nếu sai.")
