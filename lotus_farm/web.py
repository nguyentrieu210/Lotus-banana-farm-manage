"""Serve a session-independent worker; API/file payloads are never SW-cached."""
import json
import hashlib
from pathlib import Path
import frappe
from werkzeug.wrappers import Response


@frappe.whitelist(allow_guest=True, methods=['GET'])
def service_worker():
    root=Path(frappe.get_app_path('lotus_farm','public'))
    manifest=json.loads((root/'frontend/.vite/manifest.json').read_text())
    assets={'/assets/lotus_farm/images/lotus-agritech.jpg'}
    assets.update('/assets/lotus_farm/frontend/'+key for key in manifest if key.endswith('.html'))
    for entry in manifest.values():
        for file in [entry.get('file'),*entry.get('css',[]),*entry.get('assets',[])]:
            if file:assets.add('/assets/lotus_farm/frontend/'+file)
    code=(root/'lotus-worker.js').read_text().replace('__LOTUS_ASSETS__',json.dumps(sorted(assets))).replace('__LOTUS_VERSION__',json.dumps(hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()[:16]))
    return Response(code,content_type='application/javascript; charset=utf-8',headers={'Service-Worker-Allowed':'/lotus/','Cache-Control':'no-cache'})
