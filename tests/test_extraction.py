import unittest
from io import BytesIO
from openpyxl import Workbook
from lotus_farm.extraction import read_workbook
from lotus_farm.rules import RuleError


class ExtractionTests(unittest.TestCase):
    def workbook(self,values):
        book=Workbook();sheet=book.active;sheet.title='Actual'
        sheet.append(['Org','Qty','Date']);sheet.append(values)
        output=BytesIO();book.save(output);return output.getvalue()
    def mapping(self):
        return dict(sheet_name='Actual',header_row=1,first_data_row=2,source_key='source1',legacy_org_column='Org',decimal_mark=',',grouping_mark='.',fields=[dict(source_column='Qty',target_field='plant_qty',value_type='Integer',required=1),dict(source_column='Date',target_field='posting_date',value_type='Date',required=1)])
    def test_locale_date_raw_lineage_and_control_totals(self):
        result=read_workbook(self.workbook(['XNC / farm','1.250','07/10/2026']),self.mapping())
        import json
        row=result['rows'][0];self.assertEqual(row['source_row'],2)
        self.assertEqual(json.loads(row['normalized_json']),dict(plant_qty=1250,posting_date='2026-10-07'))
        self.assertEqual(result['control_totals']['plant_qty'],1250)
        self.assertIn('1.250',row['raw_json'])
    def test_formula_and_blank_never_become_zero(self):
        result=read_workbook(self.workbook(['farm','=100+20',None]),self.mapping())
        self.assertIn('Formula cell',result['rows'][0]['validation_error'])
        self.assertIn('blank',result['rows'][0]['validation_error'])
        self.assertEqual(result['control_totals']['plant_qty'],0)
    def test_wrong_sheet_does_not_guess(self):
        mapping=self.mapping();mapping['sheet_name']='Unknown'
        with self.assertRaises(RuleError):read_workbook(self.workbook(['farm',1,'07/10/2026']),mapping)
