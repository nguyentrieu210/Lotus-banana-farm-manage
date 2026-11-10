"""Vườn & lô: the lot list of a farm with area, trees, density and data gaps; one lot's page (map, work and
materials, yield and losses, disease and bunch care, change history); editing lots; and the Excel
round-trip (export, preview every change, apply the valid rows). The lô is the smallest unit of land.

Everyone with read on Farm Block sees the lots of the farms they are permitted; Administrator, System
Manager and Lotus Farm Manager edit. What was done and harvested on a lot is read from the confirmed lines
of the sổ lô (Lotus Work Entry). Rules and the Excel comparison live in lotus_farm.farm_land_rules.
"""
import json
from collections import defaultdict
from io import BytesIO

import frappe
from frappe.utils import add_days, cint, flt, getdate, nowdate

from lotus_farm import farm_land_rules as rules

ENTRY = 'Lotus Work Entry'
CARE_STAGES = ('Bud Injection', 'Cut Bud', 'Bag', 'Care', 'Prop')
BLOCK_FIELDS = ['name', 'modified', 'farm', 'block_code', 'block_name', 'farm_zone', 'area_ha', 'variety', 'planting_date', 'planting_density',
                'irrigation_zone', 'manager', 'active', 'notes', 'lotus_tree_count', 'lotus_tree_count_source', 'lotus_estimated_flowering_date',
                'lotus_inferred_planting_date', 'lotus_estimation_basis', 'lotus_estimated_sucker_selection_date', 'lotus_current_cycle_no']
MANAGERS = ('System Manager', 'Lotus Farm Manager')


def can_edit():
    return frappe.session.user == 'Administrator' or bool(set(MANAGERS) & set(frappe.get_roles()))


def _editor():
    if frappe.session.user == 'Guest':
        frappe.throw('Vui lòng đăng nhập.', frappe.AuthenticationError)
    if not can_edit():
        frappe.throw('Chỉ Quản lý vườn, Quản trị hệ thống hoặc Administrator được sửa vườn, lô.', frappe.PermissionError)


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
    """Farms the user may see, and the lots of one farm (or all) with map and data gaps."""
    if frappe.session.user == 'Guest':
        frappe.throw('Vui lòng đăng nhập.', frappe.AuthenticationError)
    farms = frappe.get_list('Farm', fields=['name', 'farm_name', 'area_ha', 'location', 'company'], order_by='name', limit_page_length=0)
    if farm:
        _farm(farm)
    blocks = _blocks(farm)
    names = [b.name for b in blocks] or ['']
    # Whether a lot has a boundary is shown to everyone who sees the lot (the geometry itself stays restricted).
    mapped = set(frappe.get_all('Farm Block Geometry', filters={'farm_block': ['in', names]}, pluck='farm_block', distinct=True))
    names_of = {v.name: v.variety_name or v.name for v in frappe.get_all('Banana Variety', fields=['name', 'variety_name'], limit_page_length=0)}
    rows = []
    for b in blocks:
        row = dict(b)
        row.update(has_map=b.name in mapped, density=rules.density(b.get('lotus_tree_count'), b.area_ha),
                   variety_label=names_of.get(b.variety, b.variety or ''))
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


def _lines(doc, begin, end, fields, **filters):
    """Confirmed lines of the sổ lô on this lot in the range. None when the user may not read the sổ lô: the
    section then says "no permission" instead of showing an empty table."""
    if not frappe.has_permission(ENTRY, 'read'):
        return None
    filters.update(farm_block=doc.name, state='Confirmed', posting_date=['between', [begin, end]])
    return frappe.get_all(ENTRY, filters=filters, fields=fields, limit_page_length=0)


def _overview(doc):
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
                geometry=dict(geojson=json.loads(geometry[0].geojson), version=geometry[0].version,
                              approval_state=geometry[0].approval_state) if geometry else None,
                history=history, can_edit=can_edit())


def _work(doc, begin, end):
    """What was done on the lot: every việc with its quantity and công, công by tổ, and the materials reported used."""
    lines = _lines(doc, begin, end, ['name', 'work_type', 'work_team', 'qty', 'uom', 'posting_date'])
    if lines is None:
        return dict(work=None, teams=None, materials=None)
    from lotus_farm.field_reports import _works
    entries = [l.name for l in lines] or ['']
    # A buổi is half a công; a buổi shared between lines carries its share (weight) on each of them.
    workdays = defaultdict(float)
    for s in frappe.get_all('Lotus Work Session', filters={'entry': ['in', entries]}, fields=['entry', 'weight'], limit_page_length=0):
        workdays[s.entry] += flt(s.weight) / 2
    works = _works({l.work_type for l in lines})
    by_work, by_team = {}, defaultdict(float)
    for l in lines:
        row = by_work.setdefault(l.work_type, dict(work=works.get(l.work_type, l.work_type), uom=l.uom or '', qty=0.0, workdays=0.0, days=set(), last=''))
        row['qty'] += flt(l.qty)
        row['workdays'] += workdays[l.name]
        row['days'].add(str(l.posting_date))
        row['last'] = max(row['last'], str(l.posting_date))
        by_team[l.work_team] += workdays[l.name]
    work = sorted(({**v, 'days': len(v['days'])} for v in by_work.values()), key=lambda v: -v['workdays'])
    teams = {t.name: t.team_name for t in frappe.get_all('Work Team', filters={'name': ['in', [t for t in by_team if t] or ['']]}, fields=['name', 'team_name'])}
    items = {}
    for m in frappe.get_all('Lotus Work Entry Material', filters={'parenttype': ENTRY, 'parent': ['in', entries]}, fields=['item_code', 'uom', 'qty'],
                            limit_page_length=0):
        row = items.setdefault(m.item_code, dict(item=m.item_code, uom=m.uom, used=0.0))
        row['used'] += flt(m.qty)
    names = {i.name: i.item_name for i in frappe.get_all('Item', filters={'name': ['in', list(items) or ['']]}, fields=['name', 'item_name'])}
    return dict(work=work,
                teams=[dict(team=teams.get(k, k) or 'Chưa ghi tổ', workdays=round(v, 2)) for k, v in sorted(by_team.items(), key=lambda kv: -kv[1]) if v],
                materials=sorted(({**v, 'item_name': names.get(v['item'], v['item'])} for v in items.values()), key=lambda v: v['item_name']))


def _yield(doc, begin, end):
    """The forecast of the lot by month, and what the sổ lô holds for the range: bunches harvested with their weight,
    and bunches rejected by reason."""
    from lotus_farm.block_forecast import board
    forecasts = board(farm=doc.farm, block=doc.name)['months']
    lines = _lines(doc, begin, end, ['stage', 'qty', 'weight_kg', 'reason'], stage=['in', ['Harvest', 'Reject']])
    if lines is None:
        return dict(forecasts=forecasts, harvest=None, cancellations=None)
    harvested = [l for l in lines if l.stage == 'Harvest']
    reasons = defaultdict(int)
    for l in lines:
        if l.stage == 'Reject':
            reasons[l.reason or 'Chưa ghi nguyên nhân'] += cint(l.qty)
    labels = {r.name: r.reason_name for r in frappe.get_all('Cancellation Reason', fields=['name', 'reason_name'], limit_page_length=0)} if reasons else {}
    return dict(forecasts=forecasts,
                harvest=dict(lines=len(harvested), bunches=sum(cint(l.qty) for l in harvested), kg=round(sum(flt(l.weight_kg) for l in harvested), 2)),
                cancellations=[dict(reason=labels.get(k, k), bunches=v) for k, v in sorted(reasons.items(), key=lambda kv: -kv[1])])


def _care(doc, begin, end):
    """Diseases noted on the lot (the latest severity kept) and bunch care by week and stage, from the sổ lô."""
    lines = _lines(doc, begin, end, ['posting_date', 'stage', 'qty', 'disease', 'severity'])
    if lines is None:
        return dict(diseases=None, operations=None)
    names = {d.name: d.disease_name for d in frappe.get_all('Disease', fields=['name', 'disease_name'], limit_page_length=0)}
    by_disease, weeks = {}, {}
    for l in sorted(lines, key=lambda l: str(l.posting_date)):
        if l.disease:
            row = by_disease.setdefault(l.disease, dict(disease=names.get(l.disease) or l.disease, observations=0, plants=0, severity='', last=''))
            row['observations'] += 1
            row['plants'] += cint(l.qty)
            row['last'], row['severity'] = str(l.posting_date), l.severity or ''
        if l.stage in CARE_STAGES:
            day = getdate(l.posting_date)
            week = str(add_days(day, -day.weekday()))
            row = weeks.setdefault((week, l.stage), dict(week=week, stage=l.stage, qty=0))
            row['qty'] += cint(l.qty)
    return dict(diseases=sorted(by_disease.values(), key=lambda r: r['last'], reverse=True),
                operations=sorted(weeks.values(), key=lambda r: (r['week'], r['stage']), reverse=True))


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
    header = ['Mã lô (không sửa)', *[label for _, label, _ in rules.EDITABLE]]
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
        sheet.append([b['block_code'], *values])
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
        result = rules.diff_row(current, row['values'], known_zones=zones)
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
    if frappe.db.exists('DocType', 'Farm Block') and not frappe.get_meta('Farm Block').track_changes:
        make_property_setter('Farm Block', None, 'track_changes', 1, 'Check', for_doctype=True, validate_fields_for_doctype=False)
