import importlib.util
import pathlib
import unittest

_spec = importlib.util.spec_from_file_location("report_filter_rules", pathlib.Path(__file__).parents[1] / "report_filter_rules.py")
rules = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rules)


def fact(day, zone="A", block="A1"):
    return dict(rules.date_facts(day), zone=zone, block=block)


FACTS = [fact("2026-10-21"), fact("2026-11-04", block="A10"), fact("2026-11-05", zone="B", block="B2"), fact("2027-01-06", zone="B", block="B3")]


class DateFacts(unittest.TestCase):
    def test_week_follows_the_iso_year(self):
        self.assertEqual(rules.date_facts("2027-01-01"), {"year": "2026", "month": "2027-01", "week": "2026-W53", "day": "2027-01-01"})

    def test_a_plain_day(self):
        self.assertEqual(rules.date_facts("2026-11-09")["week"], "2026-W46")


class Keep(unittest.TestCase):
    def test_no_filter_keeps_everything(self):
        self.assertTrue(rules.keep(FACTS[0], {}))

    def test_fields_combine(self):
        wanted = rules.clean({"zone": ["B"], "month": ["2026-11"]})
        self.assertEqual([f["block"] for f in FACTS if rules.keep(f, wanted)], ["B2"])

    def test_several_values_of_a_field(self):
        wanted = rules.clean({"block": ["A1", "B3"]})
        self.assertEqual(len([f for f in FACTS if rules.keep(f, wanted)]), 2)

    def test_nothing_ticked_shows_nothing(self):
        self.assertFalse(rules.keep(FACTS[0], rules.clean({"zone": []})))

    def test_a_field_the_row_does_not_have_does_not_exclude_it(self):
        self.assertTrue(rules.keep(FACTS[0], rules.clean({"team": ["Tổ 01"]})))


class Options(unittest.TestCase):
    def test_other_fields_narrow_the_list(self):
        result = rules.options(FACTS, rules.clean({"zone": ["B"]}), ("block", "zone"))
        self.assertEqual([o["value"] for o in result["block"]], ["B2", "B3"])

    def test_a_row_without_the_field_does_not_widen_the_lists(self):
        facts = [dict(rules.date_facts("2026-10-21"), colour="Đỏ"), rules.date_facts("2026-11-09")]
        result = rules.options(facts, rules.clean({"colour": ["Đỏ"]}), ("week",))
        self.assertEqual([o["value"] for o in result["week"]], ["2026-W43"])

    def test_a_field_ignores_its_own_filter(self):
        result = rules.options(FACTS, rules.clean({"zone": ["B"]}), ("zone",))
        self.assertEqual([o["value"] for o in result["zone"]], ["A", "B"])

    def test_lots_in_natural_order_and_time_newest_first(self):
        result = rules.options(FACTS, {}, ("block", "month"))
        self.assertEqual([o["value"] for o in result["block"]], ["A1", "B2", "B3", "A10"])
        self.assertEqual(result["month"][0]["value"], "2027-01")

    def test_labels_are_for_people(self):
        result = rules.options([dict(rules.date_facts("2026-11-09"), lan="2")], {}, ("month", "week", "day", "lan"))
        self.assertEqual(result["month"][0]["label"], "Tháng 11/2026")
        self.assertEqual(result["week"][0]["label"], "Tuần 46 · 09/11 – 15/11/2026")
        self.assertEqual(result["day"][0]["label"], "09/11/2026")
        self.assertEqual(result["lan"][0]["label"], "Lần 2")

    def test_empty_values_are_not_offered(self):
        self.assertEqual(rules.options([{"zone": ""}], {}, ("zone",))["zone"], [])


if __name__ == "__main__":
    unittest.main()
