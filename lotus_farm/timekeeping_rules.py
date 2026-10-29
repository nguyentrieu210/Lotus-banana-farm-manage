"""Attendance evidence stays separate from wages and contractor payables."""
import math


def crew_values(headcount,present,workdays,qty=0,rate=0):
    values=[float(v or 0) for v in (headcount,present,workdays,qty,rate)]
    if any(not math.isfinite(v) or v<0 for v in values):raise ValueError('Số liệu công phải là số không âm, hữu hạn.')
    total,attended,days,quantity,price=values
    if total!=int(total) or attended!=int(attended):raise ValueError('Số người phải là số nguyên.')
    if attended>total:raise ValueError('Số có mặt không được vượt tổng người.')
    if days>attended:raise ValueError('Tổng công không được vượt số người có mặt trong ngày.')
    if not math.isfinite(quantity*price):raise ValueError('Giá trị khoán vượt giới hạn hợp lệ.')
    return dict(headcount=int(total),present=int(attended),absent=int(total-attended),workdays=days,completed_qty=quantity,unit_rate=price,amount=round(quantity*price,2))


def status_days(status):
    return {'Present':1,'Work From Home':1,'Half Day':0.5}.get(status,0)


def employed_on(person, day):
    day = _as_date(day)
    joined, left = _as_date(person.get('date_of_joining')), _as_date(person.get('relieving_date'))
    return (person.get('status') in ('Active', 'Left') and (not joined or joined <= day)
            and (not left or day <= left) and (person.get('status') != 'Left' or bool(left)))


def attendance_key(employee, shift=None):
    return str(employee) + '::' + str(shift or '')


def month_range(month):
    """'YYYY-MM' -> (first day, last day); anything else raises ValueError."""
    import calendar
    from datetime import date
    text=str(month or '')
    if len(text)!=7 or text[4]!='-':raise ValueError('Tháng cần ở dạng YYYY-MM.')
    year,number=int(text[:4]),int(text[5:])
    if not 1<=number<=12:raise ValueError('Tháng cần ở dạng YYYY-MM.')
    return date(year,number,1),date(year,number,calendar.monthrange(year,number)[1])


# Solar public holidays (Labour Code 2019 art. 112). Lunar Tết, Hùng Kings day and the day next to 2/9
# change every year and are added by the manager when the calendar is set up.
VN_FIXED_HOLIDAYS=((1,1,'Tết Dương lịch'),(4,30,'Ngày Chiến thắng'),(5,1,'Quốc tế Lao động'),(9,2,'Quốc khánh'))
WEEKDAYS=('Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday')


def calendar_days(year,weekly_off=('Sunday',),extra=()):
    """Holiday List rows for a year: [(date, description, weekly_off)], one row per date, sorted."""
    from datetime import date,timedelta
    off={WEEKDAYS.index(day) for day in weekly_off}
    rows={}
    cursor=date(year,1,1)
    while cursor.year==year:
        if cursor.weekday() in off:rows[cursor]=(WEEKDAYS[cursor.weekday()],1)
        cursor+=timedelta(days=1)
    for month,day,label in VN_FIXED_HOLIDAYS:rows[date(year,month,day)]=(label,0)
    for value,label in extra:
        day=value if isinstance(value,date) else date.fromisoformat(str(value)[:10])
        if day.year!=year:raise ValueError('Ngày lễ phải thuộc năm '+str(year)+'.')
        rows[day]=(str(label or 'Nghỉ lễ')[:140],0)
    return [(day,label,flag) for day,(label,flag) in sorted(rows.items())]


def missing_attendance(people,records,begin,end,holidays,today):
    """Active employees with no Attendance on a working day up to today: {employee: [dates]}."""
    from datetime import date,timedelta
    seen={(r['employee'],str(r['attendance_date'])[:10]) for r in records}
    last=min(end,today)
    result={}
    for person in people:
        start=max(begin,_as_date(person.get('date_of_joining')) or begin)
        stop=min(last,_as_date(person.get('relieving_date')) or last)
        day=start
        while day<=stop:
            if day not in holidays and (person['name'],str(day)) not in seen:result.setdefault(person['name'],[]).append(day)
            day+=timedelta(days=1)
    return result


def _as_date(value):
    from datetime import date
    if not value:return None
    return value if isinstance(value,date) else date.fromisoformat(str(value)[:10])


def close_blockers(draft_attendance=0,draft_crew=0,open_punches=0,missing=None,has_calendar=True):
    """Reasons a timekeeping month cannot be closed; empty means it can."""
    missing=missing or {}
    rows=[]
    if not has_calendar:rows.append(dict(code='calendar',label='Công ty chưa có lịch nghỉ cho tháng này',count=1))
    if draft_attendance:rows.append(dict(code='draft_attendance',label='Phiếu công nhân sự còn nháp',count=draft_attendance))
    if draft_crew:rows.append(dict(code='draft_crew',label='Phiếu công đội khoán còn nháp',count=draft_crew))
    if open_punches:rows.append(dict(code='open_punches',label='Lượt chấm máy chưa đối chiếu',count=open_punches))
    if missing:rows.append(dict(code='missing_attendance',label='Nhân viên thiếu công ngày làm việc',count=sum(len(v) for v in missing.values()),employees=sorted(missing)))
    return rows


# Shift administration ---------------------------------------------------------------------------
SHIFT_MANAGER_ROLES = ('System Manager', 'HR Manager')


def can_manage_shifts(roles, user):
    """Administrator, System Manager and HR Manager define shifts, change rosters and correct approved days."""
    return user == 'Administrator' or bool(set(SHIFT_MANAGER_ROLES) & set(roles or ()))


def plan_roster(existing, begin, end, shift):
    """Put one employee on `shift` (None = no shift) for [begin, end] (end None = open-ended).

    existing: active submitted assignments [dict(name, shift_type, start_date, end_date|None)].
    Returns dict(end=[(name, new_end)], cancel=[name], create=[(shift, start, end|None)]): submitted
    assignments cannot move their start, so an overlap starting inside the range is cancelled and
    whatever lies outside the range is recreated.
    """
    from datetime import timedelta
    if end is not None and end < begin:
        raise ValueError('Ngày kết thúc phải sau ngày bắt đầu.')
    plan = dict(end=[], cancel=[], create=[])
    far = None
    for row in sorted(existing, key=lambda r: r['start_date']):
        start, stop = row['start_date'], row.get('end_date')
        if (end is not None and start > end) or (stop is not None and stop < begin):
            continue
        if row['shift_type'] == shift and start <= begin and (stop is None or (end is not None and stop >= end)):
            return dict(end=[], cancel=[], create=[])  # already on that shift for the whole range
        tail = None
        if end is not None and (stop is None or stop > end):
            tail = (row['shift_type'], end + timedelta(days=1), stop)
        if start < begin:
            plan['end'].append((row['name'], begin - timedelta(days=1)))
            if tail:
                plan['create'].append(tail)
        else:
            plan['cancel'].append(row['name'])
            if tail:
                plan['create'].append(tail)
    if shift:
        plan['create'].append((shift, begin, end))
    return plan


def rotation(start, weeks, pattern):
    """Weekly rotation blocks: pattern ['Ca 1','Ca 2','Ca 3'] from `start` -> [(shift, from, to)] per week."""
    from datetime import timedelta
    if not pattern or not 1 <= int(weeks) <= 26:
        raise ValueError('Chọn mẫu ca và 1–26 tuần.')
    return [(pattern[i % len(pattern)], start + timedelta(days=7 * i), start + timedelta(days=7 * i + 6)) for i in range(int(weeks))]


def overtime_suggestion(minutes_after_end, minimum=30, step=15):
    """Overtime proposed from the last punch: nothing below `minimum` minutes, rounded down to `step`."""
    minutes = max(0, int(minutes_after_end or 0))
    if minutes < minimum:
        return 0
    return round((minutes // step) * step / 60, 2)
