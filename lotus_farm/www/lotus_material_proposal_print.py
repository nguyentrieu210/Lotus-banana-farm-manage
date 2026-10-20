"""Phiếu đề xuất mua / cấp vật tư in the shared Lotus Print layout, columns as on the farm's Excel forms.

A Material Request is a proposal, not an approved Purchase Order or a Stock Entry. Only fields stored on
the request, or live stock visibly marked as such, are shown. Online proposals carry four signatures
(lotus_farm.purchase_proposal); older requests show only the final approval when one was signed.
"""
import json
from base64 import b64encode
from urllib.parse import urlencode

import frappe
from frappe.utils import flt, getdate, strip_html

from lotus_farm import print_kit as pk

no_cache = 1
ISSUE_SIGNERS = ('Người đề xuất', 'Phụ trách bộ phận', 'Thủ kho', 'Giám đốc NT / Người phê duyệt')
BUY_SIGNERS = ('Người đề xuất', 'Phụ trách bộ phận', 'Phòng Kế toán / Mua hàng', 'Giám đốc phê duyệt')


def _user_name(user):
    return frappe.db.get_value('User', user, 'full_name') or user or ''


def _approval(doc):
    """Final approval image from an immutable signature event attached to this document (older requests)."""
    events = frappe.get_all('Lotus Signature Event', filters={'document_type': doc.doctype, 'document_name': doc.name, 'action': 'APPROVE'},
                            fields=['actor', 'signed_at', 'details'], order_by='signed_at desc', limit_page_length=1)
    if not events:
        return None
    event = events[0]
    try:
        file_name = (json.loads(event.details or '{}') or {}).get('signature_file')
    except (TypeError, ValueError):
        file_name = None
    image = ''
    if file_name and frappe.db.exists('File', file_name):
        file = frappe.get_doc('File', file_name)
        if file.is_private and file.attached_to_doctype == doc.doctype and file.attached_to_name == doc.name:
            image = 'data:image/png;base64,' + b64encode(file.get_content(encodings=[])).decode('ascii')
    return dict(name=_user_name(event.actor), image=image, signed_at=event.signed_at)


def _place_date(company, value):
    """'Đồng Nai, ngày 20 tháng 10 năm 2026' from the province at the end of the printed project name."""
    project = frappe.get_cached_value('Company', company, 'lotus_print_project') or ''
    place = project.rsplit('-', 1)[-1].strip().title() if '-' in project else ''
    day = getdate(value)
    return (place + ', ' if place else '') + 'ngày %02d tháng %02d năm %d' % (day.day, day.month, day.year)


def _requirement(name):
    """Lotus planning requirement: proposed issue quantities, never proof of stock issue."""
    doc = frappe.get_doc('Material Requirement', name)
    doc.check_permission('read')
    doc.check_permission('print')
    frappe.get_doc('Farm', doc.farm).check_permission('read')
    plan = frappe.db.get_value('Daily Work Plan Line', doc.work_plan_line, ['work_type', 'planned_qty', 'uom'], as_dict=True) if doc.work_plan_line else None
    work = frappe.db.get_value('Work Type', plan.work_type, 'work_name') if plan and plan.work_type else ''
    block = frappe.db.get_value('Farm Block', doc.farm_block, 'block_code') if doc.farm_block else ''
    when = getdate(doc.get('posting_date') or doc.creation)
    rows = []
    for line in doc.lines:
        item = frappe.get_doc('Item', line.item)
        item.check_permission('read')
        rows.append(frappe._dict(item_name=item.item_name or line.item, specification=strip_html(item.get('description') or '').strip(),
                                 item_code=line.item, uom=pk.unit(line.uom), stock=None, qty=flt(line.required_qty), norm=flt(line.norm_qty),
                                 issued_qty=None, needed_date=pk.vn_date(when), area=block,
                                 scale=(pk.number(plan.planned_qty) + ' ' + (plan.uom or '')) if plan else '', purpose=work, notes=''))
    reason = ('Vật tư cho công việc: ' + work) if work else 'Vật tư theo kế hoạch sản xuất'
    return doc, rows, reason, 'Chưa xác định kho cấp trên phiếu nhu cầu', when


def _request_rows(doc):
    rows, total, priced = [], 0, True
    for line in doc.items:
        item = frappe.get_doc('Item', line.item_code)
        item.check_permission('read')
        stock = None
        if line.warehouse:
            frappe.get_doc('Warehouse', line.warehouse).check_permission('read')
            raw = frappe.db.get_value('Bin', {'item_code': line.item_code, 'warehouse': line.warehouse}, 'actual_qty')
            stock = None if raw is None else flt(raw) / (flt(line.conversion_factor) or 1)
        price = flt(line.get('rate')) or None
        amount = flt(line.qty) * price if price else None
        priced = priced and price is not None
        total += amount or 0
        description = strip_html(line.get('description') or '').strip()
        rows.append(frappe._dict(
            item_name=line.item_name or item.item_name, item_code=line.item_code,
            # ERPNext copies the item name into description; only a real spec is printed.
            specification=line.get('lotus_specification') or (description if description != (line.item_name or item.item_name) else ''),
            uom=pk.unit(line.uom), stock=stock, qty=flt(line.qty), norm=line.get('lotus_norm_qty'), issued_qty=None,
            needed_date=pk.vn_date(line.schedule_date or doc.schedule_date), area=line.get('lotus_usage_area') or '', scale='',
            purpose=line.get('lotus_purpose') or '', notes=line.get('lotus_notes') or '', supplier=line.get('lotus_supplier_hint') or '',
            price=price, amount=amount))
    return rows, total, bool(rows) and priced


def build(name, doctype='Material Request'):
    if frappe.session.user == 'Guest':
        frappe.throw('Vui lòng đăng nhập để in phiếu đề xuất vật tư.', frappe.PermissionError)
    if not name:
        frappe.throw('Cần chọn số phiếu đề xuất vật tư.')
    if doctype == 'Material Requirement':
        doc, rows, reason, warehouse, when = _requirement(name)
        purchase, total, priced = False, 0, False
        state = 'Đã lập nhu cầu' if doc.docstatus == 1 else 'Nháp'
    elif doctype == 'Material Request':
        doc = frappe.get_doc('Material Request', name)
        doc.check_permission('read')
        doc.check_permission('print')
        if doc.material_request_type not in ('Purchase', 'Material Issue'):
            frappe.throw('Chỉ in phiếu đề xuất mua hoặc cấp vật tư.', frappe.PermissionError)
        purchase = doc.material_request_type == 'Purchase'
        when = getdate(doc.get('transaction_date') or doc.creation)
        reason = strip_html(doc.get('lotus_request_note') or doc.get('remarks') or '').strip()
        warehouse = ', '.join(sorted({r.warehouse for r in doc.items if r.warehouse}))
        rows, total, priced = _request_rows(doc)
        state = 'Đã duyệt' if doc.docstatus == 1 else (doc.get('lotus_proposal_state') or pk.status_label(doc.docstatus))
    else:
        frappe.throw('Chỉ hỗ trợ phiếu đề xuất vật tư.', frappe.PermissionError)

    proposer = _user_name(doc.owner)
    department = doc.get('lotus_department') or frappe.db.get_value('Employee', {'user_id': doc.owner, 'status': 'Active'}, 'department') or ''
    p = pk.page(doc.company, 'PHIẾU ĐỀ XUẤT MUA VẬT TƯ' if purchase else 'PHIẾU ĐỀ XUẤT CẤP VẬT TƯ', doc.name, when, landscape=True,
                purchase=purchase, rows=rows, total=total, all_priced=priced, place_date=_place_date(doc.company, when), info_columns=4,
                info=[dict(label='1. Họ tên người đề xuất', value=proposer), dict(label='2. Bộ phận', value=department),
                      dict(label='3. Lý do đề xuất mua' if purchase else '3. Kho đề xuất cấp', value=reason if purchase else warehouse),
                      dict(label='Kho nhận' if purchase else 'Lý do', value=warehouse if purchase else reason)])
    p.status = state
    p.watermark = None if state in ('Đã duyệt', 'Đã lập nhu cầu') else ('ĐÃ HỦY' if doc.docstatus == 2 else 'CHƯA DUYỆT')
    if purchase and doc.get('lotus_proposal_state'):
        from lotus_farm.purchase_proposal import _signatures
        signed, _ = _signatures(doc)
        p.signatures = [pk.signature(s['title'], s['name'] or (proposer if i == 0 else ''), s['image'] or None, s['signed_at'] or None)
                        for i, s in enumerate(signed)]
    else:
        titles = BUY_SIGNERS if purchase else ISSUE_SIGNERS
        p.signatures = [pk.signature(t, proposer if i == 0 else '') for i, t in enumerate(titles)]
        approval = _approval(doc) if doc.docstatus == 1 else None
        if approval:
            p.signatures[-1] = pk.signature(titles[-1], approval['name'], approval['image'] or None, approval['signed_at'])
    query = {'name': doc.name} if doctype == 'Material Request' else {'doctype': doctype, 'name': doc.name}
    p.pdf_url = '/api/method/lotus_farm.www.lotus_material_proposal_print.download_pdf?' + urlencode(query)
    p.back_url, p.back_label = ('/buying', 'Về Mua hàng') if purchase else ('/warehouse', 'Về Kho')
    return p


def get_context(context, name=None, doctype=None):
    p = build(name or frappe.form_dict.get('name'), doctype or frappe.form_dict.get('doctype') or 'Material Request')
    p.toolbar = True
    context.html = pk.render('proposal.html', p)
    context.purchase = p.purchase
    context.no_cache = 1


@frappe.whitelist()
def download_pdf(name, doctype=None):
    p = build(name, doctype or 'Material Request')
    pk.send_pdf(pk.render('proposal.html', p), ('de-xuat-mua-' if p.purchase else 'de-xuat-cap-') + name, landscape=True)
