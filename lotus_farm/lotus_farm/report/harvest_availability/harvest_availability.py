import frappe
from frappe import _
from lotus_farm.supply import availability


def execute(filters=None):
    filters = frappe._dict(filters or {})
    db_filters = {"docstatus": 1}

    if filters.farm:
        db_filters["farm"] = filters.farm
    if filters.from_date:
        db_filters["period_start_date"] = [">=", filters.from_date]
    if filters.to_date:
        db_filters["period_end_date"] = ["<=", filters.to_date]

    rows = frappe.get_list(
        "Harvest Forecast",
        filters=db_filters,
        fields=[
            "name",
            "item_code",
            "farm",
            "farm_block",
            "crop_cycle",
            "sucker_selection_batch",
            "period_start_date",
            "period_end_date",
            "gross_forecast_kg",
            "saleable_forecast_kg",
            "packed_forecast_kg",
            "safe_saleable_kg",
            "committed_qty_kg",
            "available_to_promise_kg",
            "shortage_kg",
            "availability_status",
            "confidence",
        ],
        order_by="period_start_date asc, farm asc",
        limit_page_length=0,
    )
    for row in rows:
        row.update(availability(row))

    columns = [
        {"label": _("Item"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 130},
        {"label": _("Materialized kg"), "fieldname": "materialized_qty_kg", "fieldtype": "Float", "width": 120},
        {"label": _("Forecast"), "fieldname": "name", "fieldtype": "Link", "options": "Harvest Forecast", "width": 120},
        {"label": _("Farm"), "fieldname": "farm", "fieldtype": "Link", "options": "Farm", "width": 110},
        {"label": _("Block"), "fieldname": "farm_block", "fieldtype": "Link", "options": "Farm Block", "width": 110},
        {"label": _("Cycle"), "fieldname": "crop_cycle", "fieldtype": "Link", "options": "Crop Cycle", "width": 120},
        {"label": _("Cohort"), "fieldname": "sucker_selection_batch", "fieldtype": "Link", "options": "Sucker Selection Batch", "width": 120},
        {"label": _("From"), "fieldname": "period_start_date", "fieldtype": "Date", "width": 100},
        {"label": _("To"), "fieldname": "period_end_date", "fieldtype": "Date", "width": 100},
        {"label": _("Field Saleable kg"), "fieldname": "saleable_forecast_kg", "fieldtype": "Float", "width": 125},
        {"label": _("Packed kg"), "fieldname": "packed_forecast_kg", "fieldtype": "Float", "width": 110},
        {"label": _("Safe Commit kg"), "fieldname": "safe_saleable_kg", "fieldtype": "Float", "width": 120},
        {"label": _("Committed kg"), "fieldname": "committed_qty_kg", "fieldtype": "Float", "width": 120},
        {"label": _("ATP kg"), "fieldname": "available_to_promise_kg", "fieldtype": "Float", "width": 100},
        {"label": _("Shortage kg"), "fieldname": "shortage_kg", "fieldtype": "Float", "width": 110},
        {"label": _("Status"), "fieldname": "availability_status", "fieldtype": "Data", "width": 115},
        {"label": _("Confidence"), "fieldname": "confidence", "fieldtype": "Data", "width": 100},
    ]

    total_safe = sum(row.safe_saleable_kg or 0 for row in rows)
    total_committed = sum(row.committed_qty_kg or 0 for row in rows)
    total_atp = sum(row.available_to_promise_kg or 0 for row in rows)
    total_shortage = sum(row.shortage_kg or 0 for row in rows)

    report_summary = [
        {"label": _("Safe Commit"), "value": total_safe, "datatype": "Float"},
        {"label": _("Committed"), "value": total_committed, "datatype": "Float"},
        {"label": _("Available to Promise"), "value": total_atp, "datatype": "Float"},
        {"label": _("Shortage"), "value": total_shortage, "datatype": "Float"},
    ]

    return columns, rows, None, None, report_summary
