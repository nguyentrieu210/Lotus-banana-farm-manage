import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate

from lotus_farm.forecasting import ForecastInputError, calculate_availability


class HarvestForecast(Document):
    def validate(self):
        self._validate_period()
        self._validate_block()
        self._apply_settings_defaults()
        self._hydrate_allocations()
        self._calculate()

    def _validate_period(self):
        if self.period_start_date and self.period_end_date and getdate(self.period_end_date) < getdate(self.period_start_date):
            frappe.throw("Period End Date cannot be before Period Start Date.")

    def _validate_block(self):
        if not self.farm_block:
            return
        block_farm = frappe.db.get_value("Farm Block", self.farm_block, "farm")
        if block_farm and block_farm != self.farm:
            frappe.throw("Farm Block must belong to the selected Farm.")

    def _apply_settings_defaults(self):
        if not self.is_new():
            return
        settings = frappe.get_single("Lotus Farm Settings")
        if not self.avg_bunch_weight_kg and settings.default_avg_bunch_weight_kg:
            self.avg_bunch_weight_kg = settings.default_avg_bunch_weight_kg
        if not self.expected_defect_rate_percent and settings.default_defect_rate_percent:
            self.expected_defect_rate_percent = settings.default_defect_rate_percent
        if not self.safety_buffer_percent and settings.safety_buffer_percent:
            self.safety_buffer_percent = settings.safety_buffer_percent

    def _hydrate_allocations(self):
        for row in self.allocations or []:
            if flt(row.reserved_qty_kg) < 0:
                frappe.throw("Reserved Qty cannot be negative.")
            if not row.sales_order:
                continue

            so = frappe.db.get_value(
                "Sales Order",
                row.sales_order,
                ["customer", "delivery_date", "docstatus"],
                as_dict=True,
            )
            if not so:
                frappe.throw(f"Sales Order {row.sales_order} does not exist.")
            if so.docstatus != 1:
                frappe.throw(f"Sales Order {row.sales_order} must be submitted before it can reserve forecast.")

            row.customer = so.customer
            row.delivery_date = so.delivery_date

    def _calculate(self):
        committed_qty_kg = sum(flt(row.reserved_qty_kg) for row in (self.allocations or []))
        try:
            values = calculate_availability(
                source_bunch_qty=self.source_bunch_qty,
                avg_bunch_weight_kg=self.avg_bunch_weight_kg,
                expected_defect_rate_percent=self.expected_defect_rate_percent,
                safety_buffer_percent=self.safety_buffer_percent,
                committed_qty_kg=committed_qty_kg,
            )
        except ForecastInputError as exc:
            frappe.throw(str(exc))

        for fieldname, value in values.items():
            setattr(self, fieldname, value)
