import frappe
from frappe import _


def execute(filters=None):
    filters = frappe._dict(filters or {})
    db_filters = {"supply_state": "Released"}
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
            "item",
            "forecast_basis",
            "packout_rate_percent",
            "materialized_qty_kg",
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
        limit_page_length=10000,
    )

    expanded = []
    for row in rows:
        outputs = frappe.get_all(
            "Forecast Output Plan",
            filters={
                "parent": row.name,
                "parenttype": "Harvest Forecast",
                "parentfield": "output_plan",
            },
            fields=[
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
                if filters.item and output.item != filters.item:
                    continue
                item_row = frappe._dict(row.copy())
                item_row.update(
                    {
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
                expanded.append(item_row)
        elif not filters.item or row.item == filters.item:
            row.yield_percent = row.packout_rate_percent
            expanded.append(row)
    rows = expanded

    columns = [
        {"label": _("Item"), "fieldname": "item", "fieldtype": "Link", "options": "Item", "width": 160},
        {"label": _("Basis"), "fieldname": "forecast_basis", "fieldtype": "Data", "width": 130},
        {"label": _("Yield %"), "fieldname": "yield_percent", "fieldtype": "Percent", "width": 85},
        {
            "label": _("Already in stock kg"),
            "fieldname": "materialized_qty_kg",
            "fieldtype": "Float",
            "width": 140,
        },
        {
            "label": _("Forecast"),
            "fieldname": "name",
            "fieldtype": "Link",
            "options": "Harvest Forecast",
            "width": 120,
        },
        {"label": _("Farm"), "fieldname": "farm", "fieldtype": "Link", "options": "Farm", "width": 110},
        {
            "label": _("Block"),
            "fieldname": "farm_block",
            "fieldtype": "Link",
            "options": "Farm Block",
            "width": 110,
        },
        {
            "label": _("Cycle"),
            "fieldname": "crop_cycle",
            "fieldtype": "Link",
            "options": "Crop Cycle",
            "width": 120,
        },
        {
            "label": _("Cohort"),
            "fieldname": "sucker_selection_batch",
            "fieldtype": "Link",
            "options": "Sucker Selection Batch",
            "width": 120,
        },
        {"label": _("From"), "fieldname": "period_start_date", "fieldtype": "Date", "width": 100},
        {"label": _("To"), "fieldname": "period_end_date", "fieldtype": "Date", "width": 100},
        {
            "label": _("Field Saleable kg"),
            "fieldname": "saleable_forecast_kg",
            "fieldtype": "Float",
            "width": 125,
        },
        {"label": _("Packed kg"), "fieldname": "packed_forecast_kg", "fieldtype": "Float", "width": 110},
        {"label": _("Safe Commit kg"), "fieldname": "safe_saleable_kg", "fieldtype": "Float", "width": 120},
        {"label": _("Committed kg"), "fieldname": "committed_qty_kg", "fieldtype": "Float", "width": 120},
        {"label": _("ATP kg"), "fieldname": "available_to_promise_kg", "fieldtype": "Float", "width": 100},
        {"label": _("Shortage kg"), "fieldname": "shortage_kg", "fieldtype": "Float", "width": 110},
        {"label": _("Status"), "fieldname": "availability_status", "fieldtype": "Data", "width": 115},
        {"label": _("Confidence"), "fieldname": "confidence", "fieldtype": "Data", "width": 100},
    ]

    total_safe = sum(max((row.safe_saleable_kg or 0) - (row.materialized_qty_kg or 0), 0) for row in rows)
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
