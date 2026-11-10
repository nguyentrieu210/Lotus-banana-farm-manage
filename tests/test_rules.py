import unittest
from lotus_farm.rules import (
    quantity,
    forecast_accuracy,
    canonical_hash,
    integer_quantity,
    RuleError,
)


class TestBRDRules(unittest.TestCase):
    def test_nonfinite_and_negative_numbers_are_rejected(self):
        for value in ["nan", "inf", "-inf", -1]:
            with self.subTest(value=value), self.assertRaises(RuleError):
                quantity(value)
        with self.assertRaises(RuleError):
            quantity(0, positive=True)
        self.assertEqual(quantity("1275.4"), quantity(1275.4))

    def test_counts_are_whole_numbers(self):
        self.assertEqual(integer_quantity("12"), 12)
        with self.assertRaises(RuleError):
            integer_quantity(1.5)

    def test_forecast_accuracy_is_weighted_by_actual(self):
        self.assertIsNone(forecast_accuracy([(0, 0)])["wape"])
        self.assertEqual(forecast_accuracy([(110, 100), (80, 100)])["wape"], 0.15)
        self.assertEqual(forecast_accuracy([(110, 100), (80, 100)])["bias"], -0.05)

    def test_payload_hash_detects_conflicts(self):
        self.assertEqual(canonical_hash({"b": 1, "a": 2}), canonical_hash({"a": 2, "b": 1}))
        self.assertNotEqual(canonical_hash({"kg": 1}), canonical_hash({"kg": 2}))
