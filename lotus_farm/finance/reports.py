"""Tài chính – Kế toán: what the finance page reads. Every figure comes from ERPNext's GL Entry (is_cancelled=0)
or from the Lotus source documents it reconciles against; nothing is stored twice.
"""
import json
from io import BytesIO

import frappe
from frappe.utils import add_days, flt, get_first_day, get_last_day, getdate, nowdate

from lotus_farm.finance import posting, rules, setup


def _range(from_date=None, to_date=None):
    to_date = getdate(to_date or nowdate())
    from_date = getdate(from_date or get_first_day(to_date))
    if from_date > to_date:
        frappe.throw('Từ ngày phải trước đến ngày.')
    return from_date, to_date


def _balance(company, accounts, on_date):
    accounts = [a for a in accounts if a]
    if not accounts:
        return 0
    return flt(frappe.db.sql("""select sum(debit) - sum(credit) from `tabGL Entry` where company=%s and is_cancelled=0
        and posting_date<=%s and account in %s""", (company, on_date, tuple(accounts)))[0][0])


def _str(row, *fields):
    for f in fields:
        if row.get(f) is not None:
            row[f] = str(row[f])
    return row


@frappe.whitelist()
def overview(on_date=None):
    setup.require_view()
    cfg = setup.settings()
    company = setup.company()
    m = setup.mapping(cfg)
    on_date = getdate(on_date or nowdate())
    start = get_first_day(on_date)
    cost = frappe.db.sql("""select sum(debit) - sum(credit) from `tabGL Entry` where company=%s and is_cancelled=0
        and posting_date between %s and %s and account in %s""", (company, start, on_date, tuple(a for a in (m['production_cost'], m['admin_expense']) if a) or ('',)))[0][0]
    tiles = dict(cash=_balance(company, [m['cash']], on_date), bank=_balance(company, [m['bank']], on_date),
                 payable_supplier=-_balance(company, [m['payable_supplier']], on_date), payable_employee=-_balance(company, [m['payable_employee']], on_date),
                 insurance=-_balance(company, [m['social_insurance'], m['health_insurance'], m['unemployment_insurance']], on_date),
                 received_not_billed=-_balance(company, [m['received_not_billed']], on_date), month_cost=flt(cost))
    waiting = pending()
    return dict(company=company, currency=frappe.get_cached_value('Company', company, 'default_currency'), on_date=str(on_date),
                enabled=bool(cfg.finance_enabled), cutover_date=str(cfg.cutover_date or ''), coa_version=cfg.coa_version or '',
                mapping_errors=setup.mapping_errors(cfg), tiles=tiles, pending_counts={k: len(v) for k, v in waiting.items()},
                can_post=setup.can_post(), is_chief=setup.is_chief(), dims=[dict(field=f, doctype=d, label=l) for f, d, l in rules.DIMENSIONS],
                keys=[dict(key=k, label=v[0], account=m.get(k)) for k, v in rules.KEYS.items()])


@frappe.whitelist()
def pending():
    """Documents that still need an accountant: receipts without invoice, approved payroll not posted, issues without lot,
    payment vouchers waiting for signatures."""
    setup.require_view()
    company = setup.company()
    cfg = setup.settings()
    from lotus_farm.finance.payments import receipts_to_bill
    receipts = [dict(r, kind='receipt', reason='Đã nhận hàng, chưa có hóa đơn nhà cung cấp') for r in receipts_to_bill()]
    payroll = []
    for p in frappe.get_all('Lotus Timekeeping Period', filters={'company': company, 'status': 'Closed'}, fields=['name', 'month', 'closed_at'], order_by='month desc'):
        if not posting.active('Lotus Timekeeping Period', p.name, 'Payroll'):
            payroll.append(dict(kind='payroll', name=p.name, month=p.month, closed_at=str(p.closed_at or ''), reason='Bảng lương đã ký đủ, chưa ghi sổ'))
    issues = []
    if frappe.get_meta('Stock Entry Detail').has_field('lotus_farm'):
        since = cfg.cutover_date or '1900-01-01'
        for r in frappe.db.sql("""select se.name, se.posting_date, d.idx, d.item_code, d.lotus_usage_area, d.amount from `tabStock Entry` se
                join `tabStock Entry Detail` d on d.parent=se.name where se.docstatus=1 and se.company=%s and se.stock_entry_type='Material Issue'
                and se.posting_date>=%s and ifnull(d.lotus_farm,'')='' order by se.posting_date desc limit 300""", (company, since), as_dict=True):
            issues.append(dict(_str(r, 'posting_date'), kind='issue', reason='Phiếu xuất dòng %d (%s) chưa gắn lô: "%s"' % (r.idx, r.item_code, r.lotus_usage_area or '')))
    vouchers = []
    for p in frappe.get_all(posting.POSTING, filters={'state': 'Draft'}, fields=['name', 'voucher_type', 'voucher_name', 'purpose', 'amount', 'source_name', 'posted_by'],
                            order_by='creation desc'):
        vouchers.append(dict(p, kind='voucher', reason='Phiếu chi chờ ký'))
    return dict(receipts=receipts, payroll=payroll, issues=issues, vouchers=vouchers)


@frappe.whitelist()
def journal(from_date=None, to_date=None, voucher_type=None, account=None, limit=200):
    """Vouchers with their ledger lines and the Lotus document behind each."""
    setup.require_view()
    company = setup.company()
    start, end = _range(from_date, to_date)
    conds, values = ['company=%(c)s', 'is_cancelled=0', 'posting_date between %(s)s and %(e)s'], dict(c=company, s=start, e=end, n=int(limit or 200))
    if voucher_type:
        conds.append('voucher_type=%(vt)s')
        values['vt'] = voucher_type
    if account:
        conds.append('voucher_no in (select voucher_no from `tabGL Entry` where account=%(a)s and is_cancelled=0)')
        values['a'] = account
    heads = frappe.db.sql("""select voucher_type, voucher_no, posting_date, sum(debit) amount from `tabGL Entry` where %s
        group by voucher_type, voucher_no, posting_date order by posting_date desc, voucher_no desc limit %%(n)s""" % ' and '.join(conds), values, as_dict=True)
    if not heads:
        return []
    names = [h.voucher_no for h in heads]
    dim_cols = ''.join(', ' + f for f in rules.DIM_FIELDS if frappe.get_meta('GL Entry').has_field(f))
    lines = frappe.db.sql("""select voucher_no, account, debit, credit, party, remarks%s from `tabGL Entry` where is_cancelled=0 and voucher_no in %%s
        order by debit desc""" % dim_cols, (tuple(names),), as_dict=True)
    links = {p.voucher_name: p for p in frappe.get_all(posting.POSTING, filters={'voucher_name': ['in', names]},
                                                       fields=['voucher_name', 'source_doctype', 'source_name', 'purpose', 'state'])}
    by = {}
    for ln in lines:
        by.setdefault(ln.voucher_no, []).append(ln)
    out = []
    for h in heads:
        link = links.get(h.voucher_no)
        source = dict(doctype=link.source_doctype, name=link.source_name, purpose=link.purpose) if link else dict(doctype=h.voucher_type, name=h.voucher_no, purpose='')
        out.append(dict(voucher_type=h.voucher_type, voucher_no=h.voucher_no, posting_date=str(h.posting_date), amount=flt(h.amount), source=source,
                        lines=by.get(h.voucher_no, [])))
    return out


@frappe.whitelist()
def payables(on_date=None):
    """Per supplier: invoiced, paid, owed, overdue; and each open invoice with its age."""
    setup.require_view()
    company = setup.company()
    m = setup.mapping()
    on_date = getdate(on_date or nowdate())
    rows = frappe.db.sql("""select party supplier, sum(credit) invoiced, sum(debit) paid, sum(credit) - sum(debit) owed from `tabGL Entry`
        where company=%s and is_cancelled=0 and party_type='Supplier' and account=%s and posting_date<=%s group by party having abs(sum(credit) - sum(debit)) > 0.5
           or sum(credit) > 0""", (company, m['payable_supplier'], on_date), as_dict=True)
    from lotus_farm.finance.payments import open_invoices
    invoices = open_invoices()
    names = {s.name: s.supplier_name for s in frappe.get_all('Supplier', filters={'name': ['in', [r.supplier for r in rows] or ['']]}, fields=['name', 'supplier_name'])}
    for r in rows:
        r['supplier_name'] = names.get(r.supplier, r.supplier)
        mine = [i for i in invoices if i['supplier'] == r.supplier]
        r['overdue'] = sum(flt(i['outstanding_amount']) for i in mine if i['aging'] != 'Trong hạn')
        r['open_invoices'] = len(mine)
    return dict(suppliers=sorted(rows, key=lambda r: -flt(r.owed)), invoices=invoices,
                gl_total=-_balance(company, [m['payable_supplier']], on_date), on_date=str(on_date))


def _accounts(company):
    return frappe.get_all('Account', filters={'company': company}, fields=['name', 'account_number', 'account_name', 'root_type', 'is_group', 'parent_account', 'lft', 'rgt'],
                          order_by='lft')


@frappe.whitelist()
def trial_balance(from_date=None, to_date=None):
    """Bảng cân đối phát sinh: opening, period and closing debit/credit of every account with movement, by account number."""
    setup.require_view()
    company = setup.company()
    start, end = _range(from_date, to_date)
    rows = frappe.db.sql("""select account,
            sum(case when posting_date < %(s)s then debit - credit else 0 end) opening,
            sum(case when posting_date between %(s)s and %(e)s then debit else 0 end) debit,
            sum(case when posting_date between %(s)s and %(e)s then credit else 0 end) credit
        from `tabGL Entry` where company=%(c)s and is_cancelled=0 and posting_date<=%(e)s group by account""", dict(c=company, s=start, e=end), as_dict=True)
    meta = {a.name: a for a in _accounts(company)}
    out = []
    for r in rows:
        a = meta.get(r.account) or frappe._dict(account_number='', account_name=r.account, root_type='')
        opening, closing = flt(r.opening), flt(r.opening) + flt(r.debit) - flt(r.credit)
        if not any(round(x) for x in (opening, r.debit, r.credit, closing)):
            continue
        out.append(dict(account=r.account, number=a.account_number or '', name=a.account_name, root_type=a.root_type,
                        opening_debit=max(opening, 0), opening_credit=max(-opening, 0), debit=flt(r.debit), credit=flt(r.credit),
                        closing_debit=max(closing, 0), closing_credit=max(-closing, 0)))
    out.sort(key=lambda r: (r['number'] or 'zzz', r['name']))
    totals = {k: sum(r[k] for r in out) for k in ('opening_debit', 'opening_credit', 'debit', 'credit', 'closing_debit', 'closing_credit')}
    return dict(rows=out, totals=totals, from_date=str(start), to_date=str(end), balanced=abs(totals['debit'] - totals['credit']) < 1)


@frappe.whitelist()
def ledger(account, from_date=None, to_date=None):
    """Sổ chi tiết tài khoản: opening balance, every line with its running balance, closing balance."""
    setup.require_view()
    company = setup.company()
    start, end = _range(from_date, to_date)
    if frappe.db.get_value('Account', account, 'company') != company:
        frappe.throw('Tài khoản không thuộc công ty.')
    opening = flt(frappe.db.sql("""select sum(debit) - sum(credit) from `tabGL Entry` where account=%s and is_cancelled=0 and posting_date<%s""", (account, start))[0][0])
    dim_cols = ''.join(', ' + f for f in rules.DIM_FIELDS if frappe.get_meta('GL Entry').has_field(f))
    lines = frappe.db.sql("""select posting_date, voucher_type, voucher_no, party, remarks, debit, credit, against%s from `tabGL Entry`
        where account=%%s and is_cancelled=0 and posting_date between %%s and %%s order by posting_date, creation""" % dim_cols, (account, start, end), as_dict=True)
    running = opening
    for ln in lines:
        running += flt(ln.debit) - flt(ln.credit)
        ln['balance'] = running
        ln['posting_date'] = str(ln.posting_date)
    return dict(account=account, opening=opening, closing=running, lines=lines, from_date=str(start), to_date=str(end))


COST_GROUPS = (('lotus_farm', 'Vườn'), ('lotus_farm_block', 'Lô'), ('lotus_crop_cycle', 'Vụ'), ('lotus_work_type', 'Công việc'))


@frappe.whitelist()
def costs(from_date=None, to_date=None, group_by='lotus_farm_block', farm=None):
    """Chi phí theo vườn / lô / vụ / công việc on the production cost account, split into materials (stock issues),
    labour (payroll), crews (piece-rate) and services (supplier invoices)."""
    setup.require_view()
    if group_by not in dict(COST_GROUPS):
        frappe.throw('Chọn nhóm theo vườn, lô, vụ hoặc công việc.')
    if not frappe.get_meta('GL Entry').has_field(group_by):
        return dict(rows=[], totals={}, group_by=group_by)
    company = setup.company()
    m = setup.mapping()
    start, end = _range(from_date, to_date)
    conds = 'g.company=%(c)s and g.is_cancelled=0 and g.account=%(a)s and g.posting_date between %(s)s and %(e)s'
    values = dict(c=company, a=m['production_cost'], s=start, e=end)
    if farm:
        conds += ' and g.lotus_farm=%(f)s'
        values['f'] = farm
    rows = frappe.db.sql("""select g.%(g)s dim, g.lotus_farm farm,
            sum(case when g.voucher_type in ('Stock Entry','Stock Reconciliation') then g.debit - g.credit else 0 end) materials,
            sum(case when g.voucher_type='Journal Entry' and g.remarks not like 'Khoán%%' then g.debit - g.credit else 0 end) labour,
            sum(case when g.voucher_type='Journal Entry' and g.remarks like 'Khoán%%' then g.debit - g.credit else 0 end) crews,
            sum(case when g.voucher_type='Purchase Invoice' then g.debit - g.credit else 0 end) services,
            sum(g.debit - g.credit) total
        from `tabGL Entry` g where %(w)s group by g.%(g)s, g.lotus_farm order by total desc""".replace('%(g)s', group_by).replace('%(w)s', conds), values, as_dict=True)
    labels = _dim_labels(group_by, [r.dim for r in rows])
    blocks = {b.name: b for b in frappe.get_all('Farm Block', filters={'name': ['in', [r.dim for r in rows if r.dim] or ['']]}, fields=['name', 'area_ha'])} \
        if group_by == 'lotus_farm_block' else {}
    for r in rows:
        r['label'] = labels.get(r.dim) or ('(chưa gắn ' + dict(COST_GROUPS)[group_by].lower() + ')' if not r.dim else r.dim)
        area = flt(blocks[r.dim].area_ha) if r.dim in blocks else 0
        r['per_ha'] = round(flt(r.total) / area) if area else None
    totals = {k: sum(flt(r[k]) for r in rows) for k in ('materials', 'labour', 'crews', 'services', 'total')}
    return dict(rows=rows, totals=totals, group_by=group_by, from_date=str(start), to_date=str(end))


def _dim_labels(field, names):
    names = [n for n in names if n]
    if not names:
        return {}
    if field == 'lotus_farm_block':
        return {b.name: b.block_code + (' · ' + b.block_name if b.block_name and b.block_name != b.block_code else '')
                for b in frappe.get_all('Farm Block', filters={'name': ['in', names]}, fields=['name', 'block_code', 'block_name'])}
    if field == 'lotus_farm':
        return {f.name: f.farm_name or f.name for f in frappe.get_all('Farm', filters={'name': ['in', names]}, fields=['name', 'farm_name'])}
    if field == 'lotus_work_type':
        return {w.name: w.work_name or w.name for w in frappe.get_all('Work Type', filters={'name': ['in', names]}, fields=['name', 'work_name'])}
    return {n: n for n in names}


@frappe.whitelist()
def reconciliation(on_date=None):
    """Đối chiếu: each check is (label, ledger, source, difference); a zero difference is reconciled."""
    setup.require_view()
    company = setup.company()
    m = setup.mapping()
    on_date = getdate(on_date or nowdate())
    checks = []
    stock = frappe.db.sql("""select w.account, sum(sle.stock_value_difference) value from `tabStock Ledger Entry` sle join `tabWarehouse` w on w.name=sle.warehouse
        where sle.company=%s and sle.is_cancelled=0 and sle.posting_date<=%s group by w.account""", (company, on_date), as_dict=True)
    default_stock = frappe.get_cached_value('Company', company, 'default_inventory_account')
    by_account = {}
    for s in stock:
        by_account[s.account or default_stock] = by_account.get(s.account or default_stock, 0) + flt(s.value)
    for account, value in sorted(by_account.items()):
        checks.append(dict(label='Giá trị kho (sổ kho) so với tài khoản ' + str(account), ledger=_balance(company, [account], on_date), source=value))
    from lotus_farm.finance.payments import receipts_to_bill
    checks.append(dict(label='Hàng về chưa có hóa đơn so với phiếu nhận chưa lập hóa đơn', ledger=-_balance(company, [m['received_not_billed']], on_date),
                       source=sum(flt(r['to_bill']) for r in receipts_to_bill())))
    outstanding = flt(frappe.db.sql("""select sum(outstanding_amount) from `tabPurchase Invoice` where company=%s and docstatus=1""", company)[0][0])
    checks.append(dict(label='Phải trả người bán so với hóa đơn còn nợ', ledger=-_balance(company, [m['payable_supplier']], on_date), source=outstanding))
    for p in frappe.get_all(posting.POSTING, filters={'source_doctype': 'Lotus Timekeeping Period', 'purpose': 'Payroll', 'state': 'Posted'},
                            fields=['source_name', 'voucher_name', 'amount']):
        snap = json.loads(frappe.db.get_value('Lotus Timekeeping Period', p.source_name, 'snapshot') or '{}')
        source = sum(int(round(r.get('gross') or 0)) + int(round(r.get('employer_insurance') or 0)) for r in snap.get('rows') or []) \
            + sum(int(round(c.get('amount') or 0)) for c in snap.get('crews') or [])
        posted = flt(frappe.db.get_value('Journal Entry', p.voucher_name, 'total_debit'))
        checks.append(dict(label='Bảng lương %s so với bút toán %s' % (p.source_name, p.voucher_name), ledger=posted, source=source))
    for c in checks:
        c['difference'] = round(flt(c['ledger']) - flt(c['source']))
        c['ok'] = abs(c['difference']) < 1
    return dict(checks=checks, on_date=str(on_date))


@frappe.whitelist()
def export(kind, from_date=None, to_date=None, group_by='lotus_farm_block', account=None):
    """The report on screen as .xlsx."""
    setup.require_view()
    from openpyxl import Workbook
    from openpyxl.styles import Font
    book = Workbook()
    ws = book.active
    if kind == 'trial_balance':
        data = trial_balance(from_date, to_date)
        ws.title = 'Cân đối phát sinh'
        ws.append(['Số TK', 'Tên tài khoản', 'Dư Nợ đầu kỳ', 'Dư Có đầu kỳ', 'Phát sinh Nợ', 'Phát sinh Có', 'Dư Nợ cuối kỳ', 'Dư Có cuối kỳ'])
        for r in data['rows']:
            ws.append([r['number'], r['name'], r['opening_debit'], r['opening_credit'], r['debit'], r['credit'], r['closing_debit'], r['closing_credit']])
        t = data['totals']
        ws.append(['', 'Tổng cộng', t['opening_debit'], t['opening_credit'], t['debit'], t['credit'], t['closing_debit'], t['closing_credit']])
    elif kind == 'costs':
        data = costs(from_date, to_date, group_by)
        ws.title = 'Chi phí theo ' + dict(COST_GROUPS)[group_by].lower()
        ws.append([dict(COST_GROUPS)[group_by], 'Vật tư', 'Nhân công', 'Khoán', 'Dịch vụ', 'Tổng', 'Chi phí / ha'])
        for r in data['rows']:
            ws.append([r['label'], r['materials'], r['labour'], r['crews'], r['services'], r['total'], r['per_ha']])
    elif kind == 'ledger':
        data = ledger(account, from_date, to_date)
        ws.title = 'Sổ chi tiết'
        ws.append(['Ngày', 'Chứng từ', 'Số', 'Đối tượng', 'Diễn giải', 'Nợ', 'Có', 'Số dư'])
        ws.append(['', '', '', '', 'Số dư đầu kỳ', '', '', data['opening']])
        for ln in data['lines']:
            ws.append([ln['posting_date'], ln['voucher_type'], ln['voucher_no'], ln.get('party') or '', ln.get('remarks') or '', ln['debit'], ln['credit'], ln['balance']])
    elif kind == 'payables':
        data = payables(to_date)
        ws.title = 'Công nợ phải trả'
        ws.append(['Nhà cung cấp', 'Số hóa đơn', 'Ngày hóa đơn', 'Hạn trả', 'Tổng tiền', 'Còn nợ', 'Tuổi nợ'])
        for i in data['invoices']:
            ws.append([i['supplier_name'], i['bill_no'], i['bill_date'], i['due_date'], i['grand_total'], i['outstanding_amount'], i['aging']])
    else:
        frappe.throw('Loại báo cáo không hợp lệ.')
    for cell in ws[1]:
        cell.font = Font(bold=True)
    ws.freeze_panes = 'A2'
    out = BytesIO()
    book.save(out)
    frappe.local.response.filename = 'ke-toan-%s.xlsx' % kind
    frappe.local.response.filecontent = out.getvalue()
    frappe.local.response.type = 'download'


@frappe.whitelist()
def lookups():
    """Suppliers, farms, lots and work types for the finance forms."""
    setup.require_view()
    return dict(suppliers=frappe.get_all('Supplier', filters={'disabled': 0}, fields=['name', 'supplier_name'], order_by='supplier_name', limit_page_length=0),
                farms=frappe.get_all('Farm', fields=['name', 'farm_name'], order_by='name', limit_page_length=0),
                blocks=frappe.get_all('Farm Block', filters={'active': 1}, fields=['name', 'block_code', 'block_name', 'farm'], order_by='farm, block_code', limit_page_length=0),
                work_types=frappe.get_all('Work Type', filters={'active': 1}, fields=['name', 'work_name'], order_by='work_name', limit_page_length=0),
                accounts=frappe.get_all('Account', filters={'company': setup.company(), 'is_group': 0, 'disabled': 0},
                                        fields=['name', 'account_number', 'account_name'], order_by='account_number, name', limit_page_length=0))
