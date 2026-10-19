"""Pure aggregations for the /lotus report charts (no Frappe import, unit-tested in tests/).

Inputs are permission-filtered rows from lotus_farm.reporting.charts. Quantities with different
units are never summed together: work completion is averaged per task, workdays are summed.
"""
from collections import defaultdict
from datetime import date, timedelta

from lotus_farm.promax_rules import work_completion

UNZONED = 'Chưa chia khu'
OTHER = 'Khác'


def _num(value):
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        return 0.0
    return number if number == number and abs(number) != float('inf') else 0.0


def _day(value):
    return value if isinstance(value, date) else date.fromisoformat(str(value)[:10])


def week_start(value):
    day = _day(value)
    return day - timedelta(days=day.weekday())


def land_by_zone(blocks):
    zones = defaultdict(lambda: dict(blocks=0, area_ha=0.0, trees=0.0, counted_blocks=0, counted_area_ha=0.0))
    for block in blocks:
        row = zones[(block.get('farm_zone') or '').strip() or UNZONED]
        row['blocks'] += 1
        row['area_ha'] += _num(block.get('area_ha'))
        # A census of 0 means not planted yet (e.g. a zone waiting for its planting slot), not a density of 0.
        if _num(block.get('lotus_tree_count')) > 0:
            row['counted_blocks'] += 1
            row['counted_area_ha'] += _num(block.get('area_ha'))
            row['trees'] += _num(block.get('lotus_tree_count'))
    order = sorted(zones, key=lambda zone: (zone == UNZONED, zone))
    # Density over counted blocks only, so uncounted land does not dilute it.
    return [dict(zone=zone, **zones[zone], trees_per_ha=zones[zone]['trees'] / zones[zone]['counted_area_ha'] if zones[zone]['counted_area_ha'] else None) for zone in order]


def flowering_by_month(blocks):
    months = defaultdict(lambda: dict(blocks=0, trees=0.0))
    for block in blocks:
        flowering = block.get('lotus_estimated_flowering_date')
        if not flowering:
            continue
        row = months[str(flowering)[:7]]
        row['blocks'] += 1
        row['trees'] += _num(block.get('lotus_tree_count'))
    return [dict(month=month, **months[month]) for month in sorted(months)]


def work_by_day(days):
    """days: [(date, tasks)] from daily_overview; every listed day is kept so gaps stay visible."""
    result = []
    for day, tasks in days:
        planned = [t for t in tasks if _num(t.get('planned_qty')) > 0]
        result.append(dict(date=str(_day(day)), tasks=len(tasks), completion_percent=work_completion(planned) if planned else None,
                           required_workdays=sum(_num(t.get('required_workdays')) for t in tasks),
                           actual_workdays=sum(_num(t.get('actual_workdays')) for t in tasks)))
    return result


def work_by_type(tasks, limit=10):
    groups = defaultdict(lambda: dict(required_workdays=0.0, actual_workdays=0.0, tasks=0))
    for task in tasks:
        row = groups[task.get('work_name') or task.get('work_type') or OTHER]
        row['tasks'] += 1
        row['required_workdays'] += _num(task.get('required_workdays'))
        row['actual_workdays'] += _num(task.get('actual_workdays'))
    rows = sorted(groups.items(), key=lambda item: (-item[1]['required_workdays'], item[0]))
    if len(rows) > limit:
        rest = rows[limit - 1:]
        rows = rows[:limit - 1] + [(OTHER, dict(required_workdays=sum(r['required_workdays'] for _, r in rest),
                                                 actual_workdays=sum(r['actual_workdays'] for _, r in rest), tasks=sum(r['tasks'] for _, r in rest)))]
    return [dict(work=name, **values) for name, values in rows]


def weekly(rows, date_key, value_keys, start, end):
    """Sum value_keys per ISO week (Monday) across [start, end], including empty weeks."""
    weeks, cursor, last = {}, week_start(start), week_start(end)
    while cursor <= last:
        weeks[cursor] = {key: 0.0 for key in value_keys}
        cursor += timedelta(days=7)
    for row in rows:
        if not row.get(date_key):
            continue
        bucket = weeks.get(week_start(row[date_key]))
        if bucket is not None:
            for key in value_keys:
                bucket[key] += _num(row.get(key))
    return [dict(week=str(week), **values) for week, values in weeks.items()]


def top_totals(rows, key, value_key, limit=8):
    totals = defaultdict(float)
    for row in rows:
        totals[row.get(key) or OTHER] += _num(row.get(value_key))
    ordered = sorted(totals.items(), key=lambda item: (-item[1], item[0]))
    if len(ordered) > limit:
        ordered = ordered[:limit - 1] + [(OTHER, sum(value for _, value in ordered[limit - 1:]))]
    return [dict(label=label, value=value) for label, value in ordered]


STOCK_TYPES = {'Material Receipt': 'receipt', 'Material Issue': 'issue', 'Material Transfer': 'transfer'}


def stock_by_month(entries):
    months = defaultdict(lambda: dict(receipt=0, issue=0, transfer=0))
    for entry in entries:
        kind = STOCK_TYPES.get(entry.get('stock_entry_type'))
        if kind and entry.get('posting_date'):
            months[str(entry['posting_date'])[:7]][kind] += 1
    return [dict(month=month, **months[month]) for month in sorted(months)]
