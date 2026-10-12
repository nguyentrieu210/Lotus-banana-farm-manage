import unittest
from lotus_farm.piece_pay import terms, piece_amount
from lotus_farm.rules import RuleError


class AssignmentPayTests(unittest.TestCase):
    def test_800_at_2000_then_accept_only_750(self):
        quote = terms(2000, None, 800)
        self.assertEqual(quote['estimated_amount'], 1600000)
        self.assertEqual(quote['price_approval_state'], 'Not Required')
        self.assertEqual(piece_amount(750, quote['agreed_unit_price']), 1500000)

    def test_lower_equal_and_higher_price(self):
        self.assertEqual(terms(2000, 1800, 800)['price_approval_state'], 'Not Required')
        self.assertEqual(terms(2000, 2000, 800)['price_approval_state'], 'Not Required')
        with self.assertRaises(RuleError):
            terms(2000, 2200, 800)
        higher = terms(2000, 2200, 800, 'Long access route')
        self.assertEqual(higher['price_approval_state'], 'Pending')
        self.assertEqual(higher['estimated_amount'], 1760000)

    def test_invalid_prices_never_become_zero_pay(self):
        for price in (0, -1, 'NaN', 'Infinity'):
            with self.assertRaises(RuleError):
                terms(2000, price, 800)

