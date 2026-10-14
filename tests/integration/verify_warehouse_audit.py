import frappe,uuid,json
from frappe.utils import nowdate,add_days
frappe.init(site='frontend',sites_path='/home/frappe/frappe-bench/sites');frappe.connect();frappe.set_user('Administrator')
from lotus_farm import warehouse as w,warehouse_planning as p
if '__install__' in __import__('sys').argv:
 p.install_fields();frappe.db.commit();print('Planning schema installed');frappe.destroy();raise SystemExit
make=lambda dt,**v:frappe.get_doc(dict(doctype=dt,**v)).insert()
def post(dt,name):
 return w.submit_document(dt,name,modified=w.document(dt,name)['modified'])
try:
 tag=uuid.uuid4().hex[:8];today=nowdate();company='Lotus Agritech'
 farm=make('Farm',farm_code='AUDIT-'+tag,farm_name='Audit temporary',company=company).name
 variety=make('Banana Variety',variety_code='AUDIT-'+tag,variety_name='Audit temporary').name
 block=make('Farm Block',farm=farm,block_code='AUDIT',block_name='Audit',area_ha=1,variety=variety).name
 plot=make('Farm Plot',farm=farm,farm_block=block,plot_code='AUDIT.1',plot_name='Audit',area_ha=1).name
 cycle=make('Crop Cycle',farm=farm,farm_block=block,farm_plot=plot,cycle_no=1,planting_date=add_days(today,-100),variety=variety).name
 store=make('Warehouse',warehouse_name='Audit source '+tag,company=company).name
 other=make('Warehouse',warehouse_name='Audit other '+tag,company=company).name
 item=make('Item',item_code='AUDIT-'+tag,item_name='Audit temporary material',item_group='All Item Groups',stock_uom='Kg',is_stock_item=1).name
 cat=make('Work Category',category_code='AUDIT-'+tag,category_name='Audit work').name
 work=make('Work Type',work_code='AUDIT-'+tag,work_name='Audit work',category=cat,uom='Kg',productivity_per_workday=100).name
 basis=make('Norm Basis',basis_code='AUDIT-'+tag,basis_name='Audit basis',uom='Kg').name
 norm=make('Material Norm Profile',farm=farm,profile_name='AUDIT-'+tag,version=1,work_type=work,valid_from=add_days(today,-1),valid_to=add_days(today,30),approval_state='Approved',lines=[dict(item=item,uom='Kg',norm_qty=1,norm_basis=basis,basis_qty=1,frequency=1,conversion_factor=1)])
 scope=dict(farm=farm,farm_block=block,farm_plot=plot,crop_cycle=cycle,posting_date=today)
 plan=make('Daily Work Plan',farm=farm,posting_date=today,lines=[dict(farm=farm,farm_block=block,farm_plot=plot,crop_cycle=cycle,work_type=work,planned_qty=100,norm_profile=norm.name)])
 plan.submit()
 before=p.snapshot(company,from_date=today,to_date=today,farm=farm)
 assert before['warnings'],'Uncalculated plan must not appear sufficiently supplied'
 req=make('Material Requirement',**scope,work_plan=plan.name,work_plan_line=plan.lines[0].name);req.submit()
 missing=p.snapshot(company,from_date=today,to_date=today,farm=farm)
 assert any(s['name']==req.name for s in missing['unmapped']),missing
 p.assign_warehouse(company,req.name,store);req.reload()
 received=w.create_draft(company,'receipt',today,[dict(item=item,qty=100,rate=100)],target=store,client_event_id='receipt-'+tag)
 duplicate=w.create_draft(company,'receipt',today,[dict(item=item,qty=100,rate=100)],target=store,client_event_id='receipt-'+tag)
 assert received['name']==duplicate['name'],'Network retry duplicated receipt'
 try:w.create_draft(company,'receipt',today,[dict(item=item,qty=101,rate=100)],target=store,client_event_id='receipt-'+tag)
 except frappe.ValidationError:pass
 else:raise AssertionError('Changed retry was accepted')
 post(received['doctype'],received['name'])
 def coverage():
  result=p.snapshot(company,warehouse=store,from_date=today,to_date=today,farm=farm)
  assert not result['warnings'],result['warnings']
  return next(r for r in result['rows'] if r['item']==item)
 assert coverage()['shortage_qty']==0,coverage()
 unrelated=w.create_draft(company,'issue',today,[dict(item=item,qty=30,area='Other audit work')],source=store,receiver='Audit',notes='Audit hold')
 assert coverage()['available_qty']==70,coverage()
 line=req.lines[0].name
 own=w.create_draft(company,'issue',today,[dict(item=item,qty=40,area=block+' / '+plot,requirement=req.name,requirement_line=line)],source=store,receiver='Audit',issue_mode='Plan',work_plan=plan.name)
 assert coverage()['shortage_qty']==30 and coverage()['own_draft_qty']==40,coverage()
 post(own['doctype'],own['name'])
 row=coverage();assert row['remaining_qty']==60 and row['actual_qty']==60 and row['shortage_qty']==30,row
 result=make('Daily Work Result',**scope,work_plan=plan.name,work_plan_line=plan.lines[0].name,completed_qty=40,actual_workdays=1,unfinished_reason='Audit partial work');result.submit()
 entry=frappe.get_doc('Stock Entry',own['name'])
 use=make('Material Consumption',**scope,work_result=result.name,material_requirement=req.name,item=item,warehouse=store,stock_entry=entry.name,stock_entry_detail=entry.items[0].name,consumed_qty=20);use.submit()
 assert coverage()['remaining_qty']==60,'Consumption deducted from warehouse demand twice'
 returned=w.create_draft(company,'receipt',today,[dict(item=item,qty=20,rate=100)],target=store);post(returned['doctype'],returned['name'])
 return_doc=frappe.get_doc('Stock Entry',returned['name'])
 recovery=make('Material Recovery',**scope,consumption=use.name,recovered_qty=20,stock_entry=return_doc.name,stock_entry_detail=return_doc.items[0].name);recovery.submit()
 row=coverage();assert row['issued_qty']==20 and row['remaining_qty']==80 and row['shortage_qty']==30,row
 # A release request linked to the same requirement must not create another demand.
 mr=make('Material Request',company=company,material_request_type='Material Issue',transaction_date=today,schedule_date=today,items=[dict(item_code=item,qty=80,uom='Kg',stock_uom='Kg',conversion_factor=1,warehouse=store,schedule_date=today,lotus_requirement=req.name,lotus_requirement_line=line,lotus_usage_area=block+' / '+plot)]);mr.submit()
 assert coverage()['required_qty']==100,coverage()
 supplier=make('Supplier',supplier_name='Audit supplier '+tag,supplier_type='Company',supplier_group='All Supplier Groups').name
 material=frappe.get_doc('Item',item);material.append('uoms',dict(uom='Box',conversion_factor=10));material.save()
 order=make('Purchase Order',company=company,supplier=supplier,transaction_date=today,schedule_date=today,currency='VND',items=[dict(item_code=item,qty=2,uom='Box',conversion_factor=10,rate=1000,warehouse=store,schedule_date=today)]);order.submit()
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
 # The print template includes every item, keeps drafts marked, and escapes text.

 for kind,lines in [('issue',[dict(item=item,qty=60,area='A'),dict(item=item,qty=40,area='B')]),('transfer',[dict(item=item,qty=100)])]:
  try:w.create_draft(company,kind,today,lines,source=store,target=other,receiver='QA',notes='Over-stock check')
  except frappe.ValidationError as exc:assert 'thiếu' in str(exc),str(exc)
  else:raise AssertionError('Over-stock outbound draft accepted: '+kind)
 from lotus_farm.www.lotus_stock_print import get_context
 frappe.form_dict=frappe._dict(doctype='Stock Entry',name=received['name'])
 context=frappe._dict();get_context(context)
 html=frappe.render_template('lotus_farm/www/lotus_stock_print.html',context)
 assert received['name'] in html and '100' in html and 'PHIẾU NHẬP KHO' in html,html[:1000]
 assert 'In phiếu / Lưu PDF' in html
 for dt,name in [('Purchase Receipt',first['name']),('Material Request',purchase['name']),('Stock Reconciliation',count['name'])]:
  frappe.form_dict=frappe._dict(doctype=dt,name=name);context=frappe._dict();get_context(context)
  rendered=frappe.render_template('lotus_farm/www/lotus_stock_print.html',context)
  assert name in rendered and 'In phiếu / Lưu PDF' in rendered,(dt,rendered[:500])
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
