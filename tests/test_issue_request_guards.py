"""Spec 005: a Material Issue request is approved, cancelled, stopped and reopened only through lotus_farm.issue_request.
The hooks run with a fake frappe; the real database checks are in tests/integration/verify_issue_request.py."""
import importlib.util
import sys
import types
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch


class Refused(Exception):
    pass


class Doc:
    doctype = "Material Request"

    def __init__(self, before=None, new=False, **values):
        self.values = dict(name="MR-1", owner="doi@x", docstatus=0, status="Draft", material_request_type="Material Issue",
                           lotus_crew="DOI-AB", items=[])
        self.values.update(values)
        self.before = before
        self.new = new
        self.flags = types.SimpleNamespace()

    def __getattr__(self, key):
        try:
            return self.__dict__["values"][key]
        except KeyError:
            raise AttributeError(key)

    def get(self, key, default=None):
        return self.values.get(key, default)

    def is_new(self):
        return self.new

    def get_doc_before_save(self):
        return self.before


def line(**kw):
    return dict(dict(item_code="ANVIL", lotus_farm_block="A12", qty=1.5, warehouse="KHO", lotus_work_type="PHUN"), **kw)


class GuardTest(unittest.TestCase):
    def setUp(self):
        self.allowed = set()
        frappe = types.ModuleType("frappe")
        frappe.PermissionError = type("PermissionError", (Refused,), {})
        frappe.ValidationError = type("ValidationError", (Refused,), {})
        frappe.TimestampMismatchError = frappe.ValidationError

        def throw(message, exc=None):
            raise (exc or frappe.ValidationError)(message)

        frappe.throw = throw
        frappe.whitelist = lambda *a, **k: (lambda f: f)
        frappe.session = types.SimpleNamespace(user="doi@x")
        self.roles = {"ql@x": ["Lotus Farm Manager"]}
        frappe.get_roles = lambda user=None: self.roles.get(user, [])
        frappe.db = types.SimpleNamespace(get_value=lambda dt, name, field=None, *a, **k: "doi@x" if (dt, field) == ("Work Team", "lotus_leader") else None)
        utils = types.ModuleType("frappe.utils")
        utils.flt = lambda v, *a: float(v or 0)
        utils.cint = lambda v: int(v or 0)
        for name in ("add_days", "getdate", "now_datetime", "nowdate"):
            setattr(utils, name, lambda *a: None)
        controls = types.ModuleType("lotus_farm.controls")
        allowed = self.allowed
        controls.command_allowed = lambda doc, action: (id(doc), action) in allowed

        @contextmanager
        def command(doc, action):
            allowed.add((id(doc), action))
            try:
                yield
            finally:
                allowed.discard((id(doc), action))

        controls.command = command
        controls.lock = lambda *a: None
        self.patch = patch.dict(sys.modules, {"frappe": frappe, "frappe.utils": utils, "lotus_farm.controls": controls})
        self.patch.start()
        self.addCleanup(self.patch.stop)
        path = Path(__file__).resolve().parents[1] / "lotus_farm/issue_request.py"
        spec = importlib.util.spec_from_file_location("issue_request_under_test", path)
        self.api = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.api)
        self.frappe = frappe

    def writing(self):
        token = self.api._writing.set(True)
        self.addCleanup(self.api._writing.reset, token)

    # ------------------------------------------------------------ validate
    def test_lotus_request_is_written_only_through_the_api(self):
        doc = Doc(new=True, items=[line()])
        with self.assertRaises(self.frappe.PermissionError):
            self.api.validate(doc)
        self.writing()
        self.api.validate(doc)

    def test_desk_draft_without_doi_is_left_alone(self):
        self.api.validate(Doc(new=True, lotus_crew=None, items=[line()]))

    def test_doi_cannot_be_put_on_or_taken_off_outside_the_api(self):
        before = Doc(items=[line()])
        with self.assertRaises(self.frappe.PermissionError):
            self.api.validate(Doc(before=before, lotus_crew=None, items=[line()]))

    def test_lines_do_not_change_while_waiting_for_approval(self):
        self.writing()
        before = Doc(lotus_issue_sent_at="2026-11-11 08:00", items=[line()])
        doc = Doc(before=before, lotus_issue_sent_at="2026-11-11 08:00", items=[line(qty=3)])
        with self.assertRaises(self.frappe.ValidationError):
            self.api.validate(doc)
        with self.api.command(doc, "issue-approve"):
            self.api.validate(doc)
        self.api.validate(Doc(before=before, lotus_issue_sent_at=None, items=[line()]))

    def test_duplicate_lines_refused_on_save(self):
        self.writing()
        with self.assertRaises(self.frappe.ValidationError):
            self.api.validate(Doc(new=True, items=[line(), line()]))

    # ------------------------------------------------------------ submit
    def test_submit_needs_the_lotus_approval(self):
        doc = Doc(lotus_issue_approved_by="doi@x")
        with self.assertRaises(self.frappe.PermissionError):
            self.api.before_submit(doc)
        doc.flags.lotus_issue_approval = True
        with self.assertRaises(self.frappe.PermissionError):
            self.api.before_submit(doc)  # flag without the command (Desk / REST)
        with self.api.command(doc, "issue-approve"):
            self.api.before_submit(doc)

    def test_doi_truong_may_approve_own_request(self):
        doc = Doc(owner="doi@x", lotus_issue_approved_by="doi@x")
        doc.flags.lotus_issue_approval = True
        with self.api.command(doc, "issue-approve"):
            self.api.before_submit(doc)

    def test_manager_approves_any_but_others_do_not(self):
        doc = Doc(owner="ql@x", lotus_issue_approved_by="ql@x")
        doc.flags.lotus_issue_approval = True
        with self.api.command(doc, "issue-approve"):
            self.api.before_submit(doc)
        doc = Doc(owner="doi@x", lotus_issue_approved_by="to@x")
        doc.flags.lotus_issue_approval = True
        with self.api.command(doc, "issue-approve"):
            with self.assertRaises(self.frappe.PermissionError):
                self.api.before_submit(doc)
        doc = Doc(owner="doi@x", lotus_issue_approved_by=None)
        doc.flags.lotus_issue_approval = True
        with self.api.command(doc, "issue-approve"):
            with self.assertRaises(self.frappe.PermissionError):
                self.api.before_submit(doc)

    def test_desk_request_without_doi_needs_a_manager(self):
        doc = Doc(lotus_crew=None, owner="kho@x", lotus_issue_approved_by="doi@x")
        doc.flags.lotus_issue_approval = True
        with self.api.command(doc, "issue-approve"):
            with self.assertRaises(self.frappe.PermissionError):
                self.api.before_submit(doc)

    # ------------------------------------------------------------ cancel, trash, stop
    def test_cancel_only_in_command(self):
        doc = Doc(docstatus=1)
        with self.assertRaises(self.frappe.PermissionError):
            self.api.before_cancel(doc)
        with self.api.command(doc, "issue-cancel"):
            self.api.before_cancel(doc)

    def test_trash_only_through_the_api(self):
        with self.assertRaises(self.frappe.PermissionError):
            self.api.on_trash(Doc())
        self.api.on_trash(Doc(lotus_crew=None))
        self.writing()
        self.api.on_trash(Doc())

    def test_update_after_submit_only_through_the_api(self):
        with self.assertRaises(self.frappe.PermissionError):
            self.api.before_update_after_submit(Doc(docstatus=1))

    def test_stop_and_reopen_only_in_command(self):
        doc = Doc(before=Doc(docstatus=1, status="Pending"), docstatus=1, status="Stopped")
        with self.assertRaises(self.frappe.PermissionError):
            self.api.on_change(doc)
        with self.api.command(doc, "issue-close"):
            self.api.on_change(doc)
        doc = Doc(before=Doc(docstatus=1, status="Stopped"), docstatus=1, status="Pending")
        with self.assertRaises(self.frappe.PermissionError):
            self.api.on_change(doc)
        with self.api.command(doc, "issue-reopen"):
            self.api.on_change(doc)

    def test_erpnext_own_status_changes_pass(self):
        for old, new in (("Draft", "Pending"), ("Pending", "Partially Ordered"), ("Partially Ordered", "Issued"),
                         ("Issued", "Partially Ordered"), ("Pending", "Cancelled"), ("Stopped", "Cancelled")):
            self.api.on_change(Doc(before=Doc(docstatus=1, status=old), docstatus=1, status=new))

    def test_purchase_requests_are_not_touched(self):
        purchase = dict(material_request_type="Purchase")
        self.api.validate(Doc(new=True, **purchase))
        self.api.before_submit(Doc(**purchase))
        self.api.before_cancel(Doc(**purchase))
        self.api.on_trash(Doc(**purchase))
        self.api.before_update_after_submit(Doc(**purchase))
        self.api.on_change(Doc(before=Doc(status="Pending", **purchase), status="Stopped", **purchase))


if __name__ == "__main__":
    unittest.main()
