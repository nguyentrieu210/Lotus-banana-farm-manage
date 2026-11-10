import datetime as dt
import importlib.util
import pathlib
import unittest

_spec = importlib.util.spec_from_file_location("bunch_report_rules", pathlib.Path(__file__).parents[1] / "bunch_report_rules.py")
rules = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rules)

BLOCKS = {"B1": {"code": "A1", "zone": "A"}, "B2": {"code": "A10", "zone": "A"}, "B3": {"code": "A2", "zone": "A"}}
TAGS = {"T1": {"label": "Đỏ", "week": 43, "year": 2026, "half": 1}, "T2": {"label": "Đỏ", "week": 43, "year": 2026, "half": 2}, "U": {"label": "Trắng", "week": 44, "year": 2026, "half": 1}}
TODAY = dt.date(2026, 11, 9)


def days_for(block, first):
    return 60, 70


def line(event_type="Cut Bud", qty=10, day="2026-10-21", block="B1", tag="T1", **extra):
    return dict({"event_type": event_type, "qty": qty, "event_date": day, "farm_block": block, "bunch_tag": tag}, **extra)


def stock(lines, today=TODAY):
    return rules.stock(lines, TAGS, BLOCKS, days_for, today)


class Stock(unittest.TestCase):
    def test_left_is_cut_less_hủy_and_harvest_recorded(self):
        card = stock([line(qty=100), line("Reject", 5, "2026-11-01", reject_stage="After Cut"), line("Harvest", 10, "2026-12-21", weight_kg=200)])["cards"][0]
        self.assertEqual((card["cut"], card["rejected"], card["harvested"], card["left"]), (100, 5, 10, 85))

    def test_no_expected_loss_on_what_is_still_on_the_tree(self):
        self.assertEqual(stock([line(qty=100)])["left"], 100)

    def test_hủy_before_cut_is_not_stock(self):
        self.assertEqual(stock([line(qty=10), line("Reject", 9, tag=None, reject_stage="Before Cut")])["left"], 10)

    def test_window_runs_from_first_cut_plus_60_to_last_cut_plus_70(self):
        card = stock([line(day="2026-10-20"), line(day="2026-10-22", block="B2")])["cards"][0]
        self.assertEqual((card["start"], card["end"]), ("2026-12-19", "2026-12-31"))

    def test_status_follows_the_calendar(self):
        self.assertEqual(stock([line()])["cards"][0]["status"], rules.WAITING)
        self.assertEqual(stock([line()], dt.date(2026, 12, 15))["cards"][0]["status"], rules.DUE, "the window opens this week")
        self.assertEqual(stock([line()], dt.date(2027, 1, 15))["cards"][0]["status"], rules.OVERDUE)
        self.assertEqual(stock([line(qty=10), line("Harvest", 10, "2026-12-21", weight_kg=200)], dt.date(2027, 1, 15))["cards"][0]["status"], rules.DONE)

    def test_summary_counts_only_what_is_left(self):
        result = stock([line(qty=10), line(qty=4, block="B2", tag="U", day="2026-11-20")], dt.date(2027, 1, 19))
        self.assertEqual((result["left"], result["overdue"], result["due"]), (14, 10, 4))

    def test_same_colour_of_another_half_week_is_its_own_card(self):
        self.assertEqual(len(stock([line(tag="T1"), line(tag="T2", day="2026-10-24")])["cards"]), 2)

    def test_lots_are_in_natural_order(self):
        result = stock([line(block="B2"), line(block="B1"), line(block="B3")])
        self.assertEqual([r["code"] for r in result["cards"][0]["lots"]], ["A1", "A2", "A10"])

    def test_lots_outside_the_scope_are_left_out(self):
        self.assertEqual(rules.stock([line(block="B1")], TAGS, {"B2": BLOCKS["B2"]}, days_for, TODAY)["cards"], [])


class CutWeeks(unittest.TestCase):
    def test_lan_comes_from_the_half_week_of_the_colour(self):
        week = rules.cut_weeks([line(qty=20), line(qty=5, tag="T2", day="2026-10-24")], TAGS, BLOCKS)[0]
        self.assertEqual((week["number"], week["lan1"], week["lan2"], week["total"], week["colour"]), (43, 20, 5, 25, "Đỏ"))

    def test_weeks_without_cuts_stay_on_the_calendar(self):
        weeks = rules.cut_weeks([line(day="2026-10-21"), line(day="2026-11-04", tag="U")], TAGS, BLOCKS)
        self.assertEqual([w["number"] for w in weeks], [43, 44, 45])
        self.assertEqual(weeks[1]["total"], 0)

    def test_lots_are_listed_per_week(self):
        week = rules.cut_weeks([line(qty=3, block="B2"), line(qty=2, block="B1")], TAGS, BLOCKS)[0]
        self.assertEqual([(r["code"], r["total"]) for r in week["lots"]], [("A1", 2), ("A10", 3)])

    def test_nothing_cut_is_nothing(self):
        self.assertEqual(rules.cut_weeks([], TAGS, BLOCKS), [])


if __name__ == "__main__":
    unittest.main()
