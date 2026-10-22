import unittest

from lotus_farm import payroll_rules as pr
from lotus_farm.finance import rules

ACCOUNTS = {k: 'ACC-' + k for k in rules.KEYS}


class PayrollTax(unittest.TestCase):
    def setUp(self):
        self.data = pr.load_params()

    def test_parameters_follow_effective_dates(self):
        old, new = pr.params_on('2025-12-31', self.data), pr.params_on('2026-01-31', self.data)
        self.assertEqual((old['pit']['self'], old['pit']['dependent'], len(old['pit']['brackets'])), (11_000_000, 4_400_000, 7))
        self.assertEqual((new['pit']['self'], new['pit']['dependent'], len(new['pit']['brackets'])), (15_500_000, 6_200_000, 5))
        self.assertEqual(new['insurance']['base_salary'], 2_340_000)
        self.assertEqual(pr.params_on('2026-07-31', self.data)['insurance']['base_salary'], 2_530_000)
        # the 5 million threshold is not confirmed yet: the 2 million rule keeps applying
        self.assertEqual(pr.params_on('2026-10-31', self.data)['flat']['threshold'], 2_000_000)
        every = [r for group in ('pit_progressive', 'pit_flat', 'insurance') for r in self.data[group]]
        self.assertTrue(all(r.get('source') for r in every), 'every parameter names its legal source')

    def test_progressive_brackets(self):
        new = pr.params_on('2026-03-31', self.data)['pit']['brackets']
        old = pr.params_on('2025-03-31', self.data)['pit']['brackets']
        self.assertEqual(pr.progressive_tax(40_000_000, new), 500_000 + 2_000_000 + 2_000_000)
        self.assertEqual(pr.progressive_tax(150_000_000, new), 500_000 + 2_000_000 + 6_000_000 + 12_000_000 + 17_500_000)
        self.assertEqual(pr.progressive_tax(20_000_000, old), 250_000 + 500_000 + 1_200_000 + 400_000)
        self.assertEqual(pr.progressive_tax(0, new), 0)
        self.assertEqual(pr.progressive_tax(-5, new), 0)

    def test_insurance_bases_are_capped_and_union_fee_is_two_percent(self):
        ins = pr.params_on('2026-03-31', self.data)['insurance']
        c = pr.contributions(60_000_000, ins, 'I')
        self.assertEqual(c['employee'], dict(bhxh=3_744_000, bhyt=702_000, bhtn=600_000))
        self.assertEqual(c['employer']['bhxh'], round(46_800_000 * 0.175))
        self.assertEqual(c['union_fee'], 936_000)
        self.assertTrue(c['capped'])
        small = pr.contributions(6_000_000, ins, 'I')
        self.assertEqual(sum(small['employee'].values()), 630_000)
        self.assertFalse(small['capped'])

    def test_income_tax_by_contract(self):
        params = pr.params_on('2026-03-31', self.data)
        t = pr.income_tax(30_000_000, 0, 3_150_000, 'progressive', params, dependents=1)
        self.assertEqual((t['taxable_income'], t['pit']), (5_150_000, 257_500))
        self.assertEqual(pr.income_tax(15_000_000, 0, 1_575_000, 'progressive', params)['pit'], 0)
        self.assertEqual(pr.income_tax(3_000_000, 0, 0, 'flat', params)['pit'], 300_000)
        self.assertEqual(pr.income_tax(3_000_000, 0, 0, 'flat', params, commitment=True)['pit_method'], 'commitment')
        self.assertEqual(pr.income_tax(1_500_000, 0, 0, 'flat', params)['pit'], 0)
        self.assertEqual(pr.tax_method('Permanent'), 'progressive')
        self.assertEqual(pr.tax_method('Fixed-term', months_of_contract=2), 'flat')
        self.assertEqual(pr.tax_method('Seasonal'), 'flat')
        self.assertEqual(pr.tax_method('Probation', months_of_contract=12), 'flat')

    def test_hourly_pay_withholds_tax_but_not_on_overtime_premium(self):
        params = pr.params_on('2026-03-31', self.data)
        summary = dict(pr.empty_summary(), regular_hours=208, ot_regular=10)
        pay = pr.hourly_pay('Monthly', summary, base_salary=20_800_000, insured=True, params=params, region='I',
                            tax=dict(method='progressive', dependents=0))
        self.assertEqual(pay['gross'], 22_300_000)
        self.assertEqual(pay['pit_exempt'], 500_000)
        self.assertEqual(pay['employee_insurance'], 2_184_000)
        self.assertEqual(pay['taxable_income'], 4_116_000)
        self.assertEqual(pay['pit'], 205_800)
        self.assertEqual(pay['net'], 22_300_000 - 2_184_000 - 205_800)
        self.assertEqual(pay['union_fee'], 416_000)
        self.assertEqual(sum(pay['insurance_parts']['employer'].values()), pay['employer_insurance'])
        # without parameters the sheet keeps the old arithmetic (no tax)
        self.assertEqual(pr.hourly_pay('Monthly', summary, base_salary=20_800_000, insured=True)['net'], 22_300_000 - 2_184_000)

    def test_payroll_entry_posts_tax_and_union_fee(self):
        params = pr.params_on('2026-03-31', self.data)
        summary = dict(pr.empty_summary(), regular_hours=208, ot_regular=10)
        pay = pr.hourly_pay('Monthly', summary, base_salary=20_800_000, insured=True, params=params, region='I', tax=dict(method='progressive'))
        row = dict(pay, employee='E1')
        shares = rules.shares_from_work([dict(employee='E1', workdays=26, lotus_farm='F', lotus_farm_block='A1')])
        lines, issues = rules.payroll_entry(dict(employees=[row]), shares, ACCOUNTS, pr.EMPLOYEE_INSURANCE, pr.EMPLOYER_INSURANCE)
        self.assertEqual(issues, [])
        side = lambda key, f: sum(ln[f] for ln in lines if ln['account'] == ACCOUNTS[key])
        self.assertEqual(side('pit_payable', 'credit'), 205_800)
        self.assertEqual(side('union_fee', 'credit'), 416_000)
        self.assertEqual(side('labour_cost', 'debit'), pay['gross'] + pay['employer_insurance'] + pay['union_fee'])
        self.assertEqual(side('social_insurance', 'credit'), pay['insurance_parts']['employee']['bhxh'] + pay['insurance_parts']['employer']['bhxh'])
        self.assertEqual(side('payable_employee', 'credit'), pay['net'])


if __name__ == '__main__':
    unittest.main()
