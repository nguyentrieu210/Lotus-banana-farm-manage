import frappe
from frappe.model.document import Document
from frappe.utils import getdate

from lotus_farm.domain import SupplyError, quantity, require_capacity
from lotus_farm.supply import lock_document, materialized_total, reservation_total


class ForecastReservation(Document):
    def load_doc_before_save(self, *, raise_exception=False):
        # Frappe locks the reservation row here, before validate/before_submit.
        # Acquire its demand/supply locks first so two existing drafts cannot
        # deadlock against each other's rows during current-read capacity checks.
        lock_document("Sales Order", self.sales_order)
        lock_document("Harvest Forecast", self.forecast)
        return super().load_doc_before_save(raise_exception=raise_exception)

    def validate(self):
        # Lock before inserting even a draft. Otherwise an uncommitted draft can
        # block the current-read capacity query while its submit waits for this pool.
        lock_document("Sales Order", self.sales_order)
        lock_document("Harvest Forecast", self.forecast)
        forecast = frappe.get_doc("Harvest Forecast", self.forecast)
        forecast.check_permission("read")
        if forecast.docstatus != 1:
            frappe.throw("Only a submitted forecast can be reserved.")
        self.farm = forecast.farm
        so = frappe.get_doc("Sales Order", self.sales_order)
        so.check_permission("read")
        if so.docstatus != 1 or so.status in {"Closed", "Cancelled", "Completed", "On Hold"}:
            frappe.throw("Sales Order must be submitted and open.")
        if so.company != frappe.db.get_value("Farm", self.farm, "company"):
            frappe.throw("Sales Order and Farm must belong to the same Company.")
        row = next((r for r in so.items if r.name == self.sales_order_item), None)
        if not row or row.item_code != forecast.item_code:
            frappe.throw("Select the exact Sales Order Item matching the forecast Item.")
        if row.stock_uom != "Kg":
            frappe.throw("Pilot reservations require Sales Order stock UOM Kg.")
        if not row.delivery_date or not (
            getdate(forecast.period_start_date) <= getdate(row.delivery_date) <= getdate(forecast.period_end_date)
        ):
            frappe.throw("Sales Order Item delivery date must be inside the forecast period.")
        self.item_code = row.item_code
        self.customer = so.customer
        self.delivery_date = row.delivery_date
        try:
            quantity(self.reserved_qty_kg, "Reservation kg", positive=True)
        except SupplyError as exc:
            frappe.throw(str(exc))

    def before_submit(self):
        # All reservations lock SO first, then forecast: shared order avoids deadlocks.
        current_so = lock_document("Sales Order", self.sales_order)
        current_forecast = lock_document("Harvest Forecast", self.forecast)
        self.validate()  # Re-read demand and supply only AFTER acquiring the locks.
        forecast = frappe.get_doc("Harvest Forecast", self.forecast)
        if current_so.docstatus != 1 or current_so.status in {"Closed", "Cancelled", "Completed", "On Hold"}:
            frappe.throw("Sales Order is no longer open.")
        if current_forecast.docstatus != 1:
            frappe.throw("Forecast is no longer released.")
        rows = frappe.db.sql("SELECT * FROM `tabSales Order Item` WHERE name=%s AND parent=%s FOR UPDATE",
                             (self.sales_order_item, self.sales_order), as_dict=True)
        if not rows or rows[0].item_code != current_forecast.item_code or rows[0].stock_uom != "Kg":
            frappe.throw("Sales Order Item no longer matches forecast Item/UOM.")
        row = rows[0]
        remaining_demand = max(float(row.stock_qty) - float(row.delivered_qty or 0) * float(row.conversion_factor), 0)
        try:
            require_capacity(self.reserved_qty_kg, max(
                float(forecast.safe_saleable_kg) - materialized_total(forecast.name, locking=True), 0
            ), reservation_total(forecast=forecast.name, exclude=self.name, locking=True))
            require_capacity(self.reserved_qty_kg, remaining_demand,
                             reservation_total(sales_order_item=row.name, exclude=self.name, locking=True))
        except SupplyError as exc:
            frappe.throw(str(exc))

    def before_cancel(self):
        lock_document("Sales Order", self.sales_order)
        lock_document("Harvest Forecast", self.forecast)
