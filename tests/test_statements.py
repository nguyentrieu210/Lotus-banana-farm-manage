import unittest

from lotus_farm.finance import rules


def leaves():
    coa = rules.load_coa()
    groups = {a['parent'] for a in coa['accounts'] if a.get('parent')}
    return [a['number'] for a in coa['accounts'] if a['number'] not in groups]


def part(number, net, debit=None, credit=None, party=''):
    return dict(number=number, name=number, party=party, net=net, debit=max(net, 0) if debit is None else debit, credit=max(-net, 0) if credit is None else credit)


class Statements(unittest.TestCase):
    def setUp(self):
        self.data = rules.load_statements()

    def test_every_account_of_the_chart_lands_on_exactly_one_b01_line(self):
        parts = [part(n, sign * 1000) for n in leaves() for sign in (1, -1)]
        uncovered, double = rules.coverage(self.data['b01'], parts)
        self.assertEqual([(p['number'], p['net']) for p in uncovered], [])
        self.assertEqual([(p['number'], p['lines']) for p in double], [])

    def test_every_balance_sheet_account_lands_on_one_cash_flow_line(self):
        cash = self.data['cash']
        bs = [part(n, sign * 1000) for n in leaves() if n[:1] in '12349' and not any(n.startswith(c) for c in cash) for sign in (1, -1)]
        uncovered, double = rules.coverage([ln for ln in self.data['b03'] if ln['code'] != '60'], bs)
        self.assertEqual([p['number'] for p in uncovered], [])
        self.assertEqual([(p['number'], p['lines']) for p in double], [])

    def test_codes_follow_the_tt99_forms(self):
        codes = lambda key: [ln['code'] for ln in self.data[key]]
        self.assertEqual(len(codes('b01')), len(set(codes('b01'))))
        for c in ('100', '110', '150', '152', '160', '162', '230', '280', '300', '319', '400', '420a', '420b', '440'):
            self.assertIn(c, codes('b01'))
        self.assertEqual(codes('b02'), ['01', '02', '10', '11', '20', '21', '22', '23', '24', '25', '26', '30', '31', '32', '40', '50', '51', '52', '60'])
        self.assertEqual(codes('b03')[-4:], ['50', '60', '61', '70'])
        self.assertIn('Thông tư 99/2025/TT-BTC', self.data['source'])

    def test_balance_sheet_balances_and_splits_parties(self):
        parts = [part('111', 50_000_000), part('131', 12_000_000, party='C1'), part('131', -2_000_000, party='C2'), part('152', 30_000_000),
                 part('2141', -5_000_000), part('211', 25_000_000), part('331', -20_000_000, party='S1'), part('331', 1_000_000, party='S2'),
                 part('3335', -1_000_000), part('4111', -80_000_000), part('511', -40_000_000), part('632', 25_000_000), part('6421', 5_000_000)]
        self.assertEqual(sum(p['net'] for p in parts), 0)
        v = rules.evaluate_statement(self.data['b01'], lambda t: rules.term_amount(t, parts))
        self.assertEqual(v['280'], v['440'])
        self.assertEqual((v['131'], v['312'], v['311'], v['132']), (12_000_000, 2_000_000, 20_000_000, 1_000_000))
        self.assertEqual((v['223'], v['221']), (-5_000_000, 20_000_000))
        self.assertEqual(v['420b'], 10_000_000, 'unclosed profit of the period sits in 420b')

    def test_income_statement(self):
        moves = [part('511', -100_000_000, debit=0, credit=100_000_000), part('632', 60_000_000), part('6421', 10_000_000), part('515', -1_000_000),
                 part('711', -5_000_000), part('811', 2_000_000), part('82111', 6_000_000)]
        v = rules.evaluate_statement(self.data['b02'], lambda t: rules.term_amount(t, moves))
        self.assertEqual((v['10'], v['20'], v['30'], v['40'], v['50'], v['60']), (100_000_000, 40_000_000, 31_000_000, 3_000_000, 34_000_000, 28_000_000))

    def test_result_closing_moves_everything_to_4212(self):
        lines, profit = rules.result_entry([dict(account='511', net=-100), dict(account='632', net=60), dict(account='711', net=-5)], '911', '4212')
        self.assertEqual(profit, 45)
        self.assertEqual(rules.check_entry(lines), [])
        on = lambda acc, f: sum(ln[f] for ln in lines if ln['account'] == acc)
        self.assertEqual(on('911', 'debit'), on('911', 'credit'))
        self.assertEqual(on('4212', 'credit'), 45)
        loss, result = rules.result_entry([dict(account='511', net=-10), dict(account='642', net=30)], '911', '4212')
        self.assertEqual(result, -20)
        self.assertEqual(sum(ln['debit'] for ln in loss if ln['account'] == '4212'), 20)

    def test_bank_statement_match(self):
        ledger = [dict(date='2026-10-05', amount=-5_000_000, voucher='PAY-1', reference='UNC-01'), dict(date='2026-10-06', amount=-5_000_000, voucher='PAY-2', reference=''),
                  dict(date='2026-10-10', amount=12_000_000, voucher='REC-1', reference='BC-9')]
        statement = [dict(date='2026-10-07', amount=-5_000_000, reference='UNC-01'), dict(date='2026-10-08', amount=-5_000_000, reference=''),
                     dict(date='2026-10-11', amount=12_000_000, reference=''), dict(date='2026-10-20', amount=-30_000, reference='', description='Phí')]
        r = rules.match_bank(statement, ledger)
        self.assertEqual([m['ledger']['voucher'] for m in r['matched']], ['PAY-1', 'PAY-2', 'REC-1'])
        self.assertEqual([s['amount'] for s in r['statement_only']], [-30_000])
        self.assertEqual(r['ledger_only'], [])
        far = rules.match_bank([dict(date='2026-11-30', amount=12_000_000)], ledger)
        self.assertEqual(len(far['matched']), 0, 'same amount weeks apart is not a match')


if __name__ == '__main__':
    unittest.main()
