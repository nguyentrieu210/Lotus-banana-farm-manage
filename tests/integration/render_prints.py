"""Render Lotus prints of real documents to /tmp/prints/*.pdf for a visual check (read-only, rolls back).

python run_from_tmp.py render_prints  -> stock entries, a signed stock entry (with QR), proposals, payroll draft.
"""
import json
import os

import frappe

frappe.init(site='frontend', sites_path='/home/frappe/frappe-bench/sites')
frappe.connect()
frappe.set_user('Administrator')
frappe.in_test = True
from lotus_farm import print_kit as pk  # noqa: E402

os.makedirs('/tmp/prints', exist_ok=True)
out = {}
try:
    from lotus_farm.www import lotus_stock_print as stock, lotus_payroll_print as payroll
    for doctype in ('Stock Entry', 'Stock Reconciliation', 'Purchase Receipt'):
        for name in frappe.get_all(doctype, filters={'docstatus': 1}, pluck='name', limit=1):
            pdf = pk.pdf(str(pk.render('stock.html', stock.build(doctype, name))))
            open('/tmp/prints/%s.pdf' % name, 'wb').write(pdf)
            out[name] = len(pdf)
    entry = frappe.get_all('Stock Entry', filters={'docstatus': 1}, pluck='name', limit=1)[0]
    from lotus_farm import signing
    signing.request_signatures('Stock Entry', entry, dict(HANDOVER='Administrator', STOREKEEPER='Administrator')) \
        if frappe.db.get_value('Employee', {'user_id': 'Administrator'}) else None
    p = payroll.build('Lotus Agritech', '2026-10')
    open('/tmp/prints/payroll-2026-10.pdf', 'wb').write(pk.pdf(str(pk.render('payroll.html', p)), landscape=True))
    out['payroll'] = True
    from lotus_farm.www import lotus_timekeeping_print as sheet
    for kind in ('staff', 'crew'):
        open('/tmp/prints/timesheet-%s.pdf' % kind, 'wb').write(pk.pdf(str(pk.render('timesheet.html', sheet.build('Lotus Agritech', '2026-10', kind))), landscape=True))
    out['timesheet'] = True
    from lotus_farm.www import lotus_purchase_order_print as po_print
    for name in frappe.get_all('Purchase Order', pluck='name', limit=2):
        open('/tmp/prints/%s.pdf' % name, 'wb').write(pk.pdf(str(po_print.html(frappe.get_doc('Purchase Order', name)))))
        out[name] = True
finally:
    frappe.db.rollback()
print(json.dumps(out))
