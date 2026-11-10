"""Frozen copies of the weekly forecast, and how they compare with what was harvested. Nothing here changes the parameters in force."""
import json

import frappe
from frappe.utils import getdate, nowdate

from lotus_farm import block_forecast, bunch_forecast_engine
from lotus_farm import field_report as field
from lotus_farm.lot_ledger import ENTRY, bunch_rows
from lotus_farm import forecast_snapshot_rules as rules
from lotus_farm.forecast_parameters import DEFAULTS, validate

SNAPSHOT = "Lotus Forecast Snapshot"


def _write(farm, kind):
    today = nowdate()
    summary, cohorts = block_forecast.bunch_summary(farm)
    refs = sorted({c["profile"] for c in cohorts if c["profile"]})
    doc = frappe.new_doc(SNAPSHOT)
    doc.update({"farm": farm, "snapshot_date": today, "week_label": bunch_forecast_engine.week_key(getdate(today)), "kind": kind,
                "profile_refs": json.dumps(refs), "total_bunches": summary["totals"]["bunches"], "total_kg": summary["totals"]["kg"],
                "rows_json": json.dumps(bunch_forecast_engine.snapshot_rows(summary), ensure_ascii=False)})
    field._store(doc)
    return doc


def _require(farm, manager=False):
    field.require_farm(farm)
    if manager and not field.is_manager():
        frappe.throw("Chỉ quản lý vườn chốt bản dự thu.", frappe.PermissionError)


@frappe.whitelist(methods=["POST"])
def create(farm):
    _require(farm, manager=True)
    doc = _write(farm, "Manual")
    return {"name": doc.name, "snapshot_date": str(doc.snapshot_date), "total_bunches": doc.total_bunches, "total_kg": doc.total_kg}


def weekly():
    """Monday morning, for every farm with a bunch ledger. Running it twice in one week writes one copy."""
    week = bunch_forecast_engine.week_key(getdate(nowdate()))
    for farm in {r.farm for r in frappe.get_all(ENTRY, filters={"stage": ["is", "set"]}, fields=["farm"], distinct=True, limit_page_length=0)}:
        if not frappe.db.exists(SNAPSHOT, {"farm": farm, "week_label": week, "kind": "Weekly"}):
            _write(farm, "Weekly")


def _snapshots(farm):
    return frappe.get_all(SNAPSHOT, filters={"farm": farm}, fields=["name", "snapshot_date", "week_label", "kind", "total_bunches", "total_kg", "rows_json", "profile_refs"],
                          order_by="snapshot_date asc, creation asc", limit_page_length=0)


def _forecast_for(snapshots, week):
    """The latest copy frozen no later than the Monday of that week: what we believed when the week began."""
    monday = rules.week_monday(week)
    chosen = None
    for s in snapshots:
        if getdate(s.snapshot_date) <= monday:
            chosen = s
    return chosen


def _actual_rows(farm, first, last):
    rows = bunch_rows({"farm": farm, "state": "Confirmed", "event_type": "Harvest", "event_date": ["between", [first, last]]},
                      ["farm_block", "bunch_tag", "event_date", "qty", "weight_kg"])
    labels = frappe._dict({t.name: t.color_label for t in frappe.get_all("Bunch Tag", filters={"farm": farm}, fields=["name", "color_label"], limit_page_length=0)})
    codes = {b.name: b.block_code for b in frappe.get_all("Farm Block", filters={"farm": farm}, fields=["name", "block_code"], limit_page_length=0)}
    return [{"week": rules.week_key(r.event_date), "block": r.farm_block, "block_code": codes.get(r.farm_block, ""), "tag": r.bunch_tag, "ribbon": labels.get(r.bunch_tag, ""), "bunches": r.qty, "kg": r.weight_kg}
            for r in rows]


@frappe.whitelist()
def variance(farm, from_week, to_week, group_by="week"):
    """Forecast against harvest, week by week. Only weeks that had a frozen copy before they began are compared."""
    _require(farm)
    snapshots = _snapshots(farm)
    first, last = rules.week_monday(from_week), rules.week_monday(to_week)
    forecast, used, cursor, weeks = [], {}, first, []
    while cursor <= last:
        week = rules.week_key(cursor)
        weeks.append(week)
        chosen = _forecast_for(snapshots, week)
        if chosen:
            used[week] = {"name": chosen.name, "date": str(chosen.snapshot_date)}
            forecast += [r for r in json.loads(chosen.rows_json or "[]") if r["week"] == week]
        cursor = frappe.utils.add_days(cursor, 7)
        cursor = getdate(cursor)
    actual = [r for r in _actual_rows(farm, first, frappe.utils.add_days(last, 6)) if r["week"] in used]
    return {"rows": rules.compare(forecast, actual, group_by), "weeks": weeks, "snapshots": used, "group_by": group_by, "has_snapshot": bool(snapshots)}


@frappe.whitelist()
def suggest_parameters(farm, block=None):
    """Numbers measured from finished colours, next to those in force. Applied only when someone approves a new set of parameters."""
    _require(farm)
    filters = {"farm": farm, "state": "Confirmed", "event_type": ["in", ["Cut Bud", "Harvest", "Reject"]]}
    if block:
        filters["farm_block"] = block
    lines = bunch_rows(filters, ["farm_block", "bunch_tag", "event_type", "event_date", "qty", "weight_kg", "reject_stage"])
    result = rules.suggest(rules.colour_results(lines, nowdate()), validate(DEFAULTS))
    return dict(result, applied=False)
