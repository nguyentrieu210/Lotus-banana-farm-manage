"""HRMS payroll on Lotus working hours, posted to ERPNext accounting.

One Salary Structure per company pays by the hour: base / 208 (26 workdays x 8 hours) for ordinary
hours, paid leave and public holidays; +30% for night hours; 150/200/300% overtime; compulsory
insurance on the base. Hours come from approved Attendance (lotus_farm.payroll_rules), are copied
onto each Salary Slip before HRMS evaluates the formulas, and slips are submitted only for a
closed timekeeping month. Payroll Entry then books Salary expense against Payroll Payable.
Personal income tax is not computed; accounting adds it as Additional Salary (Income Tax).
"""
import frappe
from frappe.utils import flt, getdate, nowdate

from lotus_farm.payroll_rules import EMPLOYEE_INSURANCE, EMPLOYER_INSURANCE, HOURS_BASE, NIGHT_PREMIUM, OT_RATES, pay_base

HOUR = 'base/' + str(HOURS_BASE)
EARNINGS = (
    ('Lương giờ công', 'LGC', HOUR + '*lotus_regular_hours'),
    ('Lương ngày lễ, phép', 'LNP', HOUR + '*lotus_paid_hours'),
    ('Phụ cấp ca đêm', 'PCD', HOUR + '*lotus_night_hours*' + str(NIGHT_PREMIUM)),
    ('Tăng ca', 'TCA', HOUR + '*(lotus_ot_regular*' + str(OT_RATES['regular']) + '+lotus_ot_weekly_off*'
     + str(OT_RATES['weekly_off']) + '+lotus_ot_holiday*' + str(OT_RATES['holiday']) + ')'),
)
INSURANCE_LABELS = dict(bhxh='BHXH', bhyt='BHYT', bhtn='BHTN')
DEDUCTIONS = tuple((INSURANCE_LABELS[k] + ' người lao động', INSURANCE_LABELS[k] + '_NLD', 'base*' + str(r)) for k, r in EMPLOYEE_INSURANCE.items())
CONTRIBUTIONS = tuple((INSURANCE_LABELS[k] + ' doanh nghiệp', INSURANCE_LABELS[k] + '_DN', 'base*' + str(r)) for k, r in EMPLOYER_INSURANCE.items())
INSURED = 'lotus_social_insurance_no'
SLIP_FIELDS = ('lotus_workdays', 'lotus_regular_hours', 'lotus_paid_hours', 'lotus_night_hours',
               'lotus_ot_regular', 'lotus_ot_weekly_off', 'lotus_ot_holiday')
SLIP_LABELS = ('Công', 'Giờ công thường', 'Giờ lễ, phép hưởng lương', 'Giờ ca đêm', 'Giờ tăng ca ngày thường',
               'Giờ làm ngày nghỉ tuần', 'Giờ làm ngày lễ')


def install_fields():
    if not frappe.db.exists('DocType', 'Salary Slip'):
        return
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    fields = [dict(fieldname='lotus_hours_section', label='Lotus · Giờ công', fieldtype='Section Break', insert_after='payment_days')]
    previous = 'lotus_hours_section'
    for name, label in zip(SLIP_FIELDS, SLIP_LABELS):
        fields.append(dict(fieldname=name, label=label, fieldtype='Float', read_only=1, insert_after=previous))
        previous = name
    create_custom_fields({'Salary Slip': fields}, update=True, ignore_validate=True)


def _hr_manager():
    from lotus_farm.hr_period import _hr_manager as check
    check()


def _company(name):
    from lotus_farm.hr_period import _company as check
    return check(name)


def structure_name(company):
    return 'Lotus Giờ công - ' + (frappe.get_cached_value('Company', company, 'abbr') or company)


def _account(company, account_name, parent_candidates, root_type, account_type=''):
    abbr = frappe.get_cached_value('Company', company, 'abbr')
    found = frappe.db.get_value('Account', {'company': company, 'account_name': account_name, 'is_group': 0})
    if found:
        return found
    parent = next((p + ' - ' + abbr for p in parent_candidates if frappe.db.exists('Account', p + ' - ' + abbr)), None)
    if not parent:
        frappe.throw('Không tìm thấy nhóm tài khoản cha cho ' + account_name + '.')
    return frappe.get_doc(dict(doctype='Account', company=company, account_name=account_name, parent_account=parent,
                               root_type=root_type, account_type=account_type, is_group=0)).insert().name


def _accounts(company):
    salary = frappe.db.get_value('Account', {'company': company, 'account_name': 'Salary', 'is_group': 0}) \
        or _account(company, 'Chi phí lương', ('Indirect Expenses', 'Direct Expenses'), 'Expense')
    payable = frappe.get_cached_value('Company', company, 'default_payroll_payable_account') \
        or frappe.db.get_value('Account', {'company': company, 'account_name': 'Payroll Payable', 'is_group': 0}) \
        or _account(company, 'Phải trả người lao động', ('Current Liabilities',), 'Liability', 'Payable')
    # HRMS books net pay per employee as a party, which ERPNext allows only on a Payable account.
    if frappe.db.get_value('Account', payable, 'account_type') != 'Payable':
        account = frappe.get_doc('Account', payable)
        account.account_type = 'Payable'
        account.save()
    insurance = _account(company, 'Bảo hiểm phải nộp', ('Duties and Taxes', 'Current Liabilities'), 'Liability')
    employer = _account(company, 'Chi phí bảo hiểm doanh nghiệp', ('Indirect Expenses', 'Direct Expenses'), 'Expense')
    return frappe._dict(salary=salary, payable=payable, insurance=insurance, employer=employer)


def _component(name, abbr, kind, formula, company, account, liability=None, condition=''):
    doc = frappe.get_doc('Salary Component', name) if frappe.db.exists('Salary Component', name) else frappe.new_doc('Salary Component')
    doc.update(dict(salary_component=name, salary_component_abbr=abbr, type=kind, depends_on_payment_days=0,
                    is_tax_applicable=1 if kind == 'Earning' else 0, round_to_the_nearest_integer=1, remove_if_zero_valued=1,
                    amount_based_on_formula=1, formula=formula, condition=condition))
    rows = [r for r in doc.get('accounts') if r.company != company]
    doc.set('accounts', rows + [dict(company=company, account=account, **({'liability_account': liability} if liability else {}))])
    doc.save()
    return doc.name


@frappe.whitelist()
def payroll_setup_status(company):
    _hr_manager()
    _company(company)
    name = structure_name(company)
    return dict(structure=name if frappe.db.exists('Salary Structure', {'name': name, 'docstatus': 1}) else None,
                payable_account=frappe.get_cached_value('Company', company, 'default_payroll_payable_account'))


@frappe.whitelist(methods=['POST'])
def setup_payroll(company):
    """Create the hourly salary components, accounts and the submitted Salary Structure (idempotent)."""
    _hr_manager()
    _company(company)
    accounts = _accounts(company)
    if not frappe.get_cached_value('Company', company, 'default_payroll_payable_account'):
        frappe.db.set_value('Company', company, 'default_payroll_payable_account', accounts.payable)
        frappe.clear_document_cache('Company', company)
    rows = dict(earnings=[], deductions=[], employer_contributions=[])
    for name, abbr, formula in EARNINGS:
        rows['earnings'].append((_component(name, abbr, 'Earning', formula, company, accounts.salary), abbr, formula, ''))
    for name, abbr, formula in DEDUCTIONS:
        rows['deductions'].append((_component(name, abbr, 'Deduction', formula, company, accounts.insurance, condition=INSURED), abbr, formula, INSURED))
    for name, abbr, formula in CONTRIBUTIONS:
        rows['employer_contributions'].append((_component(name, abbr, 'Employer Contribution', formula, company, accounts.employer,
                                                          liability=accounts.insurance, condition=INSURED), abbr, formula, INSURED))
    name = structure_name(company)
    if frappe.db.exists('Salary Structure', {'name': name, 'docstatus': 1}):
        return dict(structure=name, created=False)
    doc = frappe.get_doc('Salary Structure', name) if frappe.db.exists('Salary Structure', name) else frappe.new_doc('Salary Structure')
    doc.update(dict(company=company, payroll_frequency='Monthly', is_active='Yes',
                    currency=frappe.get_cached_value('Company', company, 'default_currency')))
    for table, items in rows.items():
        doc.set(table, [dict(salary_component=component, abbr=abbr, amount_based_on_formula=1, formula=formula,
                             condition=condition, depends_on_payment_days=0) for component, abbr, formula, condition in items])
    if doc.is_new():
        doc.name = name
        doc.insert(set_name=name)
    else:
        doc.save()
    doc.submit()
    return dict(structure=doc.name, created=True)


def assign_salary(employee, from_date=None):
    """Keep one submitted Salary Structure Assignment per effective date matching the Lotus pay rate."""
    name = structure_name(employee.company)
    if not frappe.db.exists('Salary Structure', {'name': name, 'docstatus': 1}):
        return None
    base = pay_base(employee.lotus_payment_basis, employee.lotus_base_salary, employee.lotus_daily_rate)
    if employee.lotus_payment_basis == 'Piecework' or base <= 0:
        return None
    from lotus_farm.hr_period import is_closed
    joined = getdate(employee.date_of_joining) if employee.date_of_joining else None
    if from_date:
        start = getdate(from_date)
    else:
        # Without a chosen date: from joining when that month is still open, otherwise from this month.
        first = frappe.db.get_value('Salary Structure Assignment', {'employee': employee.name, 'docstatus': 1}, 'name')
        start = joined if joined and not first and not is_closed(employee.company, joined) else getdate(nowdate()).replace(day=1)
    if joined and start < joined:
        start = joined
    current = frappe.get_all('Salary Structure Assignment', filters={'employee': employee.name, 'docstatus': 1, 'from_date': ['<=', start]},
                             fields=['name', 'salary_structure', 'base', 'from_date'], order_by='from_date desc', limit=1)
    if current and current[0].salary_structure == name and abs(flt(current[0].base) - base) < 0.5:
        return current[0].name
    if is_closed(employee.company, start):
        frappe.throw('Tháng ' + str(start)[:7] + ' đã khóa công. Chọn ngày hiệu lực lương từ tháng chưa khóa.')
    for same_day in frappe.get_all('Salary Structure Assignment', filters={'employee': employee.name, 'docstatus': 1, 'from_date': start}, pluck='name'):
        frappe.get_doc('Salary Structure Assignment', same_day).cancel()
    doc = frappe.get_doc(dict(doctype='Salary Structure Assignment', employee=employee.name, salary_structure=name,
                              company=employee.company, currency=frappe.get_cached_value('Company', employee.company, 'default_currency'),
                              from_date=start, base=base,
                              payroll_payable_account=frappe.get_cached_value('Company', employee.company, 'default_payroll_payable_account')))
    doc.insert()
    doc.submit()
    return doc.name


def _lotus_slip(doc):
    return bool(doc.company and frappe.db.exists('Salary Structure', {'name': structure_name(doc.company), 'docstatus': 1}))


def fill_slip_hours(doc, method=None):
    """Salary Slip before_validate: copy approved hours of the slip period so the structure formulas can use them."""
    if doc.docstatus != 0 or not (doc.employee and doc.start_date and doc.end_date) or not _lotus_slip(doc):
        return
    from lotus_farm.hr_period import month_hours
    person = frappe.db.get_value('Employee', doc.employee, ['name', 'date_of_joining', 'relieving_date'], as_dict=True)
    begin, end = getdate(doc.start_date), getdate(doc.end_date)
    summary = month_hours(doc.company, begin, end, [person])[0].get(doc.employee) or {}
    for field, key in zip(SLIP_FIELDS, ('workdays', 'regular_hours', 'paid_hours', 'night_hours', 'ot_regular', 'ot_weekly_off', 'ot_holiday')):
        doc.set(field, flt(summary.get(key)))


def slip_period_guard(doc, method=None):
    """Salary Slip before_submit: Lotus slips are final only for a closed timekeeping month."""
    if not _lotus_slip(doc) or doc.salary_structure != structure_name(doc.company):
        return
    from lotus_farm.hr_period import is_closed
    if not is_closed(doc.company, doc.start_date):
        frappe.throw('Khóa kỳ công tháng ' + str(doc.start_date)[:7] + ' trước khi duyệt phiếu lương.')


def _month(month):
    from lotus_farm.hr_period import _month as parse
    return parse(month)


def _entry(company, begin, end):
    name = frappe.db.get_value('Payroll Entry', {'company': company, 'start_date': begin, 'end_date': end, 'docstatus': ['<', 2]})
    return frappe.get_doc('Payroll Entry', name) if name else None


@frappe.whitelist()
def payroll_run(company, month):
    """HRMS payroll state for the month next to the Lotus sheet, employee by employee."""
    _hr_manager()
    _company(company)
    begin, end = _month(month)
    entry = _entry(company, begin, end)
    slips = frappe.get_all('Salary Slip', filters={'company': company, 'start_date': begin, 'end_date': end, 'docstatus': ['<', 2]},
                           fields=['name', 'employee', 'employee_name', 'gross_pay', 'total_deduction', 'net_pay', 'docstatus', 'journal_entry'],
                           order_by='employee_name', limit_page_length=0)
    from lotus_farm.hr_period import payroll_sheet
    sheet = {e['employee']: e for e in payroll_sheet(company, month)['employees']}
    rows = []
    for slip in slips:
        lotus = sheet.get(slip.employee) or {}
        rows.append(dict(slip, lotus_gross=lotus.get('gross'), lotus_net=lotus.get('net'),
                         difference=round(flt(slip.gross_pay) - flt(lotus.get('gross')))))
    journals = sorted({s.journal_entry for s in slips if s.journal_entry})
    return dict(month=month, structure=payroll_setup_status(company)['structure'],
                entry=dict(name=entry.name, status=entry.status, docstatus=entry.docstatus) if entry else None,
                slips=rows, journal_entries=journals,
                totals=dict(gross=sum(flt(s.gross_pay) for s in slips), deductions=sum(flt(s.total_deduction) for s in slips),
                            net=sum(flt(s.net_pay) for s in slips)))


@frappe.whitelist(methods=['POST'])
def create_payroll(company, month):
    """Payroll Entry for a closed month: lists employees with a salary assignment and creates draft Salary Slips."""
    _hr_manager()
    _company(company)
    begin, end = _month(month)
    from lotus_farm.hr_period import is_closed
    if not is_closed(company, begin):
        frappe.throw('Khóa kỳ công tháng ' + month + ' trước khi tạo phiếu lương.')
    if not payroll_setup_status(company)['structure']:
        frappe.throw('Chưa cài đặt cấu trúc lương giờ công. Bấm "Cài đặt lương HRMS" trước.')
    from lotus_farm.controls import lock
    lock('Company', company)
    if _entry(company, begin, end):
        frappe.throw('Tháng ' + month + ' đã có bảng lương HRMS.')
    entry = frappe.get_doc(dict(doctype='Payroll Entry', company=company, posting_date=end, payroll_frequency='Monthly',
                                start_date=begin, end_date=end, currency=frappe.get_cached_value('Company', company, 'default_currency'),
                                exchange_rate=1, cost_center=frappe.get_cached_value('Company', company, 'cost_center'),
                                payroll_payable_account=frappe.get_cached_value('Company', company, 'default_payroll_payable_account'),
                                validate_attendance=0, salary_slip_based_on_timesheet=0))
    entry.fill_employee_details()
    entry.insert()
    entry.submit()
    return dict(name=entry.name, employees=len(entry.employees), status=frappe.db.get_value('Payroll Entry', entry.name, 'status'))


@frappe.whitelist(methods=['POST'])
def post_payroll(company, month):
    """Submit the month's draft Salary Slips; HRMS books Salary expense against Payroll Payable."""
    _hr_manager()
    _company(company)
    begin, end = _month(month)
    entry = _entry(company, begin, end)
    if not entry or entry.docstatus != 1:
        frappe.throw('Chưa có bảng lương HRMS cho tháng ' + month + '.')
    from lotus_farm.controls import lock
    lock('Company', company)
    entry.submit_salary_slips()
    journals = sorted(set(frappe.get_all('Salary Slip', filters={'payroll_entry': entry.name, 'docstatus': 1}, pluck='journal_entry')) - {None, ''})
    return dict(name=entry.name, journal_entries=journals, status=frappe.db.get_value('Payroll Entry', entry.name, 'status'))
