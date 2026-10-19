import unittest
from datetime import date
from lotus_farm import report_charts as rc


class ReportCharts(unittest.TestCase):
    def test_zones_keep_uncounted_blocks_out_of_density(self):
        blocks=[dict(farm_zone='B',area_ha=2,lotus_tree_count=3000),dict(farm_zone='A',area_ha=4,lotus_tree_count=8000),
                dict(farm_zone='A',area_ha=1,lotus_tree_count=None),dict(farm_zone='',area_ha=1.5),dict(farm_zone='E',area_ha=3,lotus_tree_count=0)]
        zones=rc.land_by_zone(blocks)
        self.assertEqual([z['zone'] for z in zones],['A','B','E',rc.UNZONED])
        self.assertEqual((zones[2]['counted_blocks'],zones[2]['trees_per_ha']),(0,None),'a census of 0 is not planted, not density 0')
        self.assertEqual(zones[0]['blocks'],2);self.assertEqual(zones[0]['counted_blocks'],1);self.assertEqual(zones[0]['trees'],8000)
        self.assertAlmostEqual(zones[0]['trees_per_ha'],8000/4,msg='the uncounted 1 ha block does not dilute density')
        self.assertIsNone(zones[3]['trees_per_ha'],'a zone with no census has no density, not zero')

    def test_flowering_groups_by_month_and_skips_unknown(self):
        rows=rc.flowering_by_month([dict(lotus_estimated_flowering_date='2026-12-01',lotus_tree_count=5),
            dict(lotus_estimated_flowering_date=date(2026,11,1),lotus_tree_count=7),dict(lotus_estimated_flowering_date=None,lotus_tree_count=9)])
        self.assertEqual(rows,[dict(month='2026-11',blocks=1,trees=7),dict(month='2026-12',blocks=1,trees=5)])

    def test_work_completion_never_sums_units_and_keeps_empty_days(self):
        tasks=[dict(planned_qty=100,completed_qty=50,required_workdays=4,actual_workdays=3,work_name='Bao buồng'),
               dict(planned_qty=10,completed_qty=10,required_workdays=1,actual_workdays=1,work_name='Cắt bắp')]
        days=rc.work_by_day([(date(2026,10,18),tasks),(date(2026,10,19),[])])
        self.assertEqual(days[0]['completion_percent'],75.0,'per-task average, not 60/110')
        self.assertEqual(days[0]['required_workdays'],5);self.assertEqual(days[0]['actual_workdays'],4)
        self.assertEqual(days[1],dict(date='2026-10-19',tasks=0,completion_percent=None,required_workdays=0,actual_workdays=0))

    def test_work_types_fold_tail_into_other(self):
        tasks=[dict(work_name='W%d'%i,required_workdays=20-i,actual_workdays=1) for i in range(12)]
        rows=rc.work_by_type(tasks,limit=4)
        self.assertEqual([r['work'] for r in rows],['W0','W1','W2',rc.OTHER])
        self.assertEqual(rows[-1]['tasks'],9);self.assertEqual(rows[-1]['actual_workdays'],9)

    def test_weekly_includes_empty_weeks_and_ignores_outside_or_bad_values(self):
        rows=[dict(d='2026-10-14',kg=10),dict(d='2026-10-15',kg='5'),dict(d='2026-09-01',kg=99),dict(d='2026-10-21',kg=float('nan'))]
        weeks=rc.weekly(rows,'d',['kg'],date(2026,10,12),date(2026,10,26))
        self.assertEqual(weeks,[dict(week='2026-10-12',kg=15.0),dict(week='2026-10-19',kg=0.0),dict(week='2026-10-26',kg=0.0)])

    def test_top_totals_and_stock_months(self):
        rows=[dict(reason='R%d'%(i%10),bunch_qty=1) for i in range(30)]+[dict(reason=None,bunch_qty=2)]
        totals=rc.top_totals(rows,'reason','bunch_qty',limit=3)
        self.assertEqual(len(totals),3);self.assertEqual(totals[-1]['label'],rc.OTHER)
        self.assertEqual(sum(t['value'] for t in totals),32)
        months=rc.stock_by_month([dict(posting_date='2026-10-02',stock_entry_type='Material Receipt'),
            dict(posting_date=date(2026,10,5),stock_entry_type='Material Issue'),dict(posting_date='2026-09-30',stock_entry_type='Manufacture')])
        self.assertEqual(months,[dict(month='2026-10',receipt=1,issue=1,transfer=0)])


if __name__=='__main__':
    unittest.main()
