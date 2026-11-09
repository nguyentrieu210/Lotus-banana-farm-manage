import datetime as dt
import importlib.util
import pathlib
import unittest

_spec = importlib.util.spec_from_file_location("work_report_rules", pathlib.Path(__file__).parents[1] / "work_report_rules.py")
rules = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rules)

BLOCKS = {"B1": {"code": "A1", "zone": "A"}, "B2": {"code": "A10", "zone": "A"}, "B3": {"code": "A2", "zone": "A"}}
WORKS = {"W": {"name": "Cắt lá", "uom": "Ha"}, "S": {"name": "Phun thuốc", "uom": "Ha"}}
TEAMS = {"X": "Tổ 01"}


def entry(name="e1", work="W", block="B1", qty=1.5, day="2026-11-09", morning=4, afternoon=2, **extra):
    return dict({"name": name, "work_type": work, "farm_block": block, "qty": qty, "posting_date": day, "morning_people": morning, "afternoon_people": afternoon, "work_team": "X", "done": 0, "notes": ""}, **extra)


class ByWork(unittest.TestCase):
    def run_it(self, entries, materials=None):
        return rules.by_work(entries, materials or {}, WORKS, BLOCKS, TEAMS, {"I": "Thuốc A"})

    def test_two_buoi_make_one_cong(self):
        self.assertEqual(rules.workdays(4, 2), 3)

    def test_one_card_per_work_with_totals(self):
        result = self.run_it([entry(), entry("e2", block="B2", qty=2), entry("e3", "S", qty=1)])
        self.assertEqual(len(result["cards"]), 2)
        card = next(c for c in result["cards"] if c["name"] == "Cắt lá")
        self.assertEqual((card["qty"], card["lots"], card["workdays"]), (3.5, 2, 6))
        self.assertEqual((result["entries"], result["lots"], result["workdays"]), (3, 2, 9))

    def test_lines_are_in_date_then_natural_lot_order(self):
        card = self.run_it([entry("e2", block="B2"), entry("e1", block="B3"), entry("e0", block="B1", day="2026-11-08")])["cards"][0]
        self.assertEqual([r["block_code"] for r in card["rows"]], ["A1", "A2", "A10"])

    def test_materials_add_up_per_work_and_overall(self):
        materials = {"e1": [{"item_code": "I", "qty": 2, "uom": "Lít", "dose": "1/1000", "phi_days": 7}], "e2": [{"item_code": "I", "qty": 3, "uom": "Lít", "dose": "", "phi_days": 7}]}
        result = self.run_it([entry(work="S"), entry("e2", "S", block="B2")], materials)
        self.assertEqual(result["materials"], [{"item": "I", "name": "Thuốc A", "qty": 5, "uom": "Lít"}])
        self.assertEqual(result["cards"][0]["rows"][0]["materials"][0]["dose"], "1/1000")

    def test_lots_or_work_outside_the_scope_are_left_out(self):
        self.assertEqual(self.run_it([entry(block="Z"), entry("e2", "NO")])["cards"], [])


class Quarantine(unittest.TestCase):
    def test_only_lots_still_held_longest_first(self):
        today = dt.date(2026, 11, 9)
        result = rules.quarantine([("B1", "2026-11-10"), ("B2", "2026-11-20"), ("B3", "2026-11-08")], BLOCKS, today)
        self.assertEqual([(r["code"], r["days"]) for r in result], [("A10", 11), ("A1", 1)])

    def test_last_day_still_counts(self):
        self.assertEqual(len(rules.quarantine([("B1", "2026-11-09")], BLOCKS, dt.date(2026, 11, 9))), 1)


class Disease(unittest.TestCase):
    def row(self, name="d1", disease="Sigatoka", block="B1", plants=10):
        return {"name": name, "disease": disease, "farm_block": block, "posting_date": "2026-11-09", "affected_plants": plants, "severity": "Nhẹ", "action_taken": "Phun"}

    def test_grouped_by_disease_worst_first(self):
        result = rules.disease_summary([self.row(), self.row("d2", block="B2", plants=5), self.row("d3", "Héo", plants=40)], BLOCKS)
        self.assertEqual([(d["disease"], d["plants"], d["lots"]) for d in result], [("Héo", 40, 1), ("Sigatoka", 15, 2)])


class Packhouse(unittest.TestCase):
    def shift(self, name="s1", day="2026-12-25", **figures):
        return dict({"name": name, "posting_date": day, "input_kg": 1000, "finished_kg": 800, "secondary_kg": 100, "loss_kg": 100, "cartons": 60, "labor": 12}, **figures)

    def test_packout_comes_from_the_kilograms(self):
        result = rules.packhouse([self.shift(), self.shift("s2", input_kg=3000, finished_kg=1500)])
        self.assertEqual(result["totals"]["packout"], 57.5)
        self.assertEqual(result["totals"]["shifts"], 2)

    def test_days_newest_first(self):
        result = rules.packhouse([self.shift(day="2026-12-24"), self.shift("s2", day="2026-12-25")])
        self.assertEqual([d["date"] for d in result["days"]], ["2026-12-25", "2026-12-24"])

    def test_nothing_recorded(self):
        result = rules.packhouse([])
        self.assertEqual((result["days"], result["totals"]["packout"]), ([], None))


if __name__ == "__main__":
    unittest.main()
