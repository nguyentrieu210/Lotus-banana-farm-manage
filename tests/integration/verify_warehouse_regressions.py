import frappe,uuid,json,time
from frappe.utils import nowdate,add_days
from lotus_farm import warehouse as w,warehouse_planning as p
frappe.init(site='frontend',sites_path='/home/frappe/frappe-bench/sites');frappe.connect();frappe.set_user('Administrator')
make=lambda dt,**values:frappe.get_doc(dict(doctype=dt,**values)).insert()
result={}
def blocked(fn):
 try:fn()
 except frappe.ValidationError:return
 raise AssertionError('Expected operation to be rejected')
try:
 company='Lotus Agritech';tag=uuid.uuid4().hex[:8];today=nowdate()
 store=make('Warehouse',warehouse_name='Review '+tag,company=company).name
 item=make('Item',item_code='REVIEW-'+tag,item_name='Review temporary',item_group='All Item Groups',stock_uom='Kg',is_stock_item=1,uoms=[dict(uom='Kg',conversion_factor=1),dict(uom='Box',conversion_factor=10)]).name
 supplier=make('Supplier',supplier_name='Review '+tag,supplier_type='Company',supplier_group='All Supplier Groups').name
 req=make('Material Request',company=company,material_request_type='Purchase',transaction_date=today,schedule_date=today,items=[dict(item_code=item,qty=10,uom='Box',conversion_factor=10,warehouse=store,schedule_date=today)]);req.submit()
 order=make('Purchase Order',company=company,supplier=supplier,transaction_date=today,schedule_date=today,currency='VND',items=[dict(item_code=item,qty=3,uom='Box',conversion_factor=10,rate=1000,warehouse=store,schedule_date=today,material_request=req.name,material_request_item=req.items[0].name)]);order.submit();req.reload()
 supply=p._supply(company,{store},frappe.utils.getdate(today))
 result['purchase_uom']=dict(request_stock_qty=req.items[0].stock_qty,native_ordered_qty=req.items[0].ordered_qty,expected_pending=70,app_pending=supply[1][(item,store)])
 receipt=make('Stock Entry',company=company,stock_entry_type='Material Receipt',posting_date=today,items=[dict(item_code=item,qty=2,uom='Box',conversion_factor=10,t_warehouse=store,basic_rate=1000,set_basic_rate_manually=1,allow_zero_valuation_rate=1)])
 view=w.document('Stock Entry',receipt.name)
 result['stock_entry_uom']=dict(native_qty=receipt.items[0].qty,native_uom=receipt.items[0].uom,native_stock_qty=receipt.items[0].transfer_qty,app_qty=view['items'][0]['qty'],app_uom=view['items'][0]['uom'],can_write=view['can_write'])
 assert view['items'][0]['qty']==20 and not view['can_write']
 blocked(lambda:w.create_draft(company,'receipt',today,[dict(item=item,qty=20,rate=100)],target=store,existing_name=receipt.name,base_modified=view['modified']))
 store2=make('Warehouse',warehouse_name='Review second '+tag,company=company).name
 multi=make('Stock Entry',company=company,stock_entry_type='Material Receipt',posting_date=today,items=[dict(item_code=item,qty=1,t_warehouse=x,basic_rate=100,set_basic_rate_manually=1,allow_zero_valuation_rate=1) for x in (store,store2)])
 assert not w.document('Stock Entry',multi.name)['can_write']
 blocked(lambda:w.create_draft(company,'receipt',today,[dict(item=item,qty=2,rate=100)],target=store,existing_name=multi.name,base_modified=str(multi.modified)))
 assert supply[1][(item,store)]==70
 initial=w.create_draft(company,'count',today,[dict(item=item,qty=10,rate=100)],target=store,count_purpose='Opening Stock');initial_view=w.document(initial['doctype'],initial['name'])
 blocked(lambda:w.create_draft(company,'count',today,[dict(item=item,qty=10,rate=100)],target=store,existing_name=initial['name'],base_modified=initial_view['modified']))
 w.create_draft(company,'count',today,[dict(item=item,qty=10,rate=100)],target=store,count_purpose='Opening Stock',existing_name=initial['name'],base_modified=initial_view['modified'])
 initial_doc=frappe.get_doc(initial['doctype'],initial['name']);assert initial_doc.purpose=='Opening Stock' and initial_doc.items[0].valuation_rate==100
 # No modified timestamp is accepted by stock submit; a freshly changed document is posted.
 stale=w.create_draft(company,'receipt',today,[dict(item=item,qty=5,rate=100)],target=store)
 seen=w.document(stale['doctype'],stale['name'])
 changed_doc=frappe.get_doc(stale['doctype'],stale['name']);changed_doc.items[0].qty=9;changed_doc.save()
 blocked(lambda:w.submit_document(stale['doctype'],stale['name']))
 blocked(lambda:w.submit_document(stale['doctype'],stale['name'],modified=seen['modified']))
 changed_doc.reload();assert changed_doc.docstatus==0
 w.submit_document(stale['doctype'],stale['name'],modified=str(changed_doc.modified));changed_doc.reload();assert changed_doc.docstatus==1
 # Historical period excludes the new purchase request's today schedule date.
 yesterday=add_days(today,-1)
 need=make('Material Request',company=company,material_request_type='Material Issue',transaction_date=yesterday,schedule_date=yesterday,items=[dict(item_code=item,qty=50,uom='Kg',conversion_factor=1,warehouse=store,schedule_date=yesterday)]);need.submit()
 blocked(lambda:p.create_purchase_request(company,store,yesterday,yesterday,[item]))
 # Bin=9; both 6-unit outbound drafts are accepted without accounting for each other.
 one=w.create_draft(company,'issue',today,[dict(item=item,qty=6,area='A')],source=store,receiver='QA',notes='Draft hold review')
 blocked(lambda:w.create_draft(company,'issue',today,[dict(item=item,qty=6,area='B')],source=store,receiver='QA',notes='Draft hold review'))
 for n in range(60):make('Item',item_code='SORT-'+tag+'-'+str(n),item_name='SORT-'+tag+'-'+f'{n:02}',item_group='All Item Groups',stock_uom='Kg',is_stock_item=1)
 page=w.overview(company,warehouse=store,search='SORT-'+tag,sort_model=[dict(colId='name',sort='desc')])
 assert page['total_count']==60 and len(page['items'])==50 and page['items'][0]['item_name'].endswith('-59') and page['items'][-1]['item_name'].endswith('-10'),page
 print(json.dumps(dict(regressions=['A01','A02','A03','A04','A05','A06','A07','A08'],result='PASS',rollback=True)))
finally:frappe.db.rollback();frappe.destroy()
