import unittest
from lotus_farm import plan_book2_reference as ref


class Book2PlanReferenceTests(unittest.TestCase):
    def test_43_codes_unique(self):
        rows = ref.catalogue()
        self.assertEqual(len(rows), 43)
        self.assertEqual([r["code"] for r in rows], [
            "CV%03d" % n for n in range(1, 44)
        ])

    def test_key_timings_from_excel(self):
        rows = {r["code"]: r for r in ref.catalogue()}
        self.assertEqual(rows["CV002"]["periodic"]["times_per_month"], 2)
        self.assertEqual(rows["CV003"]["periodic"]["times_per_month"], 1)
        self.assertEqual(rows["CV004"]["periodic"]["repeat_months"], 2)
        self.assertEqual(rows["CV010"]["periodic"]["times_per_month"], 2)
        self.assertEqual(
            [rows["CV%03d" % n]["injection_offset_days"] for n in (23, 25, 27, 31)],
            [7, 10, 13, 16],
        )
        self.assertTrue(rows["CV034"]["requires_manual_anchor"])

    def test_reconciliation_does_not_fake_missing_work_type(self):
        comparison = ref.compare([
            dict(name="W", work_code="CV002", productivity_per_workday=5,
                 piecework_rate=75000, allow_daywork=1)
        ])
        self.assertEqual(len(comparison["works"]), 43)
        self.assertEqual(comparison["works"][1]["work_type"], "W")
        self.assertEqual(len(comparison["missing_codes"]), 42)
        self.assertEqual(comparison["daywork_rate"], 290000)
        self.assertEqual(comparison["absence_reserve"], 0.1)
        self.assertEqual(sum(comparison["flower_shares"]), 1.0)


if __name__ == "__main__":
    unittest.main()
