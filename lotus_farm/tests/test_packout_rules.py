import importlib.util
import pathlib
import unittest

# Load by path: the rules are pure and this test must run without a bench.
_spec = importlib.util.spec_from_file_location("packout_rules", pathlib.Path(__file__).parents[1] / "packout_rules.py")
rules = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rules)


def source(block="A5", tag="red", bunches=100, kg=2000.0):
    return {"farm_block": block, "bunch_tag": tag, "bunches": bunches, "kg": kg}


class Sources(unittest.TestCase):
    def test_the_kg_of_the_sources_add_up_to_what_the_shift_took_in(self):
        sources = [source(), source("A6", bunches=50, kg=1000)]
        self.assertEqual(rules.check_sources(sources, 3000), [])
        self.assertIn("Tổng kg các nguồn (3000.0) phải bằng kg đưa vào ca (2990.0).", rules.check_sources(sources, 2990))

    def test_whole_bunches_kg_above_zero_and_one_row_per_lot_and_colour(self):
        errors = rules.check_sources([source(bunches=2.5), source("A6", kg=0), source("A6", kg=10)])
        self.assertEqual(len(errors), 3, errors)

    def test_a_colour_cannot_bring_more_bunches_than_were_harvested_and_not_yet_taken(self):
        harvested = {("A5", "red"): 120, ("A6", "red"): 50}
        elsewhere = {("A5", "red"): 30}
        self.assertEqual(rules.over_received([source(bunches=90)], harvested, elsewhere), [])
        self.assertEqual(rules.over_received([source(bunches=91), source("A6", bunches=10)], harvested, elsewhere),
                         [{"farm_block": "A5", "bunch_tag": "red", "bunches": 91, "left": 90}])
        self.assertEqual(rules.over_received([source("B1", bunches=1)], harvested, elsewhere)[0]["left"], 0, "nothing harvested there")


class Split(unittest.TestCase):
    def test_cartons_and_finished_goods_follow_the_kg(self):
        rows = rules.split([source(bunches=100, kg=2000), source("A6", bunches=40, kg=1000)], finished_kg=2400, secondary_kg=300, cartons=181)
        a5, a6 = rows
        self.assertEqual((a5["finished_kg"], a6["finished_kg"]), (1600.0, 800.0))
        self.assertEqual((a5["secondary_kg"], a6["secondary_kg"]), (200.0, 100.0))
        self.assertEqual((a5["cartons"], a6["cartons"]), (121, 60), "whole cartons, the remainder to the larger share")
        self.assertEqual(a5["cartons"] + a6["cartons"], 181)

    def test_kg_and_cartons_per_bunch_and_the_packout_rate(self):
        a5, a6 = rules.split([source(bunches=100, kg=2000), source("A6", bunches=40, kg=1000)], 2400, 300, 180)
        self.assertEqual((a5["kg_per_bunch"], a6["kg_per_bunch"]), (20.0, 25.0))
        self.assertEqual((a5["cartons_per_bunch"], a6["cartons_per_bunch"]), (1.2, 1.5))
        self.assertEqual(a5["packout_percent"], 80.0)

    def test_loss_and_a_shift_that_packs_more_than_it_took_in(self):
        self.assertEqual(rules.outputs(3000, 2400, 300), {"loss_kg": 300.0, "packout_percent": 80.0})
        self.assertIn("nhiều hơn kg đưa vào ca", rules.outputs(3000, 2900, 200)["error"])


class Receipt(unittest.TestCase):
    def test_each_lot_hands_over_kg_in_times_its_cost_per_kg_shared_by_kg_packed(self):
        rows = rules.split([source(bunches=100, kg=2000), source("A6", bunches=40, kg=1000)], 2400, 300, 180)
        lines, missing = rules.receipt_rows(rows, {"A5": 5000, "A6": 6000})
        self.assertEqual(missing, [])
        a5 = [l for l in lines if l["farm_block"] == "A5"]
        self.assertEqual([(l["kind"], l["qty"]) for l in a5], [("finished", 1600.0), ("secondary", 200.0)])
        self.assertAlmostEqual(sum(l["value"] for l in a5), 2000 * 5000, places=2)
        self.assertAlmostEqual(sum(l["value"] for l in lines), 2000 * 5000 + 1000 * 6000, places=2)

    def test_last_actual_cost_is_per_kg_packed_not_per_kg_brought_in(self):
        rows = rules.split([source(bunches=100, kg=2000)], 1600, 100, 120)
        lines, _ = rules.receipt_rows(rows, {"A5": 6000}, per_packed={"A5"})
        self.assertAlmostEqual(sum(l["value"] for l in lines), 1700 * 6000, places=2)
        self.assertTrue(all(abs(l["rate"] - 6000) < 0.01 for l in lines))

    def test_a_lot_without_a_cost_is_named(self):
        rows = rules.split([source(), source("A6", kg=1000)], 2400, 0, 0)
        lines, missing = rules.receipt_rows(rows, {"A5": 5000})
        self.assertEqual(missing, ["A6"])
        self.assertEqual({l["farm_block"] for l in lines}, {"A5"})


if __name__ == "__main__":
    unittest.main()
