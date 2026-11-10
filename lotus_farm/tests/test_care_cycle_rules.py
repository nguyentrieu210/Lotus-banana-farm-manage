import importlib.util
import pathlib
import unittest
from datetime import date

# Load by path: the rules are pure and this test must run without a bench.
_spec = importlib.util.spec_from_file_location("care_cycle_rules", pathlib.Path(__file__).parents[1] / "care_cycle_rules.py")
rules = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rules)

CUT_LEAF = "CL"
FARM_RULE = {"name": "r-farm", "rule_name": "Cắt lá", "work_type": CUT_LEAF, "repeat_days": 14, "valid_from": "2026-10-01", "valid_to": None,
             "version": 1, "approval_state": "Approved", "farm_zone": ""}
BLOCKS = {"A5": {"code": "A5", "zone": "A"}, "B2": {"code": "B2", "zone": "B"}}


def line(block, day, done=1, work=CUT_LEAF):
    return {"farm_block": block, "work_type": work, "posting_date": day, "done": done}


class CareCycle(unittest.TestCase):
    def rows(self, lines, today, until=None, rule_set=(FARM_RULE,), rounds=None):
        return rules.due_cells(BLOCKS, [CUT_LEAF], list(rule_set), rules.last_done(lines), rounds or {}, today, until or today)

    def test_due_is_last_done_plus_the_cycle_and_late_from_the_day_after(self):
        lines = [line("A5", "2026-11-01")]
        on_due = {r["code"]: r for r in self.rows(lines, date(2026, 11, 15))}["A5"]
        self.assertEqual((on_due["last_done"], on_due["due_date"], on_due["overdue_days"], on_due["status"]), ("2026-11-01", "2026-11-15", 0, "due"))
        self.assertEqual({r["code"]: r for r in self.rows(lines, date(2026, 11, 16))}["A5"]["overdue_days"], 1)
        late = {r["code"]: r for r in self.rows(lines, date(2026, 11, 17))}["A5"]
        self.assertEqual((late["status"], late["overdue_days"]), ("overdue", 2), "spec: cắt lá 14 ngày, xong 01/11, ngày 17/11 quá hạn 2 ngày")

    def test_a_lot_never_done_is_due_from_the_day_the_rule_starts(self):
        b2 = {r["code"]: r for r in self.rows([line("A5", "2026-11-01")], date(2026, 10, 1))}["B2"]
        self.assertEqual((b2["last_done"], b2["due_date"], b2["status"]), (None, "2026-10-01", "due"))

    def test_only_the_day_the_whole_lot_is_done_closes_the_round(self):
        lines = [line("A5", "2026-11-01", done=0), line("A5", "2026-11-02", done=0), line("A5", "2026-11-03"), line("A5", "2026-10-20")]
        self.assertEqual(rules.last_done(lines)[("A5", CUT_LEAF)], date(2026, 11, 3))
        a5 = {r["code"]: r for r in self.rows(lines, date(2026, 11, 10))}["A5"]
        self.assertEqual((a5["due_date"], a5["status"]), ("2026-11-17", "later"))
        self.assertEqual({r["code"]: r for r in self.rows(lines, date(2026, 11, 10), until=date(2026, 11, 22))}["A5"]["status"], "due",
                         "falls due within the week looked at")

    def test_a_khu_rule_wins_over_the_farm_rule_and_the_newest_version_over_older(self):
        zone_rule = dict(FARM_RULE, name="r-a", rule_name="Cắt lá khu A", farm_zone="a", repeat_days=10)
        newer = dict(FARM_RULE, name="r-farm-2", version=2, repeat_days=21)
        rows = {r["code"]: r for r in self.rows([line("A5", "2026-11-01"), line("B2", "2026-11-01")], date(2026, 11, 5), rule_set=(FARM_RULE, zone_rule, newer))}
        self.assertEqual((rows["A5"]["rule"], rows["A5"]["due_date"]), ("r-a", "2026-11-11"))
        self.assertEqual((rows["B2"]["rule"], rows["B2"]["due_date"]), ("r-farm-2", "2026-11-22"))

    def test_a_work_without_a_rule_in_force_is_never_due(self):
        draft = dict(FARM_RULE, approval_state="Draft")
        ended = dict(FARM_RULE, valid_to="2026-10-31")
        future = dict(FARM_RULE, valid_from="2026-12-01")
        for rule_set in ((), (draft,), (ended,), (future,)):
            self.assertEqual(self.rows([line("A5", "2026-11-01")], date(2026, 11, 20), rule_set=rule_set), [], rule_set)

    def test_a_version_ends_the_older_ones_and_a_season_rule_runs_over_the_year_round_one(self):
        later = dict(FARM_RULE, name="r-farm-2", version=2, repeat_days=7, valid_from="2026-12-01")
        stopped = dict(FARM_RULE, name="r-farm-3", version=3, valid_from="2026-10-01", valid_to="2026-11-10")
        self.assertEqual(rules.rule_for([FARM_RULE, later], "A", CUT_LEAF, date(2026, 11, 20))["name"], "r-farm", "v2 has not started yet")
        self.assertEqual(rules.rule_for([FARM_RULE, later], "A", CUT_LEAF, date(2026, 12, 2))["name"], "r-farm-2")
        self.assertIsNone(rules.rule_for([FARM_RULE, stopped], "A", CUT_LEAF, date(2026, 11, 20)), "v1 does not come back after v3 ended")
        rainy = dict(FARM_RULE, name="r-rain", rule_name="Cắt lá mùa mưa", repeat_days=7, valid_from="2026-11-01", valid_to="2027-01-31")
        self.assertEqual(rules.rule_for([FARM_RULE, rainy], "A", CUT_LEAF, date(2026, 11, 20))["name"], "r-rain")
        self.assertEqual(rules.rule_for([FARM_RULE, rainy], "A", CUT_LEAF, date(2027, 2, 2))["name"], "r-farm")

    def test_a_cycle_changed_midway_counts_from_the_last_done_day(self):
        rainy = dict(FARM_RULE, name="r-rain", version=2, repeat_days=7, valid_from="2026-11-05")
        a5 = {r["code"]: r for r in self.rows([line("A5", "2026-11-01")], date(2026, 11, 9), rule_set=(dict(FARM_RULE, valid_to="2026-11-04"), rainy))}["A5"]
        self.assertEqual((a5["rule"], a5["due_date"], a5["overdue_days"]), ("r-rain", "2026-11-08", 1))

    def test_the_tổ_given_shows_and_the_summary_counts_what_is_left_to_give(self):
        rounds = {("A5", CUT_LEAF): {"name": "WA-1", "work_team": "T2"}}
        rows = self.rows([line("A5", "2026-10-01")], date(2026, 11, 20), rounds=rounds)
        a5 = {r["code"]: r for r in rows}["A5"]
        self.assertEqual((a5["assignment"], a5["work_team"]), ("WA-1", "T2"))
        self.assertEqual(rules.summary(rows), [{"work_type": CUT_LEAF, "overdue": 2, "due": 0, "later": 0, "given": 1, "to_give": 1}])

    def test_a_rule_needs_a_work_a_cycle_and_a_start(self):
        self.assertEqual(rules.check_rule({"work_type": "CL", "repeat_days": 14, "valid_from": "2026-11-01"}), [])
        self.assertEqual(len(rules.check_rule({"work_type": "", "repeat_days": 0, "valid_from": ""})), 3)
        self.assertIn("Ngày hết áp dụng không được trước ngày bắt đầu.",
                      rules.check_rule({"work_type": "CL", "repeat_days": 7, "valid_from": "2026-11-10", "valid_to": "2026-11-01"}))

    def test_a_cycle_keeps_its_việc_one_draft_and_the_draft_on_top_however_it_is_saved(self):
        v1, v3 = dict(FARM_RULE, name="r1"), dict(FARM_RULE, name="r3", version=3)
        draft = dict(FARM_RULE, name="r4", version=4, approval_state="Draft")
        self.assertIsNone(rules.version_error(dict(draft, version=1), [], new=True), "the first version of a cycle")
        self.assertIsNone(rules.version_error(draft, [v1, v3], new=True), "a gap in the numbers is allowed")
        self.assertIn("phải chờ duyệt", rules.version_error(dict(draft, approval_state="Approved"), [v1, v3], new=True))
        self.assertIn("việc khác", rules.version_error(dict(draft, work_type="PC"), [v1, v3], new=True))
        self.assertIn("phải lớn hơn 3", rules.version_error(dict(draft, version=2), [v1, v3], new=True))
        self.assertIn("đang có phiên bản chờ duyệt", rules.version_error(dict(draft, name="r5", version=5), [v1, v3, draft], new=True))
        # Danh mục and Desk save the draft itself afterwards: it may change and be approved, never drop below v3.
        self.assertIsNone(rules.version_error(dict(draft, repeat_days=10, version="6"), [v1, v3], new=False))
        self.assertIsNone(rules.version_error(dict(draft, approval_state="Approved"), [v1, v3], new=False), "approving it")
        self.assertIn("phải lớn hơn 3", rules.version_error(dict(draft, version=2), [v1, v3], new=False))
        self.assertIn("phải lớn hơn 3", rules.version_error(dict(draft, version=2, approval_state="Approved"), [v1, v3], new=False))
        self.assertIn("phải lớn hơn 3", rules.version_error(dict(draft, version=3), [v1, v3], new=False), "a number already used")


if __name__ == "__main__":
    unittest.main()
