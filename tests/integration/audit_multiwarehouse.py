import frappe,uuid,json
frappe.init(site=__import__('os').environ.get('SITE','frontend'),sites_path='/home/frappe/frappe-bench/sites');frappe.connect();frappe.set_user('Administrator')
try:
 from lotus_farm import warehouse as w
 company='Lotus Agritech';tag=uuid.uuid4().hex[:8];make=lambda dt,**v:frappe.get_doc(dict(doctype=dt,**v)).insert()
 stores=[make('Warehouse',warehouse_name='Multi '+str(i)+' '+tag,company=company).name for i in range(2)]
 items=[make('Item',item_code='MULTI-'+str(i)+'-'+tag,item_name='Multi review '+str(i),item_group='All Item Groups',stock_uom='Kg',is_stock_item=1).name for i in range(2)]
 doc=make('Stock Entry',company=company,stock_entry_type='Material Receipt',lotus_receipt_reason='Surplus',items=[dict(item_code=code,qty=1,t_warehouse=store,basic_rate=100,set_basic_rate_manually=1) for code,store in zip(items,stores)])
 before=w.document('Stock Entry',doc.name)
 # A draft spread over two warehouses is not a simple Kho draft: it cannot be edited (and silently merged into one warehouse) here.
 assert not before['can_write'],before
 try:
  w.create_draft(company,'receipt',doc.posting_date,[dict(item=r['item'],qty=r['qty'],rate=r['rate']) for r in before['items']],target=before['items'][0]['target'],existing_name=doc.name,base_modified=before['modified'])
  raise AssertionError('multi-warehouse draft was rewritten')
 except frappe.ValidationError as e:assert 'đơn giản' in str(e),str(e)
 doc.reload();assert [r.t_warehouse for r in doc.items]==stores
 print(json.dumps(dict(can_write=before['can_write'],before=[r['target'] for r in before['items']],after=[r.t_warehouse for r in doc.items])))
 print('PASS multi-warehouse draft stays read-only')
finally:frappe.db.rollback();frappe.destroy()
