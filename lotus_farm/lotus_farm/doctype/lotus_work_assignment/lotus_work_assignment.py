from frappe.model.document import Document
from lotus_farm.field_report import validate_document


class LotusWorkAssignment(Document):
    def validate(self):
        validate_document(self)

    def on_trash(self):
        import frappe
        frappe.throw("Không xóa phiếu giao; huỷ phiếu (ghi lý do) nếu giao nhầm.")
