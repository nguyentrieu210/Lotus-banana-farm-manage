"""Bảng công tháng in Lotus Print, landscape (route /lotus/in-cong). kind: staff | crew.

Signatures are those of the month's timekeeping period (Người lập, Phụ trách nhân sự, Giám đốc) once it
is sent for approval (lotus_farm.hr_period.send_period), with the QR to verify the paper copy.
"""
from urllib.parse import urlencode

import frappe

from lotus_farm import print_kit as pk

no_cache = 1
CODES = {'Present': 'X', 'Absent': 'V', 'Half Day': '½', 'Work From Home': 'TX', 'On Leave': 'P'}


def build(company, month, kind='staff', farm=None):
    from lotus_farm.timekeeping import _company, crew_monthly, monthly
    if kind not in ('staff', 'crew'):
        frappe.throw('Loại bảng công không hợp lệ.')
    if not frappe.has_permission('Attendance' if kind == 'staff' else 'Lotus Crew Attendance', 'print'):
        frappe.throw('Chưa có quyền in bảng công.', frappe.PermissionError)
    _company(company)
    data = monthly(company, month) if kind == 'staff' else crew_monthly(company, month, farm)
    if kind == 'staff':
        # Only people with a day recorded in the month, listed by tổ (or bộ phận) for each tổ to check and sign.
        teams = {t.name: t.team_name for t in frappe.get_all('Work Team', filters={'name': ['in', list({r.get('work_team') for r in data['rows'] if r.get('work_team')}) or ['']]},
                                                           fields=['name', 'team_name'])}
        for row in data['rows']:
            row['group'] = teams.get(row.get('work_team')) or (row.get('department') or '').rsplit(' - ', 1)[0] or 'Chưa xếp tổ'
        data['rows'] = sorted([r for r in data['rows'] if r['days']], key=lambda r: (r['group'] == 'Chưa xếp tổ', r['group'], r['employee_name'] or ''))
    holidays = data.get('holidays') or {}
    days = [dict(day=d, off=('CN' if holidays.get(str(d)) else 'L') if str(d) in holidays else '') for d in range(1, data['days'] + 1)]
    year, number = str(month).split('-')
    title = 'BẢNG CÔNG THÁNG ' + number + '/' + year
    p = pk.page(company, title, ('BC-' if kind == 'staff' else 'BCK-') + month, None, landscape=True, staff=kind == 'staff',
                rows=data['rows'], day_list=days, codes=CODES, info_columns=3,
                info=[dict(label='Kỳ công', value=number + '/' + year), dict(label='Phạm vi', value='Nhân sự chính thức' if kind == 'staff' else 'Đội khoán'),
                      dict(label='Trạng thái kỳ', value='Đã khóa' if data.get('period_closed') else 'Đang mở')])
    p.status = 'Đã khóa kỳ' if data.get('period_closed') else 'Kỳ đang mở'
    p.watermark = None if data.get('period_closed') else 'BẢN NHÁP'
    from lotus_farm import hr_period, signing
    period = hr_period._period(company, month)
    titles = [s['title'] for s in signing.rules.chain('timekeeping_period')['steps']]
    p.signatures = (signing.print_signatures(period) if period else []) or [pk.signature(t) for t in titles]
    p.verify = signing.print_verification(period) if period else None
    p.pdf_url = '/api/method/lotus_farm.www.lotus_timekeeping_print.download_pdf?' + urlencode(dict(company=company, month=month, kind=kind, **({'farm': farm} if farm else {})))
    p.back_url, p.back_label = '/lotus/cham-cong', 'Về chấm công'
    return p


def get_context(context, company=None, month=None, kind=None, farm=None):
    args = frappe.form_dict
    p = build(company or args.get('company'), month or args.get('month'), kind or args.get('kind') or 'staff', farm or args.get('farm'))
    p.toolbar = True
    context.html = pk.render('timesheet.html', p)
    context.no_cache = 1


@frappe.whitelist()
def download_pdf(company, month, kind='staff', farm=None):
    pk.send_pdf(pk.render('timesheet.html', build(company, month, kind, farm)), 'bang-cong-' + kind + '-' + str(month), landscape=True)
