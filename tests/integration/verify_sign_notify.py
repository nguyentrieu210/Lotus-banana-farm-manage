"""Bug B1 on a real site, rolled back: a payment voucher alert to a signer with a phone subscribed to Mua hàng
used to raise ValueError and undo the signing action. Now it lands in that app; any alert failure is only logged.
Run in a bench container from sites/:  SITE=<site> ../env/bin/python ../apps/lotus_farm/tests/integration/verify_sign_notify.py"""
import hashlib
import json
import os
import uuid

import frappe

frappe.init(site=os.environ.get('SITE', 'frontend'), sites_path='/home/frappe/frappe-bench/sites')
frappe.connect()
frappe.set_user('Administrator')
frappe.flags.in_test = True
frappe.flags.mute_emails = True

from lotus_farm import push_notifications as pn, signing  # noqa: E402

tag = uuid.uuid4().hex[:6]
report = {}
try:
    email = 'lotus-notify-chief-%s@example.com' % tag
    chief = frappe.get_doc(dict(doctype='User', email=email, first_name='Kế toán trưởng', send_welcome_email=0, enabled=1,
                                roles=[dict(role='Accounts Manager')])).insert(ignore_permissions=True).name
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
    # A signer without any phone still finds the alert in the Mua hàng bell (it used to be dropped for vouchers).
    other = frappe.get_doc(dict(doctype='User', email='lotus-notify-dir-%s@example.com' % tag, first_name='Giám đốc', send_welcome_email=0,
                                enabled=1)).insert(ignore_permissions=True).name
    signing._notify(voucher, 'payment_voucher', dict(assignee=other), 'Đến lượt bạn ký: Giám đốc duyệt chi')
    assert frappe.get_all('Lotus Mobile Alert', filters={'user': other, 'document_name': voucher.name, 'app': 'buying'}), 'kept in the bell'
    report.update(voucher_alert=alerts[0]['url'], ok=True)
finally:
    frappe.db.rollback()
print(json.dumps(report, ensure_ascii=False))
