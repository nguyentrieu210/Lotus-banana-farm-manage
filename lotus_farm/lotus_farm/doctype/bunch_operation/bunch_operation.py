import frappe
from frappe.model.document import Document
from frappe.utils import add_days, cint, getdate, now_datetime


class BunchOperation(Document):
    def validate(self):
        if self.is_new():
            self.server_received_at = now_datetime()
        self._validate_scope()
        self._validate_quantities()
        self.net_bunch_qty = cint(self.bunch_qty) - cint(self.rejected_qty)

        if self.operation_type in ("Shooting", "Cut Bud"):
            self._set_expected_harvest()

        if self.expected_harvest_date:
            self.expected_harvest_week = getdate(self.expected_harvest_date).isocalendar().week

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
            frappe.throw("Ratoon operations must select a Sucker Selection Batch.")

        if self.sucker_selection_batch:
            batch = frappe.db.get_value(
                "Sucker Selection Batch",
                self.sucker_selection_batch,
                ["farm", "farm_block", "crop_cycle"],
                as_dict=True,
            )
            if not batch:
                frappe.throw("Sucker Selection Batch does not exist.")
            if (
                batch.farm != self.farm
                or batch.farm_block != self.farm_block
                or batch.crop_cycle != self.crop_cycle
            ):
                frappe.throw("Sucker Selection Batch must belong to the selected Crop Cycle.")

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

        fieldname = {
            "Shooting": "shooting_to_harvest_days",
            "Cut Bud": "cut_bud_to_harvest_days",
        }.get(self.operation_type)
        if not fieldname:
            return

        harvest_age_days = None
        if self.harvest_profile:
            harvest_age_days = frappe.db.get_value("Harvest Profile", self.harvest_profile, fieldname)

        if harvest_age_days is None and self.operation_type == "Cut Bud":
            harvest_age_days = frappe.db.get_single_value("Lotus Farm Settings", "default_harvest_age_days")

        if harvest_age_days:
            self.expected_harvest_date = add_days(self.operation_date, cint(harvest_age_days))

    def before_cancel(self):
        if frappe.db.exists("Harvest Forecast", {"crop_cycle": self.crop_cycle, "supply_state": "Released"}):
            frappe.throw(
                "Supersede/close affected released forecasts before cancelling their source operations."
            )
