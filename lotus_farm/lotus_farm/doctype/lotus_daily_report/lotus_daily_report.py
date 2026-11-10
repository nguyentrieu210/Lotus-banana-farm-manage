import frappe
from frappe.model.document import Document

from lotus_farm import lot_ledger_rules as rules
from lotus_farm.field_report import validate_document


class LotusDailyReport(Document):
    """One tổ, one day: the header of the sổ lô lines the tổ reported that day."""

    def validate(self):
        validate_document(self)
        before = self.get_doc_before_save()
        if self.state == rules.REOPENED and (not before or before.state != rules.REOPENED) and not (self.reopen_reason or "").strip():
            frappe.throw("Mở lại báo cáo phải ghi lý do.")

    def on_trash(self):
        if self.state != rules.DRAFT or frappe.db.exists("Lotus Work Entry", {"daily_report": self.name}):
            frappe.throw("Không xóa báo cáo ngày đã có dòng sổ lô.")
