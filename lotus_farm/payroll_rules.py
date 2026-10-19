"""Monthly pay by working hours (pure, unit-tested in tests/).

The base salary covers 26 workdays of 8 hours, so one hour is base / 208. The same arithmetic is
used by the Lotus payroll sheet and by the HRMS Salary Structure formulas (lotus_farm.hr_payroll),
so the sheet and the salary slips agree. Contractor crew piecework is a payable to the crew,
never an employee wage. Personal income tax is not computed here.
"""
from collections import defaultdict
from datetime import date, datetime, time, timedelta

from lotus_farm.timekeeping_rules import status_days

STANDARD_DAYS = 26
HOURS_PER_DAY = 8
HOURS_BASE = STANDARD_DAYS * HOURS_PER_DAY
# Labour Code 2019 art. 97-98: overtime at least 150% weekday, 200% weekly off, 300% public holiday;
# night work (22:00-06:00) at least 30% extra.
OT_RATES = dict(regular=1.5, weekly_off=2.0, holiday=3.0)
NIGHT_PREMIUM = 0.3
NIGHT_START, NIGHT_END = time(22), time(6)
# Compulsory insurance on the contract salary: employee share and employer share.
EMPLOYEE_INSURANCE = dict(bhxh=0.08, bhyt=0.015, bhtn=0.01)
EMPLOYER_INSURANCE = dict(bhxh=0.175, bhyt=0.03, bhtn=0.01)


def _num(value):
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        return 0.0
    return number if number == number and abs(number) != float('inf') else 0.0


def _day(value):
    return value if isinstance(value, date) and not isinstance(value, datetime) else date.fromisoformat(str(value)[:10])


def _moment(value):
    if not value:
        return None
    return value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace(' ', 'T')[:19])


def _clock(value):
    if value in (None, ''):
        return None
    if isinstance(value, time):
        return value
    if isinstance(value, timedelta):
        seconds = int(value.total_seconds()) % 86400
        return time(seconds // 3600, seconds % 3600 // 60)
    return time(*[int(p) for p in str(value).split(':')[:2]])


def day_kind(day, holidays):
    """holidays: {date: weekly_off flag} from the company Holiday List."""
    if day not in holidays:
        return 'regular'
    return 'weekly_off' if holidays[day] else 'holiday'


def night_hours(start, end):
    """Hours of [start, end] that fall between 22:00 and 06:00."""
    if not start or not end or end <= start:
        return 0.0
    total = 0.0
    day = start.date() - timedelta(days=1)
    while day <= end.date():
        window_start = datetime.combine(day, NIGHT_START)
        window_end = datetime.combine(day + timedelta(days=1), NIGHT_END)
        overlap = (min(end, window_end) - max(start, window_start)).total_seconds()
        if overlap > 0:
            total += overlap / 3600
        day += timedelta(days=1)
    return round(total, 2)


def _shift_span(day, shift):
    start, end = _clock((shift or {}).get('start_time')), _clock((shift or {}).get('end_time'))
    if not start or not end:
        return None, None
    begin, finish = datetime.combine(day, start), datetime.combine(day, end)
    return begin, finish + timedelta(days=1) if finish <= begin else finish


def empty_summary():
    return dict(workdays=0.0, regular_hours=0.0, night_hours=0.0, ot_regular=0.0, ot_weekly_off=0.0, ot_holiday=0.0,
                paid_leave_days=0.0, unpaid_leave_days=0.0, paid_holiday_days=0, absent_days=0, paid_hours=0.0)


def hour_summary(records, holidays, unpaid_leave_types=(), shifts=None, employment=None):
    """Submitted Attendance rows -> per-employee hours for the month.

    records: employee, attendance_date, status, leave_type, working_hours, overtime_hours, in_time, out_time, shift.
    employment: {employee: (first_day, last_day)} inside the month; public holidays in it are paid 8 hours.
    """
    unpaid, shifts = set(unpaid_leave_types), shifts or {}
    days = defaultdict(lambda: defaultdict(list))
    for row in records:
        days[row['employee']][_day(row['attendance_date'])].append(row)
    result = {}
    for employee in set(days) | set(employment or {}):
        total = empty_summary()
        for day, rows in days.get(employee, {}).items():
            kind = day_kind(day, holidays)
            worked = min(1.0, sum(status_days(r.get('status')) for r in rows))
            hours = sum(_num(r.get('working_hours')) for r in rows if status_days(r.get('status')))
            overtime = sum(_num(r.get('overtime_hours')) for r in rows if status_days(r.get('status')))
            if worked and not hours:
                hours = worked * HOURS_PER_DAY
            total['workdays'] += worked
            if kind == 'regular':
                total['regular_hours'] += min(HOURS_PER_DAY * worked, max(0.0, hours - overtime))
                total['ot_regular'] += overtime
            else:
                # Every hour on a weekly off day or public holiday is overtime at that day's rate.
                total['ot_' + kind] += hours
            night = 0.0
            for row in rows:
                if not status_days(row.get('status')):
                    continue
                start, end = _moment(row.get('in_time')), _moment(row.get('out_time'))
                if not (start and end):
                    start, end = _shift_span(day, shifts.get(row.get('shift')))
                night += night_hours(start, end)
            total['night_hours'] += min(night, hours)
            leave = dict(paid=0.0, unpaid=0.0)
            for row in rows:
                status, kind_of_leave = row.get('status'), row.get('leave_type')
                # HRMS marks a half-day leave as Half Day with the leave type set.
                share = 1.0 if status == 'On Leave' else 0.5 if status == 'Half Day' and kind_of_leave else 0.0
                if share:
                    leave['unpaid' if kind_of_leave in unpaid else 'paid'] += share
                if status == 'Absent':
                    total['absent_days'] += 1
            room = 1.0 - worked
            for key in ('paid', 'unpaid'):
                taken = min(room, leave[key])
                total[key + '_leave_days'] += taken
                room -= taken
        first, last = (employment or {}).get(employee, (None, None))
        if first and last:
            total['paid_holiday_days'] = sum(1 for day, weekly in holidays.items() if not weekly and first <= day <= last)
        total['paid_hours'] = (total['paid_leave_days'] + total['paid_holiday_days']) * HOURS_PER_DAY
        result[employee] = {k: round(v, 2) if isinstance(v, float) else v for k, v in total.items()}
    return result


def pay_base(basis, base_salary=0, daily_rate=0):
    """Monthly base for 26 workdays: the contract salary, or the daily rate x 26 for daywork."""
    if basis == 'Daywork':
        return _num(daily_rate) * STANDARD_DAYS
    return _num(base_salary)


def hourly_pay(basis, summary, base_salary=0, daily_rate=0, insured=False):
    """Earnings, employee deductions and employer insurance for one employee, plus data gaps."""
    issues = []
    if not basis:
        issues.append('Chưa chọn cơ chế lương')
    elif basis in ('Monthly', 'Mixed') and _num(base_salary) <= 0:
        issues.append('Thiếu lương cơ bản')
    elif basis == 'Daywork' and _num(daily_rate) <= 0:
        issues.append('Thiếu đơn giá công')
    zero = dict(hour_rate=0, regular_pay=0, paid_pay=0, night_pay=0, overtime_pay=0, gross=0,
                employee_insurance=0, net=0, employer_insurance=0)
    result = dict(zero, base=0, via_crew=basis == 'Piecework', issues=issues)
    if issues or basis == 'Piecework':
        return result
    base = pay_base(basis, base_salary, daily_rate)
    rate = base / HOURS_BASE
    s = summary
    amounts = dict(regular_pay=rate * s.get('regular_hours', 0), paid_pay=rate * s.get('paid_hours', 0),
                   night_pay=rate * s.get('night_hours', 0) * NIGHT_PREMIUM,
                   overtime_pay=rate * sum(OT_RATES[k] * s.get('ot_' + k, 0) for k in OT_RATES))
    amounts = {k: round(v) for k, v in amounts.items()}
    gross = sum(amounts.values())
    employee = sum(round(base * r) for r in EMPLOYEE_INSURANCE.values()) if insured else 0
    employer = sum(round(base * r) for r in EMPLOYER_INSURANCE.values()) if insured else 0
    result.update(amounts, base=round(base), hour_rate=round(rate), gross=gross, employee_insurance=employee,
                  net=gross - employee, employer_insurance=employer)
    return result
