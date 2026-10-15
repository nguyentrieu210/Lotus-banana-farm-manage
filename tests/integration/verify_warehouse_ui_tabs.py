"""Read-only Lotus Kho acceptance checks: Stock, document history, ledger and purchase planning."""
import os, frappe
from datetime import date, timedelta
os.chdir('/home/frappe/frappe-bench/sites')
frappe.init(site='frontend')
frappe.connect()
frappe.set_user('Administrator')
from lotus_farm import warehouse, warehouse_planning
from lotus_farm.table_filters import faceted_distinct
try:
    company=frappe.db.get_value('Company',{},'name')
    stock=warehouse.overview(company)
    assert stock['catalogue_count']>0 and 'warehouses' in stock
    print('PASS Stock:',stock['catalogue_count'],'items')
    history=warehouse.documents(company)
    ledger=warehouse.movements(company)
    assert 'filter_values' in history and 'filter_values' in ledger
    assert history['total_count']>=len(history['rows'])
    assert ledger['total_count']>=len(ledger['rows'])
    for row in history['rows']:
        assert row.name and row.posting_date and row.doctype
    for row in ledger['rows']:
        assert row.item_code and row.warehouse and row.voucher_no
    print('PASS Documents:',history['total_count'],'/ ledger rows:',ledger['total_count'])
    today=date.today()
    plan=warehouse_planning.overview(company,from_date=str(today),to_date=str(today+timedelta(days=6)))
    assert all(k in plan for k in ('rows','orders','requests','filter_values','warnings','total_count'))
    assert isinstance(plan['orders'],list) and isinstance(plan['requests'],list)
    print('PASS Planned material/purchases:',len(plan['requests']),len(plan['orders']))
    sample=[dict(item='Phân',warehouse='KHO 1',status='Cần mua'),dict(item='Phân',warehouse='KHO 2',status='Đủ hàng'),dict(item='Thuốc',warehouse='KHO 2',status='Chờ nhập')]
    result=faceted_distinct(sample,['item','warehouse','status'],{'warehouse':['KHO 2']})
    assert {r['value'] for r in result['warehouse']}=={'KHO 1','KHO 2'}
    assert {r['value'] for r in result['item']}=={'Phân','Thuốc'}
    print('PASS Excel column choices')
finally:
    frappe.db.rollback()
    frappe.destroy()
