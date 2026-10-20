"""Explicit operator bootstrap for the approved OneDrive adoption task.

Run after migrate through a connected bench process. Raw source files remain
private. No selected suckers, planting events, harvests, or stock are fabricated.
"""
import hashlib
from pathlib import Path
import frappe
from frappe.utils.file_manager import save_file
from lotus_farm.onedrive_workspace import import_handover, library, create_adoption, generate_tags


def run(journal_path, farm='LOTUS-222'):
    if frappe.session.user != 'Administrator':frappe.throw('Operator bootstrap requires Administrator.')
    content=Path(journal_path).read_bytes();digest=hashlib.sha256(content).hexdigest()
    counts={dt:frappe.db.count(dt) for dt in ('Sucker Selection Batch','Planting Event','Harvest Actual','Stock Entry')}
    stored=save_file('Nhat-Ky-Chat-Cay-Cu-20261020.xlsx',content,None,None,is_private=1)
    history=import_handover(farm,stored.file_url,digest)
    retry=import_handover(farm,stored.file_url,digest)
    assert retry['created']==0
    assert history['total_cut_qty']==430871 and sum(history['zone_totals'].values())==430871
    data,_=library();registered=0
    for source in data['sources']:
        if frappe.db.exists('Source File Registry',{'sha256':source['sha256']}):continue
        frappe.get_doc(dict(doctype='Source File Registry',source_key=f"onedrive:{source['sha256']}",source_path=source.get('url') or source.get('local_file') or source['title'],
            source_filename=source['title'],sha256=source['sha256'],business_period=source.get('modified_at','2026-10-20')[:10],
            version_marker=data['version'],source_priority=1 if source['key']=='anhdung_master' else 2,migration_tier='A',source_status='Active',source_family=source['key'])).insert(ignore_permissions=True)
        registered+=1
    # Exact neutral source preset, clearly named as reference. No condition is inferred.
    preset=next(r for r in data['defaults'] if r['source_farm']=='BP1.1.1' and r['year_band']=='2')
    configured=[];tags=[]
    for row in frappe.get_all('Farm',fields=['name']):
        existing=frappe.get_all('Lotus Process Adoption',filters={'farm':row.name,'approval_state':'Approved'},pluck='name')
        if existing:
            name=existing[0]
        else:
            model=create_adoption(row.name,preset['key'],valid_from='2026-01-01',approve=1)
            name=model['name'];configured.append(dict(farm=row.name,version=name,preset=preset['key']))
        tags.append(dict(farm=row.name,**generate_tags(name,'2026-01-01','2028-12-31')))
    assert all(frappe.db.count(dt)==qty for dt,qty in counts.items()),'Bootstrap must not create operational actuals or stock.'
    frappe.db.commit()
    return dict(handover=history,retry=retry,registered_sources=registered,configured=configured,tags=tags,
                reference_preset='BP1.1.1 / year 2, not calibrated Lotus actual yield',actual_counts_unchanged=counts)
