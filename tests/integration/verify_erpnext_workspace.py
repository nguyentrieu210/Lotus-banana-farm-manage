"""Native navigation and scope regression on procurement.test; never production."""
import unittest
import uuid
import frappe
import verify_procurement as base  # Enforces the disposable site/environment guard.
from lotus_farm import erpnext_workspace as hub


class NativeWorkspace(unittest.TestCase):
    def setUp(self):
        frappe.set_user('Administrator')
        self.user = 'native-' + uuid.uuid4().hex[:8] + '@example.invalid'

    def tearDown(self):
        frappe.set_user('Administrator')
        frappe.db.rollback()
        frappe.clear_cache(user=self.user)

    def stock_user(self):
        doc = frappe.get_doc(dict(doctype='User', email=self.user, first_name='Native Stock', send_welcome_email=0, roles=[dict(role='Stock User')])).insert()
        frappe.set_user(doc.name)
        return doc

    def test_installed_modules_and_stock_lifecycle_are_reachable(self):
        result = hub.catalog(company=base.C, warehouse=base.WH if hasattr(base, 'WH') else None, from_date='2026-10-01', to_date='2026-10-31')
        modules = {r['value'] for r in result['modules']}
        self.assertTrue({'Stock', 'Buying', 'Accounts', 'Assets', 'Selling', 'Payroll', 'Manufacturing'} <= modules)
        stock = {r['name']: r for r in result['rows'] if r['module'] == 'Stock'}
        for name in ('Stock Entry', 'Stock Reconciliation', 'Purchase Receipt', 'Delivery Note', 'Pick List', 'Landed Cost Voucher', 'Serial No', 'Batch', 'Stock Ledger', 'Stock Balance', 'Stock Settings'):
            self.assertIn(name, stock)
        self.assertIn('company=Lotus+Procurement+Test', stock['Stock Entry']['href'])
        self.assertIn('from_date=2026-10-01', stock['Stock Ledger']['href'])
        self.assertEqual(stock['Stock Settings']['href'], '/desk/stock-settings/Stock%20Settings')
        self.assertTrue(all(r['href'].startswith('/desk/') for r in result['rows']))
        self.assertEqual(len({r['id'] for r in result['rows']}), len(result['rows']))

    def test_stock_user_gets_stock_but_no_general_ledger_or_finance_settings(self):
        self.stock_user()
        result = hub.catalog()
        names = {r['name'] for r in result['rows']}
        self.assertIn('Stock Entry', names)
        self.assertIn('Stock Ledger', names)
        self.assertNotIn('General Ledger', names)
        self.assertNotIn('Accounts Settings', names)
        for row in result['rows']:
            if row['kind'] == 'DocType':
                self.assertTrue(frappe.has_permission(row['name'], 'read'))

    def test_module_profile_block_is_honored(self):
        user = self.stock_user()
        frappe.set_user('Administrator')
        user.append('block_modules', dict(module='Stock'))
        user.save(); frappe.clear_cache(user=user.name)
        frappe.set_user(user.name)
        self.assertNotIn('Stock', {r['value'] for r in hub.catalog()['modules']})

    def test_guest_and_website_accounts_cannot_open_catalog(self):
        frappe.set_user('Guest')
        with self.assertRaises(frappe.PermissionError):
            hub.catalog()
        frappe.set_user('Administrator')
        user = frappe.get_doc(dict(doctype='User', email=self.user, first_name='Website', user_type='Website User', send_welcome_email=0)).insert()
        frappe.set_user(user.name)
        with self.assertRaises(frappe.PermissionError):
            hub.catalog()

    def test_company_warehouse_and_date_scope_are_validated(self):
        with self.assertRaises(frappe.PermissionError):
            hub.catalog(company='__not_permitted__')
        with self.assertRaises(frappe.PermissionError):
            hub.catalog(company=base.C, warehouse='__not_permitted__')
        with self.assertRaises(frappe.ValidationError):
            hub.catalog(from_date='2026-10-31', to_date='2026-10-01')


if __name__ == '__main__':
    try:
        unittest.main(verbosity=2)
    finally:
        frappe.db.rollback()
        frappe.destroy()
