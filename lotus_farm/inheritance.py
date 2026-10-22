"""The explicit boundary between inherited history and observed lot records."""
import frappe
from frappe.utils import cint, getdate


INHERITED_CYCLE_FIELDS = (
    "cycle_type", "cycle_no", "origin_basis", "parent_cycle", "planting_date",
    "farm_plot", "coverage_start_date", "inheritance_note", "handover_zone",
)


def lock_plot_cycles(farm_plot):
    """Serialize roots and successors, then read the current committed lineage."""
    from lotus_farm.controls import lock
    lock("Farm Plot", farm_plot)
    cycle = frappe.qb.DocType("Crop Cycle")
    return (
        frappe.qb.from_(cycle)
        .select(cycle.name, cycle.cycle_no, cycle.origin_basis)
        .where(cycle.farm_plot == farm_plot)
        .for_update()
        .run(as_dict=True)
    )


def is_inherited_opening(cycle):
    """Only a complete, parentless opening root can omit an observed SSB."""
    return bool(
        cycle.get("origin_basis") == "Handover"
        and cycle.get("cycle_type") == "Ratoon"
        and cint(cycle.get("cycle_no")) >= 2
        and not cycle.get("parent_cycle")
        and not cycle.get("planting_date")
        and cycle.get("farm_plot")
        and cycle.get("coverage_start_date")
        and (cycle.get("inheritance_note") or "").strip()
        and cycle.get("handover_zone")
    )


def validate_coverage_date(cycle, on_date):
    if cycle.get("origin_basis") != "Handover":
        return
    if not is_inherited_opening(cycle):
        frappe.throw("Complete the inherited opening cycle and its coverage start date before recording operations.")
    if on_date and getdate(on_date) < getdate(cycle.get("coverage_start_date")):
        frappe.throw("Operation date precedes the inherited cycle coverage start date.")


def cycle_provenance(cycle):
    return {
        "origin_basis": cycle.get("origin_basis") or "Observed",
        "inherited_opening": is_inherited_opening(cycle),
        "coverage_start_date": cycle.get("coverage_start_date") or None,
        "planting_date": cycle.get("planting_date") or None,
        "planting_date_known": bool(cycle.get("planting_date")),
        "parent_cycle": cycle.get("parent_cycle") or None,
        "handover_zone": cycle.get("handover_zone") or None,
        "inheritance_note": cycle.get("inheritance_note") or None,
    }
