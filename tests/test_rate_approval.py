"""Checks that above-list piecework cannot be submitted without a real approval."""
import importlib.util
import unittest
from unittest.mock import patch

import frappe

from lotus_farm.rate_approval import resolve_rate, validate_plan, _signature


class FakePlan(frappe._dict):
    def get_doc_before_save(self):
        return None


def sample(state="Pending", docstatus=0):
    line = frappe._dict(name="ROW-1", farm_plot="P-1", crop_cycle="C-1",
                       sucker_selection_batch="", work_type="BAG", work_team="T-1",
                       payment_mode="Piece", planned_qty=800.0,
                       list_piecework_rate=2000.0, requested_piecework_rate=2500.0)
    return FakePlan(name="PLAN-1", owner="manager@example.com", farm="F-1",
                    posting_date="2026-10-15", rate_approval_state=state, docstatus=docstatus,
                    rate_request_reason="Lo kho thi cong",
                    rate_approved_by=None, rate_approved_at=None,
                    rate_approval_signature="", lines=[line])


class RateApprovalTests(unittest.TestCase):
    def setUp(self):
        stub = patch('lotus_farm.rate_approval.frappe.throw', side_effect=frappe.ValidationError)
        stub.start()
        self.addCleanup(stub.stop)
        secret = patch('lotus_farm.rate_approval.frappe.conf', {'encryption_key':'test-key'})
        secret.start()
        self.addCleanup(secret.stop)

    def test_rate_selection(self):
        self.assertFalse(resolve_rate(2000, None, "Piece")["requires_approval"])
        self.assertFalse(resolve_rate(2000, 1900, "Piece")["requires_approval"])
        self.assertTrue(resolve_rate(2000, 2500, "Piece")["requires_approval"])
        with self.assertRaises(ValueError):
            resolve_rate(2000, 2500, "Daywork")
        with self.assertRaises(ValueError):
            resolve_rate(2000, -1, "Piece")

    def test_pending_cannot_be_submitted(self):
        validate_plan(sample("Pending", 0))
        with self.assertRaises(frappe.ValidationError):
            validate_plan(sample("Pending", 1))
        with self.assertRaises(frappe.ValidationError):
            validate_plan(sample("Approved", 1))

    def test_approved_signature_binds_price_quantity_and_reason(self):
        with patch("lotus_farm.rate_approval.frappe.conf", {"encryption_key": "test-key"}):
            doc = sample("Approved", 1)
            doc.rate_approved_by = "approver@example.com"
            doc.rate_approved_at = "2026-10-15 09:00:00"
            doc.rate_approval_signature = _signature(doc)
            validate_plan(doc)
            doc.lines[0].planned_qty = 900
            with self.assertRaises(frappe.ValidationError):
                validate_plan(doc)
            doc.lines[0].planned_qty = 800
            doc.rate_request_reason = "No reason now"
            with self.assertRaises(frappe.ValidationError):
                validate_plan(doc)

    def test_self_approval_rejected(self):
        with patch("lotus_farm.rate_approval.frappe.conf", {"encryption_key": "test-key"}):
            doc = sample("Approved", 1)
            doc.rate_approved_by = doc.owner
            doc.rate_approved_at = "2026-10-15 09:00:00"
            doc.rate_approval_signature = _signature(doc)
            with self.assertRaises(frappe.ValidationError):
                validate_plan(doc)


if __name__ == "__main__":
    unittest.main()
