import unittest
from datetime import date
from lotus_farm.ribbon_cycle import periods, week_color


class RibbonCycleTest(unittest.TestCase):
    def test_table_sent_29_10_2026(self):
        expected = ["Đỏ", "Trắng", "Tím", "Cam", "Đen", "Xanh dương", "Đỏ - Xanh lá", "Trắng - Xanh lá",
                    "Tím - Xanh lá", "Cam - Xanh lá", "Đen - Xanh lá", "Xanh lá - Xanh dương"]
        rows = [r for r in periods() if r["week_half"] == "1"][:12]
        self.assertEqual([r["color_label"] for r in rows], expected)
        self.assertEqual((rows[10]["week_year"], rows[10]["week_number"]), (2026, 53))
        self.assertEqual((rows[11]["week_year"], rows[11]["week_number"]), (2027, 1))
        self.assertEqual(rows[1]["valid_from"], "2026-10-26")

    def test_cycle_repeats_every_twelve_weeks(self):
        self.assertEqual(week_color(date(2027, 1, 11)), week_color(date(2026, 10, 19)))
        self.assertEqual(week_color(date(2027, 12, 27))[1], "Tím")

    def test_both_halves_share_the_colour_and_cover_the_week(self):
        rows = list(periods())
        self.assertEqual(len(rows), 126)
        for first, second in zip(rows[::2], rows[1::2]):
            self.assertEqual(first["color_code"], second["color_code"])
            self.assertEqual((date.fromisoformat(second["valid_to"]) - date.fromisoformat(first["valid_from"])).days, 6)
        self.assertEqual(len({r["tag_code"] for r in rows}), len(rows))


if __name__ == "__main__":
    unittest.main()
