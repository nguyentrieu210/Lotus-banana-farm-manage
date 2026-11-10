"""Pure labor configuration rules of a work type; no payroll entries are created here."""
import math


def positive_number(value, label):
    try:
        number = float(value or 0)
    except (ValueError, TypeError, OverflowError):
        raise ValueError(f'{label} phải là số hợp lệ.')
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f'{label} phải là số dương và hữu hạn.')
    return number


def labor_settings(allow_daywork, allow_piecework, productivity, piecework_rate):
    daywork = bool(int(allow_daywork or 0))
    piecework = bool(int(allow_piecework or 0))
    # Old work types without the switches retain daywork behavior for compatibility.
    if not daywork and not piecework:
        daywork = True
    mode = 'Both' if daywork and piecework else 'Piece' if piecework else 'Daywork'
    # Work output per labor-day is needed for capacity planning even when the team is paid by piece.
    # The payment mode controls *money*, not the physical productivity estimate.
    productivity = positive_number(productivity, 'Năng suất trung bình (đơn vị/công)')
    rate = positive_number(piecework_rate, 'Đơn giá khoán') if piecework else 0
    return dict(mode=mode, productivity=productivity, piecework_rate=rate)
