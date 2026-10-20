"""Bảng lương tháng in Lotus Print (landscape), also the page where the named signers sign the period.

HR, or a person chosen to sign the period, may open it. While the period is being signed the frozen
snapshot is shown; the director's signature closes the period (lotus_farm.hr_period.sign_period).
"""
from urllib.parse import urlencode

import frappe

from lotus_farm import print_kit as pk

no_cache = 1


def build(company, month):
    from lotus_farm import hr_period, signing
    doc, sheet = hr_period.signed_sheet(company, month)
    year, number = str(month).split('-')
    p = pk.page(company, 'BẢNG LƯƠNG THÁNG ' + number + '/' + year, 'BL-' + month, None, landscape=True,
                rows=sheet['employees'], crews=sheet['crews'], totals=frappe._dict(sheet['totals']),
                standard_days=sheet['standard_days'], hours_base=sheet['hours_base'], info_columns=4,
                info=[dict(label='Kỳ lương', value=number + '/' + year), dict(label='Số người', value=str(sheet['totals']['employees'])),
                      dict(label='Tổng thu nhập', value=pk.money(sheet['totals']['gross'])),
                      dict(label='Đội khoán', value=pk.money(sheet['totals']['crew_amount']))])
    p.date = pk.vn_date(doc.closed_at) if doc and doc.status == 'Closed' else ''
    info = hr_period.approval(doc)
    p.status = 'Đã khóa kỳ' if doc and doc.status == 'Closed' else ('Đang trình ký' if info and not info['returned'] else 'Bản nháp')
    p.watermark = None if doc and doc.status == 'Closed' else 'BẢN NHÁP'
    titles = [s['title'] for s in signing.rules.chain('timekeeping_period')['steps']]
    p.signatures = (signing.print_signatures(doc) if doc else []) or [pk.signature(t) for t in titles]
    p.verify = signing.print_verification(doc) if info else None
    query = urlencode(dict(company=company, month=month))
    p.pdf_url = '/api/method/lotus_farm.www.lotus_payroll_print.download_pdf?' + query
    p.back_url, p.back_label = '/hr-mobile', 'Về Nhân sự'
    # The waiting signer signs right here; the page reloads with the new signature.
    if info and info['can_sign']:
        step = info['steps'][info['current']]['title']
        args = dict(company=company, month=month)
        p.actions = [dict(label='Ký duyệt: ' + step, method='lotus_farm.hr_period.sign_period', args=args, primary=True,
                          confirm='Ký ' + step + ' cho ' + p.title.lower() + '?' + (' Chữ ký này khóa kỳ công.' if info['current'] == len(titles) - 1 else ''))]
        if info['can_return']:
            p.actions.append(dict(label='Trả lại', method='lotus_farm.hr_period.return_period', args=args, reason=True))
    return p


def get_context(context):
    form = frappe.form_dict
    p = build(form.get('company'), form.get('month'))
    p.toolbar = True
    from frappe.sessions import get_csrf_token
    p.csrf = get_csrf_token()
    context.html = pk.render('payroll.html', p)
    context.no_cache = 1


@frappe.whitelist()
def download_pdf(company, month):
    p = build(company, month)
    p.actions = None
    pk.send_pdf(pk.render('payroll.html', p), 'bang-luong-' + str(month), landscape=True)
