import unittest
from datetime import date
from lotus_farm.checkin_rules import day_status
from lotus_farm.timekeeping_rules import employed_on,attendance_key
from lotus_farm.payroll_rules import salary_segments,segmented_pay,empty_summary


class HrAuditRules(unittest.TestCase):
    def test_typed_logs_require_both_directions(self):
        for kinds in [('IN','IN'),('OUT','OUT'),('','OUT'),('OUT','IN')]:
            with self.subTest(kinds=kinds):
                value=day_status(date(2026,10,1),[dict(time='2026-10-01 07:00',log_type=kinds[0]),dict(time='2026-10-01 11:00',log_type=kinds[1])])
                self.assertEqual(value['needs_review'],1)
                self.assertEqual(value['status'],'')

    def test_unlabelled_and_night_logs_still_work(self):
        for kinds in [('',''),('IN','OUT')]:
            value=day_status(date(2026,10,1),[dict(time='2026-10-01 22:00',log_type=kinds[0]),dict(time='2026-10-02 06:00',log_type=kinds[1])],dict(start_time='22:00',end_time='06:00'))
            self.assertEqual((value['status'],value['working_hours'],value['needs_review']),('Present',8,0))

    def test_historical_employment_bounds(self):
        person=dict(status='Left',date_of_joining='2026-10-02',relieving_date='2026-10-15')
        self.assertTrue(employed_on(person,'2026-10-10'))
        self.assertFalse(employed_on(person,'2026-10-01'))
        self.assertFalse(employed_on(person,'2026-10-16'))
        self.assertNotEqual(attendance_key('E','Morning'),attendance_key('E','Afternoon'))

    def test_future_salary_never_reprices_past_month(self):
        rows=[dict(name='old',from_date='2026-01-01',base=10400000),dict(name='future',from_date='2026-11-01',base=20800000)]
        intervals=salary_segments(rows,date(2026,9,1),date(2026,9,30))
        intervals[0]['summary']={**empty_summary(),'regular_hours':8}
        pay=segmented_pay(intervals)
        self.assertEqual(pay['gross'],400000)
        self.assertEqual(pay['rate_history'][0]['source'],'old')

    def test_mid_month_change_is_split_and_monthly_insurance_deducted_once(self):
        rows=[dict(name='old',from_date='2026-01-01',base=10400000),dict(name='new',from_date='2026-09-16',base=20800000)]
        intervals=salary_segments(rows,date(2026,9,1),date(2026,9,30))
        self.assertEqual([(s['start'].day,s['end'].day) for s in intervals],[(1,15),(16,30)])
        for segment in intervals:segment['summary']={**empty_summary(),'regular_hours':8}
        pay=segmented_pay(intervals,insured=True)
        self.assertEqual(pay['gross'],1200000)
        self.assertEqual(pay['employee_insurance'],2184000)

    def test_missing_historical_rate_is_explicit(self):
        rows=[dict(name='future',from_date='2026-11-01',base=20800000)]
        intervals=salary_segments(rows,date(2026,9,1),date(2026,9,30),dict(from_date='2026-01-01',base=20800000))
        intervals[0]['summary']={**empty_summary(),'regular_hours':8}
        pay=segmented_pay(intervals)
        self.assertEqual(pay['gross'],0)
        self.assertTrue(any('Thiếu mức lương có hiệu lực' in issue for issue in pay['issues']))
