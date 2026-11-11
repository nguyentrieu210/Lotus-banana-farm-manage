"""Phiếu chi / giấy đề nghị chi trả nhà cung cấp in Lotus Print (route /lotus/in-phieu-chi), also the layout of the
signed copy kept when the payment_voucher chain completes (spec 003, US6, R19).

Tiền mặt: PHIẾU CHI with boxes for Thủ quỹ and Người nhận tiền (signed on paper when the cash is handed over).
Chuyển khoản: GIẤY ĐỀ NGHỊ CHI with the transfer reference. Signatures of the chain and the QR come from signing."""
from urllib.parse import urlencode

import frappe
from frappe.utils import flt

from lotus_farm import print_kit as pk

no_cache = 1


def build(doc):
    from lotus_farm import signing
    from lotus_farm.finance import payments
    if not signing.can_view(doc=doc):
        frappe.throw('Không có quyền xem phiếu chi này.', frappe.PermissionError)
    info = payments._voucher_info(doc)
    cash = info['mode'] == 'cash'
    rows = []
    for r in doc.get('references') or []:
        bill = frappe.db.get_value(r.reference_doctype, r.reference_name, ['bill_no', 'bill_date'], as_dict=True) if r.reference_doctype == 'Purchase Invoice' else None
        rows.append(dict(label=('Hóa đơn ' + (bill.bill_no or r.reference_name)) if bill else 'Tạm ứng theo đơn mua ' + r.reference_name,
                         name=r.reference_name, date=pk.vn_date(bill.bill_date) if bill and bill.bill_date else '', amount=flt(r.allocated_amount)))
    if info.get('unallocated'):
        rows.append(dict(label='Tạm ứng cho nhà cung cấp (chưa gắn hóa đơn)', name='', date='', amount=flt(info['unallocated'])))
    if not rows:
        rows = [dict(label=l['label'], name='', date='', amount=abs(flt(l['amount']))) for l in info['lines'] if flt(l['amount']) > 0] or \
               [dict(label=info['kind'], name='', date='', amount=flt(info['amount']))]
    supplier = frappe.db.get_value('Supplier', doc.get('party'), ['tax_id'], as_dict=True) if doc.get('party_type') == 'Supplier' else None
    details = [dict(label='Người nhận tiền' if cash else 'Đơn vị thụ hưởng', value=info['party_name']),
               dict(label='Mã số thuế', value=(supplier or {}).get('tax_id') or ''),
               dict(label='Hình thức chi', value='Tiền mặt' if cash else 'Chuyển khoản'),
               dict(label='Tài khoản chi', value=info.get('money') or ''),
               dict(label='Số tham chiếu', value=info.get('reference') or ''),
               dict(label='Lý do chi', value=info.get('remark') or info['kind'])]
    p = pk.page(doc.company, 'PHIẾU CHI' if cash else 'GIẤY ĐỀ NGHỊ CHI', doc.name, doc.posting_date, doc.docstatus,
                rows=rows, grand_total=flt(info['amount']), currency='VND', info=details, info_columns=3, cash=cash)
    named = signing.print_signatures(doc)
    p.signatures = named or [pk.signature(s['title'], '') for s in signing.rules.chain('payment_voucher')['steps']]
    if cash:
        p.signatures = [*p.signatures, pk.signature('Thủ quỹ', ''), pk.signature('Người nhận tiền', '')]
    p.initials = signing.print_initials(doc)
    p.verify = signing.print_verification(doc)
    p.pdf_url = '/api/method/lotus_farm.www.lotus_payment_print.download_pdf?' + urlencode({'doctype': doc.doctype, 'name': doc.name})
    p.back_url, p.back_label = '/lotus/mua-hang?' + urlencode({'buying_view': 'payments'}), 'Về Mua hàng'
    return p


def html(doc):
    return pk.render('payment.html', build(doc))


def _doc(doctype, name):
    if doctype not in ('Payment Entry', 'Journal Entry') or not name or not frappe.db.exists(doctype, name):
        frappe.throw('Không tìm thấy phiếu chi.', frappe.DoesNotExistError)
    return frappe.get_doc(doctype, name)


def get_context(context, doctype=None, name=None):
    if frappe.session.user == 'Guest':
        frappe.throw('Vui lòng đăng nhập để in phiếu chi.', frappe.PermissionError)
    p = build(_doc(doctype or frappe.form_dict.get('doctype') or 'Payment Entry', name or frappe.form_dict.get('name')))
    p.toolbar = True
    context.html = pk.render('payment.html', p)
    context.no_cache = 1


@frappe.whitelist()
def download_pdf(name, doctype='Payment Entry'):
    from lotus_farm import signed_copy, signing
    doc = _doc(doctype, name)
    copy = signed_copy.current(doc)
    if copy and signing.can_view(doc=doc):
        return signed_copy.respond(copy, name)
    pk.send_pdf(html(doc), name)
