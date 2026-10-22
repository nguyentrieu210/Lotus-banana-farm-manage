"""Read-only, permission-filtered desktop view for banana harvest forecasting.

The board shows biological harvest forecasts, not customer receivables.
Predicted packed kg and harvested gross kg are intentionally separate measures.
"""
from collections import defaultdict
from datetime import timedelta

import frappe
from frappe.utils import add_days, flt, getdate, nowdate

from lotus_farm.reporting import records
from lotus_farm.scoping import land_filters, land_scope


def week_start(value):
    date = getdate(value)
    return date - timedelta(days=date.weekday())


def period_overlap(start_a, end_a, start_b, end_b):
    return getdate(start_a) <= getdate(end_b) and getdate(end_a) >= getdate(start_b)


def _fields():
    return [
        "name", "farm", "farm_block", "crop_cycle", "period_start_date",
        "period_end_date", "source_bunch_qty", "net_source_bunch_qty",
        "expected_harvest_bunch_qty", "avg_bunch_weight_kg",
        "gross_forecast_kg", "saleable_forecast_kg", "packed_forecast_kg",
        "safe_saleable_kg", "committed_qty_kg", "materialized_qty_kg",
        "available_to_promise_kg", "shortage_kg", "availability_status",
        "supply_state", "confidence", "forecast_basis", "revision_no",
        "supersedes", "released_at", "modified", "process_adoption",
    ]


@frappe.whitelist()
def board(company=None, farm=None, block=None, cycle=None, from_date=None, to_date=None,zone=None):
    """Return the complete scoped planning window; never sum draft/replaced supply."""
    if not frappe.has_permission("Harvest Forecast", "read"):
        frappe.throw("Không có quyền xem dự thu.", frappe.PermissionError)
    start = getdate(from_date or nowdate())
    end = getdate(to_date or add_days(start, 55))
    if start > end:
        frappe.throw("Ngày bắt đầu phải trước ngày kết thúc.")
    if (end - start).days > 366:
        frappe.throw("Chỉ xem tối đa 366 ngày; hãy thu hẹp khoảng thời gian.")

    selected = land_scope(company=company, farm=farm, block=block, cycle=cycle, zone=zone)
    filters = {
        "period_start_date": ["<=", end],
        "period_end_date": [">=", start],
    }
    filters.update(land_filters(frappe.get_meta("Harvest Forecast"), selected))
    documents = records("Harvest Forecast", filters, _fields())
    result = [dict(row) for row in documents]
    result.sort(key=lambda r: (str(r["period_start_date"]), r.get("farm") or "", r.get("farm_block") or "", r["name"]))
    for row in result:
        row["period_start_date"] = str(row["period_start_date"])
        row["period_end_date"] = str(row["period_end_date"])
        if row.get("released_at"):
            row["released_at"] = str(row["released_at"])
        if row.get("modified"):
            row["modified"] = str(row["modified"])
        row["actual_gross_kg"] = 0
        row["actual_bunch_qty"] = 0
        row["actual_count"] = 0
        row["spans_weeks"] = week_start(row["period_start_date"]) != week_start(row["period_end_date"])

    # The actual collection obeys its OWN Frappe read permissions and land filters.
    # It never represents a "missing" Harvest Actual as a confirmed zero.
    actual_readable = frappe.has_permission("Harvest Actual", "read")
    actuals = []
    if actual_readable:
        actual_filters = {
            "docstatus": 1,
            "harvest_date": ["between", [start, end]],
        }
        actual_filters.update(land_filters(frappe.get_meta("Harvest Actual"), selected))
        actuals = records("Harvest Actual", actual_filters, [
            "name", "forecast", "harvest_date", "gross_weight_kg", "harvested_bunch_qty"
        ])

    indexed = {row["name"]: row for row in result}
    weekly = {}
    cursor = week_start(start)
    while cursor <= end:
        key = str(cursor)
        weekly[key] = dict(
            week_start=key,
            week_end=str(cursor + timedelta(days=6)),
            gross_kg=0, packed_kg=0, available_kg=0,
            actual_gross_kg=None if not actual_readable else 0,
            active_count=0,
        )
        cursor += timedelta(days=7)

    for row in result:
        if row["supply_state"] != "Released":
            continue
        # One forecast is counted ONCE, under the week of its first day inside
        # the selected window. A multiweek document is never prorated falsely.
        slot = str(week_start(max(start, getdate(row["period_start_date"]))))
        if slot in weekly:
            weekly[slot]["gross_kg"] += flt(row.get("gross_forecast_kg"))
            weekly[slot]["packed_kg"] += flt(row.get("packed_forecast_kg"))
            weekly[slot]["available_kg"] += flt(row.get("available_to_promise_kg"))
            weekly[slot]["active_count"] += 1

    for actual in actuals:
        parent = indexed.get(actual.forecast)
        if parent:
            parent["actual_gross_kg"] += flt(actual.gross_weight_kg)
            parent["actual_bunch_qty"] += flt(actual.harvested_bunch_qty)
            parent["actual_count"] += 1
        slot = str(week_start(actual.harvest_date))
        if slot in weekly:
            weekly[slot]["actual_gross_kg"] += flt(actual.gross_weight_kg)

    active = [r for r in result if r["supply_state"] == "Released"]
    drafts = [r for r in result if r["supply_state"] == "Draft"]
    summary = dict(
        active_count=len(active),
        draft_count=len(drafts),
        packed_kg=round(sum(flt(r.get("packed_forecast_kg")) for r in active), 3),
        gross_kg=round(sum(flt(r.get("gross_forecast_kg")) for r in active), 3),
        available_kg=round(sum(flt(r.get("available_to_promise_kg")) for r in active), 3),
        shortages=len([r for r in active if r.get("availability_status") == "Overcommitted"]),
        harvested_gross_kg=round(sum(flt(r.gross_weight_kg) for r in actuals), 3) if actual_readable else None,
    )
    return dict(
        from_date=str(start), to_date=str(end), rows=result,
        weeks=list(weekly.values()), summary=summary,
        actual_readable=actual_readable,
        # Released is the only actionable supply; Closed/Superseded are history.
        rule="Tổng sản lượng chỉ tính bản Đã phát hành. Không cộng bản nháp hoặc bản đã thay thế.",
    )
