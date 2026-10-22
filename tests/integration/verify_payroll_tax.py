"""Lương đầy đủ on the real site, rolled back: the payroll sheet reads dependents / the 08 commitment and computes income
tax and the union fee; posting credits 3335 and 3382; an advance (signed) is deducted from the month's salary payment and
the transfer list; insurance, union fee and income tax are paid by a signed voucher that cannot exceed what is owed.
Needs finance switched on with the Thông tư 99 chart and install_finance (Employee fields, 911, mapping keys)."""
import json
import unicodedata
import uuid

import frappe
from frappe.utils import flt, get_first_day, get_last_day, nowdate

frappe.init(site='frontend', sites_path='/home/frappe/frappe-bench/sites')
frappe.connect()
frappe.set_user('Administrator')
from lotus_farm import hr_period, payroll_rules  # noqa: E402
from lotus_farm.finance import payments, payroll, posting, setup  # noqa: E402

tag = uuid.uuid4().hex[:6]
today = nowdate()
month = today[:7]
report = {}


def person(key, roles, company, **extra):
    email = 'lotus-pit-%s-%s@example.com' % (key, tag)
    frappe.get_doc(dict(doctype='User', email=email, first_name='Pit ' + key, send_welcome_email=0, enabled=1,
                        roles=[dict(role=r) for r in roles])).insert(ignore_permissions=True)
    emp = frappe.get_doc(dict(doctype='Employee', first_name='Pit ' + key, gender='Male', date_of_birth='1990-01-01', date_of_joining='2024-01-01',
                              company=company, status='Active', user_id=email, **extra)).insert(ignore_permissions=True)
    return email, emp.name


def as_user(name, fn, *args, **kwargs):
    frappe.set_user(name)
    try:
        return fn(*args, **kwargs)
    finally:
        frappe.set_user('Administrator')


def refused(fn, *args, kind=frappe.ValidationError, text=None):
    try:
        fn(*args)
    except kind as exc:
        nfc = lambda t: unicodedata.normalize('NFC', t)
        assert text is None or nfc(text) in nfc(str(exc)), exc
        return str(exc)
    raise AssertionError('expected refusal: %s' % getattr(fn, '__name__', fn))


def gl(voucher):
    return frappe.db.sql("""select account, debit, credit from `tabGL Entry` where voucher_no=%s and is_cancelled=0""", voucher, as_dict=True)


def amount(lines, account, side):
    return sum(flt(x[side]) for x in lines if x.account == account)


try:
    cfg = setup.settings()
    assert cfg.finance_enabled and cfg.coa_version, 'finance must be on with the TT99 chart'
    company = setup.company()
    m = setup.mapping()
    assert m.get('pit_payable', '').startswith('3335') and m.get('union_fee', '').startswith('3382'), (m.get('pit_payable'), m.get('union_fee'))
    assert frappe.db.exists('Account', {'company': company, 'account_number': '911'}), 'install adds 911 to a company on TT99'
    frappe.db.set_single_value(setup.SETTINGS, 'minimum_wage_region', 'II')
    accountant, _ = person('acc', ['Lotus Accountant'], company)
    chief, _ = person('chief', ['Lotus Chief Accountant'], company)
    director, _ = person('dir', ['Lotus Purchase Approver'], company)
    signers = json.dumps({'CHIEF': chief, 'APPROVE': director})
    _, staff = person('staff', [], company, lotus_worker_category='Permanent', lotus_payment_basis='Monthly', lotus_base_salary=41_600_000,
                      lotus_social_insurance_no='SI' + tag, lotus_dependents=1)
    _, casual = person('casual', [], company, lotus_worker_category='Seasonal', lotus_payment_basis='Daywork', lotus_daily_rate=300_000)

    # 1. The sheet reads the tax profile of each person
    begin, end = get_first_day(today), get_last_day(today)
    sheet = hr_period._sheet(company, month, begin, end)
    row = next(e for e in sheet['employees'] if e['employee'] == staff)
    assert row['dependents'] == 1 and 'pit' in row and row['insurance_parts'], row
    assert next(e for e in sheet['employees'] if e['employee'] == casual)['payment_basis'] == 'Daywork'
    assert 'pit' in sheet['totals'] and 'union_fee' in sheet['totals']

    params = payroll_rules.params_on(end)
    full = dict(payroll_rules.empty_summary(), regular_hours=208, ot_regular=10, workdays=26)
    a = payroll_rules.hourly_pay('Monthly', full, base_salary=41_600_000, insured=True, params=params, region='II',
                                 tax=dict(method='progressive', dependents=1))
    b = payroll_rules.hourly_pay('Daywork', dict(payroll_rules.empty_summary(), regular_hours=200, workdays=25), daily_rate=300_000, params=params,
                                 tax=dict(method='flat'))
    assert b['pit'] == round(b['gross'] * 0.10) and a['pit'] > 0, (a['pit'], b['pit'])
    rows = [dict(a, employee=staff, employee_name='Pit staff'), dict(b, employee=casual, employee_name='Pit casual')]
    snapshot = dict(employees=rows, crews=[], totals={})
    period = frappe.get_doc(dict(doctype='Lotus Timekeeping Period', company=company, month=month, status='Closed', snapshot=json.dumps(snapshot),
                                 snapshot_hash='p-' + tag))
    period.flags.lotus_period_action = True
    period.insert(ignore_permissions=True)

    # 2. Posting: 3335 and 3382
    view = as_user(accountant, payroll.preview, period.name)
    assert not view['issues'], view['issues']
    assert view['totals']['pit'] == a['pit'] + b['pit'] and view['totals']['union_fee'] == a['union_fee'], view['totals']
    posted = as_user(accountant, payroll.post, period.name, 'p-' + tag)
    lines = gl(posted['voucher'])
    assert amount(lines, m['pit_payable'], 'credit') == a['pit'] + b['pit']
    assert amount(lines, m['union_fee'], 'credit') == a['union_fee']
    assert abs(sum(flt(x.debit) for x in lines) - sum(flt(x.credit) for x in lines)) < 1

    # 3. Advance -> deducted from the salary payment
    adv = as_user(accountant, payroll.prepare_advance, staff, 2_000_000, month, 'cash', today, signers)
    refused(as_user, accountant, payroll.prepare_salary_payment, period.name, 'bank', today, signers, text='chưa ký xong')
    as_user(chief, payments.sign_payment, 'Journal Entry', adv['voucher'])
    done = as_user(director, payments.sign_payment, 'Journal Entry', adv['voucher'])
    assert done['docstatus'] == 1
    adv_gl = gl(adv['voucher'])
    assert amount(adv_gl, m['payable_employee'], 'debit') == 2_000_000 and amount(adv_gl, m['cash'], 'credit') == 2_000_000
    listing = as_user(accountant, payroll.salary_list, period.name)
    mine = next(r for r in listing['rows'] if r['employee'] == staff)
    assert mine['advance'] == 2_000_000 and mine['to_pay'] == a['net'] - 2_000_000, mine
    pay = as_user(accountant, payroll.prepare_salary_payment, period.name, 'bank', today, signers, 'UNC-' + tag)
    assert flt(frappe.db.get_value('Journal Entry', pay['voucher'], 'total_debit')) == a['net'] + b['net'] - 2_000_000
    refused(as_user, accountant, payroll.prepare_advance, staff, 500_000, month, 'cash', today, signers, text='đã có phiếu chi')
    ready = payments.vouchers()
    assert any(v['name'] == adv['voucher'] and v['kind'] == 'Tạm ứng lương' for v in ready['vouchers'])
    payroll.export_salary_transfer(period.name)
    assert frappe.local.response.filecontent, 'the transfer list is an Excel file'

    # 4. Paying insurance / union fee / income tax
    owed = {r['key']: r for r in payroll.statutory_balances()}
    assert owed['pit_payable']['owed'] >= a['pit'] + b['pit'], owed['pit_payable']
    refused(as_user, accountant, payroll.prepare_statutory, json.dumps([{'key': 'pit_payable', 'amount': owed['pit_payable']['payable'] + 1000}]),
            'bank', today, signers, 'UNC2-' + tag, text='chỉ còn phải nộp')
    st = as_user(accountant, payroll.prepare_statutory, json.dumps([{'key': 'pit_payable', 'amount': a['pit'] + b['pit']},
                                                                    {'key': 'union_fee', 'amount': a['union_fee']}]), 'bank', today, signers, 'UNC3-' + tag)
    assert payroll.statutory_balances()[-1]['pending'] >= a['pit'] + b['pit']
    as_user(chief, payments.sign_payment, 'Journal Entry', st['voucher'])
    as_user(director, payments.sign_payment, 'Journal Entry', st['voucher'])
    st_gl = gl(st['voucher'])
    assert amount(st_gl, m['pit_payable'], 'debit') == a['pit'] + b['pit'] and amount(st_gl, m['union_fee'], 'debit') == a['union_fee']
    assert amount(st_gl, m['bank'], 'credit') == a['pit'] + b['pit'] + a['union_fee']
    report.update(payroll=posted['voucher'], pit=dict(staff=a['pit'], casual=b['pit'], taxable=a['taxable_income']), union_fee=a['union_fee'],
                  advance=adv['voucher'], salary=pay['voucher'], statutory=st['voucher'], rollback=True)
finally:
    frappe.set_user('Administrator')
    frappe.db.rollback()
print(json.dumps(report, ensure_ascii=False, default=str))
