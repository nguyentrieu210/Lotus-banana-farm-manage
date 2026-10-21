"""Create standard ERPNext drafts; never write Stock Ledger or GL directly."""

import frappe
from frappe.utils import flt, now_datetime
from lotus_farm.controls import command, command_allowed, lock, positive, require_role, validate_item, validate_warehouse
from lotus_farm.rules import canonical_hash


@frappe.whitelist(methods=["POST"])
def set_output_valuation(packout, rates):
    require_role("Lotus Stock Reviewer")
    lock("Packout Run", packout)
    run = frappe.get_doc("Packout Run", packout)
    run.check_permission("write")
    if run.docstatus != 1 or run.qc_state != "Released":
        frappe.throw("Only a submitted, QC released Packout Run can be valued.")
    if len(run.outputs or []) < 2:
        frappe.throw("Manual output valuation is only required for multi-Item packout.")
    if run.stock_entry and frappe.db.get_value("Stock Entry", run.stock_entry, "docstatus") != 2:
        frappe.throw("Cancel the active Stock Entry before changing packout valuation.")

    rates = frappe.parse_json(rates) if isinstance(rates, str) else rates
    if not isinstance(rates, dict):
        frappe.throw("Valuation rates must be an Item-to-rate object.")

    expected = {row.item for row in run.outputs}
    if set(rates) != expected:
        frappe.throw("Provide one valuation rate for every finished Item, with no extras.")

    reviewed_at = now_datetime()
    for row in run.outputs:
        row.valuation_rate = positive(rates[row.item], f"Valuation rate for {row.item}")
        row.valuation_set_by = frappe.session.user
        row.valuation_set_at = reviewed_at
    with command(run, "valuation"):
        run.save()
    return {
        "packout": run.name,
        "items": [
            {"item": row.item, "valuation_rate": row.valuation_rate}
            for row in run.outputs
        ],
    }


@frappe.whitelist(methods=["POST"])
def make_repack_entry(packout):
    require_role("Lotus Packing Supervisor", "Lotus Stock Reviewer")
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
    multiple_finished = len(run.outputs) > 1
    if multiple_finished:
        missing = [
            output.item
            for output in run.outputs
            if flt(output.valuation_rate) <= 0 or not output.valuation_set_by
        ]
        if missing:
            frappe.throw(
                "Multi-Item Repack needs reviewed stock valuation rates first: "
                + ", ".join(missing)
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
                set_basic_rate_manually=1 if multiple_finished else 0,
                basic_rate=flt(output.valuation_rate) if multiple_finished else 0,
            ),
        )
    entry.insert()  # Core checks permissions, quantities, valuation and serial/batch rules.
    frappe.db.set_value("Packout Run", run.name, "stock_entry", entry.name)
    return {"stock_entry": entry.name, "docstatus": entry.docstatus}


def validate_entry(doc, method=None):
    before = doc.get_doc_before_save()
    if (doc.get('lotus_forecast_impacts_json') or '') != (before.get('lotus_forecast_impacts_json') or '' if before else ''):
        frappe.throw('Posted forecast impacts are written only by the stock bridge.')
    if not doc.get("lotus_packout_run"):
        return
    run = frappe.get_doc("Packout Run", doc.lotus_packout_run)
    run.check_permission("read")
    lock('Farm', run.farm)
    lock("Packout Run", doc.lotus_packout_run)
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
    expected_output_rates = {}

    def add(bucket, key, qty):
        bucket[key] = bucket.get(key, 0) + round(float(qty), 3)

    for source in run.sources:
        lot = frappe.get_doc("Harvest Lot", source.harvest_lot)
        add(expected_inputs, (lot.raw_item, lot.raw_warehouse, lot.raw_batch), source.input_kg)
    for output in run.outputs:
        key = (output.item, run.target_warehouse, output.batch)
        add(expected_outputs, key, output.net_kg)
        if len(run.outputs) > 1:
            if (
                flt(output.valuation_rate) <= 0
                or not output.valuation_set_by
                or not output.valuation_set_at
            ):
                frappe.throw("Multi-Item Packout must have reviewed valuation rates before Stock Entry.")
            expected_output_rates[key] = flt(output.valuation_rate, 6)
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
            key = (row.item_code, row.t_warehouse, batch_no)
            add(outputs, key, row.transfer_qty)
            if expected_output_rates:
                expected_rate = expected_output_rates.get(key)
                if (
                    expected_rate is None
                    or not row.set_basic_rate_manually
                    or abs(flt(row.basic_rate, 6) - expected_rate) > 0.000001
                ):
                    frappe.throw("Multi-Item Stock Entry valuation must match the reviewed Packout rates.")
        else:
            frappe.throw("Stock Entry row has no Warehouse.")
    if inputs != expected_inputs or outputs != expected_outputs:
        frappe.throw("Stock Entry input/output must exactly match Packout lineage and weights.")


def _forecast_outputs(run, use_snapshot=True):
    missing_posted_snapshot = False
    if use_snapshot and run.stock_entry:
        saved = frappe.db.get_value('Stock Entry', run.stock_entry, 'lotus_forecast_impacts_json')
        if saved:
            import json
            return json.loads(saved)
        missing_posted_snapshot = frappe.db.get_value('Stock Entry', run.stock_entry, 'docstatus') == 1
    totals = {}
    for source in run.sources:
        lot = frappe.get_doc("Harvest Lot", source.harvest_lot)
        for contribution in lot.sources:
            actual = frappe.get_doc("Harvest Actual", contribution.harvest_actual)
            from lotus_farm.onedrive_supply import actual_forecast_shares
            source_shares = actual_forecast_shares(actual)
            if source_shares is not None:
                if missing_posted_snapshot:
                    frappe.throw('Chứng từ kho OneDrive đã ghi sổ thiếu dấu kiểm ảnh hưởng dự thu; cần đối soát trước khi đảo kho.')
                for supply, physical_share in source_shares:
                    planned_items = {row.item for row in supply.output_plan} if supply.output_plan else {supply.item}
                    share = float(source.input_kg)/float(run.input_kg)*float(contribution.contributed_kg)/float(lot.released_raw_kg)*physical_share
                    bucket = totals.setdefault(supply.name, {})
                    for output in run.outputs:
                        if output.item in planned_items:
                            bucket[output.item] = bucket.get(output.item, 0)+float(output.net_kg)*share
                continue
            if not actual.forecast:
                from lotus_farm.harvest_matching import check_unlinked_stock
                check_unlinked_stock(actual)
                continue
            supply = frappe.get_doc("Harvest Forecast", actual.forecast)
            planned_items = (
                {row.item for row in supply.output_plan}
                if supply.output_plan
                else ({supply.item} if supply.item else set())
            )
            share = (
                float(source.input_kg)
                / float(run.input_kg)
                * float(contribution.contributed_kg)
                / float(lot.released_raw_kg)
            )
            bucket = totals.setdefault(actual.forecast, {})
            for output in run.outputs:
                if output.item in planned_items:
                    bucket[output.item] = bucket.get(output.item, 0) + float(output.net_kg) * share
    return totals


def stock_posted(doc, method=None):
    if not doc.get("lotus_packout_run"):
        return
    run = frappe.get_doc("Packout Run", doc.lotus_packout_run)
    frappe.db.set_value("Packout Run", run.name, "stock_entry", doc.name)
    # Physical finished stock replaces future supply per Item; no duplicated forecast + stock ATP.
    impacts = _forecast_outputs(run, use_snapshot=False)
    import json
    frappe.db.set_value('Stock Entry', doc.name, 'lotus_forecast_impacts_json', json.dumps(impacts, sort_keys=True))
    for name, item_amounts in sorted(impacts.items()):
        lock("Harvest Forecast", name)
        supply = frappe.get_doc("Harvest Forecast", name)
        if supply.output_plan:
            output_by_item = {row.item: row for row in supply.output_plan}
            for item, amount in item_amounts.items():
                output = output_by_item.get(item)
                if output:
                    output.materialized_qty_kg = float(output.materialized_qty_kg or 0) + amount
        else:
            amount = item_amounts.get(supply.item, 0)
            supply.materialized_qty_kg = float(supply.materialized_qty_kg or 0) + amount
        with command(supply, "supply"):
            supply.save(ignore_permissions=True)  # Authorized Stock Entry event, farm read checked above.


def before_stock_cancel(doc, method=None):
    if doc.get("lotus_packout_run"):
        from lotus_farm.daily_operations import day_guard
        day_guard(frappe.get_doc("Packout Run",doc.lotus_packout_run))
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
    for name, item_amounts in sorted(impacts.items()):
        lock("Harvest Forecast", name)
        supply = frappe.get_doc("Harvest Forecast", name)
        if supply.output_plan:
            output_by_item = {row.item: row for row in supply.output_plan}
            for item, amount in item_amounts.items():
                output = output_by_item.get(item)
                if not output or float(output.materialized_qty_kg or 0) + 0.0005 < float(amount):
                    frappe.throw("Per-Item forecast materialized quantity is smaller than the stock reversal.")
        else:
            amount = item_amounts.get(supply.item, 0)
            if float(supply.materialized_qty_kg or 0) + 0.0005 < float(amount):
                frappe.throw("Forecast materialized quantity is smaller than the stock reversal.")
        supplies[name] = (supply, item_amounts)

    for supply, item_amounts in supplies.values():
        if supply.output_plan:
            output_by_item = {row.item: row for row in supply.output_plan}
            for item, amount in item_amounts.items():
                output = output_by_item[item]
                output.materialized_qty_kg = max(float(output.materialized_qty_kg or 0) - amount, 0)
        else:
            amount = item_amounts.get(supply.item, 0)
            supply.materialized_qty_kg = max(float(supply.materialized_qty_kg or 0) - amount, 0)
        with command(supply, "supply"):
            supply.save(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def link_stock_reservation(forecast, allocation, stock_reservation, qty_kg=None):
    require_role("Lotus Sales Planner")
    farm = frappe.db.get_value('Harvest Forecast', forecast, 'farm')
    if farm: lock('Farm', farm)
    reservation = frappe.get_doc("Stock Reservation Entry", stock_reservation)
    reservation.check_permission("read")
    lock("Sales Order", reservation.voucher_no)
    lock("Stock Reservation Entry", reservation.name)
    lock("Harvest Forecast", forecast)
    reservation.reload()
    supply = frappe.get_doc("Harvest Forecast", forecast, for_update=True)
    supply.check_permission("write")
    row = next((r for r in supply.allocations or [] if r.name == allocation), None)
    if not row or reservation.docstatus != 1 or reservation.voucher_type != "Sales Order":
        frappe.throw("Select a submitted physical stock reservation and valid forecast allocation.")
    if row.stock_reservation == reservation.name and row.allocation_state == "Materialized":
        if qty_kg is not None and abs(float(qty_kg)-float(row.reserved_qty_kg))>0.0005:frappe.throw('This conversion already has a different quantity.')
        return {"allocation": row.name, "state": row.allocation_state}
    if (
        row.allocation_state != "Reserved"
        or row.sales_order != reservation.voucher_no
        or row.sales_order_item != reservation.voucher_detail_no
        or row.item != reservation.item_code
    ):
        frappe.throw("Physical reservation must match the exact forecast SO Item.")
    split = next((r for r in supply.allocations if r.materialized_from==allocation and r.stock_reservation==reservation.name and r.allocation_state=='Materialized'),None)
    if split:
        if qty_kg is not None and abs(float(qty_kg)-float(split.reserved_qty_kg))>0.0005:
            frappe.throw('This conversion already has a different quantity.')
        return {'allocation':split.name,'state':split.allocation_state,'remaining_future_kg':row.reserved_qty_kg}
    linked = frappe.get_all(
        'Forecast Allocation',filters={'stock_reservation':reservation.name,'allocation_state':'Materialized'},fields=['reserved_qty_kg'])
    if float(reservation.delivered_qty or 0):
        frappe.throw('Use a new undelivered physical reservation for further forecast conversion.')
    from lotus_farm.promax_rules import split_amount
    from lotus_farm.rules import RuleError
    try:
        amount,remainder=split_amount(row.reserved_qty_kg,float(reservation.reserved_qty)-sum(float(r.reserved_qty_kg) for r in linked),
                                      row.reserved_qty_kg if qty_kg is None else qty_kg)
    except RuleError as exc:frappe.throw(str(exc))
    from lotus_farm.allocations import _active_for_line
    order=frappe.get_doc('Sales Order',row.sales_order);order.check_permission('read')
    line=next(i for i in order.items if i.name==row.sales_order_item)
    remaining_demand=max(float(line.stock_qty)-float(line.delivered_qty or 0)*float(line.conversion_factor),0)
    if _active_for_line(line.name)-amount>remaining_demand+0.0005:
        frappe.throw('Physical plus remaining future commitments exceed the undelivered Sales Order demand. Convert enough or reduce the physical reservation.')
    converted=row
    if remainder:
        converted=supply.append('allocations',{k:row.get(k) for k in ('sales_order','sales_order_item','item','forecast_output','allocated_by','allocated_at')})
        converted.reserved_qty_kg=amount;converted.materialized_from=row.name;row.reserved_qty_kg=remainder
    converted.allocation_state,converted.stock_reservation='Materialized',reservation.name
    with command(supply,'allocation'):supply.save()
    return {'allocation':converted.name,'state':converted.allocation_state,'remaining_future_kg':remainder}



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
                remaining=next((r for r in supply.allocations if r.name!=row.name and r.sales_order_item==row.sales_order_item and r.item==row.item and r.allocation_state=='Reserved'),None) if restore else None
                if remaining:
                    remaining.reserved_qty_kg+=row.reserved_qty_kg
                    row.allocation_state='Released';row.restored_to=remaining.name
                else:
                    row.allocation_state = 'Reserved' if restore else 'Released'
                changed = True
        if changed:
            with command(supply, "allocation"):
                supply.save(ignore_permissions=True)
