import json

import frappe
from frappe.utils import flt, now_datetime

from lotus_farm.controls import command, lock, require_role
from lotus_farm.rules import canonical_hash
from lotus_farm.stock_bridge import _forecast_outputs


def _linked_materialized_allocations(stock_reservation):
    return frappe.get_all(
        "Forecast Allocation",
        filters={
            "stock_reservation": stock_reservation,
            "allocation_state": "Materialized",
            "parenttype": "Harvest Forecast",
        },
        fields=["name", "parent", "reserved_qty_kg", "sales_order", "sales_order_item", "item"],
        order_by="parent, name",
    )


def _stock_entry_effect(request):
    if not request.stock_entry or request.stock_reservation:
        frappe.throw("Stock Entry Reversal requires exactly one Stock Entry target.")
    lock("Stock Entry", request.stock_entry)
    entry = frappe.get_doc("Stock Entry", request.stock_entry)
    entry.check_permission("read")
    if entry.docstatus != 1 or not entry.get("lotus_packout_run"):
        frappe.throw("Select a submitted Lotus Repack Stock Entry.")
    run = frappe.get_doc("Packout Run", entry.lotus_packout_run)
    run.check_permission("read")
    if run.farm != request.farm:
        frappe.throw("Reconciliation Farm must match the Packout Run.")

    forecast_totals = _forecast_outputs(run)
    impacts = []
    active_reservations = set()
    for forecast in sorted(forecast_totals):
        lock("Harvest Forecast", forecast)
        supply = frappe.get_doc("Harvest Forecast", forecast)
        item_amounts = forecast_totals[forecast]
        amount = flt(sum(item_amounts.values()), 3)
        if supply.output_plan:
            materialized = {row.item: flt(row.materialized_qty_kg, 3) for row in supply.output_plan}
            for item, item_amount in item_amounts.items():
                if materialized.get(item, 0) + 0.0005 < flt(item_amount, 3):
                    frappe.throw("Per-Item forecast materialized quantity is smaller than the proposed reversal.")
        elif flt(supply.materialized_qty_kg, 3) + 0.0005 < amount:
            frappe.throw("Forecast materialized quantity is smaller than the proposed reversal.")
        impacts.append(
            {
                "forecast": forecast,
                "qty_kg": amount,
                "items": [
                    {"item": item, "qty_kg": flt(item_amount, 3)}
                    for item, item_amount in sorted(item_amounts.items())
                ],
            }
        )
        for row in frappe.get_all(
            "Forecast Allocation",
            filters={
                "parent": forecast,
                "parenttype": "Harvest Forecast",
                "allocation_state": "Materialized",
            },
            fields=["stock_reservation"],
        ):
            if row.stock_reservation and frappe.db.get_value(
                "Stock Reservation Entry", row.stock_reservation, "docstatus"
            ) == 1:
                active_reservations.add(row.stock_reservation)
    if active_reservations:
        frappe.throw(
            "Cancel linked physical Stock Reservations through reconciliation first: "
            + ", ".join(sorted(active_reservations))
        )
    return {
        "type": "Stock Entry Reversal",
        "farm": request.farm,
        "stock_entry": entry.name,
        "packout_run": run.name,
        "forecast_impacts": impacts,
    }


def _stock_reservation_effect(request):
    if not request.stock_reservation or request.stock_entry:
        frappe.throw("Stock Reservation Cancellation requires exactly one Stock Reservation Entry.")
    lock("Stock Reservation Entry", request.stock_reservation)
    reservation = frappe.get_doc("Stock Reservation Entry", request.stock_reservation)
    reservation.check_permission("read")
    if reservation.docstatus != 1 or reservation.voucher_type != "Sales Order":
        frappe.throw("Select a submitted Sales Order Stock Reservation Entry.")
    if flt(reservation.delivered_qty) or flt(reservation.consumed_qty) or flt(reservation.transferred_qty):
        frappe.throw("Delivered, consumed or transferred reservations must be reconciled downstream first.")

    rows = _linked_materialized_allocations(reservation.name)
    if not rows:
        frappe.throw("This physical reservation has no active Lotus allocation.")
    effects = []
    farms = set()
    for row in rows:
        lock("Harvest Forecast", row.parent)
        supply = frappe.get_doc("Harvest Forecast", row.parent)
        supply.check_permission("read")
        farms.add(supply.farm)
        if (
            row.sales_order != reservation.voucher_no
            or row.sales_order_item != reservation.voucher_detail_no
            or row.item != reservation.item_code
        ):
            frappe.throw("Linked Lotus allocation no longer matches the physical reservation.")
        effects.append(
            {
                "forecast": row.parent,
                "allocation": row.name,
                "qty_kg": flt(row.reserved_qty_kg, 3),
            }
        )
    if farms != {request.farm}:
        frappe.throw("One reconciliation can only cover physical reservations from one Farm.")
    return {
        "type": "Stock Reservation Cancellation",
        "farm": request.farm,
        "stock_reservation": reservation.name,
        "sales_order": reservation.voucher_no,
        "sales_order_item": reservation.voucher_detail_no,
        "reservation_disposition": request.reservation_disposition,
        "allocation_impacts": effects,
    }


def build_effect(request):
    if request.reconciliation_type == "Stock Entry Reversal":
        return _stock_entry_effect(request)
    if request.reconciliation_type == "Stock Reservation Cancellation":
        return _stock_reservation_effect(request)
    frappe.throw("Unsupported reconciliation type.")


def approve(request):
    require_role("Lotus Auditor")
    effect = build_effect(request)
    request.effect_json = json.dumps(effect, sort_keys=True, separators=(",", ":"), default=str)
    request.effect_hash = canonical_hash(effect)
    request.state = "Approved"
    request.reviewed_by = frappe.session.user
    request.reviewed_at = now_datetime()


@frappe.whitelist(methods=["POST"])
def execute(reconciliation):
    lock("Supply Reconciliation", reconciliation)
    request = frappe.get_doc("Supply Reconciliation", reconciliation)
    request.check_permission("read")
    if request.docstatus != 1 or request.state != "Approved":
        frappe.throw("Only submitted, approved reconciliations can be applied.")
    if request.reconciliation_type == "Stock Entry Reversal":
        require_role("Lotus Packing Supervisor", "Lotus Auditor")
    else:
        require_role("Lotus Sales Planner", "Lotus Auditor")

    effect = build_effect(request)
    if canonical_hash(effect) != request.effect_hash:
        frappe.throw("Target changed after approval; review and approve a new reconciliation.")

    if request.reconciliation_type == "Stock Entry Reversal":
        target = frappe.get_doc("Stock Entry", request.stock_entry)
        action = "reconciliation_cancel"
    else:
        target = frappe.get_doc("Stock Reservation Entry", request.stock_reservation)
        action = (
            "reconciliation_cancel_restore"
            if request.reservation_disposition == "Restore Future Reservation"
            else "reconciliation_cancel_release"
        )
    target.check_permission("cancel")
    # The approved reconciliation itself must not block the cancellation it authorizes.
    # Keep every other Frappe backlink check active.
    ignored = set(target.get("ignore_linked_doctypes") or [])
    ignored.add("Supply Reconciliation")
    target.set("ignore_linked_doctypes", sorted(ignored))
    with command(target, action):
        target.cancel()

    applied_at = now_datetime()
    frappe.db.set_value(
        "Supply Reconciliation",
        request.name,
        {
            "state": "Applied",
            "applied_by": frappe.session.user,
            "applied_at": applied_at,
        },
        update_modified=True,
    )
    return {
        "reconciliation": request.name,
        "state": "Applied",
        "target": target.name,
        "target_docstatus": target.docstatus,
    }
