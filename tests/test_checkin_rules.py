import unittest
from datetime import date, datetime, timedelta

from lotus_farm.checkin_rules import day_status, shift_window

DAY = date(2026, 10, 14)
SHIFT = dict(start_time=timedelta(hours=7), end_time='16:00', late_entry_grace_period=10, early_exit_grace_period=10,
             working_hours_threshold_for_half_day=6, working_hours_threshold_for_absent=2)


def punch(hour, minute=0, kind='', day=DAY):
    return dict(time=datetime.combine(day, datetime.min.time()).replace(hour=hour, minute=minute), log_type=kind)


class CheckinRules(unittest.TestCase):
    def test_full_day_inside_grace_is_present_without_flags(self):
        row = day_status(DAY, [punch(16, 5, 'OUT'), punch(7, 8, 'IN'), punch(12)], SHIFT)
        self.assertEqual((row['status'], row['late_entry'], row['early_exit'], row['needs_review']), ('Present', 0, 0, 0))
        self.assertEqual(row['working_hours'], 8.95)
        self.assertEqual(row['overtime_hours'], 0.08)

    def test_late_early_and_thresholds(self):
        half = day_status(DAY, [punch(7, 30), punch(12, 30)], SHIFT)
        self.assertEqual((half['status'], half['late_entry'], half['early_exit']), ('Half Day', 1, 1))
        absent = day_status(DAY, [punch(7), punch(8)], SHIFT)
        self.assertEqual((absent['status'], absent['reason']), ('Absent', 'Giờ làm dưới ngưỡng vắng'))

    def test_single_punch_or_reversed_needs_review_not_a_guess(self):
        for checkins in ([punch(7)], [punch(16, kind='IN'), punch(7, kind='OUT')]):
            row = day_status(DAY, checkins, SHIFT)
            self.assertEqual((row['status'], row['needs_review']), ('', 1))

    def test_no_punch_is_absent_on_working_day_and_nothing_on_holiday(self):
        self.assertEqual(day_status(DAY, [], SHIFT)['status'], 'Absent')
        self.assertEqual(day_status(DAY, [], SHIFT, is_holiday=True)['status'], '')

    def test_overnight_shift_ends_next_day(self):
        night = dict(start_time='22:00', end_time='06:00')
        begin, end = shift_window(DAY, night)
        self.assertEqual(end - begin, timedelta(hours=8))
        row = day_status(DAY, [punch(22), punch(7, day=DAY + timedelta(days=1))], night)
        self.assertEqual((row['working_hours'], row['overtime_hours'], row['status']), (9.0, 1.0, 'Present'))

    def test_no_shift_still_counts_hours(self):
        row = day_status(DAY, [dict(time='2026-10-14 08:00:00'), dict(time='2026-10-14 17:00:00')])
        self.assertEqual((row['status'], row['working_hours'], row['overtime_hours']), ('Present', 9.0, 0))


if __name__ == '__main__':
    unittest.main()
