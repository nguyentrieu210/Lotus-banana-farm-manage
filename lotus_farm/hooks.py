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

# Documents of one farm: read and written only by users granted that farm.
_scoped_doctypes = [
    "Farm",
    "Farm Block",
    "Lotus Block Forecast Profile",
    "Work Schedule Rule",
    "Warehouse Mapping",
    "Bunch Tag",
]
has_permission = {name: "lotus_farm.controls.farm_permission" for name in _scoped_doctypes}
permission_query_conditions = {
    name: "lotus_farm.permissions." + name.lower().replace(" ", "_") for name in _scoped_doctypes
}
# Công việc ngoài vườn: written only through lotus_farm.field_report, read by farm.
for _name, _query in (("Lotus Work Assignment", "assignment_query"), ("Lotus Work Entry", "entry_query"),
                      ("Lotus Work Session", "session_query"), ("Lotus Work Inspection", "inspection_query"),
                      ("Lotus Forecast Snapshot", "forecast_snapshot_query"),
                      ("Lotus Daily Report", "daily_report_query")):
    has_permission[_name] = "lotus_farm.field_report.permission"
    permission_query_conditions[_name] = "lotus_farm.field_report." + _query
doc_events = {name: {"validate": "lotus_farm.controls.check_farm"} for name in _scoped_doctypes}
doc_events['Farm Block']['before_validate']='lotus_farm.block_forecast.sync_block_dates'
doc_events["Farm"]["before_save"] = ["lotus_farm.controls.preserve_lineage", "lotus_farm.install.validate_reference_company"]
doc_events["Stock Entry"] = {
    "validate": ["lotus_farm.warehouse_issue.validate_issue", "lotus_farm.finance.stock.stock_entry_accounts"],
    "before_submit": ["lotus_farm.warehouse_issue.validate_issue", "lotus_farm.finance.stock.stock_entry_accounts"],
    "before_cancel": ["lotus_farm.shift.release_receipt"],
    "on_trash": "lotus_farm.shift.release_receipt",
}

before_install = "lotus_farm.install.create_roles"

doctype_list_js = {"Role": "public/js/role_list.js"}

# Tổ: a tổ trưởng or giám sát sees only the teams granted to them.
has_permission["Work Team"] = "lotus_farm.controls.work_team_permission"
permission_query_conditions["Work Team"] = "lotus_farm.permissions.work_team"

has_permission['Packhouse Shift'] = 'lotus_farm.controls.farm_permission'
permission_query_conditions['Packhouse Shift'] = 'lotus_farm.permissions.packhouse_shift'
website_route_rules = [{'from_route':'/login','to_route':'lotus_login'},{'from_route':'/lotus/in-phieu','to_route':'lotus_stock_print'},{'from_route':'/lotus/in-cong','to_route':'lotus_timekeeping_print'},{'from_route':'/lotus/in-de-xuat','to_route':'lotus_material_proposal_print'},{'from_route':'/lotus/in-luong','to_route':'lotus_payroll_print'},{'from_route':'/lotus/in-phieu-ngay','to_route':'lotus_daily_form'},{'from_route':'/hr-mobile','to_route':'hr_mobile'},{'from_route':'/lotus/<path:app_path>','to_route':'lotus'}]

doc_events['Material Request']={'validate':['lotus_farm.purchase_flow.validate'],'before_submit':['lotus_farm.purchase_flow.validate']}
doc_events['Purchase Order']={'before_submit':'lotus_farm.purchasing.check_submission'}
doc_events['Purchase Order']['before_submit'] = [doc_events['Purchase Order']['before_submit'], 'lotus_farm.purchase_flow.order_guard']

# Shared mobile PWA notification hooks. Keep existing validation and stock posting hooks.
for _dt in ('Purchase Order', 'Material Request', 'Purchase Receipt', 'Stock Entry'):
    for _event in (('on_update', 'on_submit') if _dt == 'Purchase Order' else ('on_submit',)):
        _value = doc_events.setdefault(_dt, {}).get(_event, [])
        if isinstance(_value, str):
            _value = [_value]
        doc_events[_dt][_event] = [*_value, 'lotus_farm.push_notifications.document_hook']

has_permission['Lotus Alert']='lotus_farm.controls.farm_permission'
permission_query_conditions['Lotus Alert']='lotus_farm.permissions.lotus_alert'
scheduler_events = {'hourly':['lotus_farm.alerts.refresh_alerts']}

doc_events['Employee'] = {**doc_events.get('Employee', {}),
                          'validate': 'lotus_farm.hr_workspace.employee_identity_guard',
                          'on_update': 'lotus_farm.push_notifications.document_hook'}
doc_events['Lotus Candidate'] = {'validate': 'lotus_farm.hr_workspace.candidate_guard'}
has_permission['Lotus Crew Attendance']='lotus_farm.controls.farm_permission'
permission_query_conditions['Lotus Crew Attendance']='lotus_farm.timekeeping.crew_query'

# Closed timekeeping months freeze Attendance and crew sheets (lotus_farm.hr_period).
override_doctype_class={**globals().get('override_doctype_class',{}),
    'Attendance':'lotus_farm.hr_historical.HistoricalAttendance',
    'Employee Checkin':'lotus_farm.hr_historical.HistoricalEmployeeCheckin'}
doc_events.setdefault('Lotus Attendance Punch', {})['before_insert']='lotus_farm.hr_period.punch_period_guard'
doc_events.setdefault('Employee Checkin', {})['validate']='lotus_farm.hr_period.punch_period_guard'
for _event in ('validate','before_cancel'):
    doc_events.setdefault('Salary Structure Assignment',{})[_event]='lotus_farm.hr_period.salary_rate_guard'
for _dt in ('Attendance', 'Lotus Crew Attendance'):
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
scheduler_events.setdefault('cron', {}).setdefault('0 6 * * 1', []).append('lotus_farm.forecast_snapshot.weekly')

# ZKTeco / Ronald Jack / Wise Eye clocks push punches to /iclock/* (lotus_farm.adms).
page_renderer = [*globals().get('page_renderer', []), 'lotus_farm.adms.ADMSRenderer']

has_permission['Lotus Financial Plan'] = 'lotus_farm.finance.planning.permission'
permission_query_conditions['Lotus Financial Plan'] = 'lotus_farm.finance.planning.query_condition'

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
