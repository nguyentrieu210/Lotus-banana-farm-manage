"""Run inside the site container with a private credential file argument."""
import json
import sys
import frappe
from lotus_farm.mail_setup import configure

frappe.init(site='frontend')
frappe.connect()
frappe.set_user('Administrator')
try:
    print(json.dumps(configure(sys.argv[1]),ensure_ascii=False))
finally:
    frappe.destroy()
