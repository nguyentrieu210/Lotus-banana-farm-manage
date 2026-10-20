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

PARENT_FIELDS = [
    dict(fieldname='lotus_proposal_state', label='Lotus · Trạng thái đề xuất', fieldtype='Select',
         options='\n'.join(rules.STATES), default=rules.DRAFT, read_only=1, insert_after='material_request_type', in_list_view=1),
    dict(fieldname='lotus_department', label='Lotus · Bộ phận đề xuất', fieldtype='Data', insert_after='lotus_proposal_state'),
    dict(fieldname='lotus_request_note', label='Lotus · Lý do đề xuất mua', fieldtype='Small Text', insert_after='lotus_department'),
    dict(fieldname='lotus_return_reason', label='Lotus · Lý do trả lại', fieldtype='Small Text', read_only=1, insert_after='lotus_request_note'),
]
ITEM_FIELDS = [
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


def _access():
    from lotus_farm.purchasing import access
    access()
    if not frappe.has_permission('Material Request', 'read'):
        frappe.throw('Không có quyền xem đề xuất mua.', frappe.PermissionError)



def _admin():
    return frappe.session.user == 'Administrator'


def _doc(name):
    doc = frappe.get_doc('Material Request', name)
    doc.check_permission('read')
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


def _stock(item, warehouse, factor=1):
    if not (item and warehouse):
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
        frappe.get_doc('Warehouse', warehouse).check_permission('read')
        line = {field: row.get(field) for field in EDIT_ALL}
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
        doc.check_permission('write')
        state = _state(doc)
        chain = _chain(doc)
        allowed = rules.editable(state, step_roles_match=chain['current'] == 2 and chain['can_sign'])
        if not allowed or doc.docstatus != 0:
            frappe.throw('Phiếu đang chờ ký, không sửa được ở bước này.')
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
            frappe.get_doc('Warehouse', values['warehouse']).check_permission('read')
            doc.set_warehouse = values['warehouse']
    _apply_lines(doc, values.get('items'), allowed)
    doc.save() if name else doc.insert()
    return detail(doc.name)


@frappe.whitelist()
def signer_options(company):
    """People who may sign each later step: active employees with a login and the step's role."""
    _access()
    from lotus_farm.warehouse import _company
    _company(company)
    return signing.candidates(CHAIN, company)


def _waiting_for_me():
    """Proposals whose waiting step is assigned to me (Administrator sees every waiting step)."""
    filters = {'document_type': 'Material Request', 'chain': CHAIN, 'state': signing_rules.WAITING, 'step_index': ['>', 0]}
    if not _admin():
        filters['assignee'] = frappe.session.user
    return set(frappe.get_all(signing.REQUEST, filters=filters, pluck='document_name', limit_page_length=1000))


@frappe.whitelist()
def proposals(company, view='mine'):
    """view: mine | todo (waiting for my signature) | all."""
    _access()
    from lotus_farm.warehouse import _company
    _company(company)
    rows = frappe.get_list('Material Request', filters={'company': company, 'material_request_type': 'Purchase', 'docstatus': ['<', 2],
                                                        'lotus_proposal_state': ['is', 'set']},
                           fields=['name', 'transaction_date', 'schedule_date', 'owner', 'docstatus', 'lotus_proposal_state', 'lotus_department', 'lotus_request_note', 'modified'],
                           order_by='modified desc', limit_page_length=300)
    mine, me = _waiting_for_me(), frappe.session.user
    result = []
    for row in rows:
        state = rules.APPROVED if row.docstatus == 1 else row.lotus_proposal_state
        step = rules.current_step(state)
        can_sign = row.docstatus == 0 and ((step == 0 and row.owner == me) or row.name in mine)
        if view == 'mine' and row.owner != me:
            continue
        if view == 'todo' and row.name not in mine:
            continue
        total = frappe.db.sql('select coalesce(sum(qty*rate),0), count(*) from `tabMaterial Request Item` where parent=%s', row.name)[0]
        result.append(dict(name=row.name, date=str(row.transaction_date), needed=str(row.schedule_date or ''), state=state,
                           proposer=frappe.db.get_value('User', row.owner, 'full_name') or row.owner, department=row.lotus_department or '',
                           reason=row.lotus_request_note or '', total=flt(total[0]), lines=int(total[1]), can_sign=can_sign))
    return result


def _chain(doc, with_images=False):
    return signing.status(doc, CHAIN, with_images=with_images)


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
    return dict(name=doc.name, company=doc.company, modified=str(doc.modified), docstatus=doc.docstatus, state=state, step=step,
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
                can_delete=drafting and doc.owner == me and doc.has_permission('delete'),
                edit=edit, print_url='/lotus/in-de-xuat?' + urlencode({'name': doc.name}))


@frappe.whitelist(methods=['POST'])
def sign(name, modified, signers=None):
    """Proposer: send with the chosen signers, signing first. Each signer then signs their own turn;
    the director's signature submits the request."""
    _access()
    from lotus_farm.controls import lock
    lock('Material Request', name)
    doc = _doc(name)
    _version(doc, modified)
    if doc.docstatus != 0:
        frappe.throw('Phiếu đã duyệt hoặc đã hủy.')
    step = rules.current_step(_state(doc))
    issues = rules.line_issues([dict(item_code=r.item_code, qty=r.qty, schedule_date=r.schedule_date, rate=r.rate) for r in doc.items])
    if not doc.items or issues:
        frappe.throw('; '.join(issues[:6]) or 'Phiếu chưa có vật tư.')
    if not str(doc.get('lotus_request_note') or '').strip():
        frappe.throw('Nhập lý do đề xuất mua trước khi gửi.')
    if step == 0:
        if doc.owner != frappe.session.user and not _admin():
            frappe.throw('Chỉ người đề xuất gửi ký phiếu.', frappe.PermissionError)
        chain = signing.start(doc, signers, require_image=True)
        doc.lotus_return_reason = ''
    else:
        chain = signing.sign(doc, require_image=True)
    doc.lotus_proposal_state = rules.APPROVED if chain['done'] else rules.state_after(chain['current'] - 1)
    doc.flags.ignore_permissions = True  # signing checked the named signer of this step
    doc.save()
    if doc.lotus_proposal_state == rules.APPROVED:
        doc.submit()
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
    doc.save()
    return detail(doc.name)


@frappe.whitelist(methods=['POST'])
def reassign_signer(name, modified, step, user):
    _access()
    doc = _doc(name)
    _version(doc, modified)
    signing.reassign('Material Request', doc.name, step, user)
    return detail(doc.name)


@frappe.whitelist(methods=['POST'])
def delete_proposal(name, modified):
    _access()
    doc = _doc(name)
    _version(doc, modified)
    if doc.docstatus != 0 or rules.current_step(_state(doc)) != 0 or doc.owner != frappe.session.user:
        frappe.throw('Chỉ xóa phiếu nháp của chính mình.')
    doc.check_permission('delete')
    frappe.delete_doc('Material Request', doc.name)
    return dict(name=name)
