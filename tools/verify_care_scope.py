"""Read-only live checks for the care-block scope and overview endpoints."""
import json
import frappe
from lotus_farm import console, field, reporting
from lotus_farm.scoping import land_scope, land_filters

frappe.init(site='frontend')
frappe.connect()
frappe.set_user('Administrator')
try:
    for zone, count in [('A', 13), ('B', 12), ('C', 14), ('D', 12), ('E', 13)]:
        options = console.scope_options(farm='LOTUS-222', zone=zone)
        assert len(options['blocks']) == count, (zone, options)
        assert all(b.farm_zone == zone for b in options['blocks'])
        shapes = field.map_block_data('LOTUS-222', zone=zone, include_draft=True)
        assert len(shapes['features']) == count
        assert all(f['properties']['zone'] == zone for f in shapes['features'])
        charts = reporting.charts('2026-10-19', '2026-10-19', farm='LOTUS-222', zone=zone)
        assert charts['land']['blocks'] == count, charts['land']
        assert [z['zone'] for z in charts['land']['zones']] == [zone]
    options = console.scope_options(farm='LOTUS-222')
    assert options['zones'] == ['A','B','C','D','E']
    b = next(b for b in options['blocks'] if b.block_code == 'B1')
    rejected = False
    try:
        land_scope(farm='LOTUS-222', zone='A', block=b.name)
    except frappe.ValidationError:
        rejected = True
        frappe.clear_messages()
    assert rejected, 'Contradictory zone and care block accepted'
    shapes = field.map_block_data('LOTUS-222', include_draft=True)
    d2 = next(f for f in shapes['features'] if f['properties']['code'] == 'D2')
    assert d2['geometry']['type'] == 'MultiPolygon' and len(d2['geometry']['coordinates']) == 2
    overview = reporting.charts('2026-10-19','2026-10-19',farm='LOTUS-222')
    assert all(k in overview for k in ['land','work','harvest','losses','stock','people','buying','sales'])
    print(json.dumps(dict(status='PASS',care_blocks=len(shapes['features']),zones=5,
                          d2_parts=2,overview_sections=8),ensure_ascii=False))
finally:
    frappe.db.rollback()
    frappe.destroy()
