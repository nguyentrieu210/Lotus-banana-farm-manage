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
