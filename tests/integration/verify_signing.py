"""Named signers on a real site: stock document, purchase order and the timekeeping period, with the
Lotus Print signatures, the QR verification page and tamper detection. Everything rolls back."""
import hashlib
import json
import os
import uuid
from urllib.parse import parse_qs, urlparse

import frappe

frappe.init(site=os.environ.get('SITE', 'frontend'), sites_path='/home/frappe/frappe-bench/sites')
frappe.connect()
frappe.set_user('Administrator')
frappe.in_test = True
frappe.flags.in_test = True

from lotus_farm import digital_signature, hr_period as hp, purchasing, signing  # noqa: E402

company, month = 'Lotus Agritech', '2026-09'
report = {}
tag = uuid.uuid4().hex[:6]


def person(key, roles):
    email = 'lotus-sign-%s-%s@example.com' % (key.lower(), tag)
    user = frappe.get_doc(dict(doctype='User', email=email, first_name='Ký ' + key.title(), send_welcome_email=0, enabled=1,
                               roles=[dict(role=r) for r in roles])).insert(ignore_permissions=True)
    frappe.get_doc(dict(doctype='Employee', first_name='Ký ' + key.title(), gender='Male', date_of_birth='1990-01-01', date_of_joining='2026-10-01',
                        company=company, status='Active', user_id=user.name)).insert(ignore_permissions=True)
    return user.name


def as_user(user, fn, *args, **kwargs):
    frappe.set_user(user)
    try:
        return fn(*args, **kwargs)
    finally:
        frappe.set_user('Administrator')


def verify(doc):
    q = {k: v[0] for k, v in parse_qs(urlparse(signing.verify_url(doc)).query).items()}
    return signing.verify(q['dt'], q['n'], q['r'], q['t']), q


def denied(fn, *args):
    try:
        fn(*args)
    except (frappe.PermissionError, frappe.ValidationError):
        return True
    return False


try:
    admin_image = digital_signature.signature_image_bytes('Administrator')
    digital_signature.signature_image_bytes = lambda user: admin_image
    hand = person('Handover', ['Stock User'])
    keeper = person('Keeper', ['Lotus Warehouse Manager', 'Stock User'])
    approver = person('Approver', ['Lotus Purchase Approver', 'Purchase User', 'Purchase Manager', 'Stock User'])
    hr_user = person('Hr', ['HR User', 'HR Manager'])

    # Stock document: posted first, then signed by the person handing over and the storekeeper.
    entry = frappe.get_doc('Stock Entry', frappe.get_all('Stock Entry', filters={'docstatus': 1, 'company': company}, pluck='name', limit=1)[0])
    options = signing.candidates('stock_document', company)
    assert hand in [c['user'] for c in options['candidates']['HANDOVER']], 'handover accepts anyone with a login'
    assert hand not in [c['user'] for c in options['candidates']['STOREKEEPER']], 'storekeeper needs a stock role'
    info = signing.chain_status('Stock Entry', entry.name)
    assert info['can_start'] and not info['round'], info
    info = signing.request_signatures('Stock Entry', entry.name, dict(HANDOVER=hand, STOREKEEPER=keeper))
    assert info['current'] == 1 and info['steps'][1]['name'] == 'Ký Handover', info
    waiting = as_user(hand, signing.inbox)
    assert [r['name'] for r in waiting['rows']] == [entry.name] and waiting['total'] == 1, waiting
    row = waiting['rows'][0]
    assert row['step'] == 2 and row['step_title'] and row['creator'] == entry.owner and row['print_url'].startswith('/lotus/in-phieu?'), row
    assert row['mobile_url'].startswith('/warehouse?sign_dt=Stock+Entry&sign_dn='), row
    assert as_user(hand, signing.inbox_count) == dict(count=1)
    assert denied(as_user, keeper, signing.confirm, 'Stock Entry', entry.name), 'storekeeper must wait for their turn'
    as_user(hand, signing.confirm, 'Stock Entry', entry.name)
    result, query = verify(entry)
    assert result['valid'] and not result['ok'] and '2/3' in result['status'], result
    assert not signing.verify(query['dt'], query['n'], query['r'], 'x' * 40)['valid'], 'forged token'
    info = as_user(keeper, signing.confirm, 'Stock Entry', entry.name)
    assert info['done'], info
    result, _ = verify(entry)
    assert result['ok'] and result['status'] == 'Đã ký đủ', result
    frappe.db.set_value('Stock Entry Detail', entry.items[0].name, 'qty', entry.items[0].qty + 1)
    entry.reload()
    result, _ = verify(entry)
    assert 'thay đổi' in result['status'], 'a quantity changed after signing is reported'
    frappe.db.set_value('Stock Entry Detail', entry.items[0].name, 'qty', entry.items[0].qty - 1)
    # Spec 003: the completed round keeps one fixed PDF; the QR page compares the paper with it.
    from lotus_farm import signed_copy
    copy = signed_copy.latest('Stock Entry', entry.name)
    assert copy and copy['round'] == 1 and signed_copy.matches(copy), copy
    assert signed_copy.pdf_bytes(copy).startswith(b'%PDF')
    result, _ = verify(entry)
    assert result['archive'] and result['archive_match'], result
    signing.sign  # noqa: B018 (archive happens once per round)
    assert frappe.db.count('Lotus Signed Copy', {'document_type': 'Stock Entry', 'document_name': entry.name}) == 1
    audit = frappe.get_all('Lotus Signature Event', filters={'document_name': entry.name, 'action': 'STOREKEEPER'},
                           fields=['actor', 'roles', 'round', 'step_key', 'content_hash', 'ip', 'user_agent'])
    assert audit and audit[0].actor == keeper and 'Lotus Warehouse Manager' in audit[0].roles and audit[0].round == 1 \
        and audit[0].step_key == 'STOREKEEPER' and audit[0].content_hash, audit
    report['stock'] = entry.name

    # Ký nhiều: two documents in one confirmation; one changed since the list was opened and fails alone.
    first, second = [frappe.get_doc('Stock Entry', n) for n in frappe.get_all(
        'Stock Entry', filters={'docstatus': 1, 'company': company, 'name': ['!=', entry.name]}, pluck='name', limit=2)]
    for doc in (first, second):
        signing.request_signatures('Stock Entry', doc.name, dict(HANDOVER=hand, STOREKEEPER=keeper))
        doc.reload()
    batch = as_user(hand, signing.sign_many, [dict(doctype='Stock Entry', name=first.name, modified=str(first.modified)),
                                              dict(doctype='Stock Entry', name=second.name, modified='2000-01-01 00:00:00')])
    outcome = {r['name']: r['ok'] for r in batch['results']}
    assert outcome == {first.name: True, second.name: False} and batch['signed'] == 1, batch
    assert signing.status(first)['current'] == 2 and signing.status(second)['current'] == 1, 'only the unchanged one moved on'
    assert [r['name'] for r in as_user(hand, signing.inbox)['rows']] == [second.name]
    # Chuyển người ký needs a reason and stays in the history.
    assert denied(signing.reassign, 'Stock Entry', second.name, 'STOREKEEPER', approver), 'a reason is required'
    signing.reassign('Stock Entry', second.name, 'STOREKEEPER', other_keeper := person('Keeper2', ['Lotus Warehouse Manager', 'Stock User']),
                     'Thủ kho chính nghỉ phép')
    moved = frappe.get_all('Lotus Signature Event', filters={'document_name': second.name, 'action': 'REASSIGN'}, pluck='details')
    assert moved and 'nghỉ phép' in moved[0] and other_keeper in moved[0], moved
    report['bulk'] = batch['results']

    # Purchase order: sent to one named approver; another approver cannot act; approval completes the chain.
    # The copied order has no approved proposal behind its lines: treat it as an order from before the purchase
    # flow (order_guard lets those finish) while the approval itself still needs the named signature.
    frappe.conf.lotus_purchase_flow_since = '2099-01-01 00:00:00'
    # Any order of the company is a template (a copy of a local test site may hold only cancelled ones); a site with
    # no order at all gets a one-line order built from an enabled supplier, a stock item and a warehouse of the company.
    found = frappe.get_all('Purchase Order', filters={'company': company}, pluck='name', order_by='docstatus asc, modified desc', limit=1)
    if found:
        source = frappe.get_doc('Purchase Order', found[0])
    else:
        store = frappe.db.get_value('Warehouse', {'company': company, 'is_group': 0, 'disabled': 0}, 'name')
        goods = frappe.db.get_value('Item', {'is_stock_item': 1, 'is_purchase_item': 1, 'disabled': 0, 'has_batch_no': 0, 'has_serial_no': 0},
                                    ['name', 'stock_uom'], as_dict=True)
        source = frappe.get_doc(dict(doctype='Purchase Order', company=company, supplier=frappe.db.get_value('Supplier', {'disabled': 0}, 'name'),
                                     transaction_date=frappe.utils.nowdate(), schedule_date=frappe.utils.add_days(frappe.utils.nowdate(), 5),
                                     currency=frappe.get_cached_value('Company', company, 'default_currency'),
                                     items=[dict(item_code=goods.name, qty=2, rate=100000, uom=goods.stock_uom, conversion_factor=1,
                                                 warehouse=store, schedule_date=frappe.utils.add_days(frappe.utils.nowdate(), 5))]))
    def unlinked(order):
        # A copy keeps no proposal or quote line of its template: those quantities are ordered already, and the purchase
        # flow rightly refuses to order them twice (seen once the browser walk-through left orders on the site copy).
        for row in order.items:
            row.schedule_date = order.schedule_date
            for field in ('material_request', 'material_request_item', 'supplier_quotation', 'supplier_quotation_item'):
                if row.meta.has_field(field):
                    row.set(field, None)
        return order

    po = frappe.copy_doc(source)
    po.update(dict(docstatus=0, lotus_approval_status='Nháp', lotus_approved_by=None, lotus_approved_at=None, schedule_date=frappe.utils.add_days(frappe.utils.nowdate(), 5)))
    unlinked(po).insert()
    other = person('Other', ['Lotus Purchase Approver', 'Purchase User', 'Purchase Manager', 'Stock User'])
    purchasing.request_approval(po.name, str(po.modified), approver)
    po.reload()
    from lotus_farm.push_notifications import _recipients
    assert _recipients(po, 'pending') == [], 'role broadcast replaced by the named approver'
    assert as_user(approver, purchasing.can_approve, po) and not as_user(other, purchasing.can_approve, po), 'only the named approver'
    assert frappe.get_all('Lotus Mobile Alert', filters={'user': approver, 'document_name': po.name}), 'approver notified'
    as_user(approver, purchasing.approve_order, po.name, str(po.modified))
    po.reload()
    assert po.docstatus == 1 and signing.status(po)['done'], signing.status(po)
    copy = signed_copy.latest('Purchase Order', po.name)
    assert copy and signed_copy.matches(copy), 'the approved order keeps its signed PDF'
    approval = frappe.get_all('Lotus Signature Event', filters={'document_name': po.name, 'action': 'APPROVE'}, fields=['actor', 'roles'])
    assert approval and approval[0].actor == approver and 'Lotus Purchase Approver' in approval[0].roles, approval
    # Spec 003, FR-019: a submit that does not come from the named approver's signature is refused.
    po2 = frappe.copy_doc(source)
    po2.update(dict(docstatus=0, lotus_approval_status='Nháp', lotus_approved_by=None, lotus_approved_at=None, schedule_date=po.schedule_date))
    unlinked(po2).insert()
    purchasing.request_approval(po2.name, str(po2.modified), approver)
    po2.reload()
    assert denied(as_user, other, po2.submit), 'another approver cannot submit through the generic API'
    report['purchase_order'] = po.name

    # Timekeeping period: fill September, send to HR and the director, sign on the print page.
    begin = frappe.utils.getdate('2026-09-01')
    for blocker in hp.period_status(company, month)['blockers']:
        if blocker['code'] == 'missing_attendance':
            for gap in blocker['employees']:
                for day in gap['days']:
                    frappe.get_doc(dict(doctype='Attendance', company=company, employee=gap['name'], attendance_date=day, status='Present')).insert().submit()
    status = hp.period_status(company, month)
    assert not status['blockers'] and status['can_send'], status
    hp.send_period(company, month, dict(HR=hr_user, APPROVE=approver))
    period = hp._period(company, month)
    alert = frappe.get_all('Lotus Mobile Alert', filters={'user': hr_user, 'document_name': period.name}, pluck='url')
    assert alert and alert[0].startswith('/hr-mobile?sign_dt=Lotus+Timekeeping+Period&sign_dn='), alert
    from lotus_farm.www import lotus_payroll_print as printer
    assert denied(as_user, other, printer.build, company, month), 'people outside HR and the chain cannot open the sheet'
    page = as_user(approver, printer.build, company, month)
    assert not page.get('actions'), 'director waits for HR'
    page = as_user(hr_user, printer.build, company, month)
    assert page.actions[0]['method'] == 'lotus_farm.hr_period.sign_period', page.actions
    as_user(hr_user, hp.sign_period, company, month)
    page = as_user(approver, printer.build, company, month)
    assert 'khóa kỳ' in page.actions[0]['confirm'] and page.verify['qr'].startswith('data:image/png'), page.actions
    html = str(printer.pk.render('payroll.html', page))
    assert 'BẢNG LƯƠNG THÁNG 09/2026' in html and 'QR đối chiếu chứng từ' in html and 'Ký Hr' in html and 'lp-action' not in html
    as_user(approver, hp.sign_period, company, month)
    period.reload()
    assert period.status == 'Closed' and period.closed_by == approver, (period.status, period.closed_by)
    result, _ = verify(period)
    assert result['ok'], result
    pdf = printer.pk.pdf(str(printer.pk.render('payroll.html', as_user(approver, printer.build, company, month))), landscape=True)
    assert pdf.startswith(b'%PDF')
    if os.environ.get('LOTUS_DUMP_PDF'):
        open(os.environ['LOTUS_DUMP_PDF'], 'wb').write(pdf)
    report.update(period=period.name, payroll_pdf=len(pdf), steps=[s['state'] for s in result['steps']])

    # Payment voucher alerts (bug B1): a signer whose phone is subscribed to Mua hàng gets the alert inside
    # that app instead of a ValueError that undid the signing action; any alert failure is only logged.
    from lotus_farm import push_notifications as pn
    chief = person('Chief', ['Lotus Chief Accountant', 'Accounts Manager'])
    endpoint = 'https://fcm.googleapis.com/fcm/send/lotus-test-' + tag
    frappe.get_doc(dict(doctype=pn.DEVICE, user=chief, app='buying', endpoint=endpoint, endpoint_hash=hashlib.sha256(endpoint.encode()).hexdigest(),
                        p256dh='B' + 'x' * 86, auth='y' * 22, enabled=1, last_seen=frappe.utils.now_datetime())).insert(ignore_permissions=True)
    voucher = frappe._dict(doctype='Payment Entry', name='ACC-PAY-TEST-' + tag)
    signing._notify(voucher, 'payment_voucher', dict(assignee=chief), 'Đến lượt bạn ký: Kế toán trưởng')
    alerts = frappe.get_all('Lotus Mobile Alert', filters={'user': chief, 'document_name': voucher.name}, fields=['app', 'url'])
    assert [dict(a) for a in alerts] == [dict(app='buying', url='/buying?sign_dt=Payment+Entry&sign_dn=' + voucher.name)], alerts
    logged = frappe.db.count('Error Log', {'method': 'Lotus: thông báo ký'})
    original = pn._add_alert
    pn._add_alert = lambda *args, **kwargs: (_ for _ in ()).throw(ValueError('push broken'))
    try:
        signing._notify(voucher, 'payment_voucher', dict(assignee=chief), 'Đã ký đủ: ' + voucher.name)
    finally:
        pn._add_alert = original
    assert frappe.db.count('Error Log', {'method': 'Lotus: thông báo ký'}) == logged + 1, 'a failing alert is logged, never raised'
    report.update(voucher_alert=alerts[0]['url'], rollback=True)
finally:
    frappe.set_user('Administrator')
    frappe.db.rollback()
print(json.dumps(report, ensure_ascii=False))
