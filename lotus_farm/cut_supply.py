"""Physical cut supply distributed over its window, independent of Frappe.

Consumption belongs to the cut, not to a particular forecast document. Calendar
capacity never moves when another forecast is published or withdrawn.
"""
import math
from datetime import timedelta
from lotus_farm.onedrive_protocol import as_date


def window_balance(start, end, quantity, events=()):
    start, end = as_date(start), as_date(end)
    quantity = float(quantity)
    if end < start or (end-start).days > 366 or not math.isfinite(quantity) or quantity < 0:
        raise ValueError('Cửa sổ hoặc số buồng nguồn không hợp lệ.')
    count = (end-start).days+1
    days = {str(start+timedelta(days=n)): quantity/count for n in range(count)}
    allocations = {}
    consumed = 0.0
    for event in sorted(events, key=lambda e: (str(e['date']), e['key'])):
        qty = float(event['quantity'])
        if not math.isfinite(qty) or qty < 0 or consumed+qty > quantity+0.000001:
            raise ValueError('Số buồng đã thu/hủy vượt số buồng nguồn.')
        consumed += qty
        month = str(as_date(event['date']))[:7]
        ordered = sorted(days, key=lambda day: (day[:7] != month, day))
        assigned = {}
        for day in ordered:
            take = min(days[day], qty)
            if take > 0:
                days[day] -= take
                assigned[day] = take
                qty -= take
            if qty <= 0.00000001:
                break
        allocations[event['key']] = assigned
    return dict(start=str(start), end=str(end), capacity=quantity, days=days,
                events=allocations, remaining=max(quantity-consumed, 0))


def interval_quantity(balance, start, end, event=None):
    start, end = str(as_date(start)), str(as_date(end))
    values = balance['events'].get(event, {}) if event else balance['days']
    return sum(qty for day, qty in values.items() if start <= day <= end)


def overlaps(start, end, other_start, other_end):
    return as_date(start) <= as_date(other_end) and as_date(other_start) <= as_date(end)
