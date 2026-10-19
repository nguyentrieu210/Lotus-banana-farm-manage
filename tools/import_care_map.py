"""Replace LOTUS-222 map drafts from pinned Lotus Map KML export; default is read-only.

Run with bench Python from sites. --commit backs up all affected geometry before deleting
old draft parcel boundaries. Business Farm Plot records and their links are preserved.
"""
import argparse
import hashlib
import json
from pathlib import Path

import frappe
from lotus_farm.promax_rules import geometry

SOURCE_COMMIT = '404f43a'


def polygons(shape):
    if shape['type'] == 'Polygon':
        return [shape['coordinates']]
    if shape['type'] == 'MultiPolygon':
        return shape['coordinates']
    if shape['type'] == 'GeometryCollection':
        return [p for child in shape['geometries'] for p in polygons(child)]
    raise ValueError('Unexpected care geometry: ' + shape['type'])


def run(source, backup, commit=False):
    raw = Path(source).read_bytes()
    bundle = json.loads(raw)
    assert bundle['type'] == 'FeatureCollection' and len(bundle['features']) == 64
    farm = 'LOTUS-222'
    frappe.get_doc('Farm', farm).check_permission('write')
    blocks = frappe.get_all('Farm Block', filters={'farm': farm},
                            fields=['name', 'block_code', 'area_ha', 'farm_zone'])
    index = {b.block_code: b for b in blocks}
    codes = [f['properties']['id'] for f in bundle['features']]
    assert len(set(codes)) == 64 and set(codes) == set(index)
    planned = []
    for feature in bundle['features']:
        p = feature['properties']
        block = index[p['id']]
        assert p['farmId'] == 'farm222' and p['layerType'] == 'care'
        assert block.farm_zone == p['id'][0]
        assert abs(float(block.area_ha) - float(p['areaHa'])) < .000001
        parts = polygons(feature['geometry'])
        shape = geometry({'type': 'MultiPolygon', 'coordinates': parts} if len(parts) > 1
                         else {'type': 'Polygon', 'coordinates': parts[0]})
        planned.append((block.name, p['id'], shape))
    old = {dt: frappe.get_all(dt, filters={'farm': farm}, fields=['*'])
           for dt in ('Plot Geometry', 'Farm Block Geometry')}
    # No deletion of approved boundaries or unrelated farms.
    assert all(r.approval_state == 'Draft' for rows in old.values() for r in rows)
    report = dict(farm=farm, source_commit=SOURCE_COMMIT, source_sha256=hashlib.sha256(raw).hexdigest(),
                  imported_blocks=len(planned), polygon_parts=sum(len(polygons(s)) for _, _, s in planned),
                  removed_parcel_geometries=len(old['Plot Geometry']),
                  replaced_care_geometries=len(old['Farm Block Geometry']),
                  status='committed' if commit else 'preview')
    if commit:
        assert not Path(backup).exists(), 'Backup path already exists'
        Path(backup).write_text(json.dumps(dict(report=report, documents=old), default=str,
                                          ensure_ascii=False), encoding='utf8')
        frappe.db.sql('SELECT name FROM `tabFarm` WHERE name=%s FOR UPDATE', (farm,))
        for dt, rows in old.items():
            for row in rows:
                frappe.delete_doc(dt, row.name)
        for name, code, shape in planned:
            frappe.get_doc(dict(doctype='Farm Block Geometry', farm=farm, farm_block=name,
                                version=1, approval_state='Draft', geojson=json.dumps(shape),
                                reason='Lotus Map KML, commit ' + SOURCE_COMMIT + '; lô ' + code
                                + '; SHA256 ' + report['source_sha256'])).insert()
        assert frappe.db.count('Plot Geometry', {'farm': farm}) == 0
        assert frappe.db.count('Farm Block Geometry', {'farm': farm}) == 64
        frappe.db.commit()
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--backup', required=True)
    parser.add_argument('--commit', action='store_true')
    args = parser.parse_args()
    frappe.init(site='frontend')
    frappe.connect()
    frappe.set_user('Administrator')
    try:
        print(json.dumps(run(args.source, args.backup, args.commit), ensure_ascii=False))
    finally:
        frappe.db.rollback()
        frappe.destroy()
