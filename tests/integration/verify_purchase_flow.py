"""Four-step purchasing UAT. Uses only the isolated procurement.test stack."""
import json
import unittest
from io import BytesIO
from unittest.mock import patch

import frappe
from PIL import Image, ImageDraw
import verify_procurement as base
from lotus_farm import purchase_proposal as pp, purchasing, purchase_flow, signing


class PurchaseFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base.seed()
        frappe.conf.lotus_purchase_flow_company = base.C
        pp.install_fields()
        frappe.get_doc('User', base.BUYER).add_roles('Lotus Purchase Requester')
        frappe.db.commit()
        frappe.conf.lotus_purchase_flow_company = None
        cls.image = BytesIO()
        image = Image.new('RGB', (200, 70), 'white')
        ImageDraw.Draw(image).line([(10, 50), (70, 15), (100, 55), (190, 20)], fill='black', width=3)
        image.save(cls.image, format='PNG')

    def setUp(self):
        base.ProcurementIntegration.setUp(self)
        self.old_company = frappe.conf.get('lotus_purchase_flow_company')
        frappe.conf.lotus_purchase_flow_company = base.C
        self.signature = patch('lotus_farm.digital_signature.signature_image_bytes', return_value=self.image.getvalue())
        self.signature.start()

    def tearDown(self):
        frappe.conf.lotus_purchase_flow_company = self.old_company
        self.signature.stop()
        base.ProcurementIntegration.tearDown(self)

    def proposal(self, qty=10, rate=100000, item='PCT-M', approve=True):
        d = base.as_user(base.BUYER, pp.save_proposal, base.C, dict(reason='Mua dự trữ độc lập', department='Kho', warehouse=base.WH,
            items=[dict(item_code=item, qty=qty, rate=rate, uom='Nos', schedule_date=base.DAY)]))
        if approve:
            d = base.as_user(base.BUYER, pp.sign, d['name'], d['modified'],
                             dict(DEPARTMENT=base.LEADER, PURCHASING=base.ACC, APPROVE=base.DIR))
            for user in (base.LEADER, base.ACC, base.DIR):
                d = base.as_user(user, pp.sign, d['name'], d['modified'])
        return d

    def order(self, qty=10, proposal=None):
        d = proposal or self.proposal(qty=qty)
        data = dict(supplier=self.supplier, warehouse=base.WH, expected_date=base.DAY, mode='Kho tự mua',
            items=[dict(item='PCT-M', qty=qty, rate=100000, uom='Nos', kind='Material', vat_code='KCT',
                        material_request=d['name'], material_request_item=d['items'][0]['name'])])
        saved = base.as_user(base.BUYER, base.buying.save_order, base.C, data)
        order = frappe.get_doc('Purchase Order', saved['name'])
        base.as_user(base.BUYER, purchasing.request_approval, order.name, str(order.modified), base.DIR)
        order.reload()
        base.as_user(base.DIR, purchasing.approve_order, order.name, str(order.modified))
        return frappe.get_doc('Purchase Order', order.name)

    receive = base.ProcurementIntegration.receive
    invoice = base.ProcurementIntegration.invoice

    def test_01_all_values_and_unknown_price_require_four_signatures(self):
        for rate in (0, 100000, 2500000):
            d = self.proposal(rate=rate)
            self.assertEqual(d['docstatus'], 1)
            self.assertEqual(len(d['signatures']), 4)
            self.assertTrue(all(s['state'] == 'Đã ký' for s in d['signatures']))

    def test_02_generic_submit_and_old_api_cannot_approve(self):
        d = base.as_user(base.BUYER, purchasing.create_request, base.C, base.WH, base.DAY,
                         [dict(item='PCT-M', qty=2, uom='Nos')], 'Mua dự trữ')
        self.assertEqual(d['docstatus'], 0)
        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc('Material Request', d['name']).submit()
        with self.assertRaises(frappe.ValidationError):
            base.receiving.purchase_action(d['name'], d['modified'], 'submit')

    def test_03_wrong_signer_stale_version_and_changed_content(self):
        d = self.proposal(approve=False)
        d = base.as_user(base.BUYER, pp.sign, d['name'], d['modified'], dict(DEPARTMENT=base.LEADER, PURCHASING=base.ACC, APPROVE=base.DIR))
        with self.assertRaises(frappe.PermissionError):
            base.as_user(base.ACC, pp.sign, d['name'], d['modified'])
        with self.assertRaises(frappe.PermissionError):
            pp.sign(d['name'], d['modified'])
        native = frappe.get_doc('Material Request', d['name'])
        native.lotus_request_note = 'Nội dung khác sau ký'
        with self.assertRaises(frappe.ValidationError):
            native.save()
        updated = base.as_user(base.LEADER, pp.sign, d['name'], d['modified'])
        with self.assertRaises(frappe.ValidationError):
            base.as_user(base.ACC, pp.sign, updated['name'], d['modified'])

    def test_04_price_edit_returns_and_restarts_every_signature(self):
        d = self.proposal(rate=0, approve=False)
        d = base.as_user(base.BUYER, pp.sign, d['name'], d['modified'], dict(DEPARTMENT=base.LEADER, PURCHASING=base.ACC, APPROVE=base.DIR))
        d = base.as_user(base.LEADER, pp.sign, d['name'], d['modified'])
        values = dict(reason=d['reason'], warehouse=base.WH, items=[dict(r, rate=100000) for r in d['items']])
        d = base.as_user(base.ACC, pp.save_proposal, base.C, values, d['name'], d['modified'])
        self.assertEqual(d['state'], 'Trả lại')
        self.assertEqual(d['step'], 0)
        self.assertEqual(len(signing._rows(frappe.get_doc('Material Request', d['name']))[0]), 4)
        d = base.as_user(base.BUYER, pp.sign, d['name'], d['modified'], d['signers'])
        for user in (base.LEADER, base.ACC, base.DIR):
            d = base.as_user(user, pp.sign, d['name'], d['modified'])
        self.assertEqual(d['docstatus'], 1)
        self.assertEqual(signing._rows(frappe.get_doc('Material Request', d['name']))[1], 2)

    def test_05_split_order_partial_receipt_invoice_payment_trace(self):
        proposal = self.proposal(qty=10)
        order = self.order(6, proposal)
        other = self.order(4, proposal)
        receipt = self.receive(order, 2)
        inv = self.invoice(receipt)
        pending = base.as_user(base.ACC, base.payments.receipts_to_bill)
        self.assertFalse(any(r['name'] == receipt.name for r in pending))
        voucher = base.as_user(base.ACC, base.p.supplier_payment, base.C, 'Purchase Invoice', inv.name, 100000, 'cash', base.DAY,
                               dict(CHIEF=base.CHIEF, APPROVE=base.DIR), self.tag+'pay')
        base.signed(voucher)
        info = base.as_user(base.ACC, pp.detail, proposal['name'])['progress']
        self.assertEqual(info['lines'][0]['ordered_qty'], 10)
        self.assertEqual(info['lines'][0]['received_qty'], 2)
        self.assertEqual(info['lines'][0]['remaining_receive_qty'], 8)
        self.assertEqual(info['outstanding_amount'], 100000)
        self.assertEqual({r['name'] for r in info['orders']}, {order.name, other.name})
        self.assertEqual(info['payments'][0]['name'], voucher['voucher'])
        self.assertEqual(base.p.chain(order.name)['proposals'][0]['name'], proposal['name'])

    def test_06_unapproved_and_overordered_sources_refused(self):
        d = self.proposal(approve=False)
        with self.assertRaises(frappe.ValidationError):
            self.order(1, d)
        d = self.proposal(qty=2)
        self.order(2, d)
        with self.assertRaises(frappe.ValidationError):
            self.order(1, d)

    def test_07_other_company_retains_previous_policy(self):
        self.assertFalse(purchase_flow.enabled('Đại Minh Lộc'))
        frappe.conf.lotus_purchase_flow_company = None
        d = self.proposal(qty=1, approve=False)
        options = base.as_user(base.BUYER, pp.signer_options, base.C, d['name'])
        self.assertEqual(len(options['steps']), 2)

    def test_08_legacy_round_preserved_and_replaced(self):
        frappe.conf.lotus_purchase_flow_company = None
        d = self.proposal(qty=1, approve=False)
        d = base.as_user(base.BUYER, pp.sign, d['name'], d['modified'], dict(DEPARTMENT=base.LEADER))
        frappe.conf.lotus_purchase_flow_company = base.C
        d = base.as_user(base.LEADER, pp.sign, d['name'], d['modified'])
        self.assertEqual(d['state'], 'Trả lại')
        self.assertEqual(signing._rows(frappe.get_doc('Material Request', d['name']))[1], 1)
        d = base.as_user(base.BUYER, pp.sign, d['name'], d['modified'], dict(DEPARTMENT=base.LEADER, PURCHASING=base.ACC, APPROVE=base.DIR))
        self.assertEqual(len(d['signatures']), 4)
        for user in (base.LEADER, base.ACC, base.DIR):
            d = base.as_user(user, pp.sign, d['name'], d['modified'])
        self.assertEqual(d['docstatus'], 1)


if __name__ == '__main__':
    try:
        unittest.main(verbosity=2)
    finally:
        frappe.db.rollback()
        frappe.destroy()
