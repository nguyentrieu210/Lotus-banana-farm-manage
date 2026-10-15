import os, json, frappe
os.chdir('/home/frappe/frappe-bench/sites')
frappe.init(site='frontend')
frappe.connect()
frappe.set_user('Administrator')
from lotus_farm.warehouse import overview, documents, movements
try:
 company=frappe.db.get_value('Company',{},'name')
 base=overview(company)
 assert len(base['warehouses'])==4,base['warehouses']
 assert base['catalogue_count']==55,base['catalogue_count']
 assert base['stocked_count']==8,base['stocked_count']
 assert base['total_count']==55,base['total_count']
 assert len(base['items'])==50 and base['has_more']
 assert all('stock_value' not in r and 'valuation_rate' not in r for r in base['items'])
 page_two=overview(company,start=50)
 assert len(page_two['items'])==5 and not page_two['has_more']
 print('PASS actual inventory 4 warehouses / 55 catalogued / 8 stocked; pagination 50+5')
 filtered=overview(company,column_filters=json.dumps({'stock_status':['Dưới tối thiểu'],'coverage_status':['Cần mua','Chờ nhập']}))
 assert filtered['total_count']==0 and filtered['items']==[]
 assert filtered['catalogue_count']==55 and filtered['stocked_count']==8
 print('PASS 2 simultaneous filters yield zero rows but 55 catalog / 8 stocked intact')
 searched=overview(company,search='__UNKNOWN_LOTUS_INVENTORY_QUERY__')
 assert searched['total_count']==0
 assert searched['catalogue_count']==55 and searched['stocked_count']==8
 print('PASS no-match search does not modify KPIs')
 single=overview(company,warehouse=base['warehouses'][0]['name'])
 assert single['catalogue_count']==55
 assert 0<=single['stocked_count']<=8
 print('PASS warehouse scoped inventory')
 doc=documents(company)
 mov=movements(company)
 assert 'total_count' in doc and 'rows' in doc
 assert 'total_count' in mov and 'rows' in mov
 assert all('stock_value_difference' not in row for row in mov['rows'])
 print('PASS document history and stock ledger APIs (no valuation leakage)',doc['total_count'],mov['total_count'])
finally:
 frappe.db.rollback()
 frappe.destroy()
