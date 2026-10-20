"""Named signers on a real site: stock document, purchase order and the timekeeping period, with the
Lotus Print signatures, the QR verification page and tamper detection. Everything rolls back."""
import json
import os
import uuid
from urllib.parse import parse_qs, urlparse

import frappe

frappe.init(site='frontend', sites_path='/home/frappe/frappe-bench/sites')
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
    frappe.get_doc(dict(doctype='Employee', first_name='Ký ' + key.title(), gender='Male', date_of_birth='1990-01-01', date_of_joining='2024-01-01',
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
    assert [r['name'] for r in as_user(hand, signing.inbox)] == [entry.name]
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
    report['stock'] = entry.name

    # Purchase order: sent to one named approver; another approver cannot act; approval completes the chain.
    source = frappe.get_doc('Purchase Order', frappe.get_all('Purchase Order', filters={'company': company, 'docstatus': 1}, pluck='name', limit=1)[0])
    po = frappe.copy_doc(source)
    po.update(dict(docstatus=0, lotus_approval_status='Nháp', lotus_approved_by=None, lotus_approved_at=None, schedule_date=frappe.utils.add_days(frappe.utils.nowdate(), 5)))
    for row in po.items:
        row.schedule_date = po.schedule_date
    po.insert()
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
    assert alert and alert[0].startswith('/lotus/in-luong?'), alert
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
    report.update(period=period.name, payroll_pdf=len(pdf), steps=[s['state'] for s in result['steps']], rollback=True)
finally:
    frappe.set_user('Administrator')
    frappe.db.rollback()
print(json.dumps(report, ensure_ascii=False))
