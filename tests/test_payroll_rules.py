import unittest
from datetime import date, datetime, timedelta

from lotus_farm import payroll_rules as pr

# October 2026: Sundays 4, 11, 18, 25 are weekly off; the 20th is set as a public holiday for the test.
HOLIDAYS = {date(2026, 10, d): 1 for d in (4, 11, 18, 25)} | {date(2026, 10, 20): 0}
SHIFTS = {'C1': dict(start_time='06:00', end_time='14:00'), 'C3': dict(start_time=timedelta(hours=22), end_time='06:00')}


def att(day, status='Present', **extra):
    return dict(employee='E1', attendance_date=date(2026, 10, day), status=status, **extra)


class PayrollRules(unittest.TestCase):
    def test_night_hours_cross_midnight(self):
        self.assertEqual(pr.night_hours(datetime(2026, 10, 1, 22), datetime(2026, 10, 2, 6)), 8)
        self.assertEqual(pr.night_hours(datetime(2026, 10, 1, 14), datetime(2026, 10, 1, 23)), 1)
        self.assertEqual(pr.night_hours(datetime(2026, 10, 1, 5), datetime(2026, 10, 1, 14)), 1)
        self.assertEqual(pr.night_hours(datetime(2026, 10, 1, 8), datetime(2026, 10, 1, 7)), 0)

    def test_hours_split_by_day_kind_shift_and_overtime(self):
        rows = [att(1, working_hours=9, overtime_hours=1, in_time='2026-10-01 06:00:00', out_time='2026-10-01 15:00:00'),
                att(2, shift='C3', working_hours=8),
                att(5, working_hours=10, overtime_hours=0),
                att(4, working_hours=6),
                att(20, working_hours=8),
                att(6, 'Half Day', working_hours=4),
                att(7, 'On Leave', leave_type='Annual'), att(8, 'On Leave', leave_type='LWP'), att(9, 'Absent')]
        s = pr.hour_summary(rows, HOLIDAYS, {'LWP'}, SHIFTS, {'E1': (date(2026, 10, 1), date(2026, 10, 31))})['E1']
        self.assertEqual(s['regular_hours'], 8 + 8 + 8 + 4, 'a regular day never pays more than 8 ordinary hours')
        self.assertEqual(s['ot_regular'], 1, 'only approved overtime is overtime')
        self.assertEqual((s['ot_weekly_off'], s['ot_holiday']), (6, 8))
        self.assertEqual(s['night_hours'], 8, 'night shift without clock times uses the shift span')
        self.assertEqual((s['paid_leave_days'], s['unpaid_leave_days'], s['absent_days']), (1, 1, 1))
        self.assertEqual(s['paid_holiday_days'], 1, 'public holiday paid; weekly off is not')
        self.assertEqual(s['paid_hours'], 16)
        self.assertEqual(s['workdays'], 5.5)

    def test_employment_window_limits_holiday_pay(self):
        s = pr.hour_summary([], HOLIDAYS, employment={'E9': (date(2026, 10, 21), date(2026, 10, 31))})['E9']
        self.assertEqual((s['paid_holiday_days'], s['paid_hours']), (0, 0))

    def test_hourly_pay_uses_base_over_208_with_legal_rates(self):
        summary = dict(regular_hours=200, paid_hours=8, night_hours=10, ot_regular=2, ot_weekly_off=8, ot_holiday=0)
        pay = pr.hourly_pay('Monthly', summary, base_salary=6_240_000, insured=True)
        self.assertEqual(pay['hour_rate'], 30_000)
        self.assertEqual((pay['regular_pay'], pay['paid_pay'], pay['night_pay']), (6_000_000, 240_000, 90_000))
        self.assertEqual(pay['overtime_pay'], 30_000 * (2 * 1.5 + 8 * 2))
        self.assertEqual(pay['gross'], 6_000_000 + 240_000 + 90_000 + 570_000)
        self.assertEqual(pay['employee_insurance'], round(6_240_000 * 0.105))
        self.assertEqual(pay['net'], pay['gross'] - pay['employee_insurance'])
        self.assertEqual(pay['employer_insurance'], round(6_240_000 * 0.215))

    def test_daywork_base_piecework_and_missing_rates(self):
        daywork = pr.hourly_pay('Daywork', dict(regular_hours=208), daily_rate=250_000)
        self.assertEqual((daywork['base'], daywork['gross'], daywork['employee_insurance']), (6_500_000, 6_500_000, 0))
        piece = pr.hourly_pay('Piecework', dict(regular_hours=100))
        self.assertEqual((piece['gross'], piece['via_crew'], piece['issues']), (0, True, []))
        self.assertEqual(pr.hourly_pay('Daywork', {})['issues'], ['Thiếu đơn giá công'])
        self.assertEqual(pr.hourly_pay('Monthly', {})['issues'], ['Thiếu lương cơ bản'])
        self.assertEqual(pr.hourly_pay('', {})['issues'], ['Chưa chọn cơ chế lương'])


if __name__ == '__main__':
    unittest.main()
