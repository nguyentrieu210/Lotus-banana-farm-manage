"""Online purchase proposal (Phiếu đề xuất mua vật tư) on ERPNext Material Request (type Purchase).

The form follows the farm's Excel template: proposer, department, reason; per line the item,
specification, unit, stock on hand, proposed quantity, expected price, needed date, suggested
supplier and purpose. Four people sign in order (lotus_farm.proposal_rules). Each signature is a
snapshot of the signer's image stored on the request with a Lotus Signature Event; the director's
signature submits the request, which then appears in Mua hàng as a request waiting for an order.
"""
import json

import frappe
from frappe.utils import flt, getdate, now_datetime, nowdate

from lotus_farm import proposal_rules as rules

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


def _roles():
    return set(frappe.get_roles(frappe.session.user))


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
        allowed = rules.editable(state, step_roles_match=bool(set(rules.STEPS[2]['roles']) & _roles()) or _admin())
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
def proposals(company, view='mine'):
    """view: mine | todo (waiting for my signature) | all."""
    _access()
    from lotus_farm.warehouse import _company
    _company(company)
    rows = frappe.get_list('Material Request', filters={'company': company, 'material_request_type': 'Purchase', 'docstatus': ['<', 2],
                                                        'lotus_proposal_state': ['is', 'set']},
                           fields=['name', 'transaction_date', 'schedule_date', 'owner', 'docstatus', 'lotus_proposal_state', 'lotus_department', 'lotus_request_note', 'modified'],
                           order_by='modified desc', limit_page_length=300)
    roles, admin, me = _roles(), _admin(), frappe.session.user
    result = []
    for row in rows:
        state = rules.APPROVED if row.docstatus == 1 else row.lotus_proposal_state
        step = rules.current_step(state)
        can_sign = row.docstatus == 0 and rules.may_sign(step, roles, row.owner == me, admin)
        if view == 'mine' and row.owner != me:
            continue
        if view == 'todo' and not (can_sign and step and step > 0):
            continue
        total = frappe.db.sql('select coalesce(sum(qty*rate),0), count(*) from `tabMaterial Request Item` where parent=%s', row.name)[0]
        result.append(dict(name=row.name, date=str(row.transaction_date), needed=str(row.schedule_date or ''), state=state,
                           proposer=frappe.db.get_value('User', row.owner, 'full_name') or row.owner, department=row.lotus_department or '',
                           reason=row.lotus_request_note or '', total=flt(total[0]), lines=int(total[1]), can_sign=can_sign))
    return result


def _signatures(doc):
    events = frappe.get_all('Lotus Signature Event', filters={'document_type': doc.doctype, 'document_name': doc.name},
                            fields=['action', 'actor', 'signed_at', 'details'], order_by='signed_at asc, creation asc', limit_page_length=100)
    # The chain restarts after a return: only signatures after the last RETURN count.
    last_return = max([i for i, e in enumerate(events) if e.action == 'RETURN'], default=-1)
    signed = {}
    for event in events[last_return + 1:]:
        if event.action in {s['action'] for s in rules.STEPS}:
            signed[event.action] = event
    result = []
    for step in rules.STEPS:
        event = signed.get(step['action'])
        image = ''
        if event:
            try:
                file_name = (json.loads(event.details or '{}') or {}).get('signature_file')
            except (TypeError, ValueError):
                file_name = None
            if file_name and frappe.db.exists('File', file_name):
                file = frappe.get_doc('File', file_name)
                if file.attached_to_doctype == doc.doctype and file.attached_to_name == doc.name and file.is_private:
                    from base64 import b64encode
                    image = 'data:image/png;base64,' + b64encode(file.get_content(encodings=[])).decode('ascii')
        result.append(dict(action=step['action'], title=step['title'],
                           name=(frappe.db.get_value('User', event.actor, 'full_name') or event.actor) if event else '',
                           signed_at=str(event.signed_at) if event else '', image=image))
    returns = [e for e in events if e.action == 'RETURN']
    return result, (returns[-1] if returns else None)


@frappe.whitelist()
def detail(name):
    _access()
    doc = _doc(name)
    state = _state(doc)
    step = rules.current_step(state)
    roles, admin, me = _roles(), _admin(), frappe.session.user
    signatures, returned = _signatures(doc)
    items = []
    for row in doc.items:
        items.append(dict(name=row.name, item_code=row.item_code, item_name=row.item_name, uom=row.uom, qty=flt(row.qty), rate=flt(row.rate),
                          amount=flt(row.qty) * flt(row.rate), warehouse=row.warehouse, schedule_date=str(row.schedule_date or ''),
                          stock=_stock(row.item_code, row.warehouse, row.conversion_factor),
                          lotus_specification=row.get('lotus_specification') or '', lotus_supplier_hint=row.get('lotus_supplier_hint') or '',
                          lotus_purpose=row.get('lotus_purpose') or '', lotus_notes=row.get('lotus_notes') or ''))
    edit = rules.editable(state, step_roles_match=bool(set(rules.STEPS[2]['roles']) & roles) or admin) if doc.docstatus == 0 else None
    if edit == 'all' and doc.owner != me and not admin:
        edit = None
    from urllib.parse import urlencode
    return dict(name=doc.name, company=doc.company, modified=str(doc.modified), docstatus=doc.docstatus, state=state, step=step,
                step_title=rules.STEPS[step]['title'] if step is not None else '',
                proposer=frappe.db.get_value('User', doc.owner, 'full_name') or doc.owner, owner=doc.owner, date=str(doc.transaction_date),
                department=doc.get('lotus_department') or '', reason=doc.get('lotus_request_note') or '', warehouse=doc.get('set_warehouse') or '',
                return_reason=doc.get('lotus_return_reason') or '', returned_by=(returned.actor if returned else ''),
                items=items, total=sum(i['amount'] for i in items), signatures=signatures,
                can_sign=doc.docstatus == 0 and rules.may_sign(step, roles, doc.owner == me, admin),
                can_return=doc.docstatus == 0 and step not in (None, 0) and rules.may_sign(step, roles, doc.owner == me, admin),
                can_delete=doc.docstatus == 0 and step == 0 and doc.owner == me and doc.has_permission('delete'),
                edit=edit, print_url='/lotus/in-de-xuat?' + urlencode({'name': doc.name}))


def _snapshot_signature(doc, step):
    from frappe.utils.file_manager import save_file
    from lotus_farm.digital_signature import signature_image_bytes
    image = signature_image_bytes(frappe.session.user)
    if not image:
        frappe.throw('Chưa có ảnh chữ ký. Thiết lập chữ ký trong mục Tôi trước khi ký phiếu.')
    saved = save_file('de-xuat-' + rules.STEPS[step]['action'].lower() + '.png', image, doc.doctype, doc.name, is_private=1)
    return saved.name


@frappe.whitelist(methods=['POST'])
def sign(name, modified):
    """Sign the step the proposal is waiting for; the director's signature submits the request."""
    _access()
    from lotus_farm.controls import lock
    from lotus_farm.digital_signature import _event
    lock('Material Request', name)
    doc = _doc(name)
    _version(doc, modified)
    if doc.docstatus != 0:
        frappe.throw('Phiếu đã duyệt hoặc đã hủy.')
    state = _state(doc)
    step = rules.current_step(state)
    if not rules.may_sign(step, _roles(), doc.owner == frappe.session.user, _admin()):
        frappe.throw('Bạn không có quyền ký bước "' + rules.STEPS[step]['title'] + '".', frappe.PermissionError)
    issues = rules.line_issues([dict(item_code=r.item_code, qty=r.qty, schedule_date=r.schedule_date, rate=r.rate) for r in doc.items])
    if not doc.items or issues:
        frappe.throw('; '.join(issues[:6]) or 'Phiếu chưa có vật tư.')
    if not str(doc.get('lotus_request_note') or '').strip():
        frappe.throw('Nhập lý do đề xuất mua trước khi gửi.')
    file_name = _snapshot_signature(doc, step)
    when = now_datetime()
    _event(doc, rules.STEPS[step]['action'], frappe.session.user, when, signature_type='IMAGE',
           details=json.dumps(dict(signature_file=file_name, step=step + 1)))
    doc.lotus_proposal_state = rules.state_after(step)
    if step == 0:
        doc.lotus_return_reason = ''
    doc.flags.ignore_permissions = True  # role checked above for this exact step
    doc.save()
    if doc.lotus_proposal_state == rules.APPROVED:
        doc.submit()
    return detail(doc.name)


@frappe.whitelist(methods=['POST'])
def return_proposal(name, modified, reason):
    _access()
    from lotus_farm.controls import lock
    from lotus_farm.digital_signature import _event
    lock('Material Request', name)
    doc = _doc(name)
    _version(doc, modified)
    state = _state(doc)
    step = rules.current_step(state)
    if doc.docstatus != 0 or step in (None, 0):
        frappe.throw('Phiếu không ở bước chờ ký.')
    if not rules.may_sign(step, _roles(), doc.owner == frappe.session.user, _admin()):
        frappe.throw('Bạn không có quyền xử lý bước này.', frappe.PermissionError)
    reason = str(reason or '').strip()
    if len(reason) < 3:
        frappe.throw('Ghi lý do trả lại.')
    _event(doc, 'RETURN', frappe.session.user, now_datetime(), details=json.dumps(dict(reason=reason[:500], step=step + 1)))
    doc.lotus_proposal_state = rules.RETURNED
    doc.lotus_return_reason = reason[:500]
    doc.flags.ignore_permissions = True
    doc.save()
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
