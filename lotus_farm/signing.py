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
from urllib.parse import quote, urlencode

import frappe
from frappe.utils import cint, get_url, now_datetime

from lotus_farm import signing_rules as rules

REQUEST = 'Lotus Sign Request'
# chain -> link to the document inside the chain's app (push targets must stay in that app).
URLS = {
    'purchase_proposal': lambda d: '/buying?proposal=' + quote(d.name),
    'purchase_proposal_small': lambda d: '/buying?proposal=' + quote(d.name),
    'issue_proposal': lambda d: '/warehouse?doc=' + quote(d.name) + '&doctype=Material%20Request',
    'purchase_order': lambda d: '/buying?doc=' + quote(d.name),
    'stock_document': lambda d: '/warehouse?doc=' + quote(d.name) + '&doctype=' + quote(d.doctype),
    # The period is signed on its print page, which any signer can open (no HR role needed).
    'timekeeping_period': lambda d: '/lotus/in-luong?company=' + quote(d.company) + '&month=' + quote(d.month),
    'payment_voucher': lambda d: '/lotus/tai-chinh?tab=cash&doctype=' + quote(d.doctype) + '&doc=' + quote(d.name),
}


def chain_for(doc, fresh=False):
    """fresh=True picks the chain for a new round; otherwise a started round keeps the chain it began with."""
    if doc.doctype == 'Material Request':
        if doc.material_request_type != 'Purchase':
            return 'issue_proposal'
        from lotus_farm import proposal_rules
        if not fresh and doc.name:
            started = frappe.get_all(REQUEST, filters={'document_type': doc.doctype, 'document_name': doc.name},
                                     pluck='chain', order_by='round desc', limit_page_length=1)
            if started and started[0] in proposal_rules.CHAINS:
                return started[0]
        from lotus_farm.purchase_flow import enabled
        if enabled(doc.company):
            return 'purchase_proposal'
        return proposal_rules.chain_for_lines(doc.items)
    if (doc.doctype == 'Payment Entry' and (doc.get('payment_type') != 'Receive' or doc.get('party_type')=='Supplier')) or (doc.doctype == 'Journal Entry' and doc.get('lotus_payment_kind') in ('Salary', 'Advance', 'Statutory', 'PurchaseFunding', 'PurchaseReimbursement')):
        return 'payment_voucher'
    if doc.doctype == 'Purchase Receipt':
        return _receipt_chain(doc, fresh)
    return {'Purchase Order': 'purchase_order', 'Stock Entry': 'stock_document', 'Stock Reconciliation': 'stock_document',
            'Lotus Timekeeping Period': 'timekeeping_period'}.get(doc.doctype)


def _receipt_chain(doc, fresh=False):
    """A receipt against an order of the purchase-flow company is signed by the storekeeper who confirms it
    (one step, spec 003 FR-043). Returns, other companies and rounds begun on the earlier three-step chain
    stay on stock_document."""
    from lotus_farm.purchase_flow import enabled
    if doc.get('is_return') or not enabled(doc.company) or not any(r.get('purchase_order') for r in doc.get('items') or []):
        return 'stock_document'
    if not fresh and doc.name:
        started = frappe.get_all(REQUEST, filters={'document_type': doc.doctype, 'document_name': doc.name},
                                 pluck='chain', order_by='round desc', limit_page_length=1)
        if started and started[0] == 'stock_document':
            return 'stock_document'
    return 'purchase_receipt'


def _admin():
    return frappe.session.user == 'Administrator'


def _roles(user):
    return frappe.get_roles(user)


def can_view(doctype=None, name=None, doc=None, user=None):
    """Read access for signing (spec 003, FR-027): normal read permission, the preparer, or anyone named in
    the latest signing round, so a signer without rights on the module still sees what they must sign.
    Read-only: acting stays limited to the person whose turn it is."""
    user = user or frappe.session.user
    if not user or user == 'Guest':
        return False
    doc = doc or frappe.get_doc(doctype, name)
    if doc.owner == user or frappe.has_permission(doc.doctype, 'read', doc=doc, user=user):
        return True
    last = frappe.get_all(REQUEST, filters={'document_type': doc.doctype, 'document_name': doc.name}, pluck='round',
                          order_by='round desc', limit_page_length=1)
    return bool(last) and bool(frappe.db.exists(REQUEST, {'document_type': doc.doctype, 'document_name': doc.name,
                                                          'round': last[0], 'assignee': user}))


def _doc(doctype, name, permission='read'):
    if frappe.session.user == 'Guest':
        frappe.throw('Vui lòng đăng nhập.', frappe.AuthenticationError)
    doc = frappe.get_doc(doctype, name)
    if permission == 'read':
        if not can_view(doc=doc):
            frappe.throw('Không có quyền xem chứng từ này.', frappe.PermissionError)
    else:
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
                          fields=['name', 'round', 'chain', 'step_index', 'step_key', 'title', 'assignee', 'employee', 'state', 'signed_at',
                                  'signature_file', 'note', 'content_hash', 'signer_designation', 'initials_file'],
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
                          designation=(row.get('signer_designation') or '') if row else '', image=image))
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
    info['signed_copy'] = copy_info(doc)
    return info


def copy_info(doc):
    """{url, pdf_sha256} of the stored signed PDF of the latest round, None until that round is complete."""
    from lotus_farm import signed_copy
    copy = signed_copy.current(doc)
    if not copy:
        return None
    return dict(url='/api/method/lotus_farm.signing.signed_pdf?' + urlencode(dict(doctype=doc.doctype, name=doc.name)),
                pdf_sha256=copy['pdf_sha256'], created_at=str(copy['created_at'] or ''))


@frappe.whitelist()
def signed_pdf(doctype, name):
    """Download the stored signed copy (spec 003, FR-014): anyone who may see the document."""
    _login()
    doc = frappe.get_doc(doctype, name)
    if not can_view(doc=doc):
        frappe.throw('Không có quyền xem chứng từ này.', frappe.PermissionError)
    from lotus_farm import signed_copy
    copy = signed_copy.current(doc)
    if not copy:
        frappe.throw('Chứng từ chưa có bản PDF đã ký.')
    signed_copy.respond(copy, 'da-ky-' + name)


def _snapshot(doc, step_key, require_image=False):
    """Private copy of the signer's image attached to the document. The signer was checked as the named
    assignee; they need not have write access to the document (e.g. a director signing the period)."""
    from lotus_farm.digital_signature import signature_image_bytes
    image = signature_image_bytes(frappe.session.user)
    if not image:
        if require_image:
            frappe.throw('Chưa có ảnh chữ ký. Thiết lập chữ ký trong mục Tôi trước khi ký.')
        return ''
    return _private_copy(doc, 'ky-' + step_key.lower() + '.png', image)


def _private_copy(doc, file_name, content):
    file = frappe.get_doc(dict(doctype='File', file_name=file_name, content=content, is_private=1,
                              attached_to_doctype=doc.doctype, attached_to_name=doc.name))
    file.flags.ignore_permissions = True
    return file.insert(ignore_permissions=True).name


def _image_sha(file_name):
    if not file_name:
        return ''
    import hashlib
    return hashlib.sha256(frappe.get_doc('File', file_name).get_content(encodings=[])).hexdigest()


def _audit(key, row, content, image_sha):
    """Who signed, from where, in which role and title (FR-013). Typed columns of Lotus Signature Event."""
    user = frappe.session.user
    steps = rules.chain(key)['steps']
    step = steps[row.step_index] if row.step_index < len(steps) else {}
    roles = sorted(set(step.get('roles') or ()) & set(frappe.get_roles(user)))
    request = getattr(frappe.local, 'request', None)
    agent = (frappe.get_request_header('User-Agent') if request else '') or ''
    return dict(ip=getattr(frappe.local, 'request_ip', None) or '', user_agent=agent[:500], roles=', '.join(roles),
                designation=frappe.db.get_value('Employee', {'user_id': user, 'status': 'Active'}, 'designation') or '',
                round=cint(row.get('round')), step_key=row.step_key, content_hash=content, image_sha256=image_sha)


def _record(doc, row, details=None, require_image=False, key=None):
    from lotus_farm.digital_signature import _event, initials_image_bytes
    key = key or row.get('chain') or chain_for(doc)
    when = now_datetime()
    file_name = _snapshot(doc, row.step_key, require_image)
    content = fingerprint(doc)
    audit = _audit(key, row, content, _image_sha(file_name))
    _event(doc, row.step_key, frappe.session.user, when, signature_type='IMAGE' if file_name else 'NAME',
           details=json.dumps(dict(details or {}, signature_file=file_name, step=row.step_index + 1, content=content)), extra=audit)
    values = dict(state=rules.SIGNED, signed_at=when, signature_file=file_name, content_hash=content,
                  signer_designation=audit['designation'])
    if rules.checker_step(key) == row.step_index:
        # Ký nháy of the checking step, printed at the foot of every page of the signed copy (FR-023).
        initials = initials_image_bytes(frappe.session.user)
        values['initials_file'] = _private_copy(doc, 'ky-nhay-' + row.step_key.lower() + '.png', initials) if initials else ''
    frappe.db.set_value(REQUEST, row.name, values,
                        update_modified=False)


def _notify(doc, key, row, title, body=None):
    """Tell one signer. A failure to notify must never undo the signing action itself (FR-021):
    alert, push and e-mail run inside a savepoint and errors only reach the Error Log."""
    if not row or not row.get('assignee'):
        return
    frappe.db.savepoint('lotus_sign_notify')
    try:
        _deliver(doc, key, row, title, body)
    except Exception:
        frappe.db.rollback(save_point='lotus_sign_notify')
        frappe.log_error(frappe.get_traceback(), 'Lotus: thông báo ký')


def _deliver(doc, key, row, title, body):
    from lotus_farm.push_notifications import DEVICE, _add_alert
    user, text, link = row['assignee'], body or (rules.chain(key)['label'] + ' ' + doc.name), URLS[key](doc)
    devices = frappe.get_all(DEVICE, filters={'user': user, 'enabled': 1}, pluck='app', order_by='last_seen desc',
                             limit_page_length=20)
    app = rules.notify_app(rules.chain(key)['app'], devices)
    if app:
        alert = _add_alert(user, app, title, text, rules.push_link(app, link, doc.doctype, doc.name), doc.doctype, doc.name,
                           key='sign:' + doc.doctype + ':' + doc.name + ':' + str(row.get('name') or '') + ':' + title)
        if alert:
            frappe.enqueue('lotus_farm.push_notifications._send_alert', queue='short', enqueue_after_commit=True, alert_name=alert)
    email = frappe.db.get_value('User', user, 'email')
    if email and '@' in email:
        # One link for every device: /lotus/mo opens the phone app on a phone, the desktop screen otherwise.
        opener = '/lotus/mo?' + urlencode(dict(dt=doc.doctype, n=doc.name))
        frappe.sendmail(recipients=[email], subject=title + ' · ' + doc.name, now=False,
                        message='<p>' + frappe.utils.escape_html(text) + '</p>'
                                '<p><a href="' + frappe.utils.escape_html(get_url(opener)) + '">Mở chứng từ trên Lotus</a></p>')
    if row.get('name'):
        frappe.db.set_value(REQUEST, row['name'], 'notified_at', now_datetime(), update_modified=False)


def start(doc, signers, details=None, require_image=False, effect=None):
    """Create a new round with the chosen signers; the caller signs the first step. Returns status.
    A one-step chain (purchase receipt confirmed by the storekeeper) completes at once: see _completed."""
    key = chain_for(doc, fresh=True)
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
    _record(doc, created[0], details, require_image, key=key)
    if len(created) > 1:
        frappe.db.set_value(REQUEST, created[1].name, 'state', rules.WAITING, update_modified=False)
        _notify(doc, key, created[1].as_dict(), 'Đến lượt bạn ký: ' + created[1].title)
    else:
        _completed(doc, key, round_ + 1, effect)
    return status(doc, key)


def _completed(doc, key, round_, effect=None):
    """Last signature of a round, in the signing transaction: the document's own effect (submit, approve,
    close the period), then the fixed signed PDF (spec 003, R1). A failure anywhere undoes the signature."""
    if effect:
        effect()
        doc.reload()
    from lotus_farm import signed_copy
    signed_copy.archive(doc, key, round_)


def sign(doc, details=None, require_image=False, effect=None):
    """The named signer of the waiting step signs. effect() is what the last signature means for the
    document (submit, approve, close); it runs before the signed copy is stored."""
    key = chain_for(doc)
    rows, round_ = _rows(doc)
    index = rules.current(rows) if rows else None
    if not rows or any(r.state == rules.RETURNED for r in rows) or not rules.may_act(rows, index, frappe.session.user, _admin()):
        frappe.throw('Chưa đến lượt bạn ký chứng từ này.', frappe.PermissionError)
    if not _admin() and index:
        _validate_person(frappe.session.user, rules.chain(key)['steps'][index], _company(doc))
    # Previously signed steps must still match the document being signed now.
    if any(not r.content_hash or r.content_hash != fingerprint(doc) for r in rows if r.state == rules.SIGNED):
        frappe.throw('Chứng từ đã đổi nội dung sau chữ ký trước. Trả lại và ký lại từ đầu.')
    _record(doc, rows[index], details, require_image, key=key)
    _states, done = rules.after_sign(rows, index)
    if not done:
        nxt = rows[index + 1]
        frappe.db.set_value(REQUEST, nxt.name, 'state', rules.WAITING, update_modified=False)
        _notify(doc, key, nxt, 'Đến lượt bạn ký: ' + nxt.title)
    else:
        _completed(doc, key, round_, effect)
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
def reassign(doctype, name, step, user, reason=None):
    """Hand a step that has not been signed to another eligible employee (preparer, current signer or admin).
    A reason is required and the change is kept in the signing history (spec 003, FR-016)."""
    reason = str(reason or '').strip()
    if len(reason) < 3:
        frappe.throw('Ghi lý do chuyển người ký.')
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
                                                   note=('Chuyển từ ' + _person(target.assignee) + ' bởi ' + _person(frappe.session.user)
                                                         + ': ' + reason)[:500]),
                        update_modified=False)
    from lotus_farm.digital_signature import _event
    _event(doc, 'REASSIGN', frappe.session.user, now_datetime(),
           details=json.dumps(dict(step=target.step_index + 1, step_key=step, from_user=target.assignee, to_user=user, reason=reason[:300]), ensure_ascii=False),
           extra=dict(round=cint(target.get('round')), step_key=step))
    if target.state == rules.WAITING:
        _notify(doc, key, dict(target, assignee=user), 'Đến lượt bạn ký: ' + target.title)
    return status(doc, key)


@frappe.whitelist()
def inbox(limit=100, offset=0, chain=None):
    """Chờ tôi ký (spec 003, FR-011): every document waiting for my signature, across chains, newest alert
    first. Each row carries what the list shows and where to open it on desktop, phone and print. Being
    named in the round is enough to see it (can_view); acting still needs my turn."""
    user = _login()
    rows, total = _waiting(user, cint(limit) or 100, cint(offset), chain)
    found = {}
    for row in rows:
        found.setdefault(row.document_type, []).append(row.document_name)
    summaries = {dt: _summaries(dt, names) for dt, names in found.items()}
    result = []
    for row in rows:
        summary = summaries.get(row.document_type, {}).get(row.document_name)
        if summary is None:
            continue  # deleted since the alert
        config = rules.chain(row.chain)
        result.append(dict(doctype=row.document_type, name=row.document_name, chain=row.chain, chain_label=config['label'],
                           step=row.step_index + 1, step_title=row.title, notified_at=str(row.notified_at or row.modified or ''),
                           **summary, **targets(row.document_type, row.document_name, row.chain)))
    return dict(rows=result, total=total)


@frappe.whitelist()
def inbox_count():
    """The number on the Chờ tôi ký button; one query, polled when the app gets focus."""
    user = _login()
    return dict(count=_waiting(user, 0, 0, None, count_only=True))


def _login():
    if frappe.session.user == 'Guest':
        frappe.throw('Vui lòng đăng nhập.', frappe.AuthenticationError)
    return frappe.session.user


def _waiting(user, limit, offset, chain, count_only=False):
    """Open steps assigned to the user in the latest round of each document (an older round's row that was
    never closed does not count)."""
    filters = {'assignee': user, 'state': rules.WAITING, 'step_index': ['>', 0]}
    if chain:
        filters['chain'] = chain
    rows = frappe.get_all(REQUEST, filters=filters, limit_page_length=0,
                          fields=['document_type', 'document_name', 'chain', 'title', 'step_index', 'round', 'notified_at', 'modified'])
    if rows:
        newest = {}
        for r in frappe.get_all(REQUEST, filters={'document_name': ['in', list({r.document_name for r in rows})]},
                                fields=['document_type', 'document_name', 'round'], limit_page_length=0):
            key = (r.document_type, r.document_name)
            newest[key] = max(newest.get(key, 0), cint(r.round))
        rows = [r for r in rows if cint(r.round) == newest.get((r.document_type, r.document_name))]
    if count_only:
        return len(rows)
    rows.sort(key=lambda r: (str(r.notified_at or ''), str(r.modified or '')), reverse=True)
    return rows[offset:offset + limit], len(rows)


# What the inbox shows of each kind of document: (date field, amount field or child-table sum, currency field).
_SUMMARY = {
    'Material Request': ('transaction_date', ('Material Request Item', 'amount'), None),
    'Purchase Order': ('transaction_date', 'grand_total', 'currency'),
    'Purchase Receipt': ('posting_date', 'grand_total', 'currency'),
    'Payment Entry': ('posting_date', 'paid_amount', 'paid_from_account_currency'),
    'Journal Entry': ('posting_date', 'total_debit', None),
    'Stock Entry': ('posting_date', 'total_incoming_value', None),
    'Stock Reconciliation': ('posting_date', None, None),
    'Lotus Timekeeping Period': ('month', None, None),
}


def _summaries(doctype, names):
    date_field, amount, currency = _SUMMARY.get(doctype, (None, None, None))
    meta = frappe.get_meta(doctype)
    fields = ['name', 'owner', 'modified'] + [f for f in (date_field, currency) if f and meta.has_field(f)]
    if isinstance(amount, str) and meta.has_field(amount):
        fields.append(amount)
    docs = frappe.get_all(doctype, filters={'name': ['in', names]}, fields=fields, limit_page_length=0)
    totals = {}
    if isinstance(amount, tuple) and frappe.get_meta(amount[0]).has_field(amount[1]):
        child, field = amount
        for row in frappe.get_all(child, filters={'parent': ['in', names], 'parenttype': doctype}, fields=['parent', field],
                                  limit_page_length=0):
            totals[row.parent] = totals.get(row.parent, 0) + (row.get(field) or 0)
    result = {}
    for d in docs:
        result[d.name] = dict(creator=d.owner, creator_name=_person(d.owner), posting_date=str(d.get(date_field) or '') if date_field else '',
                              amount=totals.get(d.name) if isinstance(amount, tuple) else d.get(amount) if isinstance(amount, str) else None,
                              currency=(d.get(currency) if currency else None) or 'VND', modified=str(d.modified))
    return result


def targets(doctype, name, chain=None):
    """Where one document opens: the desktop screen, the phone signing sheet and its print page."""
    from urllib.parse import urlencode
    chain = chain or frappe.db.get_value(REQUEST, {'document_type': doctype, 'document_name': name}, 'chain', order_by='round desc')
    buying = {'Material Request': 'needs', 'Purchase Order': 'orders', 'Purchase Receipt': 'receipts'}
    if doctype in buying:
        desktop = '/lotus/mua-hang?' + urlencode(dict(buying_view=buying[doctype], purchase_doc=name, purchase_type=buying[doctype],
                                                          purchase_doctype=doctype))
    elif doctype in ('Payment Entry', 'Journal Entry'):
        desktop = '/lotus/tai-chinh?' + urlencode(dict(tab='cash', doctype=doctype, doc=name))
    else:
        desktop = ''  # no desktop screen of its own: the signing sheet is the way in
    app = rules.notify_app(rules.chain(chain)['app'] if chain in rules.CHAINS else 'buying', [])
    prints = {'Material Request': '/lotus/in-de-xuat?' + urlencode(dict(name=name)),
              'Purchase Order': '/lotus/in-don-mua?' + urlencode(dict(name=name)),
              'Payment Entry': '/lotus/in-phieu-chi?' + urlencode(dict(doctype=doctype, name=name)),
              'Journal Entry': '/lotus/in-phieu-chi?' + urlencode(dict(doctype=doctype, name=name))}
    if doctype in ('Purchase Receipt', 'Stock Entry', 'Stock Reconciliation'):
        prints[doctype] = '/lotus/in-phieu?' + urlencode(dict(doctype=doctype, name=name))
    if doctype == 'Lotus Timekeeping Period':
        company, month = frappe.db.get_value(doctype, name, ['company', 'month']) or ('', '')
        prints[doctype] = '/lotus/in-luong?' + urlencode(dict(company=company or '', month=month or ''))
    sign = '/lotus/cho-ky?' + urlencode(dict(sign_dt=doctype, sign_dn=name))
    return dict(desktop_url=desktop, sign_url=sign, mobile_url=rules.sign_link(app, doctype, name), print_url=prints.get(doctype, ''))


def _handler(key):
    """Each chain signs through its own screen logic (checks, effect of the last signature)."""
    if key in ('purchase_proposal', 'purchase_proposal_small'):
        from lotus_farm import purchase_proposal
        return lambda doc: purchase_proposal.sign(doc.name, str(doc.modified))
    if key == 'purchase_order':
        from lotus_farm import purchasing
        return lambda doc: purchasing.approve_order(doc.name, str(doc.modified))
    if key == 'payment_voucher':
        from lotus_farm.finance import payments
        return lambda doc: payments.sign_payment(doc.doctype, doc.name)
    if key == 'timekeeping_period':
        from lotus_farm import hr_period
        return lambda doc: hr_period.sign_period(doc.company, doc.month)
    if key in ('stock_document', 'issue_proposal'):
        return lambda doc: confirm(doc.doctype, doc.name)
    return None


@frappe.whitelist(methods=['POST'])
def return_any(doctype, name, reason, modified=None):
    """Trả lại from the shared signing sheet: each chain returns through its own screen logic, which keeps
    the document's own status in step (proposal, order, voucher, period); stock documents use the generic one."""
    _login()
    doc = frappe.get_doc(doctype, name)
    if modified and str(doc.modified) != str(modified):
        frappe.throw('Chứng từ đã thay đổi sau khi mở. Mở lại để xem trước khi trả lại.')
    key = chain_for(doc)
    if key in ('purchase_proposal', 'purchase_proposal_small'):
        from lotus_farm import purchase_proposal
        return purchase_proposal.return_proposal(doc.name, str(doc.modified), reason)
    if key == 'purchase_order':
        from lotus_farm import purchasing
        return purchasing.reject_order(doc.name, str(doc.modified), reason)
    if key == 'payment_voucher':
        from lotus_farm.finance import payments
        return payments.return_payment(doc.doctype, doc.name, reason)
    if key == 'timekeeping_period':
        from lotus_farm import hr_period
        return hr_period.return_period(doc.company, doc.month, reason)
    return return_document(doctype, name, reason)


@frappe.whitelist(methods=['POST'])
def sign_many(items):
    """Ký nhiều (spec 003, FR-017): one confirmation for several documents waiting for me. Each document is
    signed through its own chain in its own savepoint, so one failure leaves the others signed."""
    _login()
    items = frappe.parse_json(items) if isinstance(items, str) else (items or [])
    if not isinstance(items, list) or not items:
        frappe.throw('Chọn chứng từ cần ký.')
    if len(items) > 50:
        frappe.throw('Mỗi lần ký nhiều tối đa 50 chứng từ.')
    wanted = sorted({(str(i.get('doctype') or ''), str(i.get('name') or '')): str(i.get('modified') or '')
                     for i in items if isinstance(i, dict)}.items())  # fixed order: documents are locked one after another
    results = []
    for (doctype, name), modified in wanted:
        frappe.db.savepoint('lotus_bulk_sign')
        try:
            if not doctype or not frappe.db.exists(doctype, name):
                frappe.throw('Không tìm thấy chứng từ.')
            doc = frappe.get_doc(doctype, name)
            if modified and str(doc.modified) != modified:
                frappe.throw('Chứng từ đã thay đổi sau khi mở danh sách. Mở lại để xem trước khi ký.')
            handler = _handler(chain_for(doc))
            if not handler:
                frappe.throw('Chứng từ này không ký nhiều được.')
            handler(doc)
            results.append(dict(doctype=doctype, name=name, ok=True, message='Đã ký'))
        except Exception as error:
            frappe.db.rollback(save_point='lotus_bulk_sign')
            frappe.clear_messages()
            known = isinstance(error, (frappe.ValidationError, frappe.PermissionError))
            if not known:
                frappe.log_error(frappe.get_traceback(), 'Lotus: ký nhiều')
            message = frappe.utils.strip_html(str(error)).strip() if known else 'Lỗi hệ thống khi ký; đã ghi nhật ký lỗi.'
            results.append(dict(doctype=doctype, name=name, ok=False, message=message[:300] or 'Không ký được.'))
    return dict(results=results, signed=sum(1 for r in results if r['ok']))


@frappe.whitelist()
def open_targets(doctype, name):
    """For /lotus/mo: the two links of one document I may see."""
    doc = frappe.get_doc(doctype, name)
    if not can_view(doc=doc):
        frappe.throw('Không có quyền xem chứng từ này.', frappe.PermissionError)
    return targets(doctype, name, chain_for(doc))


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
                         s['signed_at'] if s['state'] == rules.SIGNED else None, designation=s.get('designation') or '',
                         electronic=s['state'] == rules.SIGNED) for s in info['steps']]


def print_initials(doc):
    """Ký nháy of the checking step of the latest round, as a data URI for the page footer (FR-023)."""
    key = chain_for(doc)
    step = rules.checker_step(key) if key else None
    if step is None:
        return None
    rows, _ = _rows(doc)
    row = rows[step] if step < len(rows) else None
    if not row or row.state != rules.SIGNED or not row.get('initials_file') or not frappe.db.exists('File', row.initials_file):
        return None
    file = frappe.get_doc('File', row.initials_file)
    if not file.is_private or file.attached_to_doctype != doc.doctype or file.attached_to_name != doc.name:
        return None
    from base64 import b64encode
    return 'data:image/png;base64,' + b64encode(file.get_content(encodings=[])).decode('ascii')


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
    if key in ('purchase_order', 'payment_voucher', 'purchase_proposal', 'purchase_proposal_small', 'timekeeping_period', 'purchase_receipt'):
        # These keep a status of their own in step with the signatures; their screens return them.
        # A confirmed receipt is not returned: it is cancelled with a reason.
        frappe.throw('Trả lại chứng từ này trong màn hình xử lý của nó.')
    from lotus_farm.controls import lock
    lock(doctype, name)
    return send_back(doc, reason)


# Verification: QR on every print -------------------------------------------------------------------

def _purchase_json(value):
    def normalize(v):
        if isinstance(v,dict):
            return {k:normalize({a:(b or 0) for a,b in frappe.parse_json(x).items()} if k=='item_tax_rate' and x else x) for k,x in v.items()}
        if isinstance(v,(list,tuple)):
            return [normalize(x) for x in v]
        if isinstance(v,(float,int)):
            return round(float(v),6)
        return v
    return json.dumps(normalize(value),sort_keys=True,default=str)


def fingerprint(doc):
    """What a signature covers. The period signs its payroll snapshot; other documents their lines and totals."""
    if doc.doctype == 'Lotus Timekeeping Period':
        return rules.fingerprint(dict(snapshot=doc.get('snapshot_hash') or ''), [])
    if doc.doctype == 'Payment Entry':
        if doc.get('lotus_procurement_key'):
            return rules.fingerprint(dict(purchase_payment=_purchase_json({k: doc.get(k) for k in (
                'company', 'party_type', 'party', 'payment_type', 'posting_date', 'paid_from', 'paid_to',
                'paid_amount', 'received_amount', 'source_exchange_rate', 'target_exchange_rate', 'reference_no', 'reference_date',
                'lotus_procurement_key')} | {'references': [[r.reference_doctype, r.reference_name, r.allocated_amount] for r in doc.references]})), [])
        return rules.fingerprint(dict(party=doc.party, paid_from=doc.paid_from, paid_amount=doc.paid_amount, posting_date=str(doc.posting_date),
                                      references=';'.join('%s=%s' % (r.reference_name, r.allocated_amount) for r in doc.get('references') or [])), [])
    if doc.doctype == 'Journal Entry':
        if doc.get('lotus_purchase_funding'):
            return rules.fingerprint(dict(funding=_purchase_json({k: doc.get(k) for k in ('company', 'posting_date', 'lotus_payment_kind',
                'lotus_purchase_funding', 'lotus_funding_hash', 'cheque_no', 'cheque_date')} |
                {'accounts': [[a.account, a.party_type, a.party, a.reference_type, a.reference_name,
                    a.debit_in_account_currency, a.credit_in_account_currency, a.exchange_rate, a.cost_center] for a in doc.accounts]})), [])
        return rules.fingerprint(dict(posting_date=str(doc.posting_date), total=doc.total_debit,
                                      accounts=';'.join('%s:%s:%s' % (a.account, a.debit, a.credit) for a in doc.get('accounts') or [])), [])
    header = {field: doc.get(field) for field in ('company', 'supplier', 'set_warehouse', 'posting_date', 'transaction_date',
                                                   'stock_entry_type', 'grand_total', 'total_qty') if doc.meta.has_field(field)}
    if doc.doctype == 'Material Request' and doc.get('lotus_proposal_policy') == 2:
        header['proposal'] = _purchase_json(dict(department=doc.get('lotus_department'), reason=doc.get('lotus_request_note'),
            owner=doc.owner, lines=[{k: r.get(k) for k in ('lotus_specification', 'lotus_supplier_hint', 'lotus_purpose',
                'lotus_notes', 'lotus_purchase_sources')} for r in doc.items]))
    if any(r.get('lotus_purchase_kind') for r in doc.get('items') or []):
        header['procurement'] = _purchase_json(dict(lines=[{k: r.get(k) for k in ('lotus_purchase_kind', 'lotus_line_vat', 'lotus_line_freight',
            'lotus_quote_reason', 'supplier_quotation', 'supplier_quotation_item', 'material_request', 'material_request_item',
            'conversion_factor', 'item_tax_template', 'item_tax_rate', 'lotus_farm', 'lotus_farm_block', 'expense_account')} for r in doc.items],
            taxes=[{k: r.get(k) for k in ('charge_type', 'account_head', 'rate', 'tax_amount', 'category', 'add_deduct_tax')} for r in doc.get('taxes') or []]))
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
    from lotus_farm import print_kit as pk, signed_copy
    copy = signed_copy.latest(dt, n, round_)
    return dict(valid=True, document_type=rules.chain(key)['label'], document_no=doc.name,
                archive=bool(copy), archive_match=signed_copy.matches(copy) if copy else None,
                date=pk.vn_date(when) if when and doc.doctype != 'Lotus Timekeeping Period' else str(when),
                status=status_text, ok=status_text == 'Đã ký đủ',
                steps=[dict(title=r.title, state=r.state or rules.PENDING, signed_at=pk.vn_datetime(r.signed_at) if r.signed_at else '') for r in rows],
                notice='Đối chiếu số chứng từ, ngày và các chữ ký trên bản giấy với thông tin này. Muốn xem nội dung cần đăng nhập Lotus.')
