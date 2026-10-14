import importlib.util
from pathlib import Path
from datetime import date
from decimal import Decimal
import json,sys,types,unittest
from unittest.mock import patch,Mock

class TestTableFilters(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('check_table_filters',Path(__file__).parents[1]/'lotus_farm/table_filters.py')
        self.module=importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules,{'frappe':types.SimpleNamespace(parse_json=lambda x:json.loads(x) if isinstance(x,str) else x,throw=Mock(side_effect=ValueError))}):spec.loader.exec_module(self.module)

    def test_filtering_all_rows_before_pagination_can_find_later_records(self):
        rows=[dict(name='Item '+str(i),group='Other' if i<60 else 'Selected') for i in range(75)]
        selected=self.module.selections({'group':['Selected']},['group'])
        matches=[row for row in rows if self.module.matches(row,selected)]
        self.assertEqual(len(matches[:50]),15)
        self.assertEqual(matches[0]['name'],'Item 60')
        self.assertEqual(len(self.module.distinct(rows,['group'])['group']),2)

    def test_empty_values_dates_decimal_and_blank_are_exact(self):
        self.assertFalse(self.module.matches(dict(value=0),{'value':[]}))
        self.assertTrue(self.module.matches(dict(value=None),{'value':[None]}))
        self.assertTrue(self.module.matches(dict(value=date(2026,10,13)),{'value':['2026-10-13']}))
        self.assertTrue(self.module.matches(dict(value=Decimal('1.25')),{'value':[1.25]}))

    def test_unknown_columns_and_nested_values_are_rejected(self):
        for raw in [{'secret':['x']},{'name':'not a list'},{'name':[{}]},[]]:
            with self.subTest(raw=raw),self.assertRaises(ValueError):self.module.selections(raw,['name'])

    def test_global_sort_happens_before_page_slice(self):
        rows=[dict(name=str(i),qty=i) for i in range(75)]
        ordered=self.module.sorted_rows(rows,[{'colId':'qty','sort':'desc'}],['name','qty'])
        self.assertEqual((ordered[0]['qty'],ordered[:50][-1]['qty']),(74,25))

    def test_sort_rejects_unknown_fields_and_uses_display_alias(self):
        with self.assertRaises(ValueError):self.module.sorted_rows([], [{'colId':'secret','sort':'asc'}],['name'])
        rows=[dict(name='B',item_name='Apple'),dict(name='A',item_name='Zebra')]
        self.assertEqual(self.module.sorted_rows(rows,[{'colId':'name','sort':'asc'}],['name'],{'name':'item_name'})[0]['name'],'B')
