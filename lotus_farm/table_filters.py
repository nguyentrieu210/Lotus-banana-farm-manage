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
