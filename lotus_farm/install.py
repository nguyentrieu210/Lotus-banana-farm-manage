import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def setup():
    create_custom_fields({
        "Stock Entry": [{"fieldname": "lotus_packout_run", "label": "Lotus Packout Run",
                         "fieldtype": "Link", "options": "Packout Run", "insert_after": "remarks",
                         "read_only": 1, "no_copy": 1}],
        "Batch": [{"fieldname": "lotus_packout_run", "label": "Lotus Packout Run",
                   "fieldtype": "Link", "options": "Packout Run", "read_only": 1}],
    })
    frappe.db.add_unique("Harvest Profile", ["profile_name", "profile_version"],
                         constraint_name="unique_harvest_profile_version")
    frappe.db.add_unique("Forecast Materialization", ["stock_entry", "forecast"],
                         constraint_name="unique_stock_forecast_materialization")
