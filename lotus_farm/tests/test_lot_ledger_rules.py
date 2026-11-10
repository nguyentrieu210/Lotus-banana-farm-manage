import importlib.util
import pathlib
import unittest
from datetime import date

# Load by path: the rules are pure and this test must run without a bench.
_spec = importlib.util.spec_from_file_location("lot_ledger_rules", pathlib.Path(__file__).parents[1] / "lot_ledger_rules.py")
r = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(r)


def work(**values):
    return dict({"name": "W", "stage": "", "group": r.FIELD_GROUP, "pay_mode": "Lot", "requires_material": 0, "records_disease": 0}, **values)


BUNCH = dict(group=r.BUNCH_GROUP, pay_mode="Daywork")


class CleanLine(unittest.TestCase):
    def test_bunch_numbers_are_whole_and_positive(self):
        for bad in ("0", "-3", "2.5", "12,5", "abc", ""):
            with self.assertRaises(r.LineError):
                r.clean_line({"qty": bad}, work(stage=r.INJECT, **BUNCH))
        self.assertEqual(r.clean_line({"qty": "12.0"}, work(stage=r.INJECT, **BUNCH))["qty"], 12)

    def test_cut_bud_takes_the_ribbon_of_the_day_never_a_typed_colour(self):
        line = r.clean_line({"qty": 120, "bunch_tag": "TYPED"}, work(stage=r.CUT, **BUNCH), ribbon_tag="RED-46-1")
        self.assertEqual(line["bunch_tag"], "RED-46-1")
        with self.assertRaises(r.LineError):
            r.clean_line({"qty": 120}, work(stage=r.CUT, **BUNCH), ribbon_tag=None)

    def test_bag_and_harvest_need_a_colour_harvest_needs_kg(self):
        with self.assertRaises(r.LineError):
            r.clean_line({"qty": 10}, work(stage=r.BAG, **BUNCH))
        with self.assertRaises(r.LineError):
            r.clean_line({"qty": 10, "bunch_tag": "T"}, work(stage=r.HARVEST, **BUNCH))
        line = r.clean_line({"qty": 10, "bunch_tag": "T", "weight_kg": "195,5"}, work(stage=r.HARVEST, **BUNCH))
        self.assertEqual((line["bunch_tag"], line["weight_kg"]), ("T", 195.5))

    def test_tree_capped_stages_carry_no_colour(self):
        for stage in (r.INJECT, r.CARE, r.PROP):
            self.assertIsNone(r.clean_line({"qty": 5, "bunch_tag": "T"}, work(stage=stage, **BUNCH))["bunch_tag"])

    def test_reject_needs_reason_and_stage_and_colour_after_cut(self):
        w = work(stage=r.REJECT, **BUNCH)
        with self.assertRaises(r.LineError):
            r.clean_line({"qty": 2, "reject_stage": r.AFTER_CUT, "bunch_tag": "T"}, w)
        with self.assertRaises(r.LineError):
            r.clean_line({"qty": 2, "reason": "GD"}, w)
        with self.assertRaises(r.LineError):
            r.clean_line({"qty": 2, "reason": "GD", "reject_stage": r.AFTER_CUT}, w)
        before = r.clean_line({"qty": 2, "reason": "GD", "reject_stage": r.BEFORE_CUT, "bunch_tag": "T"}, w)
        self.assertIsNone(before["bunch_tag"])

    def test_spraying_needs_material_quantity_and_dose(self):
        w = work(group=r.PROTECTION, pay_mode="Count", requires_material=1)
        with self.assertRaises(r.LineError):
            r.clean_line({"qty": 3}, w)
        with self.assertRaises(r.LineError):
            r.clean_line({"qty": 3, "materials": [{"item_code": "THUOC", "qty": 2}]}, w)
        line = r.clean_line({"qty": 3, "materials": [{"item_code": "THUOC", "qty": "2,5", "dose": "50 ml/bình"}]}, w)
        self.assertEqual(line["materials"][0]["qty"], 2.5)

    def test_disease_check_needs_disease_trees_and_severity(self):
        w = work(group=r.PROTECTION, pay_mode="Daywork", records_disease=1)
        with self.assertRaises(r.LineError):
            r.clean_line({"qty": 12, "severity": "Nặng"}, w)
        with self.assertRaises(r.LineError):
            r.clean_line({"qty": 12, "disease": "SIGA"}, w)
        with self.assertRaises(r.LineError):
            r.clean_line({"qty": 0, "disease": "SIGA", "severity": "Vừa"}, w)
        line = r.clean_line({"qty": 12, "disease": "SIGA", "severity": "Vừa"}, w)
        self.assertEqual((line["disease"], line["severity"], line["qty"]), ("SIGA", "Vừa", 12))

    def test_field_work_needs_a_quantity_or_the_lot_finished(self):
        with self.assertRaises(r.LineError):
            r.clean_line({}, work())
        self.assertEqual(r.clean_line({"done": 1}, work())["done"], 1)
        with self.assertRaises(r.LineError):
            r.clean_line({"done": 1}, work(pay_mode="Count"))

    def test_sucker_select_is_reported_in_hectares(self):
        with self.assertRaises(r.LineError):
            r.clean_line({}, work(stage=r.SUCKER))
        self.assertEqual(r.clean_line({"area_ha": "1,5"}, work(stage=r.SUCKER))["area_ha"], 1.5)


class Caps(unittest.TestCase):
    def rows(self):
        return [{"farm_block": "A5", "bunch_tag": "RED", "stage": r.CUT, "qty": 120},
                {"farm_block": "A5", "bunch_tag": "RED", "stage": r.BAG, "qty": 100},
                {"farm_block": "A5", "bunch_tag": "RED", "stage": r.REJECT, "reject_stage": r.AFTER_CUT, "qty": 3},
                {"farm_block": "A5", "bunch_tag": "RED", "stage": r.HARVEST, "qty": 77}]

    def test_colour_balance_and_what_is_left_on_the_plants(self):
        bal = r.colour_balance(self.rows())[("A5", "RED")]
        self.assertEqual((bal["cut"], bal["bag"], bal["used"], bal["left"]), (120, 100, 80, 40))

    def test_bagging_and_harvest_are_capped_separately_by_the_cut(self):
        self.assertEqual(r.over_cut(self.rows()), {})
        too_many_bags = self.rows() + [{"farm_block": "A5", "bunch_tag": "RED", "stage": r.BAG, "qty": 30}]
        self.assertIn(("A5", "RED"), r.over_cut(too_many_bags))
        too_much_harvest = self.rows() + [{"farm_block": "A5", "bunch_tag": "RED", "stage": r.HARVEST, "qty": 45}]
        self.assertIn(("A5", "RED"), r.over_cut(too_much_harvest))

    def test_two_cycles_of_one_colour_are_different_tags(self):
        rows = [{"farm_block": "A5", "bunch_tag": "RED-W46", "stage": r.CUT, "qty": 10},
                {"farm_block": "A5", "bunch_tag": "RED-W58", "stage": r.HARVEST, "qty": 10}]
        self.assertIn(("A5", "RED-W58"), r.over_cut(rows))

    def test_tree_capped_work_in_the_cycle_cannot_exceed_the_trees(self):
        rows = [{"farm_block": "A5", "stage": r.INJECT, "qty": 900, "cycle_no": 2},
                {"farm_block": "A5", "stage": r.INJECT, "qty": 200, "cycle_no": 2},
                {"farm_block": "A5", "stage": r.INJECT, "qty": 5000, "cycle_no": 1}]
        self.assertEqual(r.over_trees(rows, {"A5": 1000}, {"A5": 2}), {("A5", r.INJECT): (1100, 1000)})
        self.assertEqual(r.over_trees(rows[:1], {"A5": 1000}, {"A5": 2}), {})


class Quarantine(unittest.TestCase):
    def test_latest_end_of_all_confirmed_sprays(self):
        lines = [{"posting_date": date(2026, 11, 1), "materials": [{"phi_days": 14}, {"phi_days": 3}]},
                 {"posting_date": date(2026, 11, 10), "materials": [{"phi_days": 7}]},
                 {"posting_date": date(2026, 11, 12), "materials": [{"phi_days": 0}]}]
        self.assertEqual(r.quarantine_end(lines), date(2026, 11, 17))
        self.assertIsNone(r.quarantine_end([{"posting_date": date(2026, 11, 1), "materials": [{"phi_days": 0}]}]))

    def test_harvest_blocked_from_the_spray_day_to_the_end(self):
        intervals = r.quarantine_intervals([{"posting_date": date(2026, 11, 10), "materials": [{"phi_days": 7}]}])
        self.assertEqual(intervals, [(date(2026, 11, 10), date(2026, 11, 17))])
        self.assertTrue(r.harvest_blocked(date(2026, 11, 17), intervals))
        self.assertTrue(r.harvest_blocked(date(2026, 11, 10), intervals))
        self.assertIsNone(r.harvest_blocked(date(2026, 11, 18), intervals))
        self.assertIsNone(r.harvest_blocked(date(2026, 11, 18), []))

    def test_a_spray_after_a_late_entered_harvest_does_not_block_it(self):
        intervals = r.quarantine_intervals([{"posting_date": date(2026, 11, 20), "materials": [{"phi_days": 14}]}])
        self.assertIsNone(r.harvest_blocked(date(2026, 11, 18), intervals))


class SessionWeights(unittest.TestCase):
    def test_same_work_on_two_lots_splits_by_quantity_and_sums_to_one(self):
        lines = [{"key": "a5", "work_type": "CL", "qty": 3, "people": {"E1": {"morning": 1, "afternoon": 0}}},
                 {"key": "a6", "work_type": "CL", "qty": 1, "people": {"E1": {"morning": 1, "afternoon": 1}}}]
        w = r.session_weights(lines)
        self.assertAlmostEqual(w[("a5", "E1", r.MORNING)], 0.75)
        self.assertAlmostEqual(w[("a6", "E1", r.MORNING)], 0.25)
        self.assertAlmostEqual(w[("a6", "E1", r.AFTERNOON)], 1.0)

    def test_different_works_split_evenly_first(self):
        lines = [{"key": "x", "work_type": "CL", "qty": 9, "people": {"E1": {"morning": 1}}},
                 {"key": "y", "work_type": "LC", "qty": 1, "people": {"E1": {"morning": 1}}},
                 {"key": "z", "work_type": "LC", "qty": 1, "people": {"E1": {"morning": 1}}}]
        w = r.session_weights(lines)
        self.assertAlmostEqual(w[("x", "E1", r.MORNING)], 0.5)
        self.assertAlmostEqual(w[("y", "E1", r.MORNING)] + w[("z", "E1", r.MORNING)], 0.5)
        self.assertAlmostEqual(sum(v for k, v in w.items() if k[1] == "E1" and k[2] == r.MORNING), 1.0, places=9)

    def test_zero_quantities_split_evenly(self):
        lines = [{"key": "a", "work_type": "CL", "qty": 0, "people": {"E1": {"afternoon": 1}}},
                 {"key": "b", "work_type": "CL", "qty": 0, "people": {"E1": {"afternoon": 1}}},
                 {"key": "c", "work_type": "CL", "qty": 0, "people": {"E1": {"afternoon": 1}}}]
        w = r.session_weights(lines)
        self.assertAlmostEqual(sum(w.values()), 1.0, places=9)

    def test_a_lot_ticked_done_without_a_number_keeps_its_share(self):
        lines = [{"key": "a5", "work_type": "CL", "qty": 0, "people": {"E1": {"morning": 1}}},
                 {"key": "a6", "work_type": "CL", "qty": 1.2, "people": {"E1": {"morning": 1}}}]
        w = r.session_weights(lines)
        self.assertAlmostEqual(w[("a5", "E1", r.MORNING)], 0.5)
        self.assertAlmostEqual(w[("a6", "E1", r.MORNING)], 0.5)

    def test_count_line_per_tree_is_capped_by_the_trees_of_the_lot(self):
        self.assertIsNone(r.line_cap("Count", "LotTrees", "", 1800, 1800))
        self.assertIn("vượt số cây 1800", r.line_cap("Count", "LotTrees", "", 4000, 1800))
        self.assertIsNone(r.line_cap("Count", "LotTrees", "Bag", 4000, 1800))   # bunch stages: cumulative caps
        self.assertIsNone(r.line_cap("Lot", "LotTrees", "", 4000, 1800))
        self.assertIsNone(r.line_cap("Count", "LotTrees", "", 4000, 0))        # lô without a tree count: not judged

    def test_overage_of_a_colour(self):
        self.assertEqual(r.overage({"cut": 100, "bag": 90, "used": 80}), 0)
        self.assertEqual(r.overage({"cut": 0, "bag": 120, "used": 80}), 200)


class ReportFlow(unittest.TestCase):
    def test_states(self):
        self.assertEqual(r.next_report_state(r.DRAFT, "send"), r.SENT)
        self.assertEqual(r.next_report_state(r.REOPENED, "send"), r.SENT)
        self.assertEqual(r.next_report_state(r.SENT, "confirm"), r.CONFIRMED)
        self.assertEqual(r.next_report_state(r.CONFIRMED, "reopen"), r.REOPENED)
        with self.assertRaises(ValueError):
            r.next_report_state(r.DRAFT, "confirm")
        with self.assertRaises(ValueError):
            r.next_report_state(r.CONFIRMED, "send")

    def test_editable_only_before_sending(self):
        self.assertTrue(r.can_edit(r.DRAFT))
        self.assertTrue(r.can_edit(r.REOPENED))
        self.assertFalse(r.can_edit(r.SENT))
        self.assertFalse(r.can_edit(r.CONFIRMED))

    def test_nobody_confirms_their_own_lines(self):
        self.assertFalse(r.can_confirm("hai@lotus", "hai@lotus"))
        self.assertFalse(r.can_confirm(None, "hai@lotus"))
        self.assertTrue(r.can_confirm("to3@lotus", "hai@lotus"))

    def test_line_key_and_free_key(self):
        self.assertEqual(r.line_key("R1", "A5", "CB", "RED", None), "day:R1:A5:CB:RED:")
        self.assertEqual(r.line_amount("Count", 120, 4000), 480000)
        self.assertEqual(r.line_amount("Lot", 120, 4000), 0)


if __name__ == "__main__":
    unittest.main()
