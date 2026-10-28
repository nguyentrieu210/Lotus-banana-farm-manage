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


if __name__ == '__main__':
    unittest.main()
