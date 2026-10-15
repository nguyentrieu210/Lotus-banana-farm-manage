import unittest
from lotus_farm.labor_pricing import labor_settings, planned_labor


class LaborPricingTests(unittest.TestCase):
    def test_daywork_is_productivity_not_price(self):
        settings = labor_settings(1, 0, 80, 0)
        self.assertEqual(settings['mode'], 'Daywork')
        self.assertEqual(planned_labor(800, settings), {
            'required_workdays': 10, 'estimated_piecework_amount': 0})

    def test_piecework_estimates_labor_even_when_paid_by_piece(self):
        settings = labor_settings(0, 1, 80, 2000)
        self.assertEqual(settings['mode'], 'Piece')
        self.assertEqual(planned_labor(800, settings), {
            'required_workdays': 10, 'estimated_piecework_amount': 1600000})

    def test_both_are_independent(self):
        settings = labor_settings(1, 1, 80, 2000)
        self.assertEqual(settings['mode'], 'Both')
        self.assertEqual(planned_labor(800, settings), {
            'required_workdays': 10, 'estimated_piecework_amount': 1600000})
        self.assertEqual(labor_settings(1, 1, 80, 2000, 'Daywork')['piecework_rate'], 0)
        self.assertEqual(labor_settings(1, 1, 80, 2000, 'Piece')['productivity'], 80)

    def test_invalid_rates_and_modes(self):
        for args in [(0, 1, 0, 0, 'Piece'), (1, 0, 0, 0, 'Daywork'),
                     (0, 1, 0, -1, 'Piece'), (1, 1, 80, float('inf'), 'Both'),
                     (1, 1, 80, 2000, 'Wrong'), (0, 1, 0, 2000, 'Daywork'), (0, 1, 0, 2000, 'Piece')]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                labor_settings(*args)

    def test_original_snapshot_does_not_change(self):
        first = labor_settings(1, 1, 80, 2000)
        next_version = labor_settings(1, 1, 100, 3000)
        self.assertEqual(planned_labor(800, first)['estimated_piecework_amount'], 1600000)
        self.assertEqual(planned_labor(800, next_version)['estimated_piecework_amount'], 2400000)

    def test_legacy_default_keeps_daywork(self):
        self.assertEqual(labor_settings(0, 0, 40, 0)['mode'], 'Daywork')


if __name__ == '__main__':
    unittest.main()
