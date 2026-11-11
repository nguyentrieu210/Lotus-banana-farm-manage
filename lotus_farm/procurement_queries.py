"""Permission-scoped purchase inquiry APIs, separate from posting permissions."""
import frappe
from frappe.utils import flt, getdate, nowdate
from lotus_farm.procurement import access, document
from lotus_farm.procurement_masters import financial_access, page_args, text

STATUS = {0: 'Nháp / chờ ký', 1: 'Đã ghi sổ', 2: 'Đã hủy'}


def require_finance(company):
    access(company)
    if not financial_access(company):
        frappe.throw('Không có quyền xem tài chính mua hàng.', frappe.PermissionError)


def filters_for(company, supplier=None, state=None, from_date=None, to_date=None):
    filters={'company': company}
    if supplier:
        frappe.get_doc('Supplier', supplier).check_permission('read')
        filters['supplier']=supplier
    if state in ('0','1','2',0,1,2):
        filters['docstatus']=int(state)
    if from_date and to_date:
        if getdate(from_date)>getdate(to_date):
            frappe.throw('Từ ngày không được sau đến ngày.')
        filters['posting_date']=['between', [from_date, to_date]]
    elif from_date:
        filters['posting_date']=['>=', from_date]
    elif to_date:
        filters['posting_date']=['<=', to_date]
    return filters


def paged(dt, filters, fields, search, start, length, search_fields):
    if not frappe.has_permission(dt, 'read'):
        frappe.throw('Không có quyền xem '+dt, frappe.PermissionError)
    term=text(search)
    ors=[[dt, f, 'like', '%'+term+'%'] for f in search_fields] if term else None
    rows=frappe.get_list(dt, filters=filters, or_filters=ors, fields=fields,
                         order_by='posting_date desc, name desc', start=start, page_length=length+1)
    total=frappe.get_list(dt, filters=filters, or_filters=ors, fields=[{'COUNT':'name','as':'total'}])[0].total
    return rows[:length], total, len(rows)>length


@frappe.whitelist()
def invoices(company, supplier=None, search=None, state=None, from_date=None, to_date=None, start=0, page_length=50):
    require_finance(company)
    start,length=page_args(start,page_length)
    rows,total,more=paged('Purchase Invoice', filters_for(company,supplier,state,from_date,to_date),
        ['name','supplier','supplier_name','posting_date as date','bill_no','bill_date','due_date',
         'base_grand_total as amount','outstanding_amount','docstatus','is_return','return_against'],
        search,start,length,['name','supplier','supplier_name','bill_no'])
    for r in rows:
        r.status=STATUS[r.docstatus]; r.doctype='Purchase Invoice'
    return dict(rows=rows,total_count=total,has_more=more)


@frappe.whitelist()
def invoice(company, name):
    require_finance(company)
    d=document('Purchase Invoice',name,company)
    return dict(name=d.name,doctype=d.doctype,modified=str(d.modified),supplier=d.supplier,
        date=str(d.posting_date),bill_no=d.bill_no,bill_date=str(d.bill_date),due_date=str(d.due_date),
        amount=flt(d.base_grand_total),outstanding_amount=flt(d.outstanding_amount),docstatus=d.docstatus,
        is_return=d.is_return,return_against=d.return_against,can_submit=d.has_permission('submit'),
        items=[dict(line=r.name,item=r.item_code,item_name=r.item_name,qty=flt(r.qty),uom=r.uom,
            rate=flt(r.rate),amount=flt(r.amount),vat_code=r.get('lotus_line_vat'),freight=flt(r.get('lotus_line_freight')),
            order=r.purchase_order,receipt=r.purchase_receipt,kind=r.get('lotus_purchase_kind')) for r in d.items],
        taxes=[dict(description=r.description,amount=flt(r.tax_amount)) for r in d.taxes])


@frappe.whitelist()
def payments(company, supplier=None, search=None, state=None, from_date=None, to_date=None, start=0, page_length=50):
    require_finance(company)
    start,length=page_args(start,page_length)
    entries=[]; total=0
    for dt in ('Payment Entry','Journal Entry'):
        if not frappe.has_permission(dt,'read'):
            continue
        f=filters_for(company,None,state,from_date,to_date)
        if dt=='Payment Entry':
            f.update(party_type='Supplier')
            if supplier: f['party']=supplier
            fields=['name','posting_date as date','party as supplier','paid_amount as amount','payment_type','docstatus']
            search_fields=['name','party','reference_no']
        else:
            f['lotus_payment_kind']=['in',['PurchaseFunding','PurchaseReimbursement']]
            if supplier:
                refs=frappe.get_list('Lotus Purchase Funding',filters={'company':company,'supplier':supplier},pluck='name',limit_page_length=0)
                f['lotus_purchase_funding']=['in',refs or ['']]
            fields=['name','posting_date as date','total_debit as amount','docstatus','lotus_payment_kind','lotus_purchase_funding']
            search_fields=['name','cheque_no']
        found,count,_=paged(dt,f,fields,search,0,start+length,search_fields)
        total+=count
        for r in found:
            r.doctype=dt; r.status=STATUS[r.docstatus]
            r.kind=('Hoàn tiền từ NCC' if r.payment_type=='Receive' else 'Trả / tạm ứng NCC') if dt=='Payment Entry' else ('Cá nhân chi hộ' if r.lotus_payment_kind=='PurchaseFunding' else 'Hoàn ứng')
            if dt=='Journal Entry':
                r.supplier=frappe.db.get_value('Lotus Purchase Funding',r.lotus_purchase_funding,'supplier')
            entries.append(r)
    # Deleted drafts retain their native accounting-posting audit record.
    from lotus_farm.finance import posting
    if state in (None,'','2',2):
        dt='Lotus Purchase Funding'
        if frappe.has_permission(dt,'read'):
            f=filters_for(company,supplier,None,from_date,to_date);f['cancelled']=1
            found,count,_=paged(dt,f,['name','posting_date as date','supplier','amount','evidence','classification'],search,0,start+length,['name','supplier','external_reference'])
            total+=count
            for r in found:
                r.update(doctype=dt,status='Đã hủy',docstatus=2,kind='Chi hộ đã hủy',audit_only=1)
                entries.append(r)
        f=filters_for(company,None,None,from_date,to_date); f.update(state='Reversed',purpose='Supplier Payment')
        if frappe.has_permission(posting.POSTING,'read'):
            for audit in frappe.get_list(posting.POSTING,filters=f,fields=['name','voucher_type','voucher_name','posting_date','amount','source_hash','reason'],limit_page_length=0):
                # Native naming series may reuse a deleted draft's number.
                # Keep the cancelled attempt under its immutable posting ID.
                if frappe.db.get_value(audit.voucher_type,audit.voucher_name,'docstatus')==2: continue
                party=frappe.db.get_value('Purchase Invoice',audit.source_hash,'supplier') or frappe.db.get_value('Purchase Order',audit.source_hash,'supplier')
                if supplier and supplier!=party or search and text(search).casefold() not in (audit.voucher_name+' '+(party or '')).casefold(): continue
                entries.append(dict(name=audit.name,voucher_name=audit.voucher_name,doctype=audit.voucher_type,date=str(audit.posting_date),amount=flt(audit.amount),
                    supplier=party,kind='Phiếu đã hủy',status='Đã hủy',docstatus=2,audit_only=1,reason=audit.reason)); total+=1
    entries.sort(key=lambda r:(str(r['date']),r['name']),reverse=True)
    return dict(rows=entries[start:start+length],total_count=total,has_more=total>start+length)


@frappe.whitelist()
def payables(company, as_of=None, supplier=None, search=None, start=0, page_length=50):
    require_finance(company)
    as_of=getdate(as_of or nowdate())
    # Use the same dated Payment Ledger Entry basis as procurement_reports.
    from lotus_farm.finance import setup
    account=setup.mapping().get('payable_supplier')
    if not account:
        frappe.throw('Chưa cấu hình tài khoản phải trả NCC.')
    suppliers=frappe.get_list('Supplier',filters={'name':supplier} if supplier else {},fields=['name','supplier_name'],limit_page_length=0)
    names={r.name:r.supplier_name for r in suppliers}
    ledger=frappe.db.sql('''select party supplier, against_voucher_type doctype, against_voucher_no name, sum(amount) balance
        from `tabPayment Ledger Entry` where company=%s and account=%s and party_type='Supplier'
        and posting_date<=%s and delinked=0 group by party,against_voucher_type,against_voucher_no''',(company,account,as_of),as_dict=True)
    from lotus_farm import procurement_rules
    rows=[];everything=[]
    for r in ledger:
        if r.supplier not in names or abs(flt(r.balance))<.000001: continue
        r.supplier_name=names[r.supplier]; r.amount=flt(r.balance)
        r.date=''; r.due_date=''; r.bill_no=''; r.overdue_days=0
        if r.doctype=='Purchase Invoice':
            inv=frappe.db.get_value('Purchase Invoice',r.name,['posting_date','due_date','bill_no'],as_dict=True)
            if inv:
                r.date=str(inv.posting_date); r.due_date=str(inv.due_date or '')
                r.bill_no=inv.bill_no; r.overdue_days=max(0,(as_of-getdate(inv.due_date)).days) if inv.due_date and r.balance>0 else 0
        r.status='Quá hạn' if r.overdue_days else 'Tạm ứng / dư trả' if r.balance<0 else 'Còn phải trả'
        r.bucket=procurement_rules.aging_bucket(r.due_date or None,as_of) if r.balance>0 else 'advance'
        r.due_soon=bool(r.balance>0 and procurement_rules.due_within(r.due_date or None,as_of,7))
        everything.append(r)
        if search and text(search).casefold() not in ' '.join(str(x or '') for x in [r.name,r.supplier_name,r.bill_no]).casefold(): continue
        rows.append(r)
    rows.sort(key=lambda r:(-r.overdue_days,r.supplier_name,r.name))
    start,length=page_args(start,page_length)
    # Spec 003, FR-057/FR-058: aging by due date on the closing date, what falls due in 7 days, goods received but
    # not invoiced, per supplier — over every open amount, whatever page or search is shown.
    owed=[r for r in everything if r.balance>0]
    waiting=unbilled(company,as_of,supplier)
    per={}
    for r in everything:
        s=per.setdefault(r.supplier,dict(supplier=r.supplier,supplier_name=r.supplier_name,invoiced=0.0,advance=0.0,net=0.0,due_7d=0.0,unbilled=0.0,
                                         claim=0.0,aging={k:0.0 for k in procurement_rules.AGING_BUCKETS}))
        s['net']+=r.balance
        if r.balance>0:
            s['invoiced']+=r.balance;s['aging'][r.bucket]+=r.balance
            if r.due_soon:s['due_7d']+=r.balance
        else:s['advance']-=r.balance
    # Goods still waiting for their invoice and claims on the supplier (returned after the invoice) are shown apart.
    for name in set(waiting['waiting'])|set(waiting['claims']):
        if name not in names:continue
        s=per.setdefault(name,dict(supplier=name,supplier_name=names[name],invoiced=0.0,advance=0.0,net=0.0,due_7d=0.0,unbilled=0.0,
                                   claim=0.0,aging={k:0.0 for k in procurement_rules.AGING_BUCKETS}))
        s['unbilled']=waiting['waiting'].get(name,0.0);s['claim']=waiting['claims'].get(name,0.0)
    ledger_balance=-flt(frappe.db.sql('''select sum(debit-credit) from `tabGL Entry` where company=%s and account=%s and is_cancelled=0
        and posting_date<=%s'''+(' and party=%s' if supplier else ''),(company,account,as_of,*([supplier] if supplier else [])))[0][0])
    return dict(rows=rows[start:start+length],total_count=len(rows),has_more=len(rows)>start+length,as_of=str(as_of),
                owed=sum(max(0,r.balance) for r in rows),advance=-sum(min(0,r.balance) for r in rows),
                net=sum(r.balance for r in rows),overdue=sum(r.balance for r in rows if r.overdue_days),
                aging=procurement_rules.age([dict(amount=r.balance,due_date=r.due_date or None) for r in owed],as_of),
                aging_labels=procurement_rules.AGING_LABELS,due_7d=sum(r.balance for r in owed if r.due_soon),
                suppliers=sorted(per.values(),key=lambda s:(-s['net']-s['unbilled'],s['supplier_name'])),
                unbilled=waiting['total'],unbilled_waiting=sum(waiting['waiting'].values()),unbilled_claims=sum(waiting['claims'].values()),
                unbilled_ledger=waiting['ledger'],unbilled_matches=abs(waiting['total']-waiting['ledger'])<1 if not supplier else None,
                ledger_balance=ledger_balance,ledger_matches=abs(ledger_balance-sum(r.balance for r in everything))<1)


@frappe.whitelist()
def supplier_history(company, supplier):
    access(company)
    frappe.get_doc('Supplier',supplier).check_permission('read')
    result={}
    for view,dt,datefield in [('quotes','Supplier Quotation','transaction_date'),('orders','Purchase Order','transaction_date'),('receipts','Purchase Receipt','posting_date')]:
        result[view]=frappe.get_list(dt,filters={'company':company,'supplier':supplier},fields=['name',datefield+' as date','docstatus'],order_by=datefield+' desc',limit_page_length=10) if frappe.has_permission(dt,'read') else []
    if financial_access(company):
        result['invoices']=invoices(company,supplier=supplier,page_length=10)['rows'] if frappe.has_permission('Purchase Invoice','read') else []
        result['payments']=payments(company,supplier=supplier,page_length=10)['rows']
        result['payables']=payables(company,supplier=supplier,page_length=10)
    return result


def unbilled(company, as_of, supplier=None):
    """Hàng đã nhận, chưa có hóa đơn trên ngày chốt (spec 003, FR-057): receipts of orders and Mua nhanh receipts without
    an invoice by that date. `ledger` is what the books hold on 3388 + 33881 for the same date; the two agree when nothing
    was posted there by hand.

    A receipt line counts with what the receipt itself credited for the quantity still waiting (nhận − trả − đã có hóa
    đơn): the net amount of goods and assets, plus for a household business their VAT (33881) and their own freight
    (3388). A service line posts nothing there: its VAT and freight are a cost of the line (procurement._line_costs).
    The quantity waiting is negative when more was invoiced than kept (goods returned after the invoice): that is the
    claim on the supplier until the credit note, and it counts negative.
    Invoice differences are posted by finance.invoice_cost at the receipt's own date: those of invoices dated after the
    closing date, and the receipt's split vouchers (freight per line, differences carried by returns), are added, so the
    two agree on any date."""
    from lotus_farm.finance import rules as finance_rules, setup
    as_of = getdate(as_of)
    household = setup.vat_in_cost()
    extra = ' and pr.supplier=%(supplier)s' if supplier else ''
    args = dict(company=company, day=as_of, supplier=supplier)
    lines = frappe.db.sql('''select pr.name receipt, pr.supplier, pr.posting_date day, pr.conversion_rate, pri.name line, pri.qty,
            pri.base_net_amount net, pri.lotus_line_vat vat_code, pri.lotus_line_freight freight,
            (ifnull(it.is_stock_item, 0)=1 or ifnull(pri.is_fixed_asset, 0)=1) capital
        from `tabPurchase Receipt Item` pri join `tabPurchase Receipt` pr on pr.name=pri.parent left join `tabItem` it on it.name=pri.item_code
        where pr.docstatus=1 and pr.is_return=0 and pr.company=%(company)s and pr.posting_date<=%(day)s''' + extra, args, as_dict=True)
    for l in lines:
        credited = flt(l.net) if l.capital else 0.0
        if household and l.capital:
            try:
                credited += flt(l.net) * finance_rules.vat_rate(l.vat_code or 'KCT', l.day)
            except ValueError:
                pass
            credited += flt(l.freight) * (flt(l.conversion_rate) or 1)
        l.unit = credited / flt(l.qty) if flt(l.qty) else 0.0
    names = [l.line for l in lines]
    billed, returned = {}, {}
    if names:
        for row in frappe.db.sql('''select pii.pr_detail line, sum(pii.qty) qty from `tabPurchase Invoice Item` pii
            join `tabPurchase Invoice` pi on pi.name=pii.parent where pi.docstatus=1 and pi.posting_date<=%s and pii.pr_detail in %s
            group by pii.pr_detail''', (as_of, tuple(names)), as_dict=True):
            billed[row.line] = flt(row.qty)
        for row in frappe.db.sql('''select pri.purchase_receipt_item line, sum(abs(pri.qty)) qty from `tabPurchase Receipt Item` pri
            join `tabPurchase Receipt` pr on pr.name=pri.parent where pr.docstatus=1 and pr.is_return=1 and pr.posting_date<=%s
            and pri.purchase_receipt_item in %s group by pri.purchase_receipt_item''', (as_of, tuple(names)), as_dict=True):
            returned[row.line] = flt(row.qty)
    by_supplier, rows = {}, []
    for l in lines:
        left = flt(l.qty) - returned.get(l.line, 0) - billed.get(l.line, 0)
        if abs(left) <= 0.000001:
            continue
        amount = left * flt(l.unit)
        if abs(amount) < 0.5:
            continue
        by_supplier[l.supplier] = by_supplier.get(l.supplier, 0) + amount
        rows.append(dict(doctype='Purchase Receipt', name=l.receipt, supplier=l.supplier, amount=amount, mua_nhanh=False))
    meta = frappe.get_meta('Landed Cost Voucher') if frappe.db.exists('DocType', 'Landed Cost Voucher') else None
    if meta and meta.has_field('lotus_purchase_invoice') and meta.has_field('lotus_cost_receipt'):
        for row in frappe.db.sql('''select pr.supplier, if(ifnull(pr.return_against, '')='', pr.name, pr.return_against) receipt,
                    sum(i.applicable_charges) amount
                from `tabLanded Cost Item` i join `tabLanded Cost Voucher` v on v.name=i.parent
                join `tabPurchase Receipt` pr on pr.name=i.receipt_document
                where v.docstatus=1 and v.company=%(company)s and pr.posting_date<=%(day)s
                  and (ifnull(v.lotus_cost_receipt, '')!='' or (ifnull(v.lotus_purchase_invoice, '')!='' and v.posting_date>%(day)s))''' + extra + '''
                group by pr.supplier, if(ifnull(pr.return_against, '')='', pr.name, pr.return_against)''', args, as_dict=True):
            if abs(flt(row.amount)) < 0.5:
                continue
            by_supplier[row.supplier] = by_supplier.get(row.supplier, 0) + flt(row.amount)
            rows.append(dict(doctype='Purchase Receipt', name=row.receipt, supplier=row.supplier, amount=flt(row.amount), mua_nhanh=False))
    if frappe.get_meta('Stock Entry').has_field('lotus_purchase_invoice'):
        quick = frappe.db.sql('''select se.name, se.lotus_supplier supplier, se.total_incoming_value value, se.total_additional_costs costs,
                se.lotus_purchase_invoice invoice from `tabStock Entry` se
            where se.docstatus=1 and se.company=%(company)s and se.stock_entry_type='Material Receipt' and se.lotus_receipt_reason='Purchase'
            and se.posting_date<=%(day)s''' + (' and se.lotus_supplier=%(supplier)s' if supplier else ''), args, as_dict=True)
        invoiced = {r.name: getdate(r.posting_date) for r in frappe.get_all('Purchase Invoice', filters={'name': ['in', [q.invoice for q in quick if q.invoice] or ['']], 'docstatus': 1},
                                                                           fields=['name', 'posting_date'])}
        # A Mua nhanh price correction (finance.stock, Stock Reconciliation on 3388) waits with its entry until the
        # invoice, which clears both (third review, 11/11/2026).
        corrections = {}
        if quick and frappe.get_meta('Stock Reconciliation').has_field('lotus_client_key'):
            from lotus_farm.finance.payments import _CORRECTION_KEY
            for c in frappe.get_all('Stock Reconciliation', filters={'company': company, 'docstatus': 1, 'purpose': 'Stock Reconciliation',
                                                                      'lotus_client_key': ['like', _CORRECTION_KEY + '%'], 'posting_date': ['<=', as_of],
                                                                      'expense_account': setup.mapping().get('received_not_billed')},
                                    fields=['lotus_client_key', 'difference_amount'], limit_page_length=0):
                origin = c.lotus_client_key[len(_CORRECTION_KEY):].split(':v', 1)[0]
                corrections[origin] = corrections.get(origin, 0.0) + flt(c.difference_amount)
        for q in quick:
            if q.invoice and q.invoice in invoiced and invoiced[q.invoice] <= as_of:
                continue
            amount = flt(q.value) - flt(q.costs) + corrections.get(q.name, 0.0)
            by_supplier[q.supplier] = by_supplier.get(q.supplier, 0) + amount
            rows.append(dict(doctype='Stock Entry', name=q.name, supplier=q.supplier, amount=amount, mua_nhanh=True))
    accounts = [a for a in (setup.mapping().get('received_not_billed'), setup.valuation_tax_account(company)) if a]
    ledger = -flt(frappe.db.sql('''select sum(debit-credit) from `tabGL Entry` where company=%s and account in %s and is_cancelled=0
        and posting_date<=%s''', (company, tuple(accounts), as_of))[0][0]) if accounts else 0.0
    merged = {}
    for r in rows:
        key = (r['doctype'], r['name'])
        if key in merged:
            merged[key]['amount'] += r['amount']
        else:
            merged[key] = dict(r)
    # Per supplier, goods still waiting and claims (goods sent back after their invoice, owed back until the credit note)
    # are told apart: netted together, a claim hides behind other goods waiting (third review, 11/11/2026).
    waits, claims = {}, {}
    for r in merged.values():
        if r['amount'] > 0.5:
            waits[r['supplier']] = waits.get(r['supplier'], 0) + r['amount']
        elif r['amount'] < -0.5:
            claims[r['supplier']] = claims.get(r['supplier'], 0) - r['amount']
    return dict(total=sum(by_supplier.values()), by_supplier=by_supplier, waiting=waits, claims=claims, rows=list(merged.values()),
                ledger=ledger)


@frappe.whitelist()
def due_soon(company, as_of=None, days=7):
    """Các khoản đến hạn trong `days` ngày tới sau ngày chốt (chưa quá hạn), gần hạn nhất trước."""
    from lotus_farm import procurement_rules
    day = getdate(as_of or nowdate())
    found = payables(company, as_of=day, page_length=10000)['rows']
    rows = [r for r in found if r.balance > 0 and procurement_rules.due_within(r.due_date or None, day, days)]
    rows.sort(key=lambda r: (r.due_date, r.supplier_name))
    return dict(rows=rows, total=sum(r.balance for r in rows), as_of=str(day), days=frappe.utils.cint(days))


STATEMENT_KINDS = dict(invoice='Hóa đơn', credit='Điều chỉnh / trả hàng', payment='Phiếu chi', advance='Tạm ứng', refund='NCC hoàn tiền',
                       funding='Chi hộ', journal='Bút toán')


def _statement_kind(row):
    if row.voucher_type == 'Purchase Invoice':
        return 'credit' if frappe.db.get_value('Purchase Invoice', row.voucher_no, 'is_return') else 'invoice'
    if row.voucher_type == 'Payment Entry':
        if frappe.db.get_value('Payment Entry', row.voucher_no, 'payment_type') == 'Receive':
            return 'refund'
        return 'payment' if row.settles else 'advance'
    if row.voucher_type == 'Journal Entry':
        return 'funding' if frappe.db.get_value('Journal Entry', row.voucher_no, 'lotus_purchase_funding') else 'journal'
    return 'journal'


@frappe.whitelist()
def supplier_statement(company, supplier, from_date=None, to_date=None):
    """Sổ chi tiết công nợ một nhà cung cấp (spec 003, FR-059): số đầu kỳ, từng chứng từ làm tăng (Có) hoặc giảm (Nợ)
    khoản phải trả, số cuối kỳ. Số dương là còn phải trả; số âm là NCC đang giữ tiền tạm ứng."""
    require_finance(company)
    from lotus_farm.finance import setup
    frappe.get_doc('Supplier', supplier).check_permission('read')
    account = setup.mapping().get('payable_supplier')
    end = getdate(to_date or nowdate())
    start = getdate(from_date) if from_date else frappe.utils.get_first_day(end)
    if start > end:
        frappe.throw('Khoảng ngày không hợp lệ.')
    base = (company, account, supplier)
    opening = flt(frappe.db.sql('''select sum(amount) from `tabPayment Ledger Entry` where company=%s and account=%s and party_type='Supplier'
        and party=%s and delinked=0 and posting_date<%s''', (*base, start))[0][0])
    moves = frappe.db.sql('''select voucher_type, voucher_no, posting_date, sum(amount) amount,
            max(case when against_voucher_type='Purchase Invoice' then 1 else 0 end) settles
        from `tabPayment Ledger Entry` where company=%s and account=%s and party_type='Supplier' and party=%s and delinked=0
        and posting_date between %s and %s group by voucher_type, voucher_no, posting_date
        order by posting_date, min(creation), voucher_no''', (*base, start, end), as_dict=True)
    balance, lines = opening, []
    for row in moves:
        if abs(flt(row.amount)) < .000001:
            continue
        kind = _statement_kind(row)
        balance += flt(row.amount)
        bill = frappe.db.get_value('Purchase Invoice', row.voucher_no, 'bill_no') if row.voucher_type == 'Purchase Invoice' else ''
        lines.append(dict(doctype=row.voucher_type, name=row.voucher_no, date=str(row.posting_date), kind=kind, kind_label=STATEMENT_KINDS[kind],
                          bill_no=bill or '', credit=max(0, flt(row.amount)), debit=max(0, -flt(row.amount)), balance=balance))
    ledger = -flt(frappe.db.sql('''select sum(debit-credit) from `tabGL Entry` where company=%s and account=%s and party_type='Supplier'
        and party=%s and is_cancelled=0 and posting_date<=%s''', (*base, end))[0][0])
    from urllib.parse import urlencode
    return dict(supplier=supplier, supplier_name=frappe.get_cached_value('Supplier', supplier, 'supplier_name') or supplier,
                from_date=str(start), to_date=str(end), opening=opening, lines=lines, closing=balance,
                debit=sum(l['debit'] for l in lines), credit=sum(l['credit'] for l in lines),
                ledger_balance=ledger, ledger_matches=abs(ledger - balance) < 1,
                print_url='/lotus/in-doi-chieu?' + urlencode(dict(supplier=supplier, from_date=str(start), to_date=str(end))))
