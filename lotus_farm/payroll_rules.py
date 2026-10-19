"""Monthly payroll sheet arithmetic (pure, unit-tested in tests/).

The sheet is handed to accounting: amounts are gross before social insurance and personal
income tax. Contractor crew piecework is a payable to the crew, never an employee wage.
"""
from collections import defaultdict
from datetime import date

from lotus_farm.timekeeping_rules import status_days

# Labour Code 2019 art. 98: at least 150% weekday, 200% weekly off, 300% public holiday.
OT_RATES = dict(regular=1.5, weekly_off=2.0, holiday=3.0)
HOURS_PER_DAY = 8


def _num(value):
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        return 0.0
    return number if number == number and abs(number) != float('inf') else 0.0


def _day(value):
    return value if isinstance(value, date) else date.fromisoformat(str(value)[:10])


def day_kind(day, holidays):
    """holidays: {date: weekly_off flag} from the company Holiday List."""
    if day not in holidays:
        return 'regular'
    return 'weekly_off' if holidays[day] else 'holiday'


def standard_days(begin, end, holidays):
    """Working days in [begin, end] that are neither weekly off nor public holiday."""
    return sum(1 for n in range((end - begin).days + 1) if date.fromordinal(begin.toordinal() + n) not in holidays)


def summarize_attendance(records, holidays, unpaid_leave_types=()):
    """Submitted Attendance rows -> per-employee day counts. One calendar day never exceeds one workday."""
    unpaid = set(unpaid_leave_types)
    days = defaultdict(lambda: defaultdict(list))
    for row in records:
        days[row['employee']][_day(row['attendance_date'])].append(row)
    result = {}
    for employee, by_day in days.items():
        total = dict(regular=0.0, weekly_off=0.0, holiday=0.0, paid_leave=0.0, unpaid_leave=0.0, absent=0.0, half_days=0,
                     overtime=dict(regular=0.0, weekly_off=0.0, holiday=0.0))
        for day, rows in by_day.items():
            kind = day_kind(day, holidays)
            worked = min(1.0, sum(status_days(r.get('status')) for r in rows))
            total[kind] += worked
            leave_day = dict(paid_leave=0.0, unpaid_leave=0.0)
            for row in rows:
                status, leave = row.get('status'), row.get('leave_type')
                if status == 'Half Day':
                    total['half_days'] += 1
                # HRMS marks a half-day leave as Half Day with the leave type set.
                share = 1.0 if status == 'On Leave' else 0.5 if status == 'Half Day' and leave else 0.0
                if share:
                    leave_day['unpaid_leave' if leave in unpaid else 'paid_leave'] += share
                if status == 'Absent':
                    total['absent'] += 1
                total['overtime'][kind] += max(0.0, _num(row.get('overtime_hours')))
            room = 1.0 - worked
            for key in ('paid_leave', 'unpaid_leave'):
                taken = min(room, leave_day[key])
                total[key] += taken
                room -= taken
        result[employee] = total
    return result


def employee_pay(basis, summary, standard, base_salary=0, daily_rate=0):
    """Gross pay for one employee and the data gaps that block a correct figure."""
    base, rate = _num(base_salary), _num(daily_rate)
    regular, off, holiday = summary.get('regular', 0), summary.get('weekly_off', 0), summary.get('holiday', 0)
    pay_days = regular + summary.get('paid_leave', 0)
    issues = []
    if not basis:
        issues.append('Chưa chọn cơ chế lương')
    if basis in ('Monthly', 'Mixed') and base <= 0:
        issues.append('Thiếu lương cơ bản')
    if basis in ('Daywork', 'Mixed') and rate <= 0:
        issues.append('Thiếu đơn giá công')
    if basis in ('Monthly', 'Mixed') and standard <= 0:
        issues.append('Chưa có công chuẩn (lịch nghỉ)')
    result = dict(pay_days=pay_days, daily_wage=0.0, time_pay=0.0, off_day_pay=0.0, overtime_pay=0.0, total=0.0,
                  via_crew=basis == 'Piecework', issues=issues)
    if issues or basis == 'Piecework':
        return result
    if basis == 'Daywork':
        daily = rate
        time_pay = pay_days * rate
    else:
        daily = base / standard
        time_pay = base * min(pay_days, standard) / standard
        if basis == 'Mixed':
            daily = rate
            time_pay += max(0.0, pay_days - standard) * rate
    off_day_pay = daily * (off * OT_RATES['weekly_off'] + holiday * OT_RATES['holiday'])
    hourly = daily / HOURS_PER_DAY
    overtime = summary.get('overtime', {})
    overtime_pay = sum(hourly * OT_RATES[kind] * _num(overtime.get(kind)) for kind in OT_RATES)
    result.update(daily_wage=round(daily), time_pay=round(time_pay), off_day_pay=round(off_day_pay),
                  overtime_pay=round(overtime_pay))
    result['total'] = result['time_pay'] + result['off_day_pay'] + result['overtime_pay']
    return result
