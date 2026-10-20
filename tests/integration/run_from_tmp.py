"""Run an integration script against code copied to /tmp/lt before it is deployed.

Usage (inside the backend container, from /home/frappe/frappe-bench/sites):
    python /tmp/lt/tests/integration/run_from_tmp.py verify_purchase_proposal [doctype_dir ...]
The copied lotus_farm package shadows the installed one. Each doctype_dir (relative to
lotus_farm/lotus_farm/doctype) is synced first; creating a table commits, so do it only for doctypes
the next release adds anyway.
"""
import runpy
import sys

sys.path.insert(0, '/tmp/lt')
import frappe  # noqa: E402

script, doctypes = sys.argv[1], sys.argv[2:]
if doctypes:
    frappe.init(site='frontend', sites_path='/home/frappe/frappe-bench/sites')
    frappe.connect()
    from frappe.modules.import_file import import_file_by_path
    for name in doctypes:
        import_file_by_path('/tmp/lt/lotus_farm/lotus_farm/doctype/%s/%s.json' % (name, name), force=True)
    frappe.db.commit()
    frappe.destroy()
runpy.run_path('/tmp/lt/tests/integration/%s.py' % script, run_name='__main__')
