import importlib.util
import pathlib
import unittest

_spec = importlib.util.spec_from_file_location("field_report_rules", pathlib.Path(__file__).parents[1] / "field_report_rules.py")
rules = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rules)


class StagesBeforeAndAfterCutting(unittest.TestCase):
    def test_only_bao_buong_carries_a_colour(self):
        self.assertEqual(rules.COLOUR_STAGES, ("Bag",))

    def test_every_care_stage_still_counts_for_the_report(self):
        self.assertEqual(set(rules.CARE_STAGES), {"Bag", "Care", "Prop"})

    def test_prop_and_care_are_not_capped_by_the_cut(self):
        rows = [{"stage": stage, "farm_block": "B", "bunch_tag": "T", "qty": 50} for stage in ("Prop", "Care")]
        self.assertFalse(rules.bunch_over_cut({("B", "T"): 1}, {}, rows))

    def test_bao_buong_stays_capped_by_the_cut(self):
        self.assertTrue(rules.bunch_over_cut({("B", "T"): 1}, {}, [{"stage": "Bag", "farm_block": "B", "bunch_tag": "T", "qty": 50}]))

    def test_the_trees_of_the_lot_are_the_cap(self):
        self.assertEqual(rules.cap_left(rules.CAP_TREES, 30, lot_trees=100), 70)


if __name__ == "__main__":
    unittest.main()
