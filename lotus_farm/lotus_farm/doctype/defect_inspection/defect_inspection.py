import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt


class DefectInspection(Document):
    def validate(self):
        self._validate_block()
        inspected_qty = cint(self.inspected_qty)
        defect_qty = cint(self.defect_qty)
        if inspected_qty < 0 or defect_qty < 0:
            frappe.throw("Inspection quantities cannot be negative.")
        if defect_qty > inspected_qty:
            frappe.throw("Defect Qty cannot exceed Inspected Qty.")
        self.defect_rate_percent = flt(defect_qty / inspected_qty * 100, 2) if inspected_qty else 0

    def _validate_block(self):
        if not self.farm_block:
            return
        block_farm = frappe.db.get_value("Farm Block", self.farm_block, "farm")
        if block_farm and block_farm != self.farm:
            frappe.throw("Farm Block must belong to the selected Farm.")
