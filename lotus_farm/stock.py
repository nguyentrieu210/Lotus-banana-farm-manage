"""First-receipt pilot bridge. ERPNext owns stock ledger and accounting."""
import frappe
from frappe.utils import flt

from lotus_farm.supply import lock_document, materialized_total


@frappe.whitelist(methods=["POST"])
def create_stock_entry(packout_run):
    lock_document("Packout Run", packout_run)
    run = frappe.get_doc("Packout Run", packout_run)
    run.check_permission("read")
    frappe.has_permission("Stock Entry", "create", throw=True)
    if run.docstatus != 1 or run.qc_status != "Released":
        frappe.throw("Only submitted QC-released packout can enter stock.")
    if run.stock_entry:
        entry = frappe.get_doc("Stock Entry", run.stock_entry)
        entry.check_permission("read")
        if entry.docstatus != 2:
            return entry.name
        frappe.throw("This run has a cancelled receipt. Amend the packout before re-posting.")
    entry = frappe.new_doc("Stock Entry")
    entry.stock_entry_type = "Material Receipt"
    entry.company = run.company
    entry.posting_date = run.packing_date
    entry.lotus_packout_run = run.name
    entry.remarks = f"Lotus measured packout {run.name}; first stock recognition (raw fruit not in ERP stock)."
    for row in run.outputs:
        if row.output_type == "Waste" or not flt(row.net_kg):
            continue
        if flt(row.valuation_rate) <= 0:
            frappe.throw("Finance must supply a positive valuation rate for every stock output.")
        batch = None
        if frappe.db.get_value("Item", row.item_code, "has_batch_no"):
            batch = frappe.get_doc({"doctype": "Batch", "batch_id": f"LF-{run.name}-{row.idx}",
                                    "item": row.item_code, "lotus_packout_run": run.name}).insert()
        entry.append("items", {"item_code": row.item_code, "qty": row.net_kg,
                               "uom": "Kg", "stock_uom": "Kg", "conversion_factor": 1,
                               "t_warehouse": run.target_warehouse, "basic_rate": row.valuation_rate,
                               "batch_no": batch.name if batch else None,
                               "use_serial_batch_fields": 1 if batch else 0})
    if not entry.items:
        frappe.throw("Packout has no stock output to receive.")
    entry.insert()  # Draft: normal ERPNext permission/valuation/QC/finance checks still apply.
    run.db_set("stock_entry", entry.name)
    return entry.name


def validate_receipt(doc, method=None):
    linked = frappe.db.get_value("Packout Run", {"stock_entry": doc.name}, "name")
    if linked and doc.get("lotus_packout_run") != linked:
        frappe.throw("The Lotus link cannot be removed or changed on a packout receipt.")
    if not doc.get("lotus_packout_run"):
        return
    lock_document("Packout Run", doc.lotus_packout_run)
    run = frappe.get_doc("Packout Run", doc.lotus_packout_run)
    if run.docstatus != 1 or run.qc_status != "Released" or run.stock_entry != doc.name:
        frappe.throw("Stock Entry must be the linked receipt of a submitted QC-released packout.")
    if doc.purpose != "Material Receipt" or doc.company != run.company:
        frappe.throw("Lotus pilot supports only first-recognition Material Receipt in the Farm Company.")
    expected = [(r.item_code, flt(r.net_kg, 6), run.target_warehouse) for r in run.outputs
                if r.output_type != "Waste" and flt(r.net_kg)]
    actual = [(r.item_code, flt(r.transfer_qty, 6), r.t_warehouse) for r in doc.items]
    if sorted(expected) != sorted(actual) or any(r.s_warehouse for r in doc.items):
        frappe.throw("Receipt Items, kilograms and Warehouse must match the measured packout outputs.")
    for row in doc.items:
        if frappe.db.get_value("Item", row.item_code, "has_batch_no"):
            # ERPNext may generate a Serial and Batch Bundle from batch_no on submit.
            batches = [row.batch_no] if row.batch_no else []
            if row.serial_and_batch_bundle:
                bundle = frappe.get_doc("Serial and Batch Bundle", row.serial_and_batch_bundle)
                batches = [r.batch_no for r in bundle.entries if r.batch_no]
            if not batches or any(frappe.db.get_value("Batch", b, "lotus_packout_run") != run.name for b in batches):
                frappe.throw("Receipt Batch must preserve Lotus Packout lineage.")


def receipt_submitted(doc, method=None):
    if not doc.get("lotus_packout_run"):
        return
    validate_receipt(doc)
    run = frappe.get_doc("Packout Run", doc.lotus_packout_run)
    by_forecast = {}
    for source in run.sources:
        forecast = frappe.db.get_value("Harvest Lot", source.harvest_lot, "forecast")
        if forecast:
            by_forecast[forecast] = by_forecast.get(forecast, 0) + flt(source.source_kg)
    for forecast_name in sorted(by_forecast):
        lock_document("Harvest Forecast", forecast_name)
        forecast = frappe.get_doc("Harvest Forecast", forecast_name)
        if forecast.docstatus != 1 or not flt(forecast.saleable_forecast_kg):
            frappe.throw("Physical stock requires a released non-zero source forecast.")
        raw_kg = by_forecast[forecast_name]
        retirement = min(max(flt(forecast.safe_saleable_kg) - materialized_total(forecast_name, locking=True), 0),
                         raw_kg / flt(forecast.saleable_forecast_kg) * flt(forecast.safe_saleable_kg))
        event = frappe.get_doc({"doctype": "Forecast Materialization", "farm": forecast.farm,
                               "forecast": forecast.name, "packout_run": run.name, "stock_entry": doc.name,
                               "source_raw_kg": raw_kg, "retired_forecast_kg": retirement})
        event.flags.from_stock_hook = True
        event.insert(ignore_permissions=True)
        event.submit()


def receipt_cancelled(doc, method=None):
    if not doc.get("lotus_packout_run"):
        return
    lock_document("Packout Run", doc.lotus_packout_run)
    events = frappe.get_all("Forecast Materialization", filters={"stock_entry": doc.name, "docstatus": 1},
                            fields=["name", "forecast"], order_by="forecast asc")
    for row in events:
        lock_document("Harvest Forecast", row.forecast)
        event = frappe.get_doc("Forecast Materialization", row.name)
        event.flags.from_stock_hook = True
        event.flags.ignore_permissions = True
        event.cancel()
    # The measured run stays submitted as historical evidence after its receipt
    # is reversed. Allow only this reciprocal link through Frappe's cancellation
    # check; standard downstream stock/accounting links still block cancellation.
    doc.ignore_linked_doctypes = list(doc.get("ignore_linked_doctypes") or []) + ["Packout Run"]
