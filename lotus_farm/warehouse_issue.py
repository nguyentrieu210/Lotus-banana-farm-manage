"""Approved-request picking and locked quantity limits for warehouse issues."""
from collections import defaultdict

import frappe
from frappe.utils import flt
from lotus_farm.controls import lock


def install_fields():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    create_custom_fields({
        'Stock Entry': [
            dict(fieldname='lotus_issue_mode', label='Lotus Issue Mode', fieldtype='Select',
                 options='\nManual\nRequest', read_only=1, no_copy=1, insert_after='stock_entry_type'),
            dict(fieldname='lotus_receiver', label='Tên người nhận (HRMS)', fieldtype='Data', read_only=1, insert_after='lotus_issue_mode'),
            dict(fieldname='lotus_receiver_employee', label='Người nhận vật tư (HRMS)', fieldtype='Link', options='Employee', insert_after='lotus_receiver'),
        ],
        'Stock Entry Detail': [
            dict(fieldname='lotus_usage_area', label='Khu vực / lô sử dụng', fieldtype='Data', insert_after='item_code'),
        ],
        'Material Request Item': [
            dict(fieldname='lotus_usage_area', label='Khu vực / lô sử dụng', fieldtype='Data', insert_after='item_code'),
        ],
    })


def approved(name, company):
    """The approved material issue request `name` of the company, read with the user's permission."""
    doc = frappe.get_doc('Material Request', name)
    doc.check_permission('read')
    if doc.docstatus != 1 or doc.company != company:
        frappe.throw('Nguồn phải đã duyệt và thuộc công ty đang chọn.')
    if doc.material_request_type != 'Material Issue':
        frappe.throw('Chỉ dùng yêu cầu cấp vật tư, không dùng đề xuất mua hoặc chuyển kho.')
    if doc.get('status') in ('Stopped', 'Closed', 'Cancelled'):
        frappe.throw('Yêu cầu đã đóng hoặc dừng, không thể cấp thêm.')
    return doc


def source_line(name, line_name, company):
    doc = approved(name, company)
    row = next((r for r in doc.items if r.name == line_name), None)
    if not row:
        frappe.throw('Dòng yêu cầu không hợp lệ.')
    item = frappe.get_doc('Item', row.item_code)
    item.check_permission('read')
    return dict(item=item.name, item_name=item.item_name, uom=item.stock_uom,
                required_qty=flt(row.stock_qty), area=row.get('lotus_usage_area') or '',
                material_request=doc.name, material_request_item=row.name,warehouse=row.warehouse,
                # Spec 005: the lô and việc of the request line go onto the issue line (validate_issue).
                farm=row.get('lotus_farm') or None, farm_block=row.get('lotus_farm_block') or None,
                work_type=row.get('lotus_work_type') or None)


def allocation_totals(name, line_name, exclude=None):
    # The request has already been permission-checked. Count all allocations,
    # including those made by another stock user, without exposing their documents.
    result = frappe.db.sql('''select p.docstatus, coalesce(sum(d.qty * d.conversion_factor), 0)
        from `tabStock Entry Detail` d join `tabStock Entry` p on p.name=d.parent
        where p.docstatus < 2 and p.stock_entry_type='Material Issue' and p.name != %(exclude)s
        and d.material_request=%(name)s and d.material_request_item=%(line)s group by p.docstatus''',
        dict(exclude=exclude or '', name=name, line=line_name))
    return dict(draft=sum(flt(r[1]) for r in result if r[0]==0),posted=sum(flt(r[1]) for r in result if r[0]==1))


def allocated(name,line_name,exclude=None):
    return sum(allocation_totals(name,line_name,exclude).values())


def choices(company, mode):
    from lotus_farm.warehouse import _access, _company
    _access()
    _company(company)
    if mode != 'Request':
        frappe.throw('Tab nguồn xuất không hợp lệ.')
    if not frappe.has_permission('Material Request', 'read'):
        return dict(rows=[], note='Tài khoản chưa có quyền đọc nguồn này.')
    # Spec 005: a request already issued in full is no longer offered; the label names đội/tổ, lô, việc and ngày cần.
    filters = dict(company=company, docstatus=1, material_request_type='Material Issue',
                   status=['not in', ['Stopped', 'Closed', 'Cancelled', 'Issued']])
    rows = frappe.get_list('Material Request', filters=filters, fields=['name', 'transaction_date', 'schedule_date', 'title'],
                           order_by='transaction_date desc, modified desc', limit_page_length=100)
    return dict(rows=[dict(name=r.name, date=r.transaction_date, needed=r.schedule_date, label=_label(r)) for r in rows],
                note='Hiển thị tối đa 100 nguồn đã duyệt gần nhất.')


def _label(row):
    needed = row.get('schedule_date')
    day = needed.strftime('%d/%m') if hasattr(needed, 'strftime') else str(needed or '')[8:10] + '/' + str(needed or '')[5:7]
    parts = [row.get('name'), row.get('title') if row.get('title') != row.get('name') else None, ('cần ' + day) if needed else None]
    return ' · '.join(p for p in parts if p)


def _header(doc):
    """Who and what of a request, for the issue form (spec 005): kho, người nhận, người lập, đội/tổ, việc, người duyệt."""
    def user_name(user):
        return (frappe.db.get_value('User', user, 'full_name') or user) if user else ''

    def team_name(team):
        return (frappe.db.get_value('Work Team', team, 'team_name') or team) if team else ''
    work = next((r.get('lotus_work_type') for r in doc.items if r.get('lotus_work_type')), None)
    receiver = doc.get('lotus_issue_receiver')
    return dict(name=doc.name, title=doc.get('title') or doc.name, warehouse=doc.get('set_warehouse') or '',
                needed=str(doc.get('schedule_date') or ''), receiver=receiver or '',
                receiver_name=(frappe.db.get_value('Employee', receiver, 'employee_name') or receiver) if receiver else '',
                requester=doc.owner, requester_name=user_name(doc.owner),
                crew=doc.get('lotus_crew') or '', crew_name=team_name(doc.get('lotus_crew')),
                team=doc.get('lotus_work_team') or '', team_name=team_name(doc.get('lotus_work_team')),
                work_type=work or '', work_name=(frappe.db.get_value('Work Type', work, 'work_name') or work) if work else '',
                approved_by=doc.get('lotus_issue_approved_by') or '', approved_by_name=user_name(doc.get('lotus_issue_approved_by')),
                approved_at=str(doc.get('lotus_issue_approved_at') or ''), note=doc.get('lotus_request_note') or '')


def queue(company, warehouse=None):
    """Spec 005, Kho › Xuất kho › Cấp theo yêu cầu: approved requests not closed with something left to issue, earliest
    ngày cần first."""
    from lotus_farm.warehouse import _access, _company
    from lotus_farm import issue_request
    from lotus_farm import issue_request_rules as rules
    from frappe.utils import nowdate
    _access()
    _company(company)
    if not frappe.has_permission('Material Request', 'read'):
        return dict(rows=[], count=0, note='Tài khoản chưa có quyền đọc yêu cầu cấp vật tư.')
    filters = dict(company=company, docstatus=1, material_request_type='Material Issue',
                   status=['not in', ['Stopped', 'Closed', 'Cancelled', 'Issued']])
    if warehouse:
        filters['set_warehouse'] = warehouse
    heads = frappe.get_list('Material Request', filters=filters, fields=issue_request.HEAD_FIELDS,
                            order_by='schedule_date asc, transaction_date asc', limit_page_length=500)
    lines = issue_request._progress([h.name for h in heads])
    blocks = issue_request._codes([l.lotus_farm_block for ls in lines.values() for l in ls])
    works = {w.name: w.work_name for w in frappe.get_all('Work Type', filters={'name': ['in', list({l.lotus_work_type for ls in lines.values() for l in ls if l.lotus_work_type}) or ['']]},
                                                       fields=['name', 'work_name'])}
    teams = {t.name: t.team_name for t in frappe.get_all('Work Team', filters={'name': ['in', list({x for h in heads for x in (h.lotus_crew, h.lotus_work_team) if x}) or ['']]},
                                                         fields=['name', 'team_name'])}
    users = {u.name: u.full_name or u.name for u in frappe.get_all('User', filters={'name': ['in', list({x for h in heads for x in (h.owner, h.lotus_issue_approved_by) if x}) or ['']]},
                                                                   fields=['name', 'full_name'])}
    receivers = {e.name: e.employee_name for e in frappe.get_all('Employee', filters={'name': ['in', list({h.lotus_issue_receiver for h in heads if h.lotus_issue_receiver}) or ['']]},
                                                                 fields=['name', 'employee_name'])}
    today = nowdate()
    rows = []
    for h in heads:
        own = lines.get(h.name, [])
        totals = dict(required=sum(flt(l.stock_qty) for l in own), posted=sum(flt(l.posted) for l in own), draft=sum(flt(l.draft) for l in own))
        if totals['posted'] >= totals['required'] - rules.EPSILON:
            continue
        current = rules.state(h.docstatus, h.status, h.lotus_issue_sent_at, h.lotus_issue_return_reason, totals)
        work = next((l.lotus_work_type for l in own if l.lotus_work_type), None)
        rows.append(dict(name=h.name, title=h.title or h.name, label=_label(h), state=current, state_code=rules.CODES[current],
                         overdue=rules.overdue(current, h.schedule_date, today), needed=str(h.schedule_date or ''),
                         warehouse=h.set_warehouse, crew=h.lotus_crew, crew_name=teams.get(h.lotus_crew, h.lotus_crew or ''),
                         team=h.lotus_work_team, team_name=teams.get(h.lotus_work_team, '') if h.lotus_work_team else '',
                         work_type=work, work_name=works.get(work, work or ''),
                         blocks=list(dict.fromkeys(blocks.get(l.lotus_farm_block, l.lotus_farm_block) or l.lotus_usage_area
                                                   for l in own if l.lotus_farm_block or l.lotus_usage_area)),
                         lines=len(own), open_lines=sum(1 for l in own if l.remaining > 0), held=totals['draft'] > 0,
                         requester=h.owner, requester_name=users.get(h.owner, h.owner),
                         approved_by=h.lotus_issue_approved_by, approved_by_name=users.get(h.lotus_issue_approved_by, h.lotus_issue_approved_by or ''),
                         receiver=h.lotus_issue_receiver, receiver_name=receivers.get(h.lotus_issue_receiver, h.lotus_issue_receiver or '')))
    return dict(rows=rows, count=len(rows))


def lines(company, mode, name):
    from lotus_farm.warehouse import _access, _company
    from lotus_farm.warehouse_masters import item_uoms
    _access()
    _company(company)
    if mode != 'Request':
        frappe.throw('Nguồn không hợp lệ.')
    rows = []
    doc = approved(name, company)
    for row in doc.items:
        info = source_line(name, row.name, company)
        item = frappe.get_doc('Item', info['item'])
        info.update(stock_uom=item.stock_uom, uoms=item_uoms(item))
        info['allocated_qty'] = allocated(name, row.name)
        info['remaining_qty'] = max(0, info['required_qty'] - info['allocated_qty'])
        if info['remaining_qty'] > 0:
            rows.append(info)
    return dict(rows=rows, header=_header(doc), note='Phần còn cấp đã trừ phiếu nháp và phiếu đã ghi sổ; phiếu hủy không giữ số lượng.')


def validate_issue(doc, method=None):
    mode = doc.get('lotus_issue_mode')
    if doc.docstatus == 2 or not mode:
        return
    if mode not in ('Manual', 'Request') or doc.stock_entry_type != 'Material Issue':
        frappe.throw('Hình thức xuất kho không hợp lệ.')
    if doc.get('lotus_receiver_employee'):
        from lotus_farm.warehouse_masters import employee_contact
        staff=employee_contact(doc.company,doc.lotus_receiver_employee)
        # Name is a display snapshot; HRMS remains the source of truth.
        doc.lotus_receiver=staff.employee_name
    if not str(doc.get('lotus_receiver') or '').strip():
        frappe.throw('Cần nhập người nhận vật tư.')
    if mode == 'Manual' and not str(doc.remarks or '').strip():
        frappe.throw('Xuất thủ công cần lý do xuất.')
    refs = []
    for row in doc.items:
        request = row.get('material_request')
        if not str(row.get('lotus_usage_area') or '').strip():
            frappe.throw('Mỗi dòng xuất cần khu vực / lô sử dụng.')
        if mode == 'Manual':
            if request:
                frappe.throw('Xuất thủ công không được gắn nguồn yêu cầu.')
            continue
        if not request:
            frappe.throw('Dòng xuất thiếu nguồn hợp lệ của tab đã chọn.')
        refs.append((request, row.get('material_request_item'), row))
    for name in sorted({name for name, _, _ in refs}):
        lock('Material Request', name)
    totals = defaultdict(float)
    limits = {}
    for name, line_name, row in refs:
        info = source_line(name, line_name, doc.company)
        if info['item'] != row.item_code or (info['area'] and row.lotus_usage_area != info['area']):
            frappe.throw('Vật tư hoặc khu vực không khớp nguồn đã duyệt.')
        if info.get('warehouse') and info['warehouse']!=row.s_warehouse:
            frappe.throw('Kho xuất không khớp kho đã chỉ định của nhu cầu.')
        # Spec 005 (FR-022): the 621 cost goes to the lô and việc of the approved line, whatever the browser sent.
        # Requests made before spec 005 carry no lô column; their lô is still read from "Khu vực / lô sử dụng".
        if info.get('farm_block'):
            row.lotus_farm_block = info['farm_block']
            row.lotus_farm = info.get('farm')
            row.lotus_work_type = info.get('work_type')
        qty = flt(row.qty) * flt(row.conversion_factor)
        if qty <= 0:
            frappe.throw('Số lượng cấp phải lớn hơn 0.')
        key = (name, line_name)
        totals[key] += qty
        limits[key] = info['required_qty']
    for key, qty in totals.items():
        if qty + allocated(*key, exclude=doc.name) > limits[key] + 0.000001:
            frappe.throw('Số lượng cấp vượt phần còn được cấp của nguồn đã duyệt.')
