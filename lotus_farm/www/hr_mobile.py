"""Separate HR mobile app. Same HRMS records, permissions and authenticated session."""
import json
from pathlib import Path
import frappe
no_cache=1

def get_context(context):
    context.guest=frappe.session.user=='Guest'
    context.no_cache=1
    context.styles=[]
    context.script=''
    if context.guest:return
    from lotus_farm.hr_workspace import _hr_access
    _hr_access()
    path=Path(frappe.get_app_path('lotus_farm','public','frontend','.vite','manifest.json'))
    if not path.exists():frappe.throw('Cần build giao diện Nhân sự điện thoại.')
    entries=json.loads(path.read_text(encoding='utf-8'))
    styles,seen=[],set()
    def collect(key):
        if key in seen:return
        seen.add(key)
        row=entries[key]
        for dep in row.get('imports',[]):collect(dep)
        for css in row.get('css',[]):
            if css not in styles:styles.append(css)
    collect('hr-mobile.html')
    context.script='/assets/lotus_farm/frontend/'+entries['hr-mobile.html']['file']
    context.styles=['/assets/lotus_farm/frontend/'+s for s in styles]
