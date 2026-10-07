import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt


class HarvestActual(Document):
    def validate(self):
        self._validate_scope()

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
            forecast = frappe.db.get_value(
                "Harvest Forecast",
                self.forecast,
                ["farm", "farm_block", "crop_cycle", "sucker_selection_batch", "saleable_forecast_kg"],
                as_dict=True,
            )
            if not forecast:
                frappe.throw("Harvest Forecast does not exist.")
            if (
                forecast.farm != self.farm
                or forecast.farm_block != self.farm_block
                or forecast.crop_cycle != self.crop_cycle
            ):
                frappe.throw("Harvest Forecast must belong to the same Farm, Block and Crop Cycle.")
            if forecast.sucker_selection_batch != self.sucker_selection_batch:
                frappe.throw("Harvest Forecast must belong to the same Sucker Selection Batch.")

            self.forecast_saleable_kg = flt(forecast.saleable_forecast_kg or 0, 3)
            self.variance_kg = flt(self.saleable_weight_kg - self.forecast_saleable_kg, 3)
            if self.forecast_saleable_kg:
                self.variance_percent = flt(self.variance_kg / self.forecast_saleable_kg * 100, 2)

    def _validate_scope(self):
        block_farm = frappe.db.get_value("Farm Block", self.farm_block, "farm")
        if block_farm and block_farm != self.farm:
            frappe.throw("Farm Block must belong to the selected Farm.")

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
        if cycle.cycle_type == "Ratoon" and not self.sucker_selection_batch:
            frappe.throw("Ratoon harvests must select a Sucker Selection Batch.")

        if self.sucker_selection_batch:
            batch_cycle = frappe.db.get_value(
                "Sucker Selection Batch", self.sucker_selection_batch, "crop_cycle"
            )
            if batch_cycle != self.crop_cycle:
                frappe.throw("Sucker Selection Batch must belong to the selected Crop Cycle.")

    def before_cancel(self):
        source = frappe.qb.DocType("Harvest Lot Source")
        lot = frappe.qb.DocType("Harvest Lot")
        rows = (
            frappe.qb.from_(source)
            .join(lot)
            .on(source.parent == lot.name)
            .select(lot.name)
            .where((source.harvest_actual == self.name) & (lot.docstatus == 1))
            .run()
        )
        if rows:
            frappe.throw("Cancel dependent Harvest Lots before cancelling this harvest.")
