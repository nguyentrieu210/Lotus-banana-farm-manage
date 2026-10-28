import unittest
from datetime import date
from lotus_farm.bunch_tag_rules import day, overlaps, manual_tag_code


class BunchTagDateRulesTest(unittest.TestCase):
    def test_inclusive_overlap(self):
        self.assertTrue(overlaps("2026-11-01", "2026-11-05", "2026-11-05", "2026-11-09"))
        self.assertFalse(overlaps("2026-11-01", "2026-11-05", "2026-11-06", "2026-11-10"))

    def test_open_ended_legacy(self):
        self.assertTrue(overlaps("2026-11-01", "2026-11-05", "2026-10-01", None))
        self.assertFalse(overlaps("2026-11-01", "2026-11-05", "2026-12-01", None))

    def test_code_stable_and_farm_specific(self):
        first = manual_tag_code("Farm 222", "2026-11-01", "M01")
        self.assertEqual(first, manual_tag_code("Farm 222", date(2026, 11, 1), "M01"))
        self.assertNotEqual(first, manual_tag_code("Farm 180", "2026-11-01", "M01"))
        self.assertNotEqual(first, manual_tag_code("Farm 222", "2026-11-02", "M01"))

    def test_parse_day(self):
        self.assertEqual(day("2026-11-01"), date(2026, 11, 1))


if __name__ == "__main__":
    unittest.main()
