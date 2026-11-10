import unittest
from datetime import date

from lotus_farm.finance import planning_rules as model


def plan(**extra):
    return dict(title='Kế hoạch 2027', start_month='2027-01', month_count=12, **extra)


def cohort(layer='cut', farm='F1', cycle=2, profile='P1', days=(('2027-01-15', 100),), **config):
    """A group of bunches of the shared forecast: when they are due, and the parameters that turn them into kg."""
    return dict(layer=layer, farm=farm, cycle=cycle, profile=profile, days=[(date.fromisoformat(day), bunches) for day, bunches in days],
                config=dict(dict(kg_cycle_1=19, kg_cycle_2=20, kg_cycle_3=19, pack_rate=.98), **config))


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

    def test_forecast_import_puts_each_bunch_in_its_month_and_keeps_only_the_plan_months(self):
        cohorts = [cohort(days=(('2026-12-30', 10), ('2027-01-15', 100), ('2027-02-01', 50))),
                   cohort(layer='tree', cycle=1, profile=None, days=(('2027-01-20', 10), ('2028-01-05', 7))),
                   cohort(farm='F2', days=(('2027-01-31', 1),))]
        today = date(2026, 12, 20)
        result = model.forecast_quantities('2027-01', 12, cohorts, today)
        self.assertEqual(len(result['rows']), 12)
        self.assertEqual((result['from_month'], result['kept']), ('2027-01', []), 'a plan ahead of today: every month is replaced')
        january, february, march = result['rows'][:3]
        self.assertEqual((january['gross_kg'], january['sales_kg']), (2210, 2165.8), '100 × 20 kg + 10 × 19 kg + 1 × 20 kg, 98% packed')
        self.assertEqual((february['gross_kg'], february['sales_kg']), (1000, 980))
        self.assertEqual((march['gross_kg'], march['sales_kg']), (0, 0), 'a month without bunches goes to 0')
        self.assertEqual([(s['month'], s['farm'], s['layer'], s['bunches'], s['sales_kg']) for s in result['sources']],
                         [('2027-01', 'F1', 'cut', 100, 1960), ('2027-01', 'F1', 'tree', 10, 186.2), ('2027-01', 'F2', 'cut', 1, 19.6),
                          ('2027-02', 'F1', 'cut', 50, 980)], 'bunches due before or after the plan are left out')
        self.assertEqual(len({s['name'] for s in result['sources']}), 4)
        self.assertEqual(len(result['warnings']), 1, 'kg worked out with default parameters are pointed out')
        self.assertEqual(result, model.forecast_quantities('2027-01', 12, cohorts, today))
        self.assertEqual(model.forecast_quantities('2027-01', 12, [cohort()], today)['warnings'], [])
        self.assertEqual(model.forecast_quantities('2030-01', 12, cohorts, today)['sources'], [])
        for wrong in (cohort(pack_rate=1.2), cohort(layer='guess'), cohort(layer='packed')):
            with self.assertRaises(ValueError):
                model.forecast_quantities('2027-01', 12, [wrong], today)

    def test_forecast_import_keeps_the_months_past_and_completes_this_one_with_its_closed_shifts(self):
        cohorts = [cohort(days=(('2027-03-20', 10), ('2027-04-02', 50)))]
        packed = [dict(farm='F1', bunches=40, gross_kg=900, sales_kg=760.5)]
        result = model.forecast_quantities('2027-01', 6, cohorts, date(2027, 3, 20), packed)
        self.assertEqual([r['month'] for r in result['rows']], ['2027-03', '2027-04', '2027-05', '2027-06'], 'January and February are not replaced')
        self.assertEqual((result['current'], result['from_month'], result['kept']), ('2027-03', '2027-03', ['2027-01', '2027-02']))
        march, april = result['rows'][:2]
        self.assertEqual((march['gross_kg'], march['sales_kg']), (1100, 956.5), '900 kg into the shifts + 10 bunches × 20 kg still due')
        self.assertEqual((april['gross_kg'], april['sales_kg']), (1000, 980))
        self.assertEqual([(s['month'], s['layer'], s['bunches'], s['gross_kg'], s['sales_kg']) for s in result['sources']],
                         [('2027-03', 'packed', 40, 900, 760.5), ('2027-03', 'cut', 10, 200, 196), ('2027-04', 'cut', 50, 1000, 980)])
        ahead = model.forecast_quantities('2027-01', 6, cohorts, date(2026, 12, 1), packed)
        self.assertEqual((len(ahead['rows']), ahead['kept']), (6, []))
        self.assertNotIn('packed', [s['layer'] for s in ahead['sources']], 'the shifts of a month outside the plan add nothing')
        over = model.forecast_quantities('2027-01', 2, cohorts, date(2027, 3, 20), packed)
        self.assertEqual((over['rows'], over['sources'], over['from_month'], over['kept']), ([], [], None, ['2027-01', '2027-02']),
                         'a plan already over has nothing to replace')
        with self.assertRaises(ValueError):
            model.forecast_quantities('2027-01', 6, cohorts, date(2027, 3, 20), [dict(farm='F1', bunches=1, gross_kg=10, sales_kg=11)])


if __name__ == '__main__':
    unittest.main()
