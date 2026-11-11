import unittest
from lotus_farm.rules import (
    quantity,
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

