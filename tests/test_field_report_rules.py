import unittest
from datetime import date
from lotus_farm import field_report_rules as r


class FieldWorkRulesTest(unittest.TestCase):
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

    def test_pay_by_mode(self):
        self.assertEqual(r.pay_amount("Count", 120, None, 4000), 480000, "khoán số lượng: what was reported")
        self.assertEqual(r.pay_amount("Lot", 1.2, 4.48, 300000, passed=True), 1344000, "khoán lô: the whole lô")
        self.assertEqual(r.pay_amount("Lot", 4.48, 4.48, 300000, passed=False), 0, "failed inspection: nothing")
        self.assertEqual(r.pay_amount("Daywork", 3, 4.48, 300000), 0, "công nhật is paid from the clock")
        self.assertEqual(r.whole_lot_qty("Trees", 4.48, 10668), 10668)
        self.assertIsNone(r.whole_lot_qty("Count", 4.48, 10668))

    def test_split_keeps_the_total(self):
        shares = r.split_by_sessions(1000000, {"A": 2, "B": 2, "C": 1})
        self.assertEqual(shares, {"A": 400000, "B": 400000, "C": 200000})
        odd = r.split_by_sessions(100000, {"A": 1, "B": 1, "C": 1})
        self.assertEqual(sum(odd.values()), 100000)
        self.assertEqual(r.split_by_sessions(0, {"A": 1}), {"A": 0})
        self.assertEqual(r.split_by_sessions(5000, {}), {})

    def test_ticket_flow(self):
        self.assertEqual(r.next_state("Open", "report"), "Reported")
        self.assertEqual(r.next_state("Failed", "report"), "Reported", "rework after a failed inspection")
        self.assertEqual(r.next_state("Reported", "approve", "Lot"), "Approved", "khoán lô waits for the inspection")
        self.assertEqual(r.next_state("Reported", "approve", "Count"), "Passed", "counted work needs no inspection")
        self.assertEqual(r.next_state("Approved", "fail"), "Failed")
        self.assertEqual(r.next_state("Passed", "lock"), "Locked")
        with self.assertRaisesRegex(ValueError, "trạng thái"):
            r.next_state("Locked", "cancel")
        with self.assertRaisesRegex(ValueError, "trạng thái"):
            r.next_state("Open", "approve", "Lot")
        self.assertTrue(r.can_report("Failed"))
        self.assertFalse(r.can_report("Reported"))

    def test_inspection(self):
        self.assertEqual(r.inspection_result(20, 19, 95), (95.0, "Pass"))
        self.assertEqual(r.inspection_result(20, 18, 95), (90.0, "Fail"))
        self.assertEqual(r.inspection_result(30, 27, 90), (90.0, "Pass"))
        with self.assertRaisesRegex(ValueError, "mẫu"):
            r.inspection_result(0, 0, 90)
        with self.assertRaisesRegex(ValueError, "đạt"):
            r.inspection_result(20, 21, 90)

    def test_caps(self):
        self.assertEqual(r.cap_left("LotArea", 1.5, lot_area=4.48), 2.98)
        self.assertEqual(r.cap_left("LotTrees", 11000, lot_trees=10668), 0, "never negative")
        self.assertEqual(r.cap_left("CutBud", 30, cut=40), 10)
        self.assertIsNone(r.cap_left("None", 10))
        self.assertFalse(r.cap_blocks("2026-11-30"))
        self.assertTrue(r.cap_blocks(date(2026, 12, 1)))

    def test_bunch_cannot_exceed_cut_bud_of_its_colour(self):
        cut = {("A1", "W44"): 40}
        done = {("A1", "W44", "Bag"): 30}
        row = {"farm_block": "A1", "bunch_tag": "W44", "stage": "Bag", "qty": 10}
        self.assertEqual(r.bunch_over_cut(cut, done, [row]), {})
        self.assertEqual(r.bunch_over_cut(cut, done, [dict(row, qty=15)]), {("A1", "W44", "Bag"): (45.0, 40.0)})
        self.assertEqual(r.bunch_over_cut(cut, done, [dict(row, stage="Prop", qty=40)]), {}, "another stage counts apart")

    def test_minimum_topup(self):
        # 10 buổi khoán = 40 giờ; vùng II 22.700 đ/giờ → sàn 908.000 đ.
        self.assertEqual(r.minimum_topup(800000, 10, 22700), 108000)
        self.assertEqual(r.minimum_topup(1000000, 10, 22700), 0)
        self.assertEqual(r.minimum_topup(0, 0, 22700), 0)

    def test_quarantine_and_state_display(self):
        self.assertEqual(r.quarantine_until("2026-11-02", 7), date(2026, 11, 9))
        self.assertIsNone(r.quarantine_until("2026-11-02", 0))
        self.assertEqual(r.display_state("Open", "2026-10-28", "2026-10-29"), "Late")
        self.assertEqual(r.display_state("Open", None, "2026-10-29", reported=True), "Working")
        self.assertEqual(r.display_state("Locked", "2026-10-28", "2026-10-29"), "Locked")

    def test_under_norm_and_zones(self):
        self.assertTrue(r.under_norm(4.48, 9, 1))
        self.assertFalse(r.under_norm(0, 9, 1), "no output recorded")
        self.assertEqual(r.crew_zones("A + B"), ["A", "B"])


if __name__ == "__main__":
    unittest.main()
