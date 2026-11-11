"""Whole-workspace UAT; inherits the existing sixteen native purchase regressions."""
import json
import unittest
import uuid
import frappe
import verify_procurement as base
from lotus_farm import procurement_masters as masters, procurement_queries as queries, procurement_adjustments as adjustments
from frappe.utils import flt, add_days


class CompleteProcurement(base.ProcurementIntegration):
    def test_17_supplier_full_profile_shared_links_and_idempotency(self):
        values=dict(supplier_name='PCT Profile '+self.tag,type='Company',group=frappe.db.get_value('Supplier',self.supplier,'supplier_group'),
                    country='Vietnam',tax_id='PCT-'+self.tag,contact='Test Contact',phone='0901234567',email=self.tag+'@example.invalid',
                    address_line1='Test address',city='Test city',notes='Profile')
        r=base.as_user(base.BUYER,masters.save,base.C,'suppliers',values,self.tag)
        again=base.as_user(base.BUYER,masters.save,base.C,'suppliers',values,self.tag)
        self.assertEqual(r['name'],again['name'])
        self.assertEqual(r['phone'],'0901234567');self.assertEqual(r['email'],values['email'])
        d=frappe.get_doc('Supplier',r['name'])
        self.assertTrue(d.supplier_primary_contact);self.assertTrue(d.supplier_primary_address)
        with self.assertRaises(frappe.ValidationError):
            base.as_user(base.BUYER,masters.save,base.C,'suppliers',{**values,'notes':'changed'},self.tag)
        page=base.as_user(base.BUYER,masters.listing,base.C,'suppliers',search=values['supplier_name'],page_length=1)
        self.assertEqual(page['total_count'],1)
        changed={**r,'phone':'0909999999','supplier_name':d.supplier_name}
        updated=base.as_user(base.BUYER,masters.save,base.C,'suppliers',changed,self.tag+'edit',name=d.name,modified=r['modified'])
        self.assertEqual(updated['phone'],'0909999999')
        with self.assertRaises(frappe.ValidationError):
            base.as_user(base.BUYER,masters.save,base.C,'suppliers',changed,self.tag+'stale',name=d.name,modified=r['modified'])

    def test_18_supplier_bank_write_boundary(self):
        r=masters.detail(base.C,'suppliers',self.supplier)
        values={**r,'bank_account_no':'123456','bank':'Test bank'}
        with self.assertRaises(frappe.PermissionError):
            base.as_user(base.BUYER,masters.save,base.C,'suppliers',values,self.tag,name=r['name'],modified=r['modified'])

    def test_19_item_four_kinds_and_repeat_request(self):
        for kind in ('Material','Tool','Asset','Service'):
            values=dict(item_code='PCT-New-'+kind+'-'+self.tag,item_name=kind+' '+self.tag,kind=kind,uom='Nos',
                group=frappe.db.get_value('Item','PCT-M','item_group'),conversions=[dict(uom='Nos',conversion_factor=1)])
            if kind=='Asset': values['asset_category']=frappe.db.get_value('Item','PCT-A','asset_category')
            r=base.as_user(base.BUYER,masters.save,base.C,'items',values,self.tag+kind)
            self.assertEqual(r['kind'],kind)
            self.assertEqual(base.as_user(base.BUYER,masters.save,base.C,'items',values,self.tag+kind)['name'],r['name'])
            with self.assertRaises(frappe.ValidationError):
                base.as_user(base.BUYER,masters.save,base.C,'items',{**r,'uom':'Kg'},self.tag+'change',name=r['name'],modified=r['modified'])

    def test_20_invoices_payment_history_and_asof_payables(self):
        inv=self.invoice(self.receive(self.order(),10))
        page=base.as_user(base.ACC,queries.invoices,base.C,supplier=self.supplier,page_length=1)
        self.assertEqual(page['rows'][0]['name'],inv.name)
        self.assertEqual(base.as_user(base.ACC,queries.invoice,base.C,inv.name)['items'][0]['receipt'],inv.items[0].purchase_receipt)
        before=base.as_user(base.ACC,queries.payables,base.C,as_of=base.DAY,supplier=self.supplier)
        self.assertEqual(before['net'],1000000)
        v=base.as_user(base.ACC,base.p.supplier_payment,base.C,'Purchase Invoice',inv.name,200000,'cash',add_days(base.DAY,1),{'CHIEF':base.CHIEF,'APPROVE':base.DIR},self.tag)
        waiting=base.as_user(base.ACC,queries.payments,base.C,supplier=self.supplier,state='0')
        self.assertEqual(waiting['total_count'],1)
        base.signed(v)
        self.assertEqual(base.as_user(base.ACC,queries.payments,base.C,supplier=self.supplier,state='1')['total_count'],1)
        self.assertEqual(base.as_user(base.ACC,queries.payables,base.C,as_of=base.DAY,supplier=self.supplier)['net'],1000000)
        self.assertEqual(base.as_user(base.ACC,queries.payables,base.C,as_of=add_days(base.DAY,1),supplier=self.supplier)['net'],800000)
        with self.assertRaises(frappe.PermissionError):
            base.as_user(base.BUYER,queries.invoices,base.C)

    def test_21_native_credit_note_and_signed_refund(self):
        inv=self.invoice(self.receive(self.order(),10))
        paid=base.as_user(base.ACC,base.p.supplier_payment,base.C,'Purchase Invoice',inv.name,1000000,'cash',base.DAY,{'CHIEF':base.CHIEF,'APPROVE':base.DIR},self.tag+'paid')
        base.signed(paid)
        credit=base.as_user(base.ACC,adjustments.credit_note,base.C,inv.name,base.DAY,{inv.items[0].name:2},self.tag+'credit',bill_no='CN-'+self.tag)
        cn=frappe.get_doc('Purchase Invoice',credit['invoice'])
        self.assertEqual(cn.update_stock,0);self.assertEqual(cn.return_against,inv.name)
        refund=base.as_user(base.ACC,adjustments.refund,base.C,cn.name,200000,'cash',base.DAY,'',{'CHIEF':base.CHIEF,'APPROVE':base.DIR},self.tag+'refund')
        d=frappe.get_doc('Payment Entry',refund['voucher'])
        self.assertEqual(d.payment_type,'Receive')
        d.lotus_procurement_key=None
        d.lotus_procurement_hash=None
        with self.assertRaises(frappe.ValidationError): d.submit()
        base.signed(refund)
        self.assertEqual(flt(frappe.db.get_value('Purchase Invoice',cn.name,'outstanding_amount')),0)
        report=base.as_user(base.ACC,base.reports.report,base.C,month=base.DAY[:7],as_of=base.DAY,supplier=self.supplier,kind='Material')
        self.assertEqual(report['totals']['company_cash'],800000)

    def test_22_receiver_without_buying_write_can_receive(self):
        order=self.order()
        actor=base.user('receiver',['Lotus Warehouse Receiver'])
        result=base.as_user(actor,base.receiving.receive_order,order.name,base.DAY,{order.items[0].name:1},self.tag+'receiver')
        self.assertTrue(result['name'])

    def test_23_accountant_bank_profile_and_buyer_redaction(self):
        bank='PCT Bank'
        if not frappe.db.exists('Bank',bank): base.insert('Bank',bank_name=bank)
        original=masters.detail(base.C,'suppliers',self.supplier)
        values={**original,'bank':bank,'bank_account_no':str(int(self.tag,16)).zfill(10),'bank_account_name':'PCT Account '+self.tag}
        saved=base.as_user(base.ACC,masters.save,base.C,'suppliers',values,self.tag+'bank',name=self.supplier,modified=original['modified'])
        self.assertEqual(saved['bank_account_no'],values['bank_account_no'])
        buyer=base.as_user(base.BUYER,masters.detail,base.C,'suppliers',self.supplier)
        self.assertNotIn('bank_account_no',buyer)

    def test_24_billing_source_exposes_only_unbilled_quantity(self):
        receipt=self.receive(self.order(qty=4),4)
        base.as_user(base.ACC,base.p.invoice_receipt,receipt.name,'PART-'+self.tag,base.DAY,base.DAY,self.tag,
            quantities={receipt.items[0].name:1})
        source=base.as_user(base.ACC,base.p.billing_source,base.C,receipt.name)
        self.assertEqual(source['items'][0]['remaining_qty'],3)

    def test_25_new_master_items_complete_all_four_purchase_flows(self):
        for kind in ('Material','Tool','Asset','Service'):
            with self.subTest(kind=kind):
                self.tag=uuid.uuid4().hex[:8]
                values=dict(item_code='PCT-Flow-'+self.tag,item_name='PCT '+kind,kind=kind,uom='Nos',
                    group=frappe.db.get_value('Item','PCT-M','item_group'),conversions=[dict(uom='Nos',conversion_factor=1)])
                if kind=='Asset':values['asset_category']=frappe.db.get_value('Item','PCT-A','asset_category')
                item=base.as_user(base.BUYER,masters.save,base.C,'items',values,self.tag+'item')
                data=dict(supplier=self.supplier,warehouse=base.WH,expected_date=base.DAY,mode='Kho tự mua',
                    items=[dict(item=item['name'],qty=1,rate=100000,uom='Nos',kind=kind,vat_code='KCT')])
                created=base.as_user(base.BUYER,base.buying.save_order,base.C,data)
                order=frappe.get_doc('Purchase Order',created['name'])
                base.as_user(base.BUYER,base.purchasing.request_approval,order.name,str(order.modified),base.DIR)
                order.reload();base.as_user(base.DIR,base.purchasing.approve_order,order.name,str(order.modified))
                order.reload();invoice=self.invoice(self.receive(order,1))
                self.assertEqual(invoice.docstatus,1)
                self.assertEqual(invoice.items[0].item_code,item['name'])

    def test_26_cancelled_payment_remains_visible_after_new_attempt(self):
        invoice=self.invoice(self.receive(self.order(),10))
        first=base.as_user(base.ACC,base.p.supplier_payment,base.C,'Purchase Invoice',invoice.name,100000,'cash',base.DAY,{'CHIEF':base.CHIEF,'APPROVE':base.DIR},self.tag+'old')
        base.as_user(base.ACC,base.payments.cancel_draft,'Payment Entry',first['voucher'],'PCT cancel attempt')
        base.as_user(base.ACC,base.p.supplier_payment,base.C,'Purchase Invoice',invoice.name,100000,'cash',base.DAY,{'CHIEF':base.CHIEF,'APPROVE':base.DIR},self.tag+'new')
        history=base.as_user(base.ACC,queries.payments,base.C,supplier=self.supplier,state='2')
        cancelled=[r for r in history['rows'] if r.get('voucher_name')==first['voucher']]
        self.assertEqual(len(cancelled),1)
        self.assertTrue(cancelled[0]['audit_only'])
        self.assertEqual(cancelled[0]['reason'],'PCT cancel attempt')


    # ---- Spec 003 · US6: payables on a closing date, supplier statement, one payment voucher for several invoices ----
    def test_30_payables_statement_and_one_voucher_for_several_invoices(self):
        from lotus_farm.finance import supplier_invoice as si, supplier_payment as sp, posting
        from lotus_farm.www import lotus_payment_print, lotus_statement_print
        from lotus_farm import print_kit
        C, DAY, ACC, CHIEF, DIR = base.C, base.DAY, base.ACC, base.CHIEF, base.DIR
        first = self.receive(self.order(qty=10, rate=100000), 10)
        a = base.as_user(ACC, si.create, receipts=[first.name], bill_no='A-' + self.tag, bill_date=DAY, due_date=add_days(DAY, 5), client_key=self.tag + 'a')
        tag = self.tag
        self.tag = uuid.uuid4().hex[:8]
        second = self.receive(self.order(qty=5, rate=100000), 5)
        b = base.as_user(ACC, si.create, receipts=[second.name], bill_no='B-' + tag, bill_date=DAY, due_date=add_days(DAY, 20), client_key=tag + 'b')
        self.tag = uuid.uuid4().hex[:8]
        waiting = self.receive(self.order(qty=2, rate=100000), 2)  # received, not invoiced
        now = base.as_user(ACC, queries.payables, C, DAY, self.supplier)
        mine = next(s for s in now['suppliers'] if s['supplier'] == self.supplier)
        self.assertEqual((mine['invoiced'], mine['aging']['current'], mine['due_7d'], mine['unbilled']), (1500000, 1500000, 1000000, 200000))
        self.assertEqual((now['aging']['current'], now['due_7d'], now['unbilled'], now['ledger_matches']), (1500000, 1000000, 200000, True))
        self.assertEqual(base.as_user(ACC, queries.unbilled, C, DAY, self.supplier)['rows'][0]['name'], waiting.name)
        later = base.as_user(ACC, queries.payables, C, add_days(DAY, 45), self.supplier)
        self.assertEqual((later['aging']['d31_60'], later['aging']['d1_30'], later['aging']['current'], later['due_7d']), (1000000, 500000, 0, 0))
        soon = base.as_user(ACC, queries.due_soon, C, DAY)
        self.assertIn(a['invoice'], [r['name'] for r in soon['rows']])
        self.assertNotIn(b['invoice'], [r['name'] for r in soon['rows']])
        # One voucher: two invoices and an advance; nothing above what is owed unless it is called an advance.
        items = base.as_user(ACC, sp.open_items, self.supplier)
        self.assertEqual({i['name']: i['payable'] for i in items['items'] if i['doctype'] == 'Purchase Invoice'}, {a['invoice']: 1000000, b['invoice']: 500000})
        signers = dict(CHIEF=CHIEF, APPROVE=DIR)
        frappe.db.savepoint('over_pay')
        with self.assertRaises(frappe.ValidationError) as over:
            base.as_user(ACC, sp.prepare, supplier=self.supplier, allocations=[dict(doctype='Purchase Invoice', name=b['invoice'], amount=600000)],
                         mode='cash', posting_date=DAY, signers=signers, client_key=tag + 'over')
        frappe.db.rollback(save_point='over_pay')
        self.assertIn('tạm ứng', str(over.exception))
        args = dict(supplier=self.supplier, advance_amount=100000, mode='bank', reference_no='UNC-' + tag, posting_date=DAY, signers=signers,
                    allocations=[dict(doctype='Purchase Invoice', name=a['invoice'], amount=400000), dict(doctype='Purchase Invoice', name=b['invoice'], amount=500000)])
        voucher = base.as_user(ACC, sp.prepare, client_key=tag + 'pay', **args)
        self.assertEqual(base.as_user(ACC, sp.prepare, client_key=tag + 'pay', **args)['voucher'], voucher['voucher'], 'the same request makes one voucher')
        draft = frappe.get_doc('Payment Entry', voucher['voucher'])
        self.assertEqual((flt(draft.paid_amount), draft.docstatus, len(draft.references)), (1000000, 0, 2))
        self.assertEqual(next(i['payable'] for i in base.as_user(ACC, sp.open_items, self.supplier)['items'] if i['name'] == a['invoice']), 600000,
                         'a voucher waiting for signatures holds its amount')
        page = base.as_user(ACC, lambda: str(lotus_payment_print.html(draft)))
        for text in ('GIẤY ĐỀ NGHỊ CHI', 'UNC-' + tag, 'Hóa đơn A-' + tag, 'Tạm ứng cho nhà cung cấp'):
            self.assertIn(text, page)
        base.signed(voucher)
        self.assertEqual(frappe.db.get_value('Payment Entry', voucher['voucher'], 'docstatus'), 1)
        self.assertTrue(frappe.db.exists('Lotus Signed Copy', {'document_type': 'Payment Entry', 'document_name': voucher['voucher']}),
                        'the signed voucher keeps its PDF')
        self.assertEqual([flt(frappe.db.get_value('Purchase Invoice', n, 'outstanding_amount')) for n in (a['invoice'], b['invoice'])], [600000, 0])
        info = base.as_user(ACC, base.p.voucher, 'Payment Entry', voucher['voucher'])
        self.assertEqual((info['mode'], info['unallocated'], bool(info['signed_copy']), bool(info['posting']), info['can_reverse']), ('bank', 100000, True, True, False))
        statement = base.as_user(ACC, queries.supplier_statement, C, self.supplier, DAY, DAY)
        self.assertEqual((statement['opening'], statement['credit'], statement['debit'], statement['closing'], statement['ledger_matches']),
                         (0, 1500000, 1000000, 500000, True))
        self.assertEqual(sorted(l['kind'] for l in statement['lines']), ['invoice', 'invoice', 'payment'])
        sheet = base.as_user(ACC, lambda: str(print_kit.render('statement.html', lotus_statement_print.build(self.supplier, DAY, DAY))))
        self.assertIn('BIÊN BẢN ĐỐI CHIẾU CÔNG NỢ', sheet)
        after = next(s for s in base.as_user(ACC, queries.payables, C, DAY, self.supplier)['suppliers'] if s['supplier'] == self.supplier)
        self.assertEqual((after['invoiced'], after['advance'], after['net']), (600000, 100000, 500000))
        # Only the chief accountant reverses a posted voucher.
        frappe.db.savepoint('reverse_try')
        with self.assertRaises(frappe.PermissionError):
            base.as_user(ACC, posting.reverse, info['posting'], 'Chi nhầm nhà cung cấp')
        frappe.db.rollback(save_point='reverse_try')
        base.as_user(CHIEF, posting.reverse, info['posting'], 'Chi nhầm nhà cung cấp')
        self.assertEqual([flt(frappe.db.get_value('Purchase Invoice', n, 'outstanding_amount')) for n in (a['invoice'], b['invoice'])], [1000000, 500000])


if __name__=='__main__':
    try: unittest.main(verbosity=2)
    finally:
        frappe.db.rollback();frappe.destroy()
