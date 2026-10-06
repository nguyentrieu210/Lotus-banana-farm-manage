"""Create standard ERPNext drafts; never write Stock Ledger or GL directly."""

import frappe
from lotus_farm.controls import command, command_allowed, lock, require_role, validate_item, validate_warehouse
from lotus_farm.rules import canonical_hash


@frappe.whitelist(methods=["POST"])
def make_repack_entry(packout):
    require_role("Lotus Packing Supervisor")
    lock("Packout Run", packout)
    run = frappe.get_doc("Packout Run", packout)
    run.check_permission("read")
    if run.docstatus != 1 or run.qc_state != "Released":
        frappe.throw("Only submitted, QC released packout can create an ERPNext draft.")
    if run.stock_entry:
        entry = frappe.get_doc("Stock Entry", run.stock_entry)
        entry.check_permission("read")
        if entry.docstatus != 2:
            return {"stock_entry": entry.name, "docstatus": entry.docstatus}
    entry = frappe.get_doc(
        dict(
            doctype="Stock Entry",
            stock_entry_type="Repack",
            purpose="Repack",
            company=run.company,
            lotus_packout_run=run.name,
            posting_date=run.packing_date,
            items=[],
        )
    )
    for source in run.sources:
        lot = frappe.get_doc("Harvest Lot", source.harvest_lot)
        lot.check_permission("read")
        if not all((lot.raw_item, lot.raw_warehouse, lot.raw_batch)):
            frappe.throw("Receive raw inventory in ERPNext and map Item/Warehouse/Batch on each lot first.")
        validate_item(lot.raw_item, batched=True)
        validate_warehouse(lot.raw_warehouse, run.company)
        entry.append(
            "items",
            dict(
                item_code=lot.raw_item,
                s_warehouse=lot.raw_warehouse,
                qty=source.input_kg,
                uom="Kg",
                stock_uom="Kg",
                conversion_factor=1,
                batch_no=lot.raw_batch,
                use_serial_batch_fields=1,
            ),
        )
    for output in run.outputs:
        # Stable Batch ID means transaction retries never create duplicate batches.
        batch_id = "LOTUS-" + canonical_hash([run.name, output.item])[:24]
        existing = frappe.db.get_value("Batch", {"batch_id": batch_id}, "name")
        if existing:
            if frappe.db.get_value("Batch", existing, "item") != output.item:
                frappe.throw("Output Batch identity conflict.")
            batch = frappe.get_doc("Batch", existing)
            batch.check_permission("read")
        else:
            batch = frappe.get_doc(
                dict(
                    doctype="Batch", batch_id=batch_id, item=output.item, manufacturing_date=run.packing_date
                )
            ).insert()
        frappe.db.set_value("Packout Output", output.name, "batch", batch.name)
        entry.append(
            "items",
            dict(
                item_code=output.item,
                t_warehouse=run.target_warehouse,
                qty=output.net_kg,
                uom="Kg",
                stock_uom="Kg",
                conversion_factor=1,
                batch_no=batch.name,
                use_serial_batch_fields=1,
                is_finished_item=1,
            ),
        )
    entry.insert()  # Core checks permissions, quantities, valuation and serial/batch rules.
    frappe.db.set_value("Packout Run", run.name, "stock_entry", entry.name)
    return {"stock_entry": entry.name, "docstatus": entry.docstatus}


def validate_entry(doc, method=None):
    if not doc.get("lotus_packout_run"):
        return
    lock("Packout Run", doc.lotus_packout_run)
    run = frappe.get_doc("Packout Run", doc.lotus_packout_run)
    run.check_permission("read")
    if (
        run.docstatus != 1
        or run.qc_state != "Released"
        or doc.company != run.company
        or doc.purpose != "Repack"
    ):
        frappe.throw("Stock Entry must match a submitted, released Lotus Packout Run.")
    if run.stock_entry and run.stock_entry != doc.name:
        prior_status = frappe.db.get_value("Stock Entry", run.stock_entry, "docstatus")
        if prior_status != 2:
            frappe.throw("Packout already has a different active Stock Entry.")
    expected_inputs, expected_outputs = {}, {}

    def add(bucket, key, qty):
        bucket[key] = bucket.get(key, 0) + round(float(qty), 3)

    for source in run.sources:
        lot = frappe.get_doc("Harvest Lot", source.harvest_lot)
        add(expected_inputs, (lot.raw_item, lot.raw_warehouse, lot.raw_batch), source.input_kg)
    for output in run.outputs:
        add(expected_outputs, (output.item, run.target_warehouse, output.batch), output.net_kg)
    inputs, outputs = {}, {}
    for row in doc.items:
        batch_no = row.batch_no
        # ERPNext v15+ may replace legacy batch fields with a bundle on submission.
        if row.serial_and_batch_bundle:
            bundle = frappe.get_doc("Serial and Batch Bundle", row.serial_and_batch_bundle)
            if len(bundle.entries) != 1:
                frappe.throw("Lotus bridge requires one Batch per Stock Entry row.")
            batch_no = bundle.entries[0].batch_no
        if row.stock_uom != "Kg" or (row.s_warehouse and row.t_warehouse):
            frappe.throw("Lotus bridge requires separate input/output rows in Kg.")
        if row.s_warehouse:
            add(inputs, (row.item_code, row.s_warehouse, batch_no), row.transfer_qty)
        elif row.t_warehouse:
            add(outputs, (row.item_code, row.t_warehouse, batch_no), row.transfer_qty)
        else:
            frappe.throw("Stock Entry row has no Warehouse.")
    if inputs != expected_inputs or outputs != expected_outputs:
        frappe.throw("Stock Entry input/output must exactly match Packout lineage and weights.")


def _forecast_outputs(run):
    totals = {}
    for source in run.sources:
        lot = frappe.get_doc("Harvest Lot", source.harvest_lot)
        for contribution in lot.sources:
            actual = frappe.get_doc("Harvest Actual", contribution.harvest_actual)
            if not actual.forecast:
                continue
            item = frappe.db.get_value("Harvest Forecast", actual.forecast, "item")
            net = sum(float(o.net_kg) for o in run.outputs if o.item == item)
            share = (
                float(source.input_kg)
                / float(run.input_kg)
                * float(contribution.contributed_kg)
                / float(lot.released_raw_kg)
            )
            totals[actual.forecast] = totals.get(actual.forecast, 0) + net * share
    return totals


def stock_posted(doc, method=None):
    if not doc.get("lotus_packout_run"):
        return
    run = frappe.get_doc("Packout Run", doc.lotus_packout_run)
    frappe.db.set_value("Packout Run", run.name, "stock_entry", doc.name)
    # Physical finished stock replaces future supply; no duplicated forecast + stock ATP.
    for name, amount in sorted(_forecast_outputs(run).items()):
        lock("Harvest Forecast", name)
        supply = frappe.get_doc("Harvest Forecast", name)
        supply.materialized_qty_kg = float(supply.materialized_qty_kg or 0) + amount
        with command(supply, "supply"):
            supply.save(ignore_permissions=True)  # Authorized Stock Entry event, farm read checked above.


def before_stock_cancel(doc, method=None):
    if doc.get("lotus_packout_run") and not command_allowed(doc, "reconciliation_cancel"):
        frappe.throw(
            "Create and apply an approved Supply Reconciliation before cancelling Lotus stock."
        )


def stock_reversed(doc, method=None):
    if not doc.get("lotus_packout_run"):
        return
    if not command_allowed(doc, "reconciliation_cancel"):
        frappe.throw("Lotus stock reversal must run through Supply Reconciliation.")
    run = frappe.get_doc("Packout Run", doc.lotus_packout_run)
    impacts = _forecast_outputs(run)
    supplies = {}
    for name, amount in sorted(impacts.items()):
        lock("Harvest Forecast", name)
        supply = frappe.get_doc("Harvest Forecast", name)
        if float(supply.materialized_qty_kg or 0) + 0.0005 < float(amount):
            frappe.throw("Forecast materialized quantity is smaller than the stock reversal.")
        supplies[name] = (supply, float(amount))
    for supply, amount in supplies.values():
        supply.materialized_qty_kg = max(float(supply.materialized_qty_kg or 0) - amount, 0)
        with command(supply, "supply"):
            supply.save(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def link_stock_reservation(forecast, allocation, stock_reservation):
    require_role("Lotus Sales Planner")
    reservation = frappe.get_doc("Stock Reservation Entry", stock_reservation)
    reservation.check_permission("read")
    lock("Sales Order", reservation.voucher_no)
    lock("Stock Reservation Entry", reservation.name)
    lock("Harvest Forecast", forecast)
    reservation.reload()
    supply = frappe.get_doc("Harvest Forecast", forecast)
    supply.check_permission("write")
    row = next((r for r in supply.allocations or [] if r.name == allocation), None)
    if not row or reservation.docstatus != 1 or reservation.voucher_type != "Sales Order":
        frappe.throw("Select a submitted physical stock reservation and valid forecast allocation.")
    if row.stock_reservation == reservation.name and row.allocation_state == "Materialized":
        return {"allocation": row.name, "state": row.allocation_state}
    if (
        row.allocation_state != "Reserved"
        or row.sales_order != reservation.voucher_no
        or row.sales_order_item != reservation.voucher_detail_no
        or row.item != reservation.item_code
    ):
        frappe.throw("Physical reservation must match the exact forecast SO Item.")
    linked = frappe.get_all(
        "Forecast Allocation",
        filters={"stock_reservation": reservation.name, "allocation_state": "Materialized"},
        fields=["reserved_qty_kg"],
    )
    if (
        sum(float(r.reserved_qty_kg) for r in linked) + float(row.reserved_qty_kg)
        > float(reservation.reserved_qty) + 0.0005
    ):
        frappe.throw("Physical reservation is too small for these allocations.")
    row.allocation_state, row.stock_reservation = "Materialized", reservation.name
    with command(supply, "allocation"):
        supply.save()
    return {"allocation": row.name, "state": row.allocation_state}


def reservation_cancel(doc, method=None):
    allowed = command_allowed(doc, "reconciliation_cancel_restore") or command_allowed(
        doc, "reconciliation_cancel_release"
    )
    if frappe.db.exists(
        "Forecast Allocation", {"stock_reservation": doc.name, "allocation_state": "Materialized"}
    ) and not allowed:
        frappe.throw(
            "Create and apply an approved Supply Reconciliation before cancelling this physical reservation."
        )


def reservation_cancelled(doc, method=None):
    restore = command_allowed(doc, "reconciliation_cancel_restore")
    release = command_allowed(doc, "reconciliation_cancel_release")
    if not (restore or release):
        return
    linked = frappe.get_all(
        "Forecast Allocation",
        filters={
            "stock_reservation": doc.name,
            "allocation_state": "Materialized",
            "parenttype": "Harvest Forecast",
        },
        fields=["name", "parent"],
        order_by="parent, name",
    )
    for forecast in sorted({row.parent for row in linked}):
        lock("Harvest Forecast", forecast)
        supply = frappe.get_doc("Harvest Forecast", forecast)
        changed = False
        names = {row.name for row in linked if row.parent == forecast}
        for row in supply.allocations or []:
            if row.name in names and row.allocation_state == "Materialized":
                row.allocation_state = "Reserved" if restore else "Released"
                changed = True
        if changed:
            with command(supply, "allocation"):
                supply.save(ignore_permissions=True)
