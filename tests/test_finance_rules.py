import datetime as dt
import unittest

from lotus_farm import bunch_flow_rules, payroll_rules
from lotus_farm.finance import rules
from lotus_farm.forecast_parameters import DEFAULTS, validate

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

    def test_cost_difference_of_fruit_still_in_stock_stays_in_wip(self):
        pools = [dict(lotus_farm='F', lotus_farm_block='A1', wip_open=6_000_000, cost_month=4_000_000, provisional=1_500_000, kg_harvested=1000, kg_remaining=4000),
                 dict(lotus_farm='F', lotus_farm_block='B', wip_open=0, cost_month=100_000, provisional=300_000, kg_harvested=10, kg_remaining=0)]
        sold = rules.costing_rows(pools)
        self.assertEqual([(r['adjustment'], r['unsold_adjustment'], r['wip_close']) for r in sold], [(500_000, 0, 8_000_000), (-200_000, 0, 0)],
                         'everything sold: the whole difference is cost of goods sold')
        a1, b = rules.costing_rows(pools, unsold_share=0.4)
        self.assertEqual((a1['absorbed'], a1['adjustment'], a1['unsold_adjustment'], a1['wip_close']), (2_000_000, 300_000, 200_000, 8_200_000),
                         '40% of the fruit still in stock: 40% of the difference stays in 154')
        self.assertEqual((b['adjustment'], b['unsold_adjustment'], b['wip_close']), (-120_000, -80_000, -80_000))
        for p, r in zip(pools, (a1, b)):
            self.assertEqual(r['wip_close'], p['wip_open'] + p['cost_month'] - p['provisional'] - r['adjustment'],
                             'the sheet closes on what 154 holds after the receipts and the adjustment')
        cogs = [ln for ln in rules.costing_entry([a1, b], ACCOUNTS) if ln['account'] == ACCOUNTS['cost_of_goods_sold']]
        self.assertEqual([(ln['debit'], ln['credit'], ln['lotus_farm_block']) for ln in cogs], [(300_000, 0, 'A1'), (0, 120_000, 'B')])
        self.assertEqual(rules.costing_entry(rules.costing_rows(pools, unsold_share=1), ACCOUNTS), [], 'nothing sold: nothing reaches 632')
        self.assertEqual(rules.costing_rows(pools, unsold_share=7)[0]['unsold_adjustment'], 500_000, 'a share is never above the whole')

    def test_remaining_kg_count_each_day_after_the_month_up_to_one_crop_pipeline(self):
        config = validate(DEFAULTS)
        self.assertEqual(rules.pipeline_end(dt.date(2026, 11, 30), config), dt.date(2027, 9, 22),
                         'a sucker selected on 30/11 flowers 6 months later, comes in 86 days after that, over 30 days')
        later = dict(config, sucker_to_flower_months=7)
        cohorts = [dict(block='A1', cycle=2, config=config, days=[(dt.date(2026, 11, 30), 10), (dt.date(2026, 12, 1), 100), (dt.date(2026, 12, 6), 3),
                                                                (dt.date(2027, 9, 22), 5), (dt.date(2027, 9, 23), 7)]),
                   dict(block='A2', cycle=1, config=dict(config, pack_rate=.5), days=[(dt.date(2026, 12, 10), 20)]),
                   dict(block='A3', cycle=3, config=later, days=[(dt.date(2027, 10, 23), 4), (dt.date(2027, 10, 24), 9)])]
        self.assertEqual(rules.remaining_kg(cohorts, '2026-11-30'), {'A1': round(108 * 20 * .98, 3), 'A2': 190.0, 'A3': round(4 * 19 * .98, 3)},
                         'the month end itself is out; 1–6/12 count although their week starts on 30/11; beyond one pipeline is out, '
                         'by the parameters of each group')
        self.assertEqual(rules.remaining_kg([], '2026-11-30'), {})

    def test_a_closed_month_counts_the_harvest_of_its_last_day_and_brings_the_rest_in_from_the_next_day(self):
        """As block_forecast.bunches_after reads it: the sổ lô lines dated up to the month end, whenever confirmed, and the
        bunches still due coming in from the next day."""
        config = validate(DEFAULTS)
        lines = [dict(name='C1', farm_block='A1', bunch_tag='RED', event_type=bunch_flow_rules.CUT, event_date='2026-09-25', qty=100, cycle_no=2),
                 dict(name='H1', farm_block='A1', bunch_tag='RED', event_type=bunch_flow_rules.HARVEST, event_date='2026-11-30', qty=40, cycle_no=2)]
        cohorts = bunch_flow_rules.cut_cohorts(lines, lambda block, day: (None, config), dt.date(2026, 12, 1))
        self.assertEqual(sum(c['bunches'] for c in cohorts), 57, '100 cut, 3 expected lost, 40 harvested on the last day')
        self.assertTrue(all(day > dt.date(2026, 11, 30) for c in cohorts for day, _ in c['days']))
        self.assertEqual(rules.remaining_kg(cohorts, '2026-11-30'), {'A1': round(57 * 20 * .98, 3)})

    def test_costing_is_refused_while_the_tree_count_forecast_stops_before_one_crop_pipeline(self):
        config = validate(DEFAULTS)
        # The farm's earliest estimated flowering date is in November 2026: the tree-count waves run to 31/10/2029.
        reach = dict(until=dt.date(2029, 10, 31), since=dt.date(2026, 11, 1), waves=[(dt.date(2027, 3, 30), config), (dt.date(2029, 10, 31), config)],
                     flowering={'B-1': dt.date(2026, 12, 1), 'A-2': dt.date(2026, 11, 20), 'A-1': dt.date(2026, 11, 1)})
        self.assertIsNone(rules.forecast_gap('2028-12-31', reach), 'December 2028 reads up to 23/10/2029, inside the window')
        self.assertEqual(rules.forecast_gap(dt.date(2029, 1, 31), reach),
                         dict(need=dt.date(2029, 11, 23), until=dt.date(2029, 10, 31), start=dt.date(2026, 12, 1), blocks=['A-1', 'A-2']),
                         'January 2029 reads up to 23/11/2029: the window must start in December 2026, the lô flowering in November hold it back')
        longer = dict(config, sucker_to_flower_months=8)
        self.assertIsNone(rules.forecast_gap('2028-12-31', dict(reach, waves=[(dt.date(2027, 3, 30), longer), (dt.date(2029, 10, 31), config)])),
                          'a parameter set only crops already in followed says nothing of the crops beyond the window')
        self.assertEqual(rules.forecast_gap('2029-01-31', dict(reach, waves=[(dt.date(2029, 6, 30), config), (dt.date(2029, 10, 31), longer)])),
                         dict(need=dt.date(2030, 1, 23), until=dt.date(2029, 10, 31), start=dt.date(2027, 2, 1), blocks=['A-1', 'A-2', 'B-1']),
                         'the longest pipeline of the crops still to come in')
        self.assertEqual(rules.forecast_gap('2029-12-31', dict(reach, waves=[(dt.date(2029, 10, 31), config)]))['need'], dt.date(2030, 10, 23),
                         'a window over before the month: by every wave')
        self.assertIsNone(rules.forecast_gap('2031-06-30', dict(reach, waves=[])), 'no tree-count forecast: nothing to stop short')

    def test_forecast_kg_go_on_the_basis_of_the_kg_received(self):
        self.assertEqual(rules.kg_mix((2000, 1600), (5000, 4500)), 1.25, 'the pool\'s own month: finished + secondary per finished kg')
        self.assertEqual(rules.kg_mix((300, 0), (5000, 4000)), 1.25, 'secondary fruit only: the farm\'s month')
        self.assertEqual(rules.kg_mix((300, 0), (300, 0)), 1.0, 'no finished fruit anywhere: the forecast as it is')
        self.assertEqual(rules.kg_mix((0, 0), (0, 0)), 1.0)
        # 1 600 kg finished + 400 kg secondary received; the forecast still expects 8 000 kg finished, about 10 000 kg received.
        pool = dict(lotus_farm='F', lotus_farm_block='A', wip_open=80_000_000, cost_month=40_000_000, provisional=0, kg_harvested=2000,
                    kg_remaining=8000 * 1.25, kg_mix=1.25)
        row = rules.costing_rows([pool])[0]
        self.assertEqual((row['absorbed'], row['cost_per_kg'], row['wip_close']), (20_000_000, 10_000, 100_000_000),
                         '2 000 of 12 000 kg on one basis, not 2 000 of 10 000')
        self.assertIn('× 1,25', row['basis'])
        self.assertNotIn('×', rules.costing_rows([dict(pool, kg_mix=1.0)])[0]['basis'], 'no secondary fruit: nothing to say')

    def test_vu_of_the_fruit_is_the_one_with_most_bunches_harvested(self):
        lines = [dict(farm_block='A', cycle_no=2, qty=30), dict(farm_block='A', cycle_no=3, qty=20), dict(farm_block='A', cycle_no=3, qty=15),
                 dict(farm_block='B', cycle_no=1, qty=10), dict(farm_block='B', cycle_no=2, qty=10), dict(farm_block='C', cycle_no=None, qty=50)]
        self.assertEqual(rules.harvest_cycles(lines), {'A': 3, 'B': 2}, 'most bunches, the later vụ on a tie; a line without vụ says nothing')
        self.assertEqual(rules.harvest_cycles([]), {})

    def test_ledger_lines_carry_farm_lot_and_work_type(self):
        self.assertEqual(rules.DIM_FIELDS, ('lotus_farm', 'lotus_farm_block', 'lotus_work_type'))
        self.assertEqual(sorted(rules.line('A', debit=1, dims=dict(lotus_farm='F', lotus_farm_block='A1'))),
                         ['account', 'credit', 'debit', 'lotus_farm', 'lotus_farm_block', 'lotus_work_type', 'note'])

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
