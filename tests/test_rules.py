import unittest
from lotus_farm.forecasting import calculate_availability, ForecastInputError
from lotus_farm.rules import (
    quantity,
    reconcile_mass,
    reserve_limit,
    scale_net,
    calibration,
    forecast_accuracy,
    canonical_hash,
    RuleError,
)


class TestBRDRules(unittest.TestCase):
    def test_brd_golden_forecast_and_signed_shortage(self):
        values = calculate_availability(
            1000,
            25,
            bunch_survival_rate_percent=97,
            quality_pass_rate_percent=92,
            packout_rate_percent=84,
            safety_buffer_percent=5,
            committed_qty_kg=5000,
        )
        self.assertEqual(values["gross_forecast_kg"], 24250)
        self.assertEqual(values["saleable_forecast_kg"], 22310)
        self.assertEqual(values["packed_forecast_kg"], 18740.4)
        self.assertEqual(values["safe_saleable_kg"], 17803.38)
        self.assertEqual(values["available_to_promise_kg"], 12803.38)
        short = calculate_availability(10, 20, committed_qty_kg=300)
        self.assertEqual(short["available_to_promise_kg"], -100)
        self.assertEqual(short["shortage_kg"], 100)

    def test_nonfinite_numbers_and_out_of_range_rates(self):
        for value in ["nan", "inf", "-inf", -1]:
            with self.subTest(value=value), self.assertRaises(RuleError):
                quantity(value)
            with self.subTest(value=value), self.assertRaises(ForecastInputError):
                calculate_availability(value, 25)
        for value in [-1, 101, float("nan")]:
            with self.assertRaises(ForecastInputError):
                calculate_availability(10, 25, packout_rate_percent=value)

    def test_qc_not_subtracted_twice(self):
        values = calculate_availability(
            100, 10, quality_pass_rate_percent=80, expected_defect_rate_percent=20, packout_rate_percent=75
        )
        self.assertEqual(values["packed_forecast_kg"], 600)

    def test_reservation_rejects_second_planner_and_excess_demand(self):
        self.assertEqual(reserve_limit(10000, 0, 8000, 8000), 8000)
        with self.assertRaises(RuleError):
            reserve_limit(10000, 8000, 8000, 8000)
        with self.assertRaises(RuleError):
            reserve_limit(10000, 0, 8000, 5000)
        with self.assertRaises(RuleError):
            reserve_limit(10000, 0, 0, 5000)

    def test_mass_balance_keeps_reject_and_loss(self):
        result = reconcile_mass([800, 200], [600, 300], 80, 20, 0)
        self.assertEqual(result["mass_variance_kg"], 0)
        with self.assertRaises(RuleError):
            reconcile_mass([1000], [900], 0, 0, 1)
        with self.assertRaises(RuleError):
            reconcile_mass([1000], [1100], 0, 0, 1)
        self.assertEqual(reconcile_mass([0.3], [0.1], 0.1, 0.1, 0)["mass_variance_kg"], 0)

    def test_scale_tare_cannot_exceed_gross(self):
        self.assertEqual(scale_net(1275.4, 84.7), 1190.7)
        with self.assertRaises(RuleError):
            scale_net(10, 11)

    def test_weighted_learning(self):
        rows = [
            dict(harvested_bunch_qty=1, gross_weight_kg=10, saleable_weight_kg=8),
            dict(harvested_bunch_qty=9, gross_weight_kg=270, saleable_weight_kg=243),
        ]
        result = calibration(rows, 2)
        self.assertEqual(result["avg_bunch_weight_kg"], 28)
        self.assertAlmostEqual(result["quality_pass_rate_percent"], 251 / 280 * 100)
        with self.assertRaises(RuleError):
            calibration(rows, 3)
        self.assertIsNone(forecast_accuracy([(0, 0)])["wape"])
        self.assertEqual(forecast_accuracy([(110, 100), (80, 100)])["wape"], 0.15)
        self.assertEqual(forecast_accuracy([(110, 100), (80, 100)])["bias"], -0.05)

    def test_payload_hash_detects_conflicts(self):
        self.assertEqual(canonical_hash({"b": 1, "a": 2}), canonical_hash({"a": 2, "b": 1}))
        self.assertNotEqual(canonical_hash({"kg": 1}), canonical_hash({"kg": 2}))
