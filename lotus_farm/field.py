"""Session info and the care map (lô boundaries) for the workspace."""
import json
import frappe


def _density(block):
    from lotus_farm.farm_land_rules import density
    return density(block.get('lotus_tree_count'), block.get('area_ha'))


@frappe.whitelist()
def map_block_data(farm, block=None, zone=None, include_draft=False):
    """Care boundaries, with explicit draft visibility for imported KML sources."""
    from lotus_farm.reporting import records, scope
    from lotus_farm.scoping import land_scope, land_filters
    scope(farm)
    selected_scope = land_scope(farm=farm, block=block, zone=zone)
    selected = records('Farm Block',
                       land_filters(frappe.get_meta('Farm Block'), selected_scope),
                       ['name', 'block_code', 'block_name', 'farm_zone', 'area_ha', 'variety',
                        *[f for f in ('lotus_tree_count', 'lotus_estimated_flowering_date') if frappe.get_meta('Farm Block').has_field(f)]])
    allowed = {b.name for b in selected}
    blocks = {b.name: b for b in selected}
    states = ['Draft', 'Approved'] if include_draft in (True, 1, '1', 'true') else ['Approved']
    versions = records('Farm Block Geometry',
                       {'farm': farm, 'approval_state': ['in', states]},
                       ['name', 'farm_block', 'version', 'geojson', 'approval_state'])
    latest = {}
    for row in versions:
        if row.farm_block not in allowed:
            continue
        if row.farm_block not in latest or row.version > latest[row.farm_block].version:
            latest[row.farm_block] = row
    result = dict(type='FeatureCollection',
                features=[dict(type='Feature', geometry=json.loads(row.geojson),
                               properties=dict(block=row.farm_block,
                                               code=blocks[row.farm_block].block_code,
                                               zone=blocks[row.farm_block].farm_zone,
                                               area_ha=blocks[row.farm_block].area_ha,
                                               variety=blocks[row.farm_block].variety,
                                               tree_count=blocks[row.farm_block].get('lotus_tree_count') or 0,
                                               density=_density(blocks[row.farm_block]),
                                               flowering_month=str(blocks[row.farm_block].get('lotus_estimated_flowering_date') or '')[:7],
                                               approval_state=row.approval_state, version=row.version,
                                               document=row.name)) for row in latest.values()])
    if farm == 'LOTUS-180' and 'Draft' in states:
        from pathlib import Path
        root = Path(frappe.get_app_path('lotus_farm')).parent / 'data'
        result['perimeter'] = json.loads((root / 'farm180-perimeter.geojson').read_text(encoding='utf8'))
        source = json.loads((root / 'farm180-care-boundaries.geojson').read_text(encoding='utf8'))
        by_code = {b.block_code: b for b in selected}
        result['open_features'] = [dict(type='Feature', geometry=f['geometry'],
            properties=dict(code=f['properties']['id'], zone=f['properties']['zone'],
                block=by_code[f['properties']['id']].name, approval_state='Draft'))
            for f in source['features'] if f['geometry']['type'] not in ('Polygon', 'MultiPolygon')
            and f['properties']['id'] in by_code]
        result['source_label'] = 'KML gốc HTT 170 ha'
    return result


@frappe.whitelist()
def session_info():
    if frappe.session.user=='Guest':frappe.throw('Đăng nhập trước khi mở Lotus.',frappe.AuthenticationError)
    from frappe.sessions import get_csrf_token
    roles=set(frappe.get_roles())
    return dict(user=frappe.session.user,csrf_token=get_csrf_token(),capabilities=dict(
        stock=all(frappe.has_permission(t,'read') for t in ('Stock Entry','Warehouse','Item','Bin','Company')),
        # Tổng quan: the people who run or audit the farm.
        home=frappe.session.user=='Administrator' or bool(roles.intersection(('Lotus Farm Manager','Lotus Auditor')))),
        farms=frappe.get_list('Farm',fields=['name','farm_name'],limit_page_length=1000) if frappe.has_permission('Farm','read') else [])
