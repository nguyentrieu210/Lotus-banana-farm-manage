"""Online purchase proposal on a real site: save → four signatures → submitted request → print. Rolls back."""
import json

import frappe

frappe.init(site='frontend', sites_path='/home/frappe/frappe-bench/sites')
frappe.connect()
frappe.set_user('Administrator')
frappe.in_test = True
from PIL import Image
from io import BytesIO

from lotus_farm import purchase_proposal as pp
from lotus_farm.digital_signature import signature_image_bytes
from lotus_farm.www import lotus_material_proposal_print as printer

report = {}
try:
    image = Image.open(BytesIO(signature_image_bytes('Administrator'))).convert('RGBA')
    histogram = image.getchannel('A').histogram()
    report['signature_transparent_share'] = round(histogram[0] / sum(histogram), 3)
    company = frappe.get_all('Company', pluck='name')[0]
    warehouse = frappe.get_all('Warehouse', filters={'company': company, 'is_group': 0}, pluck='name', limit=1)[0]
    items = frappe.get_all('Item', filters={'is_stock_item': 1, 'disabled': 0}, fields=['name', 'stock_uom'], limit=2)
    values = dict(reason='Chăm sóc vườn, buồng khu A + B + C', department='Đội khu A', warehouse=warehouse,
                  items=[dict(item_code=i.name, uom=i.stock_uom, qty=5 + n, rate=0, schedule_date=frappe.utils.add_days(frappe.utils.nowdate(), 2),
                              lotus_specification='cuộn 1 kg', lotus_purpose='Bón khu A', lotus_supplier_hint='') for n, i in enumerate(items)])
    d = pp.save_proposal(company, values)
    assert d['state'] == 'Nháp' and d['step'] == 0 and d['edit'] == 'all', d
    d = pp.sign(d['name'], d['modified'])
    assert d['state'] == 'Chờ phụ trách bộ phận', d['state']
    d = pp.sign(d['name'], d['modified'])
    assert d['state'] == 'Chờ kế toán / mua hàng' and d['edit'] == 'prices', d
    priced = dict(values, items=[dict(r, rate=12000) for r in values['items']])
    d = pp.save_proposal(company, priced, d['name'], d['modified'])
    assert all(i['rate'] == 12000 for i in d['items']), d['items']
    d = pp.return_proposal(d['name'], d['modified'], 'Kiểm tra lại số lượng')
    assert d['state'] == 'Trả lại' and d['step'] == 0, d['state']
    assert [s['signed_at'] for s in d['signatures']] == ['', '', '', ''], 'a return restarts the chain'
    for _ in range(4):
        d = pp.sign(d['name'], d['modified'])
    assert d['docstatus'] == 1 and d['state'] == 'Đã duyệt', (d['docstatus'], d['state'])
    assert all(s['image'] for s in d['signatures']), 'four signature snapshots'
    events = frappe.get_all('Lotus Signature Event', filters={'document_name': d['name']}, pluck='action', order_by='creation')
    assert events == ['PROPOSE', 'DEPARTMENT', 'RETURN', 'PROPOSE', 'DEPARTMENT', 'PURCHASING', 'APPROVE'], events
    from lotus_farm.purchasing import requests
    assert any(r['name'] == d['name'] for r in requests(company)), 'approved proposal waits for a purchase order'
    p = printer.build(d['name'])
    html = str(printer.pk.render('proposal.html', p))
    assert 'PHIẾU ĐỀ XUẤT MUA VẬT TƯ' in html and 'Giám đốc phê duyệt' in html and 'đồng chẵn' in html
    pdf = printer.pk.pdf(html, landscape=True)
    assert pdf.startswith(b'%PDF')
    report.update(proposal=d['name'], events=len(events), total=d['total'], pdf_bytes=len(pdf), rollback=True)
finally:
    frappe.set_user('Administrator')
    frappe.db.rollback()
print(json.dumps(report, ensure_ascii=False))
