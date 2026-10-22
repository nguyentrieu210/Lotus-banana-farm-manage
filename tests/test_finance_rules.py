import datetime as dt
import unittest

from lotus_farm import payroll_rules
from lotus_farm.finance import rules

ACCOUNTS = {k: 'ACC-' + k for k in rules.KEYS}


def employee(code, base, gross, insured=True):
    ee = sum(round(base * r) for r in payroll_rules.EMPLOYEE_INSURANCE.values()) if insured else 0
    er = sum(round(base * r) for r in payroll_rules.EMPLOYER_INSURANCE.values()) if insured else 0
    return dict(employee=code, base=base, gross=gross, employee_insurance=ee, employer_insurance=er, net=gross - ee)


class FinanceRules(unittest.TestCase):
    def test_tt99_chart_is_consistent(self):
        coa = rules.load_coa()
        self.assertEqual(rules.validate_coa(coa), [])
        numbers = {a['number']: a for a in coa['accounts']}
        for n in ('111', '112', '152', '154', '155', '331', '334', '3383', '3384', '3386', '3388', '4111', '621', '622', '6277', '6421', '6427', '2153'):
            self.assertIn(n, numbers)
        self.assertEqual(numbers['3386']['name'], 'Bảo hiểm thất nghiệp', 'TT99: 3386 is unemployment insurance')
        self.assertNotIn('3385', numbers)
        self.assertNotIn('1111', numbers, 'TT99: 111 and 112 have no level-2 accounts')
        self.assertEqual(numbers['112']['name'], 'Tiền gửi không kỳ hạn')
        self.assertEqual(numbers['155']['name'], 'Sản phẩm')
        self.assertEqual(numbers['215']['name'], 'Tài sản sinh học')
        self.assertEqual(numbers['6277']['parent'], '627')
        self.assertEqual(sum(1 for a in coa['accounts'] if len(a['number']) == 3), 71, 'TT99 has 71 level-1 accounts, 911 included')
        self.assertEqual(numbers['911']['root_type'], 'Equity')
        for key, number in coa['defaults'].items():
            self.assertIn(key, rules.KEYS, 'default for an unknown key ' + key)
        self.assertEqual(numbers['331']['account_type'], 'Payable')
        self.assertEqual(numbers['3388']['account_type'], 'Stock Received But Not Billed')
        plan = rules.coa_plan(coa, {'111'})
        self.assertNotIn('111', [a['number'] for a in plan])
        self.assertEqual(next(a for a in plan if a['number'] == '338')['is_group'], 1)
        self.assertEqual(next(a for a in plan if a['number'] == '3388')['is_group'], 0)

    def test_chart_validation_catches_mistakes(self):
        coa = dict(accounts=[dict(number='1', name='Loại 1', parent=None, root_type='Asset', account_type=''),
                             dict(number='111', name='Tiền', parent='1', root_type='Asset', account_type=''),
                             dict(number='111', name='Trùng', parent='1', root_type='Asset', account_type=''),
                             dict(number='331', name='Sai loại', parent='1', root_type='Liability', account_type=''),
                             dict(number='3388', name='Thiếu cha', parent='338', root_type='Liability', account_type='')],
                   defaults={'cash': '1', 'bank': '999'})
        errors = rules.validate_coa(coa)
        self.assertTrue(any('trùng' in e for e in errors))
        self.assertTrue(any('khác loại gốc' in e for e in errors))
        self.assertTrue(any('chưa khai báo' in e for e in errors))
        self.assertTrue(any('999' in e for e in errors))
        self.assertTrue(any('tổng hợp' in e for e in errors), 'a default pointing at a group account is refused')

    def test_mapping_messages_are_about_the_business(self):
        accounts = {'A-152': dict(root_type='Asset', account_type='Stock', is_group=0, company_ok=True),
                    'A-331': dict(root_type='Liability', account_type='', is_group=0, company_ok=True),
                    'A-111': dict(root_type='Asset', account_type='Cash', is_group=1, company_ok=True)}
        errors = rules.validate_mapping({'inventory_material': 'A-152', 'payable_supplier': 'A-331', 'cash': 'A-111'}, accounts)
        self.assertTrue(any('Phải trả người bán' in e and 'Payable' in e for e in errors))
        self.assertTrue(any('Tiền mặt' in e and 'tổng hợp' in e for e in errors))
        self.assertTrue(any('Chưa chọn tài khoản cho "Hàng về chưa có hóa đơn"' in e for e in errors))
        self.assertFalse(any('Kho nguyên liệu' in e for e in errors))

    def test_split_amount_is_exact(self):
        self.assertEqual(rules.split_amount(100, [1, 1, 1]), [34, 33, 33])
        self.assertEqual(sum(rules.split_amount(7_654_321, [2.5, 1, 0.5, 3])), 7_654_321)
        self.assertEqual(rules.split_amount(10, [0, 0]), [5, 5])
        self.assertEqual(rules.split_amount(5, []), [])

    def test_check_entry(self):
        good = [rules.line('A', debit=100), rules.line('B', credit=100)]
        self.assertEqual(rules.check_entry(good), [])
        bad = [rules.line('A', debit=100), rules.line('B', credit=90), dict(rules.line('C'), debit=5, credit=5)]
        errors = rules.check_entry(bad)
        self.assertTrue(any('Tổng Nợ' in e for e in errors))
        self.assertTrue(any('một bên' in e for e in errors))

    def test_payroll_entry_splits_cost_by_lot_work_and_balances(self):
        a, b, c = employee('E1', 6_000_000, 7_000_000), employee('E2', 5_000_000, 5_500_000), employee('E3', 0, 3_000_000, insured=False)
        snapshot = dict(employees=[a, b, c], crews=[dict(work_team='T1', work_type='Cắt bắp', amount=2_000_000)])
        shares = rules.shares_from_work([
            dict(employee='E1', workdays=10, lotus_farm='F', lotus_farm_block='A1', lotus_work_type='Phun'),
            dict(employee='E1', workdays=12, lotus_farm='F', lotus_farm_block='A2', lotus_work_type='Phun'),
            dict(employee='E1', workdays=2, lotus_farm='F', lotus_farm_block='A1', lotus_work_type='Phun'),
            dict(employee='E2', workdays=20, lotus_farm='F', lotus_farm_block='B1', lotus_work_type='Bao buồng')])
        lines, issues = rules.payroll_entry(snapshot, shares, ACCOUNTS, payroll_rules.EMPLOYEE_INSURANCE, payroll_rules.EMPLOYER_INSURANCE,
                                            crew_farms={'T1': 'F'}, employee_farms={'E3': 'F'})
        self.assertEqual(issues, [])
        self.assertEqual(rules.check_entry(lines), [])
        debit = sum(ln['debit'] for ln in lines)
        cost = sum(r['gross'] + r['employer_insurance'] for r in (a, b, c)) + 2_000_000
        self.assertEqual(debit, cost)
        e1 = a['gross'] + a['employer_insurance']
        a1 = next(ln for ln in lines if ln['lotus_farm_block'] == 'A1' and ln['note'] == 'Lương')
        a2 = next(ln for ln in lines if ln['lotus_farm_block'] == 'A2')
        self.assertEqual(a1['debit'] + a2['debit'], e1)
        self.assertEqual(a1['debit'], round(e1 * 12 / 24), 'E1 worked 12 of 24 days on A1')
        indirect = next(ln for ln in lines if ln['account'] == ACCOUNTS['admin_labour'])
        self.assertEqual((indirect['debit'], indirect['lotus_farm']), (3_000_000, 'F'), 'no lot work -> management staff cost (6421) of the farm')
        self.assertTrue(all(ln['account'] == ACCOUNTS['labour_cost'] for ln in lines if ln.get('lotus_farm_block')), 'lot work -> direct labour 622')
        crew = next(ln for ln in lines if ln['note'] == 'Khoán T1' and ln['debit'])
        self.assertEqual((crew['lotus_farm'], crew['lotus_work_type'], crew['debit']), ('F', 'Cắt bắp', 2_000_000))
        bhxh = next(ln for ln in lines if ln['account'] == ACCOUNTS['social_insurance'])
        self.assertEqual(bhxh['credit'], round(6_000_000 * 0.08) + round(6_000_000 * 0.175) + round(5_000_000 * 0.08) + round(5_000_000 * 0.175))
        net = next(ln for ln in lines if ln['account'] == ACCOUNTS['payable_employee'])
        self.assertEqual(net['credit'], a['net'] + b['net'] + c['net'])

    def test_payroll_entry_reports_gaps(self):
        row = employee('E1', 6_000_000, 7_000_000)
        row['net'] += 1
        snapshot = dict(employees=[row], crews=[dict(work_team='T9', work_type='X', amount=100)])
        _, issues = rules.payroll_entry(snapshot, {}, ACCOUNTS, payroll_rules.EMPLOYEE_INSURANCE, payroll_rules.EMPLOYER_INSURANCE)
        self.assertTrue(any('thực nhận' in i for i in issues))
        self.assertTrue(any('Đội T9 chưa gắn vườn' in i for i in issues))

    def test_standard_chart_has_vietnamese_names(self):
        import json
        names = json.loads((rules.COA_FILE.parent / 'erpnext_standard_accounts_vi.json').read_text(encoding='utf-8'))
        for english in ('Stock In Hand', 'Stock Adjustment', 'Temporary Opening', 'Creditors', 'Cash', 'Round Off', 'Stock Received But Not Billed'):
            self.assertIn(english, names['accounts'])
        for english in ('Application of Funds (Assets)', 'Source of Funds (Liabilities)', 'Equity', 'Income', 'Expenses'):
            self.assertIn(english, names['groups'])
        self.assertFalse(set(names['groups']) & set(names['accounts']), 'a name is either a group or a leaf')

    def test_closing_moves_each_lot_to_wip(self):
        rows = [dict(account='621', net=300000, lotus_farm='F', lotus_farm_block='A1'), dict(account='622', net=1000000, lotus_farm='F', lotus_farm_block='A1'),
                dict(account='6277', net=-50000, lotus_farm='F', lotus_farm_block='A2'), dict(account='622', net=0, lotus_farm='F')]
        lines = rules.closing_entry(rows, '154')
        self.assertEqual(rules.check_entry(lines), [])
        wip = [ln for ln in lines if ln['account'] == '154']
        self.assertEqual([(ln['debit'], ln['credit'], ln['lotus_farm_block']) for ln in wip], [(300000, 0, 'A1'), (1000000, 0, 'A1'), (0, 50000, 'A2')])
        self.assertEqual(len(lines), 6, 'a zero balance is skipped')

    def test_snapshot_people_reads_the_frozen_sheet(self):
        self.assertEqual(rules.snapshot_people(dict(employees=[1, 2])), [1, 2], 'hr_period._sheet stores employees')
        self.assertEqual(rules.snapshot_people(dict(rows=[3])), [3])
        self.assertEqual(rules.snapshot_people({}), [])

    def test_costing_spreads_lot_costs_over_expected_harvest(self):
        rows = rules.costing_rows([
            dict(lotus_farm='F', lotus_farm_block='A1', wip_open=6_000_000, cost_month=4_000_000, provisional=1_500_000, kg_harvested=1000, kg_remaining=4000),
            dict(lotus_farm='F', lotus_farm_block='A2', wip_open=3_000_000, cost_month=0, provisional=0, kg_harvested=0, kg_remaining=0),
            dict(lotus_farm='F', lotus_farm_block='A3', wip_open=0, cost_month=900_000, provisional=200_000, kg_harvested=300, kg_remaining=0)])
        a1, a2, a3 = rows
        self.assertEqual((a1['absorbed'], a1['wip_close'], a1['cost_per_kg'], a1['adjustment']), (2_000_000, 8_000_000, 2000.0, 500_000),
                         '1000 of 5000 kg: one fifth of 10 M, the rest stays in 154')
        self.assertEqual((a2['absorbed'], a2['wip_close'], a2['adjustment']), (0, 3_000_000, 0), 'a lot without harvest keeps its cost in progress')
        self.assertEqual((a3['absorbed'], a3['wip_close']), (900_000, 0), 'no forecast left: the harvest carries everything')
        self.assertIn('không có dự thu', a3['basis'])
        lines = rules.costing_entry(rows, ACCOUNTS)
        self.assertEqual(rules.check_entry(lines), [])
        cogs = [ln for ln in lines if ln['account'] == ACCOUNTS['cost_of_goods_sold']]
        self.assertEqual([(ln['debit'], ln['lotus_farm_block']) for ln in cogs], [(500_000, 'A1'), (700_000, 'A3')])
        below = rules.costing_entry(rules.costing_rows([dict(lotus_farm='F', lotus_farm_block='B', wip_open=0, cost_month=100, provisional=300,
                                                              kg_harvested=10, kg_remaining=0)]), ACCOUNTS)
        self.assertEqual([(ln['account'], ln['debit']) for ln in below if ln['debit']], [(ACCOUNTS['production_cost'], 200)],
                         'a provisional rate above the actual cost comes back to 154')

    def test_provisional_rate(self):
        self.assertEqual(rules.provisional_rate(2100, 1800), 2100)
        self.assertEqual(rules.provisional_rate(None, 1800), 1800)
        self.assertIsNone(rules.provisional_rate(0, None))

    def test_aging(self):
        today = dt.date(2026, 10, 22)
        self.assertEqual(rules.aging(dt.date(2026, 10, 30), today), 'Trong hạn')
        self.assertEqual(rules.aging(dt.date(2026, 10, 1), today), 'Quá hạn 1–30 ngày')
        self.assertEqual(rules.aging(dt.date(2026, 6, 1), today), 'Quá hạn trên 90 ngày')


if __name__ == '__main__':
    unittest.main()
