import unittest
from lotus_farm.timekeeping_rules import crew_values,status_days


class TestTimekeepingRules(unittest.TestCase):
    def test_partial_crew_days_and_piecework_amount(self):
        row=crew_values(20,18,17.5,125.5,12000)
        self.assertEqual((row['absent'],row['workdays'],row['amount']),(2,17.5,1506000))

    def test_impossible_headcounts_or_days_are_rejected(self):
        for values in [(10,11,10),(10,8,9),(2.5,2,2),(3,2.5,2),(-1,0,0)]:
            with self.subTest(values=values),self.assertRaises(ValueError):crew_values(*values)

    def test_nan_infinity_and_negative_cost_are_rejected(self):
        for qty,rate in [(float('nan'),1),(1,float('inf')),(-1,1),(1,-1),(1e308,1e308)]:
            with self.assertRaises(ValueError):crew_values(1,1,1,qty,rate)

    def test_absence_leave_and_unknown_do_not_become_workdays(self):
        self.assertEqual(status_days('Present'),1)
        self.assertEqual(status_days('Half Day'),.5)
        for status in ('Absent','On Leave','',None):self.assertEqual(status_days(status),0)


class TestTimekeepingCalendarAndClose(unittest.TestCase):
    def test_month_range_rejects_bad_text(self):
        from datetime import date
        from lotus_farm.timekeeping_rules import month_range
        self.assertEqual(month_range('2026-02'),(date(2026,2,1),date(2026,2,28)))
        for value in ('2026-13','2026/10','26-10','',None):
            with self.subTest(value=value),self.assertRaises(ValueError):month_range(value)

    def test_calendar_has_sundays_fixed_holidays_and_extras_once(self):
        from datetime import date
        from lotus_farm.timekeeping_rules import calendar_days
        rows=calendar_days(2026,('Sunday',),[('2026-02-17','Tết'),('2026-09-01','Liền kề Quốc khánh')])
        days={r[0]:r for r in rows}
        self.assertEqual(len(rows),len(days),'one row per date')
        self.assertEqual(sum(1 for r in rows if r[2]),52)
        self.assertEqual(days[date(2026,9,2)][1:],('Quốc khánh',0))
        self.assertEqual(days[date(2026,2,17)][1:],('Tết',0))
        with self.assertRaises(ValueError):calendar_days(2026,extra=[('2027-01-01','x')])

    def test_missing_attendance_respects_joining_holidays_and_today(self):
        from datetime import date
        from lotus_farm.timekeeping_rules import missing_attendance,close_blockers
        people=[dict(name='E1',date_of_joining='2026-10-05'),dict(name='E2',date_of_joining='2025-01-01',relieving_date='2026-10-02')]
        records=[dict(employee='E1',attendance_date='2026-10-05')]
        holidays={date(2026,10,4):1,date(2026,10,11):1}
        gaps=missing_attendance(people,records,date(2026,10,1),date(2026,10,31),holidays,date(2026,10,8))
        self.assertEqual(gaps,{'E1':[date(2026,10,6),date(2026,10,7),date(2026,10,8)],'E2':[date(2026,10,1),date(2026,10,2)]})
        self.assertEqual(close_blockers(),[])
        codes=[r['code'] for r in close_blockers(draft_attendance=2,draft_crew=1,open_punches=3,missing=gaps,has_calendar=False)]
        self.assertEqual(codes,['calendar','draft_attendance','draft_crew','open_punches','missing_attendance'])
