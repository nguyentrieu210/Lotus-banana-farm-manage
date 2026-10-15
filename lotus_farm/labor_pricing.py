"""Pure labor configuration and planning rules; no payroll entries are created here."""
import math


def positive_number(value, label, allow_zero=False):
    try:
        number = float(value or 0)
    except (ValueError, TypeError, OverflowError):
        raise ValueError(f'{label} phải là số hợp lệ.')
    if not math.isfinite(number) or number < 0 or (not allow_zero and number == 0):
        raise ValueError(f'{label} phải là số dương và hữu hạn.' if not allow_zero else f'{label} không được âm.')
    return number


def labor_settings(allow_daywork, allow_piecework, productivity, piecework_rate, mode=None):
    daywork = bool(int(allow_daywork or 0))
    piecework = bool(int(allow_piecework or 0))
    # Old work types without the switches retain daywork behavior for compatibility.
    if not daywork and not piecework and mode is None:
        daywork = True
    if mode is None or mode == '':
        mode = 'Both' if daywork and piecework else 'Piece' if piecework else 'Daywork'
    if mode not in ('Daywork', 'Piece', 'Both'):
        raise ValueError('Hình thức công không hợp lệ.')
    if mode in ('Daywork', 'Both') and not daywork:
        raise ValueError('Công việc không cho phép công nhật.')
    if mode in ('Piece', 'Both') and not piecework:
        raise ValueError('Công việc không cho phép công khoán.')
    # Work output per labor-day is needed for capacity planning even when the team is paid by piece.
    # The chosen payment mode controls *money*, not the physical productivity estimate.
    productivity = positive_number(productivity, 'Năng suất trung bình (đơn vị/công)')
    rate = positive_number(piecework_rate, 'Đơn giá khoán') if mode in ('Piece', 'Both') else 0
    return dict(mode=mode, productivity=productivity, piecework_rate=rate)


def planned_labor(qty, settings):
    qty = positive_number(qty, 'Sản lượng giao')
    return dict(required_workdays=round(qty/settings['productivity'],6) if settings['productivity'] else 0,
                estimated_piecework_amount=round(qty*settings['piecework_rate'],2) if settings['piecework_rate'] else 0)
