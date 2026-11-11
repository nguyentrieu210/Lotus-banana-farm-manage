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

    def order(self, kind='Material', qty=10, rate=100000, vat='KCT', freight=0, lines=None):
        """lines: several order lines, each dict(kind, qty, rate, vat, freight)."""
        lines=lines or [dict(kind=kind,qty=qty,rate=rate,vat=vat,freight=freight)]
        data=dict(supplier=getattr(self,'supplier','PCT Supplier'),warehouse=WH,expected_date=DAY,mode='Kho tự mua',
            items=[dict(item={'Material':'PCT-M','Tool':'PCT-T','Asset':'PCT-A','Service':'PCT-S'}[l['kind']],qty=l['qty'],rate=l['rate'],uom='Nos',
                        kind=l['kind'],vat_code=l.get('vat','KCT'),freight=l.get('freight',0)) for l in lines])
        result=as_user(BUYER,buying.save_order,C,data)
        d=frappe.get_doc('Purchase Order',result['name'])
        as_user(BUYER,purchasing.request_approval,d.name,str(d.modified),DIR)
        d.reload()
        as_user(DIR,purchasing.approve_order,d.name,str(d.modified))
        return frappe.get_doc('Purchase Order',d.name)

    def receive(self, order, qty, day=DAY):
        # test_01 repeats the request with the key tag + qty: a receipt of today keeps exactly that key.
        result=as_user('Administrator',receiving.receive_order,order.name,day,json.dumps({order.items[0].name:qty}),self.tag+str(qty)+('' if day==DAY else str(day)))
        d=frappe.get_doc('Purchase Receipt',result['name'])
        receiving.receipt_action(d.name,str(d.modified),'submit')
        return frappe.get_doc('Purchase Receipt',d.name)

    def receive_all(self, order, day=DAY):
        result=as_user('Administrator',receiving.receive_order,order.name,day,json.dumps({r.name:flt(r.qty) for r in order.items}),self.tag+'all'+str(day))
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

    def ledger(self, account, vouchers, as_of=None):
        return flt(frappe.db.sql('select sum(debit-credit) from `tabGL Entry` where account=%s and voucher_no in %s and is_cancelled=0'
                                 + (' and posting_date<=%s' if as_of else ''), (account, tuple(vouchers), *([as_of] if as_of else [])))[0][0])

    def clearing(self, vouchers, as_of=None):
        """What 3388 + 33881 hold for these vouchers (credit as a positive number)."""
        return -(self.ledger(MAP['received_not_billed'], vouchers, as_of) + self.ledger(setup.valuation_tax_account(C), vouchers, as_of))

    def frozen(self, day):
        frappe.db.set_value('Company', C, 'accounts_frozen_till_date', day)
        frappe.clear_document_cache('Company', C)
        frappe.clear_cache(doctype='Company')
        self.addCleanup(lambda: (frappe.clear_document_cache('Company', C), frappe.clear_cache(doctype='Company')))

    def repost(self):
        """Run ERPNext's queued valuation reposts (the scheduler does it on a live site) without committing this case."""
        from erpnext.stock.doctype.repost_item_valuation.repost_item_valuation import repost_entries
        previous = (frappe.flags.in_test, getattr(frappe, 'in_test', False))
        frappe.flags.in_test = frappe.in_test = True
        try:
            repost_entries()
        finally:
            frappe.flags.in_test, frappe.in_test = previous

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
        # A read carries its arguments in the URL: the list comes as JSON text or as "A,B" (live-site copy, 10/11/2026).
        for sent in (frappe.as_json([a.name, b.name]), a.name + ',' + b.name):
            self.assertEqual(len(as_user(ACC, si.source, sent)['lines']), 2, sent)
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

    def test_24_cost_follows_each_invoice_and_both_clearing_accounts_return_to_zero(self):
        """FR-051, R16 (bản sao site thật 10/11/2026). Hộ kinh doanh; 2 trên 10 đã trả trước khi có hóa đơn; hóa đơn tăng giá
        một dòng, giảm giá và đổi thuế suất dòng kia, kèm dòng dịch vụ. Hóa đơn không tính lại hàng đã trả; phần chênh của
        đúng số lượng trên hóa đơn vào giá vốn; 3388 và 33881 về 0; phiếu nhận có hóa đơn đủ theo số lượng; hủy hóa đơn
        thì sổ trở lại như trước."""
        from lotus_farm import procurement_queries as queries
        from lotus_farm.finance import supplier_invoice as si
        self.household()
        a = self.receive(self.order(qty=10, rate=100000, vat='5', freight=50000), 10)
        first = self.tag
        self.tag = uuid.uuid4().hex[:8]
        b = self.receive(self.order(qty=4, rate=25000, vat='8'), 4)
        back = p.return_receipt(a.name, DAY, {a.items[0].name: 2}, first + 'ret', 1, 'Hàng móp')
        self.assertEqual(back['docstatus'], 1)
        self.assertEqual([l['qty'] for l in as_user(ACC, si.source, [a.name, b.name])['lines']], [8, 4],
                         'goods returned before the invoice are not invoiced again')
        clearing, grni = setup.valuation_tax_account(C), MAP['received_not_billed']
        vouchers = [a.name, b.name, back['name']]
        books = lambda: -(self.ledger(grni, vouchers) + self.ledger(clearing, vouchers))
        waiting = lambda: queries.unbilled(C, DAY, self.supplier)['by_supplier'].get(self.supplier, 0)
        self.assertAlmostEqual(waiting(), 8 * 110000 + 4 * 27000, delta=1, msg='net + VAT + freight of what waits for an invoice')
        self.assertAlmostEqual(books(), waiting(), delta=1, msg='3388 + 33881 hold what waits for an invoice')
        lines = [dict(source_item=a.items[0].name, qty=8, rate=110000, vat_code='5', variance_reason='NCC tăng giá theo thông báo'),
                 dict(source_item=b.items[0].name, qty=4, rate=24000, vat_code='10', variance_reason='Chiết khấu cuối tháng')]
        result = as_user(ACC, si.create, receipts=[a.name, b.name], lines=lines, bill_no='CL-' + first, bill_date=DAY, client_key=first + 'cl',
                         service_lines=[dict(description='Bốc xếp', amount=200000, vat_code='8', cost='admin')])
        invoice = result['invoice']
        self.assertEqual(result['amount'], 880000 + 44000 + 40000 + 96000 + 9600 + 200000 + 16000)
        # The vouchers post on the receipts; the VAT transfer is its own journal entry, dated with the invoice.
        vouchers += [invoice] + [r['name'] for r in as_user(ACC, si.detail, invoice)['cost_adjustments'] if r['doctype'] == 'Journal Entry']
        self.repost()
        self.assertAlmostEqual(self.ledger(grni, vouchers), 0, delta=1, msg='3388')
        self.assertAlmostEqual(self.ledger(clearing, vouchers), 0, delta=1, msg='33881')
        self.assertEqual(frappe.db.count('GL Entry', {'voucher_no': invoice, 'account': MAP['input_vat'], 'is_cancelled': 0}), 0, 'never 1331')
        self.assertAlmostEqual(self.ledger(MAP['admin_expense'], [invoice]), 216000, delta=1, msg='service VAT joins its own expense')
        self.assertAlmostEqual(waiting(), 0, delta=1)
        # The kept 8 carry what the invoice says: 110.000 + 5 % VAT + 5.000 freight each. The 2 returned leave at what they
        # cost, so nothing lands on an expense account (the review of 11/11/2026 found 16.800 there).
        self.assertAlmostEqual(flt(frappe.db.get_value('Purchase Receipt Item', a.items[0].name, 'valuation_rate')), 120500, delta=1)
        kept = flt(frappe.db.sql("select sum(stock_value_difference) from `tabStock Ledger Entry` where voucher_no in %s and is_cancelled=0",
                                 ((a.name, back['name']),))[0][0])
        self.assertAlmostEqual(kept, 8 * 120500, delta=2)
        for account in {MAP['admin_expense'], frappe.get_cached_value('Company', C, 'default_expense_account')}:
            self.assertAlmostEqual(self.ledger(account, [back['name']]), 0, delta=1, msg='return booked to ' + account)
        self.assertAlmostEqual(flt(frappe.db.get_value('Purchase Receipt Item', b.items[0].name, 'valuation_rate')), 26400, delta=1, msg='24.000 + 10 %')
        made = as_user(ACC, si.detail, invoice)['cost_adjustments']
        self.assertEqual(sorted((r['doctype'], r['kind'], r['amount']) for r in made),
                         [('Journal Entry', 'vat', 5600), ('Landed Cost Voucher', 'cost', -2400), ('Landed Cost Voucher', 'cost', 84000)],
                         'price and VAT into cost on 3388, the VAT part then moved to 33881')
        self.assertEqual({r.name: flt(r.per_billed) for r in frappe.get_all('Purchase Receipt', filters={'name': ['in', [a.name, b.name]]}, fields=['name', 'per_billed'])},
                         {a.name: 100, b.name: 100}, 'billed in full by quantity, the cheaper invoice included')
        self.assertFalse({a.name, b.name} & {r['name'] for r in as_user(ACC, si.queue, self.supplier)['rows']})
        # Cancelling the invoice takes its adjustments with it.
        as_user(ACC, si.cancel, invoice, 'Nhập sai đơn giá')
        self.repost()
        self.assertEqual(frappe.db.count('Landed Cost Voucher', {'lotus_purchase_invoice': invoice, 'docstatus': 1}), 0)
        self.assertAlmostEqual(flt(frappe.db.get_value('Purchase Receipt Item', a.items[0].name, 'valuation_rate')), 110000, delta=1)
        self.assertAlmostEqual(books(), waiting(), delta=1)
        self.assertAlmostEqual(waiting(), 8 * 110000 + 4 * 27000, delta=1)
        self.assertAlmostEqual(flt(frappe.db.get_value('Purchase Receipt', a.name, 'per_billed')), 0, delta=0.01,
                               msg='measured over the 8 kept, none of them invoiced (the 2 returned need no invoice)')
        self.assertEqual(frappe.db.count('Landed Cost Voucher', {'lotus_cost_receipt': a.name, 'docstatus': 1}), 0, 'the split went with the invoice')

    def test_25_household_receipt_without_vat_invoiced_with_vat(self):
        """A receipt with no VAT has no ledger line on 33881, so ERPNext books the invoice VAT on 3388 itself. The VAT still
        goes into cost and both accounts return to zero (review of 11/11/2026)."""
        from lotus_farm.finance import supplier_invoice as si
        self.household()
        receipt = self.receive(self.order(qty=10, rate=100000, vat='KCT'), 10)
        result = as_user(ACC, si.create, receipts=[receipt.name], bill_no='VAT-' + self.tag, bill_date=DAY, client_key=self.tag + 'vat',
                         lines=[dict(source_item=receipt.items[0].name, qty=10, vat_code='10')])
        self.repost()
        vouchers = [receipt.name, result['invoice']]
        self.assertAlmostEqual(self.ledger(MAP['received_not_billed'], vouchers), 0, delta=1, msg='3388')
        self.assertAlmostEqual(self.ledger(setup.valuation_tax_account(C), vouchers), 0, delta=1, msg='33881')
        self.assertAlmostEqual(flt(frappe.db.get_value('Purchase Receipt Item', receipt.items[0].name, 'valuation_rate')), 110000, delta=1)
        made = as_user(ACC, si.detail, result['invoice'])['cost_adjustments']
        self.assertEqual([(r['doctype'], r['amount']) for r in made], [('Landed Cost Voucher', 100000)], 'no transfer: ERPNext already moved it')

    def test_26_household_service_line_received_with_goods_and_freight(self):
        """A Service line on the order and the receipt (household): the receipt credits 33881 only for the goods' VAT and
        3388 only for the goods' own freight; the service's VAT and freight are part of the service cost, on the invoice
        (second review, 11/11/2026: its freight used to go into the stock of the goods); 3388 and 33881 return to zero."""
        from lotus_farm import procurement_queries as queries
        from lotus_farm.finance import supplier_invoice as si
        self.household()
        order = self.order(lines=[dict(kind='Material', qty=10, rate=100000, vat='5', freight=50000),
                                  dict(kind='Service', qty=1, rate=2000000, vat='8', freight=20000)])
        receipt = self.receive_all(order)
        vouchers = [receipt.name]
        waiting = lambda: queries.unbilled(C, DAY, self.supplier)['by_supplier'].get(self.supplier, 0)
        self.assertAlmostEqual(-self.ledger(setup.valuation_tax_account(C), vouchers), 50000, delta=1, msg='33881: the goods VAT only')
        self.assertAlmostEqual(self.clearing(vouchers), 1000000 + 50000 + 50000, delta=1, msg='goods, their VAT and their own freight')
        self.assertAlmostEqual(flt(frappe.db.get_value('Purchase Receipt Item', receipt.items[0].name, 'valuation_rate')), 110000, delta=1,
                               msg='100.000 + 5 % + 5.000 freight: none of the service freight')
        self.assertAlmostEqual(waiting(), self.clearing(vouchers), delta=1)
        result = as_user(ACC, si.create, receipts=[receipt.name], bill_no='DVN-' + self.tag, bill_date=DAY, client_key=self.tag + 'dvn')
        self.assertEqual(result['amount'], 1000000 + 50000 + 50000 + 2000000 + 160000 + 20000)
        vouchers.append(result['invoice'])
        self.repost()
        self.assertAlmostEqual(self.ledger(MAP['received_not_billed'], vouchers), 0, delta=1, msg='3388')
        self.assertAlmostEqual(self.ledger(setup.valuation_tax_account(C), vouchers), 0, delta=1, msg='33881')
        self.assertAlmostEqual(self.ledger(MAP['admin_expense'], [result['invoice']]), 2180000, delta=1, msg='the service VAT and freight are part of its cost')
        self.assertAlmostEqual(waiting(), 0, delta=1)

    def test_27_return_after_the_invoice_then_an_adjustment_invoice(self):
        """Goods returned after an invoice at another price, then the supplier's adjustment invoice: the returned goods leave
        at what they cost (nothing to expense), the kept goods carry the invoice price, 3388 returns to zero."""
        from lotus_farm import procurement_adjustments as adjustments
        from lotus_farm.finance import supplier_invoice as si
        receipt = self.receive(self.order(qty=10, rate=100000), 10)
        line = receipt.items[0].name
        invoice = as_user(ACC, si.create, receipts=[receipt.name], bill_no='RA-' + self.tag, bill_date=DAY, client_key=self.tag + 'ra',
                          lines=[dict(source_item=line, qty=10, rate=110000, variance_reason='NCC tăng giá')])['invoice']
        back = p.return_receipt(receipt.name, DAY, {line: 2}, self.tag + 'ret', 1, 'Hàng móp')
        self.assertTrue(back['needs_credit_note'])
        # Before the adjustment invoice: 10 invoiced, 8 kept. The 2 returned leave at the invoice price and the supplier owes
        # them back: 'chưa có hóa đơn' is negative and equals 3388 (second review, 11/11/2026: it was left out).
        from lotus_farm import procurement_queries as queries
        self.repost()
        claim = queries.unbilled(C, DAY, self.supplier)['by_supplier'].get(self.supplier, 0)
        self.assertAlmostEqual(claim, -220000, delta=1)
        self.assertAlmostEqual(self.clearing([receipt.name, back['name'], invoice]), claim, delta=1)
        for account in {MAP['admin_expense'], frappe.get_cached_value('Company', C, 'default_expense_account')}:
            self.assertAlmostEqual(self.ledger(account, [back['name']]), 0, delta=1, msg='return booked to ' + account)
        pi_line = frappe.get_doc('Purchase Invoice', invoice).items[0].name
        note = as_user(ACC, adjustments.credit_note, C, invoice, DAY, json.dumps({pi_line: 2}), self.tag + 'cn')['invoice']
        self.repost()
        self.assertAlmostEqual(self.ledger(MAP['received_not_billed'], [receipt.name, back['name'], invoice, note]), 0, delta=1)
        for account in {MAP['admin_expense'], frappe.get_cached_value('Company', C, 'default_expense_account')}:
            self.assertAlmostEqual(self.ledger(account, [back['name']]), 0, delta=1, msg='return booked to ' + account)
        kept = flt(frappe.db.sql("select sum(stock_value_difference) from `tabStock Ledger Entry` where voucher_no in %s and is_cancelled=0",
                                 ((receipt.name, back['name']),))[0][0])
        self.assertAlmostEqual(kept, 8 * 110000, delta=2, msg='the kept goods carry the invoice price')
        self.assertAlmostEqual(flt(frappe.db.get_value('Purchase Receipt', receipt.name, 'per_billed')), 100, delta=0.01)
        # Cancelling the adjustment invoice brings the claim back. The split leaves out the credit note being cancelled
        # (second review, 11/11/2026: it counted it, and the kept goods took 20.000 too much).
        as_user(ACC, si.cancel, note, 'Nhập nhầm')
        self.repost()
        kept = flt(frappe.db.sql("select sum(stock_value_difference) from `tabStock Ledger Entry` where voucher_no in %s and is_cancelled=0",
                                 ((receipt.name, back['name']),))[0][0])
        self.assertAlmostEqual(kept, 8 * 110000, delta=2)
        self.assertAlmostEqual(queries.unbilled(C, DAY, self.supplier)['by_supplier'].get(self.supplier, 0), -220000, delta=1)
        self.assertAlmostEqual(self.clearing([receipt.name, back['name'], invoice, note]), -220000, delta=1)

    def close_receipts(self, day):
        """An accounting period closed for Purchase Receipt on one day, as the chief accountant would close it."""
        name = getattr(self, 'period', None)  # ERPNext names the period "title - company abbr"
        if not name:
            name = self.period = frappe.get_doc(dict(doctype='Accounting Period', period_name='PCT ' + self.tag + ' ' + str(day), company=C,
                                                     start_date=day, end_date=day, closed_documents=[dict(document_type='Purchase Receipt', closed=1)])
                                                ).insert(ignore_permissions=True).name
            self.addCleanup(lambda: setattr(self, 'period', None))
        frappe.db.sql("update `tabClosed Document` set closed=1 where parent=%s and document_type='Purchase Receipt'", name)
        return name

    def test_28_receipt_in_a_closed_period(self):
        """The receipt's books are closed: the difference is a cost of the invoice's period, the closed books do not move.
        An invoice whose adjustment rewrote a receipt that has since been closed is not cancelled (review of 11/11/2026)."""
        from lotus_farm.finance import supplier_invoice as si
        receipt = self.receive(self.order(qty=10, rate=100000), 10)
        line = receipt.items[0].name
        period = self.close_receipts(DAY)
        invoice = as_user(ACC, si.create, receipts=[receipt.name], bill_no='KS-' + self.tag, bill_date=DAY, client_key=self.tag + 'ks',
                          lines=[dict(source_item=line, qty=10, rate=110000, variance_reason='NCC tăng giá')])['invoice']
        made = as_user(ACC, si.detail, invoice)['cost_adjustments']
        self.assertEqual([(r['doctype'], r['kind'], r['amount']) for r in made], [('Journal Entry', 'expense', 100000)])
        self.assertAlmostEqual(self.ledger(MAP['received_not_billed'], [receipt.name, invoice, made[0]['name']]), 0, delta=1)
        self.assertAlmostEqual(flt(frappe.db.get_value('Purchase Receipt Item', line, 'valuation_rate')), 100000, delta=1, msg='closed books untouched')
        as_user(ACC, si.cancel, invoice, 'Nhập lại đúng giá')
        self.assertEqual(frappe.db.get_value('Journal Entry', made[0]['name'], 'docstatus'), 2)
        frappe.db.sql("update `tabClosed Document` set closed=0 where parent=%s", period)
        again = as_user(ACC, si.create, receipts=[receipt.name], bill_no='KS2-' + self.tag, bill_date=DAY, client_key=self.tag + 'ks2',
                        lines=[dict(source_item=line, qty=10, rate=110000, variance_reason='NCC tăng giá')])['invoice']
        self.assertEqual([r['doctype'] for r in as_user(ACC, si.detail, again)['cost_adjustments']], ['Landed Cost Voucher'])
        self.close_receipts(DAY)
        self.assertIn('hóa đơn điều chỉnh', self.refused(as_user, ACC, si.cancel, again, 'Thử hủy khi kỳ đã khóa'))

    def test_29_billing_counts_each_line_by_value_and_follows_returns(self):
        """per_billed by quantity, each line weighted by its value; a return or its cancellation after the invoice moves it."""
        from lotus_farm.finance import supplier_invoice as si
        order = self.order(lines=[dict(kind='Material', qty=10, rate=600000), dict(kind='Tool', qty=500, rate=2000)])
        receipt = self.receive_all(order)
        a = next(r.name for r in receipt.items if r.item_code == 'PCT-M')
        b = next(r.name for r in receipt.items if r.item_code == 'PCT-T')
        billed = lambda: flt(frappe.db.get_value('Purchase Receipt', receipt.name, 'per_billed'))
        v1 = as_user(ACC, si.create, receipts=[receipt.name], bill_no='V1-' + self.tag, bill_date=DAY, client_key=self.tag + 'v1', lines=[dict(source_item=a, qty=10)])['invoice']
        self.assertAlmostEqual(billed(), 600 / 7, delta=0.01, msg='6.000.000 of 7.000.000, not 10 of 510 units')
        waiting = {r['name']: r for r in as_user(ACC, si.queue, self.supplier)['rows']}
        self.assertAlmostEqual(waiting[receipt.name]['amount'], 1000000, delta=1)
        v2 = as_user(ACC, si.create, receipts=[receipt.name], bill_no='V2-' + self.tag, bill_date=DAY, client_key=self.tag + 'v2',
                     lines=[dict(source_item=b, qty=490, rate=1900, variance_reason='Chiết khấu')])['invoice']
        part = 100 * (6000000 + 980000) / 7000000
        self.assertAlmostEqual(billed(), part, delta=0.01)
        back = p.return_receipt(receipt.name, DAY, {b: 10}, self.tag + 'ret', 1, 'Hỏng')
        self.assertAlmostEqual(billed(), 100, delta=0.01, msg='the rest went back')
        self.assertNotIn(receipt.name, [r['name'] for r in as_user(ACC, si.queue, self.supplier)['rows']])
        # Third review: the books too. The cheaper invoice (-49.000) stays with the 490 kept; the 10 returned leave at
        # 1.900 each; 3388 is clear; nothing goes to expense.
        from lotus_farm import procurement_queries as queries
        self.repost()
        stock = lambda: flt(frappe.db.sql("select sum(stock_value_difference) from `tabStock Ledger Entry` where voucher_no in %s and is_cancelled=0",
                                          ((receipt.name, back['name']),))[0][0])
        self.assertAlmostEqual(stock(), 6000000 + 490 * 1900, delta=2)
        self.assertAlmostEqual(self.clearing([receipt.name, back['name'], v1, v2]), 0, delta=1)
        for account in {MAP['admin_expense'], frappe.get_cached_value('Company', C, 'default_expense_account')}:
            self.assertAlmostEqual(self.ledger(account, [back['name']]), 0, delta=1, msg='return booked to ' + account)
        ret = frappe.get_doc('Purchase Receipt', back['name'])
        receiving.receipt_action(ret.name, str(ret.modified), 'cancel', 'Trả nhầm')
        self.assertAlmostEqual(billed(), part, delta=0.01, msg='the cancelled return is waiting for an invoice again')
        self.assertEqual(frappe.db.count('Landed Cost Voucher', {'lotus_cost_receipt': receipt.name, 'docstatus': 1}), 0)
        self.repost()
        self.assertAlmostEqual(stock(), 6000000 + 1000000 - 49000, delta=2)
        self.assertAlmostEqual(self.clearing([receipt.name, back['name'], v1, v2]), 20000, delta=1)
        self.assertAlmostEqual(queries.unbilled(C, DAY, self.supplier)['by_supplier'].get(self.supplier, 0), 20000, delta=1)

    def test_30_asset_line_at_another_price_is_refused(self):
        from lotus_farm.finance import supplier_invoice as si
        receipt = self.receive(self.order(kind='Asset', qty=1, rate=50000000), 1)
        message = self.refused(as_user, CHIEF, si.create, receipts=[receipt.name], bill_no='TS-' + self.tag, bill_date=DAY,
                               client_key=self.tag + 'ts', lines=[dict(source_item=receipt.items[0].name, qty=1, rate=48000000, variance_reason='Giảm giá')])
        self.assertIn('tài sản cố định', message)

    def test_31_waiting_goods_match_the_books_on_any_closing_date(self):
        """The difference is posted at the receipt's date: on a closing date between the receipt and a later invoice,
        'hàng đã nhận, chưa có hóa đơn' still equals 3388 + 33881."""
        from lotus_farm import procurement_queries as queries
        from lotus_farm.finance import supplier_invoice as si
        earlier = add_days(DAY, -2)
        order = self.order(qty=10, rate=100000)
        frappe.db.set_value('Purchase Order', order.name, 'transaction_date', earlier)
        receipt = self.receive(order, 10, day=earlier)
        invoice = as_user(ACC, si.create, receipts=[receipt.name], bill_no='AO-' + self.tag, bill_date=DAY, client_key=self.tag + 'ao',
                          lines=[dict(source_item=receipt.items[0].name, qty=10, rate=110000, variance_reason='NCC tăng giá')])['invoice']
        self.repost()
        for day, expected in ((add_days(DAY, -1), 1100000), (DAY, 0)):
            self.assertAlmostEqual(self.clearing([receipt.name, invoice], day), expected, delta=1, msg='books on %s' % day)
            self.assertAlmostEqual(queries.unbilled(C, day, self.supplier)['by_supplier'].get(self.supplier, 0), expected, delta=1, msg='waiting on %s' % day)

    def test_32_lotus_adjustments_move_with_their_invoice_only(self):
        from lotus_farm.finance import supplier_invoice as si
        self.household()
        receipt = self.receive(self.order(qty=10, rate=100000, vat='5'), 10)
        invoice = as_user(ACC, si.create, receipts=[receipt.name], bill_no='GD-' + self.tag, bill_date=DAY, client_key=self.tag + 'gd',
                          lines=[dict(source_item=receipt.items[0].name, qty=10, rate=110000, vat_code='8', variance_reason='NCC tăng giá')])['invoice']
        made = as_user(ACC, si.detail, invoice)['cost_adjustments']
        self.assertEqual(sorted(r['doctype'] for r in made), ['Journal Entry', 'Landed Cost Voucher'])
        for row in made:
            frappe.db.savepoint('own_cancel')
            with self.assertRaises(frappe.PermissionError):
                frappe.get_doc(row['doctype'], row['name']).cancel()
            frappe.db.rollback(save_point='own_cancel')
        as_user(ACC, si.cancel, invoice, 'Nhập sai')
        for row in made:
            self.assertEqual(frappe.db.get_value(row['doctype'], row['name'], 'docstatus'), 2)

    # ---- Second independent review (11/11/2026) ----
    def test_33_asset_pieces_are_numbered_once(self):
        """An asset line of 2 is received as 2 rows of 1. ERPNext 16 spreads VAT and freight by row number, so the rows are
        numbered 1..n again and each piece carries its VAT and freight once (they used to share number 1)."""
        self.household()
        receipt = self.receive(self.order(kind='Asset', qty=2, rate=10000000, vat='10', freight=200000), 2)
        self.assertEqual([r.idx for r in receipt.items], [1, 2])
        self.assertAlmostEqual(sum(flt(r.item_tax_amount) for r in receipt.items), 2000000 + 200000, delta=2)
        self.assertAlmostEqual(-self.ledger(setup.valuation_tax_account(C), [receipt.name]), 2000000, delta=1)

    def test_34_each_goods_line_carries_its_own_freight(self):
        """Household: ERPNext spreads the freight row over the goods by value; Lotus moves it back so each line carries its
        own freight. A line returned in full then leaves at what it cost, and the invoice clears 3388."""
        from lotus_farm import procurement_queries as queries
        from lotus_farm.finance import supplier_invoice as si
        self.household()
        receipt = self.receive_all(self.order(lines=[dict(kind='Material', qty=10, rate=100000, freight=0),
                                                     dict(kind='Tool', qty=10, rate=100000, freight=200000)]))
        self.repost()
        a = next(r.name for r in receipt.items if r.item_code == 'PCT-M')
        b = next(r.name for r in receipt.items if r.item_code == 'PCT-T')
        rate = lambda line: flt(frappe.db.get_value('Purchase Receipt Item', line, 'valuation_rate'))
        self.assertEqual((round(rate(a)), round(rate(b))), (100000, 120000))
        back = p.return_receipt(receipt.name, DAY, {a: 10}, self.tag + 'ret', 1, 'Sai quy cách')
        self.repost()
        for account in {MAP['admin_expense'], frappe.get_cached_value('Company', C, 'default_expense_account')}:
            self.assertAlmostEqual(self.ledger(account, [back['name']]), 0, delta=1, msg='return booked to ' + account)
        waiting = lambda: queries.unbilled(C, DAY, self.supplier)['by_supplier'].get(self.supplier, 0)
        vouchers = [receipt.name, back['name']]
        self.assertAlmostEqual(waiting(), 1000000 + 200000, delta=1)
        self.assertAlmostEqual(self.clearing(vouchers), waiting(), delta=1)
        invoice = as_user(ACC, si.create, receipts=[receipt.name], bill_no='VC-' + self.tag, bill_date=DAY, client_key=self.tag + 'vc')['invoice']
        self.repost()
        self.assertAlmostEqual(self.clearing(vouchers + [invoice]), 0, delta=1)
        self.assertAlmostEqual(waiting(), 0, delta=1)
        self.assertAlmostEqual(rate(b), 120000, delta=1)

    def test_35_everything_returned_after_the_invoice(self):
        """Goods invoiced at a higher price, then all sent back: they leave at what they cost (nothing to expense), 3388
        holds the claim on the supplier at the invoice price, the receipt says it went back; the credit note follows its
        invoice into stock and everything returns to zero."""
        from lotus_farm import procurement_adjustments as adjustments, procurement_queries as queries
        from lotus_farm.finance import supplier_invoice as si
        receipt = self.receive(self.order(qty=10, rate=100000), 10)
        line = receipt.items[0].name
        invoice = as_user(ACC, si.create, receipts=[receipt.name], bill_no='TH-' + self.tag, bill_date=DAY, client_key=self.tag + 'th',
                          lines=[dict(source_item=line, qty=10, rate=110000, variance_reason='NCC tăng giá')])['invoice']
        # Two returns of one line (ERPNext's own returned-quantity map keeps only one of them).
        returns = [p.return_receipt(receipt.name, DAY, {line: qty}, self.tag + 'ret' + str(qty), 1, 'Trả hàng')['name'] for qty in (4, 6)]
        self.repost()
        stock = lambda: flt(frappe.db.sql("select sum(stock_value_difference) from `tabStock Ledger Entry` where voucher_no in %s and is_cancelled=0",
                                          ((receipt.name, *returns),))[0][0])
        expense = {MAP['admin_expense'], frappe.get_cached_value('Company', C, 'default_expense_account')}
        for account in expense:
            self.assertAlmostEqual(self.ledger(account, returns), 0, delta=1, msg='returns booked to ' + account)
        self.assertAlmostEqual(stock(), 0, delta=2)
        claim = queries.unbilled(C, DAY, self.supplier)['by_supplier'].get(self.supplier, 0)
        self.assertAlmostEqual(claim, -1100000, delta=1, msg='the supplier owes the 10 at the invoice price')
        self.assertAlmostEqual(self.clearing([receipt.name, *returns, invoice]), claim, delta=1)
        self.assertEqual({r['name']: r for r in p.receipts(C)}[receipt.name]['billing'], 'Đã trả hết hàng')
        self.assertEqual(p.receipt(receipt.name)['items'][0]['returned_qty'], 10)
        pi_line = frappe.get_doc('Purchase Invoice', invoice).items[0].name
        note = as_user(ACC, adjustments.credit_note, C, invoice, DAY, json.dumps({pi_line: 10}), self.tag + 'cn')['invoice']
        self.repost()
        made = as_user(ACC, si.detail, note)['cost_adjustments']
        self.assertEqual([(r['doctype'], r['kind'], r['amount']) for r in made], [('Landed Cost Voucher', 'cost', -100000)])
        self.assertAlmostEqual(self.clearing([receipt.name, *returns, invoice, note]), 0, delta=1)
        self.assertAlmostEqual(stock(), 0, delta=2)
        for account in expense:
            self.assertAlmostEqual(self.ledger(account, [*returns, note]), 0, delta=1, msg='booked to ' + account)
        self.assertEqual(frappe.db.count('Landed Cost Voucher', {'lotus_cost_receipt': receipt.name, 'docstatus': 1}), 0)

    def test_36_credit_note_follows_how_its_invoice_was_booked(self):
        """An invoice booked as a cost because the receipt's books were closed. Once they reopen, its credit note is a
        cost too, not a voucher on the receipt; 3388 returns to zero."""
        from lotus_farm import procurement_adjustments as adjustments
        from lotus_farm.finance import supplier_invoice as si
        receipt = self.receive(self.order(qty=10, rate=100000), 10)
        line = receipt.items[0].name
        period = self.close_receipts(DAY)
        invoice = as_user(ACC, si.create, receipts=[receipt.name], bill_no='CP-' + self.tag, bill_date=DAY, client_key=self.tag + 'cp',
                          lines=[dict(source_item=line, qty=10, rate=110000, variance_reason='NCC tăng giá')])['invoice']
        first = as_user(ACC, si.detail, invoice)['cost_adjustments']
        self.assertEqual([(r['kind'], r['amount']) for r in first], [('expense', 100000)])
        frappe.db.sql("update `tabClosed Document` set closed=0 where parent=%s", period)
        back = p.return_receipt(receipt.name, DAY, {line: 2}, self.tag + 'ret', 1, 'Hàng móp')
        pi_line = frappe.get_doc('Purchase Invoice', invoice).items[0].name
        note = as_user(ACC, adjustments.credit_note, C, invoice, DAY, json.dumps({pi_line: 2}), self.tag + 'cn')['invoice']
        made = as_user(ACC, si.detail, note)['cost_adjustments']
        self.assertEqual([(r['doctype'], r['kind'], r['amount']) for r in made], [('Journal Entry', 'expense', -20000)])
        self.repost()
        vouchers = [receipt.name, back['name'], invoice, note] + [r['name'] for r in first + made]
        self.assertAlmostEqual(self.ledger(MAP['received_not_billed'], vouchers), 0, delta=1)
        self.assertAlmostEqual(flt(frappe.db.get_value('Purchase Receipt Item', line, 'valuation_rate')), 100000, delta=1)
        self.assertEqual(frappe.db.count('Landed Cost Voucher', {'lotus_cost_receipt': receipt.name, 'docstatus': 1}), 0)

    def test_37_period_closing_voucher_counts_as_closed_books(self):
        """A receipt on or before the last Period Closing Voucher: ERPNext refuses to repost it, so the invoice difference
        is a cost of the invoice's period (the invoice used to fail to submit)."""
        from lotus_farm.finance import invoice_cost, supplier_invoice as si
        earlier = add_days(DAY, -2)
        order = self.order(qty=10, rate=100000)
        frappe.db.set_value('Purchase Order', order.name, 'transaction_date', earlier)
        receipt = self.receive(order, 10, day=earlier)
        closing = frappe.get_doc(dict(doctype='Period Closing Voucher', company=C, fiscal_year='2026', transaction_date=earlier,
                                      posting_date=earlier, period_start_date='2026-01-01', period_end_date=earlier, remarks='Kiểm thử',
                                      closing_account_head=frappe.db.get_value('Account', {'company': C, 'root_type': 'Equity', 'is_group': 0}, 'name')))
        closing.name = 'PCT-PCV-' + self.tag
        closing.docstatus = 1
        closing.db_insert()  # the closing itself is ERPNext's; only its date matters here
        self.assertIn('kết chuyển', invoice_cost._closed(C, earlier) or '')
        invoice = as_user(ACC, si.create, receipts=[receipt.name], bill_no='PCV-' + self.tag, bill_date=DAY, client_key=self.tag + 'pcv',
                          lines=[dict(source_item=receipt.items[0].name, qty=10, rate=110000, variance_reason='NCC tăng giá')])['invoice']
        made = as_user(ACC, si.detail, invoice)['cost_adjustments']
        self.assertEqual([(r['doctype'], r['kind'], r['amount']) for r in made], [('Journal Entry', 'expense', 100000)])
        self.assertAlmostEqual(flt(frappe.db.get_value('Purchase Receipt Item', receipt.items[0].name, 'valuation_rate')), 100000, delta=1)
        self.assertAlmostEqual(self.ledger(MAP['received_not_billed'], [receipt.name, invoice, made[0]['name']]), 0, delta=1)

    def test_38_advance_on_an_order_after_part_of_it_is_invoiced(self):
        """The advance an invoice already used is not counted again (ERPNext 16 keeps it in advance_paid); an order
        invoiced in full takes no further advance, on any payment path."""
        from lotus_farm.finance import supplier_invoice as si, supplier_payment as sp
        order = self.order(qty=10, rate=1000000)
        signed(as_user(ACC, p.supplier_payment, C, 'Purchase Order', order.name, 4000000, 'cash', DAY, {'CHIEF': CHIEF, 'APPROVE': DIR}, self.tag + 'adv'))
        first = self.receive(order, 5)
        made = as_user(ACC, si.create, receipts=[first.name], bill_no='AD1-' + self.tag, bill_date=DAY, client_key=self.tag + 'ad1')
        self.assertEqual(flt(frappe.db.get_value('Purchase Invoice', made['invoice'], 'outstanding_amount')), 1000000, 'the advance paid the invoice')
        self.assertAlmostEqual(funding._remaining_source('Purchase Order', order.name, lock_rows=False), 5000000, delta=1)
        listed = {i['name']: i for i in as_user(ACC, sp.open_items, self.supplier)['items']}
        self.assertAlmostEqual(listed[order.name]['payable'], 5000000, delta=1)
        # A 5.000.000 advance is prepared; 3 more units are invoiced before the director signs: only 2.000.000 is left.
        waiting = as_user(ACC, p.supplier_payment, C, 'Purchase Order', order.name, 5000000, 'cash', DAY, {'CHIEF': CHIEF, 'APPROVE': DIR}, self.tag + 'adv5')
        more = self.receive(order, 3)
        as_user(ACC, si.create, receipts=[more.name], bill_no='AD2-' + self.tag, bill_date=DAY, client_key=self.tag + 'ad2')
        self.assertIn('chỉ còn tạm ứng được 2.000.000', self.refused(signed, waiting))
        last = self.receive(order, 2)
        as_user(ACC, si.create, receipts=[last.name], bill_no='AD3-' + self.tag, bill_date=DAY, client_key=self.tag + 'ad3')
        self.assertNotIn(order.name, [i['name'] for i in as_user(ACC, sp.open_items, self.supplier)['items']])
        self.assertNotIn(order.name, [s['name'] for s in funding.options(C)['sources']['Purchase Order']])
        self.assertIn('không tạm ứng thêm', self.refused(as_user, ACC, p.supplier_payment, C, 'Purchase Order', order.name, 100000, 'cash', DAY,
                                                         {'CHIEF': CHIEF, 'APPROVE': DIR}, self.tag + 'adv2'))

    def test_39_goods_received_after_a_vat_rate_ended(self):
        """Code 8 % ends on 31/12/2026 and gives way to 10 % (vat_vn.json, here moved to yesterday). Goods ordered at 8 %
        and received later carry 10 %. An asset received at 8 % and invoiced after the end keeps its value; the VAT
        difference is a cost of the period and 33881 returns to zero (household)."""
        from lotus_farm.finance import rules as finance_rules, supplier_invoice as si
        self.household()
        earlier, yesterday = add_days(DAY, -2), add_days(DAY, -1)
        goods = self.order(qty=10, rate=100000, vat='8')
        asset = self.order(kind='Asset', qty=1, rate=10000000, vat='8')
        for order in (goods, asset):
            frappe.db.set_value('Purchase Order', order.name, 'transaction_date', earlier)
        data = finance_rules.load_vat()
        next(r for r in data['rates'] if r['code'] == '8')['to'] = yesterday
        with patch.object(finance_rules, 'load_vat', return_value=data):
            piece = self.receive(asset, 1, day=yesterday)
            self.assertEqual(piece.items[0].lotus_line_vat, '8', 'still in force on the receipt date')
            received = self.receive(goods, 10)
            self.assertEqual(received.items[0].lotus_line_vat, '10')
            self.assertAlmostEqual(-self.ledger(setup.valuation_tax_account(C), [received.name]), 100000, delta=1)
            result = as_user(CHIEF, si.create, receipts=[piece.name], bill_no='TS8-' + self.tag, bill_date=DAY, client_key=self.tag + 'ts8')
            made = as_user(ACC, si.detail, result['invoice'])['cost_adjustments']
        self.assertEqual(frappe.db.get_value('Purchase Invoice Item', {'parent': result['invoice']}, 'lotus_line_vat'), '10')
        self.assertEqual([(r['doctype'], r['kind'], r['amount']) for r in made], [('Journal Entry', 'expense', 200000)])
        self.assertAlmostEqual(self.ledger(setup.valuation_tax_account(C), [piece.name, result['invoice'], made[0]['name']]), 0, delta=1, msg='33881')

    def test_40_rounding_on_a_deductible_invoice_with_an_untaxed_line(self):
        """Deductible VAT, one line at 10 % and one without VAT: the đồng of rounding go to the round-off account. On the
        VAT account ERPNext 16 refuses the invoice (Item Wise Tax Details do not match)."""
        from lotus_farm.finance import supplier_invoice as si
        receipt = self.receive_all(self.order(lines=[dict(kind='Material', qty=3, rate=33333, vat='10'),
                                                     dict(kind='Tool', qty=1, rate=100000, vat='KCT')]))
        result = as_user(ACC, si.create, receipts=[receipt.name], bill_no='LT-' + self.tag, bill_date=DAY, client_key=self.tag + 'lt',
                         printed_total=210000)
        self.assertEqual(result['amount'], 210000)
        self.assertTrue(0 < result['rounding_adjustment'] <= 2, result['rounding_adjustment'])
        round_off = frappe.get_cached_value('Company', C, 'round_off_account')
        self.assertAlmostEqual(self.ledger(round_off, [result['invoice']]), result['rounding_adjustment'], delta=0.01)
        self.assertAlmostEqual(self.ledger(MAP['input_vat'], [result['invoice']]), 10000, delta=1, msg='1331 keeps the VAT of the taxed line only')

    def test_42_credit_note_for_goods_returned_after_the_invoice_once_the_books_closed(self):
        """Goods returned after the invoice while the books were open: their difference waits on 3388 as the claim. If
        the receipt's books close before the credit note, Lotus cannot book it right by itself and says so (it used to
        leave the claim on 3388 and show a gain); once the period is open again the credit note posts and 3388 clears."""
        from lotus_farm import procurement_adjustments as adjustments
        from lotus_farm.finance import supplier_invoice as si
        receipt = self.receive(self.order(qty=10, rate=100000), 10)
        line = receipt.items[0].name
        invoice = as_user(ACC, si.create, receipts=[receipt.name], bill_no='KN-' + self.tag, bill_date=DAY, client_key=self.tag + 'kn',
                          lines=[dict(source_item=line, qty=10, rate=110000, variance_reason='NCC tăng giá')])['invoice']
        back = p.return_receipt(receipt.name, DAY, {line: 2}, self.tag + 'ret', 1, 'Hàng móp')
        period = self.close_receipts(DAY)
        pi_line = frappe.get_doc('Purchase Invoice', invoice).items[0].name
        message = self.refused(as_user, ACC, adjustments.credit_note, C, invoice, DAY, json.dumps({pi_line: 2}), self.tag + 'cn')
        self.assertIn('Mở lại kỳ đó', message)
        frappe.db.sql("update `tabClosed Document` set closed=0 where parent=%s", period)
        note = as_user(ACC, adjustments.credit_note, C, invoice, DAY, json.dumps({pi_line: 2}), self.tag + 'cn2')['invoice']
        self.repost()
        self.assertAlmostEqual(self.clearing([receipt.name, back['name'], invoice, note]), 0, delta=1)

    # ---- Third independent review (11/11/2026) ----
    def test_43_invoice_on_a_receipt_of_a_closed_order(self):
        """The rest of an order closed with Đóng đơn: ERPNext refuses to repost a receipt of a closed order, which every
        Landed Cost Voucher does. The invoice at another price still goes into the cost and can be cancelled; the order
        stays closed and its ordered quantity stays out of the stock plan."""
        from lotus_farm.finance import supplier_invoice as si
        order = self.order(qty=10, rate=100000)
        receipt = self.receive(order, 6)
        order.reload()
        as_user(DIR, purchasing.close_order, order.name, str(order.modified), 'NCC hết hàng')
        self.assertEqual(frappe.db.get_value('Purchase Order', order.name, 'status'), 'Closed')
        ordered = lambda: flt(frappe.db.get_value('Bin', {'item_code': 'PCT-M', 'warehouse': WH}, 'ordered_qty'))
        before = ordered()
        line = receipt.items[0].name
        invoice = as_user(ACC, si.create, receipts=[receipt.name], bill_no='DD-' + self.tag, bill_date=DAY, client_key=self.tag + 'dd',
                          lines=[dict(source_item=line, qty=6, rate=110000, variance_reason='NCC tăng giá')])['invoice']
        self.repost()
        self.assertAlmostEqual(flt(frappe.db.get_value('Purchase Receipt Item', line, 'valuation_rate')), 110000, delta=1)
        self.assertEqual(frappe.db.get_value('Purchase Order', order.name, 'status'), 'Closed')
        self.assertAlmostEqual(ordered(), before, delta=0.001)
        self.assertAlmostEqual(self.ledger(MAP['received_not_billed'], [receipt.name, invoice]), 0, delta=1)
        as_user(ACC, si.cancel, invoice, 'Nhập sai đơn giá')
        self.assertAlmostEqual(flt(frappe.db.get_value('Purchase Receipt Item', line, 'valuation_rate')), 100000, delta=1)
        self.assertEqual(frappe.db.get_value('Purchase Order', order.name, 'status'), 'Closed')
        self.assertAlmostEqual(ordered(), before, delta=0.001)

    def test_44_invoice_that_uses_an_advance_from_a_closed_month(self):
        """An advance paid on an order in a month whose result is already closed: ERPNext links it to the new invoice by
        saving the old Payment Entry again. That save changes no ledger line, so the closed month lets it through (the
        whole invoice used to be refused)."""
        from lotus_farm.finance import posting, supplier_invoice as si
        last_month = add_days(DAY[:8] + '01', -1)
        order = self.order(qty=10, rate=100000)
        frappe.db.set_value('Purchase Order', order.name, 'transaction_date', last_month)
        signed(as_user(ACC, p.supplier_payment, C, 'Purchase Order', order.name, 300000, 'cash', last_month, {'CHIEF': CHIEF, 'APPROVE': DIR}, self.tag + 'adv'))
        closing = frappe.get_doc(dict(doctype=posting.POSTING, company=C, source_doctype=setup.SETTINGS, source_name=setup.SETTINGS, purpose='Result Closing',
                                      voucher_type='Journal Entry', voucher_name='PCT-RC-' + self.tag, posting_date=last_month, state='Posted',
                                      active_key=posting.active_key(setup.SETTINGS, setup.SETTINGS, 'Result Closing', str(last_month)[:7])))
        closing.name = 'PCT-RC-' + self.tag
        closing.db_insert()
        receipt = self.receive(order, 10)
        made = as_user(ACC, si.create, receipts=[receipt.name], bill_no='AV-' + self.tag, bill_date=DAY, client_key=self.tag + 'av')
        self.assertEqual(flt(frappe.db.get_value('Purchase Invoice', made['invoice'], 'outstanding_amount')), 700000, 'the advance paid part of it')

    def test_45_credit_notes_in_closed_books_follow_the_claim_actually_held(self):
        """Closed books, two receipts. (1) More invoiced than kept: 24.000 of the difference waits on 3388 as the claim, so a
        credit note at the receipt price, or cancelling that invoice, would change the claim: refused with the way out.
        (2) Invoiced no more than kept: the split balances and nothing is held, so a later credit note simply goes to
        expense (it used to be refused because a split voucher existed)."""
        from lotus_farm import procurement_adjustments as adjustments
        from lotus_farm.finance import invoice_cost, supplier_invoice as si
        earlier = add_days(DAY, -2)

        def received():
            order = self.order(qty=10, rate=100000)
            frappe.db.set_value('Purchase Order', order.name, 'transaction_date', earlier)
            self.tag = uuid.uuid4().hex[:8]
            return self.receive(order, 10, day=earlier)

        def bill(receipt, qty, rate, key, day):
            extra = dict(variance_reason='NCC tăng giá') if rate != 100000 else {}
            return as_user(ACC, si.create, receipts=[receipt.name], bill_no='CB-' + key + self.tag, bill_date=day, client_key=self.tag + key,
                           lines=[dict(source_item=receipt.items[0].name, qty=qty, rate=rate, **extra)])['invoice']

        held = lambda r: invoice_cost._parked_claim(frappe._dict(name=r.items[0].name, parent=r.name))
        one = received()
        bill(one, 6, 110000, 'a1', earlier)
        i2 = bill(one, 4, 100000, 'a2', earlier)
        p.return_receipt(one.name, earlier, {one.items[0].name: 4}, self.tag + 'x1', 1, 'Hỏng')
        self.assertAlmostEqual(held(one), -24000, delta=1)
        two = received()
        bill(two, 6, 110000, 'b1', earlier)
        p.return_receipt(two.name, earlier, {two.items[0].name: 2}, self.tag + 'y1', 1, 'Hỏng')
        self.assertAlmostEqual(held(two), 0, delta=1)
        self.close_receipts(earlier)
        line = frappe.get_doc('Purchase Invoice', i2).items[0].name
        self.assertIn('Mở lại kỳ đó', self.refused(as_user, ACC, adjustments.credit_note, C, i2, DAY, json.dumps({line: 4}), self.tag + 'cn1'))
        self.assertIn('Mở lại kỳ đó', self.refused(as_user, ACC, si.cancel, i2, 'Thử hủy khi kỳ đã khóa'))
        j2 = bill(two, 2, 110000, 'b2', DAY)
        p.return_receipt(two.name, DAY, {two.items[0].name: 2}, self.tag + 'y2', 1, 'Hỏng')
        pi_line = frappe.get_doc('Purchase Invoice', j2).items[0].name
        note = as_user(ACC, adjustments.credit_note, C, j2, DAY, json.dumps({pi_line: 2}), self.tag + 'cn2')['invoice']
        made = as_user(ACC, si.detail, note)['cost_adjustments']
        self.assertEqual([(r['doctype'], r['kind'], r['amount']) for r in made], [('Journal Entry', 'expense', -20000)])

    def test_46_cancelling_an_invoice_without_a_difference_resplits_the_returns(self):
        """10 received; 5 invoiced at 110.000 and 5 at the receipt price; 2 returned: more invoiced than kept, 10.000 waits
        on 3388. Cancelling the invoice at the receipt price (no voucher of its own) splits again: the 8 kept carry the
        whole 50.000 and 3388 equals what waits for an invoice."""
        from lotus_farm import procurement_queries as queries
        from lotus_farm.finance import invoice_cost, supplier_invoice as si
        receipt = self.receive(self.order(qty=10, rate=100000), 10)
        line = receipt.items[0].name
        first = as_user(ACC, si.create, receipts=[receipt.name], bill_no='NA-' + self.tag, bill_date=DAY, client_key=self.tag + 'na',
                        lines=[dict(source_item=line, qty=5, rate=110000, variance_reason='NCC tăng giá')])['invoice']
        second = as_user(ACC, si.create, receipts=[receipt.name], bill_no='NB-' + self.tag, bill_date=DAY, client_key=self.tag + 'nb',
                         lines=[dict(source_item=line, qty=5)])['invoice']
        back = p.return_receipt(receipt.name, DAY, {line: 2}, self.tag + 'ret', 1, 'Hỏng')
        self.assertAlmostEqual(invoice_cost._parked_claim(frappe._dict(name=line, parent=receipt.name)), -10000, delta=1)
        as_user(ACC, si.cancel, second, 'Nhập trùng')
        self.repost()
        self.assertAlmostEqual(invoice_cost._parked_claim(frappe._dict(name=line, parent=receipt.name)), 0, delta=1)
        kept = flt(frappe.db.sql("select sum(stock_value_difference) from `tabStock Ledger Entry` where voucher_no in %s and is_cancelled=0",
                                 ((receipt.name, back['name']),))[0][0])
        self.assertAlmostEqual(kept, 800000 + 50000, delta=2)
        waiting = queries.unbilled(C, DAY, self.supplier)['by_supplier'].get(self.supplier, 0)
        self.assertAlmostEqual(waiting, 300000, delta=1)
        self.assertAlmostEqual(self.clearing([receipt.name, back['name'], first, second]), waiting, delta=1)

    def test_47_billing_and_returned_labels_never_round_up(self):
        """A small line still waiting keeps the receipt in 'chờ hóa đơn' (99.99 % used to count as done), and everything of
        one line sent back is not 'Đã trả hết hàng' while another line is kept (quantities of different units)."""
        from lotus_farm.finance import supplier_invoice as si
        receipt = self.receive_all(self.order(lines=[dict(kind='Material', qty=20, rate=30000000), dict(kind='Tool', qty=1, rate=50000)]))
        big = next(r.name for r in receipt.items if r.item_code == 'PCT-M')
        as_user(ACC, si.create, receipts=[receipt.name], bill_no='BG-' + self.tag, bill_date=DAY, client_key=self.tag + 'bg', lines=[dict(source_item=big, qty=20)])
        self.assertLess(flt(frappe.db.get_value('Purchase Receipt', receipt.name, 'per_billed')), 99.99)
        self.assertIn(receipt.name, [r['name'] for r in as_user(ACC, si.queue, self.supplier)['rows']], 'the small line still waits')
        self.tag = uuid.uuid4().hex[:8]
        other = self.receive_all(self.order(lines=[dict(kind='Material', qty=20000, rate=1000), dict(kind='Tool', qty=2, rate=1000000)]))
        many = next(r.name for r in other.items if r.item_code == 'PCT-M')
        p.return_receipt(other.name, DAY, {many: 20000}, self.tag + 'ret', 1, 'Sai quy cách')
        self.assertNotEqual({r['name']: r for r in p.receipts(C)}[other.name]['billing'], 'Đã trả hết hàng')
        self.assertIn(other.name, [r['name'] for r in as_user(ACC, si.queue, self.supplier)['rows']], 'the 2 kept still wait for an invoice')

    def test_48_waiting_goods_include_mua_nhanh_price_corrections_and_match_finance(self):
        """A Mua nhanh price correction (Stock Reconciliation on 3388) waits with its entry; Tài chính › Đối chiếu shows the
        same figures as Mua hàng › Công nợ (3388 + 33881 against goods waiting)."""
        from lotus_farm import warehouse, procurement_queries as queries
        from lotus_farm.finance import reports
        group = frappe.db.get_value('Item', 'PCT-M', 'item_group')
        code = insert('Item', item_code='PCT-QC-' + self.tag, item_name='PCT QC ' + self.tag, item_group=group, stock_uom='Nos', is_stock_item=1,
                      is_purchase_item=1, valuation_rate=100000, item_defaults=[dict(company=C, default_warehouse=WH, expense_account=MAP['admin_expense'])]).name
        quick = warehouse.create_draft(C, 'receipt', DAY, [dict(item=code, qty=2, rate=100000)], target=WH, receipt_reason='Purchase',
                                       supplier=self.supplier, post=1, client_event_id=self.tag + 'qc')
        fix = frappe.get_doc(dict(doctype='Stock Reconciliation', company=C, purpose='Stock Reconciliation', posting_date=DAY,
                                  lotus_client_key='lotus-cost-of-receipt:%s:v1' % quick['name'],
                                  items=[dict(item_code=code, warehouse=WH, qty=2, valuation_rate=110000)]))
        fix.insert(ignore_permissions=True)
        fix.submit()
        self.assertAlmostEqual(queries.unbilled(C, DAY, self.supplier)['by_supplier'].get(self.supplier, 0), 220000, delta=1)
        self.assertAlmostEqual(self.clearing([quick['name'], fix.name]), 220000, delta=1)
        everything = queries.unbilled(C, DAY)
        check = next(c for c in reports.reconciliation(DAY)['checks'] if c['label'].startswith('Hàng về chưa có hóa đơn'))
        self.assertEqual((round(check['ledger']), round(check['source'])), (round(everything['ledger']), round(everything['total'])))

    def test_49_advance_room_counts_each_line_with_its_own_vat(self):
        """Line A 10 × 1.000.000 at 10 %, line B 10 × 1.000.000 without VAT; A invoiced in full. What is left to invoice is
        B's 10.000.000, not half of the 21.000.000 total."""
        from lotus_farm.finance import supplier_invoice as si
        order = self.order(lines=[dict(kind='Material', qty=10, rate=1000000, vat='10'), dict(kind='Tool', qty=10, rate=1000000, vat='KCT')])
        receipt = self.receive_all(order)
        a = next(r.name for r in receipt.items if r.item_code == 'PCT-M')
        as_user(ACC, si.create, receipts=[receipt.name], bill_no='MV-' + self.tag, bill_date=DAY, client_key=self.tag + 'mv', lines=[dict(source_item=a, qty=10)])
        self.assertAlmostEqual(funding._remaining_source('Purchase Order', order.name, lock_rows=False), 10000000, delta=1)

    def test_50_asset_invoiced_before_its_rate_ended_and_one_rate_for_the_invoice(self):
        """(1) Ordered at 8 %, invoiced while 8 % was in force, received after it ended (the receipt then carries 10 %): the
        invoice keeps 8 % and the 2 % the receipt capitalised in excess comes back from expense; 33881 returns to zero.
        (2) One VAT rate for the whole invoice (Tài chính › Chờ hạch toán) on a household receipt without VAT: accepted,
        the VAT goes into the cost."""
        from lotus_farm.finance import rules as finance_rules, supplier_invoice as si
        self.household()
        earlier, yesterday = add_days(DAY, -2), add_days(DAY, -1)
        asset = self.order(kind='Asset', qty=1, rate=10000000, vat='8')
        frappe.db.set_value('Purchase Order', asset.name, 'transaction_date', earlier)
        data = finance_rules.load_vat()
        next(r for r in data['rates'] if r['code'] == '8')['to'] = yesterday
        with patch.object(finance_rules, 'load_vat', return_value=data):
            piece = self.receive(asset, 1)
            self.assertEqual(piece.items[0].lotus_line_vat, '10')
            result = as_user(CHIEF, si.create, receipts=[piece.name], bill_no='T8-' + self.tag, bill_date=earlier, posting_date=DAY,
                             client_key=self.tag + 't8', lines=[dict(source_item=piece.items[0].name, qty=1, vat_code='8')])
            made = as_user(ACC, si.detail, result['invoice'])['cost_adjustments']
        self.assertEqual([(r['doctype'], r['kind'], r['amount']) for r in made], [('Journal Entry', 'expense', -200000)])
        self.assertAlmostEqual(self.ledger(setup.valuation_tax_account(C), [piece.name, result['invoice'], made[0]['name']]), 0, delta=1, msg='33881')
        self.tag = uuid.uuid4().hex[:8]
        plain = self.receive(self.order(qty=10, rate=100000, vat='KCT'), 10)
        goods = as_user(ACC, payments.make_goods_invoice, [plain.name], 'HV-' + self.tag, DAY, None, None, '10')
        self.repost()
        self.assertAlmostEqual(self.clearing([plain.name, goods['invoice']]), 0, delta=1)
        self.assertAlmostEqual(flt(frappe.db.get_value('Purchase Receipt Item', plain.items[0].name, 'valuation_rate')), 110000, delta=1)

    def test_51_every_kind_of_closed_books_is_recognised(self):
        """Stock Closing Entry, Lotus result closing and the Company frozen date each make _closed() answer, so the
        difference goes to expense instead of a voucher ERPNext would refuse."""
        from lotus_farm.finance import invoice_cost, posting
        entry = frappe.get_doc(dict(doctype='Stock Closing Entry', company=C, from_date=add_days(DAY, -30), to_date=DAY, status='Completed'))
        entry.name = 'PCT-SCE-' + self.tag
        entry.docstatus = 1
        entry.db_insert()
        self.assertIn('kho đã khóa', invoice_cost._closed(C, DAY) or '')
        frappe.db.delete('Stock Closing Entry', {'name': entry.name})
        closing = frappe.get_doc(dict(doctype=posting.POSTING, company=C, source_doctype=setup.SETTINGS, source_name=setup.SETTINGS, purpose='Result Closing',
                                      voucher_type='Journal Entry', voucher_name='PCT-RC2-' + self.tag, posting_date=DAY, state='Posted',
                                      active_key=posting.active_key(setup.SETTINGS, setup.SETTINGS, 'Result Closing', DAY[:7])))
        closing.name = 'PCT-RC2-' + self.tag
        closing.db_insert()
        self.assertIn('đã kết chuyển', invoice_cost._closed(C, DAY) or '')
        frappe.db.delete(posting.POSTING, {'name': closing.name})
        self.frozen(DAY)
        self.assertIn('sổ đã khóa', invoice_cost._closed(C, DAY) or '')

    def test_41_buying_settings_keep_the_lotus_switches_off(self):
        settings = frappe.get_single('Buying Settings')
        settings.set_landed_cost_based_on_purchase_invoice_rate = 1
        self.assertIn('hai lần', self.refused(settings.save))

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
