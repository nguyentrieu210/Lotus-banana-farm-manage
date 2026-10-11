import json
from pathlib import Path
import frappe

no_cache = 1


def get_context(context):
    if frappe.session.user == 'Guest':
        frappe.local.flags.redirect_location = '/login?redirect-to=/lotus/today'
        raise frappe.Redirect
    manifest=Path(frappe.get_app_path('lotus_farm','public','frontend','.vite','manifest.json'))
    if not manifest.exists():frappe.throw('Build the Lotus frontend before opening this application.')
    entries=json.loads(manifest.read_text())
    # Standalone mobile shell, using the existing authenticated Frappe site.
    request_path=frappe.request.path.rstrip('/')
    entry_key='assign.html' if request_path.endswith('/giao-viec') else 'index.html'
    entry=entries[entry_key]
    context.script='/assets/lotus_farm/frontend/'+entry['file']
    context.styles=['/assets/lotus_farm/frontend/'+p for p in entry.get('css',[])]
    context.no_cache=1
