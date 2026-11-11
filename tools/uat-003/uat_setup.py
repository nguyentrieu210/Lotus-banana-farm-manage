"""UAT accounts on the live-site copy mua.test (test stack only): one login per role, an active employee of the
company, a drawn signature and initials. Prints {key: [email, password]} as JSON on the last line."""
import json
import secrets
from base64 import b64encode
from io import BytesIO

import frappe
from PIL import Image, ImageDraw

frappe.init(site='mua.test', sites_path='/home/frappe/frappe-bench/sites')
frappe.connect()
frappe.set_user('Administrator')
assert frappe.local.site == 'mua.test'
from frappe.utils.password import update_password
from lotus_farm import digital_signature
from lotus_farm.finance import setup

company = setup.company()
ROLES = {
    'proposer': ('Tổ trưởng UAT', ['Lotus Team Leader', 'Lotus Purchase Requester']),
    'head': ('Trưởng bộ phận UAT', ['Lotus Field Supervisor']),
    'head2': ('Trưởng bộ phận thay UAT', ['Lotus Field Supervisor']),
    'buyer': ('Mua hàng UAT', ['Lotus Purchasing Buyer', 'Lotus Purchase Requester']),
    'accountant': ('Kế toán UAT', ['Lotus Accountant']),
    'chief': ('Kế toán trưởng UAT', ['Lotus Chief Accountant']),
    'director': ('Giám đốc UAT', ['Lotus Purchase Approver']),
    'director2': ('Phó giám đốc UAT', ['Lotus Purchase Approver']),
    'keeper': ('Thủ kho UAT', ['Lotus Warehouse Receiver', 'Lotus Warehouse Manager', 'Lotus Warehouse Operator']),
    'keeper2': ('Thủ kho phụ UAT', ['Lotus Warehouse Receiver', 'Lotus Warehouse Operator']),
}
missing = sorted({r for _, roles in ROLES.values() for r in roles if not frappe.db.exists('Role', r)})
assert not missing, missing


def drawing(text, width=480, height=150, seed=1):
    image = Image.new('RGB', (width, height), 'white')
    pen = ImageDraw.Draw(image)
    x = 20
    for i, ch in enumerate(text):
        y = 70 + (i * seed * 7) % 40 - 20
        pen.line([(x, 100), (x + 12, y), (x + 24, 105)], fill='black', width=4)
        x += 22
        if x > width - 40:
            break
    pen.line([(20, 120), (x, 110)], fill='black', width=3)
    # Random strokes: every drawing is different, so no two users share one stored file.
    for _ in range(6):
        pen.line([(secrets.randbelow(width), secrets.randbelow(height)), (secrets.randbelow(width), secrets.randbelow(height))], fill='black', width=3)
    out = BytesIO()
    image.save(out, format='PNG')
    return 'data:image/png;base64,' + b64encode(out.getvalue()).decode('ascii')


gender = frappe.db.get_value('Gender', {}, 'name') or 'Male'
result = {}
for key, (name, roles) in ROLES.items():
    email = 'uat-%s@lotus-uat.invalid' % key
    if not frappe.db.exists('User', email):
        frappe.get_doc(dict(doctype='User', email=email, first_name=name, send_welcome_email=0, enabled=1, user_type='System User',
                            roles=[dict(role=r) for r in roles])).insert(ignore_permissions=True)
    if not frappe.db.exists('Employee', {'user_id': email}):
        frappe.get_doc(dict(doctype='Employee', first_name=name, gender=gender, date_of_birth='1990-01-01', date_of_joining='2026-10-01',
                            company=company, status='Active', user_id=email)).insert(ignore_permissions=True)
    password = secrets.token_urlsafe(14)
    update_password(email, password)
    frappe.set_user(email)
    digital_signature.save_my_signature_image(drawing(name + key, seed=len(key) + sum(map(ord, key)) % 11))
    digital_signature.save_my_initials_image(drawing(key, width=200, height=90, seed=sum(map(ord, key)) % 13 + 1))
    frappe.set_user('Administrator')
    result[key] = [email, password]
admin = secrets.token_urlsafe(14)
update_password('Administrator', admin)
result['admin'] = ['Administrator', admin]
frappe.db.commit()
print(json.dumps(dict(company=company, users=result)))
frappe.destroy()
