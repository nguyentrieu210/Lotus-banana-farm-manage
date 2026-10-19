"""Read-only checks: land scope never hides company totals, and report filters apply."""
import json
import sys
import importlib.util
import frappe

frappe.init(site='frontend')
frappe.connect()
frappe.set_user('Administrator')
try:
    from lotus_farm import reporting
    if len(sys.argv)>1:
        spec=importlib.util.spec_from_file_location('preview_reporting',sys.argv[1])
        reporting=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(reporting)
    args=dict(from_date='2026-10-13',to_date='2026-10-19',farm='LOTUS-222',company='Lotus Agritech')
    full=reporting.charts(**args)
    selected=reporting.charts(**args,zone='B')
    for key in ('buying','sales','stock','people'):
        assert selected[key]['allowed'],(key,selected[key])
        assert 'note' not in selected[key],(key,selected[key])
        assert selected[key]==full[key],key
        assert 'options' in selected[key],key
    filtered=reporting.charts(**args,zone='B',report_filters=json.dumps(dict(supplier='__none__',customer='__none__',department='__none__',stock_type='__none__')))
    assert filtered['buying']['count']==filtered['sales']['count']==0
    assert filtered['people']['active']==0
    assert not filtered['stock']['months']
    assert selected['land']['blocks']==12
    print('PASS: zone B retains company totals; supplier/customer/department/stock filters applied; land remains 12 care blocks.')
finally:
    frappe.db.rollback()
    frappe.destroy()
