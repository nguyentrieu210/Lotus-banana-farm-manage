import unittest

from lotus_farm.finance import planning_rules as model


def plan(**extra):
    return dict(title='Kế hoạch 2027', start_month='2027-01', month_count=12, **extra)


def source(name='HF1', **extra):
    return dict(name=name, period_start_date='2027-01-15', period_end_date='2027-01-21',
                gross_forecast_kg=1000, packed_forecast_kg=800, supply_state='Released', **extra)


class FinancialPlanning(unittest.TestCase):
    def test_all_months_filled_and_decimal_money_rounded_half_up(self):
        values = plan(rows=[dict(month='2027-01', gross_kg=3, sales_kg=3, price_per_kg=100.5)])
        result = model.calculate(values)
        self.assertEqual(len(result['rows']), 12)
        self.assertEqual(result['rows'][0]['revenue'], 302)
        self.assertEqual(result['totals']['closing_cash'], 302)

    def test_capex_depreciation_and_financing_have_different_cash_profit_effects(self):
        values = plan(opening_cash=100, rows=[dict(month='2027-01', gross_kg=1000, sales_kg=800,
            price_per_kg=10, materials=1000, labour=2000, services=500, packing_per_kg=1,
            transport_per_kg=0.5, overhead=300, depreciation=700, interest=100, tax=200,
            capex=5000, funding=3000, debt_payment=200, other_receipts=400, other_payments=50)])
        result = model.calculate(values)
        jan = result['rows'][0]
        self.assertEqual(jan['operating_cost'], 5000)
        self.assertEqual(jan['profit_before_tax'], 2200)
        self.assertEqual(jan['profit'], 2000)
        self.assertEqual(jan['cash_in'], 11400)
        self.assertEqual(jan['cash_out'], 10550)
        self.assertEqual(jan['closing_cash'], 950)

    def test_cash_delays_cross_year_and_show_unsettled_amounts_after_horizon(self):
        values = dict(title='Cuối năm', start_month='2026-12', month_count=2,
            collection_delay=2, payment_delay=1, rows=[
                dict(month='2026-12', gross_kg=1, sales_kg=1, price_per_kg=1000, materials=200),
                dict(month='2027-01', gross_kg=2, sales_kg=2, price_per_kg=1000, materials=300)])
        result = model.calculate(values)
        self.assertEqual([r['cash_in'] for r in result['rows']], [0, 0])
        self.assertEqual([r['cash_out'] for r in result['rows']], [0, 200])
        self.assertEqual(result['totals']['receivables_after_horizon'], 3000)
        self.assertEqual(result['totals']['payables_after_horizon'], 300)
        self.assertEqual(result['totals']['funding_gap'], 200)
        self.assertEqual(result['totals']['profit'], 2500)

    def test_payment_and_receipt_due_inside_horizon_are_counted_once(self):
        values = plan(collection_delay=1, payment_delay=1,
            rows=[dict(month='2027-01', gross_kg=1, sales_kg=1, price_per_kg=1000, materials=300)])
        rows = model.calculate(values)['rows']
        self.assertEqual(rows[0]['cash_in'], 0)
        self.assertEqual(rows[1]['cash_in'], 1000)
        self.assertEqual(rows[1]['cash_out'], 300)
        self.assertEqual(rows[2]['cash_in'], 0)

    def test_scenario_changes_only_quantity_price_and_unit_variable_cost(self):
        values = plan(quantity_percent=50, price_percent=200, variable_cost_percent=200,
            rows=[dict(month='2027-01', gross_kg=10, sales_kg=8, price_per_kg=10, materials=7, packing_per_kg=2)])
        base = model.calculate(values, base=True)['rows'][0]
        scenario = model.calculate(values)['rows'][0]
        self.assertEqual((base['revenue'], scenario['revenue']), (80, 80))
        self.assertEqual((base['operating_cost'], scenario['operating_cost']), (23, 23))
        self.assertEqual((base['sales_kg'], scenario['sales_kg']), (8, 4))

    def test_zero_quantity_still_has_fixed_budget_and_negative_opening_cash(self):
        result = model.calculate(plan(opening_cash=-500, rows=[dict(month='2027-01', labour=300)]))
        self.assertEqual(result['totals']['profit'], -300)
        self.assertEqual(result['totals']['funding_gap'], 800)

    def test_missing_price_is_visible_before_approval(self):
        result = model.calculate(plan(rows=[dict(month='2027-02', gross_kg=10, sales_kg=8)]))
        self.assertEqual(len(result['warnings']), 1)
        self.assertIn('2027-02', result['warnings'][0])

    def test_invalid_inputs_cannot_silently_produce_a_budget(self):
        invalid = [plan(rows=[dict(month='2027-01', gross_kg=1, sales_kg=2)]),
                   plan(rows=[dict(month='2027-01', labour=-1)]),
                   plan(rows=[dict(month='2027-01', materials='NaN')]),
                   plan(rows=[dict(month='2027-01', labour=float('inf'))]),
                   plan(rows=[dict(month='2028-01')]),
                   plan(rows=[dict(month='2027-01'), dict(month='2027-01')]),
                   plan(collection_delay=1.5), plan(payment_delay=13), plan(quantity_percent=301)]
        for values in invalid:
            with self.subTest(values=values), self.assertRaises(ValueError):
                model.calculate(values)
        with self.assertRaises(ValueError):
            model.calculate(dict(title='X', start_month='2027-13', month_count=12))
        with self.assertRaises(ValueError):
            model.calculate(plan(rows=[dict(month='2027-01', gross_kg=10**15, sales_kg=10**15, price_per_kg=10**15)]))

    def test_forecast_import_counts_released_sources_once_and_warns_cross_month(self):
        docs = [source(), dict(source('draft'), supply_state='Draft'),
                dict(source('replaced'), supply_state='Superseded'),
                dict(source('cross'), period_start_date='2027-01-30', period_end_date='2027-02-05'),
                dict(source('partial'), period_start_date='2026-12-30', period_end_date='2027-01-05')]
        result = model.forecast_quantities('2027-01', 12, docs)
        self.assertEqual(len(result['sources']), 2)
        self.assertEqual(result['rows'][0]['gross_kg'], 2000)
        self.assertEqual(result['rows'][0]['sales_kg'], 1600)
        self.assertEqual(result['rows'][1]['gross_kg'], 0)
        self.assertEqual(len(result['warnings']), 2)
        self.assertEqual(result, model.forecast_quantities('2027-01', 12, docs))
        with self.assertRaises(ValueError):
            model.forecast_quantities('2027-01', 12, [source(), source()])


if __name__ == '__main__':
    unittest.main()
