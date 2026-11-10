"""DB-free security regression tests for Lotus role + team boundaries.

Run with Python inside the Frappe image; never creates site users or transactions.
"""
import importlib.util
import os
from pathlib import Path
import sys
import types
import unittest
from unittest import mock


class Row(dict):
    def __getattr__(self, key):
        return self.get(key)


class AccessDenied(Exception):
    pass


GRANTS = {
    "lead.a": {"farms": {"Farm-A"}, "teams": {"Team-A"}},
    "lead.b": {"farms": {"Farm-A"}, "teams": {"Team-B"}},
    "supervisor.a": {"farms": {"Farm-A"}, "teams": {"Team-A", "Team-B"}},
    "manager.a": {"farms": {"Farm-A"}, "teams": set()},
    "auditor.a": {"farms": {"Farm-A"}, "teams": set()},
    "outsider": {"farms": {"Farm-B"}, "teams": {"Team-C"}},
    "unassigned": {"farms": {"Farm-A"}, "teams": set()},
    "clerk": {"farms": {"Farm-A"}, "teams": {"Team-A"}},
}
ROLES = {
    "lead.a": {"Lotus Team Leader"},
    "lead.b": {"Lotus Team Leader"},
    "supervisor.a": {"Lotus Field Supervisor"},
    "manager.a": {"Lotus Farm Manager"},
    "auditor.a": {"Lotus Auditor"},
    "outsider": {"Lotus Team Leader"},
    "unassigned": {"Lotus Team Leader"},
    "clerk": {"Stock User"},
}
TEAMS = {
    "Team-A": Row(name="Team-A", farm="Farm-A", active=1, team_name="Tổ A"),
    "Team-B": Row(name="Team-B", farm="Farm-A", active=1, team_name="Tổ B"),
    "Team-C": Row(name="Team-C", farm="Farm-B", active=1, team_name="Tổ C"),
    "Team-Old": Row(name="Team-Old", farm="Farm-A", active=0, team_name="Tổ đã nghỉ"),
}


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
    raise AssertionError("Unexpected query: " + doctype)


frappe = types.ModuleType("frappe")
frappe.PermissionError = AccessDenied
frappe.session = types.SimpleNamespace(user="lead.a")
frappe.get_all = records
frappe.get_roles = lambda user=None: list(ROLES.get(user or frappe.session.user, ()))
frappe.throw = lambda message, exception=None: (_ for _ in ()).throw((exception or ValueError)(message))
package = types.ModuleType("lotus_farm")
package.__path__ = []
controls = types.ModuleType("lotus_farm.controls")
controls.farm_allowed = lambda farm, user=None: farm in GRANTS.get(user or frappe.session.user, {}).get("farms", ())
# Stubs are only installed while loading and inside each test, so other test
# modules in the same process still import the real lotus_farm package.
STUBS = {"frappe": frappe, "lotus_farm": package, "lotus_farm.controls": controls}

source = Path(os.environ.get("LOTUS_RBAC_SOURCE_ROOT", Path(__file__).resolve().parents[1] / "lotus_farm"))


def load(name):
    spec = importlib.util.spec_from_file_location("lotus_farm." + name, source / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    STUBS["lotus_farm." + name] = module
    sys.modules["lotus_farm." + name] = module
    spec.loader.exec_module(module)
    return module


with mock.patch.dict(sys.modules, STUBS):
    access = load("mobile_access")


class MobileAccessTest(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.dict(sys.modules, STUBS)
        patcher.start()
        self.addCleanup(patcher.stop)
        frappe.session.user = "lead.a"

    def test_leader_only_sees_own_team(self):
        self.assertEqual(access.allowed_teams("Farm-A"), {"Team-A"})
        self.assertEqual(access.allowed_teams("Farm-A", "lead.b"), {"Team-B"})
        with self.assertRaises(AccessDenied):
            access.allowed_teams("Farm-B")
        with self.assertRaises(AccessDenied):
            access.allowed_teams("Farm-A", "outsider")

    def test_supervisor_manager_and_auditor_scope(self):
        self.assertFalse(access.is_manager("lead.a"))
        self.assertFalse(access.is_manager("supervisor.a"))
        self.assertTrue(access.is_manager("manager.a"))
        self.assertTrue(access.is_manager("Administrator"))
        self.assertEqual(access.allowed_teams("Farm-A", "supervisor.a"), {"Team-A", "Team-B"})
        self.assertEqual(access.allowed_teams("Farm-A", "manager.a"), {"Team-A", "Team-B"}, "every active team, no retired one")
        self.assertEqual(access.allowed_teams("Farm-A", "auditor.a"), {"Team-A", "Team-B"})

    def test_no_team_without_a_grant_or_a_field_role(self):
        self.assertEqual(access.allowed_teams("Farm-A", "unassigned"), set())
        self.assertEqual(access.allowed_teams("Farm-A", "clerk"), set(), "a team grant without a field role opens nothing")
        self.assertEqual(access.roles("Guest"), set())

    def test_farm_grant_is_required(self):
        access.require_farm("Farm-A")
        for farm in ("Farm-B", "", None):
            with self.assertRaises(AccessDenied):
                access.require_farm(farm)


if __name__ == "__main__":
    unittest.main()
