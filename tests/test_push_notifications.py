"""Spec 005 (FR-036): approving a yêu cầu cấp vật tư does not tell the purchase approvers "Có đề xuất mua mới"."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class RecipientsTest(unittest.TestCase):
    def setUp(self):
        frappe = types.ModuleType("frappe")
        frappe.whitelist = lambda *a, **k: (lambda f: f)
        frappe.get_all = lambda doctype, filters=None, **k: ["mua@x", "giamdoc@x"] if filters and filters.get("role") == "Lotus Purchase Approver" else []
        frappe.db = types.SimpleNamespace(get_value=lambda *a, **k: 1, exists=lambda *a, **k: False)
        utils = types.ModuleType("frappe.utils")
        utils.now_datetime = lambda: None
        self.patch = patch.dict(sys.modules, {"frappe": frappe, "frappe.utils": utils})
        self.patch.start()
        self.addCleanup(self.patch.stop)
        path = Path(__file__).resolve().parents[1] / "lotus_farm/push_notifications.py"
        spec = importlib.util.spec_from_file_location("push_under_test", path)
        self.api = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.api)

    def doc(self, kind):
        doc = types.SimpleNamespace(doctype="Material Request", name="MR-1", owner="doi@x", material_request_type=kind,
                                    has_permission=lambda *a, **k: True)
        doc.get = lambda key, default=None: getattr(doc, key, default)
        return doc

    def test_issue_request_has_no_purchase_recipients(self):
        self.assertEqual(self.api._recipients(self.doc("Material Issue"), "submitted"), [])

    def test_purchase_proposal_keeps_its_recipients(self):
        self.assertEqual(self.api._recipients(self.doc("Purchase"), "submitted"), ["giamdoc@x", "mua@x"])


if __name__ == "__main__":
    unittest.main()
