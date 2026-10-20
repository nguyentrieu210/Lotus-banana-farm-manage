"""Named signers for Lotus documents: pick people from HR, sign in turn, notify each one.

One Lotus Sign Request per step and round. Starting a chain records who signs each step (employees
whose login holds the step's roles); the preparer signs first. Each later signer is notified by
in-app alert, web push and e-mail when their turn comes, and only they may sign, return the document
or hand their step to someone else. A return starts a new round. Each signature stores a private
copy of the signer's image (when one is set up) and a Lotus Signature Event. Chain rules live in
lotus_farm.signing_rules. Gated chains (proposal, order, period) are driven by their own module, which
calls start / sign / send_back and applies the effect (submit, approve, close) of the last signature.
"""
import json
from urllib.parse import quote

import frappe
from frappe.utils import cint, get_url, now_datetime

from lotus_farm import signing_rules as rules

REQUEST = 'Lotus Sign Request'
# chain -> link to the document inside the chain's app (push targets must stay in that app).
URLS = {
    'purchase_proposal': lambda d: '/buying?proposal=' + quote(d.name),
    'issue_proposal': lambda d: '/warehouse?doc=' + quote(d.name) + '&doctype=Material%20Request',
    'purchase_order': lambda d: '/buying?doc=' + quote(d.name),
    'stock_document': lambda d: '/warehouse?doc=' + quote(d.name) + '&doctype=' + quote(d.doctype),
    # The period is signed on its print page, which any signer can open (no HR role needed).
    'timekeeping_period': lambda d: '/lotus/in-luong?company=' + quote(d.company) + '&month=' + quote(d.month),
}


def chain_for(doc):
    if doc.doctype == 'Material Request':
        return 'purchase_proposal' if doc.material_request_type == 'Purchase' else 'issue_proposal'
    return {'Purchase Order': 'purchase_order', 'Stock Entry': 'stock_document', 'Stock Reconciliation': 'stock_document',
            'Purchase Receipt': 'stock_document', 'Lotus Timekeeping Period': 'timekeeping_period'}.get(doc.doctype)


def _admin():
    return frappe.session.user == 'Administrator'


def _roles(user):
    return frappe.get_roles(user)


def _doc(doctype, name, permission='read'):
    if frappe.session.user == 'Guest':
        frappe.throw('Vui lòng đăng nhập.', frappe.AuthenticationError)
    doc = frappe.get_doc(doctype, name)
    doc.check_permission(permission)
    key = chain_for(doc)
    if not key:
        frappe.throw('Chứng từ này chưa có quy trình ký.')
    return doc, key


def _rows(doc):
    last = frappe.get_all(REQUEST, filters={'document_type': doc.doctype, 'document_name': doc.name}, pluck='round',
                          order_by='round desc', limit_page_length=1)
    last = cint(last[0]) if last else 0
    if not last:
        return [], 0
    rows = frappe.get_all(REQUEST, filters={'document_type': doc.doctype, 'document_name': doc.name, 'round': last},
                          fields=['name', 'step_index', 'step_key', 'title', 'assignee', 'employee', 'state', 'signed_at', 'signature_file', 'note'],
                          order_by='step_index asc')
    return rows, cint(last)


def _company(doc):
    return doc.get('company') or frappe.defaults.get_user_default('Company')


def _person(user):
    if not user:
        return ''
    return frappe.db.get_value('Employee', {'user_id': user, 'status': 'Active'}, 'employee_name') or frappe.db.get_value('User', user, 'full_name') or user


@frappe.whitelist()
def candidates(chain, company=None, step=None):
    """Active employees with an enabled login who may sign each step of `chain`."""
    if frappe.session.user == 'Guest':
        frappe.throw('Vui lòng đăng nhập.', frappe.AuthenticationError)
    config = rules.chain(chain)
    company = company or frappe.defaults.get_user_default('Company')
    if not company:
        frappe.throw('Chọn công ty trước khi chọn người ký.')
    frappe.get_doc('Company', company).check_permission('read')
    filters = {'status': 'Active', 'user_id': ['is', 'set']}
    if company:
        filters['company'] = company
    people = frappe.get_all('Employee', filters=filters, fields=['name', 'employee_name', 'user_id', 'designation', 'department'], order_by='employee_name')
    enabled = set(frappe.get_all('User', filters={'enabled': 1, 'name': ['in', [p.user_id for p in people] or ['']]}, pluck='name'))
    from lotus_farm.localization import ROLE_LABELS, catalog_label
    role_map = {user: _roles(user) for user in enabled}
    current = frappe.db.get_value('Employee', {'user_id': frappe.session.user, 'status': 'Active', 'company': company}, 'reports_to')
    result, diagnostics, suggested = {}, {}, {}
    for item in config['steps'][1:]:
        if step and item['key'] != step:
            continue
        result[item['key']] = [dict(user=p.user_id, employee=p.name, name=p.employee_name, designation=catalog_label(p.designation) or '', department=catalog_label(p.department) or '',
                                    recommended=bool(item['key'] == 'DEPARTMENT' and p.name == current))
                               for p in people if p.user_id in enabled and rules.eligible(item, role_map[p.user_id])]
        active = frappe.db.count('Employee', {'status': 'Active', 'company': company})
        required = [ROLE_LABELS.get(r, r) for r in item['roles']]
        if not active:
            message = 'Công ty chưa có nhân sự đang làm việc. Thêm nhân sự tại mục Nhân sự.'
        elif not people:
            message = 'Nhân sự trong công ty chưa được gắn tài khoản đăng nhập. Gắn tài khoản tại Hồ sơ & quyền hoặc mục Nhân sự.'
        elif not enabled:
            message = 'Các tài khoản đã gắn nhân sự đang bị khóa. Kiểm tra trạng thái tài khoản tại mục Người dùng.'
        else:
            message = 'Chưa có nhân sự có tài khoản hoạt động và role phù hợp. Cấp một trong các role: ' + ' / '.join(required) + '.'
        diagnostics[item['key']] = dict(message=message, required_roles=required, active_employees=active, linked_employees=len(people), enabled_logins=len(enabled))
        recommended = next((p['user'] for p in result[item['key']] if p['recommended']), None)
        if recommended:
            suggested[item['key']] = recommended
    remembered = frappe.defaults.get_user_default('lotus_signers_' + chain)
    return dict(steps=[dict(key=s['key'], title=s['title']) for s in config['steps']], candidates=result,
                remembered=json.loads(remembered) if remembered else {}, diagnostics=diagnostics, suggested=suggested)


def _validate_person(user, step, company):
    """Recheck on send, reassign and sign; stale picker choices cannot bypass current eligibility."""
    if not frappe.db.get_value('User', user, 'enabled'):
        frappe.throw(step['title'] + ': tài khoản người ký đang bị khóa.', frappe.PermissionError)
    if not rules.eligible(step, _roles(user)):
        frappe.throw(step['title'] + ': người được chọn không có quyền ký bước này.', frappe.PermissionError)
    if not frappe.db.exists('Employee', {'user_id': user, 'status': 'Active', 'company': company}):
        frappe.throw(step['title'] + ': người ký phải là nhân sự đang làm việc thuộc công ty của chứng từ.')


def status(doc, key=None, with_images=False):
    key = key or chain_for(doc)
    config = rules.chain(key)
    rows, round_ = _rows(doc)
    index = rules.current(rows) if rows else None
    returned = bool(rows) and any(r.state == rules.RETURNED for r in rows)
    me, admin = frappe.session.user, _admin()
    steps = []
    for i, step in enumerate(config['steps']):
        row = rows[i] if i < len(rows) else None
        if row and returned and row.state != rules.RETURNED:
            # A returned round no longer counts; keep only who was chosen, to prefill the next round.
            row = frappe._dict(assignee=row.assignee, state='', signed_at=None, note='', signature_file=None)
        image = ''
        if with_images and row and row.signature_file and frappe.db.exists('File', row.signature_file):
            file = frappe.get_doc('File', row.signature_file)
            if file.is_private and file.attached_to_doctype == doc.doctype and file.attached_to_name == doc.name:
                from base64 import b64encode
                image = 'data:image/png;base64,' + b64encode(file.get_content(encodings=[])).decode('ascii')
        steps.append(dict(key=step['key'], title=step['title'], assignee=row.assignee if row else '', name=_person(row.assignee) if row else '',
                          state=row.state if row else '', signed_at=str(row.signed_at or '') if row else '', note=row.note or '' if row else '',
                          image=image))
    waiting = None if returned or index is None else index
    started_by = rows[0].assignee if rows else None
    can_act = bool(rows) and not returned and rules.may_act(rows, waiting, me, admin)
    return dict(chain=key, label=config['label'], round=round_, started=bool(rows) and not returned, returned=returned,
                done=bool(rows) and not returned and index is None, current=waiting, steps=steps,
                can_sign=can_act, can_return=can_act and waiting not in (None, 0),
                can_reassign=bool(rows) and not returned and waiting is not None and (me in (started_by, rows[waiting].assignee) or admin))


@frappe.whitelist()
def chain_status(doctype, name):
    """Status for the signing panel; can_start when the preparer may (re)send a non-gated chain."""
    doc, key = _doc(doctype, name)
    info = status(doc, key, with_images=True)
    info['can_start'] = (not rules.chain(key)['gate'] and (not info['round'] or info['returned'])
                         and (doc.owner == frappe.session.user or _admin()) and doc.docstatus == 1)
    return info


def _snapshot(doc, step_key, require_image=False):
    """Private copy of the signer's image attached to the document. The signer was checked as the named
    assignee; they need not have write access to the document (e.g. a director signing the period)."""
    from lotus_farm.digital_signature import signature_image_bytes
    image = signature_image_bytes(frappe.session.user)
    if not image:
        if require_image:
            frappe.throw('Chưa có ảnh chữ ký. Thiết lập chữ ký trong mục Tôi trước khi ký.')
        return ''
    file = frappe.get_doc(dict(doctype='File', file_name='ky-' + step_key.lower() + '.png', content=image, is_private=1,
                              attached_to_doctype=doc.doctype, attached_to_name=doc.name))
    file.flags.ignore_permissions = True
    return file.insert(ignore_permissions=True).name


def _record(doc, row, details=None, require_image=False):
    from lotus_farm.digital_signature import _event
    when = now_datetime()
    file_name = _snapshot(doc, row.step_key, require_image)
    content = fingerprint(doc)
    _event(doc, row.step_key, frappe.session.user, when, signature_type='IMAGE' if file_name else 'NAME',
           details=json.dumps(dict(details or {}, signature_file=file_name, step=row.step_index + 1, content=content)))
    frappe.db.set_value(REQUEST, row.name, dict(state=rules.SIGNED, signed_at=when, signature_file=file_name, content_hash=content),
                        update_modified=False)


def _notify(doc, key, row, title, body=None):
    if not row or not row.get('assignee'):
        return
    from lotus_farm.push_notifications import DEVICE, _add_alert
    app, url = rules.chain(key)['app'], URLS[key](doc)
    if url.startswith('/lotus/'):
        # Print-page links reach the signer in whichever Lotus app their phone is subscribed to.
        apps = frappe.get_all(DEVICE, filters={'user': row['assignee'], 'enabled': 1}, pluck='app', limit_page_length=20)
        app = app if app in apps or not apps else apps[0]
    alert = _add_alert(row['assignee'], app, title, body or (rules.chain(key)['label'] + ' ' + doc.name), url, doc.doctype, doc.name,
                       key='sign:' + doc.doctype + ':' + doc.name + ':' + str(row.get('name') or '') + ':' + title)
    if alert:
        frappe.enqueue('lotus_farm.push_notifications._send_alert', queue='short', enqueue_after_commit=True, alert_name=alert)
    email = frappe.db.get_value('User', row['assignee'], 'email')
    if email and '@' in email:
        frappe.sendmail(recipients=[email], subject=title + ' · ' + doc.name, now=False,
                        message='<p>' + frappe.utils.escape_html(body or (rules.chain(key)['label'] + ' ' + doc.name)) + '</p>'
                                '<p><a href="' + get_url(url) + '">Mở chứng từ trên Lotus</a></p>')
    if row.get('name'):
        frappe.db.set_value(REQUEST, row['name'], 'notified_at', now_datetime(), update_modified=False)


def start(doc, signers, details=None, require_image=False):
    """Create a new round with the chosen signers; the caller signs the first step. Returns status."""
    key = chain_for(doc)
    config = rules.chain(key)
    signers = frappe.parse_json(signers) if isinstance(signers, str) else (signers or {})
    issues = rules.validate_assignment(key, signers, _roles, frappe.session.user)
    if issues:
        frappe.throw('; '.join(issues))
    rows, round_ = _rows(doc)
    if rows and not any(r.state == rules.RETURNED for r in rows) and rules.current(rows) is not None:
        frappe.throw('Chứng từ đang trong lượt ký. Chờ ký xong hoặc trả lại trước.')
    for step in config['steps'][1:]:
        user = signers[step['key']]
        _validate_person(user, step, _company(doc))
    created = []
    for index, step in enumerate(config['steps']):
        user = frappe.session.user if index == 0 else signers[step['key']]
        created.append(frappe.get_doc(dict(doctype=REQUEST, document_type=doc.doctype, document_name=doc.name, chain=key,
                                           company=_company(doc), round=round_ + 1, step_index=index, step_key=step['key'],
                                           title=step['title'], assignee=user,
                                           employee=frappe.db.get_value('Employee', {'user_id': user, 'status': 'Active'}),
                                           state=rules.WAITING if index == 0 else rules.PENDING)).insert(ignore_permissions=True))
    frappe.defaults.set_user_default('lotus_signers_' + key, json.dumps({k: v for k, v in signers.items() if k in {s['key'] for s in config['steps']}}))
    _record(doc, created[0], details, require_image)
    if len(created) > 1:
        frappe.db.set_value(REQUEST, created[1].name, 'state', rules.WAITING, update_modified=False)
        _notify(doc, key, created[1].as_dict(), 'Đến lượt bạn ký: ' + created[1].title)
    return status(doc, key)


def sign(doc, details=None, require_image=False, record=True):
    """The named signer of the waiting step signs. The caller applies what the last signature means.
    record=False marks the step signed when the caller writes its own signature evidence."""
    key = chain_for(doc)
    rows, _ = _rows(doc)
    index = rules.current(rows) if rows else None
    if not rows or any(r.state == rules.RETURNED for r in rows) or not rules.may_act(rows, index, frappe.session.user, _admin()):
        frappe.throw('Chưa đến lượt bạn ký chứng từ này.', frappe.PermissionError)
    if not _admin() and index:
        _validate_person(frappe.session.user, rules.chain(key)['steps'][index], _company(doc))
    if record:
        _record(doc, rows[index], details, require_image)
    else:
        # Purchase approval writes its own audit event and archived PDF, but the signer image
        # must still be snapshotted for the same timeline shown in every Lotus app.
        signature_file = _snapshot(doc, rows[index].step_key)
        frappe.db.set_value(REQUEST, rows[index].name,
                            dict(state=rules.SIGNED, signed_at=now_datetime(),
                                 signature_file=signature_file, content_hash=fingerprint(doc)),
                            update_modified=False)
    _states, done = rules.after_sign(rows, index)
    if not done:
        nxt = rows[index + 1]
        frappe.db.set_value(REQUEST, nxt.name, 'state', rules.WAITING, update_modified=False)
        _notify(doc, key, nxt, 'Đến lượt bạn ký: ' + nxt.title)
    else:
        _notify(doc, key, rows[0], 'Đã ký đủ: ' + doc.name, rules.chain(key)['label'] + ' ' + doc.name + ' đã được ký đủ.')
    return status(doc, key)


def send_back(doc, reason):
    key = chain_for(doc)
    rows, _ = _rows(doc)
    index = rules.current(rows) if rows else None
    reason = str(reason or '').strip()
    if len(reason) < 3:
        frappe.throw('Ghi lý do trả lại.')
    if not rows or index in (None, 0) or not rules.may_act(rows, index, frappe.session.user, _admin()):
        frappe.throw('Chưa đến lượt bạn xử lý chứng từ này.', frappe.PermissionError)
    from lotus_farm.digital_signature import _event
    _event(doc, 'RETURN', frappe.session.user, now_datetime(), details=json.dumps(dict(reason=reason[:500], step=index + 1)))
    frappe.db.set_value(REQUEST, rows[index].name, dict(state=rules.RETURNED, note=reason[:500]), update_modified=False)
    _notify(doc, key, rows[0], 'Bị trả lại: ' + doc.name, rows[index].title + ' trả lại: ' + reason[:200])
    return status(doc, key)


@frappe.whitelist(methods=['POST'])
def reassign(doctype, name, step, user):
    """Hand a step that has not been signed to another eligible employee (preparer, current signer or admin)."""
    doc, key = _doc(doctype, name)
    from lotus_farm.controls import lock
    lock(doctype, name)
    rows, _ = _rows(doc)
    target = next((r for r in rows if r.step_key == step), None)
    if not target or target.state == rules.SIGNED or target.step_index == 0 or any(r.state == rules.RETURNED for r in rows):
        frappe.throw('Không đổi được người ký bước này.')
    waiting = rules.current(rows)
    if not (_admin() or frappe.session.user in (rows[0].assignee, rows[waiting].assignee if waiting is not None else None)):
        frappe.throw('Chỉ người lập, người đang đến lượt ký hoặc quản trị được đổi người ký.', frappe.PermissionError)
    config_step = next(s for s in rules.chain(key)['steps'] if s['key'] == step)
    _validate_person(user, config_step, _company(doc))
    frappe.db.set_value(REQUEST, target.name, dict(assignee=user, employee=frappe.db.get_value('Employee', {'user_id': user, 'status': 'Active'}),
                                                   note=('Chuyển từ ' + _person(target.assignee) + ' bởi ' + _person(frappe.session.user))[:500]),
                        update_modified=False)
    if target.state == rules.WAITING:
        _notify(doc, key, dict(target, assignee=user), 'Đến lượt bạn ký: ' + target.title)
    return status(doc, key)


@frappe.whitelist()
def inbox():
    """Documents waiting for my signature, newest first, with the app link to open them."""
    if frappe.session.user == 'Guest':
        frappe.throw('Vui lòng đăng nhập.', frappe.AuthenticationError)
    rows = frappe.get_all(REQUEST, filters={'assignee': frappe.session.user, 'state': rules.WAITING, 'step_index': ['>', 0]},
                          fields=['document_type', 'document_name', 'chain', 'title', 'modified'], order_by='modified desc', limit_page_length=100)
    result = []
    for row in rows:
        if not frappe.db.exists(row.document_type, row.document_name):
            continue
        doc = frappe.get_doc(row.document_type, row.document_name)
        if not doc.has_permission('read'):
            continue
        config = rules.chain(row.chain)
        result.append(dict(doctype=row.document_type, name=row.document_name, step=row.title, label=config['label'], app=config['app'],
                           url=URLS[row.chain](doc), since=str(row.modified)))
    return result


def print_signatures(doc):
    """Signature boxes for Lotus Print from the latest round: title and the named signer; image and
    time once signed. Empty when the document was never sent for signatures."""
    from lotus_farm import print_kit as pk
    key = chain_for(doc)
    if not key:
        return []
    info = status(doc, key, with_images=True)
    if not info['round']:
        return []
    return [pk.signature(s['title'], s['name'], (s['image'] or None) if s['state'] == rules.SIGNED else None,
                         s['signed_at'] if s['state'] == rules.SIGNED else None) for s in info['steps']]


@frappe.whitelist(methods=['POST'])
def confirm(doctype, name):
    """Sign a non-gated chain step (e.g. stock documents already posted)."""
    doc, key = _doc(doctype, name)
    if rules.chain(key)['gate']:
        frappe.throw('Chứng từ này ký trong màn hình xử lý của nó.')
    from lotus_farm.controls import lock
    lock(doctype, name)
    return sign(doc)


@frappe.whitelist(methods=['POST'])
def request_signatures(doctype, name, signers):
    """Start a non-gated chain on an existing document (stock documents, issue proposals)."""
    doc, key = _doc(doctype, name)
    if rules.chain(key)['gate']:
        frappe.throw('Chứng từ này gửi ký trong màn hình xử lý của nó.')
    if doc.owner != frappe.session.user and not _admin():
        frappe.throw('Chỉ người lập chứng từ được gửi ký.', frappe.PermissionError)
    from lotus_farm.controls import lock
    lock(doctype, name)
    return start(doc, signers)


@frappe.whitelist(methods=['POST'])
def return_document(doctype, name, reason):
    doc, key = _doc(doctype, name)
    from lotus_farm.controls import lock
    lock(doctype, name)
    return send_back(doc, reason)


# Verification: QR on every print -------------------------------------------------------------------

def fingerprint(doc):
    """What a signature covers. The period signs its payroll snapshot; other documents their lines and totals."""
    if doc.doctype == 'Lotus Timekeeping Period':
        return rules.fingerprint(dict(snapshot=doc.get('snapshot_hash') or ''), [])
    header = {field: doc.get(field) for field in ('company', 'supplier', 'set_warehouse', 'posting_date', 'transaction_date',
                                                   'stock_entry_type', 'grand_total', 'total_qty') if doc.meta.has_field(field)}
    return rules.fingerprint(header, [row.as_dict() for row in doc.get('items') or []])


def _secret():
    from frappe.utils.password import get_encryption_key
    return get_encryption_key()


def verify_url(doc, round_=None):
    from urllib.parse import urlencode
    if round_ is None:
        round_ = _rows(doc)[1]
    if not round_:
        return ''
    token = rules.verify_token(_secret(), doc.doctype, doc.name, round_)
    return get_url('/verify/lotus?' + urlencode(dict(dt=doc.doctype, n=doc.name, r=round_, t=token)))


def print_verification(doc):
    """{url, qr} for the print, or None when the document was never sent for signatures."""
    url = verify_url(doc)
    if not url:
        return None
    from base64 import b64encode
    from lotus_farm.digital_signature import _qr_png
    return dict(url=url, qr='data:image/png;base64,' + b64encode(_qr_png(url)).decode('ascii'))


@frappe.whitelist(allow_guest=True, methods=['GET'])
def verify(dt, n, r, t):
    """Public summary for a QR on a printed document: no amounts, names or files, only enough to compare
    the paper with Lotus (type, number, date, signing steps and times, whether the content still matches)."""
    import hmac
    try:
        round_ = int(r)
    except (TypeError, ValueError):
        return dict(valid=False)
    if not (dt and n and t) or len(str(t)) != 40 or not hmac.compare_digest(str(t), rules.verify_token(_secret(), dt, n, round_)):
        return dict(valid=False)
    if not frappe.db.exists(dt, n):
        return dict(valid=False)
    doc = frappe.get_doc(dt, n)
    key = chain_for(doc)
    rows = frappe.get_all(REQUEST, filters={'document_type': dt, 'document_name': n, 'round': round_},
                          fields=['title', 'state', 'signed_at', 'content_hash'], order_by='step_index asc')
    if not key or not rows:
        return dict(valid=False)
    latest = max((r for r in rows if r.state == rules.SIGNED and r.content_hash), key=lambda r: r.signed_at, default=None)
    newer = frappe.db.count(REQUEST, {'document_type': dt, 'document_name': n, 'round': ['>', round_]})
    matches = not latest or latest.content_hash == fingerprint(doc)
    states = [r.state for r in rows]
    status_text = 'Đã có lượt ký mới — bản in này không còn hiệu lực' if newer else rules.verdict(states, matches, doc.docstatus == 2)
    when = doc.get('posting_date') or doc.get('transaction_date') or doc.get('month') or ''
    from lotus_farm import print_kit as pk
    return dict(valid=True, document_type=rules.chain(key)['label'], document_no=doc.name,
                date=pk.vn_date(when) if when and doc.doctype != 'Lotus Timekeeping Period' else str(when),
                status=status_text, ok=status_text == 'Đã ký đủ',
                steps=[dict(title=r.title, state=r.state or rules.PENDING, signed_at=pk.vn_datetime(r.signed_at) if r.signed_at else '') for r in rows],
                notice='Đối chiếu số chứng từ, ngày và các chữ ký trên bản giấy với thông tin này. Muốn xem nội dung cần đăng nhập Lotus.')