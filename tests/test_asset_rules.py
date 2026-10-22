import unittest
from lotus_farm.finance import asset_rules as r


class AssetRulesTest(unittest.TestCase):
    def rows(self, weights):
        return [dict(percent=w, expense_account='expense', cost_center='center', lotus_farm='farm'+str(i))
                for i, w in enumerate(weights)]

    def test_whole_dong_largest_remainder_and_stable_ties(self):
        result = r.split_amount(1001, self.rows(['33.333333', '33.333333', '33.333334']))
        self.assertEqual([v['amount'] for v in result], [334, 333, 334])
        self.assertEqual(sum(v['amount'] for v in result), 1001)
        self.assertEqual([v['amount'] for v in r.split_amount(1, self.rows([50, 50]))], [1, 0])

    def test_invalid_percentages_and_duplicates(self):
        for weights in ([50, 49], [0, 100], [-1, 101], ['nan', 100], ['Infinity'], ['bad']):
            with self.subTest(weights=weights), self.assertRaises(ValueError):
                r.split_amount(100, self.rows(weights))
        with self.assertRaises(ValueError):
            r.allocation_rows([dict(percent=50, expense_account='x', cost_center='c')]*2)

    def test_native_fractional_depreciation_is_never_rounded_away(self):
        for source in ['526027.92', '4931506.85', '0.01', '0.1234']:
            parts=r.split_amount(source,self.rows(['33.333333','33.333333','33.333334']))
            self.assertEqual(sum(r.decimal(row['amount']) for row in parts),r.decimal(source))

    def test_fractional_depreciation_survives_closing_costing_and_result_closing(self):
        from lotus_farm.finance import rules
        lines=rules.closing_entry([dict(account='6274',net=526027.92,lotus_farm='F')],'154')
        self.assertEqual(lines[0]['debit'],526027.92)
        self.assertFalse(rules.check_entry(lines))
        cost=rules.costing_rows([dict(wip_open=0,cost_month=526027.92,provisional=100000,kg_harvested=1,kg_remaining=0)])[0]
        self.assertEqual(cost['absorbed'],526027.92)
        self.assertEqual(cost['wip_close'],0)
        cogs=rules.costing_entry([cost],dict(production_cost='154',cost_of_goods_sold='632'))
        self.assertEqual(cogs[0]['debit'],426027.92)
        result,profit=rules.result_entry([dict(account='711',net=-600000),dict(account='811',net=526027.92)],'911','4212')
        self.assertEqual(profit,73972.08)
        self.assertFalse(rules.check_entry(result))

    def test_money_and_date_boundaries(self):
        self.assertEqual(r.money('100.5'), 101)
        self.assertEqual(r.bounds('2028-02'), ('2028-02-01', '2028-02-29'))
        for val in ['2026-13', '2026', '2026-9', 'bad']:
            with self.assertRaises(ValueError):
                r.bounds(val)

    def test_profile_does_not_invent_required_data(self):
        v, errors = r.profile({})
        self.assertIn('code', errors)
        self.assertIn('purchase_date', errors)
        self.assertIn('supplier', errors)
        self.assertIn('amount', errors)

    def test_opening_cannot_exceed_depreciable_value(self):
        values = dict(code='TS1', asset_name='Máy bơm', asset_category='Máy', location='Farm', existing=True,
                      purchase_date='2025-01-01', available_for_use_date='2025-01-01', amount=120_000_000,
                      opening_depreciation=20_000_000, months=24, booked_months=4, salvage_value=0)
        self.assertFalse(r.profile(values)[1])
        self.assertEqual(r.profile(dict(values, purchase_date='02/09/2024'))[0]['purchase_date'], '2024-09-02')
        self.assertIn('opening_depreciation', r.profile(dict(values, opening_depreciation=121_000_000))[1])
        self.assertIn('months', r.profile(dict(values, months=24.5))[1])

    def test_fingerprint_detects_allocation_or_version_changes(self):
        self.assertEqual(r.fingerprint({'b':2,'a':1}), r.fingerprint({'a':1,'b':2}))
        self.assertNotEqual(r.fingerprint({'modified':'a'}), r.fingerprint({'modified':'b'}))


if __name__ == '__main__':
    unittest.main()
