"""Stock documents in the shared Lotus Print layout, permission-checked (route /lotus/in-phieu).

Stock Entry (nhập / xuất / chuyển / tồn đầu), Stock Reconciliation and Purchase Receipt. Material
Request and Material Requirement are proposals and print through lotus_material_proposal_print.
Signatures come from the named signers of the document (lotus_farm.signing) with the QR to verify.
"""
from urllib.parse import urlencode

import frappe
from frappe.utils import flt, strip_html

from lotus_farm import print_kit as pk

no_cache = 1
TITLES = {'Material Receipt': 'PHIẾU NHẬP KHO', 'Material Issue': 'PHIẾU XUẤT KHO', 'Material Transfer': 'PHIẾU CHUYỂN KHO',
          'Opening Stock': 'PHIẾU TỒN ĐẦU KỲ'}
PROPOSALS = ('Material Request', 'Material Requirement')


def build(doctype, name):
    if doctype in ('Stock Entry', 'Stock Reconciliation'):
        from lotus_farm.warehouse import document
        info = document(doctype, name)
        title = TITLES.get(info['kind'], 'PHIẾU KIỂM KÊ KHO')
    elif doctype == 'Purchase Receipt':
        from lotus_farm.warehouse_planning import purchase_receipt
        info = purchase_receipt(name)
        title = 'PHIẾU NHẬN HÀNG'
    else:
        frappe.throw('Loại phiếu không hỗ trợ in.', frappe.PermissionError)
    doc = frappe.get_doc(doctype, name)
    doc.check_permission('read')
    doc.check_permission('print')
    rows = info['items']
    show_cost = doctype == 'Purchase Receipt' or info.get('kind') in ('Material Receipt', 'Opening Stock')
    extra = [dict(description=strip_html(r.get('description') or '').strip() or r.get('expense_account') or 'Chi phí phụ khác', amount=flt(r.get('amount')))
             for r in info.get('additional_costs', []) if flt(r.get('amount'))]
    goods = flt(info.get('basic_total')) or sum(flt(r.get('amount')) for r in rows)
    from lotus_farm import signing
    owner = signing._person(doc.owner)
    details = [dict(label='Người lập', value=owner)]
    if info.get('supplier'):
        details.append(dict(label='Nhà cung cấp', value=frappe.db.get_value('Supplier', info['supplier'], 'supplier_name') or info['supplier']))
    if info.get('receiver'):
        details.append(dict(label='Người nhận', value=info['receiver']))
    warehouses = sorted({w for r in rows for w in (r.get('source'), r.get('target'), r.get('warehouse')) if w})
    details.append(dict(label='Kho', value=', '.join(warehouses)))
    p = pk.page(info['company'], title, doc.name, doc.get('posting_date'), doc.docstatus, rows=rows, show_cost=show_cost,
                counting=doctype == 'Stock Reconciliation', same_unit=len({r.get('uom') for r in rows}) == 1,
                goods_total=goods, extra_costs=extra, grand_total=flt(info.get('incoming_total')) or goods + sum(c['amount'] for c in extra),
                info=details, info_columns=len(details), notes=strip_html(doc.get('remarks') or info.get('notes') or '').strip())
    p.signatures = signing.print_signatures(doc) or [pk.signature(s['title'], owner if i == 0 else '')
                                                      for i, s in enumerate(signing.rules.chain('stock_document')['steps'])]
    p.verify = signing.print_verification(doc)
    p.pdf_url = '/api/method/lotus_farm.www.lotus_stock_print.download_pdf?' + urlencode({'doctype': doctype, 'name': name})
    p.back_url, p.back_label = '/warehouse', 'Về Kho'
    return p


def get_context(context, doctype=None, name=None):
    doctype = doctype or frappe.form_dict.get('doctype')
    name = name or frappe.form_dict.get('name')
    if doctype in PROPOSALS:
        from lotus_farm.www.lotus_material_proposal_print import get_context as proposal_context
        return proposal_context(context, name=name, doctype=doctype)
    p = build(doctype, name)
    p.toolbar = True
    context.html = pk.render('stock.html', p)
    context.no_cache = 1


@frappe.whitelist()
def download_pdf(doctype, name):
    if doctype in PROPOSALS:
        from lotus_farm.www.lotus_material_proposal_print import download_pdf as proposal_pdf
        return proposal_pdf(name, doctype=doctype)
    pk.send_pdf(pk.render('stock.html', build(doctype, name)), name)
