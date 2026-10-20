import unittest
from datetime import date
from pathlib import Path
import json

from lotus_farm.onedrive_protocol import edate, selection_schedule, harvest_curve, forecast_quantities, color_periods, scheduled_work_due, source_balance, window_months


class OneDriveProtocolTests(unittest.TestCase):
    def test_selection_uses_original_anchor_and_preserves_month_end(self):
        rows = selection_schedule('2026-03-31', count=4)
        self.assertEqual([r['selection_date'] for r in rows], ['2026-03-31','2026-09-30','2027-03-31','2027-09-30'])
        self.assertEqual(rows[0]['date_kind'], 'Equivalent')
        self.assertTrue(all(not r['observed'] for r in rows))
        self.assertEqual(edate('2024-02-29', 12),date(2025,2,28))

    def test_planting_is_not_handover_or_an_observed_selection(self):
        self.assertEqual(selection_schedule('2026-03-31',basis='Planting')[0]['selection_date'],'2026-09-30')
        with self.assertRaises(ValueError):selection_schedule('2026-03-31',basis='Invented Planting')
        with self.assertRaises(ValueError):edate('2026-03-31',1.5)

    def test_mother_crop_and_selected_ratoon_have_distinct_curves(self):
        mother=harvest_curve('2026-03-31',basis='Planting',cycles=2)
        ratoon=harvest_curve('2026-09-30',basis='Selection')
        self.assertEqual([r['month'] for r in mother[:4]],['2026-11','2026-12','2027-01','2027-02'])
        self.assertEqual([r['month'] for r in mother[4:]],[r['month'] for r in ratoon])
        self.assertEqual([r['share'] for r in ratoon],[.17,.25,.4,.18])
        self.assertAlmostEqual(sum(r['share'] for r in ratoon),1)
        # PowerQuery aligns an anchor on day 1 or 2 to the preceding month bucket.
        self.assertEqual(harvest_curve('2026-03-02')[0]['month'],'2026-11')

    def test_processed_kg_is_not_multiplied_by_packout_twice(self):
        params=dict(cut_rate=.82,harvest_rate=.95,processed_rate=.97,gross_bunch_kg=20,processed_bunch_kg=17)
        result=forecast_quantities(1000,params)
        self.assertEqual(result['gross_kg'],15580)
        self.assertEqual(result['processed_kg'],12845.71)
        for key,value in [('cut_rate',1.1),('gross_bunch_kg',float('nan')),('processed_bunch_kg',21)]:
            with self.assertRaises(ValueError):forecast_quantities(1000,{**params,key:value})

    def test_color_period_is_inclusive_and_wraps_17_to_1(self):
        colors=[dict(code=f'M{n:02}',label=str(n)) for n in range(1,18)]
        rows=color_periods('2025-12-28','M13',colors,'2026-01-17','2026-01-23')
        self.assertEqual(rows[0]['color_code'],'M17')
        self.assertEqual(rows[0]['valid_to'],'2026-01-21')
        self.assertEqual(rows[1]['color_code'],'M01')
        self.assertTrue(all(r['date_kind']=='Planned' for r in rows))
        with self.assertRaises(ValueError):color_periods('2025-12-28','M13',colors,'2026-02-01','2026-01-01')

    def test_work_schedule_repeats_from_original_calendar_anchor(self):
        self.assertTrue(scheduled_work_due('2026-03-31','2026-09-30',offset_months=6,repeat_months=6))
        self.assertTrue(scheduled_work_due('2026-03-31','2027-03-31',offset_months=6,repeat_months=6))
        self.assertFalse(scheduled_work_due('2026-03-31','2027-03-30',offset_months=6,repeat_months=6))
        self.assertTrue(scheduled_work_due('2026-03-31','2026-04-07',offset_days=7,repeat_days=7))
        with self.assertRaises(ValueError):scheduled_work_due('2026-03-31','2026-09-30',repeat_days=180,repeat_months=6)

    def test_cut_actuals_replace_that_portion_of_sucker_projection(self):
        result=source_balance(82,30,28,20,2)
        self.assertEqual(result,dict(unobserved_cut=52,remaining_observed_cut=6))
        self.assertEqual(sum(result.values()),58)
        with self.assertRaises(ValueError):source_balance(82,30,28,27,2)
        rows=window_months('2026-12-25','2027-01-09')
        self.assertEqual([r['month'] for r in rows],['2026-12','2027-01'])
        self.assertAlmostEqual(rows[0]['share'],7/16)
        self.assertAlmostEqual(sum(r['share'] for r in rows),1)

    def test_extracted_presets_and_all_source_curves_reconcile(self):
        data=json.loads((Path(__file__).resolve().parents[1]/'lotus_farm/data/onedrive_protocol_v1.json').read_text(encoding='utf8'))
        self.assertEqual(len(data['defaults']),57)
        self.assertEqual(len(data['conditions']),9)
        self.assertEqual(len(data['color_history']),183)
        self.assertEqual(len(data['colors']),17)
        for params in data['defaults']:forecast_quantities(1,params)
        for enterprise in [k for k in data['curves'][0] if k.startswith('XNC-')]:
            for cycle in range(1,19):
                self.assertAlmostEqual(sum(r.get(enterprise) or 0 for r in data['curves'] if r['Vụ TH']==cycle),1)
        self.assertEqual(data['color_extension']['period_days'],5)


if __name__=='__main__':unittest.main()
