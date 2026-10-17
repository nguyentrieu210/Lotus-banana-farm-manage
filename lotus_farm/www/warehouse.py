"""Mobile Warehouse shell, scoped independently from the Lotus operations PWA."""
import json
from pathlib import Path
from urllib.parse import quote
import frappe

no_cache = 1


def get_context(context):
    if frappe.session.user == 'Guest':
        frappe.local.flags.redirect_location = '/login?redirect-to=' + quote('/warehouse', safe='/')
        raise frappe.Redirect
    from lotus_farm.warehouse import _access
    _access()
    manifest_path=Path(frappe.get_app_path('lotus_farm','public','frontend','.vite','manifest.json'))
    if not manifest_path.exists():
        frappe.throw('Cần build giao diện Kho Lotus.')
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    visited=set()
    css=[]
    def include(entry_key):
        if entry_key in visited:
            return
        visited.add(entry_key)
        entry=manifest[entry_key]
        for dependency in entry.get('imports',[]):
            include(dependency)
        for stylesheet in entry.get('css',[]):
            if stylesheet not in css:
                css.append(stylesheet)
    include('warehouse.html')
    context.script='/assets/lotus_farm/frontend/'+manifest['warehouse.html']['file']
    context.styles=['/assets/lotus_farm/frontend/'+name for name in css]
    context.no_cache=1
