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
    rows=[]
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
        if search and text(search).casefold() not in ' '.join(str(x or '') for x in [r.name,r.supplier_name,r.bill_no]).casefold(): continue
        rows.append(r)
    rows.sort(key=lambda r:(-r.overdue_days,r.supplier_name,r.name))
    start,length=page_args(start,page_length)
    return dict(rows=rows[start:start+length],total_count=len(rows),has_more=len(rows)>start+length,as_of=str(as_of),
                owed=sum(max(0,r.balance) for r in rows),advance=-sum(min(0,r.balance) for r in rows),
                net=sum(r.balance for r in rows),overdue=sum(r.balance for r in rows if r.overdue_days))


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
