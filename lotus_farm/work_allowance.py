"""Phụ cấp công việc and the common đơn giá công nhật (Lotus Pay Rate, by effective date).

The timekeeper ticks Phụ cấp on an employee's day (Attendance.lotus_allowance). The amount is fixed on the
record when it is saved: the Allowance rate in force that day x the workdays present (one buổi = half), so a
later change of rate leaves past days as they were. The month's approved amounts are paid on the payroll sheet
as "Phụ cấp công việc": not subject to personal income tax and outside the insurance base.
The Daywork rate is the đơn giá công for công nhân without their own; fill_daily_rates writes it on their profile
so the payroll sheet and the HRMS salary assignment keep one source.
"""
import frappe
from frappe.utils import cint, flt, getdate, nowdate

from lotus_farm.payroll_rules import allowance_amount, rate_in_force

RATE = 'Lotus Pay Rate'
ALLOWANCE, DAYWORK = 'Allowance', 'Daywork'
KIND_LABELS = {ALLOWANCE: 'Phụ cấp công việc', DAYWORK: 'Đơn giá công nhật chung'}


def install_fields():
    if not frappe.db.exists('DocType', 'Attendance'):
        return
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    create_custom_fields({'Attendance': [
        dict(fieldname='lotus_allowance', label='Lotus · Có phụ cấp công việc', fieldtype='Check', allow_on_submit=1, no_copy=0),
        dict(fieldname='lotus_allowance_amount', label='Lotus · Tiền phụ cấp', fieldtype='Currency', read_only=1, allow_on_submit=1),
    ]}, update=True, ignore_validate=True)


# The farm's rates from 01/10/2026: phụ cấp chăm buồng / phun thuốc and đơn giá công nhật of the F222 plan.
DEFAULTS = ((ALLOWANCE, 20000, 'Phụ cấp chăm buồng / phun thuốc'), (DAYWORK, 290000, 'Đơn giá công nhật kế hoạch F222'))
DEFAULT_FROM = '2026-10-01'


def seed_rates():
    """after_migrate: give each company the default rates once; companies that have any rate of a kind keep theirs."""
    if not frappe.db.exists('DocType', RATE):
        return
    for company in frappe.get_all('Company', pluck='name'):
        for kind, rate, notes in DEFAULTS:
            if not frappe.db.exists(RATE, {'company': company, 'kind': kind}):
                doc = frappe.new_doc(RATE)
                doc.update(dict(company=company, kind=kind, rate=rate, valid_from=DEFAULT_FROM, notes=notes))
                # Runs in migrate as Administrator, outside an HR session: the agreed defaults, not a user's edit.
                doc.flags.seed = True
                doc.insert(ignore_permissions=True)


def _hr_manager():
    from lotus_farm.hr_period import _hr_manager as check
    check()


def rows(company, kind):
    return frappe.get_all(RATE, filters={'company': company, 'kind': kind}, fields=['name', 'rate', 'valid_from', 'notes', 'modified'],
                          order_by='valid_from desc', limit_page_length=0)


def rate_on(company, kind, day):
    return rate_in_force(rows(company, kind), getdate(day))


def amount_for(company, day, allowance, workdays):
    """The phụ cấp fixed on one employee day."""
    return allowance_amount(rate_on(company, ALLOWANCE, day), workdays) if cint(allowance) else 0


def validate_rate(doc):
    if not doc.flags.seed:
        _hr_manager()
    if doc.kind not in KIND_LABELS:
        frappe.throw('Chọn loại mức.')
    if not (0 < flt(doc.rate) <= 100_000_000):
        frappe.throw('Mức tiền phải lớn hơn 0.')
    from lotus_farm.hr_period import is_closed
    if is_closed(doc.company, doc.valid_from):
        frappe.throw('Tháng ' + str(doc.valid_from)[:7] + ' đã khóa công; chọn ngày áp dụng từ tháng chưa khóa.')
    if frappe.db.exists(RATE, {'company': doc.company, 'kind': doc.kind, 'valid_from': doc.valid_from, 'name': ['!=', doc.name or '']}):
        frappe.throw('Đã có mức áp dụng từ ngày này.')


def _missing_daily_rate(company):
    people = frappe.get_all('Employee', filters={'company': company, 'status': 'Active', 'lotus_payment_basis': 'Daywork'},
                            fields=['name', 'lotus_daily_rate'], limit_page_length=0)
    return [p.name for p in people if not flt(p.lotus_daily_rate)]


@frappe.whitelist()
def pay_rates(company):
    if not (frappe.has_permission(RATE, 'read')):
        frappe.throw('Chưa có quyền xem mức phụ cấp.', frappe.PermissionError)
    today = nowdate()
    result = {}
    for kind, label in KIND_LABELS.items():
        history = rows(company, kind)
        result[kind] = dict(label=label, current=rate_in_force(history, today),
                            history=[dict(r, valid_from=str(r.valid_from), modified=str(r.modified)) for r in history])
    return dict(rates=result, missing_daily_rate=len(_missing_daily_rate(company)), can_edit=frappe.has_permission(RATE, 'create'))


@frappe.whitelist(methods=['POST'])
def save_pay_rate(company, kind, rate, valid_from, notes=None):
    doc = frappe.new_doc(RATE)
    doc.update(dict(company=company, kind=kind, rate=flt(rate), valid_from=getdate(valid_from), notes=str(notes or '')[:500]))
    doc.insert()
    return doc.name


@frappe.whitelist(methods=['POST'])
def fill_daily_rates(company):
    """Write the common đơn giá công on every active công nhân without one (and their salary assignment)."""
    _hr_manager()
    rate = rate_on(company, DAYWORK, nowdate())
    if not rate:
        frappe.throw('Chưa đặt đơn giá công nhật chung.')
    from lotus_farm.hr_payroll import assign_salary
    names = _missing_daily_rate(company)
    for name in names:
        doc = frappe.get_doc('Employee', name)
        doc.lotus_daily_rate = rate
        doc.save()
        assign_salary(doc)
    return dict(updated=len(names), rate=rate)


def month_allowance(company, begin, end, names):
    """Approved phụ cấp per employee for [begin, end]: days (one buổi = half) and amount."""
    result = {}
    if not names or not frappe.get_meta('Attendance').has_field('lotus_allowance'):
        return result
    for row in frappe.get_all('Attendance', filters={'company': company, 'employee': ['in', list(names)], 'docstatus': 1,
                                                     'attendance_date': ['between', [begin, end]], 'lotus_allowance': 1},
                              fields=['employee', 'working_hours', 'lotus_allowance_amount'], limit_page_length=0):
        item = result.setdefault(row.employee, dict(days=0.0, amount=0.0))
        item['days'] += min(flt(row.working_hours), 8) / 8
        item['amount'] += flt(row.lotus_allowance_amount)
    return result


def month_advances(company, month):
    """Tạm ứng lương of the pay month already paid (finance advance vouchers), deducted on the payroll sheet the same
    way the salary transfer list deducts them (lotus_farm.finance.payroll.pay_list)."""
    from lotus_farm.finance.payroll import _advances
    return _advances(company, month)
