from copy import deepcopy
import frappe
from lotus_farm.controls import require_role, local_timestamp, whole_count
from lotus_farm.rules import canonical_hash


def _insert_idempotent(doctype, key_field, key, payload, submit=False):
    payload_hash = canonical_hash(payload)
    existing = frappe.db.get_value(doctype, {key_field: key}, "name")
    if existing:
        doc = frappe.get_doc(doctype, existing)
        doc.check_permission("read")
        if doc.client_payload_hash != payload_hash:
            frappe.throw("This event ID already belongs to a different payload.")
        if submit and doc.docstatus != 1:
            frappe.throw("This event is not a submitted document; reconcile it before retrying.")
        return doc
    frappe.db.savepoint("lotus_event")
    try:
        doc = frappe.get_doc(dict(doctype=doctype, **deepcopy(payload)))
        doc.set(key_field, key)
        doc.client_payload_hash = payload_hash
        doc.insert()
        if submit:
            doc.submit()
        return doc
    except frappe.DuplicateEntryError:
        frappe.db.rollback(save_point="lotus_event")
        existing = frappe.db.get_value(doctype, {key_field: key}, "name")
        if not existing:
            raise
        doc = frappe.get_doc(doctype, existing)
        doc.check_permission("read")
        if doc.client_payload_hash != payload_hash:
            frappe.throw("Conflicting payload for an existing event ID.")
        if submit and doc.docstatus != 1:
            frappe.throw("This event is not a submitted document; reconcile it before retrying.")
        return doc


@frappe.whitelist(methods=["POST"])
def create_operation(
    client_event_id,
    farm,
    farm_block,
    crop_cycle,
    operation_date,
    operation_type,
    bunch_qty,
    rejected_qty=0,
    sucker_selection_batch=None,
    harvest_profile=None,
):
    require_role("Lotus Farm Manager", "Lotus Integration User")
    if not client_event_id:
        frappe.throw("client_event_id is required for retries.")
    payload = dict(
        farm=farm,
        farm_block=farm_block,
        crop_cycle=crop_cycle,
        operation_date=str(local_timestamp(operation_date).date()),
        operation_type=operation_type,
        bunch_qty=whole_count(bunch_qty, "Bunch quantity"),
        rejected_qty=whole_count(rejected_qty, "Rejected bunch quantity"),
        sucker_selection_batch=sucker_selection_batch,
        harvest_profile=harvest_profile,
    )
    doc = _insert_idempotent("Bunch Operation", "client_event_id", client_event_id, payload, submit=True)
    return {
        "document": doc.name,
        "net_bunch_qty": doc.net_bunch_qty,
        "client_event_id": client_event_id,
        "server_received_at": doc.server_received_at,
    }


@frappe.whitelist(methods=["POST"])
def ingest_scale(farm, device_id, reading_id, captured_at, gross_kg, tare_kg):
    require_role("Lotus Integration User")
    if not device_id or not reading_id:
        frappe.throw("Device and reading IDs are required.")
    payload = dict(
        farm=farm,
        device_id=device_id,
        reading_id=reading_id,
        captured_at=str(local_timestamp(captured_at)),
        gross_kg=float(gross_kg),
        tare_kg=float(tare_kg),
    )
    key = canonical_hash([farm, device_id, reading_id])
    doc = _insert_idempotent("Scale Reading", "event_key", key, payload)
    return {"document": doc.name, "net_kg": doc.net_kg, "server_received_at": doc.server_received_at}


@frappe.whitelist()
def availability(period_start, period_end, farm=None, item=None):
    # Parent get_list enforces role + Farm User Permission and custom query hooks.
    filters = {
        "supply_state": "Released",
        "period_start_date": ["<=", period_end],
        "period_end_date": [">=", period_start],
    }
    if farm:
        filters["farm"] = farm

    forecasts = frappe.get_list(
        "Harvest Forecast",
        filters=filters,
        fields=[
            "name",
            "farm",
            "farm_block",
            "crop_cycle",
            "sucker_selection_batch",
            "forecast_basis",
            "confidence",
            "item",
            "period_start_date",
            "period_end_date",
            "gross_forecast_kg",
            "saleable_forecast_kg",
            "packed_forecast_kg",
            "safe_saleable_kg",
            "materialized_qty_kg",
            "committed_qty_kg",
            "available_to_promise_kg",
            "shortage_kg",
            "snapshot_hash",
        ],
        order_by="period_start_date, farm",
        limit_page_length=500,
    )

    result = []
    for forecast in forecasts:
        outputs = frappe.get_all(
            "Forecast Output Plan",
            filters={
                "parent": forecast.name,
                "parenttype": "Harvest Forecast",
                "parentfield": "output_plan",
            },
            fields=[
                "name",
                "item",
                "yield_percent",
                "expected_packed_kg",
                "safe_commit_kg",
                "materialized_qty_kg",
                "committed_qty_kg",
                "available_to_promise_kg",
                "shortage_kg",
                "availability_status",
            ],
            order_by="idx",
        )
        if outputs:
            for output in outputs:
                if item and output.item != item:
                    continue
                row = dict(forecast)
                row.update(
                    {
                        "forecast_output": output.name,
                        "item": output.item,
                        "yield_percent": output.yield_percent,
                        "packed_forecast_kg": output.expected_packed_kg,
                        "safe_saleable_kg": output.safe_commit_kg,
                        "materialized_qty_kg": output.materialized_qty_kg,
                        "committed_qty_kg": output.committed_qty_kg,
                        "available_to_promise_kg": output.available_to_promise_kg,
                        "shortage_kg": output.shortage_kg,
                        "availability_status": output.availability_status,
                    }
                )
                result.append(row)
        elif not item or forecast.item == item:
            row = dict(forecast)
            row["forecast_output"] = None
            result.append(row)
    return result
