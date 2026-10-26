import frappe
from frappe.model.document import Document

from lotus_farm import cut_forecast_rules as rules


class LotusCutJournalEntry(Document):
    """Written only by lotus_farm.cut_forecast (import, undo) after its own role and farm checks."""

    def validate(self):
        if (self.tree_qty or 0) <= 0:
            frappe.throw('Số cây phải lớn hơn 0.')
        self.farm_zone = (self.farm_zone or '').strip().upper()
        self.entry_key = rules.entry_key(self.farm, self.farm_zone, self.cut_date, self.source_ref or '')
