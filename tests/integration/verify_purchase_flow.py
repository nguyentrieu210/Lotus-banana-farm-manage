"""Four-step purchasing UAT. Uses only the isolated procurement.test stack."""
import json
import unittest
from io import BytesIO
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import frappe
from frappe.utils import flt
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
        cls.keeper = base.user('keeper', ['Lotus Warehouse Receiver', 'Lotus Warehouse Manager', 'Lotus Warehouse Operator'])
        cls.keeper_only = base.user('receiver', ['Lotus Warehouse Receiver', 'Lotus Warehouse Operator'])
        frappe.db.commit()
        frappe.conf.lotus_purchase_flow_company = None
        cls.image = BytesIO()
        image = Image.new('RGB', (200, 70), 'white')
        ImageDraw.Draw(image).line([(10, 50), (70, 15), (100, 55), (190, 20)], fill='black', width=3)
        image.save(cls.image, format='PNG')
        from base64 import b64encode
        cls.signature_data = 'data:image/png;base64,' + b64encode(cls.image.getvalue()).decode('ascii')

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

    def receive(self, order, qty):
        result = base.receiving.receive_order(order.name, base.DAY, json.dumps({order.items[0].name: qty}), self.tag + 'in' + str(qty),
                                              post=1, deliverer_name='Người giao thử', deliverer_signature=self.signature_data)
        return frappe.get_doc('Purchase Receipt', result['name'])

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
        item = frappe.copy_doc(frappe.get_doc('Item', 'PCT-M'))
        item.item_code = 'FLOW-'+self.tag
        item.item_name = item.item_code
        item.insert()
        # The demand: an approved request to issue 2 units to the lot. The lot is named by its code, which is
        # how a stock issue finds the lot its cost belongs to.
        demand = base.insert('Material Request', company=base.C, material_request_type='Material Issue',
            transaction_date=base.DAY, schedule_date=base.DAY,
            items=[dict(item_code=item.name, qty=2, uom='Nos', stock_uom='Nos', conversion_factor=1, warehouse=base.WH,
                        schedule_date=base.DAY, lotus_usage_area=block.block_code)])
        from lotus_farm.issue_request import _approve  # spec 005: issue_request_fixture.approve_native
        _approve(demand, 'Administrator')
        line = demand.items[0].name
        d = base.receiving.create_purchase_request(base.C, base.WH, base.DAY, base.DAY, [item.name])
        self.assertEqual(d['docstatus'], 0)
        source = frappe.get_doc('Material Request', d['name'])
        self.assertEqual(source.material_request_type, 'Purchase')
        self.assertEqual(source.items[0].qty, 2)
        self.assertEqual(json.loads(source.items[0].lotus_purchase_sources)[0],
                         dict(doctype='Material Request', name=demand.name, line=line))
        self.assertEqual(source_allocations(demand.name, line)['posted'], 0)
        d = pp.sign(d['name'], d['modified'], dict(DEPARTMENT=base.LEADER, PURCHASING=base.ACC, APPROVE=base.DIR))
        for user in (base.LEADER, base.ACC, base.DIR):
            d = base.as_user(user, pp.sign, d['name'], d['modified'])
        receipt = warehouse.create_draft(base.C, 'receipt', base.DAY, [dict(item=item.name, qty=2, rate=100000)],
            target=base.WH, receipt_reason='Purchase', supplier=self.supplier, post=1, client_event_id=self.tag+'work-stock')
        self.assertEqual(receipt['docstatus'], 1)
        # Buying and receiving the goods issues nothing: the demand stays open until the warehouse issues to the lot.
        self.assertEqual(source_allocations(demand.name, line), dict(draft=0, posted=0))
        issue = warehouse.create_draft(base.C, 'issue', base.DAY,
            [dict(item=item.name, qty=2, uom='Nos', area=block.block_code, material_request=demand.name, material_request_item=line)],
            source=base.WH, issue_mode='Request',
            receiver_employee=frappe.db.get_value('Employee', {'user_id': base.BUYER}, 'name'), notes='Cấp theo công việc', client_event_id=self.tag+'work-issue')
        doc = frappe.get_doc('Stock Entry', issue['name'])
        self.assertEqual(source_allocations(demand.name, line), dict(draft=2, posted=0))
        warehouse.submit_document('Stock Entry', doc.name, modified=str(doc.modified))
        self.assertEqual(source_allocations(demand.name, line), dict(draft=0, posted=2))

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

    # ---- Spec 003 · US3: the chosen quote reaches the order, warnings at save, the director signs every order ----
    def other_supplier(self):
        group = frappe.db.get_value('Supplier', 'PCT Supplier', 'supplier_group')
        return base.insert('Supplier', supplier_name='PCT Other ' + self.tag, supplier_group=group, supplier_type='Company').name

    def quote(self, proposal, qty, rate, supplier=None, confirm=True, vat='KCT', freight=0, key=''):
        data = dict(supplier=supplier or self.supplier, warehouse=base.WH, expected_date=base.DAY, valid_till=frappe.utils.add_days(base.DAY, 7),
                    items=[dict(item='PCT-M', qty=qty, rate=rate, uom='Nos', kind='Material', vat_code=vat, freight=freight,
                                material_request=proposal['name'], material_request_item=proposal['items'][0]['name'])])
        saved = base.as_user(base.BUYER, base.p.save_quotation, base.C, data, self.tag + 'quote' + key)
        doc = frappe.get_doc('Supplier Quotation', saved['name'])
        if confirm:
            base.as_user(base.BUYER, base.p.confirm_quotation, doc.name, str(doc.modified))
            doc.reload()
        return doc

    def draft(self, proposal, qty, extra=()):
        data = dict(supplier=self.supplier, warehouse=base.WH, expected_date=base.DAY, mode='Kho tự mua',
            items=[dict(item='PCT-M', qty=qty, rate=100000, uom='Nos', kind='Material', vat_code='KCT',
                        material_request=proposal['name'], material_request_item=proposal['items'][0]['name']), *extra])
        return base.as_user(base.BUYER, base.buying.save_order, base.C, data), data

    def test_13_chosen_quote_carries_supplier_and_price_into_the_order(self):
        proposal = self.proposal(qty=10, rate=90000)
        line = proposal['items'][0]['name']
        signed_content = signing.fingerprint(frappe.get_doc('Material Request', proposal['name']))
        cheap = self.quote(proposal, 10, 100000, key='a')
        other = self.other_supplier()
        dear = self.quote(proposal, 10, 120000, supplier=other, vat='10', freight=50000, key='b')
        with self.assertRaises(frappe.ValidationError):  # not the cheapest: say why
            base.as_user(base.BUYER, base.p.choose_quote, base.C, proposal['name'], line, dear.name, dear.items[0].name)
        base.as_user(base.BUYER, base.p.choose_quote, base.C, proposal['name'], line, dear.name, dear.items[0].name, 'Giao ngay trong ngày')
        row = next(r for r in base.as_user(base.BUYER, base.p.compare, base.C, proposal['name'])['rows'] if r['request_line'] == line)
        self.assertEqual((row['selected_line'], row['selected_reason'], row['best_line']),
                         (dear.items[0].name, 'Giao ngay trong ngày', cheap.items[0].name))
        self.assertEqual(signing.fingerprint(frappe.get_doc('Material Request', proposal['name'])), signed_content,
                         'choosing a quote does not touch what was signed')
        detail = base.as_user(base.BUYER, base.buying.request_detail, proposal['name'], base.C)
        got = detail['items'][0]
        # The phone app lists proposals through purchasing.requests: the same choice must come along there.
        phone = next(r for r in base.as_user(base.BUYER, purchasing.requests, base.C) if r['name'] == proposal['name'])
        self.assertEqual((phone['supplier'], phone['items'][0]['supplier'], phone['items'][0]['rate'], phone['items'][0]['supplier_quotation']),
                         (other, other, 120000, dear.name))
        self.assertEqual(detail['supplier'], other)
        self.assertEqual((got['supplier'], got['rate'], got['vat_code'], got['freight'], got['supplier_quotation'], got['supplier_quotation_item']),
                         (other, 120000, '10', 50000, dear.name, dear.items[0].name))
        saved = base.as_user(base.BUYER, base.buying.save_order, base.C,
                             dict(supplier=detail['supplier'], warehouse=base.WH, expected_date=base.DAY, mode='Kho tự mua', items=[got]))
        order = frappe.get_doc('Purchase Order', saved['name'])
        self.assertEqual((order.supplier, frappe.utils.flt(order.items[0].rate), order.items[0].supplier_quotation, order.items[0].lotus_line_vat),
                         (other, 120000, dear.name, '10'))
        self.assertEqual(saved['warnings'], [])
        with self.assertRaises(frappe.ValidationError):  # a quote an order points at stays
            base.as_user(base.BUYER, base.p.cancel_quotation, dear.name, str(dear.modified), 'Hủy thử')
        with self.assertRaises(frappe.ValidationError):  # a confirmed quote is cancelled with a reason
            base.as_user(base.BUYER, base.p.cancel_quotation, cheap.name, str(cheap.modified))
        base.as_user(base.BUYER, base.p.cancel_quotation, cheap.name, str(cheap.modified), 'NCC rút báo giá')
        self.assertEqual(frappe.db.get_value('Supplier Quotation', cheap.name, 'docstatus'), 2)
        # Without a choice the line falls back to the price expected in the proposal.
        base.as_user(base.BUYER, base.buying.delete_draft, saved['name'], saved['modified'])
        base.as_user(base.BUYER, base.p.choose_quote, base.C, proposal['name'], line)
        got = base.as_user(base.BUYER, base.buying.request_detail, proposal['name'], base.C)['items'][0]
        self.assertEqual((got.get('supplier'), got['rate'], got.get('supplier_quotation')), (None, 90000, None))

    def test_14_saving_an_order_says_which_lines_approval_will_refuse(self):
        proposal = self.proposal(qty=5)
        stray = dict(item='PCT-T', qty=1, rate=50000, uom='Nos', kind='Tool', vat_code='KCT')
        saved, data = self.draft(proposal, 5, extra=[stray])
        self.assertEqual([(w['line'], w['code']) for w in saved['warnings']], [(2, 'no_source')])
        self.assertIn('Mua nhanh', saved['warnings'][0]['message'])
        with self.assertRaises(frappe.ValidationError):
            base.as_user(base.BUYER, purchasing.request_approval, saved['name'], saved['modified'], base.DIR)
        data['items'] = data['items'][:1]
        fixed = base.as_user(base.BUYER, base.buying.save_order, base.C, data, saved['name'], saved['modified'])
        self.assertEqual(fixed['warnings'], [])
        # A second draft on the same proposal line only warns; the order approved first takes the quantity.
        second, _ = self.draft(proposal, 5)
        self.assertEqual([(w['line'], w['code']) for w in second['warnings']], [(1, 'held')])
        base.as_user(base.BUYER, purchasing.request_approval, fixed['name'], fixed['modified'], base.DIR)
        first = frappe.get_doc('Purchase Order', fixed['name'])
        base.as_user(base.DIR, purchasing.approve_order, first.name, str(first.modified))
        info = base.as_user(base.BUYER, purchasing.detail, second['name'])
        self.assertEqual([(w['line'], w['code']) for w in info['warnings']], [(1, 'over')])
        with self.assertRaises(frappe.ValidationError):
            base.as_user(base.BUYER, purchasing.request_approval, second['name'], info['modified'], base.DIR)

    def test_15_orders_from_a_comparison_wait_for_the_director(self):
        self.assertFalse({'Lotus Purchase Approver', 'Purchase Manager', 'System Manager'} & set(frappe.get_roles(base.BUYER)),
                         'the buyer account holds no approving role')
        proposal = self.proposal(qty=4)
        quote = self.quote(proposal, 4, 100000, confirm=False)
        result = base.as_user(base.BUYER, base.p.select_quotes, base.C,
                              [dict(quotation=quote.name, line=quote.items[0].name, modified=str(quote.modified), qty=4)], self.tag + 'sel')
        order = frappe.get_doc('Purchase Order', result['orders'][0])
        self.assertEqual((order.docstatus, order.lotus_approval_status, result['sent']), (0, 'Nháp', []))
        self.assertEqual(frappe.db.get_value('Supplier Quotation', quote.name, 'docstatus'), 1, 'the chosen draft quote is confirmed')
        self.assertEqual(base.as_user(base.BUYER, purchasing.detail, order.name)['status'], 'Nháp')
        again = self.proposal(qty=2)
        quote = self.quote(again, 2, 100000, key='2')
        result = base.as_user(base.BUYER, base.p.select_quotes, base.C,
                              [dict(quotation=quote.name, line=quote.items[0].name, modified=str(quote.modified), qty=2)], self.tag + 'sel2', base.DIR)
        self.assertEqual(result['sent'], result['orders'])
        order = frappe.get_doc('Purchase Order', result['orders'][0])
        self.assertEqual((order.docstatus, order.lotus_approval_status), (0, 'Chờ duyệt'))
        info = base.as_user(base.DIR, purchasing.detail, order.name)
        self.assertEqual((info['status'], info['can_approve']), ('Chờ duyệt', True))
        approver_only = base.user('approver' + self.tag, ['Lotus Purchase Approver'])
        frappe.db.savepoint('approver_only')
        base.as_user(base.DIR, purchasing.approve_order, order.name, info['modified'])
        self.assertEqual(frappe.db.get_value('Purchase Order', order.name, 'docstatus'), 1, 'the named approver approves an order made from a quote')
        self.assertTrue(base.as_user(approver_only, frappe.has_permission, 'Supplier Quotation', 'read'), 'approvers read the quotes behind orders')

    def test_16_only_the_named_approver_signature_submits_an_order(self):
        proposal = self.proposal(qty=3)
        saved, _ = self.draft(proposal, 3)
        native = lambda: frappe.get_doc('Purchase Order', saved['name']).submit()
        with self.assertRaises(frappe.ValidationError):  # not sent for approval
            native()
        base.as_user(base.BUYER, purchasing.request_approval, saved['name'], saved['modified'], base.DIR)
        order = frappe.get_doc('Purchase Order', saved['name'])
        deputy = base.user('deputy' + self.tag, ['Lotus Purchase Approver'])
        with self.assertRaises(frappe.PermissionError):  # holds the role, was not named
            base.as_user(deputy, purchasing.approve_order, order.name, str(order.modified))
        for who in (deputy, base.DIR, 'Administrator'):  # Desk / REST submit: no signature, no approval
            with self.assertRaises(frappe.PermissionError):
                base.as_user(who, native)
        self.assertEqual(frappe.db.get_value('Purchase Order', order.name, 'docstatus'), 0)
        base.as_user(base.DIR, purchasing.approve_order, order.name, str(order.modified))
        info = base.as_user(base.DIR, purchasing.detail, order.name)
        self.assertEqual((info['docstatus'], info['status'], info['approved_by']), (1, 'Đã duyệt', base.DIR))
        self.assertEqual([s['state'] for s in info['signing']['steps']], ['Đã ký', 'Đã ký'])
        self.assertTrue(info['signed_copy'] and info['signed_copy']['pdf_sha256'], 'the signed PDF is stored with the approval')

    def test_17_return_and_cancel_need_a_reason_and_free_the_proposal_line(self):
        proposal = self.proposal(qty=6)
        stage = lambda: base.as_user(base.BUYER, pp.detail, proposal['name'])['stage']
        saved, data = self.draft(proposal, 6)
        base.as_user(base.BUYER, purchasing.request_approval, saved['name'], saved['modified'], base.DIR)
        order = frappe.get_doc('Purchase Order', saved['name'])
        with self.assertRaises(frappe.ValidationError):
            base.as_user(base.DIR, purchasing.reject_order, order.name, str(order.modified), ' ')
        base.as_user(base.DIR, purchasing.reject_order, order.name, str(order.modified), 'Giá cao hơn báo giá')
        info = base.as_user(base.BUYER, purchasing.detail, order.name)
        self.assertEqual((info['status'], info['reject_reason'], info['can_write']), ('Bị trả lại', 'Giá cao hơn báo giá', True))
        fixed = base.as_user(base.BUYER, base.buying.save_order, base.C, data, order.name, info['modified'])
        base.as_user(base.BUYER, purchasing.request_approval, order.name, fixed['modified'], base.DIR)
        order.reload()
        base.as_user(base.DIR, purchasing.approve_order, order.name, str(order.modified))
        self.assertEqual(stage(), 'Đang mua')
        order.reload()
        with self.assertRaises(frappe.PermissionError):  # the buyer does not cancel an approved order
            base.as_user(base.BUYER, purchasing.cancel_order, order.name, str(order.modified), 'NCC không giao được')
        with self.assertRaises(frappe.ValidationError):
            base.as_user(base.DIR, purchasing.cancel_order, order.name, str(order.modified), '  ')
        base.as_user(base.DIR, purchasing.cancel_order, order.name, str(order.modified), 'NCC không giao được')
        info = base.as_user(base.BUYER, purchasing.detail, order.name)
        self.assertEqual((info['status'], info['cancel_reason']), ('Đã hủy', 'NCC không giao được'))
        self.assertEqual(stage(), 'Chờ mua', 'the proposal line can be ordered again')

    def test_18_only_the_preparer_deletes_a_draft_or_returned_order(self):
        proposal = self.proposal(qty=2)
        saved, _ = self.draft(proposal, 2)
        colleague = base.user('buyer' + self.tag, ['Lotus Purchasing Buyer'])
        with self.assertRaises(frappe.PermissionError):
            base.as_user(colleague, base.buying.delete_draft, saved['name'], saved['modified'])
        base.as_user(base.BUYER, purchasing.request_approval, saved['name'], saved['modified'], base.DIR)
        order = frappe.get_doc('Purchase Order', saved['name'])
        with self.assertRaises(frappe.ValidationError):  # waiting for the approver
            base.as_user(base.BUYER, base.buying.delete_draft, order.name, str(order.modified))
        base.as_user(base.DIR, purchasing.reject_order, order.name, str(order.modified), 'Sai nhà cung cấp')
        info = base.as_user(base.BUYER, purchasing.detail, order.name)
        self.assertTrue(info['can_delete'])
        base.as_user(base.BUYER, base.buying.delete_draft, order.name, info['modified'])
        self.assertFalse(frappe.db.exists('Purchase Order', order.name))

    def test_19_one_status_vocabulary_and_progress_on_the_order_list(self):
        from lotus_farm import purchase_status
        proposal = self.proposal(qty=4)
        saved, _ = self.draft(proposal, 4)
        row = lambda who=None: next(r for r in base.as_user(who or base.ACC, purchasing.orders, base.C) if r['name'] == saved['name'])
        states = [row()['status']]
        base.as_user(base.BUYER, purchasing.request_approval, saved['name'], saved['modified'], base.DIR)
        states.append(row()['status'])
        order = frappe.get_doc('Purchase Order', saved['name'])
        base.as_user(base.DIR, purchasing.approve_order, order.name, str(order.modified))
        states.append(row()['status'])
        order.reload()
        base.as_user(base.BUYER, purchasing.mark_order_sent, order.name, str(order.modified))
        states.append(row()['status'])
        order.reload()
        base.as_user(base.BUYER, purchasing.confirm_supplier_order, order.name, str(order.modified))
        states.append(row()['status'])
        order.reload()
        receipt = self.receive(order, 1)
        states.append(row()['status'])
        invoice = self.invoice(receipt)
        seen = row()
        self.assertEqual((seen['billed_percent'], seen['paid_amount'], seen['paid_percent']), (25, 0, 0))
        voucher = base.as_user(base.ACC, base.p.supplier_payment, base.C, 'Purchase Invoice', invoice.name, 50000, 'cash', base.DAY,
                               dict(CHIEF=base.CHIEF, APPROVE=base.DIR), self.tag + 'pay')
        self.assertEqual(row()['paid_amount'], 0, 'a voucher still being signed is not money paid')
        base.signed(voucher)
        seen = row()
        self.assertEqual((seen['paid_amount'], seen['paid_percent']), (50000, 12.5))
        self.assertIsNone(row(base.BUYER)['paid_percent'], 'payments are shown only to people who may read them')
        order.reload()
        self.receive(order, 3)
        states.append(row()['status'])
        self.assertEqual(states, ['Nháp', 'Chờ duyệt', 'Đã duyệt', 'Đã gửi NCC', 'NCC đã xác nhận', 'Đang nhận', 'Đã nhận đủ'])
        self.assertTrue(set(states) <= set(purchase_status.ORDER_STATES))

    def test_23_proposal_keeps_the_typed_price_when_a_buying_price_list_exists(self):
        list_name = frappe.db.get_value('Price List', {'buying': 1, 'enabled': 1}, 'name') or base.insert('Price List', price_list_name='UAT Buying', buying=1, currency='VND').name
        frappe.db.set_default('buying_price_list', list_name)
        if not frappe.db.exists('Item Price', {'item_code': 'PCT-M', 'price_list': list_name}):
            base.insert('Item Price', item_code='PCT-M', price_list=list_name, price_list_rate=14500)
        d = self.proposal(qty=3, rate=120000, approve=False)
        d = base.as_user(base.BUYER, pp.sign, d['name'], d['modified'], dict(DEPARTMENT=base.LEADER, PURCHASING=base.ACC, APPROVE=base.DIR))
        doc = frappe.get_doc('Material Request', d['name'])
        self.assertEqual((flt(doc.items[0].rate), doc.get('buying_price_list')), (120000, None), 'the price the proposer typed is what is signed')

    # ---- Spec 003 · US4: one-step receiving, the deliverer's confirmation, the storekeeper signs by confirming ----
    def refused(self, fn, *args, error=frappe.ValidationError, **kwargs):
        """A refused request leaves nothing behind (a web request is rolled back as a whole)."""
        frappe.db.savepoint('refused_call')
        with self.assertRaises(error) as caught:
            fn(*args, **kwargs)
        frappe.db.rollback(save_point='refused_call')
        return str(caught.exception)

    def photo(self, name, owner):
        """A private file the user has just uploaded, not attached to anything yet."""
        from PIL import Image, ImageDraw
        image = Image.new('RGB', (320, 200), 'white')
        ImageDraw.Draw(image).text((20, 80), name + self.tag, fill='black')
        content = BytesIO()
        image.save(content, format='PNG')
        file = frappe.get_doc(dict(doctype='File', file_name=self.tag + name, content=content.getvalue(), is_private=1))
        return base.as_user(owner, lambda: file.insert(ignore_permissions=True)).file_url

    def test_20_receiving_is_one_step_signed_by_the_storekeeper(self):
        order = self.order(5)
        line = order.items[0].name
        goods = self.photo('hang.png', self.keeper)
        take = lambda key, qty, **more: base.as_user(self.keeper, base.receiving.receive_order, order.name, base.DAY,
                                                     json.dumps({line: qty}), self.tag + key, post=1, **more)
        self.assertIn('người giao hàng', self.refused(take, 'a', 2))
        self.assertIn('người giao hàng', self.refused(take, 'a', 2, deliverer_signature=self.signature_data), 'a signature needs the name beside it')
        self.assertFalse(frappe.db.exists('Purchase Receipt Item', {'purchase_order': order.name}))
        result = take('b', 2, files=json.dumps([goods]), deliverer_name='Trần Văn Giao', deliverer_signature=self.signature_data, notes='Giao bằng xe tải')
        self.assertEqual((result['docstatus'], result['state']), (1, 'Đã nhập kho'))
        self.assertTrue(result['signed_copy'] and result['signed_copy']['pdf_sha256'])
        self.assertEqual(result['remaining'][0]['remaining_qty'], 3)
        receipt = frappe.get_doc('Purchase Receipt', result['name'])
        rows, _ = signing._rows(receipt)
        self.assertEqual([(r.chain, r.step_key, r.state, r.assignee) for r in rows], [('purchase_receipt', 'STOREKEEPER', 'Đã ký', self.keeper)])
        self.assertTrue(frappe.db.exists('Lotus Signed Copy', {'document_type': 'Purchase Receipt', 'document_name': receipt.name}))
        self.assertEqual(take('b', 2, files=json.dumps([goods]), deliverer_name='Trần Văn Giao', deliverer_signature=self.signature_data,
                              notes='Giao bằng xe tải')['name'], receipt.name, 'sending the same request again creates nothing new')
        detail = base.as_user(self.keeper, base.p.receipt, receipt.name)
        self.assertEqual((detail['deliverer_name'], detail['deliverer_signed'], detail['billing'], detail['notes'], detail['has_evidence']),
                         ('Trần Văn Giao', True, 'Chưa có hóa đơn', 'Giao bằng xe tải', True))
        self.assertIn(goods, [f['file_url'] for f in detail['files']])
        from lotus_farm import print_kit
        from lotus_farm.www import lotus_stock_print
        page = base.as_user(self.keeper, lambda: str(print_kit.render('stock.html', lotus_stock_print.build('Purchase Receipt', receipt.name))))
        for text in ('Người giao hàng', 'Trần Văn Giao', 'Thủ kho nhận hàng', 'Ký trên màn hình khi giao hàng'):
            self.assertIn(text, page)
        self.assertEqual(self.refused(base.as_user, self.keeper, signing.return_document, 'Purchase Receipt', receipt.name, 'Trả lại thử')[:8], 'Trả lại ')
        # The photographed delivery note alone is enough; the receipt of the rest completes the order.
        note = self.photo('phieu-giao.png', self.keeper)
        rest = take('c', 3, delivery_proof=note)
        self.assertEqual((rest['docstatus'], rest['remaining']), (1, []))
        proof = base.as_user(self.keeper, base.receiving.purchase_receipt, rest['name'])
        self.assertEqual((proof['delivery_proof'], proof['deliverer_signed'], proof['has_evidence']), (note, False, True))
        page = base.as_user(self.keeper, lambda: str(print_kit.render('stock.html', lotus_stock_print.build('Purchase Receipt', rest['name']))))
        self.assertIn('Đã ký trên phiếu giao hàng đính kèm', page)
        self.assertIn('lp-proof', page)
        self.assertEqual(base.as_user(base.BUYER, purchasing.detail, order.name)['status'], 'Đã nhận đủ')

    def test_21_no_path_posts_a_receipt_without_the_deliverer(self):
        order = self.order(4)
        line = order.items[0].name
        draft = base.as_user(self.keeper, base.receiving.receive_order, order.name, base.DAY, json.dumps({line: 4}), self.tag + 'draft')
        self.assertEqual((draft['docstatus'], draft['state']), (0, 'Nháp'))
        info = base.as_user(self.keeper, base.receiving.purchase_receipt, draft['name'])
        self.assertEqual((info['needs_evidence'], info['has_evidence'], info['can_submit']), (True, False, True))
        self.refused(lambda: frappe.get_doc('Purchase Receipt', draft['name']).submit())  # Desk / REST
        self.refused(base.as_user, self.keeper, base.receiving.receipt_action, draft['name'], draft['modified'], 'submit')
        base.as_user(self.keeper, base.receiving.receipt_action, draft['name'], draft['modified'], 'submit', None, 'Lê Thị Giao', self.signature_data)
        receipt = frappe.get_doc('Purchase Receipt', draft['name'])
        self.assertEqual(receipt.docstatus, 1)
        self.assertEqual(signing.status(receipt)['done'], True)
        # Cancelling says why, and only people who may cancel receipts do it.
        self.refused(base.as_user, self.keeper_only, base.receiving.receipt_action, receipt.name, str(receipt.modified), 'cancel', 'Nhập nhầm', error=frappe.PermissionError)
        self.refused(base.as_user, self.keeper, base.receiving.receipt_action, receipt.name, str(receipt.modified), 'cancel', '  ')
        base.as_user(self.keeper, base.receiving.receipt_action, receipt.name, str(receipt.modified), 'cancel', 'Nhập nhầm đơn mua')
        info = base.as_user(self.keeper, base.receiving.purchase_receipt, receipt.name)
        self.assertEqual((info['state'], info['cancel_reason']), ('Đã hủy', 'Nhập nhầm đơn mua'))
        self.assertEqual(base.as_user(base.BUYER, purchasing.detail, order.name)['status'], 'Đã duyệt', 'the order waits for its goods again')

    def test_22_quick_purchase_is_named_mua_nhanh_everywhere(self):
        from lotus_farm import purchase_status, warehouse
        result = warehouse.create_draft(base.C, 'receipt', base.DAY, [dict(item='PCT-M', qty=1, rate=100000)],
            target=base.WH, receipt_reason='Purchase', supplier=self.supplier, post=1, client_event_id=self.tag + 'label')
        self.assertEqual(purchase_status.QUICK_PURCHASE, 'Mua nhanh')
        row = next(r for r in base.p.quick_purchases(base.C) if r['name'] == result['name'])
        self.assertIn('Mua nhanh', row['source_type'])
        listed = warehouse.documents(base.C, kind='receipts')
        rows = listed['rows'] if isinstance(listed, dict) else listed
        mine = next(r for r in rows if r['name'] == result['name'])
        self.assertIn('Mua nhanh', json.dumps(mine, ensure_ascii=False, default=str))
        self.assertNotIn('Mua ngoài', json.dumps(mine, ensure_ascii=False, default=str))
        from lotus_farm.finance import stock
        self.assertIn('Mua nhanh', stock.RECEIPT_REASONS['Purchase'][0])


if __name__ == '__main__':
    try:
        unittest.main(verbosity=2)
    finally:
        frappe.db.rollback()
        frappe.destroy()
