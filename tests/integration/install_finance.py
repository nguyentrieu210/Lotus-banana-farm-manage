"""Additive finance install on the real site before the release (roles, read permissions, the Journal Entry
payment field and the four accounting dimensions). Adding columns commits, so it cannot run inside a
rolled-back check; it is exactly what migrate does on release. Finance stays switched off; TT133 is not applied."""
import json

import frappe

frappe.init(site='frontend', sites_path='/home/frappe/frappe-bench/sites')
frappe.connect()
frappe.set_user('Administrator')
from lotus_farm.finance import rules, setup  # noqa: E402

setup.install()
frappe.db.commit()
report = dict(roles=[r for r in (setup.ACCOUNTANT, setup.CHIEF) if frappe.db.exists('Role', r)],
              dimensions=frappe.get_all('Accounting Dimension', fields=['document_type', 'fieldname']),
              gl_columns=[f for f in rules.DIM_FIELDS if frappe.get_meta('GL Entry').has_field(f)],
              stock_row_columns=[f for f in rules.DIM_FIELDS if frappe.get_meta('Stock Entry Detail').has_field(f)],
              enabled=bool(setup.settings().finance_enabled))
print(json.dumps(report, default=str, ensure_ascii=False))
