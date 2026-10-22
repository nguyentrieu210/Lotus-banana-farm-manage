"""Import original HTT 170ha KML rings into LOTUS-180, with an explicit rejected-draft replacement option."""
import argparse
import json
import hashlib
from pathlib import Path
import frappe
from lotus_farm.promax_rules import geometry

def run(source,backup=None,commit=False,replace_rejected_source=False):
    raw=Path(source).read_bytes();bundle=json.loads(raw)
    assert len(bundle['features'])==82
    assert len({f['properties']['id'] for f in bundle['features']})==82
    farm='LOTUS-180';frappe.get_doc('Farm',farm).check_permission('write')
    planned=[]
    for f in bundle['features']:
        p=f['properties'];assert p['areaHa']>0 and p['zone'] in 'ABCDEF'
        assert p['boundaryStatus'] in ('original-kml','original-kml-open')
        assert p['source_sha256']=='842d41bad538cadd933f002bad2fc2b13cde6bdbccabc51d7195098d34e995dc'
        closed=f['geometry']['type'] in ('Polygon','MultiPolygon')
        shape=geometry(f['geometry']) if closed else None
        assert closed or (p['id']=='C-13' and f['geometry']['type']=='Point')
        planned.append((p,shape))
    assert sum(shape is not None for _,shape in planned)==81
    if commit:
        assert backup and not Path(backup).exists()
        before={dt:frappe.get_all(dt,filters={'farm':farm},fields=['*']) for dt in ('Farm Block','Farm Block Geometry')}
        Path(backup).write_text(json.dumps(before,default=str,ensure_ascii=False),encoding='utf8')
        frappe.db.sql('SELECT name FROM `tabFarm` WHERE name=%s FOR UPDATE',(farm,))
        if replace_rejected_source:
            for old in frappe.get_all('Farm Block Geometry',filters={'farm':farm},fields=['name','approval_state','reason']):
                is_rejected='8b34425865607790ffeb40e121cf53b672732347ebf837817b14627367c36954' in (old.reason or '')
                is_bad_c13=(frappe.db.get_value('Farm Block',frappe.db.get_value('Farm Block Geometry',old.name,'farm_block'),'block_code')=='C-13' and '183465314d5ce5bc9dab68071d7b225b805a8105b86fe9a3103e783b3ad1f038' in (old.reason or ''))
                if is_rejected or is_bad_c13:
                    assert old.approval_state=='Draft'
                    frappe.delete_doc('Farm Block Geometry',old.name)
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
            if commit:frappe.get_doc(dict(doctype='Farm Block Geometry',farm=farm,farm_block=block,version=max((v.version for v in versions),default=0)+1,approval_state='Draft',geojson=json.dumps(shape),reason='HTT_170ha_Model.kml gốc; SHA256 842d41bad538cadd933f002bad2fc2b13cde6bdbccabc51d7195098d34e995dc; vòng ranh giữ nguyên tọa độ KML; dữ liệu nhập '+digest)).insert()
    if commit:
        assert frappe.db.count('Farm Block',{'farm':farm})>=82
        assert frappe.db.count('Farm Block Geometry',{'farm':farm})>=81
        frappe.db.commit()
    return dict(status='committed' if commit else 'preview',farm=farm,source_farm='HTT 170ha KML gốc',blocks=82,closed_geometries=81,unclosed='C-13',source_area_ha=round(sum(p['areaHa'] for p,_ in planned),2),created_blocks=created_blocks,source_sha256=digest)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',required=True);parser.add_argument('--backup');parser.add_argument('--commit',action='store_true');parser.add_argument('--replace-rejected-source',action='store_true');args=parser.parse_args()
    frappe.init(site='frontend');frappe.connect();frappe.set_user('Administrator')
    try:print(json.dumps(run(args.source,args.backup,args.commit,args.replace_rejected_source),ensure_ascii=False))
    finally:frappe.db.rollback();frappe.destroy()
