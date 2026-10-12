"""Exercise controller rules with explicit in-memory Frappe dependencies."""
import copy
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch


class Row(dict):
    def __getattr__(self, name):
        return self.get(name)

    def __setattr__(self, name, value):
        self[name] = value


class PriceGuardTests(unittest.TestCase):
    def setUp(self):
        self.allowed = False
        self.rate = Row(name='R1', unit_price=2000, currency='VND', docstatus=1)
        self.rate.check_permission = lambda *args: None
        self.work = Row(payment_basis='Piece')
        self.api = SimpleNamespace(session=SimpleNamespace(user='creator'),
            get_list=lambda *args, **kwargs: ['R1'],
            get_doc=lambda kind, name: self.rate if kind == 'Work Piece Rate' else self.work,
            throw=lambda msg: (_ for _ in ()).throw(ValueError(msg)))
        modules = {'frappe': self.api,
            'frappe.utils': SimpleNamespace(getdate=lambda x: x, now_datetime=lambda: 'NOW'),
            'lotus_farm.controls': SimpleNamespace(command_allowed=lambda *args: self.allowed)}
        spec = importlib.util.spec_from_file_location('price_guard_under_test',
            Path(__file__).parents[1] / 'lotus_farm/assignment_pay.py')
        self.mod = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, modules):
            spec.loader.exec_module(self.mod)

    def doc(self, price=2000):
        row = Row(name='line1',work_type='bag',uom='Bunch',work_team='team',planned_qty=800,
                  payment_basis='Piece',agreed_unit_price=price,acceptance_criteria='Intact bags',
                  price_reason='Long access route')
        return Row(lines=[row],farm='farm',posting_date='2026-10-12',docstatus=0,
                   owner='creator',modified_by='creator',get_doc_before_save=lambda: None)

    def test_forged_approval_is_replaced_and_direct_submit_blocked(self):
        doc=self.doc(2200)
        doc.lines[0].update(price_approval_state='Approved',price_approved_by='boss')
        self.mod.validate_plan_prices(doc)
        self.assertEqual(doc.lines[0].price_approval_state,'Pending')
        self.assertIsNone(doc.lines[0].price_approved_by)
        doc.docstatus=1
        with self.assertRaises(ValueError): self.mod.validate_plan_prices(doc)

    def test_self_approval_blocked_even_through_command(self):
        doc=self.doc(2200);doc.docstatus=1;self.allowed=True
        with self.assertRaises(ValueError): self.mod.validate_plan_prices(doc)

    def test_distinct_reviewer_records_server_identity(self):
        doc=self.doc(2200);doc.docstatus=1;self.allowed=True;self.api.session.user='reviewer'
        self.mod.validate_plan_prices(doc)
        self.assertEqual(doc.price_approval_state,'Approved')
        self.assertEqual(doc.lines[0].price_approved_by,'reviewer')
        self.assertEqual(doc.lines[0].price_approved_at,'NOW')

    def test_saved_price_snapshot_survives_catalog_change_and_forgery(self):
        doc=self.doc();self.mod.validate_plan_prices(doc)
        before=copy.deepcopy(doc);doc.get_doc_before_save=lambda:before
        self.rate.unit_price=9000
        doc.lines[0].listed_unit_price=1
        doc.lines[0].piece_rate='forged'
        self.mod.validate_plan_prices(doc)
        self.assertEqual(doc.lines[0].listed_unit_price,2000)
        self.assertEqual(doc.lines[0].piece_rate,'R1')

    def test_submitted_price_is_immutable(self):
        doc=self.doc();self.mod.validate_plan_prices(doc);doc.docstatus=1
        before=copy.deepcopy(doc);doc.get_doc_before_save=lambda:before
        doc.lines[0].agreed_unit_price=1
        with self.assertRaises(ValueError): self.mod.protect_submitted_prices(doc)

    def test_daywork_clears_piece_amount(self):
        doc=self.doc();doc.lines[0].payment_basis='Daywork'
        doc.lines[0].estimated_amount=999999
        self.mod.validate_plan_prices(doc)
        self.assertEqual(doc.lines[0].estimated_amount,0)
        self.assertIsNone(doc.lines[0].piece_rate)
