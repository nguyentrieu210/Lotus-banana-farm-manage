import datetime as dt
import unittest

from lotus_farm import bunch_flow_rules as flow
from lotus_farm import bunch_forecast_engine as engine
from lotus_farm.forecast_parameters import DEFAULTS, validate

CONFIG = validate(dict(DEFAULTS))
TODAY = dt.date(2026, 11, 9)


def params(block, day):
    return "P1", CONFIG


def line(event_type, qty, day, block="B", tag=None, name=None, cycle=2, **extra):
    return dict({"name": name or f"{event_type}{day}", "event_type": event_type, "qty": qty, "event_date": day, "farm_block": block, "bunch_tag": tag, "cycle_no": cycle}, **extra)


def inject(lines, today=TODAY):
    return flow.inject_cohorts(lines, params, today)


def wave(shoots=1000, harvest=873, start="2027-01-26", end="2027-02-24", block="B", generation=0, number=1, cycle=1):
    return {"farm_block": block, "bunches_shoot": shoots, "bunches_cut": 900, "bunches_harvest": harvest, "harvest_date": start, "harvest_window_end": end, "wave": number, "generation": generation,
            "cycle_no": cycle, "window_days": 30, "timing": CONFIG, "profile": "P1", "tree_qty": shoots, "flower_window_start": "2026-11-01", "source": "s", "count_status": "c"}


def trees(waves, observed=None, claimed=None, today=TODAY, current=None):
    return flow.tree_cohorts(waves, observed or {}, claimed or {}, current if current is not None else {"B": 2}, today)


def bunches(cohorts):
    return sum(c["bunches"] for c in cohorts)


class InjectLayer(unittest.TestCase):
    def test_injected_and_not_cut_is_forecast_with_the_expected_rate(self):
        cohorts, observed = inject([line(flow.INJECT, 100, "2026-11-02")])
        self.assertEqual(bunches(cohorts), 97)
        self.assertEqual(observed, {("B", 2): 100})
        self.assertEqual(cohorts[0]["layer"], "inject")

    def test_harvest_window_runs_from_the_expected_cut(self):
        c = inject([line(flow.INJECT, 100, "2026-11-02")])[0][0]
        self.assertEqual(c["window_start"], dt.date(2026, 11, 18) + dt.timedelta(days=60))
        self.assertEqual(sum(n for _, n in c["days"]), c["bunches"])

    def test_cuts_in_the_first_days_do_not_use_up_injections(self):
        cohorts, observed = inject([line(flow.INJECT, 100, "2026-11-02"), line(flow.CUT, 40, "2026-11-10", tag="T")])
        self.assertEqual(bunches(cohorts), 97, "those 40 were injected before recording began")
        self.assertEqual(observed[("B", 2)], 140)

    def test_later_cuts_take_the_oldest_injections_first(self):
        lines = [line(flow.INJECT, 60, "2026-11-02", name="a"), line(flow.INJECT, 40, "2026-11-05", name="b"), line(flow.CUT, 70, "2026-11-20", tag="T")]
        cohorts, observed = inject(lines, dt.date(2026, 11, 21))
        self.assertEqual([c["event"] for c in cohorts], ["b"])
        self.assertEqual(observed[("B", 2)], 100, "70 cut and 30 waiting: the total never grows")

    def test_everything_cut_leaves_nothing_waiting(self):
        cohorts, observed = inject([line(flow.INJECT, 50, "2026-11-02"), line(flow.CUT, 60, "2026-11-20", tag="T")], dt.date(2026, 11, 21))
        self.assertEqual(cohorts, [])
        self.assertEqual(observed[("B", 2)], 60)

    def test_recorded_rejects_are_inside_the_expected_loss(self):
        self.assertEqual(bunches(inject([line(flow.INJECT, 100, "2026-11-02"), line(flow.REJECT, 2, "2026-11-03", reject_stage=flow.BEFORE_CUT)])[0]), 97)

    def test_rejects_above_the_expected_loss_count_in_full(self):
        self.assertEqual(bunches(inject([line(flow.INJECT, 100, "2026-11-02"), line(flow.REJECT, 10, "2026-11-03", reject_stage=flow.BEFORE_CUT)])[0]), 90)

    def test_late_injection_moves_to_a_cut_from_today(self):
        c = inject([line(flow.INJECT, 100, "2026-10-01")])[0][0]
        self.assertTrue(c["overdue"])
        self.assertEqual(c["window_start"], TODAY + dt.timedelta(days=60))

    def test_a_lot_with_only_cuts_is_still_seen(self):
        cohorts, observed = inject([line(flow.CUT, 30, "2026-11-01", tag="T")])
        self.assertEqual((cohorts, observed), ([], {("B", 2): 30}))

    def test_vu_are_kept_apart(self):
        _, observed = inject([line(flow.INJECT, 10, "2026-11-02"), line(flow.INJECT, 20, "2026-11-02", cycle=3)])
        self.assertEqual(observed, {("B", 2): 10, ("B", 3): 20})


class Waiting(unittest.TestCase):
    def test_late_after_its_cutting_day(self):
        result = flow.waiting_injections([line(flow.INJECT, 30, "2026-10-01", name="a")], params, TODAY)
        self.assertEqual((result[0]["left"], result[0]["due"], result[0]["late_days"]), (30, "2026-10-17", 23))

    def test_cuts_take_the_oldest_first_after_the_first_days(self):
        lines = [line(flow.INJECT, 10, "2026-10-01", name="a"), line(flow.INJECT, 10, "2026-10-05", name="b"), line(flow.CUT, 12, "2026-10-20", tag="T")]
        self.assertEqual([(w["event"], w["left"]) for w in flow.waiting_injections(lines, params, TODAY)], [("b", 8)])


class SuckerLayer(unittest.TestCase):
    def test_dates_come_from_the_real_selection_day(self):
        c = flow.sucker_cohorts([line(flow.SUCKER, 4000, "2026-11-04", area_ha=2)], {}, params, TODAY)[0][0]
        self.assertEqual(c["window_start"], dt.date(2027, 5, 4) + dt.timedelta(days=5 + 16 + 65))
        self.assertEqual(c["layer"], "sucker")

    def test_rates_are_those_of_a_tree(self):
        cohorts, claimed = flow.sucker_cohorts([line(flow.SUCKER, 4000, "2026-11-04")], {}, params, TODAY)
        self.assertEqual(claimed, {("B", 2): 3600}, "counted at cắt bắp, like the waves they replace")
        self.assertEqual(bunches(cohorts), round(round(4000 * .9) * .97))

    def test_suckers_already_seen_as_bunches_are_not_counted_again(self):
        self.assertEqual(flow.sucker_cohorts([line(flow.SUCKER, 100, "2026-11-04")], {("B", 2): 100}, params, TODAY), ([], {}))


class TreeLayer(unittest.TestCase):
    def test_nothing_observed_keeps_the_wave(self):
        self.assertEqual(bunches(trees([wave()])), 873)

    def test_observed_bunches_come_off_the_earliest_wave(self):
        result = trees([wave(number=2, start="2027-02-26", end="2027-03-27"), wave()], {("B", 2): 1500})
        self.assertEqual([c["group"]["wave"] for c in result], [2])
        self.assertEqual(result[0]["group"]["seen"], 600, "900 finish the first wave, 600 come off the second")
        self.assertEqual(result[0]["bunches"], 291)

    def test_total_never_exceeds_the_tree_forecast(self):
        self.assertLessEqual(bunches(trees([wave()], {("B", 2): 200}, {("B", 2): 100})), 873)

    def test_observed_of_another_vu_does_not_touch_this_one(self):
        self.assertEqual(bunches(trees([wave()], {("B", 3): 1000})), 873)

    def test_generation_counts_from_the_current_vu(self):
        self.assertEqual(trees([wave(generation=0, cycle=1)])[0]["cycle"], 2)
        self.assertEqual(trees([wave(generation=1, cycle=2)])[0]["cycle"], 3)

    def test_a_running_window_only_uses_days_left_and_keeps_the_total(self):
        c = trees([wave()], today=dt.date(2027, 2, 10))[0]
        self.assertEqual(c["days"][0][0], dt.date(2027, 2, 10))
        self.assertEqual(sum(n for _, n in c["days"]), 873)
        self.assertFalse(c["overdue"])

    def test_a_past_wave_moves_into_the_coming_weeks(self):
        c = trees([wave()], today=dt.date(2027, 4, 1))[0]
        self.assertTrue(c["overdue"])
        self.assertEqual(c["days"][0][0], dt.date(2027, 4, 1))
        self.assertEqual(sum(n for _, n in c["days"]), 873)


class NoDoubleCounting(unittest.TestCase):
    def all_layers(self, lines, waves):
        cut = flow.cut_cohorts(lines, params, TODAY)
        injected, observed = inject(lines)
        suckers, claimed = flow.sucker_cohorts(lines, observed, params, TODAY)
        return cut + injected + suckers + trees(waves, observed, claimed)

    def test_each_lot_uses_the_nearest_source(self):
        lines = [line(flow.CUT, 100, "2026-11-01", block="C1", tag="T"), line(flow.INJECT, 100, "2026-11-02", block="C2"), line(flow.SUCKER, 100, "2026-11-02", block="C3")]
        layers = {c["block"]: c["layer"] for c in self.all_layers(lines, [])}
        self.assertEqual(layers, {"C1": "cut", "C2": "inject", "C3": "sucker"})

    def test_a_forecast_total_shrinks_by_what_moved_to_a_nearer_layer(self):
        base = bunches(self.all_layers([], [wave()]))
        moved = self.all_layers([line(flow.CUT, 200, "2026-11-01", tag="T"), line(flow.INJECT, 100, "2026-11-02")], [wave()])
        tree = [c for c in moved if c["layer"] == "tree"][0]
        self.assertEqual(tree["group"]["seen"], 300)
        self.assertEqual(bunches(moved), base, "bunches seen replace the wave one for one at the same rates")

    def test_summary_splits_the_layers(self):
        cohorts = self.all_layers([line(flow.CUT, 100, "2026-11-01", tag="T"), line(flow.INJECT, 100, "2026-11-02")], [wave()])
        result = engine.summarize(cohorts, {"B": {"code": "A1", "zone": "A"}}, {"T": "Đỏ"}, TODAY, 26)
        self.assertGreater(result["totals"]["layers"]["cut"], 0)
        self.assertGreater(result["totals"]["layers"]["inject"], 0)
        self.assertGreater(result["totals"]["layers"]["tree"], 0)
        self.assertEqual(result["totals"]["bunches"], sum(result["totals"]["layers"].values()))
        self.assertEqual({r["layer"]: r["confidence"] for r in result["rows"]}, {"cut": "high", "inject": "medium", "tree": "low"})

    def test_months_look_further_than_the_weeks(self):
        cohorts = trees([wave(start="2027-08-01", end="2027-08-30")])
        result = engine.summarize(cohorts, {"B": {"code": "A1", "zone": "A"}}, {}, TODAY)
        self.assertEqual(len(result["months"]), 12)
        self.assertEqual(sum(m["bunches"] for m in result["months"]), 873)
        self.assertEqual(result["totals"]["bunches"], 0)
        self.assertEqual(result["later"], 0, "a far tree forecast is not news")

    def test_moved_waves_are_warned_once_per_layer(self):
        cohorts = trees([wave(), wave(number=2)], today=dt.date(2027, 4, 1))
        result = engine.summarize(cohorts, {"B": {"code": "A1", "zone": "A"}}, {}, dt.date(2027, 4, 1))
        self.assertEqual(len([w for w in result["warnings"] if "chuyển sang" in w]), 1)


if __name__ == "__main__":
    unittest.main()
