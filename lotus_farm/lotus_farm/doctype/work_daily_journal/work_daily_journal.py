from frappe.model.document import Document
from lotus_farm.work_journal import validate_document
class WorkDailyJournal(Document):
    def validate(self):
        validate_document(self)
    def on_trash(self):
        import frappe
        frappe.throw("Không được xóa vĩnh viễn nhật ký.")
