"""Hóa đơn nhà cung cấp đã nhập, in Lotus Print (route /lotus/in-hoa-don): what was typed from the supplier's
invoice — ký hiệu, số, ngày, từng dòng với thuế suất, tổng in — and the list of original files kept as evidence.
It is the bookkeeping record of the invoice, not the invoice itself (spec 003, FR-055)."""
from urllib.parse import urlencode

import frappe
from frappe.utils import flt, strip_html

from lotus_farm import print_kit as pk

no_cache = 1


def build(name):
    from lotus_farm.finance import supplier_invoice
    info = supplier_invoice.detail(name)  # checks finance view rights and the company
    doc = frappe.get_doc('Purchase Invoice', name)
    supplier = frappe.db.get_value('Supplier', doc.supplier, ['supplier_name', 'tax_id'], as_dict=True) or {}
    number = ' · '.join(x for x in (info['series'], info['bill_no']) if x)
    p = pk.page(doc.company, 'BẢNG KÊ HÓA ĐƠN TRẢ HÀNG' if doc.is_return else 'BẢNG KÊ HÓA ĐƠN MUA HÀNG', doc.name, doc.posting_date, doc.docstatus,
                rows=[dict(item_name=r['item_name'], item_code=r['item'], qty=r['qty'], uom=r['uom'], rate=r['rate'], amount=r['amount'],
                           vat_code=r['vat_code'], note=' · '.join(x for x in (r['receipt'], r['variance_reason']) if x)) for r in info['items']],
                taxes=[dict(description=strip_html(t['description'] or '').strip(), amount=t['amount']) for t in info['taxes'] if flt(t['amount'])],
                net_total=info['net'], grand_total=info['amount'], printed_total=info['printed_total'], currency=doc.currency or 'VND',
                outstanding=info['outstanding_amount'], info_columns=3,
                info=[dict(label='Nhà cung cấp', value=supplier.get('supplier_name') or doc.supplier),
                      dict(label='Mã số thuế NCC', value=supplier.get('tax_id') or ''),
                      dict(label='Ký hiệu · Số hóa đơn', value=number),
                      dict(label='Ngày hóa đơn', value=pk.vn_date(doc.bill_date)),
                      dict(label='Hạn thanh toán', value=pk.vn_date(doc.due_date)),
                      dict(label='Mã cơ quan thuế', value=info['tax_code']),
                      dict(label='Tình trạng', value=info['status']),
                      dict(label='Phiếu nhận', value=', '.join(info['receipts'] + info['quick_receipts']))],
                files=[f['file_name'] for f in info['files']],
                notes=('Đã hủy: ' + info['cancel_reason']) if info['cancel_reason'] else '')
    p.status = info['status']
    p.signatures = [pk.signature('Người lập', frappe.utils.get_fullname(doc.owner)), pk.signature('Kế toán trưởng', '')]
    p.pdf_url = '/api/method/lotus_farm.www.lotus_invoice_print.download_pdf?' + urlencode({'name': name})
    p.back_url, p.back_label = '/lotus/mua-hang?' + urlencode({'buying_view': 'invoices'}), 'Về Mua hàng'
    return p


def get_context(context, name=None):
    name = name or frappe.form_dict.get('name')
    if frappe.session.user == 'Guest':
        frappe.throw('Vui lòng đăng nhập để in hóa đơn.', frappe.PermissionError)
    if not name or not frappe.db.exists('Purchase Invoice', name):
        frappe.throw('Không tìm thấy hóa đơn.', frappe.DoesNotExistError)
    p = build(name)
    p.toolbar = True
    context.html = pk.render('invoice.html', p)
    context.no_cache = 1


@frappe.whitelist()
def download_pdf(name):
    pk.send_pdf(pk.render('invoice.html', build(name)), name)
