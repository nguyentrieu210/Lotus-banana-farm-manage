import frappe,uuid,json
from frappe.utils import nowdate
frappe.init(site=__import__('os').environ.get('SITE','frontend'),sites_path='/home/frappe/frappe-bench/sites');frappe.connect();frappe.set_user('Administrator')
from lotus_farm import warehouse as w,warehouse_planning as p
from lotus_farm.issue_request import _approve as approve_issue_request  # spec 005: a Material Issue request is submitted only by its approval (issue_request_fixture.approve_native)
if '__install__' in __import__('sys').argv:
 p.install_fields();frappe.db.commit();print('Planning schema installed');frappe.destroy();raise SystemExit
make=lambda dt,**v:frappe.get_doc(dict(doctype=dt,**v)).insert()
def post(dt,name):
 return w.submit_document(dt,name,modified=w.document(dt,name)['modified'])
try:
 tag=uuid.uuid4().hex[:8];today=nowdate();company='Lotus Agritech'
 # Stock coverage and receiving are checked under the plain purchase policy. The four-signature policy has its own
 # script (verify_purchase_flow.py), so it is switched off for this process only; site_config is not written.
 frappe.conf.lotus_purchase_flow_company=None
 emp=frappe.db.get_value('Employee',{'company':company,'status':'Active'})  # issues name an HRMS receiver
 farm=make('Farm',farm_code='AUDIT-'+tag,farm_name='Audit temporary',company=company).name
 variety=make('Banana Variety',variety_code='AUDIT-'+tag,variety_name='Audit temporary').name
 # An issue finds its lot by the lot code that starts "Khu vực / lô sử dụng", so the code is unique to this run.
 lot='AUD'+tag
 make('Farm Block',farm=farm,block_code=lot,block_name='Audit',area_ha=1,variety=variety)
 store=make('Warehouse',warehouse_name='Audit source '+tag,company=company).name
 other=make('Warehouse',warehouse_name='Audit other '+tag,company=company).name
 item=make('Item',item_code='AUDIT-'+tag,item_name='Audit temporary material',item_group='All Item Groups',stock_uom='Kg',is_stock_item=1).name
 def request(qty):
  # Demand of the warehouse: an approved request to issue material to the lot.
  doc=make('Material Request',company=company,material_request_type='Material Issue',transaction_date=today,schedule_date=today,items=[dict(item_code=item,qty=qty,uom='Kg',stock_uom='Kg',conversion_factor=1,warehouse=store,schedule_date=today,lotus_usage_area=lot)])
  approve_issue_request(doc,'Administrator');return doc
 def coverage():
  result=p.snapshot(company,warehouse=store,from_date=today,to_date=today)
  assert not result['warnings'],result['warnings']
  return next(r for r in result['rows'] if r['item']==item)
 demand=request(100);line=demand.items[0].name
 row=coverage();assert row['required_qty']==100 and row['shortage_qty']==100 and row['status']=='Cần mua','Approved demand without stock must show as a shortage: '+str(row)
 assert any(r['name']==demand.name for r in w.issue_sources(company,'Request')['rows']),'Approved request is not offered to the issue form'
 offered=w.issue_lines(company,'Request',demand.name)['rows']
 assert len(offered)==1 and offered[0]['remaining_qty']==100 and offered[0]['area']==lot and offered[0]['warehouse']==store,offered
 received=w.create_draft(company,'receipt',today,[dict(item=item,qty=100,rate=100)],target=store,receipt_reason='Surplus',client_event_id='receipt-'+tag)
 duplicate=w.create_draft(company,'receipt',today,[dict(item=item,qty=100,rate=100)],target=store,receipt_reason='Surplus',client_event_id='receipt-'+tag)
 assert received['name']==duplicate['name'],'Network retry duplicated receipt'
 try:w.create_draft(company,'receipt',today,[dict(item=item,qty=101,rate=100)],target=store,receipt_reason='Surplus',client_event_id='receipt-'+tag)
 except frappe.ValidationError:pass
 else:raise AssertionError('Changed retry was accepted')
 post(received['doctype'],received['name'])
 assert coverage()['shortage_qty']==0,coverage()
 unrelated=w.create_draft(company,'issue',today,[dict(item=item,qty=30,area=lot+' / other work')],source=store,receiver_employee=emp,notes='Audit hold')
 assert coverage()['available_qty']==70,coverage()
 own=w.create_draft(company,'issue',today,[dict(item=item,qty=40,area=lot,material_request=demand.name,material_request_item=line)],source=store,receiver_employee=emp,issue_mode='Request')
 assert coverage()['shortage_qty']==30 and coverage()['own_draft_qty']==40,coverage()
 assert w.issue_lines(company,'Request',demand.name)['rows'][0]['remaining_qty']==60,'A draft issue must hold its part of the request'
 view=w.document(own['doctype'],own['name'])
 assert view['issue_mode']=='Request' and view['items'][0]['material_request']==demand.name and view['items'][0]['material_request_item']==line,view
 post(own['doctype'],own['name'])
 row=coverage();assert row['issued_qty']==40 and row['remaining_qty']==60 and row['actual_qty']==60 and row['shortage_qty']==30,row
 # Thu hồi từ lô is a receipt of its own: the stock comes back, what the request was issued stays issued.
 returned=w.create_draft(company,'receipt',today,[dict(item=item,qty=20,rate=100,area=lot)],target=store,receipt_reason='Recovery');post(returned['doctype'],returned['name'])
 row=coverage();assert row['issued_qty']==40 and row['remaining_qty']==60 and row['actual_qty']==80 and row['shortage_qty']==10,row
 # Every approved request is demand of its own.
 request(20)
 row=coverage();assert row['required_qty']==120 and row['remaining_qty']==80 and row['shortage_qty']==30,row
 supplier=make('Supplier',supplier_name='Audit supplier '+tag,supplier_type='Company',supplier_group='All Supplier Groups').name
 material=frappe.get_doc('Item',item);material.append('uoms',dict(uom='Box',conversion_factor=10));material.save()
 order=make('Purchase Order',company=company,supplier=supplier,transaction_date=today,schedule_date=today,currency='VND',items=[dict(item_code=item,qty=2,uom='Box',conversion_factor=10,rate=1000,warehouse=store,schedule_date=today)]);flow=frappe.conf.get('lotus_purchase_flow_company');frappe.conf.lotus_purchase_flow_company=None;order.db_set('lotus_approval_status','Chờ duyệt',update_modified=False);order.submit();frappe.conf.lotus_purchase_flow_company=flow
 row=coverage();assert row['incoming_qty']==20 and row['to_buy_qty']==10,row
 main=w.overview(company,warehouse=store,search=item,from_date=today,to_date=today)['items'][0]
 assert (main.demand_qty,main.available_qty,main.demand_shortage_qty,main.incoming_qty,main.to_buy_qty,main.coverage_status)==(80,50,30,20,10,'Cần mua'),main

 purchase=p.create_purchase_request(company,store,today,today,[item]);assert purchase['name'],purchase
 retry=p.create_purchase_request(company,store,today,today,[item]);assert not retry.get('name'),retry
 row=coverage();assert row['requested_qty']==10 and row['to_request_qty']==0 and row['to_buy_qty']==10,row
 info=p.purchase_request(purchase['name']);p.purchase_action(info['name'],info['modified'],'submit')
 # Receive a partial order using stock units; retries and other drafts cannot overreceive.
 po_info=p.purchase_order(order.name);po_line=po_info['items'][0]['line']
 first=p.receive_order(order.name,today,{po_line:10},'purchase-receipt-'+tag)
 again=p.receive_order(order.name,today,{po_line:10},'purchase-receipt-'+tag)
 assert first['name']==again['name'],'Purchase receipt retry duplicated'
 waiting=p.purchase_order(order.name);assert waiting['items'][0]['remaining_qty']==10,waiting
 try:p.receive_order(order.name,today,{po_line:11},'purchase-over-'+tag)
 except frappe.ValidationError:pass
 else:raise AssertionError('Overreceipt bypassed existing draft')
 pr=p.purchase_receipt(first['name']);p.receipt_action(pr['name'],pr['modified'],'submit')
 po_info=p.purchase_order(order.name);assert po_info['items'][0]['received_qty']==10,po_info
 row=coverage();assert row['incoming_qty']==10 and row['actual_qty']==90,row
 # Inventory count must retain value even if a stale browser sends rate zero.
 count=w.create_draft(company,'count',today,[dict(item=item,qty=89,rate=0)],target=store)
 count_doc=frappe.get_doc('Stock Reconciliation',count['name'])
 assert count_doc.items[0].valuation_rate==100,count_doc.items[0].as_dict()
 # Full document listing and warehouse scope; user data is never mutated.
 listing=w.documents(company,warehouse=store,search=received['name'])
 assert listing['total_count']==1,listing
 excluded=w.documents(company,warehouse=other,search=received['name']);assert excluded['total_count']==0,excluded
 ledger=w.movements(company,warehouse=store,search=first['name'])
 assert ledger['total_count']==1 and ledger['rows'][0].opening_qty==80 and ledger['rows'][0].qty_after_transaction==90,ledger
 # The issue to the lot shows who received it and where it was used.
 issued=w.movements(company,warehouse=store,search=own['name'])
 assert issued['total_count']==1 and issued['rows'][0].out_qty==40 and issued['rows'][0].usage_area==lot and issued['rows'][0].receiver,issued
 # The print template includes every item, keeps drafts marked, and escapes text.

 for kind,lines in [('issue',[dict(item=item,qty=60,area='A'),dict(item=item,qty=40,area='B')]),('transfer',[dict(item=item,qty=100)])]:
  try:w.create_draft(company,kind,today,lines,source=store,target=other,receiver_employee=emp,notes='Over-stock check')
  except frappe.ValidationError as exc:assert 'thiếu' in str(exc),str(exc)
  else:raise AssertionError('Over-stock outbound draft accepted: '+kind)
 from lotus_farm.www.lotus_stock_print import get_context
 frappe.form_dict=frappe._dict(doctype='Stock Entry',name=received['name'])
 context=frappe._dict();get_context(context)
 html=frappe.render_template('lotus_farm/www/lotus_stock_print.html',context)
 assert received['name'] in html and '100' in html and 'PHIẾU NHẬP KHO' in html,html[:1000]
 assert 'In / Lưu PDF' in html
 for dt,name,title in [('Purchase Receipt',first['name'],'PHIẾU NHẬN HÀNG'),('Material Request',purchase['name'],'PHIẾU ĐỀ XUẤT MUA VẬT TƯ'),('Material Request',demand.name,'PHIẾU ĐỀ XUẤT CẤP VẬT TƯ'),('Stock Entry',own['name'],'PHIẾU XUẤT KHO'),('Stock Reconciliation',count['name'],'PHIẾU KIỂM KÊ KHO')]:
  frappe.form_dict=frappe._dict(doctype=dt,name=name);context=frappe._dict();get_context(context)
  rendered=frappe.render_template('lotus_farm/www/lotus_stock_print.html',context)
  assert name in rendered and title in rendered and 'In / Lưu PDF' in rendered,(dt,rendered[:500])
 frappe.form_dict=frappe._dict(doctype='User',name='Administrator')
 try:get_context(frappe._dict())
 except frappe.PermissionError:pass
 else:raise AssertionError('Print accepted an unrelated doctype')
 from lotus_farm.www.lotus_stock_print import download_pdf
 download_pdf('Stock Entry',received['name'])
 pdf=frappe.local.response.filecontent
 assert pdf.startswith(b'%PDF') and len(pdf)>1000,'PDF rendering failed'
 print('Printable PDF verified:',len(pdf),'bytes')
 print(json.dumps(dict(coverage=row,receipt_retry=received['name'],purchase_retry=retry,inventory_rate=count_doc.items[0].valuation_rate,rollback=True),default=str))
finally:
 frappe.db.rollback();frappe.destroy()
