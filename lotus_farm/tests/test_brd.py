"""Run inside a disposable ERPNext site; these are NOT part of pure unit checks."""

import unittest
import frappe
from frappe.utils import nowdate


class TestBRDOnSite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        from erpnext.setup.setup_wizard.operations.install_fixtures import install

        install("India")
        year = int(nowdate()[:4])
        if not frappe.db.exists("Fiscal Year", str(year)):
            frappe.get_doc(dict(
                doctype="Fiscal Year", year=str(year),
                year_start_date=f"{year}-01-01", year_end_date=f"{year}-12-31",
            )).insert()
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")
        frappe.db.savepoint("lotus_brd_test")
        self.tag = frappe.generate_hash(length=8)
        self.company = self.make(
            "Company",
            company_name="Lotus Test " + self.tag,
            abbr=self.tag,
            country="India",
            default_currency="INR",
            create_chart_of_accounts_based_on="Standard Template",
            chart_of_accounts="Standard",
            enable_perpetual_inventory=1,
        ).name
        self.farm = self.make("Farm", farm_code="F-" + self.tag, farm_name="Test", company=self.company).name
        self.variety = self.make("Banana Variety", variety_code="V-" + self.tag, variety_name="Test").name
        self.block = self.make(
            "Farm Block", farm=self.farm, block_code="A12", block_name="A12", area_ha=1, variety=self.variety
        ).name

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback(save_point="lotus_brd_test")

    @staticmethod
    def make(doctype, **values):
        # Disposable sites can be restored with a user's default Company. Farm
        # fixtures must carry their explicit Company through custom-field
        # defaults too, rather than inheriting an unrelated installed company.
        if "company" not in values and values.get("farm") and frappe.get_meta(doctype).has_field("company"):
            values["company"] = frappe.db.get_value("Farm", values["farm"], "company")
        return frappe.get_doc(dict(doctype=doctype, **values)).insert()

    def test_farm_permission_denies_other_farm(self):
        from lotus_farm.controls import farm_allowed

        user = self.make(
            "User",
            email=self.tag + "@example.invalid",
            first_name="Operator",
            send_welcome_email=0,
            roles=[dict(role="Lotus Farm Manager")],
        ).name
        self.assertFalse(farm_allowed(self.farm, user))
        self.make("User Permission", user=user, allow="Farm", for_value=self.farm)
        self.assertTrue(farm_allowed(self.farm, user))
        other = self.make("Farm", farm_code="F2-" + self.tag, farm_name="Other", company=self.company)
        self.assertFalse(farm_allowed(other.name, user))
        frappe.set_user(user)
        self.assertTrue(frappe.get_doc("Farm Block", self.block).has_permission("read"))
        with self.assertRaises(frappe.PermissionError):
            other.check_permission("read")
        self.assertEqual(frappe.get_list("Farm", pluck="name"), [self.farm])
        from lotus_farm.console import detail,audit,listing
        with self.assertRaises(frappe.PermissionError):detail('Farm',other.name)
        with self.assertRaises(frappe.PermissionError):audit('Farm',other.name)
        self.assertNotIn(other.name,[r.name for r in listing('Farm')['rows']])

    def test_farm_with_blocks_keeps_its_company(self):
        other = self.make(
            "Company",
            company_name="Lotus Other " + self.tag,
            abbr="O" + self.tag[:7],
            country="India",
            default_currency="INR",
            create_chart_of_accounts_based_on="Standard Template",
            chart_of_accounts="Standard",
        ).name
        farm = frappe.get_doc("Farm", self.farm)
        farm.farm_name = "Renamed"
        farm.save()
        farm.company = other
        with self.assertRaises(frappe.ValidationError):
            farm.save()

    def test_master_codes_are_stable_and_team_codes_unique(self):
        disease = self.make("Disease", disease_code="D-" + self.tag, disease_name="Test")
        disease.disease_name = "Renamed"
        disease.save()
        disease.disease_code = "X-" + self.tag
        with self.assertRaises(frappe.ValidationError):
            disease.save()
        self.make("Work Team", farm=self.farm, team_code="T1", team_name="Team 1")
        with self.assertRaises(frappe.ValidationError):
            self.make("Work Team", farm=self.farm, team_code="T1", team_name="Team 1 again")
