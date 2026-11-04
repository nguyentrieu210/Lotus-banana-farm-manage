import frappe,uuid,json,time
from frappe.utils import nowdate,add_days
from lotus_farm import warehouse as w,warehouse_planning as p
frappe.init(site=__import__('os').environ.get('SITE','frontend'),sites_path='/home/frappe/frappe-bench/sites');frappe.connect();frappe.set_user('Administrator')
make=lambda dt,**values:frappe.get_doc(dict(doctype=dt,**values)).insert()
result={}
try:
 company='Lotus Agritech';tag=uuid.uuid4().hex[:8];today=nowdate()
 store=make('Warehouse',warehouse_name='Review '+tag,company=company).name
 item=make('Item',item_code='REVIEW-'+tag,item_name='Review temporary',item_group='All Item Groups',stock_uom='Kg',is_stock_item=1,uoms=[dict(uom='Kg',conversion_factor=1),dict(uom='Box',conversion_factor=10)]).name
 supplier=make('Supplier',supplier_name='Review '+tag,supplier_type='Company',supplier_group='All Supplier Groups').name
 req=make('Material Request',company=company,material_request_type='Purchase',transaction_date=today,schedule_date=today,items=[dict(item_code=item,qty=10,uom='Box',conversion_factor=10,warehouse=store,schedule_date=today)]);req.submit()
 order=make('Purchase Order',company=company,supplier=supplier,transaction_date=today,schedule_date=today,currency='VND',items=[dict(item_code=item,qty=3,uom='Box',conversion_factor=10,rate=1000,warehouse=store,schedule_date=today,material_request=req.name,material_request_item=req.items[0].name)]);frappe.local.lotus_policy_approved=order.name;order.submit();frappe.local.lotus_policy_approved=None;req.reload()
 supply=p._supply(company,{store},frappe.utils.getdate(today))
 result['purchase_uom']=dict(request_stock_qty=req.items[0].stock_qty,native_ordered_qty=req.items[0].ordered_qty,expected_pending=70,app_pending=supply[1][(item,store)])
 receipt=make('Stock Entry',company=company,stock_entry_type='Material Receipt',lotus_receipt_reason='Surplus',posting_date=today,items=[dict(item_code=item,qty=2,uom='Box',conversion_factor=10,t_warehouse=store,basic_rate=1000,set_basic_rate_manually=1,allow_zero_valuation_rate=1)])
 view=w.document('Stock Entry',receipt.name)
 result['stock_entry_uom']=dict(native_qty=receipt.items[0].qty,native_uom=receipt.items[0].uom,native_stock_qty=receipt.items[0].transfer_qty,app_qty=view['items'][0]['qty'],app_uom=view['items'][0]['uom'],can_write=view['can_write'])
 changed=w.create_draft(company,'receipt',today,[dict(item=item,qty=view['items'][0]['qty'],uom=view['items'][0]['uom'],rate=view['items'][0]['rate'])],target=store,existing_name=receipt.name,base_modified=view['modified']);receipt.reload()
 result['stock_entry_uom']['saved_stock_qty']=receipt.items[0].transfer_qty
 initial=w.create_draft(company,'count',today,[dict(item=item,qty=10,rate=100)],target=store,count_purpose='Opening Stock');initial_view=w.document(initial['doctype'],initial['name'])
 w.create_draft(company,'count',today,[dict(item=item,qty=10,rate=100)],target=store,count_purpose='Opening Stock',existing_name=initial['name'],base_modified=initial_view['modified'])
 initial_doc=frappe.get_doc(initial['doctype'],initial['name']);result['opening_edit']=dict(before_kind=initial_view['kind'],after_kind=initial_doc.purpose,before_rate=initial_view['items'][0]['rate'],after_rate=initial_doc.items[0].valuation_rate)
 # Posting needs the version the user reviewed: a document changed after review is refused.
 stale=w.create_draft(company,'receipt',today,[dict(item=item,qty=5,rate=100)],target=store,receipt_reason='Surplus')
 seen=w.document(stale['doctype'],stale['name'])
 changed_doc=frappe.get_doc(stale['doctype'],stale['name']);changed_doc.items[0].qty=9;changed_doc.save()
 for version in (None,seen['modified']):
  try:w.submit_document(stale['doctype'],stale['name'],modified=version);raise AssertionError('changed document was posted')
  except frappe.ValidationError as e:assert 'thay đổi' in str(e),str(e)
 changed_doc.reload();assert changed_doc.docstatus==0
 w.submit_document(stale['doctype'],stale['name'],modified=w.document(stale['doctype'],stale['name'])['modified']);changed_doc.reload()  # reviewed again, then posted: Bin=9
 result['stale_submit']=dict(reviewed_qty=seen['items'][0]['qty'],posted_qty=changed_doc.items[0].qty,docstatus=changed_doc.docstatus)
 # Historical period excludes the new purchase request's today schedule date.
 yesterday=add_days(today,-1)
 need=make('Material Request',company=company,material_request_type='Material Issue',transaction_date=yesterday,schedule_date=yesterday,items=[dict(item_code=item,qty=50,uom='Kg',conversion_factor=1,warehouse=store,schedule_date=yesterday)]);need.submit()
 # A finished demand period cannot raise a purchase request (so a retry cannot duplicate one either).
 try:p.create_purchase_request(company,store,yesterday,yesterday,[item]);raise AssertionError('past period raised a purchase request')
 except frappe.ValidationError as e:assert 'Kỳ nhu cầu đã kết thúc' in str(e),str(e)
 result['historical_purchase_retry']='blocked'
 # Bin=9: the first 6-unit draft holds stock, so a second 6-unit draft is refused.
 one=w.create_draft(company,'issue',today,[dict(item=item,qty=6,area=frappe.db.get_value('Farm Block',{},'block_code'))],source=store,receiver_employee=frappe.db.get_value('Employee',{'company':company,'status':'Active'}),notes='Draft hold review')
 try:
  w.create_draft(company,'issue',today,[dict(item=item,qty=6,area=frappe.db.get_value('Farm Block',{},'block_code'))],source=store,receiver_employee=frappe.db.get_value('Employee',{'company':company,'status':'Active'}),notes='Draft hold review');raise AssertionError('second draft over-allocated stock')
 except frappe.ValidationError as e:assert 'thiếu' in str(e),str(e)
 result['draft_overallocation']=dict(actual=9,first=one['name'],second='blocked')
 # Read-only timings and evidence for live state; all temporary business writes roll back.
 assert result['stock_entry_uom']['saved_stock_qty']==20,result
 print(json.dumps(result,ensure_ascii=True,default=str))
finally:frappe.db.rollback();frappe.destroy()
