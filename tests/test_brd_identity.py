import json
import unittest
from io import BytesIO
from openpyxl import Workbook
from lotus_farm.extraction import read_workbook


class IdentityTests(unittest.TestCase):
    def source(self,rows):
        book=Workbook();sheet=book.active;sheet.title='Events';sheet.append(['Org','Event ID','Qty','L1','L2'])
        for row in rows:sheet.append(row)
        out=BytesIO();book.save(out);return out.getvalue()

    def mapping(self,version):
        return dict(sheet_name='Events',header_row=1,first_data_row=2,legacy_org_column='Org',source_key=version,source_family='drive/item',business_key_columns='["Event ID"]',decimal_mark=',',grouping_mark='.',fields=[dict(source_column='Qty',target_field='plant_qty',value_type='Integer')])

    def test_reordered_revised_workbook_keeps_business_identity(self):
        first=read_workbook(self.source([['farm','event-a',25,None,None],['farm','event-b',25,None,None]]),self.mapping('v1'))['rows']
        second=read_workbook(self.source([['farm','event-b',25,None,None],['farm','event-a',25,None,None]]),self.mapping('v2'))['rows']
        self.assertEqual(first[0]['row_key'],second[1]['row_key'])
        self.assertEqual(first[0]['normalized_hash'],second[1]['normalized_hash'])
        self.assertNotEqual(first[0]['business_key'],first[1]['business_key'])
        revised=read_workbook(self.source([['farm','event-a',26,None,None]]),self.mapping('v3'))['rows'][0]
        self.assertEqual(first[0]['business_key'],revised['business_key'])
        self.assertNotEqual(first[0]['normalized_hash'],revised['normalized_hash'])

    def test_duplicate_and_blank_event_identity_need_review(self):
        rows=read_workbook(self.source([['farm','same',1,None,None],['farm','same',1,None,None],['farm',None,1,None,None]]),self.mapping('v1'))['rows']
        self.assertIn('Duplicate business identity',rows[1]['validation_error'])
        self.assertIn('identity is blank',rows[2]['validation_error'])

    def test_samples_unpivot_preserves_lane_identity_and_blank(self):
        mapping=self.mapping('v1');mapping['sample_columns_json']=json.dumps([dict(column='L1',lane='Lane 1',sample_no='1',uom='cm'),dict(column='L2',lane='Lane 2',sample_no='2',uom='cm')])
        row=read_workbook(self.source([['farm','measure-a',1,'18,5',None]]),mapping)['rows'][0]
        self.assertFalse(row['validation_error'])
        samples=json.loads(row['normalized_json'])['samples']
        self.assertEqual(samples,[dict(sample_no='1',lane='Lane 1',dimension='Length',value=18.5,uom='cm')])
