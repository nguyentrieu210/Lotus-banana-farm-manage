import frappe
from frappe.model.document import Document

from lotus_farm import cut_forecast_rules as rules


class LotusCutJournalEntry(Document):
    """Written only by lotus_farm.cut_forecast (import, undo) after its own role and farm checks."""

    def validate(self):
        if (self.tree_qty or 0) <= 0:
            frappe.throw('Số cây phải lớn hơn 0.')
        self.farm_zone = (self.farm_zone or '').strip().upper()
        if self.farm_block:
            block = frappe.get_doc("Farm Block", self.farm_block)
            if block.farm != self.farm:
                frappe.throw("Lô lớn phải thuộc đúng vườn.")
            if (block.farm_zone or "").strip().upper() != self.farm_zone:
                frappe.throw("Khu của lô không khớp với khu trong nhật ký.")
        if self.crop_cycle:
            cycle = frappe.get_doc("Crop Cycle", self.crop_cycle)
            if cycle.farm != self.farm or cycle.farm_block != self.farm_block:
                frappe.throw("Vụ cây không thuộc đúng lô và vườn.")
        if self.plan_cohort:
            cohort = frappe.get_doc("Plan Cohort", self.plan_cohort)
            if cohort.farm != self.farm or cohort.farm_block != self.farm_block:
                frappe.throw("Đợt cây không thuộc đúng lô và vườn.")
            if self.crop_cycle and cohort.crop_cycle and cohort.crop_cycle != self.crop_cycle:
                frappe.throw("Đợt cây không thuộc vụ đang chọn.")
        self.entry_key = rules.entry_key(self.farm, self.farm_zone, self.cut_date, self.source_ref or '')
