"""Tài chính – Kế toán: an approved month of pay (Lotus Timekeeping Period, Closed, with its frozen snapshot)
posted as one Journal Entry. Each person's cost (gross + employer insurance + union fee) is split over the lots they
worked that month by actual workdays (Daily Work Result labour, else Labor Allocation); people without lot
work go to the administrative expense account. Paying the month is a signed cash/bank voucher for the net pay less
the advances of the month; advances and the payment of insurance / union fee / income tax are signed vouchers too.
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
                                 pit=sum(int(round(r.get('pit') or 0)) for r in rules.snapshot_people(snapshot)),
                                 union_fee=sum(int(round(r.get('union_fee') or 0)) for r in rules.snapshot_people(snapshot)),
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


def _advances(company, month, docstatus=1):
    """Salary advances of a pay month per employee (submitted vouchers; docstatus=0 for the ones still being signed)."""
    if not frappe.get_meta('Journal Entry').has_field('lotus_pay_month'):
        return {}
    out = {}
    for r in frappe.get_all('Journal Entry', filters={'company': company, 'docstatus': docstatus, 'lotus_payment_kind': 'Advance', 'lotus_pay_month': month},
                            fields=['lotus_employee', 'total_debit']):
        out[r.lotus_employee] = out.get(r.lotus_employee, 0) + int(round(flt(r.total_debit)))
    return out


def pay_list(doc):
    """What each person receives for the month: net pay of the frozen sheet less the advances already paid."""
    people = rules.snapshot_people(json.loads(doc.snapshot or '{}'))
    advances = _advances(doc.company, doc.month)
    meta = frappe.get_meta('Employee')
    bank_fields = [f for f in ('bank_name', 'bank_ac_no', 'salary_mode') if meta.has_field(f)]
    banks = {e.name: e for e in frappe.get_all('Employee', filters={'name': ['in', [p.get('employee') for p in people] or ['']]},
                                                fields=['name'] + bank_fields)}
    rows = []
    for p in people:
        net = int(round(p.get('net') or 0))
        advance = advances.get(p.get('employee'), 0)
        if not net and not advance:
            continue
        bank = banks.get(p.get('employee')) or frappe._dict()
        rows.append(dict(employee=p.get('employee'), employee_name=p.get('employee_name'), net=net, advance=advance, to_pay=net - advance,
                         bank_name=bank.get('bank_name') or '', bank_ac_no=bank.get('bank_ac_no') or '', salary_mode=bank.get('salary_mode') or ''))
    return rows


@frappe.whitelist()
def salary_list(period):
    setup.require_view()
    doc = _period(period)
    rows = pay_list(doc)
    return dict(period=doc.name, month=doc.month, rows=rows, total=sum(max(0, r['to_pay']) for r in rows),
                issues=['%s: tạm ứng %s lớn hơn thực lĩnh %s' % (r['employee_name'], r['advance'], r['net']) for r in rows if r['to_pay'] < 0])


@frappe.whitelist()
def export_salary_transfer(period):
    """Bank transfer list (Excel) of the month: one row per person paid by bank."""
    setup.require_view()
    doc = _period(period)
    from io import BytesIO
    from openpyxl import Workbook
    from openpyxl.styles import Font
    book = Workbook()
    ws = book.active
    ws.title = 'Chuyển khoản lương'
    ws.append(['Danh sách chi lương tháng ' + doc.month + ' (thực lĩnh trừ tạm ứng)'])
    ws.append(['STT', 'Mã NV', 'Họ tên', 'Ngân hàng', 'Số tài khoản', 'Thực lĩnh', 'Đã tạm ứng', 'Số tiền chuyển', 'Nội dung'])
    for cell in ws[2]:
        cell.font = Font(bold=True)
    for i, r in enumerate([r for r in pay_list(doc) if r['to_pay'] > 0], start=1):
        account = str(r['bank_ac_no'] or '')
        ws.append([i, r['employee'], r['employee_name'], r['bank_name'], "'" + account if account[:1] in ('=', '+', '-', '@') else account,
                   r['net'], r['advance'], r['to_pay'], 'Luong thang %s %s' % (doc.month[5:] + '/' + doc.month[:4], r['employee'])])
    output = BytesIO()
    book.save(output)
    frappe.local.response.filename = 'chuyen-khoan-luong-' + doc.month + '.xlsx'
    frappe.local.response.filecontent = output.getvalue()
    frappe.local.response.type = 'download'


@frappe.whitelist(methods=['POST'])
def prepare_advance(employee, amount, month, mode, posting_date, signers, reference_no=None):
    """Salary advance (Nợ 334 / Có tiền) for a pay month, signed like every payment voucher; the month's salary payment
    pays the rest."""
    setup.require_post()
    setup.require_enabled()
    company = setup.company()
    amount = int(round(flt(amount)))
    if amount <= 0:
        frappe.throw('Nhập số tiền tạm ứng.')
    if not frappe.db.exists('Employee', {'name': employee, 'company': company}):
        frappe.throw('Nhân viên không thuộc công ty.')
    month = str(month or '')[:7]
    if len(month) != 7 or month[4] != '-':
        frappe.throw('Chọn tháng lương được tạm ứng.')
    period = frappe.db.get_value(PERIOD, {'company': company, 'month': month})
    if period and posting.active(PERIOD, period, 'Salary Payment'):
        frappe.throw('Lương tháng %s đã có phiếu chi, không tạm ứng thêm vào tháng này.' % month)
    m = setup.mapping()
    money = m['bank'] if mode == 'bank' else m['cash']
    setup.check_cutover(posting_date)
    posting.check_open(company, posting_date)
    name = frappe.db.get_value('Employee', employee, 'employee_name')
    je = journal(company, posting_date, [rules.line(m['payable_employee'], debit=amount, note='Tạm ứng lương ' + name),
                                         rules.line(money, credit=amount, note='Tạm ứng lương ' + name)],
                 'Tạm ứng lương tháng %s: %s' % (month, name), kind='Advance')
    je.db_set(dict(lotus_employee=employee, lotus_pay_month=month, **({'cheque_no': reference_no, 'cheque_date': posting_date} if mode == 'bank' and reference_no else {})))
    posting.record('Employee', employee, 'Salary Advance', je, amount=amount, source_hash=month, key_suffix=je.name)
    from lotus_farm.finance.payments import start_signing
    return start_signing(je, signers)


STATUTORY_KEYS = (('social_insurance', 'BHXH'), ('health_insurance', 'BHYT'), ('unemployment_insurance', 'BHTN'),
                  ('union_fee', 'Kinh phí công đoàn'), ('pit_payable', 'Thuế TNCN'))


@frappe.whitelist()
def statutory_balances():
    """What is owed to the social insurance agency, the union and the tax office (credit balances), less vouchers being signed."""
    setup.require_view()
    company = setup.company()
    m = setup.mapping()
    drafts = {}
    for a in frappe.db.sql("""select a.account, sum(a.debit) amount from `tabJournal Entry Account` a join `tabJournal Entry` j on j.name=a.parent
            where j.docstatus=0 and j.company=%s and j.lotus_payment_kind='Statutory' group by a.account""", company, as_dict=True) \
            if frappe.get_meta('Journal Entry').has_field('lotus_payment_kind') else []:
        drafts[a.account] = flt(a.amount)
    rows = []
    for key, label in STATUTORY_KEYS:
        account = m.get(key)
        if not account:
            continue
        owed = -flt(frappe.db.sql("""select sum(debit-credit) from `tabGL Entry` where company=%s and account=%s and is_cancelled=0""",
                                  (company, account))[0][0])
        rows.append(dict(key=key, label=label, account=account, owed=round(owed), pending=round(drafts.get(account, 0)),
                         payable=max(0, round(owed - drafts.get(account, 0)))))
    return rows


@frappe.whitelist(methods=['POST'])
def prepare_statutory(lines, mode, posting_date, signers, reference_no=None, remark=None):
    """Payment of insurance / union fee / personal income tax (Nợ 3383, 3384, 3386, 3382, 3335 / Có tiền), signed."""
    setup.require_post()
    setup.require_enabled()
    company = setup.company()
    m = setup.mapping()
    owed = {r['key']: r for r in statutory_balances()}
    chosen = [(l.get('key'), int(round(flt(l.get('amount'))))) for l in (frappe.parse_json(lines) if isinstance(lines, str) else lines or [])]
    chosen = [(k, a) for k, a in chosen if a > 0]
    if not chosen:
        frappe.throw('Nhập số tiền nộp.')
    for key, amount in chosen:
        if key not in owed:
            frappe.throw('Khoản nộp không hợp lệ.')
        if amount > owed[key]['payable'] + 0.5:
            frappe.throw('%s chỉ còn phải nộp %s.' % (owed[key]['label'], format(owed[key]['payable'], ',').replace(',', '.')))
    if mode == 'bank' and not reference_no:
        frappe.throw('Chuyển khoản cần số ủy nhiệm chi.')
    money = m['bank'] if mode == 'bank' else m['cash']
    setup.check_cutover(posting_date)
    posting.check_open(company, posting_date)
    total = sum(a for _, a in chosen)
    labels = dict(STATUTORY_KEYS)
    je = journal(company, posting_date, [rules.line(m[k], debit=a, note='Nộp ' + labels[k]) for k, a in chosen] + [rules.line(money, credit=total, note='Nộp bảo hiểm / thuế')],
                 remark or 'Nộp ' + ', '.join(labels[k] for k, _ in chosen), kind='Statutory')
    if reference_no:
        je.db_set(dict(cheque_no=reference_no, cheque_date=posting_date))
    posting.record('Lotus Finance Settings', setup.SETTINGS, 'Statutory Payment', je, amount=total, source_hash=','.join(k for k, _ in chosen), key_suffix=je.name)
    from lotus_farm.finance.payments import start_signing
    return start_signing(je, signers)


@frappe.whitelist(methods=['POST'])
def prepare_salary_payment(period, mode, posting_date, signers, reference_no=None):
    """Draft voucher paying the month's net pay less advances (Nợ phải trả NLĐ / Có tiền), sent for signatures."""
    setup.require_post()
    setup.require_enabled()
    doc = _period(period)
    if not posting.active(PERIOD, doc.name, 'Payroll'):
        frappe.throw('Ghi sổ bảng lương tháng %s trước khi chi lương.' % doc.month)
    if _advances(doc.company, doc.month, docstatus=0):
        frappe.throw('Còn phiếu tạm ứng lương tháng %s chưa ký xong. Ký hoặc hủy trước khi chi lương.' % doc.month)
    posting.guard(PERIOD, doc.name, 'Salary Payment')
    rows = pay_list(doc)
    short = [r for r in rows if r['to_pay'] < 0]
    if short:
        frappe.throw('Tạm ứng lớn hơn thực lĩnh: ' + ', '.join(r['employee_name'] for r in short))
    net = sum(r['to_pay'] for r in rows)
    if net <= 0:
        frappe.throw('Không còn lương phải chi cho tháng %s.' % doc.month)
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
