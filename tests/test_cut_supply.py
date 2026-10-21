import unittest
from lotus_farm.cut_supply import window_balance, interval_quantity, overlaps


class CutSupplyTests(unittest.TestCase):
    def test_consumption_is_stable_across_months_and_publications(self):
        events = [dict(key='harvest:H1', date='2026-11-02', quantity=8),
                  dict(key='cancel:C1', date='2026-10-31', quantity=2)]
        balance = window_balance('2026-10-28', '2026-11-06', 20, events)
        self.assertAlmostEqual(balance['remaining'], 10)
        self.assertAlmostEqual(interval_quantity(balance, '2026-10-01', '2026-10-31'), 6)
        self.assertAlmostEqual(interval_quantity(balance, '2026-11-01', '2026-11-30'), 4)
        self.assertAlmostEqual(interval_quantity(balance, '2026-11-01', '2026-11-30', 'harvest:H1'), 8)
        self.assertEqual(balance, window_balance('2026-10-28', '2026-11-06', 20, reversed(events)))

    def test_overflow_uses_oldest_remaining_capacity(self):
        balance = window_balance('2026-10-31', '2026-11-02', 3,
                                 [dict(key='H', date='2026-11-02', quantity=3)])
        self.assertAlmostEqual(sum(balance['days'].values()), 0)
        self.assertAlmostEqual(interval_quantity(balance, '2026-10-31', '2026-10-31', 'H'), 1)

    def test_overconsumption_and_invalid_values_rejected(self):
        for qty in (-1, float('nan')):
            with self.assertRaises(ValueError): window_balance('2026-01-01', '2026-01-02', qty)
        with self.assertRaises(ValueError):
            window_balance('2026-01-01', '2026-01-02', 1, [dict(key='H', date='2026-01-01', quantity=2)])

    def test_inclusive_boundaries_and_reversal(self):
        self.assertTrue(overlaps('2026-01-01', '2026-01-05', '2026-01-05', '2026-01-09'))
        self.assertFalse(overlaps('2026-01-01', '2026-01-05', '2026-01-06', '2026-01-09'))
        self.assertEqual(window_balance('2026-01-01', '2026-01-01', 3)['remaining'], 3)
