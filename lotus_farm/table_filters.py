"""Exact-value checklist filters; caller supplies its permission-scoped rows."""
import frappe
from datetime import date,datetime
from decimal import Decimal


def selections(raw, fields):
    result = frappe.parse_json(raw) if raw not in (None,'') else {}
    if not isinstance(result, dict):
        frappe.throw('Bộ lọc cột không hợp lệ.')
    for field, values in result.items():
        if field not in fields or not isinstance(values, list) or len(values) > 10000:
            frappe.throw('Giá trị lọc cột không hợp lệ.')
        if any(not isinstance(value, (str, int, float, type(None))) for value in values):
            frappe.throw('Giá trị lọc phải là dữ liệu đơn.')
    return result


def matches(row, filters):
    def normal(value):
        if isinstance(value,(date,datetime)):return str(value)
        if isinstance(value,Decimal):return float(value)
        return value
    return all(normal(row.get(field)) in [normal(value) for value in values] for field, values in filters.items())


def distinct(rows, fields, labels=None):
    result = {}
    for field in fields:
        values = {}
        for row in rows:
            value = row.get(field)
            key = str(value)
            if key not in values:
                entry = dict(value=value)
                if labels and field in labels:
                    entry['label'] = labels[field](row)
                values[key] = entry
        result[field] = list(values.values())
    return result



def faceted_distinct(rows, fields, selected, labels=None):
    """Excel-like choices after applying other column filters, not the field's own.

    Keep selected choices visible if other filters currently yield zero matches.
    """
    result = {}
    for field in fields:
        other = {name: values for name, values in selected.items() if name != field}
        choices = distinct([row for row in rows if matches(row, other)], [field], labels)[field]
        included = {str(entry['value']) for entry in choices}
        for value in selected.get(field, []):
            if str(value) not in included:
                choices.append(dict(value=value, label=str(value) if value is not None else '(Trống)'))
        result[field] = choices
    return result


def sorted_rows(rows,raw,fields,aliases=None):
    model=frappe.parse_json(raw) if raw not in (None,'') else []
    if not isinstance(model,list) or len(model)>5:frappe.throw('Sắp xếp không hợp lệ.')
    aliases=aliases or {}
    for entry in model:
        if not isinstance(entry,dict) or entry.get('colId') not in fields or entry.get('sort') not in ('asc','desc'):
            frappe.throw('Cột sắp xếp không hợp lệ.')
    result=list(rows)
    for entry in reversed(model):
        field=aliases.get(entry['colId'],entry['colId'])
        def key(row):
            value=row.get(field)
            return (value is None, float(value) if isinstance(value,(int,float,Decimal)) else str(value or '').casefold())
        result.sort(key=key,reverse=entry['sort']=='desc')
    return result
