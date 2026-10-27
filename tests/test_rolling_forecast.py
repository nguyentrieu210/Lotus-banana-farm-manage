import unittest
from collections import defaultdict
from lotus_farm.block_forecast_engine import forecast,months_after

def block():
    return dict(name='A1',active=1,farm_zone='A',lotus_tree_count=1000,lotus_estimated_flowering_date='2026-11-01')

class RollingForecastTests(unittest.TestCase):
    def test_selection_at_flowering_repeats_each_wave_after_six_calendar_months(self):
        result=forecast([block()],[],horizon_months=36,include_daily=True)
        first={(r['cycle_no'],r['wave']):r for r in result['rows']}
        for wave in range(1,5):
            current=first[1,wave];following=first[2,wave]
            self.assertEqual(current['selection_date'],current['flower_date'])
            self.assertEqual(following['flower_date'],str(months_after(current['selection_date'],6)))
            self.assertEqual(current['next_flower_date'],following['flower_date'])
        self.assertEqual(first[2,1]['flower_date'],'2027-05-01')
        self.assertEqual(first[2,1]['harvest_date'],'2027-07-26')
        self.assertEqual(first[2,2]['flower_date'],'2027-06-01')

    def test_36_month_totals_are_scoped_and_include_zero_months(self):
        result=forecast([block()],[],horizon_months=36)
        self.assertEqual((result['window_start'],result['window_end']),('2026-11-01','2029-10-31'))
        self.assertEqual(len(result['monthly']),36)
        self.assertEqual(result['monthly'][0]['bunches'],0)
        self.assertEqual(sum(r['bunches'] for r in result['monthly']),sum(r['bunches_harvest'] for r in result['rows']))
        self.assertEqual(sum(r['packed_kg'] for r in result['monthly']),sum(r['kg_pack'] for r in result['rows']))
        self.assertTrue(all(r['harvest_window_end']<=result['window_end'] for r in result['rows']))

    def test_counted_trees_are_not_reduced_or_split_four_times_each_generation(self):
        result=forecast([block()],[],horizon_months=36,include_daily=True)
        counts=defaultdict(int)
        for day in result['daily_rows']:counts[day['cycle_no']]+=day['tree_qty']
        self.assertEqual(len(counts),6)
        self.assertTrue(all(n==1000 for n in counts.values()))
        future=next(r for r in result['rows'] if r['generation']==1)
        self.assertIsNone(future['crop_cycle']);self.assertEqual(future['count_status'],'Planning Baseline')

    def test_explicit_successor_supersedes_derived_future_crop(self):
        def cohort(cycle,qty,anchor,when):
            return dict(name='C'+str(cycle),farm_block='A1',crop_cycle='CYCLE'+str(cycle),cycle_no=cycle,cohort_code='SOURCE',version=1,approval_state='Approved',planned_qty=qty,quantity_basis='Trees',anchor=anchor,anchor_date=when)
        result=forecast([block()],[cohort(1,1000,'Shooting','2026-11-01'),cohort(2,800,'Selection','2026-11-01')],horizon_months=36,include_daily=True)
        counts=defaultdict(int)
        for day in result['daily_rows']:counts[day['cycle_no']]+=day['tree_qty']
        self.assertEqual(counts[1],1000);self.assertEqual(counts[2],800)

    def test_observed_bunches_do_not_become_sucker_counts(self):
        source=dict(name='OBS',farm_block='A1',crop_cycle='C1',cycle_no=1,cohort_code='OBS',version=1,approval_state='Approved',planned_qty=1000,quantity_basis='Bunches',anchor='Shooting',anchor_date='2026-11-01')
        result=forecast([block()],[source],horizon_months=36)
        self.assertEqual(len(result['rows']),1)
        self.assertTrue(any('Nguồn buồng' in warning for warning in result['warnings']))

    def test_calendar_month_end_is_carried_from_previous_crop(self):
        b={**block(),'lotus_estimated_flowering_date':'2026-08-31'}
        result=forecast([b],[],horizon_months=36)
        starts={r['cycle_no']:r['flower_date'] for r in result['rows'] if r['wave']==1}
        self.assertEqual(starts[2],'2027-02-28');self.assertEqual(starts[3],'2027-08-28')
