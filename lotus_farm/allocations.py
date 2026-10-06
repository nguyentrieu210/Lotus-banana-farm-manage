"""Future supply only. ERPNext owns physical stock reservations."""

import json
import frappe
from frappe.utils import now_datetime

from lotus_farm.controls import command, lock, require_role, validate_item
from lotus_farm.rules import RuleError, reserve_limit, canonical_hash


def _active_for_line(line):
    # Called with the Sales Order locked, so cross-forecast reservations serialize.
    future = sum(
        float(r.reserved_qty_kg)
        for r in frappe.get_all(
            "Forecast Allocation",
            filters={
                "sales_order_item": line,
                "allocation_state": "Reserved",
                "parenttype": "Harvest Forecast",
            },
            fields=["reserved_qty_kg"],
        )
    )
    physical = sum(
        max(float(r.reserved_qty) - float(r.delivered_qty or 0), 0)
        for r in frappe.get_all(
            "Stock Reservation Entry",
            filters={"voucher_type": "Sales Order", "voucher_detail_no": line, "docstatus": 1},
            fields=["reserved_qty", "delivered_qty"],
        )
    )
    return future + physical


@frappe.whitelist(methods=["POST"])
def reserve(forecast, sales_order, sales_order_item, qty_kg, client_event_id):
    require_role("Lotus Sales Planner")
    lock("Sales Order", sales_order)
    lock("Harvest Forecast", forecast)
    if not client_event_id:
        frappe.throw("client_event_id is required for allocation retries.")
    event_key = canonical_hash(["allocation", frappe.session.user, client_event_id])
    payload_hash = canonical_hash([forecast, sales_order, sales_order_item, str(qty_kg)])
    existing = frappe.db.get_value("Integration Event", {"event_key": event_key}, "name")
    if existing:
        event = frappe.get_doc("Integration Event", existing)
        event.check_permission("read")
        if event.payload_hash != payload_hash:
            frappe.throw("Allocation event ID already has a different payload.")
        return json.loads(event.result_json)
    supply = frappe.get_doc("Harvest Forecast", forecast)
    supply.check_permission("write")
    if supply.supply_state != "Released":
        frappe.throw("Only released future supply can be reserved.")
    order = frappe.get_doc("Sales Order", sales_order)
    order.check_permission("read")
    if (
        order.docstatus != 1
        or order.status in ("Closed", "Cancelled")
        or order.company != frappe.db.get_value("Farm", supply.farm, "company")
    ):
        frappe.throw("Sales Order must be open, submitted and belong to the Farm Company.")
    line = next((r for r in order.items if r.name == sales_order_item), None)
    if not line or line.item_code != supply.item:
        frappe.throw("Select the exact Sales Order Item matching forecast supply.")
    validate_item(supply.item)
    # ERPNext stock_qty is already converted to Item stock UOM (Kg). Delivered qty is in sales UOM.
    remaining_demand = max(
        float(line.stock_qty) - float(line.delivered_qty or 0) * float(line.conversion_factor), 0
    )
    committed = sum(
        float(r.reserved_qty_kg) for r in supply.allocations or [] if r.allocation_state == "Reserved"
    )
    try:
        amount = reserve_limit(
            max(float(supply.safe_saleable_kg) - float(supply.materialized_qty_kg or 0), 0),
            committed,
            qty_kg,
            max(remaining_demand - _active_for_line(line.name), 0),
        )
    except RuleError as exc:
        frappe.throw(str(exc))
    row = next(
        (
            r
            for r in supply.allocations or []
            if r.sales_order_item == line.name and r.allocation_state == "Reserved"
        ),
        None,
    )
    if row:
        row.reserved_qty_kg += amount
    else:
        row = supply.append(
            "allocations",
            dict(
                sales_order=sales_order,
                sales_order_item=line.name,
                reserved_qty_kg=amount,
                allocation_state="Reserved",
                allocated_by=frappe.session.user,
                allocated_at=now_datetime(),
            ),
        )
    with command(supply, "allocation"):
        supply.save()
    result = {"forecast": supply.name, "allocation": row.name, "atp_kg": supply.available_to_promise_kg}
    event = frappe.get_doc(
        dict(
            doctype="Integration Event",
            farm=supply.farm,
            event_key=event_key,
            payload_hash=payload_hash,
            result_json=json.dumps(result),
        )
    )
    with command(event, "integration_event"):
        event.insert()
    return result


@frappe.whitelist(methods=["POST"])
def release(forecast, allocation):
    require_role("Lotus Sales Planner")
    lock("Harvest Forecast", forecast)
    supply = frappe.get_doc("Harvest Forecast", forecast)
    supply.check_permission("write")
    row = next((r for r in supply.allocations or [] if r.name == allocation), None)
    if not row:
        frappe.throw("Allocation does not belong to this forecast.")
    if row.allocation_state == "Materialized":
        frappe.throw("Release physical reservations through ERPNext.")
    row.allocation_state = "Released"
    with command(supply, "allocation"):
        supply.save()
    return {"atp_kg": supply.available_to_promise_kg}


def sales_order_cancel(doc, method=None):
    # Block before ERP cancellation; historical commitments remain auditable.
    if frappe.db.exists("Forecast Allocation", {"sales_order": doc.name, "allocation_state": "Reserved"}):
        frappe.throw("Release Lotus forecast allocations before cancelling this Sales Order.")
