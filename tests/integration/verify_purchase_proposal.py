"""Online purchase proposal on a real site with named signers: pick three people from HR → each signs in
turn, only on their turn → return restarts → director's signature submits → print. Rolls back."""
import json

import frappe

frappe.init(site='frontend', sites_path='/home/frappe/frappe-bench/sites')
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
    assert [r['name'] for r in as_user(people['DEPARTMENT'], pp.proposals, company, 'todo')] == [d['name']]
    assert not as_user(people['PURCHASING'], pp.proposals, company, 'todo'), 'not their turn yet'
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
    assert events == ['PROPOSE', 'DEPARTMENT', 'RETURN', 'PROPOSE', 'DEPARTMENT', 'PURCHASING', 'APPROVE'], events
    owner_alerts = frappe.get_all('Lotus Mobile Alert', filters={'user': 'Administrator', 'document_name': d['name']}, pluck='title')
    assert any(t.startswith('Bị trả lại') for t in owner_alerts) and any(t.startswith('Đã ký đủ') for t in owner_alerts), owner_alerts
    from lotus_farm.purchasing import requests
    assert any(r['name'] == d['name'] for r in requests(company)), 'approved proposal waits for a purchase order'
    p = printer.build(d['name'])
    html = str(printer.pk.render('proposal.html', p))
    assert 'PHIẾU ĐỀ XUẤT MUA VẬT TƯ' in html and 'Giám đốc phê duyệt' in html and 'Ký Approve' in html and 'đồng chẵn' in html
    pdf = printer.pk.pdf(html, landscape=True)
    assert pdf.startswith(b'%PDF')
    report.update(proposal=d['name'], events=len(events), total=d['total'], pdf_bytes=len(pdf), inbox=len(signing.inbox()), rollback=True)
finally:
    frappe.set_user('Administrator')
    frappe.db.rollback()
print(json.dumps(report, ensure_ascii=False))
