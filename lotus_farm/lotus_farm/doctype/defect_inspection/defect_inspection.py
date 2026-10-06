import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt


class DefectInspection(Document):
    def validate(self):
        self._validate_scope()
        inspected_qty = cint(self.inspected_qty)
        defect_qty = cint(self.defect_qty)

        if inspected_qty < 0 or defect_qty < 0:
            frappe.throw("Inspection quantities cannot be negative.")
        if defect_qty > inspected_qty:
            frappe.throw("Defect Qty cannot exceed Inspected Qty.")

        self.defect_rate_percent = (
            flt(defect_qty / inspected_qty * 100, 2) if inspected_qty else 0
        )

    def _validate_scope(self):
        block_farm = frappe.db.get_value("Farm Block", self.farm_block, "farm")
        if block_farm and block_farm != self.farm:
            frappe.throw("Farm Block must belong to the selected Farm.")

        cycle = frappe.db.get_value(
            "Crop Cycle", self.crop_cycle, ["farm", "farm_block"], as_dict=True
        )
        if not cycle:
            frappe.throw("Crop Cycle does not exist.")
        if cycle.farm != self.farm or cycle.farm_block != self.farm_block:
            frappe.throw("Crop Cycle must belong to the selected Farm and Farm Block.")

        if self.sucker_selection_batch:
            batch_cycle = frappe.db.get_value(
                "Sucker Selection Batch", self.sucker_selection_batch, "crop_cycle"
            )
            if batch_cycle != self.crop_cycle:
                frappe.throw("Sucker Selection Batch must belong to the selected Crop Cycle.")
