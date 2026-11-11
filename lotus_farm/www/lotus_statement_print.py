"""Biên bản đối chiếu công nợ với một nhà cung cấp in Lotus Print (route /lotus/in-doi-chieu): số đầu kỳ, từng chứng
từ trong kỳ, số cuối kỳ — from lotus_farm.procurement_queries.supplier_statement (spec 003, FR-059)."""
from urllib.parse import urlencode

import frappe

from lotus_farm import print_kit as pk

no_cache = 1


def build(supplier, from_date=None, to_date=None):
    from lotus_farm.finance import setup
    from lotus_farm.procurement_queries import supplier_statement
    data = supplier_statement(setup.company(), supplier, from_date, to_date)  # checks finance rights
    tax_id = frappe.db.get_value('Supplier', supplier, 'tax_id') or ''
    p = pk.page(setup.company(), 'BIÊN BẢN ĐỐI CHIẾU CÔNG NỢ', '', data['to_date'], 1,
                rows=data['lines'], opening=data['opening'], closing=data['closing'], debit=data['debit'], credit=data['credit'], currency='VND',
                info=[dict(label='Nhà cung cấp', value=data['supplier_name']), dict(label='Mã số thuế', value=tax_id),
                      dict(label='Kỳ đối chiếu', value=pk.vn_date(data['from_date']) + ' – ' + pk.vn_date(data['to_date']))], info_columns=3)
    p.status = ''
    p.signatures = [pk.signature('Đại diện bên mua', '', hint='(Ký, ghi rõ họ tên, đóng dấu)'),
                    pk.signature('Đại diện nhà cung cấp', '', hint='(Ký, ghi rõ họ tên, đóng dấu)')]
    p.pdf_url = '/api/method/lotus_farm.www.lotus_statement_print.download_pdf?' + urlencode(
        dict(supplier=supplier, from_date=data['from_date'], to_date=data['to_date']))
    p.back_url, p.back_label = '/lotus/mua-hang?' + urlencode({'buying_view': 'payables'}), 'Về Mua hàng'
    return p


def get_context(context, supplier=None, from_date=None, to_date=None):
    form = frappe.form_dict
    if frappe.session.user == 'Guest':
        frappe.throw('Vui lòng đăng nhập để in biên bản đối chiếu.', frappe.PermissionError)
    supplier = supplier or form.get('supplier')
    if not supplier or not frappe.db.exists('Supplier', supplier):
        frappe.throw('Không tìm thấy nhà cung cấp.', frappe.DoesNotExistError)
    p = build(supplier, from_date or form.get('from_date') or form.get('from'), to_date or form.get('to_date') or form.get('to'))
    p.toolbar = True
    context.html = pk.render('statement.html', p)
    context.no_cache = 1


@frappe.whitelist()
def download_pdf(supplier, from_date=None, to_date=None):
    pk.send_pdf(pk.render('statement.html', build(supplier, from_date, to_date)), 'doi-chieu-' + supplier)
