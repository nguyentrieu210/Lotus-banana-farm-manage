"""Real profile persistence and authorization; disposable .test sites only."""
import unittest
from uuid import uuid4
import frappe
from lotus_farm import forecast_profiles
from lotus_farm.forecast_parameters import DEFAULTS


class TestForecastProfilesOnSite(unittest.TestCase):
    def setUp(self):
        if not str(frappe.local.site).endswith('.test'):
            self.skipTest('Forecast fixtures require a disposable .test site.')
        frappe.set_user('Administrator')
        key=uuid4().hex[:8]
        company=frappe.get_all('Company',pluck='name',limit_page_length=1)[0]
        self.farm=frappe.get_doc(dict(doctype='Farm',farm_code='FC-'+key,farm_name='Forecast test',company=company)).insert().name
        self.values=dict(DEFAULTS,profile_name='Book2 test',valid_from='2026-01-01',valid_to='2030-12-31',source_reference='Test fixture',notes='Approval fixture on isolated site.')

    def tearDown(self):
        frappe.set_user('Administrator')
        frappe.db.rollback()

    def test_approved_profile_is_locked_and_successor_cannot_overlap(self):
        saved=forecast_profiles.save_draft(self.farm,self.values)
        forecast_profiles.approve(saved['name'],str(saved['modified']))
        doc=frappe.get_doc(forecast_profiles.DOCTYPE,saved['name'])
        self.assertEqual(doc.approved_by,'Administrator')
        with self.assertRaises(frappe.ValidationError):
            forecast_profiles.save_draft(self.farm,self.values,doc.name,str(doc.modified))
        successor=forecast_profiles.save_draft(self.farm,self.values)
        self.assertEqual(successor['version'],2)
        with self.assertRaises(frappe.ValidationError):
            forecast_profiles.approve(successor['name'],str(successor['modified']))

    def test_stale_edit_rejected_and_auditor_cannot_approve(self):
        saved=forecast_profiles.save_draft(self.farm,self.values)
        with self.assertRaises(frappe.ValidationError):
            forecast_profiles.save_draft(self.farm,self.values,saved['name'],'stale')
        email='forecast-'+uuid4().hex[:8]+'@example.invalid'
        frappe.get_doc(dict(doctype='User',email=email,first_name='Forecast auditor',send_welcome_email=0,roles=[dict(role='Lotus Auditor')])).insert()
        frappe.set_user(email)
        listed=forecast_profiles.list_profiles(self.farm)
        self.assertFalse(listed['can_approve'])
        with self.assertRaises(frappe.PermissionError):
            forecast_profiles.approve(saved['name'],str(saved['modified']))
