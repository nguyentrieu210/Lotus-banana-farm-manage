import unittest
from lotus_farm import procurement_rules as r


class ProcurementRules(unittest.TestCase):
    def test_four_types_match_existing_item_flags(self):
        self.assertEqual(r.kind_for({'is_stock_item': 1}), 'Material')
        self.assertEqual(r.kind_for({'is_stock_item': 1}, 'Tool'), 'Tool')
        self.assertEqual(r.kind_for({'is_fixed_asset': 1}), 'Asset')
        self.assertEqual(r.kind_for({}), 'Service')
        for item, kind in (({}, 'Tool'), ({'is_stock_item': 1}, 'Asset'), ({'is_fixed_asset': 1}, 'Service')):
            with self.assertRaises(ValueError):
                r.kind_for(item, kind)

    def test_quotes_compare_stock_uom_tax_and_freight(self):
        first = r.quote_total(2, 450000, 10, '10', 50000)
        second = r.quote_total(20, 51000, 1, 'KCT', 0)
        self.assertEqual(first['gross'], 1040000)
        self.assertEqual(first['stock_qty'], 20)
        self.assertGreater(first['unit_cost'], second['unit_cost'])

    def test_missing_quote_is_not_zero_price(self):
        for rate in (None, '', 0, '0'):
            self.assertIsNone(r.quote_total(10, rate)['gross'])

    def test_calcium_with_shipping(self):
        self.assertEqual(r.quote_total(45, 45000, 1, 'KCT', 50000)['gross'], 2075000)

    def test_duplicate_photographs_have_same_business_identity(self):
        self.assertEqual(r.evidence_key('Phước Long', ' PL  159 ', '2026-10-14', 4700000),
                         r.evidence_key('Phước Long', 'pl159', '2026-10-14', '4700000'))
        self.assertNotEqual(r.evidence_key('A', '159', '2026-10-14', 4700000), r.evidence_key('B', '159', '2026-10-14', 4700000))

    def test_reservations_cap_partial_reimbursement(self):
        self.assertEqual(r.remaining(1000, 250, 300, 450), 450)
        with self.assertRaises(ValueError):
            r.remaining(1000, 250, 300, 451)

    def test_non_finite_negative_and_zero_quantities_rejected(self):
        for value in ('nan', 'Infinity', '-1', 'text'):
            with self.assertRaises(ValueError):
                r.number(value)
        with self.assertRaises(ValueError):
            r.quote_total(0, 100)

    def test_fingerprints_include_source_and_mappings(self):
        self.assertEqual(r.digest({'a': 1, 'b': 2}), r.digest({'b': 2, 'a': 1}))
        self.assertNotEqual(r.digest({'month': '2026-10'}), r.digest({'month': '2026-11'}))

    def test_reason_only_when_not_the_cheapest(self):
        self.assertFalse(r.needs_reason(12_400, [12_400, 13_000, None]))
        self.assertFalse(r.needs_reason(12_400.001, [12_400, 13_000]))  # rounding is not a choice
        self.assertTrue(r.needs_reason(13_000, [12_400, 13_000]))
        self.assertTrue(r.needs_reason(None, [12_400]))  # an unpriced line is never the cheapest
        self.assertFalse(r.needs_reason(5_000, [None, 5_000]))  # unpriced offers do not count as cheaper


    def test_printed_total_within_one_dong_per_goods_line(self):
        self.assertEqual(r.printed_total_gap(1150000, 1150002, 3), (2.0, True))
        self.assertEqual(r.printed_total_gap(1150000, 1149996, 3), (-4.0, False))
        self.assertEqual(r.printed_total_gap(500000, 500001, 0), (1.0, True), 'a service-only invoice still gets 1 đ')
        self.assertFalse(r.printed_total_gap(500000, 500001.5, 1)[1])

    def test_suspect_lines_name_the_likely_entry_error(self):
        lines = [dict(line=1, name='Ure', qty=10, rate=100000, vat=0.05), dict(line=2, name='Vôi', qty=4, rate=25000, vat=0.08)]
        self.assertEqual(r.suspect_lines(lines, 30000), [dict(line=1, name='Ure', reason='thuế suất có thể là 8%')])
        self.assertEqual(r.suspect_lines(lines, -27000), [dict(line=2, name='Vôi', reason='số lượng có thể thừa 1')])
        self.assertEqual(r.suspect_lines(lines, 210000), [dict(line=1, name='Ure', reason='số lượng có thể thiếu 2')])
        self.assertEqual(r.suspect_lines(lines, 777), [], 'no simple explanation: the message asks to check every line')

    def test_aging_by_due_date_on_the_closing_date(self):
        day = '2026-11-10'
        cases = {'2026-11-10': 'current', '2026-12-01': 'current', '2026-11-09': 'd1_30', '2026-10-11': 'd1_30', '2026-10-10': 'd31_60',
                 '2026-09-11': 'd31_60', '2026-09-10': 'd61_90', '2026-08-12': 'd61_90', '2026-08-11': 'd90_plus', None: 'no_due'}
        for due, bucket in cases.items():
            self.assertEqual(r.aging_bucket(due, day), bucket, due)
        totals = r.age([dict(amount=100, due_date='2026-11-20'), dict(amount=40, due_date='2026-10-01'), dict(amount=5, due_date=None)], day)
        self.assertEqual((totals['current'], totals['d31_60'], totals['no_due'], sum(totals.values())), (100, 40, 5, 145))
        self.assertEqual(set(totals), set(r.AGING_BUCKETS))
        self.assertEqual(set(r.AGING_LABELS), set(r.AGING_BUCKETS))

    def test_due_in_the_next_seven_days(self):
        day = '2026-11-10'
        self.assertEqual([r.due_within(d, day) for d in ('2026-11-10', '2026-11-11', '2026-11-17', '2026-11-18', '2026-11-01', None)],
                         [False, True, True, False, False, False])


if __name__ == '__main__':
    unittest.main()
