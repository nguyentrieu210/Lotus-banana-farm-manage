"""Safe unit tests: no real employee, material request or accounting record is created."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from lotus_farm import field_proposal as app


class FieldProposalRulesTest(unittest.TestCase):
    def test_material_rows_validate_known_item_and_amount(self):
        item = frappe._dict(item_name="Bao PE", stock_uom="kg", disabled=0)
        with patch.object(frappe, "db", SimpleNamespace(get_value=lambda *a, **k: item)):
            rows = app._clean_lines("Vật tư", [
                {"item_code": "PE-01", "description": "wrong input", "qty": 3, "uom": "kg", "rate": 50000}
            ])
        self.assertEqual(rows[0]["description"], "Bao PE")
        self.assertEqual(rows[0]["amount"], 150000)

    def test_cost_rejects_missing_amount(self):
        with patch.object(frappe, "throw", side_effect=ValueError):
            with self.assertRaises(ValueError):
                app._clean_lines("Chi phí", [{"description": "Thuê máy", "qty": 1, "rate": 0}])

    def test_material_may_have_unknown_price(self):
        rows = app._clean_lines("Vật tư", [{"description": "Dụng cụ cần mua", "qty": 4, "uom": "cái", "rate": 0}])
        self.assertEqual(rows[0]["amount"], 0)

    def test_reject_nan_and_negative_quantities(self):
        for value in (float("nan"), -1, 0, float("inf")):
            with self.subTest(value=value):
                with patch.object(frappe, "throw", side_effect=ValueError):
                    with self.assertRaises(ValueError):
                        app._clean_lines("Chi phí", [{"description": "Bốc xếp", "qty": value, "rate": 10}])

    def test_regular_leader_reads_only_own_proposals(self):
        with patch.object(frappe, "get_roles", return_value=["Lotus Team Leader"]), patch.object(frappe, "db", SimpleNamespace(escape=lambda s: repr(s))):
            self.assertTrue(app.permission(SimpleNamespace(owner="staff"), "read", "staff"))
            self.assertFalse(app.permission(SimpleNamespace(owner="other"), "read", "staff"))
            self.assertFalse(app.permission(SimpleNamespace(owner="staff"), "write", "staff"))
            self.assertIn("owner", app.query("staff"))
            self.assertNotIn("1=1", app.query("staff"))

    def test_supervisor_can_read_but_cannot_write_using_rest(self):
        with patch.object(frappe, "get_roles", return_value=["Lotus Field Supervisor"]):
            self.assertTrue(app.permission(SimpleNamespace(owner="other"), "read", "supervisor"))
            self.assertFalse(app.permission(SimpleNamespace(owner="other"), "write", "supervisor"))
            self.assertEqual(app.query("supervisor"), "1=1")

    def test_no_role_cannot_read(self):
        with patch.object(frappe, "get_roles", return_value=["Employee"]):
            self.assertFalse(app.permission(SimpleNamespace(owner="staff"), "read", "staff"))
            self.assertEqual(app.query("staff"), "1=0")


if __name__ == "__main__":
    unittest.main()
