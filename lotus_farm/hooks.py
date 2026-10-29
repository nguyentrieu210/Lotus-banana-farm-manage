app_name = "lotus_farm"
app_title = "Lotus Agritech"
app_logo_url = "/assets/lotus_farm/images/lotus-agritech.jpg"
app_publisher = "Nguyen Trieu"
app_description = "Banana farm operations, harvest forecast and availability-to-promise for Lotus"
app_license = "MIT"

# Chat documents and their attached private files follow conversation membership.
# These maps are extended below by the existing business-document hooks.

# Lotus red on Frappe pages too: Desk (/app) and website pages such as /login.
app_include_css = "/assets/lotus_farm/css/lotus-brand.css"
web_include_css = "/assets/lotus_farm/css/lotus-brand.css"

required_apps = ["erpnext"]


before_migrate = "lotus_farm.install.create_roles"
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
    "Lotus Block Forecast Profile",
]
has_permission = {name: "lotus_farm.controls.farm_permission" for name in _scoped_doctypes}
permission_query_conditions = {
    name: "lotus_farm.permissions." + name.lower().replace(" ", "_") for name in _scoped_doctypes
}
has_permission["Work Daily Journal"] = "lotus_farm.work_journal.permission"
permission_query_conditions["Work Daily Journal"] = "lotus_farm.work_journal.journal_query"
doc_events = {name: {"validate": "lotus_farm.controls.check_farm"} for name in _scoped_doctypes}
doc_events['Farm Block']['before_validate']='lotus_farm.block_forecast.sync_block_dates'
doc_events["Farm"]["before_save"] = "lotus_farm.install.validate_reference_company"
doc_events["Sales Order"] = {"before_cancel": "lotus_farm.allocations.sales_order_cancel"}
doc_events["Stock Entry"] = {
    "validate": ["lotus_farm.stock_bridge.validate_entry", "lotus_farm.warehouse_issue.validate_issue", "lotus_farm.finance.stock.stock_entry_accounts"],
    "before_submit": ["lotus_farm.warehouse_issue.validate_issue", "lotus_farm.finance.stock.stock_entry_accounts"],
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

doctype_list_js = {"Role": "public/js/role_list.js"}

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
has_permission["Work Team"] = "lotus_farm.controls.work_team_permission"
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
website_route_rules = [{'from_route':'/login','to_route':'lotus_login'},{'from_route':'/lotus/in-phieu','to_route':'lotus_stock_print'},{'from_route':'/lotus/in-cong','to_route':'lotus_timekeeping_print'},{'from_route':'/lotus/in-de-xuat','to_route':'lotus_material_proposal_print'},{'from_route':'/lotus/in-luong','to_route':'lotus_payroll_print'},{'from_route':'/hr-mobile','to_route':'hr_mobile'},{'from_route':'/lotus/<path:app_path>','to_route':'lotus'}]
doc_events['Daily Work Plan'] = {**doc_events.get('Daily Work Plan',{}),'validate':'lotus_farm.console.work_state_guard'}

doc_events['Harvest Actual']['on_submit']='lotus_farm.harvest_matching.refresh_supply'
doc_events['Harvest Actual']['on_cancel']='lotus_farm.harvest_matching.refresh_supply'
for _event in ('on_submit', 'on_cancel'):
    _existing = doc_events.setdefault('Bunch Cancellation', {}).get(_event, [])
    if isinstance(_existing, str): _existing = [_existing]
    doc_events['Bunch Cancellation'][_event] = [*_existing, 'lotus_farm.onedrive_supply.refresh_cut_forecasts']
doc_events['Daily Work Plan']['before_update_after_submit']='lotus_farm.console.work_state_guard'
doc_events['Material Requirement']={'validate':'lotus_farm.warehouse_planning.validate_requirement_warehouse','before_update_after_submit':'lotus_farm.warehouse_planning.validate_requirement_warehouse'}
doc_events['Material Request']={'validate':'lotus_farm.warehouse_planning.validate_request_lineage','before_submit':'lotus_farm.warehouse_planning.validate_request_lineage'}
doc_events['Purchase Order']={'before_submit':'lotus_farm.purchasing.check_submission'}

# Shared mobile PWA notification hooks. Keep existing validation and stock posting hooks.
for _dt in ('Purchase Order', 'Material Request', 'Purchase Receipt', 'Stock Entry',
            'Daily Work Plan', 'Daily Work Result'):
    for _event in (('on_update', 'on_submit') if _dt == 'Purchase Order' else ('on_submit',)):
        _value = doc_events.setdefault(_dt, {}).get(_event, [])
        if isinstance(_value, str):
            _value = [_value]
        doc_events[_dt][_event] = [*_value, 'lotus_farm.push_notifications.document_hook']

has_permission['Lotus Alert']='lotus_farm.controls.farm_permission'
permission_query_conditions['Lotus Alert']='lotus_farm.permissions.lotus_alert'
scheduler_events['hourly'].append('lotus_farm.alerts.refresh_alerts')

doc_events['Employee'] = {**doc_events.get('Employee', {}),
                          'validate': 'lotus_farm.hr_workspace.employee_identity_guard',
                          'on_update': 'lotus_farm.push_notifications.document_hook'}
doc_events['Lotus Candidate'] = {'validate': 'lotus_farm.hr_workspace.candidate_guard'}
has_permission['Lotus Crew Attendance']='lotus_farm.controls.farm_permission'
permission_query_conditions['Lotus Crew Attendance']='lotus_farm.timekeeping.crew_query'

# Closed timekeeping months freeze Attendance, crew sheets and labour allocation (lotus_farm.hr_period).
override_doctype_class={**globals().get('override_doctype_class',{}),
    'Attendance':'lotus_farm.hr_historical.HistoricalAttendance',
    'Employee Checkin':'lotus_farm.hr_historical.HistoricalEmployeeCheckin'}
doc_events.setdefault('Lotus Attendance Punch', {})['before_insert']='lotus_farm.hr_period.punch_period_guard'
doc_events.setdefault('Employee Checkin', {})['validate']='lotus_farm.hr_period.punch_period_guard'
for _event in ('validate','before_cancel'):
    doc_events.setdefault('Salary Structure Assignment',{})[_event]='lotus_farm.hr_period.salary_rate_guard'
for _dt in ('Attendance', 'Lotus Crew Attendance', 'Labor Allocation'):
    for _event in ('validate', 'before_submit', 'before_cancel', 'on_trash'):
        _value = doc_events.setdefault(_dt, {}).get(_event, [])
        if isinstance(_value, str):
            _value = [_value]
        doc_events[_dt][_event] = [*_value, 'lotus_farm.hr_period.period_guard']
scheduler_events.setdefault('daily', []).append('lotus_farm.hr_operations.sync_yesterday')

# Lotus hours on HRMS salary slips (lotus_farm.hr_payroll).
_slip = doc_events.setdefault('Salary Slip', {})
for _event, _method in (('before_validate', 'lotus_farm.hr_payroll.fill_slip_hours'), ('before_submit', 'lotus_farm.hr_payroll.slip_period_guard')):
    _value = _slip.get(_event, [])
    if isinstance(_value, str):
        _value = [_value]
    _slip[_event] = [*_value, _method]

# Rosters of closed timekeeping months stay as they were paid (lotus_farm.shift_admin).
_assignment = doc_events.setdefault('Shift Assignment', {})
for _event in ('validate', 'before_submit', 'before_cancel'):
    _value = _assignment.get(_event, [])
    if isinstance(_value, str):
        _value = [_value]
    _assignment[_event] = [*_value, 'lotus_farm.shift_admin.assignment_guard']

# Device punches reach HRMS every 10 minutes for today and yesterday (lotus_farm.attendance_day).
scheduler_events.setdefault('cron', {}).setdefault('*/10 * * * *', []).append('lotus_farm.attendance_day.sync_recent')

# ZKTeco / Ronald Jack / Wise Eye clocks push punches to /iclock/* (lotus_farm.adms).
page_renderer = [*globals().get('page_renderer', []), 'lotus_farm.adms.ADMSRenderer']

# OneDrive adoption keeps zone history and lot actuals on separate identities.
for _name in ('Lotus Handover Cohort', 'Lotus Process Adoption'):
    has_permission[_name] = 'lotus_farm.controls.farm_permission'
    permission_query_conditions[_name] = 'lotus_farm.permissions.' + _name.lower().replace(' ', '_')
has_permission['Bunch Tag'] = 'lotus_farm.controls.farm_permission'
permission_query_conditions['Bunch Tag'] = 'lotus_farm.permissions.bunch_tag'
has_permission['Lotus Financial Plan'] = 'lotus_farm.finance.planning.permission'
permission_query_conditions['Lotus Financial Plan'] = 'lotus_farm.finance.planning.query_condition'
for _dt, _event, _handler in (
    ('Bunch Tag', 'validate', 'lotus_farm.onedrive_workspace.validate_tag_master'),
    ('Sucker Selection Batch', 'validate', 'lotus_farm.onedrive_workspace.validate_handover_link'),
    ('Plan Cohort', 'validate', 'lotus_farm.onedrive_workspace.validate_handover_link'),
    ('Fruit Measurement', 'validate', 'lotus_farm.onedrive_workspace.tag_lineage'),
    ('Harvest Actual', 'validate', 'lotus_farm.onedrive_workspace.tag_lineage'),
    ('Bunch Operation', 'validate', 'lotus_farm.onedrive_workspace.preserve_cut_source'),
    ('Bunch Operation', 'before_cancel', 'lotus_farm.onedrive_workspace.preserve_cut_source'),
):
    _existing = doc_events.setdefault(_dt, {}).get(_event, [])
    if isinstance(_existing, str):
        _existing = [_existing]
    doc_events[_dt][_event] = [*_existing, _handler]

doc_events.setdefault("Stock Reconciliation", {})
doc_events["Stock Reconciliation"]["before_submit"] = "lotus_farm.finance.stock.reconciliation_accounts"

doc_events.setdefault("Journal Entry", {})
doc_events["Journal Entry"]["on_cancel"] = "lotus_farm.finance.costing.costing_reversed"

# Fixed assets are reviewed in Lotus, including writes made through native Desk/API endpoints.
for _dt in ('Asset', 'Asset Movement', 'Asset Repair', 'Asset Capitalization', 'Asset Value Adjustment', 'Asset Depreciation Schedule',
            'Journal Entry', 'Purchase Invoice', 'Sales Invoice'):
    for _event in ('before_submit', 'before_cancel', 'before_update_after_submit'):
        _handlers = doc_events.setdefault(_dt, {}).get(_event, [])
        if isinstance(_handlers, str):
            _handlers = [_handlers]
        doc_events[_dt][_event] = [*_handlers, 'lotus_farm.finance.assets.native_guard']
for _dt in ('Accounts Settings', 'Lotus Finance Settings', 'Asset Category', 'Asset Depreciation Schedule'):
    _handlers = doc_events.setdefault(_dt, {}).get('validate', [])
    if isinstance(_handlers, str):
        _handlers = [_handlers]
    doc_events[_dt]['validate'] = [*_handlers, 'lotus_farm.finance.assets.native_guard']
for _event in ('validate',):
    _handlers = doc_events.setdefault('Asset', {}).get(_event, [])
    if isinstance(_handlers, str):
        _handlers = [_handlers]
    doc_events['Asset'][_event] = [*_handlers, 'lotus_farm.finance.assets.native_guard']

# Finance safety also applies when documents are submitted/cancelled through ERPNext Desk or REST.
_handlers = doc_events.setdefault('Purchase Receipt',{}).get('before_submit',[])
if isinstance(_handlers,str):
    _handlers=[_handlers]
doc_events['Purchase Receipt']['before_submit']=[*_handlers,'lotus_farm.procurement.receipt_guard']

for _funding_event in ('validate', 'before_submit', 'before_cancel', 'before_update_after_submit'):
    _handlers = doc_events.setdefault('Journal Entry', {}).get(_funding_event, [])
    if isinstance(_handlers, str):
        _handlers = [_handlers]
    doc_events['Journal Entry'][_funding_event] = [*_handlers, 'lotus_farm.purchase_funding.native_guard']

for _purchase_dt in ('Material Request', 'Supplier Quotation', 'Purchase Order', 'Purchase Receipt', 'Purchase Invoice'):
    _handlers = doc_events.setdefault(_purchase_dt, {}).get('validate', [])
    if isinstance(_handlers, str):
        _handlers = [_handlers]
    doc_events[_purchase_dt]['validate'] = [*_handlers, 'lotus_farm.procurement.native_guard']

for _finance_dt in ('Payment Entry', 'Journal Entry', 'Purchase Invoice', 'Sales Invoice',
                    'Stock Entry', 'Stock Reconciliation', 'Purchase Receipt', 'Delivery Note'):
    for _event, _handler in (('before_submit', 'lotus_farm.finance.native_guards.guard'),
                             ('before_cancel', 'lotus_farm.finance.native_guards.guard'),
                             ('before_update_after_submit', 'lotus_farm.finance.native_guards.guard'),
                             ('on_cancel', 'lotus_farm.finance.native_guards.sync_cancel')):
        _old = doc_events.setdefault(_finance_dt, {}).get(_event, [])
        if isinstance(_old, str):
            _old = [_old]
        if _handler not in _old:
            doc_events[_finance_dt][_event] = [*_old, _handler]

for _chat_dt, _chat_query in (('Lotus Chat Room', 'room_query'), ('Lotus Chat Message', 'message_query'),
                             ('Lotus Chat Member', 'member_query')):
    has_permission[_chat_dt] = 'lotus_farm.chat.permission'
    permission_query_conditions[_chat_dt] = 'lotus_farm.chat.' + _chat_query

for _chat_file_event in ('before_validate', 'on_trash'):
    _chat_file_handlers = doc_events.setdefault('File', {}).get(_chat_file_event, [])
    if isinstance(_chat_file_handlers, str):
        _chat_file_handlers = [_chat_file_handlers]
    doc_events['File'][_chat_file_event] = [*_chat_file_handlers, 'lotus_farm.chat.file_guard']
