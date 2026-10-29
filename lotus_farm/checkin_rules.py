"""Proposed attendance from device check-ins (pure, unit-tested in tests/).

A proposal never becomes Attendance by itself: the manager reviews it in /lotus/cham-cong,
saves it as a draft and submits it. Missing punches are flagged instead of guessed.
"""
from datetime import datetime, time, timedelta


def _clock(value):
    """Frappe returns Time fields as timedelta; the UI sends 'HH:MM[:SS]'."""
    if value in (None, ''):
        return None
    if isinstance(value, time):
        return value
    if isinstance(value, timedelta):
        seconds = int(value.total_seconds()) % 86400
        return time(seconds // 3600, seconds % 3600 // 60, seconds % 60)
    parts = [int(p) for p in str(value).split(':')[:3]]
    return time(*parts)


def _moment(value):
    return value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace(' ', 'T')[:19])


def _hours(delta):
    return round(delta.total_seconds() / 3600, 2)


def shift_window(day, shift):
    """Shift start/end datetimes for the attendance day; an end at or before the start runs past midnight."""
    start, end = _clock((shift or {}).get('start_time')), _clock((shift or {}).get('end_time'))
    if not start or not end:
        return None, None
    begin = datetime.combine(day, start)
    finish = datetime.combine(day, end)
    if finish <= begin:
        finish += timedelta(days=1)
    return begin, finish


def day_status(day, checkins, shift=None, is_holiday=False):
    shift = shift or {}
    result = dict(status='', working_hours=0, in_time=None, out_time=None, late_entry=0, early_exit=0,
                  overtime_hours=0, needs_review=0, reason='')
    punches = sorted(((_moment(c['time']), (c.get('log_type') or '').upper()) for c in checkins), key=lambda p: p[0])
    if not punches:
        if is_holiday:
            result['reason'] = 'Ngày nghỉ'
        else:
            result.update(status='Absent', reason='Không có lượt chấm')
        return result
    if len(punches) == 1:
        result.update(in_time=punches[0][0], needs_review=1, reason='Thiếu lượt chấm')
        return result
    ins = [t for t, kind in punches if kind == 'IN']
    outs = [t for t, kind in punches if kind == 'OUT']
    labelled = any(kind for _, kind in punches)
    if labelled and (not ins or not outs or any(kind and kind not in ('IN', 'OUT') for _, kind in punches)):
        result.update(in_time=ins[0] if ins else None, out_time=outs[-1] if outs else None,
                      needs_review=1, reason='Thiếu cặp lượt vào/ra hợp lệ')
        return result
    if labelled and (punches[0][1] != 'IN' or punches[-1][1] != 'OUT'):
        result.update(in_time=ins[0], out_time=outs[-1], needs_review=1, reason='Thứ tự lượt vào/ra không hợp lệ')
        return result
    # Without IN/OUT labels the first punch opens and the last one closes the day.
    first_in = min(ins) if ins else punches[0][0]
    last_out = max(outs) if outs else punches[-1][0]
    if last_out <= first_in:
        result.update(in_time=first_in, needs_review=1, reason='Lượt ra trước lượt vào')
        return result
    hours = _hours(last_out - first_in)
    result.update(in_time=first_in, out_time=last_out, working_hours=hours)
    absent_below = float(shift.get('working_hours_threshold_for_absent') or 0)
    half_below = float(shift.get('working_hours_threshold_for_half_day') or 0)
    if absent_below and hours < absent_below:
        result.update(status='Absent', reason='Giờ làm dưới ngưỡng vắng')
    elif half_below and hours < half_below:
        result['status'] = 'Half Day'
    else:
        result['status'] = 'Present'
    begin, finish = shift_window(day, shift)
    if begin:
        late_grace = timedelta(minutes=int(shift.get('late_entry_grace_period') or 0))
        early_grace = timedelta(minutes=int(shift.get('early_exit_grace_period') or 0))
        result['late_entry'] = int(first_in > begin + late_grace)
        result['early_exit'] = int(last_out < finish - early_grace)
        result['overtime_hours'] = max(0, _hours(last_out - finish))
    return result
