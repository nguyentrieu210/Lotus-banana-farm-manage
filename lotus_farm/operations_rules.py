"""Daily operating calculations, with explicit UOM and no stock ledger."""
from decimal import Decimal, ROUND_CEILING
from lotus_farm.rules import quantity, integer_quantity, RuleError


def material_needed(planned, norm_qty, basis_qty, frequency, conversion_factor):
    return float(quantity(planned) * quantity(norm_qty) / quantity(basis_qty, positive=True)
                 * quantity(frequency, positive=True) * quantity(conversion_factor, positive=True))


def labor_needed(planned, productivity):
    days = quantity(planned) / quantity(productivity, 'Productivity', positive=True)
    return dict(required_workdays=float(days), required_people=int(days.to_integral_value(rounding=ROUND_CEILING)))


def labor_summary(headcount, present, target, workdays, area):
    headcount, present, target = [integer_quantity(v) for v in (headcount, present, target)]
    if present > headcount:
        raise RuleError('Present people cannot exceed headcount.')
    days, area = quantity(workdays), quantity(area)
    return dict(absent=headcount-present, staffing_gap=present-target,
                absence_percent=float(Decimal(headcount-present)/headcount*100) if headcount else 0,
                workdays_per_ha=float(days/area) if area else None)


def remaining_bunches(source, cancellations):
    source = quantity(source)
    lost = sum((quantity(v) for v in cancellations), Decimal(0))
    if lost > source:
        raise RuleError('Cancelled bunches exceed the forecast source; reconcile the source before forecasting.')
    return float(source-lost)


def completion(planned, completed, reason):
    planned, completed = quantity(planned), quantity(completed)
    unfinished = max(planned-completed, Decimal(0))
    if unfinished and not (reason or '').strip():
        raise RuleError('Unfinished work requires a reason.')
    return float(unfinished)
