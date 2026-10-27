"""Vườn & lô: the lot list of a farm with area, trees, density and data gaps; one lot's page (plots, map,
work and materials, yield and losses, disease and bunch care, change history); editing lots and plots;
and the Excel round-trip (export, preview every change, apply the valid rows).

Everyone with read on Farm Block sees the lots of the farms they are permitted; Administrator, System
Manager and Lotus Farm Manager edit. Rules and the Excel comparison live in lotus_farm.farm_land_rules.
"""
import json
from collections import defaultdict
from io import BytesIO

import frappe
from frappe.utils import add_days, flt, getdate, nowdate

from lotus_farm import farm_land_rules as rules

BLOCK_FIELDS = ['name', 'modified', 'farm', 'block_code', 'block_name', 'farm_zone', 'area_ha', 'variety', 'planting_date', 'planting_density',
                'irrigation_zone', 'manager', 'active', 'notes', 'lotus_tree_count', 'lotus_tree_count_source', 'lotus_estimated_flowering_date',
                'lotus_inferred_planting_date', 'lotus_estimation_basis', 'lotus_estimated_sucker_selection_date']
MANAGERS = ('System Manager', 'Lotus Farm Manager')


def can_edit():
    return frappe.session.user == 'Administrator' or bool(set(MANAGERS) & set(frappe.get_roles()))


def _editor():
    if frappe.session.user == 'Guest':
        frappe.throw('Vui lòng đăng nhập.', frappe.AuthenticationError)
    if not can_edit():
        frappe.throw('Chỉ Quản lý vườn, Quản trị hệ thống hoặc Administrator được sửa vườn, lô, thửa.', frappe.PermissionError)


def _fields(doctype, wanted):
    meta = frappe.get_meta(doctype)
    return [f for f in wanted if f in ('name', 'modified') or meta.has_field(f)]


def _farm(farm):
    doc = frappe.get_doc('Farm', farm)
    doc.check_permission('read')
    return doc


def _blocks(farm=None):
    filters = {'farm': farm} if farm else {}
    return frappe.get_list('Farm Block', filters=filters, fields=_fields('Farm Block', BLOCK_FIELDS), order_by='farm, block_code', limit_page_length=0)


@frappe.whitelist()
def overview(farm=None):
    """Farms the user may see, and the lots of one farm (or all) with plots, map and data gaps."""
    if frappe.session.user == 'Guest':
        frappe.throw('Vui lòng đăng nhập.', frappe.AuthenticationError)
    farms = frappe.get_list('Farm', fields=['name', 'farm_name', 'area_ha', 'location', 'company'], order_by='name', limit_page_length=0)
    if farm:
        _farm(farm)
    blocks = _blocks(farm)
    names = [b.name for b in blocks] or ['']
    plots = defaultdict(lambda: [0, 0.0])
    # Plots of lots the user may see (the lot list is permission-filtered; plot read may not be granted).
    for p in frappe.get_all('Farm Plot', filters={'farm_block': ['in', names]}, fields=['farm_block', 'area_ha'], limit_page_length=0):
        plots[p.farm_block][0] += 1
        plots[p.farm_block][1] += flt(p.area_ha)
    # Whether a lot has a boundary is shown to everyone who sees the lot (the geometry itself stays restricted).
    mapped = set(frappe.get_all('Farm Block Geometry', filters={'farm_block': ['in', names]}, pluck='farm_block', distinct=True))
    names_of = {v.name: v.variety_name or v.name for v in frappe.get_all('Banana Variety', fields=['name', 'variety_name'], limit_page_length=0)}
    rows = []
    for b in blocks:
        row = dict(b)
        row.update(plots=plots[b.name][0], plots_area_ha=round(plots[b.name][1], 2), has_map=b.name in mapped,
                   density=rules.density(b.get('lotus_tree_count'), b.area_ha), variety_label=names_of.get(b.variety, b.variety or ''))
        row['gaps'] = rules.gaps(b, row['has_map'])
        row['modified'] = str(b.modified)
        for key in ('planting_date', 'lotus_estimated_flowering_date', 'lotus_inferred_planting_date', 'lotus_estimated_sucker_selection_date'):
            row[key] = str(row[key]) if row.get(key) else ''
        rows.append(row)
    from lotus_farm.report_charts import land_by_zone
    zones = land_by_zone(rows)
    return dict(farms=farms, farm=farm or '', blocks=rows, summary=rules.summary(rows), zones=zones,
                varieties=sorted({r['variety'] for r in rows if r.get('variety')}), can_edit=can_edit(), gap_labels=rules.GAPS,
                editable=[dict(field=f, label=label, kind=kind) for f, label, kind in rules.EDITABLE])


# One lot ---------------------------------------------------------------------------------------------

def _block(name):
    doc = frappe.get_doc('Farm Block', name)
    doc.check_permission('read')
    return doc


def _range(from_date, to_date):
    end = getdate(to_date) if to_date else getdate(nowdate())
    begin = getdate(from_date) if from_date else getdate(add_days(end, -29))
    if begin > end:
        frappe.throw('Từ ngày phải trước đến ngày.')
    return begin, end


def _list(doctype, filters, fields, order_by=None):
    if not frappe.db.exists('DocType', doctype) or not frappe.has_permission(doctype, 'read'):
        return None  # the section says "no permission" instead of an empty table
    return frappe.get_list(doctype, filters=filters, fields=_fields(doctype, fields), order_by=order_by, limit_page_length=5000)


def _overview(doc):
    plots = frappe.get_all('Farm Plot', filters={'farm_block': doc.name}, fields=['name', 'modified', 'plot_code', 'plot_name', 'area_ha', 'active'],
                            order_by='plot_code', limit_page_length=0)
    geometry = frappe.get_all('Farm Block Geometry', filters={'farm_block': doc.name}, fields=['geojson', 'version', 'approval_state'],
                              order_by='version desc', limit_page_length=1)
    history = []
    for v in frappe.get_all('Version', filters={'ref_doctype': 'Farm Block', 'docname': doc.name}, fields=['owner', 'creation', 'data'],
                            order_by='creation desc', limit_page_length=30):
        try:
            changed = (json.loads(v.data or '{}') or {}).get('changed') or []
        except ValueError:
            changed = []
        history.append(dict(by=frappe.db.get_value('User', v.owner, 'full_name') or v.owner, at=str(v.creation),
                            changes=[dict(field=rules.FIELD_LABELS.get(c[0]) or doc.meta.get_label(c[0]) or c[0], old=c[1], new=c[2]) for c in changed if len(c) == 3]))
    values = {f: doc.get(f) for f in BLOCK_FIELDS if f not in ('name', 'modified')}
    for key, value in values.items():
        if hasattr(value, 'isoformat'):
            values[key] = str(value)
    return dict(block=dict(values, name=doc.name, modified=str(doc.modified), farm_name=frappe.db.get_value('Farm', doc.farm, 'farm_name'),
                           density=rules.density(doc.get('lotus_tree_count'), doc.area_ha)),
                plots=plots, geometry=dict(geojson=json.loads(geometry[0].geojson), version=geometry[0].version,
                                           approval_state=geometry[0].approval_state) if geometry else None,
                history=history, can_edit=can_edit())


def _work(doc, begin, end):
    window = {'farm_block': doc.name, 'posting_date': ['between', [begin, end]], 'docstatus': 1}
    results = _list('Daily Work Result', window, ['posting_date', 'work_plan_line', 'completed_qty', 'actual_workdays'])
    by_work = {}
    if results:
        lines = {l.name: l for l in frappe.get_all('Daily Work Plan Line', filters={'name': ['in', [r.work_plan_line for r in results if r.work_plan_line] or ['']]},
                                                   fields=['name', 'work_type', 'uom'], limit_page_length=0)}
        works = {w.name: w.work_name for w in frappe.get_all('Work Type', fields=['name', 'work_name'], limit_page_length=0)}
        for r in results:
            line = lines.get(r.work_plan_line) or frappe._dict()
            key = line.work_type or 'Khác'
            row = by_work.setdefault(key, dict(work=works.get(key, key), uom=line.uom or '', qty=0.0, workdays=0.0, days=set(), last=''))
            row['qty'] += flt(r.completed_qty)
            row['workdays'] += flt(r.actual_workdays)
            row['days'].add(str(r.posting_date))
            row['last'] = max(row['last'], str(r.posting_date))
    work = sorted(({**v, 'days': len(v['days'])} for v in by_work.values()), key=lambda v: -v['workdays'])
    labor = _list('Labor Allocation', window, ['work_team', 'allocated_workdays'])
    teams = defaultdict(float)
    for r in labor or []:
        teams[r.work_team or 'Chưa ghi đội'] += flt(r.allocated_workdays)
    used = _list('Material Consumption', window, ['item', 'uom', 'consumed_qty', 'issued_qty'])
    needed = _list('Material Requirement', window, ['name'])
    items = {}
    for r in used or []:
        row = items.setdefault(r.item, dict(item=r.item, uom=r.uom, consumed=0.0, issued=0.0, required=0.0))
        row['consumed'] += flt(r.consumed_qty)
        row['issued'] += flt(r.issued_qty)
    if needed:
        for line in frappe.get_all('Material Requirement Line', filters={'parent': ['in', [n.name for n in needed]], 'parenttype': 'Material Requirement'},
                                   fields=['item', 'uom', 'required_qty'], limit_page_length=0):
            row = items.setdefault(line.item, dict(item=line.item, uom=line.uom, consumed=0.0, issued=0.0, required=0.0))
            row['required'] += flt(line.required_qty)
    names = {i.name: i.item_name for i in frappe.get_all('Item', filters={'name': ['in', list(items) or ['']]}, fields=['name', 'item_name'])}
    materials = sorted(({**v, 'item_name': names.get(v['item'], v['item'])} for v in items.values()), key=lambda v: v['item_name'])
    return dict(work=work if results is not None else None, teams=[dict(team=k, workdays=round(v, 2)) for k, v in sorted(teams.items(), key=lambda kv: -kv[1])] if labor is not None else None,
                materials=materials if used is not None else None)


def _yield(doc, begin, end):
    from lotus_farm.block_forecast import board
    forecasts = board(farm=doc.farm, block=doc.name)['months']
    harvests = _list('Harvest Actual', {'farm_block': doc.name, 'harvest_date': ['between', [begin, end]], 'docstatus': 1},
                     ['harvest_date', 'harvested_bunch_qty', 'gross_weight_kg', 'saleable_weight_kg', 'rejected_weight_kg'], order_by='harvest_date desc')
    cancels = _list('Bunch Cancellation', {'farm_block': doc.name, 'posting_date': ['between', [begin, end]], 'docstatus': 1}, ['reason', 'bunch_qty'])
    reasons = defaultdict(int)
    for c in cancels or []:
        reasons[c.reason or 'Chưa ghi nguyên nhân'] += int(c.bunch_qty or 0)
    labels = {r.name: r.reason_name for r in frappe.get_all('Cancellation Reason', fields=['name', 'reason_name'], limit_page_length=0)} if reasons else {}
    measures = _list('Fruit Measurement', {'farm_block': doc.name, 'docstatus': 1}, ['posting_date', 'sample_count', 'average_length', 'average_diameter', 'uom'],
                     order_by='posting_date desc')
    total = lambda rows, f: round(sum(flt(r.get(f)) for r in rows or []), 2)
    return dict(forecasts=forecasts,
                harvest=dict(rows=(harvests or [])[:30], bunches=int(total(harvests, 'harvested_bunch_qty')), gross_kg=total(harvests, 'gross_weight_kg'),
                             saleable_kg=total(harvests, 'saleable_weight_kg')) if harvests is not None else None,
                cancellations=[dict(reason=labels.get(k, k), bunches=v) for k, v in sorted(reasons.items(), key=lambda kv: -kv[1])] if cancels is not None else None,
                measurements=(measures or [])[:6] if measures is not None else None)


def _care(doc, begin, end):
    window = {'farm_block': doc.name, 'posting_date': ['between', [begin, end]], 'docstatus': 1}
    diseases = _list('Disease Observation', window, ['disease', 'affected_plants', 'severity', 'posting_date'])
    by_disease = {}
    for d in diseases or []:
        row = by_disease.setdefault(d.disease, dict(disease=d.disease, observations=0, plants=0, severity='', last=''))
        row['observations'] += 1
        row['plants'] += int(d.affected_plants or 0)
        row['last'] = max(row['last'], str(d.posting_date))
        row['severity'] = d.severity if str(d.posting_date) >= row['last'] else row['severity']
    ops = _list('Bunch Operation', {'farm_block': doc.name, 'operation_date': ['between', [begin, end]], 'docstatus': 1},
                ['operation_date', 'operation_type', 'net_bunch_qty', 'bunch_qty'])
    weeks = {}
    for o in ops or []:
        day = getdate(o.operation_date)
        week = str(add_days(day, -day.weekday()))
        row = weeks.setdefault((week, o.operation_type), dict(week=week, operation=o.operation_type, bunches=0))
        row['bunches'] += int(o.net_bunch_qty or o.bunch_qty or 0)
    planting = _list('Planting Event', window, ['posting_date', 'event_type', 'plant_qty', 'area_ha', 'notes'], order_by='posting_date desc')
    return dict(diseases=sorted(by_disease.values(), key=lambda r: r['last'], reverse=True) if diseases is not None else None,
                operations=sorted(weeks.values(), key=lambda r: (r['week'], r['operation']), reverse=True) if ops is not None else None,
                planting=planting)


@frappe.whitelist()
def block_detail(block, section='overview', from_date=None, to_date=None):
    """One section of a lot's page, loaded when its tab opens: overview | work | yield | care."""
    doc = _block(block)
    if section == 'overview':
        return _overview(doc)
    begin, end = _range(from_date, to_date)
    loader = {'work': _work, 'yield': _yield, 'care': _care}.get(section)
    if not loader:
        frappe.throw('Mục không hợp lệ.')
    return dict(loader(doc, begin, end), from_date=str(begin), to_date=str(end))


# Editing ---------------------------------------------------------------------------------------------

def _apply(doc, values):
    """Allowed fields only, through the same parser as the Excel file."""
    kinds = {f: kind for f, _, kind in rules.EDITABLE}
    for field, value in (values or {}).items():
        if field not in kinds or not doc.meta.has_field(field):
            continue
        try:
            parsed = rules.parse_cell(kinds[field], value)
        except (TypeError, ValueError) as exc:
            frappe.throw(rules.FIELD_LABELS[field] + ': ' + str(exc))
        doc.set(field, parsed if parsed is not None or kinds[field] in ('text', 'date') else 0)
    if doc.get('variety') and not frappe.db.exists('Banana Variety', doc.variety):
        frappe.throw('Giống "' + str(doc.variety) + '" chưa có trong danh mục giống.')


@frappe.whitelist(methods=['POST'])
def save_block(name, modified, values):
    _editor()
    from lotus_farm.controls import lock
    lock('Farm Block', name)
    doc = _block(name)
    if str(doc.modified) != str(modified):
        frappe.throw('Lô vừa được người khác sửa. Tải lại trước khi lưu.')
    values = frappe.parse_json(values) if isinstance(values, str) else values
    before = doc.get('lotus_tree_count')
    _apply(doc, values)
    if flt(doc.get('lotus_tree_count')) != flt(before) and not str(values.get('lotus_tree_count_source') or '').strip():
        frappe.throw('Đổi số cây cần ghi Nguồn số cây (ai đếm, ngày nào).')
    doc.flags.ignore_permissions = True  # role checked by _editor; farm checked by _block
    doc.save()
    return _overview(doc)


@frappe.whitelist(methods=['POST'])
def save_plot(block, values, name=None, modified=None):
    """Add or edit a plot of a lot (code, name, area, active)."""
    _editor()
    parent = _block(block)
    values = frappe.parse_json(values) if isinstance(values, str) else values
    if name:
        doc = frappe.get_doc('Farm Plot', name)
        if doc.farm_block != parent.name or str(doc.modified) != str(modified):
            frappe.throw('Thửa vừa thay đổi hoặc không thuộc lô này. Tải lại.')
    else:
        doc = frappe.new_doc('Farm Plot')
        doc.update(dict(company=frappe.db.get_value('Farm', parent.farm, 'company'), farm=parent.farm, farm_block=parent.name, active=1))
    code = str(values.get('plot_code') or doc.get('plot_code') or '').strip()
    if not code:
        frappe.throw('Nhập mã thửa.')
    doc.plot_code = code[:140]
    doc.plot_name = str(values.get('plot_name') or doc.get('plot_name') or code).strip()[:140]
    doc.area_ha = rules.parse_cell('float', values.get('area_ha', doc.get('area_ha'))) or 0
    active = values.get('active', doc.get('active') if name else 1)
    doc.active = 1 if active in (1, True, '1', 'true', 'True') else 0
    doc.flags.ignore_permissions = True
    doc.save() if name else doc.insert()
    return _overview(parent)


# Excel round-trip --------------------------------------------------------------------------------------

@frappe.whitelist()
def export_blocks(farm):
    """Lots of a farm as .xlsx: the lot code is the key, the other columns can be edited and imported back."""
    _farm(farm)
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    book = Workbook()
    sheet = book.active
    sheet.title = 'Lô'
    header = ['Mã lô (không sửa)', *[label for _, label, _ in rules.EDITABLE], 'Số thửa', 'Tổng diện tích thửa (ha)']
    sheet.append(header)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    sheet['A1'].fill = PatternFill('solid', fgColor='E3E6EA')
    data = overview(farm)
    for b in data['blocks']:
        values = []
        for field, _, kind in rules.EDITABLE:
            value = b.get(field)
            if kind == 'date' and value:
                value = value[8:10] + '/' + value[5:7] + '/' + value[0:4]
            values.append(value if value not in (None, '') else '')
        sheet.append([b['block_code'], *values, b['plots'], b['plots_area_ha']])
    sheet.freeze_panes = 'B2'
    for column, width in zip('ABCDEFGHIJKLMN', (16, 22, 8, 12, 14, 13, 18, 12, 14, 26, 14, 30, 9, 16)):
        sheet.column_dimensions[column].width = width
    out = BytesIO()
    book.save(out)
    frappe.local.response.filename = 'lo-' + str(farm) + '.xlsx'
    frappe.local.response.filecontent = out.getvalue()
    frappe.local.response.type = 'download'


def _read_rows(content):
    from openpyxl import load_workbook
    sheet = load_workbook(BytesIO(content), read_only=True, data_only=True).worksheets[0]
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        frappe.throw('File trống.')
    labels = {label: field for field, label, _ in rules.EDITABLE}
    header = [str(h or '').strip() for h in rows[0]]
    if not header or not header[0].startswith('Mã lô'):
        frappe.throw('Cột đầu tiên phải là "Mã lô". Hãy dùng file tải từ nút Xuất Excel.')
    columns = {i: labels[h] for i, h in enumerate(header) if h in labels}
    result = []
    for number, row in enumerate(rows[1:], start=2):
        if not row or row[0] in (None, ''):
            continue
        values = {}
        for i, field in columns.items():
            cell = row[i] if i < len(row) else None
            values[field] = cell.strftime('%Y-%m-%d') if hasattr(cell, 'strftime') else cell
        result.append(dict(line=number, code=str(row[0]).strip(), values=values))
    return result


@frappe.whitelist(methods=['POST'])
def preview_blocks(farm, content):
    """content: base64 of the edited .xlsx -> every row with its changes, errors and warnings; nothing is saved."""
    _editor()
    _farm(farm)
    import base64
    rows = _read_rows(base64.b64decode(content.split(',', 1)[-1]))
    data = overview(farm)
    by_code = {b['block_code']: b for b in data['blocks']}
    zones = {b['farm_zone'] for b in data['blocks'] if b.get('farm_zone')}
    preview = []
    for row in rows:
        current = by_code.get(row['code'])
        if not current:
            preview.append(dict(line=row['line'], code=row['code'], block=None, changes=[], errors=['Mã lô không có trong vườn'], warnings=[]))
            continue
        result = rules.diff_row(current, row['values'], plots_area=current['plots_area_ha'], known_zones=zones)
        if result['changes'].get('variety') and not frappe.db.exists('Banana Variety', result['changes']['variety'][1]):
            result['errors'].append('Giống "%s" chưa có trong danh mục giống' % result['changes']['variety'][1])
        preview.append(dict(line=row['line'], code=row['code'], block=current['name'], modified=current['modified'],
                            changes=[dict(field=f, label=rules.FIELD_LABELS[f], old=o, new=n) for f, (o, n) in result['changes'].items()],
                            errors=result['errors'], warnings=result['warnings']))
    token = frappe.generate_hash(length=20)
    ready = [p for p in preview if p['block'] and p['changes'] and not p['errors']]
    frappe.cache.set_value('lotus_land_import:' + frappe.session.user + ':' + token,
                           json.dumps(dict(farm=farm, rows=[dict(block=p['block'], modified=p['modified'], values={c['field']: c['new'] for c in p['changes']}) for p in ready]),
                                      default=str), expires_in_sec=1800)
    return dict(token=token, rows=preview, ready=len(ready), unchanged=sum(1 for p in preview if p['block'] and not p['changes'] and not p['errors']),
                errors=sum(1 for p in preview if p['errors']))


@frappe.whitelist(methods=['POST'])
def commit_blocks(farm, token):
    """Apply the rows the preview found valid; a lot changed since the preview is skipped and reported."""
    _editor()
    _farm(farm)
    raw = frappe.cache.get_value('lotus_land_import:' + frappe.session.user + ':' + str(token))
    if not raw:
        frappe.throw('Bản xem trước đã hết hạn. Tải file lên lại.')
    plan = json.loads(raw)
    if plan['farm'] != farm:
        frappe.throw('Bản xem trước thuộc vườn khác.')
    from lotus_farm.controls import lock
    saved, skipped = 0, []
    for row in plan['rows']:
        lock('Farm Block', row['block'])
        doc = _block(row['block'])
        if str(doc.modified) != row['modified']:
            skipped.append(doc.block_code)
            continue
        _apply(doc, row['values'])
        doc.flags.ignore_permissions = True
        doc.save()
        saved += 1
    frappe.cache.delete_value('lotus_land_import:' + frappe.session.user + ':' + str(token))
    return dict(saved=saved, skipped=skipped)


def install():
    """Keep a change history of lots (who changed area, tree count, variety, when)."""
    from frappe.custom.doctype.property_setter.property_setter import make_property_setter
    for doctype in ('Farm Block', 'Farm Plot'):
        if frappe.db.exists('DocType', doctype) and not frappe.get_meta(doctype).track_changes:
            make_property_setter(doctype, None, 'track_changes', 1, 'Check', for_doctype=True, validate_fields_for_doctype=False)
