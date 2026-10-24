"""Direct warehouse receipt regression; disposable procurement.test only."""
import unittest
import frappe
from frappe.utils import flt
import verify_procurement as base
from lotus_farm import warehouse


class ReceiptReason(base.ProcurementIntegration):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not frappe.db.exists('Stock Entry Type','Material Receipt'):
            base.insert('Stock Entry Type',name='Material Receipt',purpose='Material Receipt',is_standard=1)
        frappe.db.commit()

    def draft(self, reason=None, supplier=None, area='', event=None):
        return warehouse.create_draft(base.C,'receipt',base.DAY,
            [dict(item='PCT-M',qty=1,uom='Nos',rate=100000,area=area)],
            target=base.WH,receipt_reason=reason,supplier=supplier,client_event_id=event or self.tag)

    def credit(self, result, account):
        doc=frappe.get_doc(result['doctype'],result['name'])
        warehouse.submit_document(doc.doctype,doc.name,str(doc.modified))
        self.assertEqual(frappe.db.get_value('Stock Entry',doc.name,'docstatus'),1)
        self.assertEqual(flt(frappe.db.get_value('GL Entry',dict(voucher_type='Stock Entry',voucher_no=doc.name,account=account),'credit')),100000)
        return doc

    def test_receipt_reason_purchase_persists_and_retry_cannot_change_accounting(self):
        with self.assertRaisesRegex(frappe.ValidationError,'lý do nhập kho'):
            self.draft()
        with self.assertRaisesRegex(frappe.ValidationError,'nhà cung cấp'):
            self.draft('Purchase')
        result=self.draft('Purchase',self.supplier)
        self.assertEqual(self.draft('Purchase',self.supplier)['name'],result['name'])
        with self.assertRaisesRegex(frappe.ValidationError,'Yêu cầu này đã tạo phiếu'):
            self.draft('Surplus',self.supplier)
        with self.assertRaisesRegex(frappe.ValidationError,'Yêu cầu này đã tạo phiếu'):
            self.draft('Purchase','PCT Supplier')
        doc=self.credit(result,base.MAP['received_not_billed'])
        self.assertEqual(doc.lotus_supplier,self.supplier)

    def test_receipt_reason_recovery_credits_the_source_lot(self):
        code='PCT-REC-'+self.tag
        farm=frappe.db.get_value('Farm',{'farm_code':'PCT-FARM'},'name')
        block=base.insert('Farm Block',farm=farm,block_name=code,block_code=code,area_ha=1,active=1)
        result=self.draft('Recovery',area=code)
        doc=self.credit(result,base.MAP['material_cost'])
        gl=frappe.db.get_value('GL Entry',dict(voucher_type='Stock Entry',voucher_no=doc.name,account=base.MAP['material_cost']),['lotus_farm','lotus_farm_block'],as_dict=True)
        self.assertEqual(gl.lotus_farm,farm)
        self.assertEqual(gl.lotus_farm_block,block.name)

    def test_receipt_reason_surplus_does_not_require_purchase_order(self):
        result=self.draft('Surplus')
        doc=self.credit(result,base.MAP['stock_adjustment'])
        self.assertFalse(doc.lotus_supplier)


if __name__=='__main__':
    try: unittest.main(verbosity=2)
    finally:
        frappe.db.rollback();frappe.destroy()
