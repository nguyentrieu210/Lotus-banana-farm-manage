"""Đóng tháng checklist on the real site (read only): every step has a state and the steps keep their order."""
import json

import frappe
from frappe.utils import nowdate

frappe.init(site='frontend', sites_path='/home/frappe/frappe-bench/sites')
frappe.connect()
frappe.set_user('Administrator')
from lotus_farm.finance import api  # noqa: E402

try:
    result = api.month_checklist(nowdate()[:7])
    keys = [s['key'] for s in result['steps']]
    assert keys == ['invoices', 'lots', 'payroll', 'vouchers', 'statutory', 'cost_closing', 'costing', 'result', 'reconciliation', 'lock'], keys
    assert all(s['state'] in ('done', 'todo', 'na') for s in result['steps'])
    print(json.dumps(dict(done=result['done'], total=result['total'], steps=[(s['key'], s['state'], s['detail'][:60]) for s in result['steps']]), ensure_ascii=False))
finally:
    frappe.db.rollback()
