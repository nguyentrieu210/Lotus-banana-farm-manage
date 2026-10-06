import frappe
from frappe.model.document import Document
from frappe.utils import add_days, cint, getdate


class BunchOperation(Document):
    def validate(self):
        self._validate_block()
        self._validate_quantities()
        self.net_bunch_qty = cint(self.bunch_qty) - cint(self.rejected_qty)

        if self.operation_type == "Cut Bud":
            self._set_expected_harvest()

        if self.expected_harvest_date:
            self.expected_harvest_week = getdate(self.expected_harvest_date).isocalendar().week

    def _validate_block(self):
        if not self.farm_block:
            return
        block_farm = frappe.db.get_value("Farm Block", self.farm_block, "farm")
        if block_farm and block_farm != self.farm:
            frappe.throw("Farm Block must belong to the selected Farm.")

    def _validate_quantities(self):
        bunch_qty = cint(self.bunch_qty)
        rejected_qty = cint(self.rejected_qty)
        if bunch_qty < 0 or rejected_qty < 0:
            frappe.throw("Bunch quantities cannot be negative.")
        if rejected_qty > bunch_qty:
            frappe.throw("Rejected Bunch Qty cannot exceed Bunch Qty.")

    def _set_expected_harvest(self):
        if self.expected_harvest_date:
            return
        harvest_age_days = frappe.db.get_single_value("Lotus Farm Settings", "default_harvest_age_days")
        if harvest_age_days:
            self.expected_harvest_date = add_days(self.operation_date, cint(harvest_age_days))
