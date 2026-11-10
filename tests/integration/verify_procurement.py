"""Native purchase accounting tests. Hard refusal on production; artificial fixtures only.

LOTUS_PROCUREMENT_TEST_ONLY=1 env/bin/python ../apps/lotus_farm/tests/integration/verify_procurement.py
"""
import json
import os
from io import BytesIO
import unittest
from unittest.mock import patch
import uuid
import frappe
from frappe.utils import flt, nowdate, add_days

assert os.environ.get('LOTUS_PROCUREMENT_TEST_ONLY') == '1', 'Use the disposable procurement test stack'
os.chdir('/home/frappe/frappe-bench/sites')
frappe.init(site='procurement.test')
frappe.connect()
assert frappe.local.site == 'procurement.test' and frappe.conf.db_host == 'db'
frappe.set_user('Administrator')
frappe.flags.mute_emails = True
from lotus_farm import procurement as p, purchasing, procurement_import as imports, procurement_reports as reports, purchase_funding as funding
from lotus_farm.finance import setup, api as finance_api, payments, asset_operations
from lotus_farm import warehouse_buying_lite as buying, warehouse_planning as receiving, signing

C = 'Lotus Procurement Test'
DAY = nowdate()


def insert(dt, **values):
    return frappe.get_doc(dict(doctype=dt, **values)).insert(ignore_permissions=True,
        ignore_mandatory=dt=='Department' and values.get('department_name')=='All Departments')


def user(key, roles):
    email = 'purchase-'+key+'@example.invalid'
    if not frappe.db.exists('User', email):
        u = insert('User', email=email, first_name=key, send_welcome_email=0, roles=[dict(role=r) for r in roles])
    if not frappe.db.exists('Employee',{'user_id':email}):
        insert('Employee', first_name=key, gender='Male', date_of_birth='1990-01-01', date_of_joining='2026-01-01', status='Active', company=C, user_id=email)
    return email


def seed():
    if not frappe.get_meta('Lotus Purchase Funding').has_field('cancelled'):
        frappe.reload_doc('lotus_farm','doctype','lotus_purchase_funding')
    from lotus_farm.procurement_setup import install
    install()
    for name,account_type in (('Supplier','Payable'),('Customer','Receivable')):
        if not frappe.db.exists('Party Type',name):
            insert('Party Type',party_type=name,account_type=account_type)
    for dt, key, value in (('Department','department_name','All Departments'),('Item Group','item_group_name','All Item Groups'),('Supplier Group','supplier_group_name','All Supplier Groups')):
        if not frappe.db.exists(dt,value):
            insert(dt,**{key:value,'is_group':1})
    if not frappe.db.exists('Gender','Male'):
        insert('Gender',gender='Male')
    if not frappe.db.exists('Fiscal Year', '2026'):
        insert('Fiscal Year', year='2026', year_start_date='2026-01-01', year_end_date='2026-12-31')
    if not frappe.db.exists('Warehouse Type', 'Transit'):
        insert('Warehouse Type', name='Transit', warehouse_type_name='Transit')
    if not frappe.db.exists('Company', C):
        insert('Company', company_name=C, abbr='PCT', default_currency='VND', country='Vietnam',
            create_chart_of_accounts_based_on='Standard Template', chart_of_accounts='Standard')
    frappe.defaults.set_global_default('company', C)
    cfg = setup.settings()
    cfg.company=C
    cfg.vat_in_cost=0  # These cases explicitly test deductible input VAT, not household-business valuation.
    cfg.flags.ignore_permissions=True
    cfg.save()
    if not cfg.coa_version:
        setup.coa_apply(on_date='2026-09-01')
    finance_api.save_settings(dict(enabled=1, cutover_date='2026-09-01'))
    global ACC, CHIEF, DIR, BUYER, LEADER, WH, MAP
    ACC=user('acc',['Lotus Accountant'])
    CHIEF=user('chief',['Lotus Chief Accountant'])
    DIR=user('director',['Lotus Purchase Approver'])
    BUYER=user('buyer',['Lotus Purchasing Buyer'])
    LEADER=user('leader',['Lotus Team Leader'])
    WH=frappe.db.get_value('Warehouse', {'company':C,'is_group':0,'disabled':0}, 'name')
    MAP=setup.mapping()
    if not frappe.db.exists('Farm',{'farm_code':'PCT-FARM'}):
        insert('Farm',farm_code='PCT-FARM',farm_name='Vườn kiểm thử mua hàng',company=C,area_ha=10,active=1)
    for key, root in (('purchase_funding_liability','Liability'),('purchase_funding_equity','Equity')):
        name=frappe.db.get_value('Account',{'company':C,'account_name':key},'name')
        if not name:
            parent=frappe.db.get_value('Account',{'company':C,'root_type':root,'is_group':1},'name')
            name=insert('Account',account_name=key,parent_account=parent,root_type=root,company=C).name
        frappe.db.set_single_value(setup.SETTINGS,'acct_'+key,name)
    if not frappe.db.exists('Asset Category','Procurement Asset'):
        from lotus_farm.finance.assets import save_category
        by_number={r.account_number:r.name for r in frappe.get_all('Account',filters={'company':C},fields=['name','account_number'])}
        save_category(dict(asset_category_name='Procurement Asset',fixed_asset_account=by_number['211'],
            accumulated_depreciation_account=by_number['2141'],depreciation_expense_account=by_number['6274'],capital_work_in_progress_account=by_number['2411']))
    if not frappe.db.exists('UOM','Nos'):
        insert('UOM',uom_name='Nos',must_be_whole_number=1)
    group=frappe.db.get_value('Item Group',{'is_group':0},'name')
    if not group:
        group=insert('Item Group',item_group_name='Procurement Test',parent_item_group='All Item Groups').name
    for code, kind in (('PCT-M','Material'),('PCT-T','Tool'),('PCT-A','Asset'),('PCT-S','Service')):
        if not frappe.db.exists('Item',code):
            insert('Item',item_code=code,item_name=code,item_group=group,stock_uom='Nos',is_stock_item=int(kind in ('Material','Tool')),
                is_fixed_asset=int(kind=='Asset'),asset_category='Procurement Asset' if kind=='Asset' else None,
                auto_create_assets=0,is_purchase_item=1,valuation_rate=100000,
                item_defaults=[dict(company=C,default_warehouse=WH,expense_account=MAP['admin_expense'])])
    if not frappe.db.exists('Supplier', 'PCT Supplier'):
        sg=frappe.db.get_value('Supplier Group', {'is_group':0}, 'name') or insert('Supplier Group',supplier_group_name='PCT Suppliers',parent_supplier_group='All Supplier Groups').name
        insert('Supplier',supplier_name='PCT Supplier',supplier_group=sg,supplier_type='Company')
    from lotus_farm.finance import assets
    assets.activate(1)
    # Source-only test files and all notifications stay inside this disposable stack.
    frappe.db.commit()


def as_user(who, fn, *args, **kwargs):
    frappe.set_user(who)
    try:
        return fn(*args, **kwargs)
    finally:
        frappe.set_user('Administrator')


def signed(voucher):
    as_user(CHIEF,payments.sign_payment,voucher['doctype'],voucher['voucher'])
    as_user(DIR,payments.sign_payment,voucher['doctype'],voucher['voucher'])
    return frappe.get_doc(voucher['doctype'],voucher['voucher'])


class ProcurementIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed()

    def setUp(self):
        frappe.set_user('Administrator')
        frappe.db.savepoint('purchase_case')
        self.notify=patch.object(signing,'_notify',return_value=None)
        self.notify.start()
        self.tag=uuid.uuid4().hex[:8]
        sg=frappe.db.get_value('Supplier','PCT Supplier','supplier_group')
        self.supplier=insert('Supplier',supplier_name='PCT Case '+self.tag,supplier_group=sg,supplier_type='Company').name

    def tearDown(self):
        frappe.set_user('Administrator')
        frappe.db.rollback(save_point='purchase_case')
        self.notify.stop()

    def order(self, kind='Material', qty=10, rate=100000, vat='KCT', freight=0):
        data=dict(supplier=getattr(self,'supplier','PCT Supplier'),warehouse=WH,expected_date=DAY,mode='Kho tự mua',items=[dict(item={'Material':'PCT-M','Tool':'PCT-T','Asset':'PCT-A','Service':'PCT-S'}[kind],qty=qty,rate=rate,uom='Nos',kind=kind,vat_code=vat,freight=freight)])
        result=as_user(BUYER,buying.save_order,C,data)
        d=frappe.get_doc('Purchase Order',result['name'])
        as_user(BUYER,purchasing.request_approval,d.name,str(d.modified),DIR)
        d.reload()
        as_user(DIR,purchasing.approve_order,d.name,str(d.modified))
        return frappe.get_doc('Purchase Order',d.name)

    def receive(self, order, qty):
        result=as_user('Administrator',receiving.receive_order,order.name,DAY,json.dumps({order.items[0].name:qty}),self.tag+str(qty))
        d=frappe.get_doc('Purchase Receipt',result['name'])
        receiving.receipt_action(d.name,str(d.modified),'submit')
        return frappe.get_doc('Purchase Receipt',d.name)

    def invoice(self, receipt):
        actor=CHIEF if any(frappe.get_cached_value('Item',r.item_code,'is_fixed_asset') for r in receipt.items) else ACC
        result=as_user(actor,p.invoice_receipt,receipt.name,'HD-'+self.tag,DAY,DAY,self.tag)
        return frappe.get_doc('Purchase Invoice',result['invoice'])

    def fund(self, invoice, amount=400000, classification='Reimbursable'):
        f=as_user(ACC,insert,'File',file_name='receipt-'+self.tag+'.txt',is_private=1,content='Evidence '+self.tag)
        employee=frappe.db.get_value('Employee',{'user_id':BUYER},'name')
        data=dict(supplier=invoice.supplier,posting_date=DAY,payer_type='Employee',payer=employee,classification=classification,
            amount=amount,evidence=f.file_url,external_reference='TX-'+self.tag,notes='Test evidence confirmed',
            allocations=[dict(reference_type=invoice.doctype,reference_name=invoice.name,amount=amount)])
        result=as_user(ACC,funding.prepare,C,data,{'CHIEF':CHIEF,'APPROVE':DIR},self.tag)
        return result,data

    def test_01_all_kinds_partial_receipt_and_no_duplicate_stock(self):
        for kind in ('Material','Tool','Service','Asset'):
            with self.subTest(kind=kind):
                self.tag=uuid.uuid4().hex[:8]
                order=self.order(kind,4)
                receipt=self.receive(order,2)
                self.assertEqual(sum(flt(r.qty) for r in receipt.items),2)
                self.assertEqual(len(receipt.items),2 if kind=='Asset' else 1)
                count=frappe.db.count('Stock Ledger Entry',{'voucher_no':receipt.name,'is_cancelled':0})
                self.assertEqual(count,1 if kind in ('Material','Tool') else 0)
                repeat=receiving.receive_order(order.name,DAY,json.dumps({order.items[0].name:2}),self.tag+'2')
                self.assertEqual(repeat['name'],receipt.name)
                self.assertEqual(flt(frappe.db.get_value('Purchase Order Item',order.items[0].name,'received_qty')),2)

    def test_02_mixed_vat_freight_invoice_and_company_payment(self):
        order=self.order(vat='10',freight=50000)
        receipt=self.receive(order,10)
        inv=self.invoice(receipt)
        self.assertEqual(flt(inv.grand_total),1150000)
        v=as_user(ACC,p.supplier_payment,C,'Purchase Invoice',inv.name,300000,'cash',DAY,{'CHIEF':CHIEF,'APPROVE':DIR},self.tag)
        signed(v)
        self.assertEqual(flt(frappe.db.get_value('Purchase Invoice',inv.name,'outstanding_amount')),850000)
        self.assertEqual(flt(frappe.db.sql('select sum(debit-credit) from `tabGL Entry` where voucher_no=%s and is_cancelled=0',v['voucher'])[0][0]),0)

    def test_03_personal_funding_partial_reimbursement_and_equity_guard(self):
        inv=self.invoice(self.receive(self.order(),10))
        result,data=self.fund(inv)
        duplicate=as_user(ACC,funding.prepare,C,data,{'CHIEF':CHIEF,'APPROVE':DIR},self.tag)
        self.assertEqual(duplicate['name'],result['name'])
        signed(result)
        self.assertEqual(flt(frappe.db.get_value('Purchase Invoice',inv.name,'outstanding_amount')),600000)
        v=as_user(ACC,funding.reimburse,result['name'],150000,DAY,'cash',{'CHIEF':CHIEF,'APPROVE':DIR},self.tag+'R')
        with self.assertRaises(frappe.ValidationError):
            as_user(ACC,funding.reimburse,result['name'],300000,DAY,'cash',{'CHIEF':CHIEF,'APPROVE':DIR},self.tag+'over')
        signed(v)
        balance=funding.reimbursement_balance(frappe.get_doc(funding.DT,result['name']))
        self.assertEqual(balance['remaining'],250000)
        report=reports.report(C,DAY[:7],DAY,supplier=self.supplier)
        self.assertEqual(report['totals']['supplier_paid'],400000)
        self.assertEqual(report['totals']['company_cash'],150000)
        self.assertEqual(report['totals']['outstanding'],600000)
        self.assertEqual(report['totals']['funding_outstanding'],250000)
        self.tag=uuid.uuid4().hex[:8]
        equity,_=self.fund(inv,200000,'Equity')
        signed(equity)
        with self.assertRaises(frappe.ValidationError):
            as_user(ACC,funding.reimburse,equity['name'],100000,DAY,'cash',{'CHIEF':CHIEF,'APPROVE':DIR},self.tag+'E')

    def test_04_advance_reconciles_to_invoice(self):
        order=self.order('Service')
        advance=as_user(ACC,p.supplier_payment,C,'Purchase Order',order.name,300000,'cash',DAY,{'CHIEF':CHIEF,'APPROVE':DIR},self.tag+'A')
        signed(advance)
        inv=self.invoice(self.receive(order,10))
        self.assertEqual(flt(inv.outstanding_amount),700000)
        self.assertEqual(frappe.db.count('Stock Ledger Entry',{'voucher_no':inv.name}),0)

    def test_05_stale_signatures_and_native_funding_tamper_refused(self):
        inv=self.invoice(self.receive(self.order(),10))
        result,_=self.fund(inv)
        j=frappe.get_doc('Journal Entry',result['voucher'])
        j.accounts[0].reference_name='forged'
        with self.assertRaises(frappe.ValidationError):
            j.submit()
        f=frappe.get_doc(funding.DT,result['name'])
        f.amount=1
        with self.assertRaises(frappe.ValidationError):
            f.save()
        with self.assertRaises(frappe.PermissionError):
            as_user(LEADER,p.supplier_payment,C,'Purchase Invoice',inv.name,1,'cash',DAY,{},'unauthorized')

    def test_06_import_months_drafts_and_stale_preview(self):
        from openpyxl import Workbook
        book=Workbook();book.active.title='Nguyên liệu';book.active.append(['type','item','qty','uom','rate','supplier','month']);book.active.append(['Need','PCT-M',4,'Nos',100000,'','2026-10']);book.active.append(['Need','PCT-T',2,'Nos',200000,'','2026-11'])
        out=BytesIO();book.save(out)
        f=insert('File',file_name='source.xlsx',is_private=1,content=out.getvalue())
        preview=imports.preview(C,f.file_url)
        mappings={r['key']:{'warehouse':WH} for r in preview['rows']}
        reviewed=imports.preview(C,f.file_url,mappings)
        self.assertTrue(reviewed['valid'],reviewed)
        result=imports.commit(C,f.file_url,mappings,reviewed['fingerprint'],self.tag)
        self.assertEqual({d['month'] for d in result['documents']},{'2026-10','2026-11'})
        self.assertTrue(all(d['docstatus']==0 for d in result['documents']))
        self.assertEqual(imports.commit(C,f.file_url,mappings,reviewed['fingerprint'],self.tag)['name'],result['name'])
        with self.assertRaises(frappe.ValidationError):
            imports.commit(C,f.file_url,mappings,'stale',self.tag+'bad')

    def test_07_quote_missing_price_not_paid_and_split_order(self):
        data=dict(supplier='PCT Supplier',warehouse=WH,expected_date=DAY,valid_till=add_days(DAY,7),items=[dict(item='PCT-M',qty=10,rate=0,uom='Nos')])
        result=as_user(BUYER,p.save_quotation,C,data,self.tag)
        row=p.quotations(C)[0]
        self.assertIsNone(row['gross'])
        self.assertEqual(frappe.db.count('Payment Entry Reference',{'reference_name':result['name']}),0)
        q=frappe.get_doc('Supplier Quotation',result['name']);q.items[0].rate=100000;q.save();q.submit()
        row=p.quotations(C)[0]
        order=as_user(BUYER,p.select_quotes,C,[dict(quotation=q.name,line=row['name'],modified=str(q.modified),qty=4,reason='Giao đúng hạn')],self.tag+'Q')
        d=frappe.get_doc('Purchase Order',order['orders'][0])
        self.assertEqual(d.docstatus,0);self.assertEqual(d.items[0].supplier_quotation,q.name)

    def test_08_returns_and_cancel_restore_canonical_quantity(self):
        order=self.order()
        receipt=self.receive(order,10)
        result=p.return_receipt(receipt.name,DAY,{receipt.items[0].name:3},self.tag+'return')
        self.assertEqual((result['docstatus'],result['needs_credit_note'],result['return_against']),(0,False,receipt.name))
        ret=frappe.get_doc('Purchase Receipt',result['name'])
        receiving.receipt_action(ret.name,str(ret.modified),'submit')
        self.assertEqual(flt(frappe.db.get_value('Purchase Order Item',order.items[0].name,'received_qty')),7)
        ret.reload()
        with self.assertRaises(frappe.ValidationError):  # spec 003, FR-045: a cancelled receipt says why
            receiving.receipt_action(ret.name,str(ret.modified),'cancel')
        receiving.receipt_action(ret.name,str(ret.modified),'cancel','Trả nhầm số lượng')
        self.assertEqual(frappe.db.get_value('Purchase Receipt',ret.name,'lotus_cancel_reason'),'Trả nhầm số lượng')
        self.assertEqual(flt(frappe.db.get_value('Purchase Order Item',order.items[0].name,'received_qty')),10)
        receipt.reload()
        receiving.receipt_action(receipt.name,str(receipt.modified),'cancel','Nhập nhầm đơn')
        self.assertEqual(receiving.purchase_receipt(receipt.name)['state'],'Đã hủy')
        self.assertEqual(flt(frappe.db.get_value('Purchase Order Item',order.items[0].name,'received_qty')),0)

    def test_09_asof_debt_does_not_use_current_invoice_balance(self):
        inv=self.invoice(self.receive(self.order(),10))
        tomorrow=add_days(DAY,1)
        result=as_user(ACC,p.supplier_payment,C,'Purchase Invoice',inv.name,300000,'cash',tomorrow,{'CHIEF':CHIEF,'APPROVE':DIR},self.tag+'future')
        signed(result)
        self.assertEqual(flt(frappe.db.get_value('Purchase Invoice',inv.name,'outstanding_amount')),700000)
        self.assertEqual(reports.report(C,DAY[:7],DAY,supplier=self.supplier)['totals']['outstanding'],1000000)
        self.assertEqual(reports.report(C,tomorrow[:7],tomorrow,supplier=self.supplier)['totals']['outstanding'],700000)

    def test_10_asset_invoice_rows_link_each_physical_piece(self):
        order=self.order('Asset',2,15000000)
        receipt=self.receive(order,2)
        inv=self.invoice(receipt)
        self.assertEqual(len(inv.items),2)
        self.assertEqual({r.pr_detail for r in inv.items},{r.name for r in receipt.items})
        self.assertEqual(len({r.name for r in inv.items}),2)
        self.assertTrue(all(flt(r.qty)==1 for r in inv.items))
        self.assertEqual(frappe.db.count('Asset',{'purchase_invoice':inv.name}),0)
        from lotus_farm.finance import assets
        location=assets.save_location('Vị trí thử '+self.tag)['name']
        values=dict(code='PCT-ASSET-'+self.tag,asset_name='Tài sản thử '+self.tag,asset_category='Procurement Asset',
            location=location,existing=False,purchase_date=DAY,available_for_use_date=DAY,posting_date=DAY,amount=15000000,
            months=24,opening_depreciation=0,booked_months=0,salvage_value=0,item_code='PCT-A',purchase_invoice=inv.name,
            purchase_row=inv.items[0].name)
        pending=as_user(ACC,assets.save_asset,values)
        preview=assets.operation_preview(pending['name'])
        self.assertFalse(preview['errors'],preview)
        as_user(CHIEF,assets.operation_post,pending['name'],preview['fingerprint'])
        self.assertEqual(frappe.db.count('Asset',{'purchase_invoice':inv.name,'docstatus':1}),1)
        duplicate=as_user(ACC,assets.save_asset,dict(values,code='PCT-DUP-'+self.tag))
        self.assertTrue(assets.operation_preview(duplicate['name'])['errors'])

    def test_11_personal_advance_on_order_reconciles_when_billed(self):
        order=self.order('Service')
        result,_=self.fund(order,200000)
        signed(result)
        inv=self.invoice(self.receive(order,10))
        self.assertEqual(flt(inv.outstanding_amount),800000)

    def test_12_source_excel_pack_units_and_months(self):
        from openpyxl import Workbook
        book=Workbook();sheet=book.active;sheet.title='Phân bón'
        sheet.append(['DANH MỤC PHÂN BÓN CẦN MUA THÁNG 10'])
        sheet.append(['Stt','Tên phân bón','Tên thương mại (SP giá tốt nhất)','ĐVT','Quy cách (ĐVT/bao-chai)','SL cần mua (bao/chai)','Giá tốt nhất (đ/ĐVT)'])
        sheet.append([1,'Vi lượng','HP','lít',20,33,82000])
        second=book.create_sheet('Vật tư');second.append(['DANH MỤC VẬT TƯ CẦN MUA THÁNG 11']);second.append(['Stt','Tên vật tư','Tên thương mại (SP giá tốt nhất)','ĐVT','Quy cách (ĐVT/bao-chai)','SL cần mua (bao/chai)','Giá tốt nhất (đ/ĐVT)']);second.append([1,'Bao cám','-','cái',1,20073,0])
        out=BytesIO();book.save(out)
        rows=imports.workbook_rows(out.getvalue())
        self.assertEqual(rows[0]['qty'],660)
        self.assertEqual(rows[0]['rate'],82000)
        self.assertEqual(rows[0]['month'],'2026-10')
        self.assertEqual(rows[1]['month'],'2026-11')
        self.assertEqual(rows[1]['item_label'],'Bao cám')

    def test_13_export_contains_every_filtered_event(self):
        inv=self.invoice(self.receive(self.order(),10))
        data=reports.report(C,DAY[:7],DAY,kind='Material')
        reports.export(C,DAY[:7],DAY,kind='Material')
        from openpyxl import load_workbook
        book=load_workbook(BytesIO(frappe.local.response.filecontent),data_only=True)
        self.assertEqual(book['Toàn bộ chi tiết'].max_row,len(data['rows'])+1)
        self.assertTrue(any(r['name']==inv.name and r['stage']=='billed' for r in data['rows']))
        self.assertEqual(reports.report(C,DAY[:7],DAY,kind='Service')['totals']['billed'],0)

    def test_14_buyer_catalogue_and_legacy_header_vat_invoice(self):
        with patch('frappe.sessions.get_csrf_token',return_value='test-csrf'):
            info=as_user(BUYER,p.bootstrap,C)
        self.assertFalse(info['can_finance'])
        self.assertTrue(any(r['name']=='PCT-S' for r in info['items']))
        result=as_user(ACC,payments.make_service_invoice,self.supplier,'LEGACY-'+self.tag,DAY,
            [dict(description='Legacy service without an Item',amount=250000,cost='admin')],vat_code='10')
        self.assertEqual(flt(frappe.db.get_value('Purchase Invoice',result['invoice'],'grand_total')),275000)
        self.assertEqual(reports.report(C,DAY[:7],DAY,supplier=self.supplier,kind='Service')['totals']['billed'],275000)

    def test_15_mixed_line_vat_and_service_acceptance(self):
        result=as_user(BUYER,buying.save_order,C,dict(supplier=self.supplier,warehouse=WH,expected_date=DAY,
            items=[dict(item=code,qty=1,uom='Nos',rate=rate,vat_code=vat,freight=freight) for code,rate,vat,freight in
                [('PCT-M',100000,'10',5000),('PCT-T',50000,'5',0),('PCT-S',20000,'KCT',0)]]))
        order=frappe.get_doc('Purchase Order',result['name'])
        as_user(BUYER,purchasing.request_approval,order.name,str(order.modified),DIR)
        order.reload();as_user(DIR,purchasing.approve_order,order.name,str(order.modified))
        result=receiving.receive_order(order.name,DAY,json.dumps({r.name:1 for r in order.items}),self.tag+'mixed')
        receipt=frappe.get_doc('Purchase Receipt',result['name'])
        receiving.receipt_action(receipt.name,str(receipt.modified),'submit')
        inv=self.invoice(receipt)
        self.assertEqual(flt(inv.grand_total),187500)
        self.assertEqual(frappe.db.count('Stock Ledger Entry',{'voucher_no':receipt.name,'is_cancelled':0}),2)

    def test_17_receipt_landed_costs_enter_stock_once(self):
        order=self.order('Material',4,100000,vat='10',freight=5000)
        expense=frappe.db.get_value('Account',
            {'company':C,'root_type':'Expense','is_group':0,'disabled':0},'name')
        self.assertTrue(expense)
        extra=[dict(description='Bốc xếp tại kho',amount=20000,expense_account=expense)]
        args=(order.name,DAY,json.dumps({order.items[0].name:2}),self.tag+'costs',extra)
        result=receiving.receive_order(*args)
        duplicate=receiving.receive_order(*args)
        self.assertEqual(result['name'],duplicate['name'])
        receipt=frappe.get_doc('Purchase Receipt',result['name'])
        self.assertEqual(receipt.docstatus,0)
        self.assertEqual(frappe.db.count('Stock Ledger Entry',{'voucher_no':receipt.name,'is_cancelled':0}),0)
        data=receiving.purchase_receipt(receipt.name)
        self.assertEqual(round(data['goods_total']),200000)
        self.assertEqual(round(data['valuation_charges']),20000)
        self.assertEqual(round(data['incoming_total']),220000)
        self.assertEqual(len(data['added_costs']),1)
        self.assertEqual(len([t for t in receipt.taxes if t.category=='Valuation']),1)
        self.assertTrue(any(t.category=='Total' for t in receipt.taxes))
        with self.assertRaises(frappe.ValidationError):
            receiving.receive_order(order.name,DAY,json.dumps({order.items[0].name:2}),
                self.tag+'costs',[dict(extra[0],amount=30000)])
        receiving.receipt_action(receipt.name,str(receipt.modified),'submit')
        receipt.reload()
        self.assertEqual(frappe.db.count('Stock Ledger Entry',{'voucher_no':receipt.name,'is_cancelled':0}),1)
        self.assertAlmostEqual(flt(receipt.items[0].valuation_rate),110000,delta=1)

    def test_18_return_posts_at_once_and_asks_for_a_credit_note_when_billed(self):
        order=self.order()
        receipt=self.receive(order,10)
        line=receipt.items[0].name
        first=p.return_receipt(receipt.name,DAY,{line:2},self.tag+'r1',1,'Hàng móp')
        self.assertEqual((first['docstatus'],first['needs_credit_note'],first['return_against']),(1,False,receipt.name))
        self.assertEqual(flt(frappe.db.get_value('Purchase Order Item',order.items[0].name,'received_qty')),8)
        again=p.return_receipt(receipt.name,DAY,{line:2},self.tag+'r1',1,'Hàng móp')
        self.assertEqual(again['name'],first['name'],'the same request never returns goods twice')
        detail=p.receipt(first['name'])
        self.assertEqual((detail['state'],detail['is_return'],detail['return_against'],detail['notes']),('Đã nhập kho',1,receipt.name,'Lý do trả hàng: Hàng móp'))
        self.invoice(receipt)
        second=p.return_receipt(receipt.name,DAY,{line:1},self.tag+'r2',1,'Sai quy cách')
        self.assertEqual((second['docstatus'],second['needs_credit_note']),(1,True),'goods already invoiced: an adjustment invoice must follow')
        listed={r['name']:r for r in p.receipts(C)}
        self.assertEqual((listed[receipt.name]['status'],listed[receipt.name]['kind'],listed[second['name']]['kind']),('Đã nhập kho','Nhập theo đơn','Trả hàng'))
        self.assertIn(listed[receipt.name]['billing'],('Đã có hóa đơn','Có hóa đơn một phần'))

    def test_19_draft_receipt_is_removed_by_its_preparer_or_a_receiver(self):
        order=self.order()
        result=receiving.receive_order(order.name,DAY,json.dumps({order.items[0].name:2}),self.tag+'draft')
        self.assertEqual((result['docstatus'],result['state'],result['signed_copy']),(0,'Nháp',None))
        self.assertEqual(result['remaining'][0]['remaining_qty'],8,'a draft holds its quantity')
        with self.assertRaises(frappe.PermissionError):  # the buyer reads receipts but does not remove them
            as_user(BUYER,receiving.receipt_action,result['name'],result['modified'],'delete')
        receiving.receipt_action(result['name'],result['modified'],'delete')
        self.assertFalse(frappe.db.exists('Purchase Receipt',result['name']))
        self.assertEqual(receiving.purchase_order(order.name)['items'][0]['remaining_qty'],10)
        over=None
        try:
            receiving.receive_order(order.name,DAY,json.dumps({order.items[0].name:11}),self.tag+'over')
        except frappe.ValidationError as exc:
            over=str(exc)
        self.assertIn('còn nhận được 10',over or '')

    # ---- Spec 003 · US5: one core for supplier invoices (finance.supplier_invoice) ----
    def household(self):
        """Hộ kinh doanh for this case only: VAT goes into cost, never to 1331."""
        def switch(value):
            frappe.db.set_single_value(setup.SETTINGS, 'vat_in_cost', value)
            frappe.clear_document_cache(setup.SETTINGS, setup.SETTINGS)
        switch(1)
        self.addCleanup(switch, 0)

    def ledger(self, account, vouchers):
        return flt(frappe.db.sql('select sum(debit-credit) from `tabGL Entry` where account=%s and voucher_no in %s and is_cancelled=0',
                                 (account, tuple(vouchers)))[0][0])

    def refused(self, fn, *args, **kwargs):
        frappe.db.savepoint('refused_call')
        with self.assertRaises(frappe.ValidationError) as caught:
            fn(*args, **kwargs)
        frappe.db.rollback(save_point='refused_call')
        return str(caught.exception)

    def test_20_one_invoice_for_two_receipts_household_vat_into_cost(self):
        from lotus_farm.finance import supplier_invoice as si
        self.household()
        a = self.receive(self.order(qty=10, rate=100000, vat='5', freight=50000), 10)
        first = self.tag
        self.tag = uuid.uuid4().hex[:8]
        b = self.receive(self.order(qty=4, rate=25000, vat='8'), 4)
        src = as_user(ACC, si.source, [a.name, b.name])
        self.assertEqual([(l['qty'], l['vat_code'], l['fixed']) for l in src['lines']], [(10, '5', False), (4, '8', False)])
        self.assertTrue(src['vat_in_cost'])
        waiting = {r['name']: r for r in as_user(ACC, si.queue, self.supplier)['rows']}
        self.assertEqual((waiting[a.name]['mua_nhanh'], waiting[a.name]['source_type']), (False, 'Nhận theo đơn'))
        args = dict(receipts=[a.name, b.name], bill_no='HD-' + first, series='1C26TAA', tax_code='CQT-1', bill_date=DAY, printed_total=1208000)
        result = as_user(ACC, si.create, client_key=first + 'inv', **args)
        self.assertEqual((result['amount'], result['rounding_adjustment']), (1208000, 0))
        self.assertEqual(as_user(ACC, si.create, client_key=first + 'inv', **args)['invoice'], result['invoice'], 'the same request is not posted twice')
        vouchers = [a.name, b.name, result['invoice']]
        self.assertEqual(frappe.db.count('GL Entry', {'voucher_no': result['invoice'], 'account': MAP['input_vat'], 'is_cancelled': 0}), 0, 'never 1331')
        self.assertAlmostEqual(self.ledger(setup.valuation_tax_account(C), vouchers), 0, delta=1, msg='33881 returns to zero once billed')
        # The same supplier invoice cannot come in again through any path.
        self.assertIn('đã được nhập', self.refused(as_user, ACC, si.create, client_key=first + 'again', **args))
        self.assertIn('đã được nhập', self.refused(as_user, ACC, payments.make_service_invoice, self.supplier, 'HD-' + first, DAY,
                                                    [dict(description='Thuê xe', amount=100000, cost='admin')]))
        info = as_user(ACC, si.detail, result['invoice'])
        self.assertEqual((info['series'], info['tax_code'], info['printed_total'], info['status'], sorted(info['receipts'])),
                         ('1C26TAA', 'CQT-1', 1208000, 'Chưa trả', sorted([a.name, b.name])))
        self.assertEqual(info['vat'], 58000)
        from lotus_farm import print_kit
        from lotus_farm.www import lotus_invoice_print
        page = as_user(ACC, lambda: str(print_kit.render('invoice.html', lotus_invoice_print.build(result['invoice']))))
        for text in ('BẢNG KÊ HÓA ĐƠN MUA HÀNG', '1C26TAA', 'Tổng thanh toán', 'Chưa có file gốc'):
            self.assertIn(text, page)
        listed = {r['name']: r for r in as_user(ACC, si.invoices, self.supplier)['rows']}
        self.assertEqual((listed[result['invoice']]['status'], listed[result['invoice']]['outstanding_amount']), ('Chưa trả', 1208000))

    def test_21_price_variance_needs_a_reason_and_printed_total_names_the_suspect_line(self):
        from lotus_farm.finance import supplier_invoice as si
        receipt = self.receive(self.order(qty=5, rate=100000, vat='10'), 5)
        line = receipt.items[0].name
        base = dict(receipts=[receipt.name], bill_no='HD-' + self.tag, bill_date=DAY)
        self.assertIn('Ghi lý do chênh lệch', self.refused(as_user, ACC, si.create, client_key=self.tag + 'v1',
                                                          lines=[dict(source_item=line, qty=5, rate=110000)], **base))
        message = self.refused(as_user, ACC, si.create, client_key=self.tag + 'v2', printed_total=540000, **base)
        self.assertIn('Dòng nghi sai', message)
        self.assertIn('thuế suất có thể là 8%', message)
        result = as_user(ACC, si.create, client_key=self.tag + 'v3', printed_total=605001, printed_vat=55000,
                         lines=[dict(source_item=line, qty=5, rate=110000, variance_reason='NCC tăng giá theo thông báo ngày giao')], **base)
        self.assertEqual((result['amount'], result['rounding_adjustment']), (605001, 1))
        self.assertTrue(result['warnings'])
        invoice = frappe.get_doc('Purchase Invoice', result['invoice'])
        self.assertEqual((flt(invoice.items[0].rate), invoice.items[0].get('lotus_variance_reason')), (110000, 'NCC tăng giá theo thông báo ngày giao'))
        self.assertEqual(as_user(ACC, si.detail, invoice.name)['rounding_adjustment'], 1)
        # FR-051: cost follows the invoice. ERPNext revalues the receipt at the invoice price in its repost job (run by the
        # scheduler on a live site, by hand here); after it nothing is left on the goods-received-not-invoiced account.
        from erpnext.stock.doctype.repost_item_valuation.repost_item_valuation import repost_entries
        previous = (frappe.flags.in_test, getattr(frappe, 'in_test', False))
        frappe.flags.in_test = frappe.in_test = True  # the repost must not commit inside this rolled-back case
        try:
            repost_entries()
        finally:
            frappe.flags.in_test, frappe.in_test = previous
        self.assertAlmostEqual(self.ledger(MAP['received_not_billed'], [receipt.name, invoice.name]), 0, delta=1)
        self.assertAlmostEqual(flt(frappe.db.get_value('Purchase Receipt Item', line, 'valuation_rate')), 110000, delta=1, msg='stock is valued at the invoice price')
        # One receipt, several invoices: the second invoice takes what is left.
        partial = self.receive(self.order(qty=6, rate=100000), 6)
        first = as_user(ACC, si.create, receipts=[partial.name], bill_no='P1-' + self.tag, bill_date=DAY, client_key=self.tag + 'p1',
                        lines=[dict(source_item=partial.items[0].name, qty=2)])
        self.assertEqual(first['amount'], 200000)
        self.assertEqual(as_user(ACC, si.source, [partial.name])['lines'][0]['qty'], 4)
        self.assertIn('vượt phần chưa lập hóa đơn', self.refused(as_user, ACC, si.create, receipts=[partial.name], bill_no='P2-' + self.tag, bill_date=DAY,
                                                              client_key=self.tag + 'p2', lines=[dict(source_item=partial.items[0].name, qty=5)]))

    def test_22_cancel_needs_a_reason_and_is_refused_once_paid(self):
        from lotus_farm import warehouse
        from lotus_farm.finance import supplier_invoice as si
        quick = warehouse.create_draft(C, 'receipt', DAY, [dict(item='PCT-M', qty=2, rate=100000)], target=WH, receipt_reason='Purchase',
                                       supplier=self.supplier, post=1, client_event_id=self.tag + 'quick')
        waiting = {r['name']: r for r in as_user(ACC, si.queue, self.supplier)['rows']}
        self.assertEqual((waiting[quick['name']]['mua_nhanh'], waiting[quick['name']]['source_type'], waiting[quick['name']]['amount']), (True, 'Mua nhanh', 200000))
        self.assertTrue(as_user(ACC, si.source, [quick['name']])['lines'][0]['fixed'])
        made = as_user(ACC, si.create, receipts=[quick['name']], bill_no='MN-' + self.tag, bill_date=DAY, client_key=self.tag + 'mn')
        self.assertEqual(frappe.db.get_value('Stock Entry', quick['name'], 'lotus_purchase_invoice'), made['invoice'])
        self.assertAlmostEqual(self.ledger(MAP['received_not_billed'], [quick['name'], made['invoice']]), 0, delta=1, msg='3388 is cleared by the invoice')
        self.assertIn('lý do', self.refused(as_user, ACC, si.cancel, made['invoice'], ' '))
        gone = as_user(ACC, si.cancel, made['invoice'], 'Nhập nhầm nhà cung cấp')
        self.assertEqual((gone['state'], gone['released']), ('Đã hủy', [quick['name']]))
        self.assertFalse(frappe.db.get_value('Stock Entry', quick['name'], 'lotus_purchase_invoice'))
        self.assertEqual(as_user(ACC, si.detail, made['invoice'])['cancel_reason'], 'Nhập nhầm nhà cung cấp')
        self.assertIn(quick['name'], [r['name'] for r in as_user(ACC, si.queue, self.supplier)['rows']], 'the receipt waits for an invoice again')
        # An invoice with a payment is not cancelled, from Lotus or from Desk.
        paid = self.invoice(self.receive(self.order(qty=3), 3))
        voucher = as_user(ACC, p.supplier_payment, C, 'Purchase Invoice', paid.name, 100000, 'cash', DAY, {'CHIEF': CHIEF, 'APPROVE': DIR}, self.tag + 'pay')
        self.assertIn('Phiếu chi đang ký', self.refused(as_user, ACC, si.cancel, paid.name, 'Thử hủy khi đang chi'))
        signed(voucher)
        self.assertIn('Đảo phiếu chi trước', self.refused(as_user, ACC, si.cancel, paid.name, 'Thử hủy khi đã chi'))
        self.refused(lambda: frappe.get_doc('Purchase Invoice', paid.name).cancel())
        info = as_user(ACC, si.detail, paid.name)
        self.assertEqual((info['can_cancel'], info['status'], info['settlements'][0]['name']), (False, 'Trả một phần', voucher['voucher']))

    def test_23_finance_screens_use_the_same_core_and_never_post_household_vat_to_1331(self):
        self.household()
        receipt = self.receive(self.order(qty=2, rate=100000, vat='8'), 2)
        goods = as_user(ACC, payments.make_goods_invoice, [receipt.name], 'TC-' + self.tag, DAY)
        service = as_user(ACC, payments.make_service_invoice, self.supplier, 'DV-' + self.tag, DAY,
                          [dict(description='Thuê xe chở phân', amount=500000, cost='admin')], None, None, '10')
        self.assertEqual((goods['amount'], service['amount']), (216000, 550000))
        for invoice in (goods['invoice'], service['invoice']):
            self.assertEqual(frappe.db.count('GL Entry', {'voucher_no': invoice, 'account': MAP['input_vat'], 'is_cancelled': 0}), 0, invoice)
        self.assertAlmostEqual(self.ledger(MAP['admin_expense'], [service['invoice']]), 550000, delta=1, msg='service VAT joins its own expense')
        self.assertAlmostEqual(self.ledger(setup.valuation_tax_account(C), [receipt.name, goods['invoice']]), 0, delta=1)

    def test_16_cancel_unposted_funding_keeps_evidence_and_releases_reservation(self):
        inv=self.invoice(self.receive(self.order(),10))
        result,_=self.fund(inv,400000)
        before=funding._remaining_source('Purchase Invoice',inv.name)
        self.assertEqual(before,600000)
        as_user(ACC,payments.cancel_draft,'Journal Entry',result['voucher'],'Phân loại lại khoản chi hộ')
        d=frappe.get_doc(funding.DT,result['name'])
        self.assertTrue(d.cancelled)
        self.assertTrue(frappe.db.exists('File',{'file_url':d.evidence,'attached_to_name':d.name,'is_private':1}))
        self.assertFalse(frappe.db.exists('Journal Entry',result['voucher']))
        self.assertEqual(funding._remaining_source('Purchase Invoice',inv.name),1000000)


if __name__ == '__main__':
    try:
        unittest.main(verbosity=2)
    finally:
        frappe.db.rollback()
        frappe.destroy()
