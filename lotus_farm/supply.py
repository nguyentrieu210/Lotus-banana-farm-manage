"""Database helpers: caller owns the transaction; never commit inside commands."""
import frappe
from frappe.utils import flt


def lock_document(doctype, name):
    # Only fixed application-owned tables can be interpolated. Names remain parameters.
    if doctype not in {"Harvest Forecast", "Crop Cycle", "Sales Order", "Harvest Lot", "Packout Run", "Harvest Actual"}:
        raise ValueError("Unsupported lock table")
    rows = frappe.db.sql(f"SELECT * FROM `tab{doctype}` WHERE name=%s FOR UPDATE", (name,), as_dict=True)
    if not rows:
        frappe.throw(f"{doctype} {name} does not exist.")
    return rows[0]


def reservation_total(forecast=None, sales_order_item=None, exclude=None, locking=False):
    if locking:
        where = ["docstatus=1"]
        params = []
        for field, value in (("forecast", forecast), ("sales_order_item", sales_order_item)):
            if value:
                where.append(f"{field}=%s")
                params.append(value)
        if exclude:
            where.append("name!=%s")
            params.append(exclude)
        rows = frappe.db.sql("SELECT reserved_qty_kg FROM `tabForecast Reservation` WHERE " +
                              " AND ".join(where) + " LOCK IN SHARE MODE", tuple(params))
        return sum(flt(row[0]) for row in rows)
    filters = {"docstatus": 1}
    if forecast:
        filters["forecast"] = forecast
    if sales_order_item:
        filters["sales_order_item"] = sales_order_item
    if exclude:
        filters["name"] = ["!=", exclude]
    return sum(flt(r.reserved_qty_kg) for r in frappe.get_all(
        "Forecast Reservation", filters=filters, fields=["reserved_qty_kg"]
    ))


def materialized_total(forecast, locking=False):
    if locking:
        return sum(flt(r[0]) for r in frappe.db.sql(
            "SELECT retired_forecast_kg FROM `tabForecast Materialization` WHERE forecast=%s AND docstatus=1 FOR UPDATE",
            (forecast,),
        ))
    return sum(flt(r.retired_forecast_kg) for r in frappe.get_all(
        "Forecast Materialization", filters={"forecast": forecast, "docstatus": 1},
        fields=["retired_forecast_kg"]
    ))


def availability(forecast):
    reserved = reservation_total(forecast.name)
    retired = materialized_total(forecast.name)
    atp = flt(forecast.safe_saleable_kg) - retired - reserved
    return {
        "committed_qty_kg": reserved, "materialized_qty_kg": retired,
        "available_to_promise_kg": atp, "shortage_kg": max(-atp, 0),
        "availability_status": "Overcommitted" if atp < 0 else (
            "Tight" if atp <= 0.1 * flt(forecast.safe_saleable_kg) else "Available"
        ),
    }
