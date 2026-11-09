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


class DayReport(unittest.TestCase):
    teams = {"X": "Tổ 01", "Y": "Tổ 02"}

    def report(self, lines):
        return rules.day_report(lines, BLOCKS, self.teams, {"T1": "Đỏ"}, {"R": "Gãy đổ"})

    def test_totals_per_tổ_and_work(self):
        result = self.report([line("Bud Injection", 15, work_team="X", state="Confirmed"), line("Cut Bud", 6, work_team="X", state="Draft"), line("Bud Injection", 4, work_team="Y", state="Confirmed")])
        self.assertEqual(result["totals"]["Bud Injection"]["qty"], 19)
        self.assertEqual([t["name"] for t in result["teams"]], ["Tổ 01", "Tổ 02"])
        self.assertEqual(result["teams"][0]["totals"]["Cut Bud"]["qty"], 6)
        self.assertEqual((result["draft"], result["teams"][0]["draft"]), (1, 1))

    def test_kg_and_hectares_are_kept(self):
        result = self.report([line("Harvest", 10, work_team="X", state="Confirmed", weight_kg=200.5), line("Sucker Select", 4000, work_team="X", state="Confirmed", area_ha=2)])
        self.assertEqual(result["totals"]["Harvest"]["kg"], 200.5)
        self.assertEqual(result["totals"]["Sucker Select"]["area"], 2)

    def test_opening_book_is_not_a_day_of_work(self):
        self.assertEqual(self.report([line(work_team=None, state="Confirmed")])["rows"], [])

    def test_rows_carry_names_for_the_reader(self):
        row = self.report([line("Reject", 2, work_team="X", state="Confirmed", reason="R", reject_stage="After Cut")])["rows"][0]
        self.assertEqual((row["block_code"], row["team_name"], row["ribbon"], row["reason"]), ("A1", "Tổ 01", "Đỏ", "Gãy đổ"))


class Progress(unittest.TestCase):
    def test_each_stage_is_counted_against_the_colour(self):
        lines = [line(qty=100), line("Reject", 2, reject_stage="After Cut"), line("Harvest", 10, "2026-12-21", weight_kg=200)]
        entries = [{"farm_block": "B1", "bunch_tag": "T1", "event_type": "Bag", "qty": 88}, {"farm_block": "B1", "bunch_tag": "T1", "event_type": "Prop", "qty": 44.0}]
        card = rules.progress(lines, entries, TAGS, BLOCKS)[0]
        self.assertEqual((card["cut"], card["bag"], card["care"], card["prop"], card["rejected"], card["harvested"], card["left"]), (100, 88, 0, 44, 2, 10, 88))

    def test_work_on_a_colour_not_cut_in_that_lot_is_ignored(self):
        self.assertEqual(rules.progress([line(block="B1")], [{"farm_block": "B2", "bunch_tag": "T1", "event_type": "Bag", "qty": 5}], TAGS, BLOCKS)[0]["bag"], 0)

    def test_lots_are_listed(self):
        cards = rules.progress([line(block="B2"), line(block="B1")], [], TAGS, BLOCKS)
        self.assertEqual([r["code"] for r in cards[0]["lots"]], ["A1", "A10"])


class Injection(unittest.TestCase):
    def test_by_week_with_gaps_kept(self):
        result = rules.injection([line("Bud Injection", 5, "2026-10-21", tag=None), line("Bud Injection", 7, "2026-11-04", tag=None)], [], BLOCKS)
        self.assertEqual([(w["number"], w["injected"]) for w in result["weeks"]], [(43, 5), (44, 0), (45, 7)])
        self.assertEqual(result["injected"], 12)

    def test_waiting_and_late(self):
        waiting = [{"block": "B1", "date": "2026-10-01", "left": 30, "late_days": 23}, {"block": "B2", "date": "2026-11-05", "left": 20, "late_days": 0}]
        result = rules.injection([], waiting, BLOCKS)
        self.assertEqual((result["waiting"], result["late_total"]), (50, 30))
        self.assertEqual(result["late"][0]["code"], "A1")


class Rejects(unittest.TestCase):
    names = {"R1": "Gãy đổ", "R2": "Sâu bệnh"}

    def test_by_reason_worst_first_and_rate_on_after_cut(self):
        lines = [line("Reject", 3, reject_stage="After Cut", reason="R1"), line("Reject", 8, tag=None, reject_stage="Before Cut", reason="R2"), line("Reject", 2, block="B2", reject_stage="After Cut", reason="R1")]
        result = rules.rejects(lines, 100, BLOCKS, TAGS, self.names)
        self.assertEqual([(c["reason"], c["qty"], c["lots"]) for c in result["cards"]], [("Sâu bệnh", 8, 1), ("Gãy đổ", 5, 2)])
        self.assertEqual((result["total"], result["before"], result["after"], result["rate"]), (13, 8, 5, 5))

    def test_worst_lot_comes_first(self):
        result = rules.rejects([line("Reject", 1, reject_stage="After Cut", reason="R1"), line("Reject", 4, block="B2", reject_stage="After Cut", reason="R1")], 10, BLOCKS, TAGS, self.names)
        self.assertEqual(result["cards"][0]["worst"][0], {"code": "A10", "qty": 4})

    def test_no_cut_no_rate(self):
        self.assertIsNone(rules.rejects([], 0, BLOCKS, TAGS, {})["rate"])


class Harvest(unittest.TestCase):
    def test_kilos_per_bunch_and_real_days(self):
        lines = [line("Harvest", 9, "2026-12-20", weight_kg=180), line("Harvest", 1, "2026-12-30", weight_kg=20)]
        card = rules.harvest(lines, {("B1", "T1"): "2026-10-21"}, TAGS, BLOCKS)["cards"][0]
        self.assertEqual((card["qty"], card["kg"], card["kg_per"], card["days"], card["min_days"], card["max_days"]), (10, 200, 20, 61, 60, 70))

    def test_totals(self):
        result = rules.harvest([line("Harvest", 10, "2026-12-20", weight_kg=205)], {}, TAGS, BLOCKS)
        self.assertEqual((result["qty"], result["kg"], result["kg_per"]), (10, 205, 20.5))
        self.assertIsNone(result["cards"][0]["days"], "no cut on record: the days are not guessed")


class Dashboard(unittest.TestCase):
    def test_every_stage_by_week_and_lot_in_one_place(self):
        lines = [line(qty=10), line("Bud Injection", 7, "2026-10-05", tag=None), line("Harvest", 4, "2026-12-21", weight_kg=80)]
        entries = [{"event_type": "Bag", "farm_block": "B2", "event_date": "2026-10-22", "qty": 3.0}]
        result = rules.dashboard(lines, entries, BLOCKS)
        self.assertEqual((result["totals"]["inject"], result["totals"]["cut"], result["totals"]["bag"], result["totals"]["harvest"], result["totals"]["kg"]), (7, 10, 3, 4, 80))

    def test_weeks_without_work_stay_on_the_calendar(self):
        result = rules.dashboard([line(day="2026-10-21"), line(day="2026-11-04")], [], BLOCKS)
        self.assertEqual([(w["number"], w["cut"]) for w in result["weeks"]], [(43, 10), (44, 0), (45, 10)])

    def test_chon_choi_is_not_a_bunch_stage(self):
        self.assertEqual(rules.dashboard([line("Sucker Select", 4000, tag=None)], [], BLOCKS)["weeks"], [])


class Cube(unittest.TestCase):
    fact = {"week": "2026-W45", "month": "2026-11", "zone": "A", "block": "A1", "team": "Tổ 01", "colour": "Đỏ", "lan": "1"}

    def test_lines_that_differ_only_by_day_are_added(self):
        rows = rules.cube([("cut", self.fact, 3, 0.0), ("cut", dict(self.fact), 4, 0.0)])
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["s"], rows[0]["z"], rows[0]["b"], rows[0]["q"]), ("cut", "A", "A1", 7))

    def test_stages_and_lots_stay_apart(self):
        self.assertEqual(len(rules.cube([("cut", self.fact, 1, 0.0), ("bag", self.fact, 1, 0.0), ("cut", dict(self.fact, block="A2"), 1, 0.0)])), 3)

    def test_a_chich_row_has_no_colour(self):
        self.assertEqual(rules.cube([("inject", {"week": "2026-W45", "zone": "A", "block": "A1"}, 2, 0.0)])[0]["c"], "")

    def test_a_reason_keeps_its_own_row(self):
        rows = rules.cube([("reject", dict(self.fact, reason="Gãy đổ"), 1, 0.0), ("reject", dict(self.fact, reason="Sâu bệnh"), 1, 0.0)])
        self.assertEqual(sorted(r["r"] for r in rows), ["Gãy đổ", "Sâu bệnh"])

    def test_kilos_add_up(self):
        self.assertEqual(rules.cube([("harvest", self.fact, 10, 200.5), ("harvest", self.fact, 5, 100.25)])[0]["k"], 300.75)


if __name__ == "__main__":
    unittest.main()
