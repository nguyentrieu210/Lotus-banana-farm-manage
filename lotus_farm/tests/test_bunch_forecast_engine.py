import datetime as dt
import unittest

from lotus_farm import bunch_flow_rules as flow
from lotus_farm import bunch_forecast_engine as engine
from lotus_farm.forecast_parameters import DEFAULTS, validate

CONFIG = validate(dict(DEFAULTS))
TODAY = dt.date(2026, 11, 9)
BLOCKS = {"B": {"code": "A1", "zone": "A"}, "C": {"code": "B2", "zone": "B"}}
LABELS = {"T": "Đỏ", "U": "Trắng"}


def params(block, day):
    return "P1", CONFIG


def line(event_type="Cut Bud", qty=100, day="2026-10-21", block="B", tag="T", name="x", **extra):
    return dict({"name": name, "event_type": event_type, "qty": qty, "event_date": day, "farm_block": block, "bunch_tag": tag, "cycle_no": 2}, **extra)


def cohorts(lines, today=TODAY):
    return flow.cut_cohorts(lines, params, today)


def total(result):
    return sum(c["bunches"] for c in result)


class ExpectedLeft(unittest.TestCase):
    def test_expected_loss_applies_when_nothing_was_recorded(self):
        self.assertEqual(flow.expected_left(100, 0, 0, .97), 97)

    def test_recorded_rejects_replace_the_expected_loss_up_to_it(self):
        self.assertEqual(flow.expected_left(100, 2, 0, .97), 97, "2 rejected is inside the 3 expected")

    def test_rejects_above_the_expected_loss_count_in_full(self):
        self.assertEqual(flow.expected_left(100, 5, 0, .97), 95)

    def test_harvest_comes_off_and_never_goes_negative(self):
        self.assertEqual(flow.expected_left(100, 0, 40, .97), 57)
        self.assertEqual(flow.expected_left(100, 0, 99, .97), 0)


class Cohorts(unittest.TestCase):
    def test_window_is_60_to_70_days_after_the_cut(self):
        c = cohorts([line()])[0]
        self.assertEqual(c["window_start"], dt.date(2026, 12, 20))
        self.assertEqual(c["window_end"], dt.date(2026, 12, 30))
        self.assertEqual(len(c["days"]), 11)

    def test_spreading_keeps_the_total(self):
        c = cohorts([line(qty=593)])[0]
        self.assertEqual(sum(n for _, n in c["days"]), c["bunches"])
        self.assertEqual(c["bunches"], 575)

    def test_rejects_and_harvest_come_off_the_lot_and_colour_only(self):
        lines = [line(), line(block="C", name="y"), line("Reject", 5, "2026-11-01", reject_stage="After Cut", name="r"),
                 line("Harvest", 10, "2026-11-08", name="h")]
        by = {c["block"]: c["bunches"] for c in cohorts(lines)}
        self.assertEqual(by, {"B": 85, "C": 97})

    def test_reject_before_cut_has_no_effect_here(self):
        self.assertEqual(total(cohorts([line(), line("Reject", 50, tag=None, reject_stage="Before Cut", name="r")])), 97)

    def test_two_cuts_of_a_colour_share_the_loss_and_keep_the_total(self):
        result = cohorts([line(qty=60, name="a"), line(qty=40, day="2026-10-22", name="b")])
        self.assertEqual(sorted(c["bunches"] for c in result), [39, 58])
        self.assertEqual(total(result), 97)

    def test_a_running_window_uses_only_the_days_left(self):
        c = cohorts([line()], dt.date(2026, 12, 26))[0]
        self.assertEqual(c["days"][0][0], dt.date(2026, 12, 26))
        self.assertEqual(sum(n for _, n in c["days"]), 97)
        self.assertFalse(c["overdue"])

    def test_a_window_already_past_lands_on_today_and_is_flagged(self):
        c = cohorts([line()], dt.date(2027, 2, 1))[0]
        self.assertTrue(c["overdue"])
        self.assertEqual(c["days"], [(dt.date(2027, 2, 1), 97)])

    def test_a_colour_fully_harvested_leaves_nothing(self):
        self.assertEqual(cohorts([line(qty=10), line("Harvest", 10, "2026-12-25", name="h")]), [])

    def test_rejects_without_a_cut_are_ignored(self):
        self.assertEqual(cohorts([line("Harvest", 3, name="h")]), [])


class Summary(unittest.TestCase):
    def result(self, lines, today=TODAY, horizon=13):
        return engine.summarize(cohorts(lines, today), BLOCKS, LABELS, today, horizon)

    def test_calendar_has_every_week_starting_this_monday(self):
        weeks = self.result([line()])["weeks"]
        self.assertEqual(len(weeks), 13)
        self.assertEqual(weeks[0]["week"], "2026-W46")
        self.assertEqual(weeks[0]["start"], "2026-11-09")
        self.assertEqual(weeks[0]["bunches"], 0)

    def test_weeks_add_up_to_the_cohort(self):
        result = self.result([line()])
        self.assertEqual(sum(w["bunches"] for w in result["weeks"]), 97)
        self.assertEqual(result["totals"]["bunches"], 97)
        self.assertEqual(sum(r["bunches"] for r in result["rows"]), 97)

    def test_kg_use_the_cycle_of_the_line(self):
        vụ2 = self.result([line()])["totals"]["kg"]
        vụ1 = self.result([line(cycle_no=1)])["totals"]["kg"]
        self.assertAlmostEqual(vụ2, 97 * CONFIG["kg_cycle_2"] * CONFIG["pack_rate"], 2)
        self.assertAlmostEqual(vụ1, 97 * CONFIG["kg_cycle_1"] * CONFIG["pack_rate"], 2)

    def test_cartons_follow_kg(self):
        totals = self.result([line()])["totals"]
        self.assertAlmostEqual(totals["cartons"], totals["kg"] / CONFIG["kg_per_carton"], 2)

    def test_rows_carry_lot_colour_and_confidence(self):
        row = self.result([line()])["rows"][0]
        self.assertEqual((row["block_code"], row["ribbon"], row["layer"], row["confidence"]), ("A1", "Đỏ", "cut", "high"))

    def test_groups_by_lot_zone_and_month_agree(self):
        result = self.result([line(), line(block="C", name="y", tag="U")])
        self.assertEqual(sum(b["bunches"] for b in result["blocks"]), 194)
        self.assertEqual({z["zone"]: z["bunches"] for z in result["zones"]}, {"A": 97, "B": 97})
        self.assertEqual(sum(m["bunches"] for m in result["months"]), 194)

    def test_overdue_is_warned(self):
        self.assertTrue(any("chưa ghi thu hoạch" in w for w in self.result([line()], dt.date(2027, 2, 1))["warnings"]))

    def test_bunches_beyond_the_horizon_are_counted_and_warned(self):
        result = self.result([line(day="2026-11-08")], horizon=2)
        self.assertEqual(result["later"], 97)
        self.assertTrue(result["warnings"])


class Containers(unittest.TestCase):
    def test_units_add_up_per_layer(self):
        totals = engine.summarize(cohorts([line()]), BLOCKS, LABELS, TODAY)["totals"]
        self.assertAlmostEqual(totals["containers"], totals["cartons"] / CONFIG["cartons_per_container"], 3)
        self.assertAlmostEqual(totals["layer_kg"]["cut"], totals["kg"], 2)
        self.assertAlmostEqual(totals["layer_containers"]["cut"], totals["containers"], 3)

    def test_start_dates_cover_what_is_past_the_weeks(self):
        result = engine.summarize(cohorts([line(day="2027-01-05")]), BLOCKS, LABELS, TODAY, horizon=2)
        self.assertEqual(result["zone_starts"], {"A": "2027-03-06"})
        self.assertEqual(result["block_starts"]["B"], {"code": "A1", "zone": "A", "first": "2027-03-06"})


class Pace(unittest.TestCase):
    def tree(self, bunches=970, day=dt.date(2027, 1, 26)):
        return {"layer": "tree", "config": CONFIG, "days": [(day, bunches)]}

    def test_real_cuts_go_to_their_week(self):
        result = engine.cut_pace([], [line(qty=298, day="2026-11-04")], TODAY)
        self.assertEqual(result["last_actual"]["number"], 45)
        self.assertEqual(result["last_actual"]["actual"], 298)

    def test_need_is_the_estimate_moved_back_to_cutting_and_before_loss(self):
        result = engine.cut_pace([self.tree()], [], TODAY)
        self.assertEqual(result["next_need"]["week"], "2026-W47")
        self.assertEqual(result["next_need"]["needed"], 1000)

    def test_a_thin_first_week_is_not_the_pace(self):
        result = engine.cut_pace([self.tree(97, dt.date(2027, 1, 26)), self.tree(3000, dt.date(2027, 2, 2))], [], TODAY)
        self.assertEqual(result["next_need"]["week"], "2026-W48")

    def test_bunches_already_cut_need_no_cutting(self):
        self.assertIsNone(engine.cut_pace([dict(self.tree(), layer="cut")], [], TODAY)["next_need"])

    def test_alert_when_the_need_is_far_above_the_pace(self):
        result = engine.cut_pace([self.tree(2910)], [line(qty=300, day="2026-11-04")], TODAY)
        self.assertTrue(result["alert"])
        self.assertEqual(result["times"], 10)

    def test_no_alert_near_the_pace_or_without_a_pace(self):
        self.assertFalse(engine.cut_pace([self.tree(485)], [line(qty=300, day="2026-11-04")], TODAY)["alert"])
        self.assertFalse(engine.cut_pace([self.tree()], [], TODAY)["alert"])

    def test_past_weeks_have_no_need(self):
        weeks = engine.cut_pace([], [], TODAY)["weeks"]
        self.assertTrue(all(w["needed"] is None for w in weeks if not w["future"]))
        self.assertEqual(len(weeks), 14)


if __name__ == "__main__":
    unittest.main()
