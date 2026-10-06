app_name = "lotus_farm"
app_title = "Lotus Farm"
app_publisher = "Nguyen Trieu"
app_description = "Banana farm operations, harvest forecast and availability-to-promise for Lotus"
app_license = "MIT"

required_apps = ["erpnext"]

after_install = "lotus_farm.install.setup"
after_migrate = "lotus_farm.install.setup"
doc_events = {
    "Stock Entry": {
        "before_submit": "lotus_farm.stock.validate_receipt",
        "on_submit": "lotus_farm.stock.receipt_submitted",
        "on_cancel": "lotus_farm.stock.receipt_cancelled",
    }
}
