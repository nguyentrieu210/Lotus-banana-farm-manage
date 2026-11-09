import importlib.util
import pathlib
import unittest

# Load by path: the rules are pure and this test must run without a bench.
_spec = importlib.util.spec_from_file_location("bunch_posting_rules", pathlib.Path(__file__).parents[1] / "bunch_posting_rules.py")
rules = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rules)


def row(**values):
    return dict({"event_type": rules.INJECT, "qty": 5}, **values)


class WholeNumber(unittest.TestCase):
    def test_accepts_whole_numbers_as_typed(self):
        self.assertEqual(rules.whole_number("12"), 12)
        self.assertEqual(rules.whole_number(12.0), 12)
        self.assertEqual(rules.whole_number("12,0"), 12)

    def test_rejects_parts_of_a_bunch_and_nonsense(self):
        for bad in ("12.5", "12,5", 0, -3, "", None, "abc", "inf", "nan"):
            self.assertIsNone(rules.whole_number(bad), bad)


class CleanRow(unittest.TestCase):
    def test_cut_takes_the_ribbon_of_the_day_not_a_typed_colour(self):
        clean = rules.clean_row(row(event_type=rules.CUT, bunch_tag="typed"), ribbon_tag="ribbon")
        self.assertEqual(clean["bunch_tag"], "ribbon")

    def test_cut_needs_a_ribbon(self):
        with self.assertRaises(rules.RowError):
            rules.clean_row(row(event_type=rules.CUT))

    def test_injection_carries_no_colour(self):
        self.assertIsNone(rules.clean_row(row(bunch_tag="x"))["bunch_tag"])

    def test_reject_before_cut_needs_reason_and_drops_colour(self):
        clean = rules.clean_row(row(event_type=rules.REJECT, reject_stage=rules.BEFORE_CUT, reason="R", bunch_tag="x"))
        self.assertIsNone(clean["bunch_tag"])
        with self.assertRaises(rules.RowError):
            rules.clean_row(row(event_type=rules.REJECT, reject_stage=rules.BEFORE_CUT))

    def test_reject_after_cut_needs_colour(self):
        with self.assertRaises(rules.RowError):
            rules.clean_row(row(event_type=rules.REJECT, reject_stage=rules.AFTER_CUT, reason="R"))

    def test_reject_needs_a_stage(self):
        with self.assertRaises(rules.RowError):
            rules.clean_row(row(event_type=rules.REJECT, reason="R"))

    def test_harvest_needs_colour_and_weight(self):
        with self.assertRaises(rules.RowError):
            rules.clean_row(row(event_type=rules.HARVEST, weight_kg=100))
        with self.assertRaises(rules.RowError):
            rules.clean_row(row(event_type=rules.HARVEST, bunch_tag="x"))
        self.assertEqual(rules.clean_row(row(event_type=rules.HARVEST, bunch_tag="x", weight_kg="120,5"))["weight_kg"], 120.5)

    def test_decimal_bunches_are_refused(self):
        with self.assertRaises(rules.RowError):
            rules.clean_row(row(qty="2.5"))

    def test_other_events_are_not_for_the_sheet(self):
        with self.assertRaises(rules.RowError):
            rules.clean_row(row(event_type=rules.SUCKER))


class Keys(unittest.TestCase):
    def test_key_separates_colour_reason_and_team(self):
        base = rules.row_key("B", "2026-11-09", rules.REJECT, "T", "R", "X")
        self.assertEqual(base, "daily:B:2026-11-09:Reject:T:R:X")
        self.assertNotEqual(base, rules.row_key("B", "2026-11-09", rules.REJECT, "", "R", "X"))
        self.assertNotEqual(base, rules.row_key("B", "2026-11-09", rules.REJECT, "T", "Q", "X"))
        self.assertNotEqual(base, rules.row_key("B", "2026-11-09", rules.REJECT, "T", "R", "Y"))


class CutCap(unittest.TestCase):
    cut = {"event_type": rules.CUT, "farm_block": "B", "bunch_tag": "T", "qty": 10}

    def test_harvest_plus_reject_after_cut_is_capped_per_lot_and_colour(self):
        harvest = {"event_type": rules.HARVEST, "farm_block": "B", "bunch_tag": "T", "qty": 8}
        reject = {"event_type": rules.REJECT, "reject_stage": rules.AFTER_CUT, "farm_block": "B", "bunch_tag": "T", "qty": 2}
        self.assertEqual(rules.over_cut([self.cut, harvest, reject]), {})
        self.assertEqual(rules.over_cut([self.cut, harvest, dict(reject, qty=3)]), {("B", "T"): (10, 11)})

    def test_other_lots_and_colours_do_not_share_a_cap(self):
        other = {"event_type": rules.HARVEST, "farm_block": "C", "bunch_tag": "T", "qty": 1}
        self.assertEqual(rules.over_cut([self.cut, other]), {("C", "T"): (0, 1)})

    def test_reject_before_cut_uses_no_cap(self):
        reject = {"event_type": rules.REJECT, "reject_stage": rules.BEFORE_CUT, "farm_block": "B", "bunch_tag": None, "qty": 99}
        self.assertEqual(rules.over_cut([self.cut, reject]), {})


class Suckers(unittest.TestCase):
    def test_estimate_scales_with_area_done(self):
        self.assertEqual(rules.sucker_estimate(4000, 1, 2), 2000)

    def test_estimate_never_passes_the_trees(self):
        self.assertEqual(rules.sucker_estimate(4000, 3, 2), 4000)

    def test_estimate_is_zero_without_a_basis(self):
        self.assertEqual(rules.sucker_estimate(0, 1, 2), 0)
        self.assertEqual(rules.sucker_estimate(4000, 1, 0), 0)

    def test_cycle_follows_fr_026(self):
        self.assertEqual(rules.sucker_cycle(2, False), 2)
        self.assertEqual(rules.sucker_cycle(2, True), 3)


class Mapping(unittest.TestCase):
    def test_only_sucker_select_writes_the_ledger_from_a_ticket(self):
        self.assertEqual(rules.event_for_stage("Sucker Select"), rules.SUCKER)
        for stage in ("Bag", "Care", "Prop", "Cut Bud", "Bud Injection"):
            self.assertIsNone(rules.event_for_stage(stage))


class Confirming(unittest.TestCase):
    def test_nobody_confirms_their_own_entry(self):
        self.assertFalse(rules.can_confirm("a@x", "a@x"))
        self.assertTrue(rules.can_confirm("a@x", "b@x"))
        self.assertFalse(rules.can_confirm(None, "b@x"))


class MorningChecks(unittest.TestCase):
    today = __import__("datetime").date(2026, 11, 20)

    def lot(self, **values):
        return dict({"code": "A1", "trees": 100, "inject": 0, "cut": 0, "used": 0, "flower_date": None}, **values)

    def kinds(self, **values):
        return [x["kind"] for x in rules.anomalies([self.lot(**values)], self.today)]

    def test_lot_with_a_ticket_and_no_number_is_listed(self):
        self.assertEqual(rules.not_reported([("B3", "T2"), ("B4", "T2")], ["B4"]), {"B3": "T2"})

    def test_lot_reported_by_anyone_is_not_listed(self):
        self.assertEqual(rules.not_reported([("B3", "T2")], ["B3"]), {})

    def test_injected_above_the_trees(self):
        found = rules.anomalies([self.lot(inject=101)], self.today)
        self.assertEqual(found[0]["kind"], "inject")
        self.assertIn("101", found[0]["message"])

    def test_cut_above_the_trees(self):
        self.assertEqual(self.kinds(cut=101), ["cut"])

    def test_used_above_cut(self):
        self.assertEqual(self.kinds(cut=5, used=6), ["used"])

    def test_lot_old_enough_to_flower_with_no_number(self):
        day = __import__("datetime").date
        self.assertEqual(self.kinds(flower_date=day(2026, 11, 1)), ["silent"])
        self.assertEqual(self.kinds(flower_date=day(2026, 11, 10)), [], "not late yet")
        self.assertEqual(self.kinds(flower_date=day(2026, 11, 1), inject=3), [], "it has numbers")

    def test_healthy_lot_says_nothing(self):
        self.assertEqual(self.kinds(inject=50, cut=20, used=10), [])

    def test_no_tree_count_is_not_an_alarm(self):
        self.assertEqual(self.kinds(trees=0, inject=5), [])


if __name__ == "__main__":
    unittest.main()
