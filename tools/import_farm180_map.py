"""Add the confirmed HTT 170ha source to LOTUS-180. Preview by default; no deletions."""
import argparse
import json
import hashlib
from pathlib import Path
import frappe
from lotus_farm.promax_rules import geometry

def run(source,backup=None,commit=False):
    raw=Path(source).read_bytes();bundle=json.loads(raw)
    assert len(bundle['features'])==82
    assert len({f['properties']['id'] for f in bundle['features']})==82
    farm='LOTUS-180';frappe.get_doc('Farm',farm).check_permission('write')
    planned=[]
    for f in bundle['features']:
        p=f['properties'];assert p['areaHa']>0 and p['zone'] in 'ABCDEF'
        closed=f['geometry']['type'] in ('Polygon','MultiPolygon')
        shape=geometry(f['geometry']) if closed else None
        assert closed or p['id']=='C-13'
        planned.append((p,shape))
    assert sum(shape is not None for _,shape in planned)==81
    if commit:
        assert backup and not Path(backup).exists()
        before={dt:frappe.get_all(dt,filters={'farm':farm},fields=['*']) for dt in ('Farm Block','Farm Block Geometry')}
        Path(backup).write_text(json.dumps(before,default=str,ensure_ascii=False),encoding='utf8')
        frappe.db.sql('SELECT name FROM `tabFarm` WHERE name=%s FOR UPDATE',(farm,))
    created_blocks=created_geometries=0
    digest=hashlib.sha256(raw).hexdigest()
    for p,shape in planned:
        existing=frappe.get_all('Farm Block',filters={'farm':farm,'block_code':p['id']},fields=['name','farm_zone','area_ha'])
        assert len(existing)<=1
        if existing:
            block=existing[0].name
            assert existing[0].farm_zone==p['zone'] and abs(float(existing[0].area_ha)-p['areaHa'])<.000001
        else:
            created_blocks+=1
            if not commit:continue
            block=frappe.get_doc(dict(doctype='Farm Block',farm=farm,block_code=p['id'],block_name='Lô chăm sóc '+p['id'],farm_zone=p['zone'],area_ha=p['areaHa'],active=1,notes='Nguồn HTT 170ha đã xác nhận dùng cho LOTUS-180; diện tích theo nguồn, không ép theo tên vườn.')).insert().name
        if shape:
            versions=frappe.get_all('Farm Block Geometry',filters={'farm_block':block},fields=['geojson','version']) if existing else []
            if any(json.loads(v.geojson)==shape for v in versions):continue
            created_geometries+=1
            if commit:frappe.get_doc(dict(doctype='Farm Block Geometry',farm=farm,farm_block=block,version=max((v.version for v in versions),default=0)+1,approval_state='Draft',geojson=json.dumps(shape),reason='Lotus Map 404f43a; farm170/as-built/lots.geojson; giữ ranh bao gốc; SHA256 '+digest)).insert()
    if commit:
        assert frappe.db.count('Farm Block',{'farm':farm})>=82
        assert frappe.db.count('Farm Block Geometry',{'farm':farm})>=81
        frappe.db.commit()
    return dict(status='committed' if commit else 'preview',farm=farm,source_farm='HTT 170ha',blocks=82,closed_geometries=81,open_geometry='C-13',source_area_ha=round(sum(p['areaHa'] for p,_ in planned),2),created_blocks=created_blocks,source_sha256=digest)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',required=True);parser.add_argument('--backup');parser.add_argument('--commit',action='store_true');args=parser.parse_args()
    frappe.init(site='frontend');frappe.connect();frappe.set_user('Administrator')
    try:print(json.dumps(run(args.source,args.backup,args.commit),ensure_ascii=False))
    finally:frappe.db.rollback();frappe.destroy()
