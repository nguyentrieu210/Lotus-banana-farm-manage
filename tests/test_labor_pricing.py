import unittest
from lotus_farm.labor_pricing import labor_settings


class LaborPricingTests(unittest.TestCase):
    def test_daywork_is_productivity_not_price(self):
        self.assertEqual(labor_settings(1, 0, 80, 0), {'mode': 'Daywork', 'productivity': 80, 'piecework_rate': 0})

    def test_piecework_keeps_productivity_even_when_paid_by_piece(self):
        self.assertEqual(labor_settings(0, 1, 80, 2000), {'mode': 'Piece', 'productivity': 80, 'piecework_rate': 2000})

    def test_both_are_independent(self):
        self.assertEqual(labor_settings(1, 1, 80, 2000), {'mode': 'Both', 'productivity': 80, 'piecework_rate': 2000})

    def test_invalid_rates(self):
        for args in [(0, 1, 0, 0), (1, 0, 0, 0), (0, 1, 80, -1), (1, 1, 80, float('inf')),
                     (0, 1, 0, 2000), (1, 0, 'many', 0)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                labor_settings(*args)

    def test_original_snapshot_does_not_change(self):
        first = labor_settings(1, 1, 80, 2000)
        next_version = labor_settings(1, 1, 100, 3000)
        self.assertEqual((first['productivity'], first['piecework_rate']), (80, 2000))
        self.assertEqual((next_version['productivity'], next_version['piecework_rate']), (100, 3000))

    def test_legacy_default_keeps_daywork(self):
        self.assertEqual(labor_settings(0, 0, 40, 0)['mode'], 'Daywork')


if __name__ == '__main__':
    unittest.main()
