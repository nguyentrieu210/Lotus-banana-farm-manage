"""Tài chính – Kế toán: month-end entries (Thông tư 99).

1. Cost closing: the month's balance of 621 / 622 / 623 / 627 on every farm / lot / crop cycle / work type is moved to
   154 on the same dimensions (Nợ 154 / Có 62x), one Journal Entry per month, so work in progress keeps the cost of
   each lot. Reversing it reopens the month's costs.
2. Result closing, after the costing run: every income and expense account's balance of the month goes to 911 and
   911 to 4212 (lợi nhuận sau thuế chưa phân phối năm nay). Reports of revenue and cost leave these vouchers out.
Order of the month: payroll → cost closing → costing → result closing → lock.
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
        group by account, %s having abs(sum(debit) - sum(credit)) > 0.005""" % (dims, dims), (company, start, end, tuple(accounts)), as_dict=True)


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
    from lotus_farm.finance.assets import ensure_settled
    ensure_settled(month)
    company = setup.company()
    if posting.active('Lotus Finance Settings', setup.SETTINGS, 'Cost Closing', month):
        frappe.throw('Tháng %s đã kết chuyển. Đảo bút toán kết chuyển trước nếu cần làm lại.' % month)
    require_no_result(month)
    result = preview(month)
    if not result['lines']:
        frappe.throw('Tháng %s không có chi phí 621 / 622 / 627 để kết chuyển.' % month)
    errors = rules.check_entry(result['lines'])
    if errors:
        frappe.throw('<br>'.join(errors))
    setup.check_cutover(result['posting_date'])
    posting.check_open(company, result['posting_date'])
    from lotus_farm.finance.payroll import journal
    from lotus_farm.finance.assets import internal
    with internal(cost_closing=month):
        je = journal(company, result['posting_date'], result['lines'], 'Kết chuyển chi phí sản xuất tháng %s sang 154' % month, kind='Closing')
        je.submit()
    posting.record('Lotus Finance Settings', setup.SETTINGS, 'Cost Closing', je, amount=result['total'], source_hash=month, key_suffix=month)
    return dict(voucher=je.name, amount=result['total'])


# Result closing (911 -> 4212) ------------------------------------------------------------------------------

def result_vouchers(company):
    """Journal entries closing income / expense to 911 (left out of revenue, cost and B02 figures)."""
    return frappe.get_all('Journal Entry', filters={'company': company, 'lotus_payment_kind': 'Result', 'docstatus': 1}, pluck='name') \
        if frappe.get_meta('Journal Entry').has_field('lotus_payment_kind') else []


def require_no_result(month):
    done = posting.active('Lotus Finance Settings', setup.SETTINGS, 'Result Closing', month)
    if done:
        frappe.throw('Tháng %s đã kết chuyển kết quả kinh doanh (%s). Đảo bút toán đó trước.' % (month, done.voucher_name))


def _pl_balances(company, month):
    start, end = _bounds(month)
    excluded = tuple(result_vouchers(company)) or ('',)
    return frappe.db.sql("""select g.account, a.account_number, a.root_type, sum(g.debit) - sum(g.credit) net from `tabGL Entry` g
        join tabAccount a on a.name=g.account where g.company=%s and g.is_cancelled=0 and g.posting_date between %s and %s
        and a.root_type in ('Income', 'Expense') and g.voucher_no not in %s and g.voucher_type != 'Period Closing Voucher'
        group by g.account, a.account_number, a.root_type having abs(sum(g.debit) - sum(g.credit)) > 0.005 order by a.account_number""",
                         (company, start, end, excluded), as_dict=True)


@frappe.whitelist()
def result_preview(month):
    setup.require_view()
    company = setup.company()
    m = setup.mapping()
    balances = _pl_balances(company, month)
    issues = []
    leftover = [b for b in balances if (b.account_number or '').startswith(COST_PREFIXES)]
    if leftover:
        issues.append('Còn chi phí %s chưa kết chuyển sang 154: bấm "Kết chuyển CP" trước.' % ', '.join(sorted({b.account_number for b in leftover})))
    start, end = _bounds(month)
    from lotus_farm.finance.costing import _receipts
    harvested = frappe.db.count('Stock Entry', {'name': ['in', _receipts(company) or ['']], 'posting_date': ['between', [start, end]]})
    if harvested and not frappe.db.exists('Lotus Costing Run', {'company': company, 'month': month, 'state': 'Posted'}):
        issues.append('Tháng có nhập kho chuối thu hoạch nhưng chưa tính giá thành: bấm "Giá thành" trước.')
    lines, profit = rules.result_entry([dict(account=b.account, net=b.net) for b in balances], m.get('income_summary'), m.get('retained_earnings'))
    if not m.get('income_summary') or not m.get('retained_earnings'):
        issues.append('Chưa chọn tài khoản 911 và 4212 ở Thiết lập.')
    done = posting.active('Lotus Finance Settings', setup.SETTINGS, 'Result Closing', month)
    income = -sum(flt(b.net) for b in balances if b.root_type == 'Income')
    expense = sum(flt(b.net) for b in balances if b.root_type == 'Expense')
    return dict(month=month, posting_date=end, lines=lines, profit=profit, income=round(income), expense=round(expense), issues=issues,
                posted=dict(voucher=done.voucher_name, posting=done.name) if done else None)


@frappe.whitelist(methods=['POST'])
def result_post(month):
    """Kết chuyển doanh thu, chi phí tháng sang 911 và 911 sang 4212 (chief accountant)."""
    setup.require_chief()
    setup.require_enabled()
    from lotus_farm.finance.assets import ensure_settled, internal
    ensure_settled(month)
    company = setup.company()
    require_no_result(month)
    result = result_preview(month)
    if result['issues']:
        frappe.throw('<br>'.join(result['issues']))
    if not result['lines']:
        frappe.throw('Tháng %s không có doanh thu, chi phí để kết chuyển.' % month)
    errors = rules.check_entry(result['lines'])
    if errors:
        frappe.throw('<br>'.join(errors))
    setup.check_cutover(result['posting_date'])
    posting.check_open(company, result['posting_date'])
    from lotus_farm.finance.payroll import journal
    with internal(result_closing=month):
        je = journal(company, result['posting_date'], result['lines'], 'Kết chuyển kết quả kinh doanh tháng %s (911 → 4212)' % month, kind='Result')
        je.submit()
    posting.record('Lotus Finance Settings', setup.SETTINGS, 'Result Closing', je, amount=abs(result['profit']), source_hash=month, key_suffix=month)
    return dict(voucher=je.name, profit=result['profit'])
