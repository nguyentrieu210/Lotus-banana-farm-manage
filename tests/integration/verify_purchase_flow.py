"""Four-step purchasing UAT. Uses only the isolated procurement.test stack."""
import json
import unittest
from io import BytesIO
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

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
        for purpose in ('Material Receipt', 'Material Issue'):
            if not frappe.db.exists('Stock Entry Type', purpose):
                base.insert('Stock Entry Type', name=purpose, purpose=purpose)
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
        self.assertTrue(base.receiving.purchase_request(d['name'])['proposal_url'].startswith('/lotus/mua-hang?'))
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

    def test_09_quick_purchase_reaches_accounting_without_duplicate_stock(self):
        from lotus_farm import warehouse
        result = warehouse.create_draft(base.C, 'receipt', base.DAY, [dict(item='PCT-M', qty=2, rate=100000)],
            target=base.WH, receipt_reason='Purchase', supplier=self.supplier, post=1, client_event_id=self.tag+'quick')
        self.assertEqual(result['docstatus'], 1)
        pending = base.as_user(base.ACC, base.payments.receipts_to_bill)
        row = next(r for r in pending if r['name'] == result['name'])
        self.assertEqual(row['unbilled_items'][0]['qty'], 2)
        self.assertIn('Mua nhanh', row['source_type'])
        invoice = base.as_user(base.ACC, base.payments.make_goods_invoice, [result['name']], 'QUICK-'+self.tag, base.DAY)
        self.assertEqual(frappe.db.count('Stock Ledger Entry', {'voucher_no': invoice['invoice']}), 0)
        self.assertEqual(frappe.db.get_value('Stock Entry', result['name'], 'lotus_purchase_invoice'), invoice['invoice'])

    def test_10_duplicate_signature_requests_advance_only_once(self):
        d = self.proposal(approve=False)
        d = base.as_user(base.BUYER, pp.sign, d['name'], d['modified'], dict(DEPARTMENT=base.LEADER, PURCHASING=base.ACC, APPROVE=base.DIR))
        frappe.db.commit()  # Separate connections need committed fixtures, only on this disposable site.
        barrier = Barrier(2)

        def worker():
            frappe.init(site='procurement.test', sites_path='/home/frappe/frappe-bench/sites')
            frappe.connect()
            frappe.conf.lotus_purchase_flow_company = base.C
            frappe.set_user(base.LEADER)
            try:
                barrier.wait(timeout=10)
                pp.sign(d['name'], d['modified'])
                frappe.db.commit()
                return 'signed'
            except frappe.ValidationError:
                frappe.db.rollback()
                return 'stale'
            finally:
                frappe.destroy()

        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                outcomes = list(pool.map(lambda _: worker(), range(2)))
            self.assertEqual(sorted(outcomes), ['signed', 'stale'])
            rows, _ = signing._rows(frappe.get_doc('Material Request', d['name']))
            self.assertEqual([r.state for r in rows], ['Đã ký', 'Đã ký', 'Chờ ký', 'Chưa đến lượt'])
        finally:
            frappe.db.rollback()
            frappe.db.savepoint('purchase_case')

    def test_11_work_demand_is_reference_until_actual_issue(self):
        from lotus_farm import warehouse
        from lotus_farm.warehouse_planning import source_allocations
        farm = frappe.db.get_value('Farm', {'farm_code': 'PCT-FARM'}, 'name')
        block = base.insert('Farm Block', farm=farm, block_name='Flow '+self.tag, block_code='F'+self.tag, area_ha=1, active=1)
        category = base.insert('Work Category', category_code=self.tag, category_name='Flow '+self.tag, active=1)
        work = base.insert('Work Type', work_code=self.tag, work_name='Flow '+self.tag, category=category.name,
                           uom='Nos', allow_daywork=1, allow_piecework=0, productivity_per_workday=1, active=1)
        basis = base.insert('Norm Basis', basis_code=self.tag, basis_name='Flow '+self.tag, uom='Nos', active=1)
        item = frappe.copy_doc(frappe.get_doc('Item', 'PCT-M'))
        item.item_code = 'FLOW-'+self.tag
        item.item_name = item.item_code
        item.insert()
        norm = base.insert('Material Norm Profile', farm=farm, profile_name='Flow '+self.tag, version=1, work_type=work.name,
            valid_from=base.DAY, valid_to=base.DAY, approval_state='Approved',
            lines=[dict(item=item.name, uom='Nos', norm_basis=basis.name, norm_qty=2, basis_qty=1, frequency=1, conversion_factor=1)])
        plan = base.insert('Daily Work Plan', company=base.C, farm=farm, posting_date=base.DAY,
            lines=[dict(farm_block=block.name, work_type=work.name, planned_qty=1, uom='Nos', norm_profile=norm.name)])
        plan.submit()
        requirement = base.insert('Material Requirement', company=base.C, farm=farm, farm_block=block.name,
            posting_date=base.DAY, work_plan=plan.name, work_plan_line=plan.lines[0].name, lotus_warehouse=base.WH)
        requirement.submit()
        d = base.receiving.create_purchase_request(base.C, base.WH, base.DAY, base.DAY, [item.name])
        self.assertEqual(d['docstatus'], 0)
        source = frappe.get_doc('Material Request', d['name'])
        self.assertEqual(json.loads(source.items[0].lotus_purchase_sources)[0]['name'], requirement.name)
        self.assertFalse(source.items[0].get('lotus_requirement'))
        self.assertEqual(source_allocations('Material Requirement', requirement.name, requirement.lines[0].name)['posted'], 0)
        d = pp.sign(d['name'], d['modified'], dict(DEPARTMENT=base.LEADER, PURCHASING=base.ACC, APPROVE=base.DIR))
        for user in (base.LEADER, base.ACC, base.DIR):
            d = base.as_user(user, pp.sign, d['name'], d['modified'])
        receipt = warehouse.create_draft(base.C, 'receipt', base.DAY, [dict(item=item.name, qty=2, rate=100000)],
            target=base.WH, receipt_reason='Purchase', supplier=self.supplier, post=1, client_event_id=self.tag+'work-stock')
        self.assertEqual(receipt['docstatus'], 1)
        issue = warehouse.create_draft(base.C, 'issue', base.DAY,
            [dict(item=item.name, qty=2, uom='Nos', area=block.name, requirement=requirement.name, requirement_line=requirement.lines[0].name)],
            source=base.WH, work_plan=plan.name, issue_mode='Plan',
            receiver_employee=frappe.db.get_value('Employee', {'user_id': base.BUYER}, 'name'), notes='Cấp theo công việc', client_event_id=self.tag+'work-issue')
        doc = frappe.get_doc('Stock Entry', issue['name'])
        warehouse.submit_document('Stock Entry', doc.name, modified=str(doc.modified))
        self.assertEqual(source_allocations('Material Requirement', requirement.name, requirement.lines[0].name)['posted'], 2)

    def test_12_historical_orders_can_finish_but_new_orders_need_sources(self):
        previous = frappe.conf.get('lotus_purchase_flow_since')
        try:
            frappe.conf.lotus_purchase_flow_since = frappe.utils.add_days(base.DAY, 1)
            order = base.ProcurementIntegration.order(self, qty=1)
            self.assertEqual(order.docstatus, 1)
            frappe.conf.lotus_purchase_flow_since = frappe.utils.add_days(base.DAY, -1)
            with self.assertRaises(frappe.ValidationError):
                base.ProcurementIntegration.order(self, qty=1)
        finally:
            frappe.conf.lotus_purchase_flow_since = previous


if __name__ == '__main__':
    try:
        unittest.main(verbosity=2)
    finally:
        frappe.db.rollback()
        frappe.destroy()
