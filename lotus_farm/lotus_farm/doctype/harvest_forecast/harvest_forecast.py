import json

import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate, now_datetime

from lotus_farm.forecasting import ForecastInputError, calculate_availability
from lotus_farm.supply import lock_document


class HarvestForecast(Document):
    def validate(self):
        old = self.get_doc_before_save()
        if old and old.docstatus == 1:
            return  # Frappe disallows submitted edits; never recalculate a released vintage.
        self._validate_period()
        self._validate_scope()
        self._apply_profile_defaults()
        self._apply_settings_fallback()
        self._pull_source_qty()
        self._hydrate_allocations()
        self._calculate()

    def before_submit(self):
        lock_document("Crop Cycle", self.crop_cycle)
        self.validate()
        if not self.item_code or not self.harvest_profile:
            frappe.throw("A released forecast requires an Item and an approved Harvest Profile.")
        item = frappe.db.get_value("Item", self.item_code, ["stock_uom", "disabled", "is_stock_item"], as_dict=True)
        if not item or item.disabled or not item.is_stock_item or item.stock_uom != "Kg":
            frappe.throw("Pilot forecast Item must be an enabled stock Item with stock UOM Kg.")
        # Single-output pilot: sharing a cohort across Item forecasts would count raw supply twice.
        overlap = frappe.db.sql("""SELECT name FROM `tabHarvest Forecast`
            WHERE crop_cycle=%s AND COALESCE(sucker_selection_batch,'')=%s
            AND docstatus=1 AND name!=%s AND period_start_date<=%s AND period_end_date>=%s FOR UPDATE""",
            (self.crop_cycle, self.sucker_selection_batch or "", self.name,
             self.period_end_date, self.period_start_date))
        if overlap:
            frappe.throw("A released forecast already covers this cohort and harvest period.")
        self.formula_version = "lotus-availability-2"
        self.calculated_at = now_datetime()
        self.calculated_by = frappe.session.user
        self.profile_version_snapshot = frappe.db.get_value("Harvest Profile", self.harvest_profile, "profile_version")
        self.source_snapshot = json.dumps(getattr(self, "_source_rows", []), sort_keys=True, default=str)

    def before_cancel(self):
        lock_document("Harvest Forecast", self.name)
        if frappe.db.sql("SELECT name FROM `tabForecast Reservation` WHERE forecast=%s AND docstatus=1 FOR UPDATE", (self.name,)):
            frappe.throw("Cancel active reservations before cancelling this forecast.")
        if frappe.db.sql("SELECT name FROM `tabForecast Materialization` WHERE forecast=%s AND docstatus=1 FOR UPDATE", (self.name,)):
            frappe.throw("Reverse physical stock materialization before cancelling this forecast.")

    def _validate_period(self):
        if (
            self.period_start_date
            and self.period_end_date
            and getdate(self.period_end_date) < getdate(self.period_start_date)
        ):
            frappe.throw("Harvest Period End cannot be before Harvest Period Start.")

    def _validate_scope(self):
        block = frappe.db.get_value(
            "Farm Block", self.farm_block, ["farm", "variety"], as_dict=True
        )
        if not block:
            frappe.throw("Farm Block does not exist.")
        if block.farm != self.farm:
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
            frappe.throw("Ratoon forecasts must select a Sucker Selection Batch.")

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

    @staticmethod
    def _is_blank(value):
        return value is None or value == ""

    def _apply_profile_defaults(self):
        if not self.harvest_profile:
            return

        profile = frappe.db.get_value(
            "Harvest Profile",
            self.harvest_profile,
            [
                "active",
                "docstatus",
                "farm",
                "farm_block",
                "variety",
                "valid_from",
                "valid_to",
                "avg_bunch_weight_kg",
                "bunch_survival_rate_percent",
                "quality_pass_rate_percent",
                "packout_rate_percent",
                "safety_buffer_percent",
            ],
            as_dict=True,
        )
        if not profile:
            frappe.throw("Harvest Profile does not exist.")
        if not profile.active:
            frappe.throw("Harvest Profile is inactive.")
        if profile.docstatus != 1:
            frappe.throw("Harvest Profile must be submitted before use.")
        if profile.farm and profile.farm != self.farm:
            frappe.throw("Harvest Profile does not apply to the selected Farm.")
        if profile.farm_block and profile.farm_block != self.farm_block:
            frappe.throw("Harvest Profile does not apply to the selected Farm Block.")

        block_variety = frappe.db.get_value("Farm Block", self.farm_block, "variety")
        if profile.variety and block_variety and profile.variety != block_variety:
            frappe.throw("Harvest Profile does not apply to the Farm Block variety.")

        on_date = getdate(self.period_start_date)
        if profile.valid_from and on_date < getdate(profile.valid_from):
            frappe.throw("Harvest Profile is not valid yet for this forecast period.")
        if profile.valid_to and getdate(self.period_end_date) > getdate(profile.valid_to):
            frappe.throw("Harvest Profile has expired for this forecast period.")

        for fieldname in (
            "avg_bunch_weight_kg",
            "bunch_survival_rate_percent",
            "quality_pass_rate_percent",
            "packout_rate_percent",
            "safety_buffer_percent",
        ):
            self.set(fieldname, profile.get(fieldname))

    def _apply_settings_fallback(self):
        settings = frappe.get_single("Lotus Farm Settings")

        if self._is_blank(self.avg_bunch_weight_kg):
            self.avg_bunch_weight_kg = settings.default_avg_bunch_weight_kg or 0

        if self._is_blank(self.bunch_survival_rate_percent):
            self.bunch_survival_rate_percent = 100

        if self._is_blank(self.quality_pass_rate_percent):
            defect_rate = flt(settings.default_defect_rate_percent or 0)
            self.quality_pass_rate_percent = 100 - defect_rate

        if self._is_blank(self.packout_rate_percent):
            self.packout_rate_percent = 100

        if self._is_blank(self.safety_buffer_percent):
            self.safety_buffer_percent = settings.safety_buffer_percent or 0

    def _pull_source_qty(self):
        if self.forecast_basis != "Cut Bud Operations":
            return

        filters = {
            "farm": self.farm,
            "farm_block": self.farm_block,
            "crop_cycle": self.crop_cycle,
            "operation_type": "Cut Bud",
            "docstatus": 1,
            "expected_harvest_date": [
                "between",
                [self.period_start_date, self.period_end_date],
            ],
        }
        if self.sucker_selection_batch:
            filters["sucker_selection_batch"] = self.sucker_selection_batch

        rows = frappe.get_all(
            "Bunch Operation",
            filters=filters,
            fields=["name", "net_bunch_qty", "modified", "expected_harvest_date"],
            order_by="name asc",
        )
        self._source_rows = [dict(row) for row in rows]
        self.source_bunch_qty = sum(flt(row.net_bunch_qty) for row in rows)

    def _hydrate_allocations(self):
        if self.allocations:
            frappe.throw("Legacy order-level allocations cannot be released. Use Forecast Reservation by Sales Order Item.")
        seen_orders = set()
        for row in self.allocations or []:
            if flt(row.reserved_qty_kg) < 0:
                frappe.throw("Reserved Qty cannot be negative.")
            if not row.sales_order:
                continue
            if row.sales_order in seen_orders:
                frappe.throw(
                    f"Sales Order {row.sales_order} is allocated more than once in this forecast."
                )
            seen_orders.add(row.sales_order)

            so = frappe.db.get_value(
                "Sales Order",
                row.sales_order,
                ["customer", "delivery_date", "docstatus"],
                as_dict=True,
            )
            if not so:
                frappe.throw(f"Sales Order {row.sales_order} does not exist.")
            if so.docstatus != 1:
                frappe.throw(
                    f"Sales Order {row.sales_order} must be submitted before it can reserve forecast."
                )

            row.customer = so.customer
            row.delivery_date = so.delivery_date

    def _calculate(self):
        committed_qty_kg = sum(
            flt(row.reserved_qty_kg) for row in (self.allocations or [])
        )
        try:
            values = calculate_availability(
                source_bunch_qty=self.source_bunch_qty,
                avg_bunch_weight_kg=self.avg_bunch_weight_kg,
                bunch_survival_rate_percent=self.bunch_survival_rate_percent,
                quality_pass_rate_percent=self.quality_pass_rate_percent,
                packout_rate_percent=self.packout_rate_percent,
                safety_buffer_percent=self.safety_buffer_percent,
                committed_qty_kg=committed_qty_kg,
            )
        except ForecastInputError as exc:
            frappe.throw(str(exc))

        for fieldname, value in values.items():
            setattr(self, fieldname, value)
