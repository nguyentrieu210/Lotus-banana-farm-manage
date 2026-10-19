"""Read-only integration validation of the Warehouse mobile route and access model."""
import os,json,frappe
from types import SimpleNamespace
os.chdir('/home/frappe/frappe-bench/sites')
frappe.init(site='frontend');frappe.connect();frappe.set_user('Administrator')
try:
 from lotus_farm.www import warehouse as warehouse_page
 from lotus_farm import web,warehouse_access
 ctx=SimpleNamespace()
 frappe.local.request=SimpleNamespace(path='/warehouse')
 warehouse_page.get_context(ctx)
 assert '/assets/warehouse-' in ctx.script,ctx.script
 assert ctx.styles
 print('PASS /warehouse authenticated context uses separate mobile frontend',ctx.script)
 manifest=json.load(open('/home/frappe/frappe-bench/apps/lotus_farm/lotus_farm/public/warehouse.webmanifest'))
 assert manifest['start_url']=='/warehouse' and manifest['scope']=='/warehouse'
 assert len(manifest['icons'])==2
 print('PASS PWA start/scope and square icons')
 worker=web.warehouse_service_worker()
 assert worker.status_code==200
 assert worker.headers['Service-Worker-Allowed']=='/warehouse'
 assert b'/api/' in worker.get_data()
 assert b'warehouse-offline.html' in worker.get_data()
 print('PASS SW scoped, no API caching')
 response=web.warehouse_manifest()
 assert 'application/manifest+json' in response.content_type
 print('PASS manifest MIME and response')
 for role in warehouse_access.ROLE_OPERATIONS:
  assert frappe.db.exists('Role',role)
 print('PASS five restricted Warehouse roles exist')
finally:
 frappe.db.rollback();frappe.destroy()
