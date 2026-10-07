import unittest
from lotus_farm.source_data import source_number,source_date,source_text,staged_row
from lotus_farm.rules import RuleError


class TestSourceData(unittest.TestCase):
    def test_locale_is_explicit_and_blank_is_unknown(self):
        self.assertEqual(source_number('1.250'),1250)
        self.assertEqual(source_number('5,5'),5.5)
        self.assertEqual(source_number('1,250',decimal_separator='.',group_separator=','),1250)
        self.assertEqual(source_number(5.5),5.5)
        self.assertIsNone(source_number(''))
        self.assertIsNone(source_number('-'))
        self.assertEqual(source_number('0'),0)
        with self.assertRaises(RuleError):source_number('1.25')
        with self.assertRaises(RuleError):source_number(float('nan'))
        with self.assertRaises(RuleError):source_number('82%')
        self.assertEqual(source_number('82%',percent=True),0.82)

    def test_excel_and_text_dates(self):
        self.assertEqual(source_date('07/10/2026'),'2026-10-07')
        self.assertEqual(source_date('07.10.2026'),'2026-10-07')
        self.assertEqual(source_date(1),'1900-01-01')
        self.assertEqual(source_date(61),'1900-03-01')
        with self.assertRaises(RuleError):source_date(60)
        with self.assertRaises(RuleError):source_date('07/10/26')

    def test_source_identity_and_hash_for_retries(self):
        row=staged_row('source-1','Data',12,{'farm':'BP1','qty':None},'org-1')
        retry=staged_row('source-1','Data',12,{'farm':'BP1','qty':None},'org-1')
        changed=staged_row('source-1','Data',12,{'farm':'BP1','qty':0},'org-1')
        self.assertEqual(row,retry)
        self.assertEqual(row['row_key'],changed['row_key'])
        self.assertNotEqual(row['source_hash'],changed['source_hash'])
        self.assertEqual(source_text('  BP1.1.1  '),'BP1.1.1')
