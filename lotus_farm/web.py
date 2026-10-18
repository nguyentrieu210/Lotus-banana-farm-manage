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

@frappe.whitelist(allow_guest=True, methods=['GET'])
def warehouse_service_worker():
    """Cache only public build assets; never cache authenticated stock or purchasing data."""
    root=Path(frappe.get_app_path('lotus_farm','public'))
    manifest=json.loads((root/'frontend/.vite/manifest.json').read_text(encoding='utf-8'))
    assets={'/assets/lotus_farm/warehouse-offline.html',
            '/assets/lotus_farm/images/warehouse-icon-v3-192.png',
            '/assets/lotus_farm/images/warehouse-icon-v3-512.png'}
    visited=set()
    def add(entry_key):
        if entry_key in visited:
            return
        visited.add(entry_key)
        chunk=manifest[entry_key]
        for dependency in chunk.get('imports',[]):
            add(dependency)
        for filename in [chunk.get('file'),*chunk.get('css',[]),*chunk.get('assets',[])]:
            if filename:
                assets.add('/assets/lotus_farm/frontend/'+filename)
    add('warehouse.html')
    code=(root/'warehouse-worker.js').read_text(encoding='utf-8')
    code=code.replace('__WAREHOUSE_ASSETS__',json.dumps(sorted(assets)))
    code=code.replace('__WAREHOUSE_VERSION__',json.dumps(hashlib.sha256(
        json.dumps(sorted(assets)).encode()).hexdigest()[:16]))
    return Response(code, content_type='application/javascript; charset=utf-8',
                    headers={'Service-Worker-Allowed':'/warehouse',
                             'Cache-Control':'no-store'})

@frappe.whitelist(allow_guest=True, methods=['GET'])
def work_service_worker():
    """Cache only the separate Work PWA assets; do not cache authenticated responses."""
    root = Path(frappe.get_app_path('lotus_farm', 'public'))
    manifest = json.loads((root / 'frontend/.vite/manifest.json').read_text(encoding='utf-8'))
    assets = {'/assets/lotus_farm/work-offline.html',
              '/assets/lotus_farm/images/work-icon-v3-192.png',
              '/assets/lotus_farm/images/work-icon-v3-512.png'}
    seen = set()
    def add(entry):
        if entry in seen:
            return
        seen.add(entry)
        chunk = manifest[entry]
        for dependency in chunk.get('imports', []):
            add(dependency)
        for file in [chunk.get('file'), *chunk.get('css', []), *chunk.get('assets', [])]:
            if file:
                assets.add('/assets/lotus_farm/frontend/' + file)
    add('work-mobile.html')
    code = (root / 'work-worker.js').read_text(encoding='utf-8')
    version = hashlib.sha256(json.dumps(sorted(assets)).encode()).hexdigest()[:16]
    code = code.replace('__WORK_ASSETS__', json.dumps(sorted(assets))).replace('__WORK_VERSION__', version)
    return Response(code, content_type='application/javascript; charset=utf-8',
                    headers={'Service-Worker-Allowed': '/work', 'Cache-Control': 'no-store'})


@frappe.whitelist(allow_guest=True, methods=['GET', 'HEAD'])
def buying_manifest():
    path=Path(frappe.get_app_path('lotus_farm','public','buying.webmanifest'))
    return Response(path.read_text(encoding='utf-8'),
                    content_type='application/manifest+json; charset=utf-8',
                    headers={'Cache-Control':'no-cache'})


@frappe.whitelist(allow_guest=True, methods=['GET', 'HEAD'])
def buying_service_worker():
    root=Path(frappe.get_app_path('lotus_farm','public'))
    manifest=json.loads((root/'frontend/.vite/manifest.json').read_text(encoding='utf-8'))
    assets={'/assets/lotus_farm/buying-offline.html',
            '/assets/lotus_farm/images/buying-icon-192.png',
            '/assets/lotus_farm/images/buying-icon-512.png'}
    seen=set()
    def add(key):
        if key in seen:return
        seen.add(key)
        chunk=manifest[key]
        for dep in chunk.get('imports',[]):add(dep)
        for f in [chunk.get('file'),*chunk.get('css',[]),*chunk.get('assets',[])]:
            if f:assets.add('/assets/lotus_farm/frontend/'+f)
    add('buying.html')
    code=(root/'buying-worker.js').read_text(encoding='utf-8')
    version=hashlib.sha256(json.dumps(sorted(assets)).encode()).hexdigest()[:16]
    code=code.replace('__BUYING_ASSETS__',json.dumps(sorted(assets))).replace('__BUYING_VERSION__',json.dumps(version))
    return Response(code,content_type='application/javascript; charset=utf-8',
                    headers={'Service-Worker-Allowed':'/buying','Cache-Control':'no-store'})


@frappe.whitelist(allow_guest=True, methods=['GET'])
def work_manifest():
    path = Path(frappe.get_app_path('lotus_farm', 'public', 'work.webmanifest'))
    return Response(path.read_text(encoding='utf-8'),
                    content_type='application/manifest+json; charset=utf-8',
                    headers={'Cache-Control': 'no-cache'})


@frappe.whitelist(allow_guest=True, methods=['GET'])
def warehouse_manifest():
    """Return PWA manifest with its explicit MIME type instead of octet-stream."""
    path=Path(frappe.get_app_path('lotus_farm','public','warehouse.webmanifest'))
    return Response(path.read_text(encoding='utf-8'),
                    content_type='application/manifest+json; charset=utf-8',
                    headers={'Cache-Control':'no-cache'})

@frappe.whitelist(allow_guest=True, methods=['GET', 'HEAD'])
def hr_mobile_manifest():
    path=Path(frappe.get_app_path('lotus_farm','public','hr-mobile.webmanifest'))
    return Response(path.read_text(encoding='utf-8'),
                    content_type='application/manifest+json; charset=utf-8',
                    headers={'Cache-Control':'no-cache'})


@frappe.whitelist(allow_guest=True, methods=['GET'])
def hr_mobile_service_worker():
    """Separate HR scope. No data or authenticated HTML caching."""
    root=Path(frappe.get_app_path('lotus_farm','public'))
    manifest=json.loads((root/'frontend/.vite/manifest.json').read_text(encoding='utf-8'))
    assets={'/assets/lotus_farm/hr-mobile-offline.html',
            '/assets/lotus_farm/images/hr-icon-192.png',
            '/assets/lotus_farm/images/hr-icon-512.png'}
    seen=set()
    def add(key):
        if key in seen:return
        seen.add(key)
        chunk=manifest[key]
        for dep in chunk.get('imports',[]):add(dep)
        for name in [chunk.get('file'),*chunk.get('css',[]),*chunk.get('assets',[])]:
            if name:assets.add('/assets/lotus_farm/frontend/'+name)
    add('hr-mobile.html')
    code=(root/'hr-mobile-worker.js').read_text(encoding='utf-8')
    version=hashlib.sha256(json.dumps(sorted(assets)).encode()).hexdigest()[:16]
    return Response(code.replace('__HR_ASSETS__',json.dumps(sorted(assets))).replace('__HR_VERSION__',version),
                    content_type='application/javascript; charset=utf-8',
                    headers={'Service-Worker-Allowed':'/hr-mobile','Cache-Control':'no-store'})
