"""Read-only integration check for Excel-style filters against real Frappe site."""
import os, json, frappe
os.chdir('/home/frappe/frappe-bench/sites')
frappe.init(site='frontend')
frappe.connect()
frappe.set_user('Administrator')
from lotus_farm.table_filters import faceted_distinct, matches
from lotus_farm import warehouse

try:
    sample=[
        dict(group='Phân',status='Có tồn',qty=20),
        dict(group='Phân',status='Thiếu',qty=0),
        dict(group='Thuốc',status='Có tồn',qty=7),
    ]
    assert [r['value'] for r in faceted_distinct(
        sample,['group','status'],{'group':['Phân']})['group']] == ['Phân','Thuốc']
    assert {r['value'] for r in faceted_distinct(
        sample,['group','status'],{'group':['Phân']})['status']} == {'Có tồn','Thiếu'}
    assert [r['value'] for r in faceted_distinct(
        sample,['group','status'],{'group':['Dữ liệu không có']})['group']] == ['Phân','Thuốc','Dữ liệu không có']
    assert not any(matches(r, {'group':[]}) for r in sample)
    print('PASS Excel faceted multi-select and empty selection logic')

    company=frappe.db.get_value('Company', {}, 'name')
    base=warehouse.overview(company)
    assert base['catalogue_count']==55
    assert len(base['warehouses'])==4
    names=[r['value'] for r in base['filter_values']['item_group'] if r['value']]
    assert names
    group=names[0]
    one=warehouse.overview(company,column_filters=json.dumps({'item_group':[group]}))
    assert all(x['item_group']==group for x in one['items'])
    assert {v['value'] for v in one['filter_values']['item_group']}==set(names)
    print('PASS group filter retains all group choices in its own dropdown')

    if one['items']:
        status=one['items'][0]['stock_status']
        two=warehouse.overview(company,column_filters=json.dumps({'item_group':[group],'stock_status':[status]}))
        assert all(r['item_group']==group and r['stock_status']==status for r in two['items'])
        assert status in [v['value'] for v in two['filter_values']['stock_status']]
        print('PASS two columns filter together and preserve checked status')

    missing=warehouse.overview(company,column_filters=json.dumps({'item_group':['__NOT_EXIST__']}))
    assert missing['total_count']==0
    assert missing['catalogue_count']==55
    assert '__NOT_EXIST__' in [v['value'] for v in missing['filter_values']['item_group']]
    print('PASS no-match state preserves catalogue and selected filter')
finally:
    frappe.db.rollback()
    frappe.destroy()
