import unittest

from lotus_farm.finance import rules


class VatRules(unittest.TestCase):
    def test_rates_follow_effective_dates(self):
        codes = lambda day: [r['code'] for r in rules.vat_rates(day)]
        self.assertEqual(codes('2026-10-22'), ['KCT', '0', '5', '8', '10'])
        self.assertNotIn('8', codes('2027-01-01'), 'the 2% reduction ends on 31/12/2026')
        self.assertEqual(codes('2025-06-30'), [], 'Luật 48/2024 applies from 01/07/2025')
        self.assertEqual(rules.vat_rate('8', '2026-12-31'), 0.08)
        self.assertEqual(rules.vat_rate(None, '2026-10-01'), 0.0)
        with self.assertRaises(ValueError):
            rules.vat_rate('8', '2027-01-01')
        with self.assertRaises(ValueError):
            rules.vat_rate('7', '2026-10-01')
        self.assertTrue(all(r.get('source') for r in rules.load_vat()['rates']))

    def test_monthly_summary(self):
        purchases = [dict(code='10', net=1_000_000, tax=100_000), dict(code='KCT', net=500_000, tax=0), dict(code='10', net=200_000, tax=20_000)]
        sales = [dict(code='KCT', net=30_000_000, tax=0), dict(code='8', net=2_000_000, tax=160_000)]
        s = rules.vat_summary(purchases, sales)
        self.assertEqual((s['input_tax'], s['output_tax'], s['payable']), (120_000, 160_000, 40_000))
        self.assertEqual((s['exempt_sales'], s['taxable_sales']), (30_000_000, 2_000_000))
        self.assertEqual([r['code'] for r in s['purchases']], ['10', 'KCT'])
        self.assertEqual(s['purchases'][0]['count'], 2)
        self.assertEqual(rules.vat_summary([], [dict(code='KCT', net=1, tax=0)])['payable'], 0)


if __name__ == '__main__':
    unittest.main()
