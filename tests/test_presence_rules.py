import unittest
from datetime import date
from lotus_farm.presence_rules import presence_status


class PresenceRules(unittest.TestCase):
    day=date(2026,10,29)

    def result(self,*stamps):
        return presence_status(self.day,[dict(time='2026-10-29 '+s,log_type='IN') for s in stamps])

    def test_one_morning_one_afternoon_is_one_day_even_if_both_labelled_in(self):
        row=self.result('06:46:00','17:01:00')
        self.assertEqual((row['status'],row['workdays'],row['working_hours']),('Present',1,8))
        self.assertIsNone(row['out_time'])
        self.assertEqual(row['afternoon_time'],'2026-10-29 17:01:00')
        self.assertEqual(row['overtime_hours'],0)

    def test_repeated_morning_stamps_only_count_half(self):
        row=self.result('06:46:00','07:01:00','11:00:00','07:01:00')
        self.assertEqual((row['workdays'],row['morning_present'],row['afternoon_present']),(.5,1,0))
        self.assertEqual(row['morning_time'],'2026-10-29 06:46:00')

    def test_afternoon_only_and_repeated_exits_count_half(self):
        row=presence_status(self.day,[dict(time='2026-10-29 '+s,log_type='OUT') for s in ['17:01:00','18:00:00']])
        self.assertEqual((row['status'],row['workdays']),('Half Day',.5))

    def test_midday_and_other_dates_do_not_count(self):
        row=presence_status(self.day,[dict(time='2026-10-29 12:00:00'),dict(time='2026-10-28 06:30:00')])
        self.assertEqual((row['morning_present'],row['afternoon_present'],row['workdays']),(0,0,0))

    def test_strict_seven_and_seventeen_boundaries(self):
        self.assertEqual(self.result('06:59:59')['workdays'],.5)
        self.assertEqual(self.result('07:00:00','07:00:01','16:59:59','17:00:00')['workdays'],0)
        self.assertEqual(self.result('17:00:01')['workdays'],.5)

    def test_no_punches_is_zero_and_no_late_exit_overtime_is_invented(self):
        self.assertEqual(self.result()['workdays'],0)
        self.assertEqual(self.result('06:46:00','19:30:00')['overtime_hours'],0)
