import frappe,uuid
frappe.init(site='frontend',sites_path='/home/frappe/frappe-bench/sites');frappe.connect();frappe.set_user('Administrator')
def post(dt,name):
 return w.submit_document(dt,name,modified=w.document(dt,name)['modified'])
try:
 from lotus_farm import warehouse as w
 code='CHECK-ZERO-'+uuid.uuid4().hex[:8]
 frappe.get_doc(dict(doctype='Item',item_code=code,item_name='Zero stock check',item_group='All Item Groups',stock_uom='Kg',is_stock_item=1,valuation_rate=100)).insert()
 store=frappe.db.get_value('Warehouse',{'company':'Lotus Agritech','is_group':0,'disabled':0},'name')
 try:w.create_draft('Lotus Agritech','issue','2026-10-14',[dict(item=code,qty=1,area='QA')],source=store,receiver='QA',notes='Zero stock test')
 except frappe.ValidationError as e:
  assert code in str(e) and 'thiếu' in str(e),str(e)
  print('PASS: zero-stock issue rejected before draft insert')
 else:raise AssertionError('Zero-stock issue draft was saved')
 doc=frappe.get_doc(dict(doctype='Stock Entry',stock_entry_type='Material Issue',company='Lotus Agritech',posting_date='2026-10-14',lotus_issue_mode='Manual',lotus_receiver='QA',remarks='QA',items=[dict(item_code=code,s_warehouse=store,qty=1,uom='Kg',stock_uom='Kg',conversion_factor=1,allow_zero_valuation_rate=1,lotus_usage_area='QA')]));doc.insert()
 try:post('Stock Entry',doc.name)
 except frappe.ValidationError as e:assert code in str(e),str(e);print('PASS: preexisting zero-stock draft rejected before submit')
 else:raise AssertionError('Zero-stock issue was submitted')
 print('Test transaction rolled back')
finally:frappe.db.rollback();frappe.destroy()
