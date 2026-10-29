import unittest
from datetime import date, datetime
from lotus_farm import field_report_rules as r


class FieldReportRulesTest(unittest.TestCase):
    rates = [
        {"work_type": "CL", "rate": 300000, "basis": "Area", "valid_from": "2026-10-21"},
        {"work_type": "CL", "rate": 320000, "basis": "Area", "valid_from": "2026-12-01"},
        {"work_type": "BB", "rate": 4000, "basis": "Count", "valid_from": "2026-10-21", "valid_to": "2026-11-30"},
    ]

    def test_price_in_force_on_the_day(self):
        self.assertEqual(r.rate_for(self.rates, "CL", "2026-11-15")["rate"], 300000)
        self.assertEqual(r.rate_for(self.rates, "CL", date(2026, 12, 1))["rate"], 320000)
        self.assertIsNone(r.rate_for(self.rates, "CL", "2026-10-20"))
        self.assertIsNone(r.rate_for(self.rates, "BB", "2026-12-01"), "expired price")

    def test_whole_lot_and_money(self):
        self.assertEqual(r.whole_lot_qty("Area", 4.48, 10668), 4.48)
        self.assertEqual(r.whole_lot_qty("Trees", 4.48, 10668), 10668)
        self.assertIsNone(r.whole_lot_qty("Count", 4.48, 10668))
        self.assertEqual(r.amount("Piece", 4.48, 300000), 1344000)
        self.assertEqual(r.amount("Daywork", 4.48, 300000), 0, "công nhật is paid from attendance")

    def test_under_norm(self):
        self.assertTrue(r.under_norm(4.48, 9, 1))      # 0,5 ha/công < 1 ha/công
        self.assertFalse(r.under_norm(4.48, 4, 1))
        self.assertFalse(r.under_norm(4.48, 0, 1), "no workdays: nothing to judge")
        self.assertFalse(r.under_norm(4.48, 9, 0), "no norm configured")
        self.assertFalse(r.under_norm(0, 9, 1), "no output recorded")

    def test_confirmation_deadline(self):
        self.assertEqual(r.deadline("2026-10-29"), datetime(2026, 10, 30, 10))
        self.assertFalse(r.overdue("2026-10-29", datetime(2026, 10, 30, 9, 59), "Draft"))
        self.assertTrue(r.overdue("2026-10-29", datetime(2026, 10, 30, 10, 1), "Draft"))
        self.assertFalse(r.overdue("2026-10-29", datetime(2026, 11, 2), "Confirmed"))

    def test_line_shapes(self):
        ok = r.check_line({"pay_kind": "Piece", "farm_block": "A1", "qty": 2.88, "workdays_am": 4, "workdays_pm": 3.5})
        self.assertEqual(ok["workdays"], 7.5)
        with self.assertRaisesRegex(ValueError, "từng lô"):
            r.check_line({"pay_kind": "Piece", "location": "Zone", "zone": "A", "qty": 1})
        r.check_line({"pay_kind": "Daywork", "location": "Zone", "zone": "A", "workdays_am": 3})
        with self.assertRaisesRegex(ValueError, "hai lô"):
            r.check_line({"pay_kind": "Daywork", "location": "Blocks", "blocks": "A1", "workdays_am": 1})
        with self.assertRaisesRegex(ValueError, "số công hoặc khối lượng"):
            r.check_line({"pay_kind": "Daywork", "farm_block": "A1"})
        with self.assertRaisesRegex(ValueError, "không âm"):
            r.check_line({"pay_kind": "Daywork", "farm_block": "A1", "qty": -1})
        with self.assertRaisesRegex(ValueError, "CN"):
            r.check_line({"farm_block": "A1", "qty": 1})

    def test_one_lot_is_paid_once_a_day(self):
        line = {"pay_kind": "Piece", "basis": "Area", "work_type": "CL", "farm_block": "A8", "lot_area_ha": 4.48, "lot_trees": 10668}
        self.assertIsNone(r.over_whole_lot([dict(line, qty=2.48), dict(line, qty=2)]), "two tổ split the lot")
        self.assertEqual(r.over_whole_lot([dict(line, qty=4.48), dict(line, qty=4.48)]), ("CL", "A8", 8.96, 4.48))
        self.assertIsNone(r.over_whole_lot([dict(line, qty=4.48), dict(line, work_type="DC", qty=4.48)]), "different work")
        self.assertIsNone(r.over_whole_lot([dict(line, basis="Count", qty=500), dict(line, basis="Count", qty=500)]), "counted work")

    def test_crew_zones(self):
        self.assertEqual(r.crew_zones("A + B"), ["A", "B"])
        self.assertEqual(r.crew_zones("d, e"), ["D", "E"])


if __name__ == "__main__":
    unittest.main()
