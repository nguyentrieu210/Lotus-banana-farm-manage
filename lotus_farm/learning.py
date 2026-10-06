"""Measured proposals only. Publishing assumptions remains a human approval."""

import frappe
from lotus_farm.controls import require_role
from lotus_farm.rules import calibration, RuleError, canonical_hash


@frappe.whitelist()
def propose_profile(farm, farm_block, crop_cycle, from_date, to_date):
    require_role("Lotus Farm Manager")
    cycle = frappe.get_doc("Crop Cycle", crop_cycle)
    cycle.check_permission("read")
    if cycle.farm != farm or cycle.farm_block != farm_block:
        frappe.throw("Select matching Farm, Block and Crop Cycle.")
    rows = frappe.get_list(
        "Harvest Actual",
        filters={
            "farm": farm,
            "farm_block": farm_block,
            "crop_cycle": crop_cycle,
            "docstatus": 1,
            "harvest_date": ["between", [from_date, to_date]],
        },
        fields=["name", "harvested_bunch_qty", "gross_weight_kg", "saleable_weight_kg"],
        limit_page_length=10000,
    )
    minimum = frappe.db.get_single_value("Lotus Farm Settings", "minimum_calibration_samples") or 10
    try:
        result = calibration(rows, minimum)
    except RuleError as exc:
        frappe.throw(str(exc))
    result.update(
        farm=farm,
        farm_block=farm_block,
        crop_cycle=crop_cycle,
        source_documents=[r.name for r in rows],
        source_hash=canonical_hash(rows),
        source_date_from=from_date,
        source_date_to=to_date,
        algorithm_version="lotus-weighted-actual/1",
        approval_state="Draft",
    )
    # Do not infer survival or packout without matched source-bunch/raw input denominators.
    return result
