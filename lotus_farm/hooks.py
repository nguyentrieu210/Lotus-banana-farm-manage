app_name = "lotus_farm"
app_title = "Lotus Farm"
app_publisher = "Nguyen Trieu"
app_description = "Banana farm operations, harvest forecast and availability-to-promise for Lotus"
app_license = "MIT"

required_apps = ["erpnext"]


after_install = "lotus_farm.install.setup"
after_migrate = "lotus_farm.install.setup"

_scoped_doctypes = [
    "Farm",
    "Farm Block",
    "Crop Cycle",
    "Sucker Selection Batch",
    "Bunch Operation",
    "Defect Inspection",
    "Harvest Forecast",
    "Harvest Actual",
    "Harvest Lot",
    "Packout Run",
    "Scale Reading",
    "Supply Reconciliation",
]
has_permission = {name: "lotus_farm.controls.farm_permission" for name in _scoped_doctypes}
permission_query_conditions = {
    name: "lotus_farm.permissions." + name.lower().replace(" ", "_") for name in _scoped_doctypes
}
doc_events = {name: {"validate": "lotus_farm.controls.check_farm"} for name in _scoped_doctypes}
doc_events["Farm"]["before_save"] = "lotus_farm.install.validate_reference_company"
doc_events["Sales Order"] = {"before_cancel": "lotus_farm.allocations.sales_order_cancel"}
doc_events["Stock Entry"] = {
    "validate": "lotus_farm.stock_bridge.validate_entry",
    "on_submit": "lotus_farm.stock_bridge.stock_posted",
    "before_cancel": "lotus_farm.stock_bridge.before_stock_cancel",
    "on_cancel": "lotus_farm.stock_bridge.stock_reversed",
}
doc_events["Stock Reservation Entry"] = {
    "before_cancel": "lotus_farm.stock_bridge.reservation_cancel",
    "on_cancel": "lotus_farm.stock_bridge.reservation_cancelled",
}

before_install = "lotus_farm.install.create_roles"
for _name in ("Farm", "Farm Block", "Crop Cycle", "Sucker Selection Batch"):
    doc_events[_name]["before_save"] = ["lotus_farm.controls.preserve_lineage"]
doc_events["Farm"]["before_save"].append("lotus_farm.install.validate_reference_company")
for _name in ("Bunch Operation", "Harvest Actual", "Defect Inspection"):
    doc_events[_name]["validate"] = [
        "lotus_farm.controls.check_farm",
        "lotus_farm.controls.validate_operation_date",
    ]

has_permission["Integration Event"] = "lotus_farm.controls.farm_permission"
permission_query_conditions["Integration Event"] = "lotus_farm.permissions.integration_event"
doc_events["Integration Event"] = {"validate": "lotus_farm.controls.check_farm"}

doctype_js = {
    "Harvest Forecast": "public/js/harvest_forecast.js",
    "Packout Run": "public/js/packout_run.js",
    "Supply Reconciliation": "public/js/supply_reconciliation.js",
}
