"""Validate shared land scope once; never silently ignore contradictory IDs."""
import frappe


def land_scope(company=None, farm=None, block=None, plot=None, cycle=None, zone=None):
    values = dict(company=company or None, farm=farm or None, block=block or None, plot=plot or None, cycle=cycle or None)
    for key, doctype in [('cycle', 'Crop Cycle'), ('plot', 'Farm Plot'), ('block', 'Farm Block'), ('farm', 'Farm')]:
        if not values[key]:
            continue
        doc = frappe.get_doc(doctype, values[key]); doc.check_permission('read')
        parents = {'farm': doc.get('farm'), 'block': doc.get('farm_block'), 'plot': doc.get('farm_plot'), 'company': doc.get('company')}
        for parent, name in parents.items():
            if parent == key or not name:
                continue
            if values[parent] and values[parent] != name:
                frappe.throw({'cycle':'Vụ','plot':'Thửa','block':'Lô','farm':'Vườn','company':'Công ty'}[key] + ' đã chọn không thuộc ' + {'cycle':'Vụ','plot':'Thửa','block':'Lô','farm':'Vườn','company':'Công ty'}[parent].lower() + ' đã chọn.')
            values[parent] = name
    if zone:
        zone = str(zone).strip()
        if not values['farm']:
            frappe.throw('Chọn vườn trước khi chọn khu.')
        blocks = frappe.get_list('Farm Block', filters={'farm': values['farm'], 'farm_zone': zone},
                                 pluck='name', limit_page_length=10000)
        if not blocks:
            frappe.throw('Khu không thuộc vườn đã chọn hoặc không có quyền xem.')
        if values['block'] and values['block'] not in blocks:
            frappe.throw('Lô không thuộc khu đã chọn.')
        values['zone'] = zone
        values['zone_blocks'] = blocks
    return values


def land_filters(meta, scope):
    fields = {'farm': 'farm', 'block': 'farm_block', 'plot': 'farm_plot', 'cycle': 'crop_cycle', 'company': 'company'}
    own = {'Farm': 'farm', 'Farm Block': 'block', 'Farm Plot': 'plot', 'Crop Cycle': 'cycle'}.get(meta.name)
    result = {}
    for key, field in fields.items():
        if scope.get(key) and meta.has_field(field):
            result[field] = scope[key]
    if scope.get('company') and not scope.get('farm') and meta.has_field('farm') and not meta.has_field('company'):
        farms=frappe.get_list('Farm',filters={'company':scope['company']},pluck='name',limit_page_length=1000)
        result['farm']=['in',farms or ['__no_permitted_farm__']]
    if own and scope.get(own):
        result['name'] = scope[own]
    if scope.get('zone_blocks') and not scope.get('block'):
        if meta.name == 'Farm Block':
            result['name'] = ['in', scope['zone_blocks']]
        elif meta.has_field('farm_block'):
            result['farm_block'] = ['in', scope['zone_blocks']]
    return result
