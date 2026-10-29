"""Monthly pay by working hours (pure, unit-tested in tests/).

The base salary covers 26 workdays of 8 hours, so one hour is base / 208. The same arithmetic is
used by the Lotus payroll sheet and by the HRMS Salary Structure formulas (lotus_farm.hr_payroll),
so the sheet and the salary slips agree. Contractor crew piecework is a payable to the crew,
never an employee wage. With the statutory parameters (data/payroll_vn.json, by effective date) the
insurance bases are capped, the employer's union fee (KPCĐ) and personal income tax are computed.
"""
import json
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path

from lotus_farm.timekeeping_rules import status_days

PARAMS_FILE = Path(__file__).resolve().parent / 'data' / 'payroll_vn.json'

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


def rate_in_force(rows, on_date):
    """The rate of the latest row (dicts with valid_from, rate) whose valid_from is on or before on_date, else 0."""
    day = _day(on_date)
    found = None
    for row in rows or []:
        start = _day(row['valid_from'])
        if start <= day and (found is None or start > _day(found['valid_from'])):
            found = row
    return _num(found['rate']) if found else 0.0


def allowance_amount(rate, workdays):
    """Phụ cấp công việc for one day: the full rate for a whole day present, half of it for one session (buổi)."""
    days = min(max(_num(workdays), 0.0), 1.0)
    return round(_num(rate) * days) if days else 0


def load_params(path=PARAMS_FILE):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def effective(rows, on_date):
    """The latest confirmed row with from <= on_date (rows marked confirmed=false are never applied)."""
    day = str(on_date)[:10]
    rows = sorted((r for r in rows or [] if r.get('confirmed', True) and str(r['from']) <= day), key=lambda r: r['from'])
    return rows[-1] if rows else None


def params_on(on_date, data=None):
    """Statutory parameters for a pay month: dict(pit, flat, insurance) or None where nothing applies yet."""
    data = data or load_params()
    return dict(pit=effective(data.get('pit_progressive'), on_date), flat=effective(data.get('pit_flat'), on_date),
                insurance=effective(data.get('insurance'), on_date))


def progressive_tax(taxable, brackets):
    """Tax on the monthly taxable income by the progressive brackets [[upper or None, rate], ...]."""
    taxable, tax, lower = max(0.0, _num(taxable)), 0.0, 0.0
    for upper, rate in brackets:
        top = taxable if upper is None else min(taxable, float(upper))
        if top > lower:
            tax += (top - lower) * rate
        if upper is None or taxable <= upper:
            break
        lower = float(upper)
    return round(tax)


def tax_method(category, months_of_contract=None):
    """'progressive' for employees on a labour contract of 3 months or more, 'flat' (10% at source) for
    seasonal / probation workers and contracts shorter than 3 months."""
    if category in ('Seasonal', 'Probation'):
        return 'flat'
    if months_of_contract is not None and months_of_contract < 3:
        return 'flat'
    return 'progressive' if category in ('Permanent', 'Fixed-term') else 'flat'


def contributions(base, insurance, region=None):
    """Compulsory insurance on the contract salary, capped: BHXH and BHYT at cap_multiple x base salary, BHTN at
    cap_multiple x regional minimum wage. Returns employee and employer parts and the union fee (2% of the BHXH base)."""
    base = _num(base)
    cap = insurance['cap_multiple'] * insurance['base_salary']
    regional = (insurance.get('regional_minimum') or {}).get(region or '')
    bases = dict(bhxh=min(base, cap), bhyt=min(base, cap), bhtn=min(base, insurance['cap_multiple'] * regional) if regional else base)
    employee = {k: round(bases[k] * r) for k, r in insurance['employee'].items()}
    employer = {k: round(bases[k] * r) for k, r in insurance['employer'].items()}
    return dict(employee=employee, employer=employer, union_fee=round(bases['bhxh'] * insurance.get('union_fee', 0)),
                capped=base > cap or (regional and base > insurance['cap_multiple'] * regional))


def income_tax(gross, exempt, employee_insurance, method, params, dependents=0, commitment=False):
    """Personal income tax withheld this month.

    progressive: (gross - exempt overtime / night premium - employee insurance - self - dependents) by the brackets.
    flat: 10% of the payment when it reaches the threshold, unless the worker filed the 08/CK-TNCN commitment.
    """
    if method == 'progressive' and params.get('pit'):
        p = params['pit']
        taxable = max(0, round(_num(gross) - _num(exempt) - _num(employee_insurance) - p['self'] - p['dependent'] * max(0, int(dependents or 0))))
        return dict(pit=progressive_tax(taxable, p['brackets']), taxable_income=taxable, pit_method='progressive')
    if method == 'flat' and params.get('flat'):
        f = params['flat']
        payment = max(0, round(_num(gross) - _num(employee_insurance)))
        due = payment >= f['threshold'] and not commitment
        return dict(pit=round(payment * f['rate']) if due else 0, taxable_income=payment if due else 0,
                    pit_method='commitment' if commitment and payment >= f['threshold'] else 'flat')
    return dict(pit=0, taxable_income=0, pit_method=method or '')


def hourly_pay(basis, summary, base_salary=0, daily_rate=0, insured=False, params=None, region=None, tax=None):
    """Earnings, employee deductions and employer insurance for one employee, plus data gaps.

    params (params_on) switches on the capped insurance, the union fee and the income tax; tax = dict(method,
    dependents, commitment) of the employee. Without params the old arithmetic applies (no cap, no tax)."""
    issues = []
    if not basis:
        issues.append('Chưa chọn cơ chế lương')
    elif basis in ('Monthly', 'Mixed') and _num(base_salary) <= 0:
        issues.append('Thiếu lương cơ bản')
    elif basis == 'Daywork' and _num(daily_rate) <= 0:
        issues.append('Thiếu đơn giá công')
    zero = dict(hour_rate=0, regular_pay=0, paid_pay=0, night_pay=0, overtime_pay=0, gross=0,
                employee_insurance=0, net=0, employer_insurance=0, union_fee=0, pit=0, taxable_income=0, pit_exempt=0,
                pit_method='', insurance_parts=None)
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
    if not params:
        employee = sum(round(base * r) for r in EMPLOYEE_INSURANCE.values()) if insured else 0
        employer = sum(round(base * r) for r in EMPLOYER_INSURANCE.values()) if insured else 0
        result.update(amounts, base=round(base), hour_rate=round(rate), gross=gross, employee_insurance=employee,
                      net=gross - employee, employer_insurance=employer)
        return result
    parts = contributions(base, params['insurance'], region) if insured and params.get('insurance') else None
    employee = sum(parts['employee'].values()) if parts else 0
    employer = sum(parts['employer'].values()) if parts else 0
    # Personal income tax does not apply to the premium part of overtime and night work (Luật Thuế TNCN, miễn thuế).
    exempt = amounts['night_pay'] + max(0, amounts['overtime_pay'] - round(rate * sum(s.get('ot_' + k, 0) for k in OT_RATES)))
    tax = tax or {}
    withheld = income_tax(gross, exempt, employee, tax.get('method'), params, tax.get('dependents'), tax.get('commitment'))
    result.update(amounts)
    result.update(withheld, base=round(base), hour_rate=round(rate), gross=gross, employee_insurance=employee,
                  employer_insurance=employer, union_fee=parts['union_fee'] if parts else 0, pit_exempt=exempt,
                  insurance_parts=dict(employee=parts['employee'], employer=parts['employer']) if parts else None,
                  net=gross - employee - withheld['pit'])
    return result


def salary_segments(rows, begin, end, fallback=None):
    """Effective salary intervals. A future assignment never supplies an earlier day's wage."""
    rows=sorted(rows,key=lambda r:(_day(r['from_date']),str(r.get('name') or '')))
    if not rows and fallback:
        rows=[fallback]
    starts=sorted({begin}|{_day(r['from_date']) for r in rows if begin<_day(r['from_date'])<=end})
    result=[]
    for index,start in enumerate(starts):
        hit=next((r for r in reversed(rows) if _day(r['from_date'])<=start),None)
        result.append(dict(start=start,end=starts[index+1]-timedelta(days=1) if index+1<len(starts) else end,
            base=_num(hit.get('base')) if hit else 0,basis=(hit.get('lotus_payment_basis') or 'Monthly') if hit else 'Monthly',
            source=hit.get('name') if hit else None,missing=hit is None))
    return result


def segmented_pay(segments, insured=False, params=None, region=None, tax=None):
    """Earn each interval at its effective rate; deduct monthly insurance and tax once."""
    if not segments:return hourly_pay('',empty_summary())
    last=segments[-1]
    result=hourly_pay(last['basis'],empty_summary(),last['base'],last['base']/STANDARD_DAYS,
        insured=insured,params=params,region=region,tax=tax)
    earnings={k:0 for k in ('regular_pay','paid_pay','night_pay','overtime_pay')}
    issues=[];exempt=0
    for segment in segments:
        pay=hourly_pay(segment['basis'],segment['summary'],segment['base'],segment['base']/STANDARD_DAYS)
        for key in earnings:earnings[key]+=pay[key]
        issues.extend(pay['issues'])
        if segment.get('missing'):issues.append('Thiếu mức lương có hiệu lực từ '+str(segment['start'])+' đến '+str(segment['end']))
        hours=segment['summary'];rate=segment['base']/HOURS_BASE
        exempt+=pay['night_pay']+max(0,pay['overtime_pay']-round(rate*sum(hours.get('ot_'+k,0) for k in OT_RATES)))
    gross=sum(earnings.values());employee=result['employee_insurance']
    withheld=income_tax(gross,exempt,employee,(tax or {}).get('method'),params or {},(tax or {}).get('dependents'),(tax or {}).get('commitment'))
    result.update(earnings)
    result.update(withheld,gross=gross,net=gross-employee-withheld['pit'],pit_exempt=exempt,
        via_crew=all(s['basis']=='Piecework' for s in segments),issues=list(dict.fromkeys(issues)),
        rate_history=[dict(start=str(s['start']),end=str(s['end']),base=s['base'],basis=s['basis'],source=s['source']) for s in segments])
    return result
