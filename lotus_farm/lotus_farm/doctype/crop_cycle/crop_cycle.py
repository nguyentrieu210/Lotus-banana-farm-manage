import frappe
from frappe.model.document import Document
from frappe.utils import cint


class CropCycle(Document):
    def validate(self):
        from lotus_farm.controls import command_allowed
        before=self.get_doc_before_save()
        if before and self.status != before.status and (self.status == "Closed" or before.status == "Closed") and not command_allowed(self,"cycle_close"):
            frappe.throw("Use the reviewed Cycle Closing Report to close or reopen a Cycle.")
        self._validate_block()
        self._validate_cycle()
        self._set_variety()
        self._validate_unique_cycle()

    def _validate_block(self):
        block = frappe.db.get_value("Farm Block", self.farm_block, ["farm", "variety"], as_dict=True)
        if not block:
            frappe.throw("Farm Block does not exist.")
        if block.farm != self.farm:
            frappe.throw("Farm Block must belong to the selected Farm.")

    def _validate_cycle(self):
        cycle_no = cint(self.cycle_no)
        if cycle_no < 1:
            frappe.throw("Cycle No. must be 1 or greater.")

        if cycle_no == 1:
            self.cycle_type = "Plant Crop"
            if not self.planting_date:
                frappe.throw("Planting Date is required for Cycle 1.")
            if self.parent_cycle:
                frappe.throw("Cycle 1 cannot have a Parent Cycle.")
        else:
            self.cycle_type = "Ratoon"
            if not self.parent_cycle:
                frappe.throw("Parent Cycle is required for ratoon cycles.")
            parent = frappe.db.get_value(
                "Crop Cycle",
                self.parent_cycle,
                ["farm", "farm_block", "farm_plot", "cycle_no"],
                as_dict=True,
            )
            if not parent:
                frappe.throw("Parent Cycle does not exist.")
            if parent.farm != self.farm or parent.farm_block != self.farm_block or (parent.farm_plot or "") != (self.farm_plot or ""):
                frappe.throw("Parent Cycle must belong to the same Farm Block.")
            if cint(parent.cycle_no) != cycle_no - 1:
                frappe.throw("Parent Cycle must be the immediately previous cycle.")

    def _set_variety(self):
        if not self.variety:
            self.variety = frappe.db.get_value("Farm Block", self.farm_block, "variety")

    def _validate_unique_cycle(self):
        existing = frappe.db.get_value(
            "Crop Cycle",
            {"farm_block": self.farm_block, "farm_plot": self.farm_plot or "", "cycle_no": self.cycle_no},
            "name",
        )
        if existing and existing != self.name:
            frappe.throw(f"Cycle {self.cycle_no} already exists for Farm Block {self.farm_block}.")
