app_name = "lotus_farm"
app_title = "Lotus Agritech"
app_logo_url = "/assets/lotus_farm/images/lotus-agritech.jpg"
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
    "validate": ["lotus_farm.stock_bridge.validate_entry", "lotus_farm.warehouse_issue.validate_issue"],
    "before_submit": "lotus_farm.warehouse_issue.validate_issue",
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

# ProMax farm/day and plot controls apply to every normal document write, not just APIs.
_daily_doctypes = [
    "Daily Work Plan", "Daily Work Result", "Labor Allocation", "Daily Labor Summary",
    "Material Requirement", "Material Consumption", "Material Recovery", "Bunch Cancellation",
    "Planting Event", "Disease Observation", "Fruit Measurement", "Incoming Quality Inspection",
    "Daily Production Close", "Source Import Batch", "Legacy Organization Map",
    "Farm Plot", "Work Team", "Material Norm Profile",
]
for _name in _daily_doctypes:
    has_permission[_name] = "lotus_farm.controls.farm_permission"
    permission_query_conditions[_name] = "lotus_farm.permissions." + _name.lower().replace(" ", "_")
for _name in ("Crop Cycle", "Sucker Selection Batch", "Bunch Operation", "Harvest Actual", "Defect Inspection", "Harvest Forecast"):
    _current = doc_events[_name].get("validate", [])
    if isinstance(_current, str):
        _current = [_current]
    # Before the forecast controller snapshots its scope, hydrate plot in before_validate.
    doc_events[_name]["before_validate"] = "lotus_farm.daily_operations.plot_scope"
for _name in ("Bunch Operation", "Harvest Actual", "Defect Inspection", "Harvest Lot", "Packout Run"):
    doc_events[_name]["before_validate"] = [
        "lotus_farm.daily_operations.day_guard",
        *(["lotus_farm.daily_operations.plot_scope"] if _name in ("Bunch Operation", "Harvest Actual", "Defect Inspection") else []),
    ]
    _current = doc_events[_name].get("before_cancel", [])
    if isinstance(_current, str):
        _current = [_current]
    doc_events[_name]["before_cancel"] = ["lotus_farm.daily_operations.day_guard", *_current]
    doc_events[_name]["on_trash"] = "lotus_farm.daily_operations.day_guard"
doc_events["Packout Run"]["before_validate"].append("lotus_farm.daily_operations.incoming_packout_guard")
doc_events["Stock Entry"]["before_cancel"] = [
    "lotus_farm.daily_operations.stock_context_cancel",
    "lotus_farm.stock_bridge.before_stock_cancel",
]

for _name in ("Secondary Product Movement", "Cycle Closing Report"):
    has_permission[_name] = "lotus_farm.controls.farm_permission"
    permission_query_conditions[_name] = "lotus_farm.permissions." + _name.lower().replace(" ", "_")

doctype_js.update({
    "Daily Work Plan": "public/js/daily_work_plan.js",
    "Material Requirement": "public/js/material_requirement.js",
    "Daily Production Close": "public/js/daily_production_close.js",
})
has_permission["Legacy Cycle Plot Mapping"] = "lotus_farm.controls.farm_permission"
permission_query_conditions["Legacy Cycle Plot Mapping"] = "lotus_farm.permissions.legacy_cycle_plot_mapping"

_promax_scoped = ['Plot Geometry','Scale Device','Work Schedule Rule','Field Capture','Integration Task','Warehouse Mapping']
for _name in _promax_scoped:
    has_permission[_name] = 'lotus_farm.controls.farm_permission'
    permission_query_conditions[_name] = 'lotus_farm.permissions.' + _name.lower().replace(' ','_')
    doc_events[_name] = {'validate':'lotus_farm.controls.check_farm'}
for _name in (*_daily_doctypes,'Harvest Actual','Harvest Lot','Packout Run','Bunch Operation','Secondary Product Movement'):
    _old = doc_events.setdefault(_name,{}).get('before_insert',[])
    if isinstance(_old,str):_old=[_old]
    doc_events[_name]['before_insert']=[*_old,'lotus_farm.promax_controls.amendment_guard']
_pack_validate = doc_events['Packout Run']['validate']
if isinstance(_pack_validate,str):_pack_validate=[_pack_validate]
doc_events['Packout Run']['validate']=[*_pack_validate,'lotus_farm.promax_controls.pack_spec_guard']
has_permission['OneDrive Feed'] = 'lotus_farm.controls.farm_permission'
permission_query_conditions['OneDrive Feed'] = 'lotus_farm.permissions.onedrive_feed'
scheduler_events = {'hourly':['lotus_farm.onedrive.scheduled_poll']}
has_permission['Source Inventory Item'] = 'lotus_farm.controls.farm_permission'
permission_query_conditions['Source Inventory Item'] = 'lotus_farm.permissions.source_inventory_item'
doc_events['Bunch Operation']['validate'].append('lotus_farm.promax_controls.bunch_tag_guard')
doc_events['Defect Reason'] = {'validate':'lotus_farm.promax_controls.defect_master_guard'}
doctype_js['Harvest Lot'] = 'public/js/harvest_lot.js'

has_permission['Packhouse Shift'] = 'lotus_farm.controls.farm_permission'
permission_query_conditions['Packhouse Shift'] = 'lotus_farm.permissions.packhouse_shift'
for _name in ('Packout Run','Material Recovery','Secondary Product Movement'):
    _old = doc_events.setdefault(_name,{}).get('validate',[])
    if isinstance(_old,str):_old=[_old]
    doc_events[_name]['validate']=[*_old,'lotus_farm.shift.shift_link_guard']
for _name in ('Harvest Actual','Harvest Lot','Packout Run'):
    _old = doc_events[_name].get('validate',[])
    if isinstance(_old,str):_old=[_old]
    doc_events[_name]['validate']=[*_old,'lotus_farm.shift.scale_link_guard']
website_route_rules = [{'from_route':'/lotus/in-phieu','to_route':'lotus_stock_print'},{'from_route':'/lotus/<path:app_path>','to_route':'lotus'}]
doc_events['Daily Work Plan'] = {**doc_events.get('Daily Work Plan',{}),'validate':'lotus_farm.console.work_state_guard'}

doc_events['Harvest Actual']['on_submit']='lotus_farm.harvest_matching.refresh_supply'
doc_events['Harvest Actual']['on_cancel']='lotus_farm.harvest_matching.refresh_supply'
doc_events['Daily Work Plan']['before_update_after_submit']='lotus_farm.console.work_state_guard'
doc_events['Material Requirement']={'validate':'lotus_farm.warehouse_planning.validate_requirement_warehouse','before_update_after_submit':'lotus_farm.warehouse_planning.validate_requirement_warehouse'}
doc_events['Material Request']={'validate':'lotus_farm.warehouse_planning.validate_request_lineage','before_submit':'lotus_farm.warehouse_planning.validate_request_lineage'}

has_permission['Lotus Alert']='lotus_farm.controls.farm_permission'
permission_query_conditions['Lotus Alert']='lotus_farm.permissions.lotus_alert'
scheduler_events['hourly'].append('lotus_farm.alerts.refresh_alerts')
