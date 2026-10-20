"""Run with bench execute before migration; never removes runtime-only fields."""
import json
from pathlib import Path
import frappe


def run():
    root=Path(frappe.get_app_path('lotus_farm'))/'lotus_farm/doctype'
    missing={}
    for path in root.glob('*/*.json'):
        doc=json.loads(path.read_text())
        if not frappe.db.exists('DocType',doc['name']):continue
        stored=set(frappe.get_all('DocField',filters={'parent':doc['name']},pluck='fieldname'))
        current={r['fieldname'] for r in doc['fields']}
        if stored-current:missing[doc['name']]=sorted(stored-current)
    return dict(runtime_fields_missing_in_source=missing,checked_doctypes=len(list(root.glob('*/*.json'))))
