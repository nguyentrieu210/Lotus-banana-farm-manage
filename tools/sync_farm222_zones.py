"""Reconcile the audited 64 existing care lots and assign zones A-E atomically.

Run using bench Python from sites. Default is read-only; --commit saves zones.
Never re-import the old irrigation bundle or overwrite owner-confirmed parcels.
"""
import argparse
import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path

import frappe

EXPECTED = {'A': (13, '45.45'), 'B': (12, '42.44'), 'C': (14, '45.57'),
            'D': (12, '42.43'), 'E': (13, '39.27')}


def digest(rows):
    return hashlib.sha256(json.dumps(sorted(rows, key=lambda r: r['name']),
        sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def run(args):
    raw = Path(args.source).read_bytes()
    source = json.loads(raw)
    rows = source['lots']
    expected = {r['code']: r for r in rows}
    assert source['farm'] == 'LOTUS-222' and len(rows) == len(expected) == 64
    groups = {}
    for row in rows:
        match = re.fullmatch(r'([A-E])([1-9][0-9]*)', row['code'])
        assert match and row['zone'] == match[1] and Decimal(str(row['area_ha'])) > 0
        groups.setdefault(row['zone'], []).append(row)
    summary = []
    for zone, (count, area) in EXPECTED.items():
        group = groups[zone]
        assert {r['code'] for r in group} == {zone + str(i) for i in range(1, count + 1)}
        total = sum((Decimal(str(r['area_ha'])) for r in group), Decimal(0))
        assert len(group) == count and total == Decimal(area)
        summary.append(dict(zone=zone, lots=count, area_ha=float(total)))
    assert sum((Decimal(str(r['area_ha'])) for r in rows), Decimal(0)) == Decimal('215.16')

    farm = frappe.get_doc('Farm', 'LOTUS-222')
    assert farm.company == 'Lotus Agritech' and farm.area_ha == 222
    blocks = frappe.get_all('Farm Block', filters={'farm': farm.name},
        fields=['name', 'block_code', 'area_ha', 'active'], limit_page_length=1000)
    assert len(blocks) == len({b.block_code for b in blocks}) == 64
    assert {b.block_code for b in blocks} == set(expected)
    for b in blocks:
        assert abs(Decimal(str(b.area_ha)) - Decimal(str(expected[b.block_code]['area_ha']))) < Decimal('.000001'), b.block_code
        assert b.active, b.block_code

    ready = frappe.get_meta('Farm Block').has_field('farm_zone')
    if args.commit and not ready:
        raise ValueError('Deploy Farm Block farm_zone schema before committing data.')
    before = {b.name: frappe.get_doc('Farm Block', b.name).as_dict() for b in blocks}
    protected = {}
    for dt in ['Farm Plot', 'Farm Block Geometry', 'Plot Geometry', 'Crop Cycle']:
        values = frappe.get_all(dt, filters={'farm': farm.name}, fields=['*'], limit_page_length=100000)
        protected[dt] = dict(count=len(values), sha256=digest(values))
    other_blocks = frappe.get_all('Farm Block', filters={'farm': ['!=', farm.name]}, fields=['*'], limit_page_length=100000)
    other_hash = digest(other_blocks)
    changes = []
    for b in blocks:
        old = before[b.name].get('farm_zone')
        wanted = expected[b.block_code]['zone']
        if old and old != wanted:
            raise ValueError('Conflicting existing zone: ' + b.block_code)
        if old == wanted:
            continue
        changes.append(dict(name=b.name, code=b.block_code, before=old, after=wanted))
        if args.commit:
            doc = frappe.get_doc('Farm Block', b.name)
            doc.farm_zone = wanted
            doc.save()

    if args.commit:
        for b in blocks:
            after = frappe.get_doc('Farm Block', b.name).as_dict()
            assert after.farm_zone == expected[b.block_code]['zone']
            skip = {'farm_zone', 'modified', 'modified_by'}
            assert {k:v for k,v in before[b.name].items() if k not in skip} == {k:v for k,v in after.items() if k not in skip}, b.block_code
        for dt, snapshot in protected.items():
            values = frappe.get_all(dt, filters={'farm': farm.name}, fields=['*'], limit_page_length=100000)
            assert len(values) == snapshot['count'] and digest(values) == snapshot['sha256'], dt
        assert digest(frappe.get_all('Farm Block', filters={'farm': ['!=', farm.name]}, fields=['*'], limit_page_length=100000)) == other_hash

    report = dict(farm=farm.name, company=farm.company, source_pdf_sha256=source['source_pdf_sha256'],
        source_sha256=hashlib.sha256(raw).hexdigest(), status='committed' if args.commit else 'dry-run',
        matched_lots=64, source_area_ha=215.16, groups=summary, created_lots=0,
        area_changes=0, zone_changes=len(changes), changes=changes,
        preserved=protected, schema_ready=ready)
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    if args.commit:
        from frappe.utils.file_manager import save_file
        stem = 'farm222-care-zones-' + report['source_sha256'][:12]
        for suffix, content in [('source', raw), ('report', json.dumps(report, ensure_ascii=False).encode())]:
            if not frappe.db.exists('File', {'attached_to_doctype':'Farm', 'attached_to_name':farm.name,
                    'file_name':['like', stem + '-' + suffix + '%.json']}):
                save_file(stem + '-' + suffix + '.json', content, 'Farm', farm.name, is_private=1)
        frappe.db.commit()
    print(json.dumps({k:v for k,v in report.items() if k not in ['changes', 'preserved']}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', default='frontend')
    parser.add_argument('--source', required=True)
    parser.add_argument('--report', required=True)
    parser.add_argument('--commit', action='store_true')
    args = parser.parse_args()
    frappe.init(site=args.site)
    frappe.connect()
    frappe.set_user('Administrator')
    try:
        run(args)
    except Exception:
        frappe.db.rollback()
        raise
    finally:
        frappe.destroy()
