"""Tài chính – Kế toán: month-end transfer of production costs (Thông tư 99). The month's balance of 621 / 622 / 623 /
627 on every farm / lot / crop cycle / work type is moved to 154 on the same dimensions (Nợ 154 / Có 62x), one
Journal Entry per month, so work in progress keeps the cost of each lot. Reversing it reopens the month's costs.
"""
import calendar

import frappe
from frappe.utils import flt

from lotus_farm.finance import posting, rules, setup

# Cost accounts whose balance moves to work in progress (by account number prefix).
COST_PREFIXES = ('621', '622', '623', '627')


def _bounds(month):
    year, mon = (int(x) for x in str(month).split('-')[:2])
    return '%04d-%02d-01' % (year, mon), '%04d-%02d-%02d' % (year, mon, calendar.monthrange(year, mon)[1])


def cost_accounts(company):
    return [a.name for a in frappe.get_all('Account', filters={'company': company, 'is_group': 0}, fields=['name', 'account_number'])
            if (a.account_number or '').startswith(COST_PREFIXES)]


def closing_vouchers(company):
    return frappe.get_all('Journal Entry', filters={'company': company, 'lotus_payment_kind': 'Closing', 'docstatus': 1}, pluck='name') \
        if frappe.get_meta('Journal Entry').has_field('lotus_payment_kind') else []


def _balances(company, month):
    start, end = _bounds(month)
    accounts = cost_accounts(company)
    if not accounts:
        return []
    dims = ', '.join(f for f in rules.DIM_FIELDS if frappe.get_meta('GL Entry').has_field(f))
    return frappe.db.sql("""select account, %s, sum(debit) - sum(credit) net from `tabGL Entry`
        where company=%%s and is_cancelled=0 and posting_date between %%s and %%s and account in %%s
        group by account, %s having abs(sum(debit) - sum(credit)) > 0.5""" % (dims, dims), (company, start, end, tuple(accounts)), as_dict=True)


@frappe.whitelist()
def preview(month):
    setup.require_view()
    company = setup.company()
    m = setup.mapping()
    lines = rules.closing_entry(_balances(company, month), m['production_cost'])
    done = posting.active('Lotus Finance Settings', setup.SETTINGS, 'Cost Closing', month)
    return dict(month=month, posting_date=_bounds(month)[1], lines=lines, total=sum(ln['debit'] for ln in lines if ln['account'] == m['production_cost']),
                posted=dict(voucher=done.voucher_name, posting=done.name) if done else None)


@frappe.whitelist(methods=['POST'])
def post(month):
    """Kết chuyển chi phí sản xuất tháng -> 154 (chief accountant), before the month is locked."""
    setup.require_chief()
    setup.require_enabled()
    company = setup.company()
    if posting.active('Lotus Finance Settings', setup.SETTINGS, 'Cost Closing', month):
        frappe.throw('Tháng %s đã kết chuyển. Đảo bút toán kết chuyển trước nếu cần làm lại.' % month)
    result = preview(month)
    if not result['lines']:
        frappe.throw('Tháng %s không có chi phí 621 / 622 / 627 để kết chuyển.' % month)
    errors = rules.check_entry(result['lines'])
    if errors:
        frappe.throw('<br>'.join(errors))
    setup.check_cutover(result['posting_date'])
    posting.check_open(company, result['posting_date'])
    from lotus_farm.finance.payroll import journal
    je = journal(company, result['posting_date'], result['lines'], 'Kết chuyển chi phí sản xuất tháng %s sang 154' % month, kind='Closing')
    je.submit()
    posting.record('Lotus Finance Settings', setup.SETTINGS, 'Cost Closing', je, amount=result['total'], source_hash=month, key_suffix=month)
    return dict(voucher=je.name, amount=result['total'])
