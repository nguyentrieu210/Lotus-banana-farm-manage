"""Báo cáo tài chính và sổ sách on the real site, rolled back: B01 balances and every account lands on one line, the month's
cost closing then result closing (911 nets to zero, profit in 4212) leaves B02 unchanged and B01 still balanced, B03 ends
on the cash in 111 + 112 + 113, the books and their Excel files build, and a bank statement matches the bank ledger
(a bank fee with no voucher stays unmatched). Needs finance switched on with the Thông tư 99 chart and install_finance."""
import base64
import json
import uuid
from io import BytesIO

import frappe
from frappe.utils import flt, get_first_day, nowdate

frappe.init(site='frontend', sites_path='/home/frappe/frappe-bench/sites')
frappe.connect()
frappe.set_user('Administrator')
from lotus_farm.finance import closing, setup, statements  # noqa: E402

tag = uuid.uuid4().hex[:6]
today = nowdate()
month = today[:7]
report = {}

try:
    cfg = setup.settings()
    assert cfg.finance_enabled and cfg.coa_version, 'finance must be on with the TT99 chart'
    company = setup.company()
    m = setup.mapping()
    year_start = today[:4] + '-01-01'
    before = statements.b01(today)
    assert all(c['ok'] for c in before['checks']), before['checks']
    assert not before['double'], before['double']
    assert not before['uncovered'], before['uncovered']
    cost_center = frappe.get_cached_value('Company', company, 'cost_center')
    pl = frappe.get_doc(dict(doctype='Journal Entry', company=company, posting_date=today, user_remark='Doanh thu, chi phí kiểm tra',
                             accounts=[dict(account=m['bank'], debit_in_account_currency=2_000_000, cost_center=cost_center),
                                       dict(account=m['sales_revenue'], credit_in_account_currency=2_000_000, cost_center=cost_center),
                                       dict(account=m['admin_expense'], debit_in_account_currency=500_000, cost_center=cost_center),
                                       dict(account=m['bank'], credit_in_account_currency=500_000, cost_center=cost_center)]))
    pl.flags.ignore_permissions = True
    pl.insert()
    pl.submit()
    b02_before = statements.b02(year_start, today)
    assert next(r for r in b02_before['rows'] if r['code'] == '50')['current'] >= 1_500_000
    # bank movement with a reference, for the statement match
    je =frappe.get_doc(dict(doctype='Journal Entry', company=company, posting_date=today, voucher_type='Bank Entry', cheque_no='BK-' + tag, cheque_date=today,
                             user_remark='Góp vốn kiểm tra', accounts=[dict(account=m['bank'], debit_in_account_currency=1_000_000, cost_center=cost_center),
                                                                        dict(account=m['opening_equity'], credit_in_account_currency=1_000_000, cost_center=cost_center)]))
    je.flags.ignore_permissions = True
    je.insert()
    je.submit()

    before = statements.b01(today)
    # month end: cost closing (if there are 62x costs), then result closing
    if closing.preview(month)['lines'] and not closing.preview(month)['posted']:
        closing.post(month)
    view = closing.result_preview(month)
    assert not view['issues'], view['issues']
    assert view['lines'] and not view['posted'], view
    if view['lines']:
        done = closing.result_post(month)
        lines = frappe.db.sql("""select account, debit, credit from `tabGL Entry` where voucher_no=%s and is_cancelled=0""", done['voucher'], as_dict=True)
        on = lambda acc, f: sum(flt(x[f]) for x in lines if x.account == acc)
        assert abs(on(m['income_summary'], 'debit') - on(m['income_summary'], 'credit')) < 1, '911 is empty after closing'
        assert abs((on(m['retained_earnings'], 'credit') - on(m['retained_earnings'], 'debit')) - done['profit']) < 1
        try:
            closing.result_post(month)
            raise AssertionError('a second result closing must be refused')
        except frappe.ValidationError:
            pass
        report['result'] = dict(voucher=done['voucher'], profit=done['profit'])
    b02_after = statements.b02(year_start, today)
    assert [r['current'] for r in b02_after['rows']] == [r['current'] for r in b02_before['rows']], 'B02 leaves the 911 closing out'
    after = statements.b01(today)
    assert all(c['ok'] for c in after['checks']), after['checks']
    row = lambda data, code: next(r for r in data['rows'] if r['code'] == code)
    assert row(after, '420')['closing'] == row(before, '420')['closing'], 'closing to 4212 does not change total retained profit'
    cash_flow = statements.b03(year_start, today)
    assert all(c['ok'] for c in cash_flow['checks']), cash_flow['checks']
    assert not cash_flow['double'], cash_flow['double']

    # books
    gj = statements.general_journal(get_first_day(today), today)
    assert abs(gj['debit'] - gj['credit']) < 1 and gj['rows']
    led = statements.general_ledger(m['bank'], get_first_day(today), today)
    assert any(r['voucher_no'] == je.name and m['opening_equity'].split(' ')[0] in r['contra'] for r in led['lines']), led['lines'][-3:]
    payables = statements.party_summary(m['payable_supplier'], year_start, today)
    assert abs(payables['totals']['closing_credit'] - payables['totals']['closing_debit']
               + flt(frappe.db.sql("""select sum(debit-credit) from `tabGL Entry` where account=%s and is_cancelled=0 and ifnull(party,'')!=''""",
                                   m['payable_supplier'])[0][0])) < 1
    stock = statements.stock_summary(get_first_day(today), today)
    assert stock['rows'], 'the warehouse has stock movements'
    for kind in ('b01', 'b02', 'b03', 'general_journal', 'stock_summary'):
        statements.export(kind, year_start, today)
        assert frappe.local.response.filecontent, kind
    statements.export('general_ledger', year_start, today, m['bank'])
    statements.export('party_summary', year_start, today, m['payable_supplier'])

    # bank statement
    from openpyxl import Workbook
    book = Workbook()
    ws = book.active
    ws.append(['SAO KÊ TÀI KHOẢN'])
    ws.append(['Ngày giao dịch', 'Số tham chiếu', 'Nội dung', 'Ghi nợ', 'Ghi có'])
    ws.append([today[8:10] + '/' + today[5:7] + '/' + today[:4], 'BK-' + tag, 'Nhan von gop', None, 1_000_000])
    ws.append([today[8:10] + '/' + today[5:7] + '/' + today[:4], 'FEE-' + tag, 'Phi quan ly tai khoan', 11_000, None])
    out = BytesIO()
    book.save(out)
    match = statements.bank_match('data:application/octet-stream;base64,' + base64.b64encode(out.getvalue()).decode())
    assert any(x['ledger']['voucher'] == je.name for x in match['matched']), match
    assert [s['amount'] for s in match['statement_only']] == [-11_000], match['statement_only']
    report.update(b01=dict(assets=row(after, '280')['closing'], equity_and_liabilities=row(after, '440')['closing']),
                  b02=dict(profit_before_tax=row(b02_after, '50')['current']), b03=dict(cash_end=row(cash_flow, '70')['current']),
                  journal_lines=len(gj['rows']), bank=dict(matched=len(match['matched']), statement_only=len(match['statement_only'])), rollback=True)
finally:
    frappe.set_user('Administrator')
    frappe.db.rollback()
print(json.dumps(report, ensure_ascii=False, default=str))
