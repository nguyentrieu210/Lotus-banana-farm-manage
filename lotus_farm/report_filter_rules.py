"""Filters of the work reports, in the manner of an Excel pivot: each field offers the values still possible given the other fields. Pure: no Frappe, no database."""
import datetime as dt

TIME_FIELDS = ("year", "month", "week", "day")


def _day(value):
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])


def date_facts(value):
    day = _day(value)
    iso = day.isocalendar()
    return {"year": str(iso[0]), "month": day.strftime("%Y-%m"), "week": f"{iso[0]}-W{iso[1]:02d}", "day": day.isoformat()}


def clean(filters):
    """What the screen sent: {field: [values]}. A field left out means everything; an empty list means nothing ticked."""
    return {field: set(str(v) for v in values) for field, values in (filters or {}).items() if isinstance(values, list)}


def keep(fact, filters):
    """A field the fact does not have (a sâu bệnh note has no tổ) does not exclude it."""
    return all(fact[field] in wanted for field, wanted in filters.items() if field in fact)


def _offered(fact, filters, skip):
    """For the lists: a value is offered only if its row really matches the other fields. Chọn Đỏ leaves only the weeks of Đỏ."""
    return all(fact.get(field) in wanted for field, wanted in filters.items() if field != skip)


def _label(field, value):
    if field == "month":
        return f"Tháng {int(value[5:7])}/{value[:4]}"
    if field == "week":
        year, week = value.split("-W")
        monday = dt.date.fromisocalendar(int(year), int(week), 1)
        sunday = monday + dt.timedelta(days=6)
        return f"Tuần {int(week)} · {monday:%d/%m} – {sunday:%d/%m}/{sunday.year}"
    if field == "day":
        return f"{value[8:10]}/{value[5:7]}/{value[:4]}"
    if field == "lan":
        return f"Lần {value}"
    return value


def _order(field, value):
    return (len(value), value) if field == "block" else (value,)


def options(facts, filters, fields):
    """{field: [{value, label}]}. Each list ignores its own filter, so ticking a value never hides the others of that field."""
    result = {}
    for field in fields:
        values = {f[field] for f in facts if f.get(field) and _offered(f, filters, field)}
        ordered = sorted(values, key=lambda v: _order(field, v), reverse=field in TIME_FIELDS)
        result[field] = [{"value": v, "label": _label(field, v)} for v in ordered]
    return result
