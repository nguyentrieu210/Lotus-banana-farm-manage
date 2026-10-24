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


if __name__=='__main__':
    try: unittest.main(verbosity=2)
    finally:
        frappe.db.rollback();frappe.destroy()
