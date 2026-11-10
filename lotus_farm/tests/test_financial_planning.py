"""Real Frappe persistence/permissions. Run only on a disposable .test site."""
import unittest
from datetime import date
from uuid import uuid4
from unittest.mock import patch

import frappe

from lotus_farm import block_forecast
from lotus_farm.finance import planning, setup


class TestFinancialPlanningOnSite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not str(frappe.local.site).endswith('.test'):
            raise unittest.SkipTest('Financial plan fixtures require a disposable .test site.')
        frappe.set_user('Administrator')
        from erpnext.setup.setup_wizard.operations.install_fixtures import install
        install('Vietnam')
        tag = uuid4().hex[:6]
        cls.company = frappe.get_doc(dict(
            doctype='Company', company_name='Financial Plan Test ' + tag, abbr='FP' + tag,
            country='Vietnam', default_currency='VND', create_chart_of_accounts_based_on='Standard Template',
            chart_of_accounts='Standard',
        )).insert().name
        cls.other_company = frappe.get_doc(dict(
            doctype='Company', company_name='Other Plan Test ' + tag, abbr='FO' + tag,
            country='Vietnam', default_currency='VND', create_chart_of_accounts_based_on='Standard Template',
            chart_of_accounts='Standard',
        )).insert().name
        cls.farm = frappe.get_doc(dict(doctype='Farm', farm_code='FP-' + tag, farm_name='Test Farm', company=cls.company)).insert().name
        cls.other_farm = frappe.get_doc(dict(doctype='Farm', farm_code='FO-' + tag, farm_name='Other Farm', company=cls.other_company)).insert().name
        cls.users = {}
        for key, role in [('accountant', setup.ACCOUNTANT), ('chief', setup.CHIEF), ('auditor', 'Lotus Auditor')]:
            cls.users[key] = frappe.get_doc(dict(doctype='User', email=f'fp-{key}-{tag}@example.invalid',
                first_name=key, send_welcome_email=0, roles=[dict(role=role)])).insert().name
        frappe.db.commit()

    def setUp(self):
        frappe.set_user('Administrator')
        frappe.db.set_single_value(setup.SETTINGS, 'company', self.company)
        self.key = uuid4().hex
        self.values = dict(title='Kế hoạch thử', start_month='2027-01', month_count=12, rows=[
            dict(month='2027-01', gross_kg=1000, sales_kg=800, price_per_kg=10000, labour=3000000)])

    def tearDown(self):
        frappe.set_user('Administrator')
        frappe.db.rollback()

    def as_user(self, key, function, *args, **kwargs):
        frappe.set_user(self.users[key])
        try:
            return function(*args, **kwargs)
        finally:
            frappe.set_user('Administrator')

    def save(self):
        return planning.save(self.values, request_key=self.key)

    def test_roundtrip_retry_and_stale_version(self):
        doc = self.as_user('accountant', self.save)
        retry = self.as_user('accountant', self.save)
        self.assertEqual(doc['name'], retry['name'])
        self.assertEqual(len(planning.detail(doc['name'])['values']['rows']), 12)
        self.assertEqual(doc['result']['base']['totals']['revenue'], 8000000)
        self.values['title'] = 'Đã cập nhật'
        changed = planning.save(self.values, name=doc['name'], modified=doc['modified'])
        with self.assertRaises(frappe.TimestampMismatchError):
            planning.save(self.values, name=doc['name'], modified=doc['modified'])
        self.assertEqual(changed['values']['title'], 'Đã cập nhật')

    def test_approval_permissions_and_native_edit_guard(self):
        gl_before = frappe.db.count('GL Entry', {'company': self.company})
        doc = self.as_user('accountant', self.save)
        with self.assertRaises(frappe.PermissionError):
            self.as_user('accountant', planning.approve, doc['name'], doc['modified'])
        approved = self.as_user('chief', planning.approve, doc['name'], doc['modified'])
        self.assertEqual(approved['state'], 'Approved')
        self.assertEqual(approved['formula_version'], planning.FORMULA_VERSION)
        with patch.object(planning, '_calculate', side_effect=AssertionError('Approved result must be frozen')):
            self.assertEqual(planning.detail(doc['name'])['result'], approved['result'])
        with self.assertRaises(frappe.ValidationError):
            planning.save(self.values, name=doc['name'], modified=approved['modified'])
        raw = frappe.get_doc(planning.DOCTYPE, doc['name'])
        raw.title = 'Native bypass'
        with self.assertRaises(frappe.PermissionError):
            raw.save(ignore_permissions=True)
        with self.assertRaises(frappe.ValidationError):
            frappe.delete_doc(planning.DOCTYPE, doc['name'], ignore_permissions=True)
        clone = self.as_user('accountant', planning.duplicate, doc['name'], self.key + '-clone')
        clone_retry = self.as_user('accountant', planning.duplicate, doc['name'], self.key + '-clone')
        self.assertEqual(clone['name'], clone_retry['name'])
        self.assertEqual(clone['state'], 'Draft')
        self.assertEqual(clone['copied_from'], doc['name'])
        self.assertEqual(planning.detail(doc['name'])['state'], 'Approved')
        self.assertEqual(frappe.db.count('GL Entry', {'company': self.company}), gl_before)

    def test_auditor_reads_but_cannot_save_and_guest_is_denied(self):
        doc = self.save()
        read = self.as_user('auditor', planning.detail, doc['name'])
        self.assertEqual(read['name'], doc['name'])
        with self.assertRaises(frappe.PermissionError):
            self.as_user('auditor', planning.save, self.values, request_key=self.key + '-forbidden')
        frappe.set_user('Guest')
        with self.assertRaises(frappe.AuthenticationError):
            planning.overview()

    def test_company_scope_cannot_be_changed_or_read_through_plan_api(self):
        with self.assertRaises(frappe.ValidationError):
            planning.save(dict(self.values, farm=self.other_farm), request_key=self.key)
        doc = self.save()
        frappe.db.set_value(planning.DOCTYPE, doc['name'], 'company', self.other_company)
        with self.assertRaises(frappe.PermissionError):
            planning.detail(doc['name'])

    def test_native_list_and_read_do_not_bypass_farm_scope(self):
        doc = planning.save(dict(self.values, farm=self.farm), request_key=self.key)
        frappe.set_user(self.users['accountant'])
        self.assertFalse(frappe.has_permission(planning.DOCTYPE, 'read', doc=doc['name']))
        self.assertNotIn(doc['name'], frappe.get_list(planning.DOCTYPE, pluck='name'))
        with self.assertRaises(frappe.PermissionError):
            planning.detail(doc['name'])

    def forecast(self, bunches=50):
        """What the shared forecast hands over for a farm: (summary, bunch cohorts). The forecast itself is built from
        the sổ lô and has its own suites; here 50 bunches of 20 kg, 80% packed, are due in January 2027."""
        return {}, [dict(layer='cut', block='LO', tag=None, cycle=2, profile='BO-THONG-SO', days=[(date(2027, 1, 12), bunches)],
                         config=dict(kg_cycle_1=19, kg_cycle_2=20, kg_cycle_3=19, pack_rate=.8))]

    def test_import_replaces_quantities_retains_budgets_and_checks_source_changes(self):
        doc = self.save()
        with patch.object(block_forecast, 'bunch_summary', return_value=self.forecast()) as read:
            preview = planning.forecast_preview(doc['name'])
        self.assertEqual([call.args for call in read.call_args_list], [(self.farm,)], 'a company plan reads the farms of its own company only')
        self.assertEqual([(s['month'], s['farm'], s['layer'], s['sales_kg']) for s in preview['sources']], [('2027-01', self.farm, 'cut', 800)])
        with patch.object(block_forecast, 'bunch_summary', return_value=self.forecast(bunches=40)):
            with self.assertRaises(frappe.ValidationError):
                planning.apply_forecast(doc['name'], doc['modified'], preview['fingerprint'])
            preview = planning.forecast_preview(doc['name'])
            imported = planning.apply_forecast(doc['name'], doc['modified'], preview['fingerprint'])
            self.assertEqual((imported['values']['rows'][0]['gross_kg'], imported['values']['rows'][0]['sales_kg']), (800, 640))
            self.assertEqual(imported['values']['rows'][0]['labour'], 3000000)
            self.assertEqual(imported['source_snapshot']['sources'][0]['bunches'], 40)
            again = planning.forecast_preview(doc['name'])
            imported = planning.apply_forecast(doc['name'], imported['modified'], again['fingerprint'])
            self.assertEqual(imported['values']['rows'][0]['sales_kg'], 640)

    def test_forecast_import_needs_the_right_to_see_the_farm(self):
        doc = self.save()
        with patch.object(block_forecast, 'bunch_summary', return_value=self.forecast()) as read:
            with self.assertRaises(frappe.PermissionError):
                self.as_user('accountant', planning.forecast_preview, doc['name'])
        read.assert_not_called()
        self.assertFalse(self.as_user('accountant', planning.overview)['can_forecast'])
        self.assertTrue(planning.overview()['can_forecast'])

    def test_manual_updates_keep_source_audit_and_scope_change_clears_it(self):
        doc = self.save()
        with patch.object(block_forecast, 'bunch_summary', return_value=self.forecast()):
            preview = planning.forecast_preview(doc['name'])
            imported = planning.apply_forecast(doc['name'], doc['modified'], preview['fingerprint'])
        values = imported['values']
        values['rows'][0]['sales_kg'] = 600
        updated = planning.save(values, name=doc['name'], modified=imported['modified'])
        self.assertTrue(updated['source_snapshot']['sources'])
        values['farm'] = self.farm
        changed = planning.save(values, name=doc['name'], modified=updated['modified'])
        self.assertEqual(changed['source_snapshot'], {})
