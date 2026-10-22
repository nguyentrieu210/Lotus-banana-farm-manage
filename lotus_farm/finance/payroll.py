"""Tài chính – Kế toán: an approved month of pay (Lotus Timekeeping Period, Closed, with its frozen snapshot)
posted as one Journal Entry. Each person's cost (gross + employer insurance) is split over the lots they
worked that month by actual workdays (Daily Work Result labour, else Labor Allocation); people without lot
work go to the administrative expense account. Paying the month is a signed cash/bank voucher.
"""
import calendar
import json

import frappe
from frappe.utils import flt, getdate

from lotus_farm import payroll_rules
from lotus_farm.finance import posting, rules, setup

PERIOD = 'Lotus Timekeeping Period'


def _month_end(month):
    year, mon = (int(x) for x in str(month).split('-')[:2])
    return '%04d-%02d-%02d' % (year, mon, calendar.monthrange(year, mon)[1])


def _work_rows(company, month):
    """Actual workdays per employee and lot in the month; Labor Allocation for people with no actual rows."""
    start, end = month + '-01', _month_end(month)
    actual = frappe.db.sql("""select l.employee, sum(l.actual_workdays) workdays, r.farm lotus_farm, r.farm_block lotus_farm_block,
            r.crop_cycle lotus_crop_cycle, pl.work_type lotus_work_type
        from `tabWork Actual Labor` l join `tabDaily Work Result` r on r.name=l.parent and l.parenttype='Daily Work Result'
        left join `tabDaily Work Plan Line` pl on pl.name=r.work_plan_line
        where r.docstatus=1 and r.company=%s and r.posting_date between %s and %s and ifnull(l.employee,'')!=''
        group by l.employee, r.farm, r.farm_block, r.crop_cycle, pl.work_type""", (company, start, end), as_dict=True)
    seen = {r.employee for r in actual}
    planned = frappe.db.sql("""select a.employee, sum(a.allocated_workdays) workdays, a.farm lotus_farm, a.farm_block lotus_farm_block,
            a.crop_cycle lotus_crop_cycle, pl.work_type lotus_work_type
        from `tabLabor Allocation` a left join `tabDaily Work Plan Line` pl on pl.name=a.work_plan_line
        where a.docstatus=1 and a.company=%s and a.posting_date between %s and %s and ifnull(a.employee,'')!=''
        group by a.employee, a.farm, a.farm_block, a.crop_cycle, pl.work_type""", (company, start, end), as_dict=True)
    return [dict(r) for r in actual] + [dict(r) for r in planned if r.employee not in seen]


def _period(name):
    doc = frappe.get_doc(PERIOD, name)
    if doc.status != 'Closed' or not doc.snapshot:
        frappe.throw('Bảng lương %s chưa ký đủ (chưa đóng kỳ) nên chưa ghi sổ được.' % doc.month)
    return doc


def build(name):
    doc = _period(name)
    snapshot = json.loads(doc.snapshot)
    m = setup.mapping()
    work = _work_rows(doc.company, doc.month)
    employees = [r.get('employee') for r in rules.snapshot_people(snapshot)]
    farms = {e.name: e.lotus_farm for e in frappe.get_all('Employee', filters={'name': ['in', employees or ['']]}, fields=['name', 'lotus_farm'])} \
        if frappe.get_meta('Employee').has_field('lotus_farm') else {}
    teams = [c.get('work_team') for c in snapshot.get('crews') or []]
    crew_farms = {t.name: t.farm for t in frappe.get_all('Work Team', filters={'name': ['in', teams or ['']]}, fields=['name', 'farm'])}
    lines, issues = rules.payroll_entry(snapshot, rules.shares_from_work(work), m, payroll_rules.EMPLOYEE_INSURANCE,
                                        payroll_rules.EMPLOYER_INSURANCE, crew_farms=crew_farms, employee_farms=farms)
    direct = {r['employee'] for r in work}
    indirect = [r.get('employee') for r in rules.snapshot_people(snapshot) if r.get('employee') not in direct and (r.get('gross') or 0)]
    totals = snapshot.get('totals') or {}
    return doc, dict(period=doc.name, month=doc.month, company=doc.company, posting_date=_month_end(doc.month), source_hash=doc.snapshot_hash,
                     lines=lines, issues=issues, people=len(rules.snapshot_people(snapshot)), indirect=indirect, crews=len(snapshot.get('crews') or []),
                     totals=dict(gross=sum(int(round(r.get('gross') or 0)) for r in rules.snapshot_people(snapshot)),
                                 net=sum(int(round(r.get('net') or 0)) for r in rules.snapshot_people(snapshot)),
                                 employer_insurance=sum(int(round(r.get('employer_insurance') or 0)) for r in rules.snapshot_people(snapshot)),
                                 crews=sum(int(round(c.get('amount') or 0)) for c in snapshot.get('crews') or []), sheet=totals),
                     posted=_posted(doc.name))


def _posted(name):
    p = posting.active(PERIOD, name, 'Payroll')
    return dict(posting=p.name, voucher=p.voucher_name, at=str(p.posted_at)) if p else None


@frappe.whitelist()
def preview(period):
    setup.require_view()
    _, result = build(period)
    return result


@frappe.whitelist(methods=['POST'])
def post(period, source_hash):
    setup.require_post()
    setup.require_enabled()
    doc, result = build(period)
    if source_hash != doc.snapshot_hash:
        frappe.throw('Bảng lương đã thay đổi sau khi bạn xem trước. Xem trước lại rồi ghi sổ.')
    if result['issues']:
        frappe.throw('Chưa ghi sổ được:<br>' + '<br>'.join(result['issues']))
    setup.check_cutover(result['posting_date'])
    posting.guard(PERIOD, doc.name, 'Payroll')
    posting.check_open(doc.company, result['posting_date'])
    je = journal(doc.company, result['posting_date'], result['lines'], 'Lương tháng %s (bảng công %s)' % (doc.month, doc.name))
    je.submit()
    total = sum(ln['debit'] for ln in result['lines'])
    posting.record(PERIOD, doc.name, 'Payroll', je, amount=total, source_hash=doc.snapshot_hash)
    return dict(voucher=je.name, amount=total)


def journal(company, posting_date, lines, remark, kind=None):
    cost_center = frappe.get_cached_value('Company', company, 'cost_center')
    accounts = []
    for ln in lines:
        row = dict(account=ln['account'], debit_in_account_currency=ln['debit'], credit_in_account_currency=ln['credit'], cost_center=cost_center,
                   user_remark=ln.get('note') or None)
        row.update({f: ln.get(f) for f in rules.DIM_FIELDS if ln.get(f)})
        accounts.append(row)
    je = frappe.get_doc(dict(doctype='Journal Entry', voucher_type='Journal Entry', company=company, posting_date=posting_date, user_remark=remark,
                             accounts=accounts, **({'lotus_payment_kind': kind} if kind else {})))
    je.flags.ignore_permissions = True
    je.insert()
    return je


def assert_reopenable(period):
    """hr_period.reopen_period: a posted month must be reversed in the ledger first."""
    p = posting.active(PERIOD, period, 'Payroll')
    if p:
        frappe.throw('Bảng lương tháng này đã ghi sổ kế toán (%s). Kế toán trưởng đảo bút toán trước khi mở lại kỳ.' % p.voucher_name)
    pay = posting.active(PERIOD, period, 'Salary Payment')
    if pay:
        frappe.throw('Lương tháng này đã có phiếu chi (%s). Hủy phiếu chi trước khi mở lại kỳ.' % pay.voucher_name)


@frappe.whitelist(methods=['POST'])
def prepare_salary_payment(period, mode, posting_date, signers, reference_no=None):
    """Draft voucher paying the month's net pay (Nợ phải trả NLĐ / Có tiền), sent for signatures."""
    setup.require_post()
    setup.require_enabled()
    doc = _period(period)
    if not posting.active(PERIOD, doc.name, 'Payroll'):
        frappe.throw('Ghi sổ bảng lương tháng %s trước khi chi lương.' % doc.month)
    posting.guard(PERIOD, doc.name, 'Salary Payment')
    snapshot = json.loads(doc.snapshot)
    net = sum(int(round(r.get('net') or 0)) for r in rules.snapshot_people(snapshot))
    m = setup.mapping()
    money = m['bank'] if mode == 'bank' else m['cash']
    setup.check_cutover(posting_date)
    posting.check_open(doc.company, posting_date)
    je = journal(doc.company, posting_date, [rules.line(m['payable_employee'], debit=net, note='Chi lương'), rules.line(money, credit=net, note='Chi lương')],
                 'Chi lương tháng %s' % doc.month, kind='Salary')
    if mode == 'bank':
        je.db_set(dict(cheque_no=reference_no or doc.name, cheque_date=posting_date))
    posting.record(PERIOD, doc.name, 'Salary Payment', je, amount=net, source_hash=doc.snapshot_hash)
    from lotus_farm.finance.payments import start_signing
    return start_signing(je, signers)
