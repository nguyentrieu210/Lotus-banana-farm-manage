"""Online purchase proposal on a real site with named signers: pick three people from HR → each signs in
turn, only on their turn → return restarts → director's signature submits → print. Rolls back."""
import json
import os

import frappe

frappe.init(site=os.environ.get('SITE', 'frontend'), sites_path='/home/frappe/frappe-bench/sites')
frappe.connect()
frappe.set_user('Administrator')
frappe.in_test = True
from PIL import Image
from io import BytesIO

from lotus_farm import digital_signature, purchase_proposal as pp, signing
from lotus_farm.www import lotus_material_proposal_print as printer

report = {}
SIGNERS = dict(DEPARTMENT=('Lotus Field Supervisor',), PURCHASING=('Accounts User',), APPROVE=('Lotus Purchase Approver',))


def person(key, roles, company):
    email = 'lotus-sign-%s@example.com' % key.lower()
    user = frappe.get_doc(dict(doctype='User', email=email, first_name='Ký ' + key.title(), send_welcome_email=0, enabled=1,
                               roles=[dict(role=r) for r in (*roles, 'Purchase User', 'Stock User')])).insert(ignore_permissions=True)
    frappe.get_doc(dict(doctype='Employee', first_name='Ký ' + key.title(), gender='Male', date_of_birth='1990-01-01', date_of_joining='2024-01-01',
                        company=company, status='Active', user_id=user.name)).insert(ignore_permissions=True)
    return user.name


def as_user(user, fn, *args):
    frappe.set_user(user)
    try:
        return fn(*args)
    finally:
        frappe.set_user('Administrator')


try:
    image = Image.open(BytesIO(digital_signature.signature_image_bytes('Administrator'))).convert('RGBA')
    histogram = image.getchannel('A').histogram()
    report['signature_transparent_share'] = round(histogram[0] / sum(histogram), 3)
    admin_image = digital_signature.signature_image_bytes('Administrator')
    digital_signature.signature_image_bytes = lambda user: admin_image  # test signers share the admin's image
    company = frappe.get_all('Company', pluck='name')[0]
    people = {key: person(key, roles, company) for key, roles in SIGNERS.items()}
    options = pp.signer_options(company)
    for key, user in people.items():
        assert user in [c['user'] for c in options['candidates'][key]], (key, options['candidates'][key])
    assert people['APPROVE'] not in [c['user'] for c in options['candidates']['DEPARTMENT']], 'only the step role is offered'

    warehouse = frappe.get_all('Warehouse', filters={'company': company, 'is_group': 0}, pluck='name', limit=1)[0]
    items = frappe.get_all('Item', filters={'is_stock_item': 1, 'disabled': 0}, fields=['name', 'stock_uom'], limit=2)
    values = dict(reason='Chăm sóc vườn, buồng khu A + B + C', department='Đội khu A', warehouse=warehouse,
                  items=[dict(item_code=i.name, uom=i.stock_uom, qty=5 + n, rate=0, schedule_date=frappe.utils.add_days(frappe.utils.nowdate(), 2),
                              lotus_specification='cuộn 1 kg', lotus_purpose='Bón khu A', lotus_supplier_hint='') for n, i in enumerate(items)])
    d = pp.save_proposal(company, values)
    assert d['state'] == 'Nháp' and d['step'] == 0 and d['edit'] == 'all' and d['needs_signers'], d
    try:
        pp.sign(d['name'], d['modified'], dict(DEPARTMENT=people['DEPARTMENT']))
        raise AssertionError('sending needs a signer for every step')
    except frappe.ValidationError as exc:
        assert 'Giám đốc phê duyệt' in str(exc), exc
    d = pp.sign(d['name'], d['modified'], people)
    assert d['state'] == 'Chờ phụ trách bộ phận' and d['waiting_for'] == 'Ký Department', (d['state'], d['waiting_for'])
    alerts = frappe.get_all('Lotus Mobile Alert', filters={'user': people['DEPARTMENT'], 'document_name': d['name']}, pluck='url')
    assert alerts and alerts[0].startswith('/buying?proposal='), alerts
    assert frappe.get_all('Email Queue Recipient', filters={'recipient': people['DEPARTMENT']}), 'e-mail queued for the signer'
    todo = as_user(people['DEPARTMENT'], pp.proposals, company, 'todo')
    assert [r['name'] for r in todo['rows']] == [d['name']] and todo['counts']['Chờ tôi ký'] == 1 and todo['rows'][0]['stage'] == 'Đang ký', todo
    assert not as_user(people['PURCHASING'], pp.proposals, company, 'todo')['rows'], 'not their turn yet'
    try:
        as_user(people['PURCHASING'], pp.sign, d['name'], d['modified'])
        raise AssertionError('only the named signer may sign')
    except frappe.PermissionError:
        pass
    d = as_user(people['DEPARTMENT'], pp.sign, d['name'], d['modified'])
    assert d['state'] == 'Chờ kế toán / mua hàng', d['state']
    d = as_user(people['PURCHASING'], pp.detail, d['name'])
    assert d['edit'] == 'prices' and d['can_sign'], (d['edit'], d['can_sign'])
    priced = dict(values, items=[dict(r, rate=12000) for r in values['items']])
    d = as_user(people['PURCHASING'], pp.save_proposal, company, priced, d['name'], d['modified'])
    assert all(i['rate'] == 12000 for i in d['items']), d['items']
    if d['state'] != 'Trả lại':
        # Outside the purchase-flow company a price edit keeps the round and the signer returns it by hand;
        # inside it (policy of 07/11/2026) adding prices already returned the proposal for a new four-step round.
        d = as_user(people['PURCHASING'], pp.return_proposal, d['name'], d['modified'], 'Kiểm tra lại số lượng')
    assert d['state'] == 'Trả lại' and d['step'] == 0 and d['needs_signers'], d['state']
    assert [s['signed_at'] for s in d['signatures']] == ['', '', '', ''], 'a return restarts the chain'
    assert d['signers'] == people, 'the last signers prefill the next round'
    d = pp.sign(d['name'], d['modified'], d['signers'])
    for key in ('DEPARTMENT', 'PURCHASING', 'APPROVE'):
        d = as_user(people[key], pp.sign, d['name'], d['modified'])
    assert d['docstatus'] == 1 and d['state'] == 'Đã duyệt', (d['docstatus'], d['state'])
    assert all(s['image'] for s in d['signatures']), 'four signature snapshots'
    events = frappe.get_all('Lotus Signature Event', filters={'document_name': d['name']}, pluck='action', order_by='creation')
    assert events == ['PROPOSE', 'DEPARTMENT', 'RETURN', 'PROPOSE', 'DEPARTMENT', 'PURCHASING', 'APPROVE', 'ARCHIVED'], events
    owner_alerts = frappe.get_all('Lotus Mobile Alert', filters={'user': 'Administrator', 'document_name': d['name']}, pluck='title')
    assert any(t.startswith('Bị trả lại') for t in owner_alerts) and any(t.startswith('Đã ký đủ') for t in owner_alerts), owner_alerts
    from lotus_farm.purchasing import requests
    assert any(r['name'] == d['name'] for r in requests(company)), 'approved proposal waits for a purchase order'
    p = printer.build(d['name'])
    html = str(printer.pk.render('proposal.html', p))
    assert 'PHIẾU ĐỀ XUẤT MUA VẬT TƯ' in html and 'Giám đốc phê duyệt' in html and 'Ký Approve' in html and 'đồng chẵn' in html
    pdf = printer.pk.pdf(html, landscape=True)
    assert pdf.startswith(b'%PDF')
    report.update(proposal=d['name'], events=len(events), total=d['total'], pdf_bytes=len(pdf), inbox=signing.inbox()['total'])

    # ---- Spec 003, US2: bảng đề xuất ----
    from urllib.parse import parse_qs, urlparse
    from lotus_farm import signed_copy, warehouse_buying_lite as buying

    def denied(fn, *args):
        try:
            fn(*args)
        except (frappe.PermissionError, frappe.ValidationError) as exc:
            return str(exc) or type(exc).__name__
        return ''

    def approved(note):
        x = pp.save_proposal(company, dict(values, reason=note))
        x = pp.sign(x['name'], x['modified'], people)
        for key in ('DEPARTMENT', 'PURCHASING', 'APPROVE'):
            x = as_user(people[key], pp.sign, x['name'], x['modified'])
        assert x['docstatus'] == 1, x['state']
        return x

    # The signed copy is stored once, downloads return it, and every viewer sees the same stage.
    d = pp.detail(d['name'])
    copy = signed_copy.current(frappe.get_doc('Material Request', d['name']))
    assert copy and signed_copy.matches(copy) and signed_copy.pdf_bytes(copy).startswith(b'%PDF'), copy
    assert d['signed_copy'] and d['signed_copy']['pdf_sha256'] == copy['pdf_sha256'], d['signed_copy']
    assert d['stage'] == 'Chờ mua' and d['can_close'] and d['can_cancel'] and not d['closed'], (d['stage'], d['can_close'], d['can_cancel'])
    board = pp.proposals(company, 'all')
    assert next(r for r in board['rows'] if r['name'] == d['name'])['stage'] == 'Chờ mua', 'board row'
    assert pp.proposals(company, 'all', 'Chờ mua')['total'] == board['counts']['Chờ mua'] >= 1, board['counts']
    assert as_user(people['DEPARTMENT'], pp.detail, d['name'])['stage'] == 'Chờ mua', 'same stage for a signer without order rights'

    # A named signer needs no rights on proposals to read and print what they sign; an outsider is refused.
    lone = frappe.get_doc(dict(doctype='User', email='lotus-sign-lone@example.com', first_name='Ký Lone', send_welcome_email=0, enabled=1,
                               roles=[dict(role='Lotus Team Leader')])).insert(ignore_permissions=True).name
    frappe.get_doc(dict(doctype='Employee', first_name='Ký Lone', gender='Male', date_of_birth='1990-01-01', date_of_joining='2024-01-01',
                        company=company, status='Active', user_id=lone)).insert(ignore_permissions=True)
    outsider = frappe.get_doc(dict(doctype='User', email='lotus-sign-outsider@example.com', first_name='Ngoài', send_welcome_email=0,
                                   enabled=1)).insert(ignore_permissions=True).name
    w = pp.save_proposal(company, dict(values, reason='Quyền xem của người ký'))
    w = pp.sign(w['name'], w['modified'], dict(people, DEPARTMENT=lone))
    seen = as_user(lone, pp.detail, w['name'])
    assert seen['can_sign'] and seen['stage'] == 'Đang ký', (seen['can_sign'], seen['stage'])
    assert as_user(lone, printer.build, w['name']).signatures, 'the named signer opens the print'
    assert [r['name'] for r in as_user(lone, signing.inbox)['rows']] == [w['name']]
    assert denied(as_user, outsider, pp.detail, w['name']), 'an outsider cannot read the proposal'
    assert denied(as_user, outsider, printer.build, w['name']), 'nor print it'
    # Chuyển người ký keeps its reason in the history.
    assert 'lý do' in denied(pp.reassign_signer, w['name'], w['modified'], 'DEPARTMENT', people['DEPARTMENT'], '')
    w = pp.reassign_signer(w['name'], w['modified'], 'DEPARTMENT', people['DEPARTMENT'], 'Trưởng bộ phận nghỉ phép')
    assert w['waiting_for'] == 'Ký Department', w['waiting_for']
    assert not as_user(lone, signing.inbox)['rows'], 'the step left the first signer'

    # A draft order holds the proposal at Đang mua and blocks closing; without it the rest can be closed.
    supplier = frappe.db.get_value('Supplier', {'disabled': 0}, 'name')
    source = frappe.get_doc('Material Request', d['name'])
    first = source.items[0]
    order = buying.save_order(company, dict(supplier=supplier, warehouse=first.warehouse, expected_date=frappe.utils.add_days(frappe.utils.nowdate(), 3),
                                            items=[dict(item=first.item_code, qty=2, uom=first.uom, rate=12000, warehouse=first.warehouse,
                                                        material_request=source.name, material_request_item=first.name)]))
    assert pp.detail(d['name'])['stage'] == 'Đang mua', 'a draft order already counts'
    assert 'Còn đơn mua chưa duyệt' in denied(pp.close_remainder, d['name'], pp.detail(d['name'])['modified'], 'Không mua nữa')
    assert 'đã có đơn mua' in denied(pp.cancel_proposal, d['name'], pp.detail(d['name'])['modified'], 'Hủy thử')
    frappe.delete_doc('Purchase Order', order['name'], ignore_permissions=True)
    assert pp.detail(d['name'])['stage'] == 'Chờ mua'
    assert 'lý do' in denied(pp.close_remainder, d['name'], pp.detail(d['name'])['modified'], ' ')
    assert denied(as_user, outsider, pp.close_remainder, d['name'], pp.detail(d['name'])['modified'], 'Không có quyền')
    closed = pp.close_remainder(d['name'], pp.detail(d['name'])['modified'], 'Đủ hàng trong kho, không mua nữa')
    assert closed['closed'] and closed['stage'] == 'Đã xong' and closed['close_reason'].startswith('Đủ hàng') and not closed['can_close'], closed['stage']
    assert frappe.db.get_value('Material Request', d['name'], 'status') == 'Stopped'

    # Cancel an approved proposal that no order uses: reason required, stage Đã hủy, still on the board.
    c = approved('Đề xuất sẽ hủy')
    assert 'lý do' in denied(pp.cancel_proposal, c['name'], c['modified'], '')
    c = pp.cancel_proposal(c['name'], c['modified'], 'Đổi kế hoạch bón phân')
    assert c['docstatus'] == 2 and c['stage'] == 'Đã hủy' and c['cancel_reason'] == 'Đổi kế hoạch bón phân', (c['docstatus'], c['stage'])
    assert next(r for r in pp.proposals(company, 'all')['rows'] if r['name'] == c['name'])['stage'] == 'Đã hủy'
    query = {k: v[0] for k, v in parse_qs(urlparse(signing.verify_url(frappe.get_doc('Material Request', c['name']))).query).items()}
    assert 'hủy' in signing.verify(query['dt'], query['n'], query['r'], query['t'])['status'].lower(), 'QR of a cancelled proposal says so'

    # A proposal imported from Excel has no reason: signing asks for it and every signature covers it.
    imported = frappe.copy_doc(frappe.get_doc('Material Request', w['name']))
    imported.update(dict(lotus_request_note='', lotus_proposal_state='Nháp', docstatus=0))
    imported.insert()
    i = pp.detail(imported.name)
    assert i['needs_reason'] and i['stage'] == 'Nháp', (i['needs_reason'], i['stage'])
    assert 'lý do' in denied(pp.sign, i['name'], i['modified'], people)
    i = pp.sign(i['name'], i['modified'], people, 'Nhập từ danh mục vật tư tháng 11')
    assert i['reason'] == 'Nhập từ danh mục vật tư tháng 11' and i['stage'] == 'Đang ký' and not i['needs_reason'], (i['reason'], i['stage'])

    # The proposer deletes their own draft without an ERPNext delete right; kho nhận must be a usable warehouse of the company.
    draft = pp.save_proposal(company, dict(values, reason='Nháp để xóa'))
    assert draft['can_delete']
    pp.delete_proposal(draft['name'], draft['modified'])
    assert not frappe.db.exists('Material Request', draft['name'])
    group = frappe.db.get_value('Warehouse', {'company': company, 'is_group': 1}, 'name')
    assert 'Kho nhận' in denied(pp.save_proposal, company, dict(values, warehouse=group, items=[dict(values['items'][0], warehouse=group)]))
    report.update(us2=dict(closed=closed['name'], cancelled=c['name'], imported=i['name'], counts=pp.proposals(company, 'all')['counts']), rollback=True)
finally:
    frappe.set_user('Administrator')
    frappe.db.rollback()
print(json.dumps(report, ensure_ascii=False))
