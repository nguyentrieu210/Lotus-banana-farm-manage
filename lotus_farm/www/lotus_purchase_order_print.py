"""Đơn mua hàng in Lotus Print (Vietnamese): web page /lotus/in-don-mua, every PO download and the signed copy.

Signatures come from the named signers of the order (lotus_farm.signing) with the QR to verify; once the
director has signed, lotus_farm.signed_copy keeps the PDF of that moment and downloads return it.
"""
from urllib.parse import urlencode

import frappe
from frappe.utils import flt, strip_html

from lotus_farm import print_kit as pk

no_cache = 1
MODES = {'Order': 'Đặt hàng', 'Buy Now': 'Mua ngay', 'Quote': 'Báo giá'}


def build(doc):
    from lotus_farm import signing
    if not signing.can_view(doc=doc):
        frappe.throw('Không có quyền xem đơn mua này.', frappe.PermissionError)
    supplier = frappe.db.get_value('Supplier', doc.supplier, ['supplier_name', 'mobile_no'], as_dict=True) or {}
    warehouses = sorted({r.warehouse for r in doc.items if r.warehouse})
    requester = doc.get('lotus_requested_by') or doc.owner
    status = 'Đã hủy' if doc.docstatus == 2 else 'Đã duyệt' if doc.docstatus == 1 else (doc.get('lotus_approval_status') or 'Nháp')
    p = pk.page(doc.company, 'ĐƠN MUA HÀNG', doc.name, doc.transaction_date, doc.docstatus,
                rows=[dict(item_code=r.item_code, item_name=r.item_name or r.item_code, qty=flt(r.qty), uom=r.uom, rate=flt(r.rate),
                           amount=flt(r.amount), schedule_date=r.schedule_date) for r in doc.items],
                taxes=[dict(description=strip_html(t.description or '').strip() or t.account_head, amount=flt(t.tax_amount))
                       for t in doc.get('taxes') or [] if flt(t.tax_amount)],
                net_total=flt(doc.net_total or doc.total), discount=flt(doc.get('discount_amount')), grand_total=flt(doc.grand_total),
                currency=doc.currency or 'VND', info_columns=3,
                info=[dict(label='Nhà cung cấp', value=supplier.get('supplier_name') or doc.supplier),
                      dict(label='Điện thoại NCC', value=supplier.get('mobile_no') or ''),
                      dict(label='Ngày cần giao', value=pk.vn_date(doc.schedule_date)),
                      dict(label='Kho nhận', value=', '.join(warehouses)),
                      dict(label='Hình thức', value=MODES.get(doc.get('lotus_purchase_mode'), doc.get('lotus_purchase_mode') or '')),
                      dict(label='Người lập đơn', value=signing._person(requester))],
                notes=strip_html(doc.get('lotus_delivery_note') or doc.get('terms') or '').strip())
    p.status = status
    named = signing.print_signatures(doc)
    if named:
        p.signatures = named
    else:
        p.signatures = [pk.signature('Người lập đơn', signing._person(requester)),
                        pk.signature('Người duyệt mua', signing._person(doc.get('lotus_approved_by')) if doc.get('lotus_approved_by') else '')]
    p.initials = signing.print_initials(doc)
    p.verify = signing.print_verification(doc)
    p.pdf_url = '/api/method/lotus_farm.digital_signature.download_purchase_pdf?' + urlencode({'name': doc.name})
    p.back_url, p.back_label = '/lotus/mua-hang?' + urlencode({'buying_view': 'orders'}), 'Về Mua hàng'
    return p


def html(doc):
    return pk.render('purchase_order.html', build(doc))


def get_context(context, name=None):
    name = name or frappe.form_dict.get('name')
    if frappe.session.user == 'Guest':
        frappe.throw('Vui lòng đăng nhập để in đơn mua.', frappe.PermissionError)
    if not name or not frappe.db.exists('Purchase Order', name):
        frappe.throw('Không tìm thấy đơn mua.', frappe.DoesNotExistError)
    p = build(frappe.get_doc('Purchase Order', name))
    p.toolbar = True
    context.html = pk.render('purchase_order.html', p)
    context.no_cache = 1
