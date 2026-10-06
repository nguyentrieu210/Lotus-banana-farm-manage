import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate


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
            so = frappe.db.get_value("Sales Order", row.sales_order, ["customer", "delivery_date", "docstatus"], as_dict=True)
            if not so:
                frappe.throw(f"Sales Order {row.sales_order} does not exist.")
            if so.docstatus != 1:
                frappe.throw(f"Sales Order {row.sales_order} must be submitted before it can reserve forecast.")
            row.customer = so.customer
            row.delivery_date = so.delivery_date

    def _calculate(self):
        source_bunch_qty = cint(self.source_bunch_qty)
        avg_weight = flt(self.avg_bunch_weight_kg)
        defect_rate = flt(self.expected_defect_rate_percent)
        safety_buffer = flt(self.safety_buffer_percent)

        if source_bunch_qty < 0 or avg_weight < 0:
            frappe.throw("Forecast quantities cannot be negative.")
        if not 0 <= defect_rate <= 100:
            frappe.throw("Expected Defect Rate must be between 0 and 100.")
        if not 0 <= safety_buffer <= 100:
            frappe.throw("Safety Buffer must be between 0 and 100.")

        self.gross_forecast_kg = flt(source_bunch_qty * avg_weight, 3)
        self.saleable_forecast_kg = flt(self.gross_forecast_kg * (1 - defect_rate / 100), 3)
        self.safe_saleable_kg = flt(self.saleable_forecast_kg * (1 - safety_buffer / 100), 3)
        self.committed_qty_kg = flt(sum(flt(row.reserved_qty_kg) for row in (self.allocations or [])), 3)
        self.available_to_promise_kg = flt(self.safe_saleable_kg - self.committed_qty_kg, 3)
        self.shortage_kg = flt(max(self.committed_qty_kg - self.safe_saleable_kg, 0), 3)

        if self.shortage_kg > 0:
            self.availability_status = "Overcommitted"
        elif self.safe_saleable_kg and self.available_to_promise_kg / self.safe_saleable_kg <= 0.1:
            self.availability_status = "Tight"
        else:
            self.availability_status = "Available"
