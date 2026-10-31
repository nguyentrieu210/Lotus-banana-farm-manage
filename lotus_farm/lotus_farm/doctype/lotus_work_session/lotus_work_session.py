from frappe.model.document import Document
from lotus_farm.field_report import validate_document


class LotusWorkSession(Document):
    def validate(self):
        validate_document(self)

    def on_trash(self):
        import frappe
        frappe.throw("Buổi công được ghi từ báo cáo phiếu.")
