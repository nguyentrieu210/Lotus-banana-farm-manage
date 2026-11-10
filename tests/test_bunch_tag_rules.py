import unittest
from datetime import date
from lotus_farm.bunch_tag_rules import day, locked_changes, overlaps, manual_tag_code


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

    def test_a_form_save_of_a_used_colour_is_compared_as_stored(self):
        # As read from the database, and as the Danh mục form or Desk sends it back (dates as text, numbers maybe as text).
        weekly = {"farm": "LOTUS-222", "tag_code": "LW-222-2026W44-1", "color_code": "C02", "color_label": "Trắng",
                  "period_basis": "Cut Bud", "valid_from": date(2026, 10, 26), "valid_to": date(2026, 10, 29), "week_year": 2026,
                  "week_number": 44, "week_half": "1", "source_kind": "Lotus Weekly", "display_name": "Trắng · Tuần 44/2026", "enabled": 1}
        sent = dict(weekly, valid_from="2026-10-26", valid_to="2026-10-29", week_year="2026", week_number=44.0,
                    display_name="Trắng tuần 44", enabled=0)
        self.assertEqual(locked_changes(weekly, sent), [])
        self.assertEqual(locked_changes(weekly, dict(sent, valid_to="2026-10-30", week_number="45")), ["valid_to", "week_number"])
        self.assertEqual(locked_changes(weekly, dict(sent, color_label="Đỏ")), ["color_label"])
        # A manual period has no week: empty stays empty however it comes back.
        manual = dict(weekly, color_label=None, week_year=0, week_number=0, week_half=None, source_kind=None)
        self.assertEqual(locked_changes(manual, dict(manual, color_label="", week_year="", week_number=None, week_half="")), [])
        self.assertEqual(locked_changes(manual, dict(manual, valid_to=None)), ["valid_to"])


if __name__ == "__main__":
    unittest.main()
