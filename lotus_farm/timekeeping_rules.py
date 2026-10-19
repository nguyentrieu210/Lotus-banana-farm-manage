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
