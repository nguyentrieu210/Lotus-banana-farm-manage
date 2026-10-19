"""Command boundaries without requiring a running Frappe site."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch


class TestWarehouseGuards(unittest.TestCase):
    def setUp(self):
        self.frappe = types.ModuleType('frappe')
        self.frappe.whitelist = lambda **kw: lambda fn: fn
        self.frappe.throw = Mock(side_effect=ValueError)
        self.frappe.PermissionError = PermissionError
        self.frappe.AuthenticationError = PermissionError
        self.frappe.session = types.SimpleNamespace(user='Administrator')
        self.frappe.has_permission = Mock(return_value=True)
        self.frappe.parse_json = lambda rows: rows
        self.frappe.get_doc = Mock()
        self.frappe.new_doc = Mock()
        self.frappe.db = Mock()
        self.frappe.db.get_value.return_value = 0
        self.frappe.get_cached_value = Mock(return_value='VND')
        utils = types.ModuleType('frappe.utils')
        utils.cint, utils.flt = int, float
        utils.getdate = lambda value: value
        utils.nowdate = lambda: '2026-10-13'
        spec = importlib.util.spec_from_file_location('warehouse_guards', Path(__file__).parents[1] / 'lotus_farm/warehouse.py')
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'frappe': self.frappe, 'frappe.utils': utils}):
            spec.loader.exec_module(self.module)

    def test_invalid_quantities_cannot_become_zero_or_nonfinite_stock(self):
        for value in ('abc', 'nan', 'inf', -1, None, 0):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.module._number(value, 'Quantity')
        self.assertEqual(self.module._number(0, 'Count', allow_zero=True), 0)

    def test_guest_and_missing_permission_are_rejected(self):
        self.frappe.session.user = 'Guest'
        with self.assertRaises(ValueError):
            self.module._access()
        self.frappe.session.user = 'reader'
        self.frappe.has_permission.return_value = False
        with self.assertRaises(ValueError):
            self.module._access()

    def test_cross_company_group_and_disabled_warehouses_are_rejected(self):
        for values in (dict(company='Other', is_group=0, disabled=0),
                       dict(company='Farm', is_group=1, disabled=0),
                       dict(company='Farm', is_group=0, disabled=1)):
            doc = Mock(**values)
            self.frappe.get_doc.return_value = doc
            with self.assertRaises(ValueError):
                self.module._warehouse('Warehouse', 'Farm')
            doc.check_permission.assert_called_with('read')

    def test_receipt_creates_native_draft_without_submitting(self):
        self.module._company = Mock()
        self.module._warehouse = Mock()
        item = Mock(name='Item')
        item.name, item.stock_uom = 'FERT-001', 'Kg'
        item.disabled = item.has_batch_no = item.has_serial_no = 0
        item.is_stock_item = 1
        self.frappe.get_doc.return_value = item
        doc = Mock()
        doc.name = 'MAT-TEST'
        doc.doctype = 'Stock Entry'
        self.frappe.new_doc.return_value = doc
        result = self.module.create_draft('Farm', 'receipt', '2026-10-13',
                                         [dict(item='FERT-001', qty=5, rate=10)], target='Main')
        self.assertEqual(doc.stock_entry_type, 'Material Receipt')
        self.assertEqual(doc.append.call_args.args[1]['t_warehouse'], 'Main')
        self.assertEqual(doc.append.call_args.args[1]['basic_rate'], 10)
        doc.insert.assert_called_once_with()
        doc.submit.assert_not_called()
        self.assertEqual(result, dict(name='MAT-TEST', doctype='Stock Entry'))

    def test_transfer_to_same_warehouse_is_rejected(self):
        self.module._company = Mock()
        self.module._warehouse = Mock()
        with self.assertRaises(ValueError):
            self.module.create_draft('Farm', 'transfer', '2026-10-13', [], source='Main', target='Main')
        self.frappe.new_doc.assert_not_called()

    def test_receipt_costs_use_company_currency_and_checked_expense_account(self):
        company = Mock(default_currency='VND')
        company.get.return_value = 'Main - Farm'
        self.module._company = Mock(return_value=company)
        account = Mock(company='Farm', is_group=0, disabled=0, root_type='Expense')
        account.name = 'Expense - Farm'
        account.get.return_value = 'VND'
        self.frappe.get_doc.return_value = account
        result = self.module._receipt_costs('Farm', [dict(description='Transport', amount=200, expense_account=account.name)], 1000)
        self.assertEqual(result[0]['base_amount'], 200)
        self.assertEqual(result[0]['exchange_rate'], 1)
        self.assertEqual(result[0]['cost_center'], 'Main - Farm')
        account.check_permission.assert_called_once_with('read')

    def test_receipt_costs_reject_invalid_money_and_zero_allocation_basis(self):
        for amount in (-1, 0, 'nan', 'inf', 'invalid'):
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                self.module._receipt_costs('Farm', [dict(description='Transport', amount=amount)], 1000)
        with self.assertRaises(ValueError):
            self.module._receipt_costs('Farm', [dict(description='Transport', amount=100)], 0)
        with self.assertRaises(ValueError):
            self.module._receipt_costs('Farm', [], float('inf'))

    def test_receipt_costs_reject_cross_company_group_and_foreign_currency_accounts(self):
        self.module._company = Mock(return_value=Mock(default_currency='VND'))
        for company, group, disabled, root, currency in [('Other', 0, 0, 'Expense', 'VND'),
                ('Farm', 1, 0, 'Expense', 'VND'), ('Farm', 0, 1, 'Expense', 'VND'),
                ('Farm', 0, 0, 'Asset', 'VND'), ('Farm', 0, 0, 'Expense', 'USD')]:
            account = Mock(company=company, is_group=group, disabled=disabled, root_type=root)
            account.get.return_value = currency
            self.frappe.get_doc.return_value = account
            with self.subTest(company=company, currency=currency), self.assertRaises(ValueError):
                self.module._receipt_costs('Farm', [dict(description='Transport', amount=100, expense_account='Expense')], 1000)

    def test_issue_does_not_accept_receipt_costs(self):
        self.module._company = Mock()
        with self.assertRaises(ValueError):
            self.module.create_draft('Farm', 'issue', '2026-10-13', [], additional_costs=[dict(amount=100)])
        self.frappe.new_doc.assert_not_called()

    def test_master_creation_requires_create_permission(self):
        self.module._company = Mock()
        self.module._access = Mock()
        self.frappe.has_permission.return_value = False
        for kind in ('item', 'group', 'warehouse'):
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                self.module.create_master('Farm', kind, {'name': 'Test'})
        self.frappe.get_doc.assert_not_called()

    def test_movement_scope_filtering_and_pagination(self):
        class Row(dict):
            __getattr__ = dict.__getitem__
            __setattr__ = dict.__setitem__
        spec = importlib.util.spec_from_file_location('lotus_farm.table_filters', Path(__file__).parents[1] / 'lotus_farm/table_filters.py')
        helper = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'frappe': self.frappe}):
            spec.loader.exec_module(helper)
        self.module._access = Mock()
        self.module._company = Mock()
        rows = [Row(name=str(i),item_code='I',actual_qty=-2 if i==60 else 5,
                    voucher_no='V-'+str(i),warehouse='W',qty_after_transaction=100) for i in range(65)]
        self.frappe.get_list = Mock(side_effect=[[Row(name='W')],[Row(name='I',item_name='Fertilizer')],rows])
        with patch.dict(sys.modules, {'lotus_farm.table_filters':helper}):
            result=self.module.movements('Farm',from_date='2026-10-01',to_date='2026-10-13',column_filters={'out_qty':[2]})
        self.assertEqual(result['total_count'],1)
        self.assertEqual(result['rows'][0].voucher_no,'V-60')
        self.assertEqual(result['rows'][0].in_qty,0)
        self.assertEqual(result['rows'][0].opening_qty,102)
        query=self.frappe.get_list.call_args.kwargs
        self.assertEqual(query['filters']['is_cancelled'],0)
        self.assertEqual(query['filters']['warehouse'],['in',['W']])
        self.assertEqual(query['filters']['item_code'],['in',['I']])
        self.assertEqual(query['filters']['posting_date'],['between',['2026-10-01','2026-10-13']])
        # Faceted choices: other columns' filters apply, the column's own does not.
        self.assertEqual([c['value'] for c in result['filter_values']['voucher_no']],['V-60'])
        self.frappe.has_permission.return_value=False
        with patch.dict(sys.modules, {'lotus_farm.table_filters':helper}), self.assertRaises(ValueError):
            self.module.movements('Farm')

    def test_document_read_rejects_unrelated_doctypes(self):
        self.module._access = Mock()
        with self.assertRaises(ValueError):
            self.module._stock_doc('User', 'Administrator')
        self.frappe.get_doc.assert_not_called()

    def test_simple_submit_does_not_accept_packout_or_serial_documents(self):
        doc = Mock()
        doc.doctype = 'Stock Entry'
        doc.stock_entry_type = 'Repack'
        self.assertFalse(self.module._simple_doc(doc))
        doc.stock_entry_type = 'Material Receipt'
        doc.get.return_value = None
        doc.items = [Mock(item_code='SERIAL',conversion_factor=1,uom='Kg',stock_uom='Kg')]
        self.frappe.get_doc.return_value = Mock(has_batch_no=0, has_serial_no=1)
        self.assertFalse(self.module._simple_doc(doc))


if __name__ == '__main__':
    unittest.main()
