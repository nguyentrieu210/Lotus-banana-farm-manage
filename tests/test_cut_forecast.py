import datetime as dt
import json
import unittest
from io import BytesIO
from pathlib import Path

from lotus_farm import cut_forecast_rules as cf

JOURNAL = Path(__file__).resolve().parents[1] / 'data' / 'farm222-cut-journal-2.json'
D = dt.date


def workbook(journal_rows, params=None, waves=(0.17, 0.4, 0.25, 0.18)):
    from openpyxl import Workbook
    book = Workbook()
    sheet = book.active
    sheet.title = 'THÔNG SỐ'
    sheet.append(['LOTUS | THÔNG SỐ'])
    for label, value in (params or [('Chặt mẹ lần 2 → bắt đầu đợt trổ 1', 120), ('Tỷ lệ cắt bắp / số cây', 0.9), ('Kg sơ chế / buồng', 20)]):
        sheet.append([label, value])
    sheet.append(['Đợt trổ', 'Tỷ lệ RH áp dụng'])
    for k, share in enumerate(waves, start=1):
        sheet.append([k, share])
    sheet.append(['Tổng tỷ lệ', sum(waves)])
    journal = book.create_sheet('NHẬT KÝ GỐC')
    journal.append(['DỮ LIỆU GỐC'])
    journal.append([])
    journal.append([])
    journal.append(['Khu', 'Ngày chặt mẹ lần 2', 'Số cây', 'Dòng trên file nguồn'])
    for row in journal_rows:
        journal.append(list(row))
    out = BytesIO()
    book.save(out)
    return out.getvalue()


class CutForecastRules(unittest.TestCase):
    def test_one_journal_row_matches_the_workbook(self):
        rows = cf.expand([dict(zone='A', cut_date=D(2026, 3, 31), tree_qty=73)], cf.DEFAULTS)
        self.assertEqual([r['shoot_qty'] for r in rows], [12, 29, 18, 14], 'last wave takes the remainder')
        first = rows[0]
        self.assertEqual((first['shoot_from'], first['shoot_to'], first['shoot_date']), (D(2026, 7, 29), D(2026, 8, 27), D(2026, 8, 12)))
        self.assertEqual((first['inject_date'], first['budcut_date'], first['harvest_date']), (D(2026, 8, 17), D(2026, 9, 1), D(2026, 11, 5)))
        self.assertLess(first['inject_date'], first['budcut_date'], 'chích bắp comes before cắt bắp')
        self.assertEqual((first['budcut_qty'], first['harvest_qty'], first['pack_qty'], first['kg']), (11, 11, 11, 220))

    def test_excel_rounding_is_half_away_from_zero(self):
        self.assertEqual(cf.excel_round(2.5), 3)
        self.assertEqual(cf.excel_round(0.5), 1)
        self.assertEqual(cf.excel_round(1.005, 2), 1.01)

    def test_whole_farm_222_journal_reproduces_the_workbook(self):
        entries = json.loads(JOURNAL.read_text(encoding='utf-8'))
        result = cf.compute(entries, cf.DEFAULTS)
        t = result['totals']
        self.assertEqual((t['entries'], t['trees'], t['shoot'], t['budcut'], t['harvest'], t['pack'], t['tonnes']),
                         (358, 430871, 430871, 387859, 376247, 368750, 7375.0))
        months = {m['month']: m for m in result['months']}
        self.assertEqual(months['2026-08']['shoot'], 63, 'the first month is kept (the workbook table started in September)')
        self.assertEqual((months['2027-02']['tonnes'], months['2027-05']['tonnes']), (513.72, 1852.64))
        self.assertEqual((t['peak_month'], t['first_harvest'], t['last_harvest']), ('2027-05', D(2026, 11, 5), D(2027, 8, 8)))
        self.assertEqual(sum(m['shoot'] for m in result['months']), t['trees'], 'no month is dropped')
        self.assertEqual({z['zone']: z['tonnes'] for z in result['zones']}, {'A': 1631.58, 'B': 1520.3, 'C': 1689.3, 'D': 1373.76, 'E': 1160.06})

    def test_profile_rules(self):
        _, errors = cf.validate_profile({**cf.DEFAULTS, 'wave_4_share': 0.1})
        self.assertTrue(any('100%' in e for e in errors), errors)
        _, errors = cf.validate_profile({**cf.DEFAULTS, 'cut_rate': 1.2, 'days_to_first_shoot': -3, 'kg_per_bunch': 0})
        self.assertEqual(len(errors), 3, errors)
        _, errors = cf.validate_profile({**cf.DEFAULTS, 'representative_day': 30})
        self.assertTrue(errors)
        profile, errors = cf.validate_profile({**cf.DEFAULTS, 'days_to_first_shoot': '180'})
        self.assertEqual((errors, profile['days_to_first_shoot']), ([], 180))

    def test_changing_a_parameter_moves_dates_not_totals(self):
        entries = [dict(zone='A', cut_date=D(2026, 5, 1), tree_qty=1000)]
        base = cf.compute(entries, cf.DEFAULTS)['totals']
        later = cf.compute(entries, {**cf.DEFAULTS, 'days_to_first_shoot': 180})['totals']
        self.assertEqual(base['pack'], later['pack'])
        self.assertEqual(later['first_harvest'] - base['first_harvest'], dt.timedelta(days=60))

    def test_parse_workbook(self):
        content = workbook([('A', dt.datetime(2026, 3, 31), 73, 'Khu A | dòng 7'), ('C', '30/07/2026', 290, 'Khu C | dòng 20'),
                            ('C', '30/07/2026', 22, 'Khu C | dòng 21'), ('B', 'hôm qua', 5, ''), ('B', D(2026, 6, 1), -4, '')])
        parsed = cf.parse_workbook(content)
        self.assertEqual([(e['zone'], e['cut_date'], e['tree_qty']) for e in parsed['entries']],
                         [('A', D(2026, 3, 31), 73), ('C', D(2026, 7, 30), 290), ('C', D(2026, 7, 30), 22)], 'two cuts on one day are both kept')
        self.assertEqual([e['line'] for e in parsed['entry_errors']], [8, 9])
        self.assertEqual(parsed['params']['days_to_first_shoot'], 120)
        self.assertEqual(parsed['params']['wave_2_share'], 0.4)
        self.assertEqual(set(parsed['found_params']), {'days_to_first_shoot', 'cut_rate', 'kg_per_bunch', *cf.WAVES})
        bad = cf.parse_workbook(workbook([('A', D(2026, 3, 31), 73, 'x')], waves=(0.2, 0.4, 0.25, 0.1)))
        self.assertTrue(bad['param_errors'], 'shares that do not add up to 100% are rejected')

    def test_entry_key_tells_same_day_cuts_apart(self):
        a = cf.entry_key('LOTUS-222', 'C', '2026-07-30', 'Khu C | dòng 20')
        b = cf.entry_key('LOTUS-222', 'C', '2026-07-30', 'Khu C | dòng 21')
        self.assertNotEqual(a, b)
        self.assertEqual(a, cf.entry_key('LOTUS-222', 'C', '2026-07-30', 'Khu C | dòng 20'))


if __name__ == '__main__':
    unittest.main()
