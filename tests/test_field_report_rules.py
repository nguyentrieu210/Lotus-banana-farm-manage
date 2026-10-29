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

    def test_round_is_paid_once_on_xong(self):
        self.assertEqual(r.round_amount("Area", False, 1.2, 4.48, 300000), 0, "progress day: nothing paid")
        self.assertEqual(r.round_amount("Area", True, 0.5, 4.48, 300000), 1344000, "Xong: the whole lot")
        self.assertEqual(r.round_amount("Trees", True, None, 10668, 300), 3200400)
        self.assertEqual(r.round_amount("Count", False, 1062, None, 200), 212400, "counted work is paid as reported")
        self.assertEqual(r.paid_qty("Area", True, 0.5, 4.48), 4.48)
        self.assertEqual(r.paid_qty("Area", False, 0.5, 4.48), 0)
        self.assertEqual(r.paid_qty("Count", True, 410, None), 410)

    def test_display_state(self):
        today = "2026-10-29"
        self.assertEqual(r.display_state("Open", None, today), "Assigned")
        self.assertEqual(r.display_state("Open", "2026-10-30", today, reported=True), "Working")
        self.assertEqual(r.display_state("Open", "2026-10-28", today, reported=True), "Late")
        self.assertEqual(r.display_state("Open", "2026-10-28", today, reported=True, reported_done=True), "Reported")
        self.assertEqual(r.display_state("Done", "2026-10-28", today), "Done")
        self.assertEqual(r.display_state("Cancelled", None, today), "Cancelled")

    def test_bunch_cannot_exceed_cut_bud_of_its_colour(self):
        cut = {("A1", "W44"): 40}
        done = {("A1", "W44", "Bag"): 30}
        row = {"farm_block": "A1", "bunch_tag": "W44", "stage": "Bag", "qty": 10}
        self.assertEqual(r.bunch_over_cut(cut, done, [row]), {}, "exactly the cut count")
        self.assertEqual(r.bunch_over_cut(cut, done, [dict(row, qty=15)]), {("A1", "W44", "Bag"): (45.0, 40.0)})
        self.assertEqual(r.bunch_over_cut(cut, done, [dict(row, stage="Prop", qty=40)]), {}, "another stage counts apart")
        self.assertIn(("A1", "W45", "Bag"), r.bunch_over_cut(cut, done, [dict(row, bunch_tag="W45", qty=1)]), "nothing cut of that colour")
        self.assertEqual(r.bunch_over_cut(cut, done, [dict(row, stage="Cut Bud", qty=99)]), {}, "cắt bắp itself is not capped")
        self.assertFalse(r.cap_blocks("2026-11-30"))
        self.assertTrue(r.cap_blocks(date(2026, 12, 1)))

    def test_crew_zones(self):
        self.assertEqual(r.crew_zones("A + B"), ["A", "B"])
        self.assertEqual(r.crew_zones("d, e"), ["D", "E"])


if __name__ == "__main__":
    unittest.main()
