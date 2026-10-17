"""DB-free security regression tests for Lotus mobile role + team boundaries.

Run with Python inside the Frappe image; never creates site users or transactions.
"""
import datetime
import importlib.util
import os
from pathlib import Path
import sys
import types
import unittest


class Row(dict):
    def __getattr__(self, key):
        return self.get(key)


class AccessDenied(Exception):
    pass


class FakeFarm:
    def __init__(self, name):
        self.name = name
        self.farm_name = name
        self.doctype = "Farm"

    def check_permission(self, *_args, **_kwargs):
        return True


class Database:
    def get_value(self, doctype, name, field, as_dict=False):
        if doctype == "Daily Work Plan Line":
            value = LINES.get(name)
            return Row(parent=value.parent, work_team=value.work_team, work_type=value.work_type) if value else None
        if doctype == "Work Type":
            return "Bao buồng"
        if doctype == "Farm Block":
            return "Lô A01"
        return None

    def exists(self, *_args, **_kwargs):
        return False


GRANTS = {
    "lead.a": {"farms": {"Farm-A"}, "teams": {"Team-A"}},
    "lead.b": {"farms": {"Farm-A"}, "teams": {"Team-B"}},
    "supervisor.a": {"farms": {"Farm-A"}, "teams": {"Team-A", "Team-B"}},
    "manager.a": {"farms": {"Farm-A"}, "teams": set()},
    "outsider": {"farms": {"Farm-B"}, "teams": {"Team-C"}},
    "unassigned": {"farms": {"Farm-A"}, "teams": set()},
}
ROLES = {
    "lead.a": {"Lotus Team Leader"},
    "lead.b": {"Lotus Team Leader"},
    "supervisor.a": {"Lotus Field Supervisor"},
    "manager.a": {"Lotus Farm Manager"},
    "outsider": {"Lotus Team Leader"},
    "unassigned": {"Lotus Team Leader"},
}
TEAMS = {
    "Team-A": Row(name="Team-A", farm="Farm-A", active=1, team_name="Tổ A"),
    "Team-B": Row(name="Team-B", farm="Farm-A", active=1, team_name="Tổ B"),
    "Team-C": Row(name="Team-C", farm="Farm-B", active=1, team_name="Tổ C"),
}
LINES = {
    "Line-A": Row(name="Line-A", parent="DWP-1", work_team="Team-A", farm_block="Block-A",
                  farm_plot=None, crop_cycle=None, sucker_selection_batch=None,
                  work_type="WT-1", planned_qty=800, required_workdays=10,
                  uom="Bunch", execution_state="Planned", blocked_reason="",
                  start_at=None, due_at=None),
    "Line-B": Row(name="Line-B", parent="DWP-1", work_team="Team-B", farm_block="Block-A",
                  farm_plot=None, crop_cycle=None, sucker_selection_batch=None,
                  work_type="WT-1", planned_qty=1200, required_workdays=12,
                  uom="Bunch", execution_state="Planned", blocked_reason="",
                  start_at=None, due_at=None),
}
PLAN = Row(name="DWP-1", farm="Farm-A", docstatus=1, posting_date="2026-10-17",
           lines=list(LINES.values()))
RESULTS = [
    Row(name="WR-A", farm="Farm-A", docstatus=1, posting_date="2026-10-17",
        farm_block="Block-A", farm_plot=None, work_plan="DWP-1", work_plan_line="Line-A",
        completed_qty=800, actual_workdays=9, unfinished_reason="", modified="2026-10-17"),
    Row(name="WR-B", farm="Farm-A", docstatus=1, posting_date="2026-10-17",
        farm_block="Block-A", farm_plot=None, work_plan="DWP-1", work_plan_line="Line-B",
        completed_qty=1200, actual_workdays=11, unfinished_reason="", modified="2026-10-17"),
]


def records(doctype, filters, fields=None, pluck=None, **_kwargs):
    user = frappe.session.user
    if doctype == "User Permission":
        k = "farms" if filters.get("allow") == "Farm" else "teams"
        return sorted(GRANTS.get(filters.get("user") or user, {}).get(k, ()))
    if doctype == "Work Team":
        rows = [t for t in TEAMS.values()
                if (not filters.get("farm") or t.farm == filters["farm"])
                and (not filters.get("active") or t.active == filters["active"])]
        if isinstance(filters.get("name"), list):
            rows = [t for t in rows if t.name in filters["name"][1]]
        return [t.name for t in rows] if pluck else rows
    if doctype == "Daily Work Plan":
        return ["DWP-1"] if filters.get("farm") == "Farm-A" and filters.get("docstatus") == 1 else []
    if doctype == "Daily Work Result":
        matches = [r for r in RESULTS if
                   (not filters.get("work_plan_line") or r.work_plan_line == filters["work_plan_line"])]
        if filters.get("farm"):
            matches = [r for r in matches if r.farm == filters["farm"]]
        return [r.name for r in matches] if pluck else matches
    raise AssertionError("Unexpected query: " + doctype)


def doc(doctype, name):
    if doctype == "Farm":
        return FakeFarm(name)
    if doctype == "Daily Work Plan":
        if name != "DWP-1":
            raise ValueError("Unknown plan")
        return PLAN
    raise AssertionError("Unexpected doc: " + doctype)


frappe = types.ModuleType("frappe")
frappe.PermissionError = AccessDenied
frappe.session = types.SimpleNamespace(user="lead.a")
frappe.db = Database()
frappe.get_all = records
frappe.get_list = records
frappe.get_doc = doc
frappe.get_roles = lambda user=None: list(ROLES.get(user or frappe.session.user, ()))
frappe.has_permission = lambda *_a, **_k: True
frappe.throw = lambda message, exception=None: (_ for _ in ()).throw((exception or ValueError)(message))
frappe.whitelist = lambda *_a, **_k: lambda f: f
utils = types.ModuleType("frappe.utils")
utils.flt = lambda value: float(value or 0)
utils.getdate = lambda value: value if isinstance(value, datetime.date) else datetime.date.fromisoformat(str(value))
utils.add_days = lambda value, days: utils.getdate(value) + datetime.timedelta(days=int(days))
sys.modules["frappe"] = frappe
sys.modules["frappe.utils"] = utils

package = types.ModuleType("lotus_farm")
package.__path__ = []
sys.modules["lotus_farm"] = package
controls = types.ModuleType("lotus_farm.controls")
controls.farm_allowed = lambda farm, user=None: farm in GRANTS.get(user or frappe.session.user, {}).get("farms", ())
sys.modules["lotus_farm.controls"] = controls
daily_api = types.ModuleType("lotus_farm.daily_api")
daily_api.daily_overview = lambda *_args: {"tasks": []}
sys.modules["lotus_farm.daily_api"] = daily_api

source = Path(os.environ.get("LOTUS_RBAC_SOURCE_ROOT", Path(__file__).resolve().parents[1] / "lotus_farm"))


def load(name):
    spec = importlib.util.spec_from_file_location("lotus_farm." + name, source / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules["lotus_farm." + name] = module
    spec.loader.exec_module(module)
    return module


access = load("mobile_access")
work = load("work_mobile")


class MobileAccessTest(unittest.TestCase):
    def setUp(self):
        frappe.session.user = "lead.a"

    def test_leader_only_sees_own_team(self):
        self.assertEqual(access.allowed_teams("Farm-A"), {"Team-A"})
        with self.assertRaises(AccessDenied):
            access.require_team("Farm-A", "Team-B")
        with self.assertRaises(AccessDenied):
            access.allowed_teams("Farm-B")

    def test_supervisor_and_manager_permissions(self):
        self.assertFalse(access.can_assign("lead.a"))
        self.assertTrue(access.can_capture("lead.a"))
        self.assertTrue(access.can_assign("supervisor.a"))
        self.assertEqual(access.allowed_teams("Farm-A", "supervisor.a"), {"Team-A", "Team-B"})
        self.assertEqual(access.allowed_teams("Farm-A", "manager.a"), {"Team-A", "Team-B"})
        self.assertEqual(access.allowed_teams("Farm-A", "unassigned"), set())

    def test_mixed_team_plan_filtered_server_side(self):
        result = work.day("Farm-A", "2026-10-17")
        self.assertEqual([t["line"] for t in result["tasks"]], ["Line-A"])
        self.assertEqual(result["plans"], [])

    def test_history_does_not_show_other_team(self):
        result = work.history("Farm-A", "2026-10-17")
        self.assertEqual([row.name for row in result["rows"]], ["WR-A"])

    def test_forged_capture_scope_is_rejected(self):
        valid = dict(work_plan="DWP-1", work_plan_line="Line-A", posting_date="2026-10-17",
                     farm_block="Block-A", completed_qty=800, actual_workdays=10)
        self.assertEqual(access.validate_capture("Farm-A", valid)[1].name, "Line-A")
        with self.assertRaises(AccessDenied):
            access.validate_capture("Farm-A", dict(valid, work_plan_line="Line-B"))
        with self.assertRaises(AccessDenied):
            access.validate_capture("Farm-A", dict(valid, farm_block="Block-B"))
        with self.assertRaises(AccessDenied):
            access.validate_capture("Farm-A", dict(valid, admin_override=True))
        with self.assertRaises(ValueError):
            access.validate_capture("Farm-A", dict(valid, completed_qty=1500))
        with self.assertRaises(ValueError):
            access.validate_capture("Farm-A", dict(valid, completed_qty=float("nan")))

    def test_permission_bypass_lifetime_is_scoped(self):
        result = Row(doctype="Daily Work Result", work_plan="DWP-1", work_plan_line="Line-A")
        self.assertFalse(access.can_skip_plan_read(result))
        with access.scoped_result_capture("DWP-1", "Line-A"):
            self.assertTrue(access.can_skip_plan_read(result))
            self.assertFalse(access.can_skip_plan_read(Row(doctype="Daily Work Result", work_plan="DWP-1", work_plan_line="Line-B")))
        self.assertFalse(access.can_skip_plan_read(result))


if __name__ == "__main__":
    unittest.main()
