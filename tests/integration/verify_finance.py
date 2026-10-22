"""Tài chính – Kế toán on the real site, end to end, rolled back:
apply TT133 (stock value moves to 152 and the books still reconcile), switch finance on, receive goods ->
supplier invoice -> pay part -> pay the rest (signed: accountant, chief accountant, director) -> supplier owes 0;
a duplicate invoice number, a second payroll posting, a stale preview and a locked month are refused; a
material issue lands on its lot; an approved payroll posts balanced and blocks reopening until reversed;
an accountant cannot close a month and a team leader cannot call the API.
Needs tests/integration/install_finance.py first (roles, dimensions)."""
import json
import unicodedata
import uuid

import frappe
from frappe.utils import add_days, flt, get_first_day, nowdate

frappe.init(site='frontend', sites_path='/home/frappe/frappe-bench/sites')
frappe.connect()
frappe.set_user('Administrator')
from lotus_farm.finance import api, payments, payroll, posting, reports, setup  # noqa: E402

tag = uuid.uuid4().hex[:6]
today = nowdate()
report = {}


def person(key, roles, company):
    email = 'lotus-fin-%s-%s@example.com' % (key, tag)
    frappe.get_doc(dict(doctype='User', email=email, first_name='Fin ' + key, send_welcome_email=0, enabled=1,
                        roles=[dict(role=r) for r in roles])).insert(ignore_permissions=True)
    frappe.get_doc(dict(doctype='Employee', first_name='Fin ' + key, gender='Male', date_of_birth='1990-01-01', date_of_joining='2024-01-01',
                        company=company, status='Active', user_id=email)).insert(ignore_permissions=True)
    return email


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
    return frappe.db.sql("""select account, debit, credit, party, lotus_farm, lotus_farm_block from `tabGL Entry`
        where voucher_no=%s and is_cancelled=0""", voucher, as_dict=True)


try:
    company = setup.company()
    # 1. TT133 -------------------------------------------------------------------------------------------
    preview = api.coa_preview(today)
    assert not preview['errors'], preview['errors']
    stock_before = reports.reconciliation(today)['checks']
    result = setup.coa_apply(today)
    m = setup.mapping()
    assert m['inventory_material'].startswith('152 ') and m['payable_supplier'].startswith('331 ') and m['unemployment_insurance'].startswith('3386 '), m
    assert m['cash'].startswith('111 ') and m['material_cost'].startswith('621 ') and m['labour_cost'].startswith('622 '), m
    live = {a.account_number for a in frappe.get_all('Account', filters={'company': company, 'disabled': 0, 'is_group': 0}, fields=['account_number'])}
    assert '1111' not in live and '3385' not in live and '' not in live and None not in live, 'only Thông tư 99 accounts stay in use'
    if result['transfer']:
        lines = gl(result['transfer'])
        assert abs(sum(flt(x.debit) for x in lines) - sum(flt(x.credit) for x in lines)) < 1, lines
    checks = reports.reconciliation(today)['checks']
    stock_checks = [c for c in checks if c['label'].startswith('Giá trị kho')]
    assert stock_checks and all(c['ok'] for c in stock_checks), stock_checks
    report['coa'] = dict(added=result['added'], updated=result['updated'], deleted=result['deleted'], disabled=result['disabled'], transfer=result['transfer'],
                         stock=[(c['label'], c['ledger']) for c in stock_checks])

    accountant = person('acc', ['Lotus Accountant'], company)
    chief = person('chief', ['Lotus Chief Accountant'], company)
    director = person('dir', ['Lotus Purchase Approver'], company)
    leader = person('lead', ['Lotus Team Leader'], company)
    refused(as_user, leader, reports.overview, kind=frappe.PermissionError)
    refused(as_user, accountant, posting.close_month, today[:7], kind=frappe.PermissionError)
    refused(as_user, accountant, api.save_settings, {'enabled': 1}, kind=frappe.PermissionError)

    cutover = str(get_first_day(add_days(today, -40)))
    saved = as_user(chief, api.save_settings, {'enabled': 1, 'cutover_date': cutover})
    assert saved['enabled'] and not saved['errors'], saved['errors']

    # 2. Purchase -> invoice -> payments -----------------------------------------------------------------
    supplier = frappe.get_doc(dict(doctype='Supplier', supplier_name='NCC kiểm tra ' + tag, supplier_group=frappe.get_all('Supplier Group', pluck='name', limit_page_length=1)[0])).insert(ignore_permissions=True).name
    item = frappe.get_all('Item', filters={'is_stock_item': 1, 'disabled': 0, 'has_batch_no': 0, 'has_serial_no': 0}, pluck='name', limit_page_length=1)[0]
    warehouse = frappe.get_all('Warehouse', filters={'company': company, 'is_group': 0}, pluck='name', limit_page_length=1)[0]
    pr = frappe.get_doc(dict(doctype='Purchase Receipt', company=company, supplier=supplier, posting_date=today, set_posting_time=1,
                             items=[dict(item_code=item, qty=10, rate=150000, warehouse=warehouse)]))
    pr.flags.ignore_permissions = True
    pr.insert()
    pr.submit()
    receipt_gl = {x.account: x for x in gl(pr.name)}
    assert flt(receipt_gl[m['inventory_material']].debit) == 1500000 and flt(receipt_gl[m['received_not_billed']].credit) == 1500000, receipt_gl
    pending = reports.pending()
    assert any(r['name'] == pr.name for r in pending['receipts']), 'the receipt waits for its invoice'

    inv = as_user(accountant, payments.make_goods_invoice, json.dumps([pr.name]), 'HD-' + tag, today, add_days(today, 30))
    inv_gl = {x.account: x for x in gl(inv['invoice'])}
    assert flt(inv_gl[m['received_not_billed']].debit) == 1500000 and inv_gl[m['payable_supplier']].party == supplier, inv_gl
    assert flt(frappe.db.get_value('Purchase Receipt', pr.name, 'per_billed')) >= 99.99
    refused(as_user, accountant, payments.make_goods_invoice, json.dumps([pr.name]), 'HD2-' + tag, today, text='đã có hóa đơn')
    pr2 = frappe.copy_doc(pr)
    pr2.flags.ignore_permissions = True
    pr2.insert()
    pr2.submit()
    refused(as_user, accountant, payments.make_goods_invoice, json.dumps([pr2.name]), 'HD-' + tag, today, text='đã được nhập')
    refused(as_user, accountant, payments.make_goods_invoice, json.dumps([pr2.name]), 'HD3-' + tag, add_days(cutover, -1), text='trước ngày bắt đầu ghi sổ')
    pr2.cancel()

    signers = {'CHIEF': chief, 'APPROVE': director}
    first = as_user(accountant, payments.prepare_supplier_payment, supplier, json.dumps([{'invoice': inv['invoice'], 'amount': 600000}]), 'cash', today, json.dumps(signers))
    refused(as_user, accountant, payments.prepare_supplier_payment, supplier, json.dumps([{'invoice': inv['invoice'], 'amount': 1000000}]), 'cash', today,
            json.dumps(signers), text='chỉ còn nợ')
    refused(as_user, director, payments.sign_payment, 'Payment Entry', first['voucher'], kind=frappe.PermissionError)
    as_user(chief, payments.sign_payment, 'Payment Entry', first['voucher'])
    done = as_user(director, payments.sign_payment, 'Payment Entry', first['voucher'])
    assert done['docstatus'] == 1, done
    assert flt(frappe.db.get_value('Purchase Invoice', inv['invoice'], 'outstanding_amount')) == 900000
    second = as_user(accountant, payments.prepare_supplier_payment, supplier, json.dumps([{'invoice': inv['invoice'], 'amount': 900000}]), 'bank', today,
                     json.dumps(signers), 'UNC-' + tag)
    as_user(chief, payments.sign_payment, 'Payment Entry', second['voucher'])
    as_user(director, payments.sign_payment, 'Payment Entry', second['voucher'])
    owed = next((s for s in reports.payables()['suppliers'] if s['supplier'] == supplier), None)
    assert owed is None or abs(flt(owed['owed'])) < 1, owed
    assert flt(frappe.db.get_value('Purchase Invoice', inv['invoice'], 'outstanding_amount')) == 0
    report['purchase'] = dict(receipt=pr.name, invoice=inv['invoice'], payments=[first['voucher'], second['voucher']])

    # 3. Material issue on a lot -------------------------------------------------------------------------
    block = frappe.db.sql("""select name, block_code, farm from `tabFarm Block` where block_code in
        (select block_code from `tabFarm Block` group by block_code having count(*)=1) limit 1""", as_dict=True)[0]
    se = frappe.get_doc(dict(doctype='Stock Entry', company=company, stock_entry_type='Material Issue', purpose='Material Issue', posting_date=today, set_posting_time=1,
                             lotus_issue_mode='Manual', lotus_receiver='Người nhận kiểm tra', remarks='Kiểm tra kế toán ' + tag,
                             items=[dict(item_code=item, qty=2, s_warehouse=warehouse, lotus_usage_area=block.block_code + ' / thửa 1')]))
    se.flags.ignore_permissions = True
    se.insert()
    se.submit()
    cost = [x for x in gl(se.name) if x.account == m['material_cost']]
    assert cost and cost[0].lotus_farm_block == block.name and cost[0].lotus_farm == block.farm, cost
    bad = frappe.copy_doc(se)
    bad.items[0].lotus_usage_area = 'không rõ ' + tag
    bad.items[0].lotus_farm = bad.items[0].lotus_farm_block = None
    bad.flags.ignore_permissions = True
    refused(bad.insert, text='chọn lô sử dụng')
    report['issue'] = dict(entry=se.name, block=block.block_code, amount=flt(cost[0].debit))
    from lotus_farm.finance import closing
    month_now = today[:7]
    view_close = closing.preview(month_now)
    assert any(ln['account'] == m['production_cost'] and ln['lotus_farm_block'] == block.name for ln in view_close['lines']), view_close['lines'][:3]
    refused(as_user, accountant, closing.post, month_now, kind=frappe.PermissionError)
    closed = as_user(chief, closing.post, month_now)
    refused(as_user, chief, closing.post, month_now, text='đã kết chuyển')
    left = frappe.db.sql("""select sum(debit-credit) from `tabGL Entry` where is_cancelled=0 and account=%s and posting_date between %s and %s""",
                         (m['material_cost'], month_now + '-01', view_close['posting_date']))[0][0]
    assert abs(flt(left)) < 1, 'after the transfer 621 is empty for the month'
    after = reports.costs(month_now + '-01', today, 'lotus_farm_block')
    assert any(r['dim'] == block.name and flt(r['materials']) > 0 for r in after['rows']), 'the lot cost report ignores the transfer'
    report['closing'] = dict(voucher=closed['voucher'], amount=closed['amount'])

    # 4. Payroll -------------------------------------------------------------------------------------------
    month = cutover[:7]
    if any(p_['closed'] and str(p_['start_date'])[:7] == month for p_ in posting.periods(company)):
        as_user(chief, posting.reopen_month, month, 'Mở để kiểm tra (rollback)')  # locked on the real site
    employees = frappe.get_all('Employee', filters={'company': company, 'status': 'Active'}, pluck='name', limit_page_length=3)
    rows = [dict(employee=e, base=6000000, gross=7000000 + i * 500000, employee_insurance=630000, net=6370000 + i * 500000, employer_insurance=1290000)
            for i, e in enumerate(employees)]
    team = frappe.get_all('Work Team', filters={'farm': block.farm}, pluck='name', limit_page_length=1)
    snapshot = dict(rows=rows, crews=[dict(work_team=team[0], work_type=None, amount=2500000)] if team else [], totals={})
    period = frappe.get_doc(dict(doctype='Lotus Timekeeping Period', company=company, month=month, status='Closed', snapshot=json.dumps(snapshot),
                                 snapshot_hash='h-' + tag))
    period.flags.lotus_period_action = True  # the signed close itself is covered by verify_timekeeping
    period.insert(ignore_permissions=True)
    view = as_user(accountant, payroll.preview, period.name)
    assert not view['issues'], view['issues']
    refused(as_user, accountant, payroll.post, period.name, 'stale', text='đã thay đổi')
    posted = as_user(accountant, payroll.post, period.name, 'h-' + tag)
    lines = gl(posted['voucher'])
    assert abs(sum(flt(x.debit) for x in lines) - sum(flt(x.credit) for x in lines)) < 1
    expected = sum(r['gross'] + r['employer_insurance'] for r in rows) + sum(c['amount'] for c in snapshot['crews'])
    assert posted['amount'] == expected, (posted['amount'], expected)
    refused(as_user, accountant, payroll.post, period.name, 'h-' + tag, text='đã được ghi sổ')
    refused(payroll.assert_reopenable, period.name, text='đã ghi sổ kế toán')
    assert any(c['ok'] for c in reports.reconciliation(today)['checks'] if 'Bảng lương' in c['label'])

    # 5. Lock and reverse ------------------------------------------------------------------------------
    as_user(chief, posting.close_month, month)
    p = posting.active('Lotus Timekeeping Period', period.name, 'Payroll')
    refused(as_user, chief, posting.reverse, p.name, 'Sai phân bổ lô', text='khóa sổ')
    refused(as_user, chief, posting.reopen_month, month, 'x', text='lý do')
    as_user(chief, posting.reopen_month, month, 'Điều chỉnh phân bổ lương')
    refused(as_user, accountant, posting.reverse, p.name, 'Sai phân bổ lô', kind=frappe.PermissionError)
    as_user(chief, posting.reverse, p.name, 'Sai phân bổ lô')
    assert not gl(posted['voucher']), 'a reversed voucher leaves no live ledger lines'
    assert frappe.db.get_value(posting.POSTING, p.name, 'state') == 'Reversed'
    payroll.assert_reopenable(period.name)
    again = as_user(accountant, payroll.post, period.name, 'h-' + tag)
    assert again['voucher'] != posted['voucher']
    report['payroll'] = dict(first=posted['voucher'], reversed=True, again=again['voucher'], amount=posted['amount'])

    # 6. Reports ---------------------------------------------------------------------------------------
    tb = reports.trial_balance(cutover, today)
    assert tb['balanced'], tb['totals']
    by_lot = reports.costs(cutover, today, 'lotus_farm_block')
    assert any(r['dim'] == block.name and flt(r['materials']) > 0 for r in by_lot['rows']), by_lot['rows'][:5]
    recon = reports.reconciliation(today)['checks']
    assert all(c['ok'] for c in recon), [c for c in recon if not c['ok']]
    led = reports.ledger(m['payable_supplier'], cutover, today)
    assert led['lines'], 'the supplier ledger shows the invoice and payments'
    report.update(trial_balance=dict(rows=len(tb['rows']), debit=tb['totals']['debit']), reconciliation=[(c['label'][:40], c['difference']) for c in recon],
                  rollback=True)
finally:
    frappe.set_user('Administrator')
    frappe.db.rollback()
print(json.dumps(report, ensure_ascii=False, default=str))
