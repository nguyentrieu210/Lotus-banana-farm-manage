"""Online purchase proposal (Phiếu đề xuất mua vật tư) on ERPNext Material Request (type Purchase).

The form follows the farm's Excel template: proposer, department, reason; per line the item,
specification, unit, stock on hand, proposed quantity, expected price, needed date, suggested
supplier and purpose. Four people sign in order. The proposer picks the three later signers from HR
(employees with a login and the step's role) when sending; each one is notified when it is their turn
and only they can sign or return it (lotus_farm.signing). The director's signature submits the
request, which then appears in Mua hàng as a request waiting for an order.
"""
import frappe
from frappe.utils import flt, getdate, nowdate

from lotus_farm import proposal_rules as rules
from lotus_farm import signing, signing_rules

CHAIN = 'purchase_proposal'
WAITING_ME = 'Chờ tôi ký'  # a filter of the board, not a stage

PARENT_FIELDS = [
    dict(fieldname='lotus_proposal_policy', label='Lotus · Phiên bản duyệt mua', fieldtype='Int', read_only=1, hidden=1, no_copy=1),
    dict(fieldname='lotus_proposal_state', label='Lotus · Trạng thái đề xuất', fieldtype='Select',
         options='\n'.join(rules.STATES), default=rules.DRAFT, read_only=1, insert_after='material_request_type', in_list_view=1),
    dict(fieldname='lotus_department', label='Lotus · Bộ phận đề xuất', fieldtype='Data', insert_after='lotus_proposal_state'),
    dict(fieldname='lotus_request_note', label='Lotus · Lý do đề xuất mua', fieldtype='Small Text', insert_after='lotus_department'),
    dict(fieldname='lotus_return_reason', label='Lotus · Lý do trả lại', fieldtype='Small Text', read_only=1, insert_after='lotus_request_note'),
]
ITEM_FIELDS = [
    dict(fieldname='lotus_purchase_sources', label='Lotus · Nguồn tham khảo mua', fieldtype='Long Text', read_only=1, hidden=1),
    dict(fieldname='lotus_specification', label='Lotus · Quy cách / thông số kỹ thuật', fieldtype='Data', insert_after='description'),
    dict(fieldname='lotus_supplier_hint', label='Lotus · Nhà cung cấp đề xuất', fieldtype='Data', insert_after='lotus_specification'),
    dict(fieldname='lotus_purpose', label='Lotus · Mục đích sử dụng', fieldtype='Data', insert_after='lotus_supplier_hint'),
    dict(fieldname='lotus_notes', label='Lotus · Ghi chú', fieldtype='Small Text', insert_after='lotus_purpose'),
]
EDIT_ALL = ('item_code', 'qty', 'uom', 'warehouse', 'schedule_date', 'rate', 'lotus_specification', 'lotus_supplier_hint', 'lotus_purpose', 'lotus_notes')
EDIT_PRICES = ('rate', 'lotus_supplier_hint', 'lotus_notes')


def install_fields():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    create_custom_fields({'Material Request': PARENT_FIELDS, 'Material Request Item': ITEM_FIELDS}, update=True, ignore_validate=True)
    from lotus_farm.purchase_flow import install
    install()


def _access():
    if frappe.session.user == 'Guest':
        frappe.throw('Vui lòng đăng nhập.', frappe.AuthenticationError)



def _admin():
    return frappe.session.user == 'Administrator'


def _doc(name):
    doc = frappe.get_doc('Material Request', name)
    if not signing.can_view(doc=doc):
        doc.check_permission('read')  # raises the standard permission error
    if doc.material_request_type != 'Purchase':
        frappe.throw('Chỉ xử lý đề xuất mua vật tư.')
    from lotus_farm.warehouse import _company
    _company(doc.company)
    return doc


def _state(doc):
    if doc.docstatus == 1:
        return rules.APPROVED
    return doc.get('lotus_proposal_state') or rules.DRAFT


def _version(doc, modified):
    if not modified or str(doc.modified) != str(modified):
        frappe.throw('Phiếu đã thay đổi. Tải lại trước khi thao tác.')


def _save_signing_state(doc):
    """A named signer updates only workflow metadata, not ERP item/catalogue data."""
    values = {field: doc.get(field) for field in ('lotus_proposal_state', 'lotus_return_reason', 'lotus_proposal_policy')
              if doc.meta.has_field(field)}
    values.update(modified=frappe.utils.now_datetime(), modified_by=frappe.session.user)
    doc.db_set(values, update_modified=False)


def _stock(item, warehouse, factor=1):
    if not (item and warehouse) or not frappe.has_permission('Bin', 'read'):
        return None
    value = frappe.db.get_value('Bin', {'item_code': item, 'warehouse': warehouse}, 'actual_qty')
    return None if value is None else flt(value) / (flt(factor) or 1)


def _employee(user):
    return frappe.db.get_value('Employee', {'user_id': user, 'status': 'Active'}, ['employee_name', 'department'], as_dict=True) or {}


@frappe.whitelist()
def form_data(company):
    """Catalogue for the proposal form: items with units, warehouses, suppliers, proposer defaults."""
    _access()
    from lotus_farm.warehouse_buying_lite import setup
    data = setup(company)
    me = _employee(frappe.session.user)
    data.update(proposer=me.get('employee_name') or frappe.db.get_value('User', frappe.session.user, 'full_name') or frappe.session.user,
                department=me.get('department') or '', can_create=frappe.has_permission('Material Request', 'create'))
    return data


@frappe.whitelist()
def stock_on_hand(item, warehouse, uom=None):
    _access()
    frappe.get_doc('Item', item).check_permission('read')
    frappe.get_doc('Warehouse', warehouse).check_permission('read')
    factor = 1
    if uom:
        factor = frappe.db.get_value('UOM Conversion Detail', {'parent': item, 'uom': uom}, 'conversion_factor') or 1
    return dict(qty=_stock(item, warehouse, factor))


def _receiving_warehouse(name, company):
    """Kho nhận: a real (not group), enabled warehouse of the proposal's company that the user may read."""
    row = frappe.db.get_value('Warehouse', name, ['company', 'is_group', 'disabled'], as_dict=True)
    if not row:
        frappe.throw('Không tìm thấy kho nhận: ' + str(name))
    frappe.get_doc('Warehouse', name).check_permission('read')
    if row.company != company or row.is_group or row.disabled:
        frappe.throw('Kho nhận phải là kho đang dùng của công ty: ' + str(name))
    return name


def _apply_lines(doc, rows, allowed):
    if not isinstance(rows, list) or not 1 <= len(rows) <= 150:
        frappe.throw('Phiếu cần từ 1 đến 150 dòng vật tư.')
    issues = rules.line_issues(rows)
    if issues:
        frappe.throw('; '.join(issues[:6]))
    if allowed == 'prices':
        if len(rows) != len(doc.items):
            frappe.throw('Kế toán / mua hàng chỉ sửa đơn giá, nhà cung cấp và ghi chú.')
        for line, row in zip(doc.items, rows):
            if row.get('item_code') != line.item_code or row.get('name') and row['name'] != line.name:
                frappe.throw('Dòng cập nhật giá không khớp đề xuất gốc. Tải lại phiếu.')
            for field in EDIT_PRICES:
                line.set(field, flt(row.get(field)) if field == 'rate' else str(row.get(field) or '')[:500])
            line.amount = flt(line.qty) * flt(line.rate)
        return
    lines = []
    for row in rows:
        item = frappe.get_doc('Item', row['item_code'])
        item.check_permission('read')
        if item.disabled:
            frappe.throw('Vật tư đã ngừng sử dụng: ' + item.item_name)
        uom = row.get('uom') or item.stock_uom
        factor = 1 if uom == item.stock_uom else flt(next((u.conversion_factor for u in item.uoms if u.uom == uom), 0))
        if factor <= 0:
            frappe.throw('Đơn vị chưa có quy đổi: ' + item.item_name + ' (' + uom + ')')
        warehouse = row.get('warehouse') or doc.get('set_warehouse')
        if not warehouse:
            frappe.throw('Chọn kho nhận cho ' + item.item_name)
        _receiving_warehouse(warehouse, doc.company)
        line = {field: row.get(field) for field in EDIT_ALL}
        from lotus_farm.procurement import line_fields
        line.update(line_fields(item, row))
        line.update(item_code=item.name, uom=uom, stock_uom=item.stock_uom, conversion_factor=factor, warehouse=warehouse,
                    qty=flt(row['qty']), rate=flt(row.get('rate')), schedule_date=getdate(row['schedule_date']))
        for field in ('lotus_specification', 'lotus_supplier_hint', 'lotus_purpose'):
            line[field] = str(line.get(field) or '')[:140]
        line['lotus_notes'] = str(line.get('lotus_notes') or '')[:500]
        lines.append(line)
    doc.set('items', lines)
    doc.schedule_date = min(getdate(l['schedule_date']) for l in lines)


@frappe.whitelist(methods=['POST'])
def save_proposal(company, values, name=None, modified=None):
    _access()
    from lotus_farm.warehouse import _company
    _company(company)
    values = frappe.parse_json(values) if isinstance(values, str) else values
    if not isinstance(values, dict):
        frappe.throw('Dữ liệu phiếu không hợp lệ.')
    reason = str(values.get('reason') or '').strip()
    from lotus_farm.controls import lock
    if name:
        lock('Material Request', name)
        doc = _doc(name)
        _version(doc, modified)
        state = _state(doc)
        chain = _chain(doc)
        allowed = rules.editable(state, step_roles_match=chain['current'] == 2 and chain['can_sign'])
        if not allowed or doc.docstatus != 0:
            frappe.throw('Phiếu đang chờ ký, không sửa được ở bước này.')
        if allowed == 'prices':
            doc.flags.ignore_permissions = True  # Named purchasing signer may edit only EDIT_PRICES.
        else:
            doc.check_permission('write')
        if allowed == 'all' and doc.owner != frappe.session.user and not _admin():
            frappe.throw('Chỉ người đề xuất sửa nội dung phiếu.')
    else:
        if not frappe.has_permission('Material Request', 'create'):
            frappe.throw('Chưa có quyền lập đề xuất mua.', frappe.PermissionError)
        doc = frappe.new_doc('Material Request')
        doc.update(dict(material_request_type='Purchase', company=company, transaction_date=nowdate(), lotus_proposal_state=rules.DRAFT))
        allowed = 'all'
    if allowed == 'all':
        if not reason:
            frappe.throw('Nhập lý do đề xuất mua.')
        doc.lotus_request_note = reason[:1000]
        doc.lotus_department = str(values.get('department') or '').strip()[:140]
        if values.get('warehouse'):
            doc.set_warehouse = _receiving_warehouse(values['warehouse'], company)
    from lotus_farm.purchase_flow import enabled
    before = signing.fingerprint(doc)
    sources = {r.item_code: r.get('lotus_purchase_sources') for r in doc.items}
    _apply_lines(doc, values.get('items'), allowed)
    for row in doc.items:
        if sources.get(row.item_code):
            row.lotus_purchase_sources = sources[row.item_code]
    if allowed == 'prices' and enabled(company) and before != signing.fingerprint(doc):
        signing.send_back(doc, 'Đã bổ sung giá / nhà cung cấp. Người đề xuất gửi lại đủ 4 bước trên nội dung mới.')
        doc.lotus_proposal_state = rules.RETURNED
        doc.lotus_return_reason = 'Đã cập nhật giá / nhà cung cấp. Cần người đề xuất gửi lại đủ 4 bước.'
    doc.save() if name else doc.insert()
    return detail(doc.name)


@frappe.whitelist()
def signer_options(company, name=None, amount=None, priced=1):
    """People who may sign each later step: active employees with a login and the step's role.
    The steps follow the proposal's value: the saved proposal when `name` is given, else `amount`
    (and whether every line is priced) while the proposal is still being written."""
    _access()
    from lotus_farm.warehouse import _company
    _company(company)
    if name:
        doc = _doc(name)
        key = signing.chain_for(doc, fresh=doc.docstatus == 0 and rules.current_step(_state(doc)) == 0)
    elif amount is not None:
        key = rules.chain_for_lines([dict(qty=1, rate=flt(amount) if frappe.utils.cint(priced) else 0)])
    else:
        key = CHAIN
    from lotus_farm.purchase_flow import enabled
    if enabled(company) and (not name or doc.docstatus == 0):
        key = CHAIN
    return signing.candidates(key, company)


def _waiting_for_me():
    """Proposals whose waiting step is assigned to me (Administrator sees every waiting step)."""
    filters = {'document_type': 'Material Request', 'chain': ['in', rules.CHAINS], 'state': signing_rules.WAITING, 'step_index': ['>', 0]}
    if not _admin():
        filters['assignee'] = frappe.session.user
    return set(frappe.get_all(signing.REQUEST, filters=filters, pluck='document_name', limit_page_length=1000))


@frappe.whitelist()
def proposals(company, view='mine', stage=None, search=None, date_from=None, date_to=None, limit=300, offset=0):
    """Bảng đề xuất mua (spec 003, FR-026). view: mine | todo (waiting for my signature) | all.
    Each row carries its board stage (proposal_rules.stage, the same for every viewer); `counts` gives the number
    per stage of the chosen view plus 'Chờ tôi ký'. Without dates the board covers proposals touched in the
    last 12 months; date_from / date_to filter on the proposal date instead."""
    _access()
    from lotus_farm.warehouse import _company
    from lotus_farm.purchase_flow import proposal_totals
    _company(company)
    filters = {'company': company, 'material_request_type': 'Purchase'}
    if date_from or date_to:
        filters['transaction_date'] = ['between', [getdate(date_from or '2000-01-01'), getdate(date_to or '2099-12-31')]]
    else:
        filters['modified'] = ['>=', frappe.utils.add_months(nowdate(), -12)]
    mine, me = _waiting_for_me(), frappe.session.user
    listing = frappe.get_list
    if not frappe.has_permission('Material Request', 'read'):
        # A named signer without rights on proposals still sees the ones they sign or signed (signing.can_view).
        named = set(frappe.get_all(signing.REQUEST, filters={'document_type': 'Material Request', 'assignee': me},
                                   pluck='document_name', limit_page_length=2000))
        filters['name'] = ['in', list(named | mine) or ['']]
        listing = frappe.get_all
    rows = listing('Material Request', filters=filters,
                   fields=['name', 'transaction_date', 'schedule_date', 'owner', 'docstatus', 'status', 'lotus_proposal_state',
                           'lotus_department', 'lotus_request_note', 'modified'],
                   order_by='modified desc', limit_page_length=2000)
    if view == 'mine':
        rows = [r for r in rows if r.owner == me]
    elif view == 'todo':
        rows = [r for r in rows if r.name in mine]
    names = [r.name for r in rows]
    totals = proposal_totals([r.name for r in rows if r.docstatus == 1])
    amounts = {r.parent: r for r in frappe.db.sql('''select parent, coalesce(sum(qty*rate),0) total, count(*) n
        from `tabMaterial Request Item` where parenttype='Material Request' and parent in %(names)s group by parent''',
        dict(names=names), as_dict=True)} if names else {}
    people = {}
    counts = dict({s: 0 for s in rules.STAGES}, **{WAITING_ME: 0})
    needle = str(search or '').strip().lower()
    result = []
    for row in rows:
        state = rules.APPROVED if row.docstatus == 1 else row.lotus_proposal_state or rules.DRAFT
        board = rules.stage(row.docstatus, row.lotus_proposal_state, totals.get(row.name, {}).get('lines', []))
        waiting = row.docstatus == 0 and row.name in mine
        counts[board] += 1
        counts[WAITING_ME] += 1 if waiting else 0
        if stage and not (board == stage or (stage == WAITING_ME and waiting)):
            continue
        if needle and needle not in ' '.join([row.name, row.lotus_request_note or '', row.lotus_department or '']).lower():
            continue
        if row.owner not in people:
            people[row.owner] = frappe.db.get_value('User', row.owner, 'full_name') or row.owner
        amount = amounts.get(row.name) or {}
        result.append(dict(name=row.name, date=str(row.transaction_date), needed=str(row.schedule_date or ''), state=state, stage=board,
                           docstatus=row.docstatus, proposer=people[row.owner], department=row.lotus_department or '',
                           reason=row.lotus_request_note or '', total=flt(amount.get('total')), lines=int(amount.get('n') or 0),
                           waiting_me=waiting, modified=str(row.modified),
                           can_sign=row.docstatus == 0 and ((rules.current_step(state) == 0 and row.owner == me) or row.name in mine)))
    limit, offset = frappe.utils.cint(limit) or 300, frappe.utils.cint(offset)
    return dict(rows=result[offset:offset + limit], total=len(result), counts=counts, stages=[WAITING_ME, *rules.STAGES])


def _chain(doc, with_images=False):
    # The chain follows the proposal's value (lotus_farm.signing.chain_for); a started round keeps its own.
    return signing.status(doc, None, with_images=with_images)


def _signatures(chain):
    return [dict(action=s['key'], title=s['title'], assignee=s['assignee'], name=s['name'], state=s['state'],
                 signed_at=s['signed_at'] if s['state'] == signing_rules.SIGNED else '',
                 image=s['image'] if s['state'] == signing_rules.SIGNED else '') for s in chain['steps']]


@frappe.whitelist()
def detail(name):
    _access()
    doc = _doc(name)
    state = _state(doc)
    step = rules.current_step(state)
    admin, me = _admin(), frappe.session.user
    chain = _chain(doc, with_images=True)
    items = []
    for row in doc.items:
        items.append(dict(name=row.name, item_code=row.item_code, item_name=row.item_name, uom=row.uom, qty=flt(row.qty), rate=flt(row.rate),
                          kind=row.get('lotus_purchase_kind'),
                          amount=flt(row.qty) * flt(row.rate), warehouse=row.warehouse, schedule_date=str(row.schedule_date or ''),
                          stock=_stock(row.item_code, row.warehouse, row.conversion_factor),
                          lotus_specification=row.get('lotus_specification') or '', lotus_supplier_hint=row.get('lotus_supplier_hint') or '',
                          lotus_purpose=row.get('lotus_purpose') or '', lotus_notes=row.get('lotus_notes') or ''))
    drafting = doc.docstatus == 0 and step == 0
    purchasing_turn = doc.docstatus == 0 and chain['current'] == 2 and chain['can_sign']
    edit = rules.editable(state, step_roles_match=purchasing_turn) if doc.docstatus == 0 else None
    if edit == 'all' and doc.owner != me and not admin:
        edit = None
    returned = next((s for s in chain['steps'] if s['state'] == signing_rules.RETURNED), None)
    # Signers of the latest round prefill the picker when the proposer sends again.
    chosen = {s['key']: s['assignee'] for s in chain['steps'][1:] if s['assignee']}
    from urllib.parse import urlencode
    from lotus_farm.purchase_flow import proposal_progress, enabled
    progress = proposal_progress(doc)
    legacy_round = enabled(doc.company) and doc.docstatus == 0 and chain['chain'] == 'purchase_proposal_small'
    stopped = doc.docstatus == 1 and doc.status == 'Stopped'
    open_part = doc.docstatus == 1 and not stopped and any(flt(r.stock_qty) - flt(r.ordered_qty) > 1e-6 for r in doc.items)
    return dict(name=doc.name, company=doc.company, modified=str(doc.modified), docstatus=doc.docstatus, state=state, step=step,
                stage=progress['stage'], needs_reason=drafting and not str(doc.get('lotus_request_note') or '').strip(),
                closed=stopped, close_reason=doc.get('lotus_close_reason') or '', cancel_reason=doc.get('lotus_cancel_reason') or '',
                closed_by=signing._person(doc.get('lotus_closed_by')) if doc.get('lotus_closed_by') else '',
                closed_at=str(doc.get('lotus_closed_at') or ''),
                can_close=open_part and _may_close(doc), can_cancel=doc.docstatus == 1 and _may_cancel(doc),
                signed_copy=signing.copy_info(doc),
                progress=progress, policy_notice='Lượt ký cũ sẽ được trả lại để gửi đủ 4 bước.' if legacy_round else '',
                step_title=rules.STEPS[step]['title'] if step is not None else '',
                waiting_for=chain['steps'][chain['current']]['name'] if not drafting and chain['current'] not in (None, 0) else '',
                proposer=frappe.db.get_value('User', doc.owner, 'full_name') or doc.owner, owner=doc.owner, date=str(doc.transaction_date),
                department=doc.get('lotus_department') or '', reason=doc.get('lotus_request_note') or '', warehouse=doc.get('set_warehouse') or '',
                return_reason=doc.get('lotus_return_reason') or '', returned_by=returned['name'] if returned else '',
                items=items, total=sum(i['amount'] for i in items), signatures=_signatures(chain), signers=chosen,
                needs_signers=drafting,
                can_sign=(drafting and (doc.owner == me or admin)) or (doc.docstatus == 0 and not drafting and chain['can_sign']),
                can_return=doc.docstatus == 0 and not drafting and chain['can_return'],
                can_reassign=doc.docstatus == 0 and not drafting and chain['can_reassign'],
                can_delete=drafting and (doc.owner == me or admin),
                edit=edit, print_url='/lotus/in-de-xuat?' + urlencode({'name': doc.name}))


@frappe.whitelist(methods=['POST'])
def sign(name, modified, signers=None, reason=None):
    """Proposer: send with the chosen signers, signing first. Each signer then signs their own turn;
    the director's signature submits the request."""
    _access()
    from lotus_farm.controls import lock
    lock('Material Request', name)
    doc = _doc(name)
    _version(doc, modified)
    if doc.docstatus != 0:
        frappe.throw('Phiếu đã duyệt hoặc đã hủy.')
    from lotus_farm.purchase_flow import enabled
    strict = enabled(doc.company)
    if strict:
        rows, _ = signing._rows(doc)
        if rows and signing.chain_for(doc) == 'purchase_proposal_small' and not any(r.state == signing_rules.RETURNED for r in rows):
            # Preserve the old round; the next send creates a separate four-step round.
            if frappe.session.user not in (doc.owner, rows[signing_rules.current(rows) or 0].assignee) and not _admin():
                frappe.throw('Chưa đến lượt bạn xử lý đề xuất này.', frappe.PermissionError)
            from lotus_farm.digital_signature import _event
            _event(doc, 'RETURN', frappe.session.user, frappe.utils.now_datetime(), details='Chuyển chính sách duyệt mua đủ 4 bước')
            frappe.db.set_value(signing.REQUEST, rows[-1].name, dict(state=signing_rules.RETURNED, note='Chuyển sang quy trình ký đủ 4 bước'), update_modified=False)
            doc.lotus_proposal_state = rules.RETURNED
            doc.lotus_return_reason = 'Chính sách mới yêu cầu đủ 4 bước. Người đề xuất chọn người ký và gửi lại.'
            doc.flags.ignore_permissions = True
            _save_signing_state(doc)
            return detail(doc.name)
        if not rows or any(r.state == signing_rules.RETURNED for r in rows):
            doc.lotus_proposal_policy = 2
        else:
            current = signing_rules.current(rows)
            if current is None or rows[current].assignee != frappe.session.user:
                frappe.throw('Chỉ người được chọn ở bước hiện tại được ký.', frappe.PermissionError)
    step = rules.current_step(_state(doc))
    issues = rules.line_issues([dict(item_code=r.item_code, qty=r.qty, schedule_date=r.schedule_date, rate=r.rate) for r in doc.items])
    if not doc.items or issues:
        frappe.throw('; '.join(issues[:6]) or 'Phiếu chưa có vật tư.')
    reason = str(reason or '').strip()
    if step == 0 and reason and not str(doc.get('lotus_request_note') or '').strip():
        # Proposals imported from Excel carry no reason yet: it is asked when the proposer signs (spec 003, FR-031).
        # Written before the round starts, so every signature covers it.
        if doc.owner != frappe.session.user and not _admin():
            frappe.throw('Chỉ người đề xuất gửi ký phiếu.', frappe.PermissionError)
        doc.lotus_request_note = reason[:1000]
        doc.db_set('lotus_request_note', doc.lotus_request_note, update_modified=False)
    if not str(doc.get('lotus_request_note') or '').strip():
        frappe.throw('Nhập lý do đề xuất mua trước khi gửi.')
    def approve():
        # The director's signature submits the request; signing then stores the signed copy.
        doc.lotus_proposal_state = rules.APPROVED
        doc.flags.ignore_permissions = True  # signing checked the named signer of this step
        _save_signing_state(doc)
        doc.submit()

    if step == 0:
        if doc.owner != frappe.session.user and not _admin():
            frappe.throw('Chỉ người đề xuất gửi ký phiếu.', frappe.PermissionError)
        if strict and doc.owner != frappe.session.user:
            frappe.throw('Người lập phiếu phải tự ký gửi đề xuất.', frappe.PermissionError)
        chain = signing.start(doc, signers, require_image=True, effect=approve)
        doc.lotus_return_reason = ''
    else:
        chain = signing.sign(doc, require_image=True, effect=approve)
    if not chain['done']:
        doc.lotus_proposal_state = rules.state_after(chain['current'] - 1)
        doc.flags.ignore_permissions = True  # signing checked the named signer of this step
        _save_signing_state(doc)
    return detail(doc.name)


@frappe.whitelist(methods=['POST'])
def return_proposal(name, modified, reason):
    _access()
    from lotus_farm.controls import lock
    lock('Material Request', name)
    doc = _doc(name)
    _version(doc, modified)
    if doc.docstatus != 0 or rules.current_step(_state(doc)) in (None, 0):
        frappe.throw('Phiếu không ở bước chờ ký.')
    signing.send_back(doc, reason)
    doc.lotus_proposal_state = rules.RETURNED
    doc.lotus_return_reason = str(reason or '').strip()[:500]
    doc.flags.ignore_permissions = True
    _save_signing_state(doc)
    return detail(doc.name)


@frappe.whitelist(methods=['POST'])
def reassign_signer(name, modified, step, user, reason=None):
    _access()
    doc = _doc(name)
    _version(doc, modified)
    signing.reassign('Material Request', doc.name, step, user, reason)
    return detail(doc.name)


@frappe.whitelist(methods=['POST'])
def delete_proposal(name, modified):
    _access()
    doc = _doc(name)
    _version(doc, modified)
    if doc.docstatus != 0 or rules.current_step(_state(doc)) != 0 or (doc.owner != frappe.session.user and not _admin()):
        frappe.throw('Chỉ xóa phiếu nháp của chính mình.')
    if frappe.db.exists('Purchase Order Item', {'material_request': doc.name}) or frappe.db.exists('Supplier Quotation Item', {'material_request': doc.name}):
        frappe.throw('Phiếu đã có báo giá hoặc đơn mua tham chiếu, không xóa được.')
    # The proposer removes their own draft (spec 003, FR-029); signing rows and events of returned rounds stay as history.
    frappe.delete_doc('Material Request', doc.name, ignore_permissions=True)
    return dict(name=name)


def _has_role(*roles):
    return _admin() or bool(set(roles) & set(frappe.get_roles(frappe.session.user)))


def _may_close(doc):
    """Đóng phần chưa mua: the proposer, purchasing / accounting, or the purchase approver."""
    return doc.owner == frappe.session.user or _has_role(*signing_rules.PURCHASING, *signing_rules.PURCHASE_APPROVER)


def _may_cancel(doc):
    return doc.owner == frappe.session.user or _has_role(*signing_rules.PURCHASE_APPROVER)


def _reason(text, label):
    text = str(text or '').strip()
    if not 3 <= len(text) <= 500:
        frappe.throw('Ghi ' + label + ' (3–500 ký tự).')
    return text


def _order_lines(doc, drafts_only=False):
    """Purchase orders citing this proposal: [(order, docstatus, approval status)], drafts and submitted."""
    rows = frappe.db.sql('''select distinct po.name, po.docstatus, po.lotus_approval_status from `tabPurchase Order Item` poi
        join `tabPurchase Order` po on po.name = poi.parent where poi.material_request = %s and po.docstatus < 2''', doc.name, as_dict=True)
    return [r for r in rows if not drafts_only or r.docstatus == 0]


@frappe.whitelist(methods=['POST'])
def close_remainder(name, modified, reason):
    """Đóng phần chưa mua của đề xuất đã duyệt (spec 003, FR-029): the quantity not yet ordered will not be bought.
    Lines already ordered follow their orders; a draft or pending order must be sent or removed first."""
    _access()
    from lotus_farm.controls import lock
    lock('Material Request', name)
    doc = _doc(name)
    _version(doc, modified)
    reason = _reason(reason, 'lý do đóng phần chưa mua')
    if doc.docstatus != 1 or doc.status in ('Stopped', 'Cancelled'):
        frappe.throw('Chỉ đóng phần chưa mua của đề xuất đã duyệt còn hiệu lực.')
    if not _may_close(doc):
        frappe.throw('Chỉ người đề xuất, mua hàng / kế toán hoặc người duyệt mua được đóng phần chưa mua.', frappe.PermissionError)
    waiting = _order_lines(doc, drafts_only=True)
    if waiting:
        frappe.throw('Còn đơn mua chưa duyệt lấy từ đề xuất này: ' + ', '.join(r.name for r in waiting) + '. Gửi duyệt hoặc xóa đơn đó trước.')
    if not any(flt(r.stock_qty) - flt(r.ordered_qty) > 1e-6 for r in doc.items):
        frappe.throw('Đề xuất không còn phần chưa đặt mua. Phần đã đặt đóng theo đơn mua.')
    doc.flags.ignore_permissions = True
    doc.update_status('Stopped')
    doc.db_set(dict(lotus_close_reason=reason, lotus_closed_by=frappe.session.user, lotus_closed_at=frappe.utils.now_datetime()))
    doc.add_comment('Comment', 'Đóng phần chưa mua: ' + reason)
    return detail(doc.name)


@frappe.whitelist(methods=['POST'])
def cancel_proposal(name, modified, reason, cancel_quotes=0):
    """Hủy đề xuất đã duyệt khi chưa có đơn mua nào lấy từ nó (spec 003, FR-029). Quotes citing only this proposal
    are cancelled with it when cancel_quotes is set; otherwise they block the cancellation."""
    _access()
    from lotus_farm.controls import lock
    lock('Material Request', name)
    doc = _doc(name)
    _version(doc, modified)
    reason = _reason(reason, 'lý do hủy đề xuất')
    if doc.docstatus != 1:
        frappe.throw('Chỉ hủy đề xuất đã duyệt. Phiếu nháp thì xóa; phiếu đang ký thì người đang ký trả lại.')
    if not _may_cancel(doc):
        frappe.throw('Chỉ người đề xuất hoặc người duyệt mua được hủy đề xuất.', frappe.PermissionError)
    orders = _order_lines(doc)
    if orders:
        frappe.throw('Đề xuất đã có đơn mua (' + ', '.join(r.name for r in orders) + '). Chỉ đóng được phần chưa mua.')
    quotes = frappe.db.sql('''select distinct sq.name, sq.docstatus from `tabSupplier Quotation Item` sqi
        join `tabSupplier Quotation` sq on sq.name = sqi.parent where sqi.material_request = %s and sq.docstatus < 2''', doc.name, as_dict=True)
    if quotes and not frappe.utils.cint(cancel_quotes):
        frappe.throw('Còn báo giá cho đề xuất này: ' + ', '.join(q.name for q in quotes) + '. Chọn hủy kèm báo giá, hoặc hủy báo giá trước.')
    for quote in quotes:
        other = frappe.db.sql('''select 1 from `tabSupplier Quotation Item` where parent = %s and coalesce(material_request, '') not in ('', %s) limit 1''',
                              (quote.name, doc.name))
        if other:
            frappe.throw('Báo giá ' + quote.name + ' còn dòng của đề xuất khác. Sửa báo giá đó trước khi hủy đề xuất.')
        q = frappe.get_doc('Supplier Quotation', quote.name)
        q.flags.ignore_permissions = True
        if q.docstatus == 1:
            q.cancel()
        else:
            frappe.delete_doc('Supplier Quotation', q.name, ignore_permissions=True)
    doc.reload()
    doc.flags.ignore_permissions = True
    doc.cancel()
    doc.db_set('lotus_cancel_reason', reason)
    doc.add_comment('Comment', 'Hủy đề xuất: ' + reason)
    return detail(doc.name)
