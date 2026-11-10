import importlib.util
import pathlib
import unittest
from datetime import date

# Load by path: the rules are pure and this test must run without a bench.
_spec = importlib.util.spec_from_file_location("bunch_report_rules", pathlib.Path(__file__).parents[1] / "bunch_report_rules.py")
rules = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rules)

BLOCKS = {"A5": {"code": "A5", "zone": "A"}, "A6": {"code": "A6", "zone": "A"}}
TAGS = {"red46": {"label": "Đỏ", "code": "DO", "week": 46, "year": 2026, "half": 1},
        "red58": {"label": "Đỏ", "code": "DO", "week": 58, "year": 2026, "half": 1}}


def line(block, stage, qty, tag, day, **extra):
    return dict({"farm_block": block, "event_type": stage, "qty": qty, "bunch_tag": tag, "event_date": day}, **extra)


def window(block, first_cut):
    return 60, 70


class RibbonBoard(unittest.TestCase):
    def board(self, lines, bags=None, quarantine=None, today=date(2026, 11, 20)):
        cards = rules.stock(lines, TAGS, BLOCKS, window, today)["cards"]
        return rules.ribbon(cards, bags or {}, quarantine or {}, today)

    def test_each_lot_and_colour_has_cut_bag_rejected_harvested_left_and_age(self):
        lines = [line("A5", "Cut Bud", 120, "red46", "2026-11-11"), line("A5", "Reject", 3, "red46", "2026-11-12", reject_stage="After Cut"),
                 line("A5", "Harvest", 10, "red46", "2026-11-19", weight_kg=200)]
        card = self.board(lines, bags={("A5", "red46"): 100})["cards"][0]
        lot = card["lots"][0]
        self.assertEqual((lot["cut"], lot["bag"], lot["rejected"], lot["harvested"], lot["left"]), (120, 100, 3, 10, 107))
        self.assertEqual(lot["bag_left"], 20)
        self.assertEqual(card["age_weeks"], 1)
        self.assertEqual(card["bag"], 100)

    def test_two_cycles_of_one_colour_stay_apart(self):
        lines = [line("A5", "Cut Bud", 10, "red46", "2026-11-11"), line("A5", "Cut Bud", 20, "red58", "2027-02-03")]
        cards = self.board(lines, today=date(2027, 2, 10))["cards"]
        self.assertEqual(sorted(c["cut"] for c in cards), [10, 20])

    def test_due_list_takes_colours_in_their_harvest_window_and_flags_quarantine(self):
        lines = [line("A5", "Cut Bud", 50, "red46", "2026-09-01"), line("A6", "Cut Bud", 40, "red46", "2026-09-01"),
                 line("A6", "Harvest", 40, "red46", "2026-11-05", weight_kg=800)]
        board = self.board(lines, quarantine={"A5": "2026-11-25"}, today=date(2026, 11, 3))
        due = rules.due_rows(board["cards"])
        self.assertEqual([(r["block"], r["left"]) for r in due], [("A5", 50)], "a lô harvested out is not due any more")
        self.assertEqual(due[0]["quarantine_until"], "2026-11-25")

    def test_nothing_due_before_the_window(self):
        board = self.board([line("A5", "Cut Bud", 50, "red46", "2026-11-11")], today=date(2026, 11, 20))
        self.assertEqual(rules.due_rows(board["cards"]), [])


if __name__ == "__main__":
    unittest.main()
