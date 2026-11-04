import os, json, frappe
os.chdir('/home/frappe/frappe-bench/sites')
frappe.init(site=__import__('os').environ.get('SITE','frontend'))
frappe.connect()
frappe.set_user('Administrator')
from lotus_farm.warehouse import overview, documents, movements
try:
 company=frappe.db.get_value('Company',{},'name')
 base=overview(company)
 # Expected numbers come from the site itself (the counts grow with real data).
 stores=frappe.get_all('Warehouse',filters={'company':company,'is_group':0,'disabled':0},pluck='name')
 catalogue=frappe.db.count('Item',{'disabled':0,'is_stock_item':1})
 stocked=len(frappe.db.sql("""select b.item_code from tabBin b join tabItem i on i.name=b.item_code where i.disabled=0 and i.is_stock_item=1
   and b.warehouse in %s group by b.item_code having sum(b.actual_qty)>0""",(tuple(stores) or ('',),)))
 assert len(base['warehouses'])==len(stores),base['warehouses']
 assert base['catalogue_count']==catalogue,(base['catalogue_count'],catalogue)
 assert base['stocked_count']==stocked,(base['stocked_count'],stocked)
 assert base['total_count']==catalogue,base['total_count']
 assert len(base['items'])==min(50,catalogue) and base['has_more']==(catalogue>50)
 assert all('stock_value' not in r and 'valuation_rate' not in r for r in base['items'])
 page_two=overview(company,start=50)
 assert len(page_two['items'])==max(0,min(50,catalogue-50)) and page_two['has_more']==(catalogue>100)
 print('PASS inventory %d warehouses / %d catalogued / %d stocked; pages of 50'%(len(stores),catalogue,stocked))
 wanted={'stock_status':['Dưới tối thiểu'],'coverage_status':['Cần mua','Chờ nhập']}
 filtered=overview(company,column_filters=json.dumps(wanted))
 assert all(r['stock_status'] in wanted['stock_status'] and r['coverage_status'] in wanted['coverage_status'] for r in filtered['items'])
 assert filtered['catalogue_count']==catalogue and filtered['stocked_count']==stocked
 print('PASS 2 simultaneous filters narrow rows, catalogue / stocked KPIs intact')
 searched=overview(company,search='__UNKNOWN_LOTUS_INVENTORY_QUERY__')
 assert searched['total_count']==0
 assert searched['catalogue_count']==catalogue and searched['stocked_count']==stocked
 print('PASS no-match search does not modify KPIs')
 single=overview(company,warehouse=base['warehouses'][0]['name'])
 assert single['catalogue_count']==catalogue
 assert 0<=single['stocked_count']<=stocked
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
