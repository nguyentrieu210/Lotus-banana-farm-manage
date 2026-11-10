import datetime as dt
import importlib.util
import pathlib
import unittest

_spec = importlib.util.spec_from_file_location("forecast_snapshot_rules", pathlib.Path(__file__).parents[1] / "forecast_snapshot_rules.py")
rules = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rules)

TODAY = dt.date(2027, 4, 1)


def cut(qty=120, day="2026-10-21", block="A5", tag="T"):
    return {"event_type": "Cut Bud", "qty": qty, "event_date": day, "farm_block": block, "bunch_tag": tag}


def harvest(qty=114, kg=2280, day="2026-12-25", block="A5", tag="T"):
    return {"event_type": "Harvest", "qty": qty, "weight_kg": kg, "event_date": day, "farm_block": block, "bunch_tag": tag}


def row(week="2026-W52", bunches=100, kg=2000, block="A5", tag="T", ribbon="Đỏ"):
    return {"week": week, "bunches": bunches, "kg": kg, "block": block, "block_code": block, "tag": tag, "ribbon": ribbon}


class ColourResults(unittest.TestCase):
    def test_the_spec_example(self):
        r = rules.colour_results([cut(), harvest()], TODAY)[0]
        self.assertEqual(r["rate"], .95)
        self.assertEqual(r["kg_per_bunch"], 20)
        self.assertEqual(r["days"], 65)

    def test_days_are_weighted_by_bunches(self):
        r = rules.colour_results([cut(10), harvest(9, 180, "2026-12-20"), harvest(1, 20, "2026-12-30")], TODAY)[0]
        self.assertEqual(r["days"], 61)
        self.assertEqual((r["min_days"], r["max_days"]), (60, 70))

    def test_a_colour_without_harvest_says_nothing(self):
        self.assertEqual(rules.colour_results([cut()], TODAY), [])

    def test_finished_when_all_came_in_or_time_is_up(self):
        self.assertTrue(rules.colour_results([cut(10), harvest(10, 200)], dt.date(2026, 12, 26))[0]["closed"])
        self.assertFalse(rules.colour_results([cut(10), harvest(5, 100)], dt.date(2026, 12, 26))[0]["closed"])
        self.assertTrue(rules.colour_results([cut(10), harvest(5, 100)], TODAY)[0]["closed"])


class Compare(unittest.TestCase):
    def test_week_totals_and_error(self):
        r = rules.compare([row(), row(block="A6")], [row(bunches=180, kg=3600)])[0]
        self.assertEqual((r["forecast_bunches"], r["actual_bunches"], r["diff_bunches"], r["diff_pct"]), (200, 180, -20, -10))

    def test_group_by_lot_and_colour(self):
        rows = rules.compare([row(), row(block="A6", tag="U", ribbon="Trắng")], [row(bunches=90, kg=1800)], "detail")
        self.assertEqual(len(rows), 2)
        self.assertEqual([r["actual_bunches"] for r in rows], [90, 0])

    def test_unforecast_harvest_has_no_percentage(self):
        self.assertIsNone(rules.compare([], [row()])[0]["diff_pct"])


class Suggest(unittest.TestCase):
    current = {"cut_to_harvest_days": 65, "harvest_rate": .97}

    def closed(self, n):
        lines = []
        for i in range(n):
            lines += [cut(tag=str(i)), harvest(tag=str(i))]
        return rules.colour_results(lines, TODAY)

    def test_too_few_finished_colours_suggest_nothing(self):
        result = rules.suggest(self.closed(2), self.current)
        self.assertFalse(result["enough"])
        self.assertTrue(all(x["suggested"] is None for x in result["lines"]))
        self.assertEqual(result["samples"], 2)

    def test_enough_colours_give_measured_values_next_to_current(self):
        result = rules.suggest(self.closed(3), self.current)
        self.assertTrue(result["enough"])
        lines = {x["field"]: x for x in result["lines"]}
        self.assertEqual(lines["cut_to_harvest_days"]["suggested"], 65)
        self.assertEqual(lines["harvest_rate"]["suggested"], .95)
        self.assertEqual(lines["harvest_rate"]["current"], .97)

    def test_no_samples_at_all(self):
        self.assertEqual(rules.suggest([], self.current)["lines"], [])


class Weeks(unittest.TestCase):
    def test_key_and_monday_round_trip(self):
        self.assertEqual(rules.week_key("2026-12-25"), "2026-W52")
        self.assertEqual(rules.week_monday("2026-W52"), dt.date(2026, 12, 21))


if __name__ == "__main__":
    unittest.main()


class AsOfMonday(unittest.TestCase):
    MONDAY = dt.date(2026, 11, 16)

    def line(self, confirmed, voided=None, qty=10):
        return dict(cut(qty), confirmed_at=confirmed, voided_at=voided)

    def test_only_lines_confirmed_before_the_moment_and_not_voided_before_it(self):
        moment = rules.week_moment(dt.date(2026, 11, 18))
        self.assertEqual(moment, dt.datetime(2026, 11, 16, 0, 0))
        lines = [self.line("2026-11-15 17:00:00", qty=1), self.line("2026-11-16 07:00:00", qty=2), self.line(None, qty=3),
                 self.line("2026-11-10 09:00:00", "2026-11-15 10:00:00", qty=4), self.line("2026-11-10 09:00:00", "2026-11-17 10:00:00", qty=5)]
        self.assertEqual([l["qty"] for l in rules.lines_as_of(lines, moment)], [1, 5], "a line voided after the Monday was still counted then")

    def test_parameters_approved_after_the_moment_are_left_out(self):
        profiles = [{"name": "p1", "approved_at": "2026-11-01 10:00:00"}, {"name": "p2", "approved_at": "2026-11-17 10:00:00"},
                    {"name": "p3", "approved_at": None, "creation": "2026-10-01 08:00:00"}, {"name": "p4", "approved_at": None}]
        self.assertEqual([p["name"] for p in rules.profiles_as_of(profiles, self.MONDAY)], ["p1", "p3"])

    def test_missed_weeks_are_built_from_the_first_monday_after_the_first_confirmation(self):
        weeks = rules.weeks_to_build(dt.datetime(2026, 10, 28, 9, 0), [dt.date(2026, 11, 9)], dt.date(2026, 11, 18))
        self.assertEqual(weeks, [dt.date(2026, 11, 2), dt.date(2026, 11, 16)], "W45 and this week; W46 is there")

    def test_nothing_before_the_sổ_lô_has_a_confirmed_line_and_at_most_eight_weeks_back(self):
        self.assertEqual(rules.weeks_to_build(None, [], dt.date(2026, 11, 18)), [])
        self.assertEqual(rules.weeks_to_build(dt.datetime(2026, 11, 17, 9, 0), [], dt.date(2026, 11, 18)), [], "the first copy is next Monday's")
        self.assertEqual(len(rules.weeks_to_build(dt.datetime(2025, 1, 6, 9, 0), [], dt.date(2026, 11, 18))), 9)
