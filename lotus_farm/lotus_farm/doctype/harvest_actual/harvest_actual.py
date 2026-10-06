import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt


class HarvestActual(Document):
    def validate(self):
        self._validate_block()
        gross_weight = flt(self.gross_weight_kg)
        rejected_weight = flt(self.rejected_weight_kg)

        if cint(self.harvested_bunch_qty) < 0 or gross_weight < 0 or rejected_weight < 0:
            frappe.throw("Harvest quantities cannot be negative.")
        if rejected_weight > gross_weight:
            frappe.throw("Rejected Weight cannot exceed Gross Weight.")

        self.saleable_weight_kg = flt(gross_weight - rejected_weight, 3)
        self.forecast_saleable_kg = 0
        self.variance_kg = 0
        self.variance_percent = 0

        if self.forecast:
            self.forecast_saleable_kg = flt(frappe.db.get_value("Harvest Forecast", self.forecast, "saleable_forecast_kg") or 0, 3)
            self.variance_kg = flt(self.saleable_weight_kg - self.forecast_saleable_kg, 3)
            if self.forecast_saleable_kg:
                self.variance_percent = flt(self.variance_kg / self.forecast_saleable_kg * 100, 2)

    def _validate_block(self):
        if not self.farm_block:
            return
        block_farm = frappe.db.get_value("Farm Block", self.farm_block, "farm")
        if block_farm and block_farm != self.farm:
            frappe.throw("Farm Block must belong to the selected Farm.")
