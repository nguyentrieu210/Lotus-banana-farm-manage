"""Đơn mua hàng in Lotus Print (Vietnamese), used for the approval archive and every PO download.

lotus_farm.digital_signature.archive_approved_purchase_pdf renders this at approval with the approver's
image and the archive QR (SHA-256 of the stored PDF); before approval the QR of the named-signer chain.
"""
import frappe
from frappe.utils import flt, strip_html

from lotus_farm import print_kit as pk

MODES = {'Order': 'Đặt hàng', 'Buy Now': 'Mua ngay', 'Quote': 'Báo giá'}


def build(doc, approver=None, approver_image=None, approved_at=None, verify=None):
    doc.check_permission('read')
    from lotus_farm import signing
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
    if doc.get('lotus_initials_by'):
        p.signatures.insert(len(p.signatures) - 1, pk.signature('Người kiểm tra (ký nháy)', signing._person(doc.lotus_initials_by),
                                                               _initials_image(doc), doc.get('lotus_initials_at')))
    if approver:
        p.signatures[-1] = pk.signature(p.signatures[-1]['title'], signing._person(approver), approver_image, approved_at)
    p.verify = verify or signing.print_verification(doc)
    return p


def _initials_image(doc):
    """The private initials snapshot stored on this order when it was checked, as a data URI."""
    url = doc.get('lotus_initials_snapshot')
    rows = frappe.get_all('File', filters={'attached_to_doctype': 'Purchase Order', 'attached_to_name': doc.name, 'attached_to_field': 'lotus_initials_snapshot',
                                           'file_url': url, 'is_private': 1}, pluck='name', limit_page_length=1) if url else []
    if not rows:
        return None
    from base64 import b64encode
    return 'data:image/png;base64,' + b64encode(frappe.get_doc('File', rows[0]).get_content(encodings=[])).decode('ascii')


def html(doc, **kwargs):
    return pk.render('purchase_order.html', build(doc, **kwargs))
