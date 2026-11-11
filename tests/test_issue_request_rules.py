"""Spec 005: rules of yêu cầu cấp vật tư, without Frappe."""
import unittest
from datetime import date

from lotus_farm import issue_request_rules as r


class StateTest(unittest.TestCase):
    def test_states_before_approval(self):
        self.assertEqual(r.state(0), r.DRAFT)
        self.assertEqual(r.state(0, "Draft", sent_at="2026-11-11 08:00"), r.SENT)
        self.assertEqual(r.state(0, "Draft", return_reason="thiếu lô A13"), r.RETURNED)
        self.assertEqual(r.state(0, "Draft", return_reason="   "), r.DRAFT)

    def test_states_after_approval(self):
        self.assertEqual(r.state(1, "Pending", totals=dict(required=6)), r.WAITING)
        self.assertEqual(r.state(1, "Pending", totals=dict(required=6, draft=2)), r.PICKING)
        self.assertEqual(r.state(1, "Partially Ordered", totals=dict(required=6, posted=2)), r.PARTIAL)
        self.assertEqual(r.state(1, "Partially Ordered", totals=dict(required=6, posted=2, draft=1)), r.PICKING)
        self.assertEqual(r.state(1, "Issued", totals=dict(required=6, posted=6)), r.DONE)
        self.assertEqual(r.state(1, "Pending", totals=dict(required=6, posted=6)), r.DONE)
        self.assertEqual(r.state(1, "Stopped", totals=dict(required=6, posted=2)), r.CLOSED)
        self.assertEqual(r.state(2, "Cancelled"), r.CANCELLED)

    def test_every_state_has_a_code(self):
        self.assertEqual(set(r.CODES), set(r.STATES))

    def test_overdue_only_while_something_is_left(self):
        today = date(2026, 11, 11)
        self.assertTrue(r.overdue(r.WAITING, "2026-11-10", today))
        self.assertTrue(r.overdue(r.PARTIAL, date(2026, 11, 1), today))
        self.assertFalse(r.overdue(r.WAITING, "2026-11-11", today))
        for done in (r.DONE, r.CLOSED, r.CANCELLED, r.SENT, r.DRAFT):
            self.assertFalse(r.overdue(done, "2026-11-01", today))


class WhoTest(unittest.TestCase):
    """Chủ vườn 11/11/2026: đội trưởng enters and approves, their own included; tổ trưởng do not make requests."""

    def test_expected_approver_is_the_doi_truong_else_the_farm_manager(self):
        self.assertEqual(r.approver_for("doi@x"), "doi@x")
        self.assertIsNone(r.approver_for(None))

    def test_doi_truong_and_manager_approve_their_own(self):
        self.assertTrue(r.may_approve("doi@x", "doi@x"))
        self.assertTrue(r.may_approve("ql@x", "doi@x", user_is_manager=True))
        self.assertTrue(r.may_approve("ql@x", None, user_is_manager=True))

    def test_others_do_not_approve(self):
        self.assertFalse(r.may_approve("to@x", "doi@x"))
        self.assertFalse(r.may_approve("doi-khac@x", "doi@x"))
        self.assertFalse(r.may_approve("to@x", None))
        self.assertFalse(r.may_approve(None, "doi@x"))

    def test_only_the_doi_truong_or_manager_requests(self):
        members = {"T3", "T5"}
        self.assertIsNone(r.may_request(None, members, supervisor=True))
        self.assertIsNone(r.may_request("T5", members, supervisor=True))
        self.assertIsNotNone(r.may_request("T9", members, supervisor=True))
        self.assertIsNotNone(r.may_request("T3", members, supervisor=False))
        self.assertIsNotNone(r.may_request(None, members, supervisor=False))


class LinesTest(unittest.TestCase):
    def line(self, **kw):
        return dict(dict(item_code="ANVIL", farm_block="A12", qty=1.5, work_type="PHUN"), **kw)

    def test_good_lines_pass(self):
        self.assertEqual(r.line_issues([self.line(), self.line(farm_block="A13")], {"A12", "A13"}, "2026-11-11", "2026-11-11"), [])

    def test_refusals(self):
        zone = {"A12", "A13"}
        self.assertTrue(r.line_issues([], zone))
        self.assertTrue(r.line_issues([self.line(farm_block="B1")], zone))
        self.assertTrue(r.line_issues([self.line(), self.line()], zone))
        self.assertTrue(r.line_issues([self.line(qty=0)], zone))
        self.assertTrue(r.line_issues([self.line(qty=-1)], zone))
        self.assertTrue(r.line_issues([self.line(qty="abc")], zone))
        self.assertTrue(r.line_issues([self.line(), self.line(farm_block="A13", work_type="BON")], zone))
        self.assertTrue(r.line_issues([self.line()], zone, today="2026-11-11", needed="2026-11-10"))
        many = [self.line(item_code=f"I{i}") for i in range(101)]
        self.assertTrue(any("100" in e for e in r.line_issues(many, zone)))
        self.assertEqual(r.line_issues(many[:100], zone), [])

    def test_zone_check_can_be_skipped(self):
        self.assertEqual(r.line_issues([self.line(farm_block="B1")]), [])


class LoweredTest(unittest.TestCase):
    def test_lower_and_drop(self):
        changes = r.lowered({"L1": 1.5, "L2": 1.5}, {"L1": 1.0})
        self.assertEqual(changes, [("L1", 1.5, 1.0), ("L2", 1.5, 0.0)])
        self.assertEqual(r.lowered({"L1": 2}, {"L1": 2}), [])

    def test_raise_add_or_drop_all_refused(self):
        with self.assertRaises(ValueError):
            r.lowered({"L1": 1}, {"L1": 2})
        with self.assertRaises(ValueError):
            r.lowered({"L1": 1}, {"L1": 1, "L9": 1})
        with self.assertRaises(ValueError):
            r.lowered({"L1": 1}, {"L1": 0})
        with self.assertRaises(ValueError):
            r.lowered({"L1": 1}, {"L1": -1})


class SplitTest(unittest.TestCase):
    def test_total_is_kept(self):
        out = r.split_by_area(6, {"A12": 1.2, "A13": 0.9, "A14": 1.1})
        self.assertAlmostEqual(sum(out["shares"].values()), 6, places=9)
        self.assertEqual(out["missing"], [])

    def test_whole_units_by_largest_remainder(self):
        out = r.split_by_area(5, {"A": 1, "B": 1, "C": 1}, whole=True)
        self.assertEqual(sum(out["shares"].values()), 5)
        self.assertEqual(sorted(out["shares"].values()), [1, 2, 2])
        self.assertTrue(all(isinstance(v, int) for v in out["shares"].values()))
        with self.assertRaises(ValueError):
            r.split_by_area(2.5, {"A": 1}, whole=True)

    def test_lot_without_area_is_not_guessed(self):
        out = r.split_by_area(4, {"A": 1, "B": None, "C": 0})
        self.assertEqual(out["missing"], ["B", "C"])
        self.assertEqual(out["shares"], {"A": 4})
        with self.assertRaises(ValueError):
            r.split_by_area(4, {"B": None})

    def test_lot_getting_zero_is_dropped(self):
        out = r.split_by_area(1, {"A": 10, "B": 0.1}, whole=True)
        self.assertEqual(out["shares"], {"A": 1})
        self.assertEqual(out["dropped"], ["B"])


class OtherTest(unittest.TestCase):
    def test_progress(self):
        self.assertEqual(r.progress(10, 4, 3)["remaining"], 3)
        self.assertEqual(r.progress(10, 8, 3)["remaining"], 0)

    def test_duplicates(self):
        found = r.duplicates([dict(item_code="ANVIL", farm_block="A12")],
                             [dict(item_code="ANVIL", farm_block="A12", request="MR-1"), dict(item_code="ANVIL", farm_block="A13", request="MR-2")])
        self.assertEqual([f["request"] for f in found], ["MR-1"])

    def test_title(self):
        self.assertEqual(r.title("Phun thuốc", "Tổ 3", ["A12", "A13"]), "Phun thuốc · Tổ 3 · A12, A13")
        self.assertTrue(r.title("Phun", None, [f"A{i}" for i in range(10)]).endswith("+4"))


class ActionsTest(unittest.TestCase):
    def test_doi_truong_approves_own_draft_at_once(self):
        a = r.actions(r.DRAFT, "doi@x", "doi@x", can_approve=True, can_request=True)
        self.assertTrue(a["approve"] and a["edit"] and a["send"] and a["delete"])
        self.assertFalse(a["return"] or a["withdraw"])

    def test_sent_request(self):
        mine = r.actions(r.SENT, "doi@x", "doi@x", can_approve=True)
        self.assertTrue(mine["withdraw"] and mine["approve"] and mine["lower"])
        self.assertFalse(mine["return"] or mine["edit"])
        manager = r.actions(r.SENT, "ql@x", "doi@x", can_approve=True, is_manager=True)
        self.assertTrue(manager["return"] and manager["approve"])
        other = r.actions(r.SENT, "to@x", "doi@x")
        self.assertFalse(any(other.values()))

    def test_after_approval(self):
        a = r.actions(r.WAITING, "doi@x", "doi@x", approved_by="doi@x")
        self.assertTrue(a["close"] and a["cancel"])
        self.assertFalse(r.actions(r.PICKING, "doi@x", "doi@x", approved_by="doi@x", has_issues=True, has_drafts=True)["close"])
        self.assertFalse(r.actions(r.PARTIAL, "doi@x", "doi@x", approved_by="doi@x", has_issues=True)["cancel"])
        self.assertTrue(r.actions(r.PARTIAL, "kho@x", "doi@x", warehouse_manager=True, has_issues=True)["close"])
        self.assertFalse(r.actions(r.PARTIAL, "to@x", "doi@x", has_issues=True)["close"])

    def test_reopen_and_print(self):
        self.assertTrue(r.actions(r.CLOSED, "doi@x", "x", approved_by="doi@x")["reopen"])
        self.assertTrue(r.actions(r.CLOSED, "ql@x", "x", is_manager=True)["reopen"])
        self.assertFalse(r.actions(r.CLOSED, "kho@x", "x", warehouse_manager=True)["reopen"])
        self.assertFalse(r.actions(r.WAITING, "doi@x", "doi@x")["print"])
        self.assertTrue(r.actions(r.WAITING, "doi@x", "doi@x", can_print=True)["print"])


if __name__ == "__main__":
    unittest.main()
