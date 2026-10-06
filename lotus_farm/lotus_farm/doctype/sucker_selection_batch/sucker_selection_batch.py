import frappe
from frappe.model.document import Document
from frappe.utils import cint


class SuckerSelectionBatch(Document):
    def validate(self):
        self._validate_scope()
        selected = cint(self.selected_sucker_qty)
        expected = cint(self.expected_productive_qty)

        if selected < 0 or expected < 0:
            frappe.throw("Sucker quantities cannot be negative.")
        if expected and expected > selected:
            frappe.throw("Expected Productive Qty cannot exceed Selected Sucker Qty.")

    def _validate_scope(self):
        cycle = frappe.db.get_value(
            "Crop Cycle",
            self.crop_cycle,
            ["farm", "farm_block", "cycle_type"],
            as_dict=True,
        )
        if not cycle:
            frappe.throw("Crop Cycle does not exist.")
        if cycle.farm != self.farm or cycle.farm_block != self.farm_block:
            frappe.throw("Crop Cycle must belong to the selected Farm and Farm Block.")
        if cycle.cycle_type != "Ratoon":
            frappe.throw("Sucker Selection Batch is used for ratoon cycles (Cycle 2+).")
