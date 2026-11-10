"""Small isolated tests for command authorization; no fake DB/concurrency claims."""

import importlib.util
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class GuardError(Exception):
    pass


class TestServerGuards(unittest.TestCase):
    def setUp(self):
        self.frappe = types.ModuleType("frappe")
        self.frappe.session = types.SimpleNamespace(user="operator")
        self.frappe.PermissionError = PermissionError
        self.frappe.get_roles = lambda: ["System Manager"]
        self.frappe.get_all = lambda *args, **kwargs: ["FARM-A"]
        self.frappe.db = types.SimpleNamespace(escape=lambda text: "'" + text.replace("'", "''") + "'")

        def throw(message, exception=GuardError):
            raise exception(message)

        self.frappe.throw = throw
        utils = types.ModuleType("frappe.utils")
        utils.getdate = lambda value: value
        self.patch = patch.dict("sys.modules", {"frappe": self.frappe, "frappe.utils": utils})
        self.patch.start()
        path = Path(__file__).resolve().parents[1] / "lotus_farm/controls.py"
        spec = importlib.util.spec_from_file_location("lotus_test_controls", path)
        self.controls = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.controls)
        self.doc = types.SimpleNamespace(
            doctype="Packhouse Shift",
            name="PS-A",
            flags=types.SimpleNamespace(lotus_allocation_command=True),
        )

    def tearDown(self):
        self.patch.stop()

    def test_client_flags_cannot_authorize_allocation(self):
        self.assertFalse(self.controls.command_allowed(self.doc, "allocation"))

    def test_command_authorization_is_scoped_and_restored(self):
        other = types.SimpleNamespace(doctype="Packhouse Shift", name="PS-B")
        with self.controls.command(self.doc, "allocation"):
            self.assertTrue(self.controls.command_allowed(self.doc, "allocation"))
            self.assertFalse(self.controls.command_allowed(other, "allocation"))
            self.assertFalse(self.controls.command_allowed(self.doc, "supply"))
            self.doc.name = "PS-generated"
            self.assertTrue(self.controls.command_allowed(self.doc, "allocation"))
        self.assertFalse(self.controls.command_allowed(self.doc, "allocation"))

    def test_command_authorization_resets_after_exception(self):
        with self.assertRaises(ValueError):
            with self.controls.command(self.doc, "allocation"):
                raise ValueError("rollback")
        self.assertFalse(self.controls.command_allowed(self.doc, "allocation"))

    def test_system_manager_is_not_business_approver(self):
        with self.assertRaises(PermissionError):
            self.controls.require_role("Lotus Farm Manager")
        self.frappe.get_roles = lambda: ["Lotus Farm Manager"]
        self.controls.require_role("Lotus Farm Manager")

    def test_farm_grants_deny_other_farms(self):
        self.assertTrue(self.controls.farm_allowed("FARM-A"))
        self.assertFalse(self.controls.farm_allowed("FARM-B"))
        self.frappe.get_all = lambda *args, **kwargs: []
        self.assertEqual(self.controls.query_condition("Packhouse Shift"), "1=0")
