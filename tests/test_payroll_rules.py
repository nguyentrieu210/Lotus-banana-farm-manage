import unittest
from datetime import date

from lotus_farm import payroll_rules as pr

# October 2026: Sundays 4, 11, 18, 25 are weekly off; the 20th is set as a holiday for the test.
HOLIDAYS = {date(2026, 10, d): 1 for d in (4, 11, 18, 25)} | {date(2026, 10, 20): 0}
BEGIN, END = date(2026, 10, 1), date(2026, 10, 31)


def att(day, status='Present', **extra):
    return dict(employee='E1', attendance_date=date(2026, 10, day), status=status, **extra)


class PayrollRules(unittest.TestCase):
    def test_standard_days_skip_weekly_off_and_holidays(self):
        self.assertEqual(pr.standard_days(BEGIN, END, HOLIDAYS), 26)

    def test_summary_splits_day_kinds_caps_a_day_and_counts_leave(self):
        rows = [att(1), att(1), att(2, 'Half Day', leave_type='Annual'), att(3, 'On Leave', leave_type='LWP'),
                att(5, 'On Leave', leave_type='Annual'), att(6, 'Absent'), att(11, overtime_hours=2), att(20), att(7, overtime_hours=1.5)]
        s = pr.summarize_attendance(rows, HOLIDAYS, unpaid_leave_types={'LWP'})['E1']
        self.assertEqual((s['regular'], s['weekly_off'], s['holiday']), (2.5, 1, 1), 'two shifts on the 1st still make one workday')
        self.assertEqual((s['paid_leave'], s['unpaid_leave'], s['absent'], s['half_days']), (1.5, 1, 1, 1))
        self.assertEqual(s['overtime'], dict(regular=1.5, weekly_off=2.0, holiday=0.0))

    def test_monthly_prorates_and_pays_off_days_and_overtime_at_legal_rates(self):
        summary = dict(regular=24, paid_leave=1, weekly_off=1, holiday=0, overtime=dict(regular=2, weekly_off=0, holiday=0))
        pay = pr.employee_pay('Monthly', summary, 26, base_salary=7_800_000)
        self.assertEqual(pay['daily_wage'], 300_000)
        self.assertEqual(pay['time_pay'], 7_500_000)
        self.assertEqual(pay['off_day_pay'], 600_000)
        self.assertEqual(pay['overtime_pay'], round(300_000 / 8 * 1.5 * 2))
        self.assertEqual(pay['total'], 7_500_000 + 600_000 + 112_500)
        full = pr.employee_pay('Monthly', dict(regular=30), 26, base_salary=7_800_000)
        self.assertEqual(full['time_pay'], 7_800_000, 'monthly salary never exceeds base for regular days')

    def test_daywork_mixed_piecework_and_missing_data(self):
        self.assertEqual(pr.employee_pay('Daywork', dict(regular=20, holiday=1), 26, daily_rate=250_000)['total'], 20 * 250_000 + 750_000)
        mixed = pr.employee_pay('Mixed', dict(regular=28), 26, base_salary=5_200_000, daily_rate=220_000)
        self.assertEqual(mixed['time_pay'], 5_200_000 + 2 * 220_000)
        piece = pr.employee_pay('Piecework', dict(regular=20), 26)
        self.assertEqual((piece['total'], piece['via_crew'], piece['issues']), (0, True, []))
        self.assertEqual(pr.employee_pay('Daywork', dict(regular=5), 26)['issues'], ['Thiếu đơn giá công'])
        self.assertEqual(pr.employee_pay('Monthly', dict(regular=5), 0, base_salary=1)['issues'], ['Chưa có công chuẩn (lịch nghỉ)'])
        self.assertEqual(pr.employee_pay('', dict(regular=5), 26)['issues'], ['Chưa chọn cơ chế lương'])


if __name__ == '__main__':
    unittest.main()
