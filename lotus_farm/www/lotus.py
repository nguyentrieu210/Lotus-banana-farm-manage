import json
from pathlib import Path
from urllib.parse import quote
import frappe

no_cache = 1


def get_context(context):
    if frappe.session.user == 'Guest':
        target = frappe.request.path or '/lotus/mobile'
        if not (target == '/lotus' or target.startswith('/lotus/')):
            target = '/lotus/mobile'
        frappe.local.flags.redirect_location = '/login?redirect-to=' + quote(target, safe='/')
        raise frappe.Redirect
    manifest=Path(frappe.get_app_path('lotus_farm','public','frontend','.vite','manifest.json'))
    if not manifest.exists():frappe.throw('Build the Lotus frontend before opening this application.')
    entries=json.loads(manifest.read_text())
    # Standalone mobile shell, using the existing authenticated Frappe site.
    request_path=frappe.request.path.rstrip('/')
    entry_key={'/lotus/giao-viec':'assign.html','/lotus/kho':'stock.html'}.get(request_path,'index.html')
    entry=entries[entry_key]
    context.script='/assets/lotus_farm/frontend/'+entry['file']
    context.styles=['/assets/lotus_farm/frontend/'+p for p in entry.get('css',[])]
    context.no_cache=1
