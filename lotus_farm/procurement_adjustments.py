"""Native supplier credit notes and explicitly recorded refunds."""
import frappe
from frappe.utils import flt
from lotus_farm.procurement import document, parse, idempotent, apply_line_taxes
from lotus_farm.controls import lock


@frappe.whitelist(methods=['POST'])
def credit_note(company, name, posting_date, quantities, client_key, bill_no=None, bill_date=None):
    from lotus_farm.finance import setup, posting
    from erpnext.controllers.sales_and_purchase_return import make_return_doc
    setup.require_post(); setup.require_enabled()
    if company!=setup.company():
        frappe.throw('Công ty khác cấu hình tài chính.')
    source=document('Purchase Invoice', name, company)
    lock('Company', company); lock('Purchase Invoice',name)
    selected=parse(quantities)
    key,fingerprint,old=idempotent('Purchase Invoice',client_key,['credit',name,posting_date,selected,bill_no,bill_date],company)
    if old: return dict(invoice=old)
    if source.docstatus!=1 or source.is_return or not isinstance(selected,dict) or not selected:
        frappe.throw('Chọn hóa đơn gốc đã ghi sổ và số lượng điều chỉnh.')
    setup.check_cutover(posting_date); posting.check_open(company,posting_date,'Purchase Invoice')
    d=make_return_doc('Purchase Invoice',name)
    kept=[]
    for r in d.items:
        line=r.purchase_invoice_item
        if line not in selected: continue
        qty=flt(selected[line])
        if qty<=0 or qty>abs(flt(r.qty))+.000001:
            frappe.throw('Số điều chỉnh vượt phần chưa trả của hóa đơn.')
        r.qty=-qty
        original=next(x for x in source.items if x.name==line)
        r.lotus_line_freight=-flt(original.get('lotus_line_freight'))*qty/flt(original.qty)
        kept.append(r)
    if {r.purchase_invoice_item for r in kept}!=set(selected):
        frappe.throw('Dòng hóa đơn đã thay đổi. Mở lại hóa đơn.')
    d.set('items',kept)
    d.update(dict(posting_date=posting_date,set_posting_time=1,update_stock=0,bill_no=bill_no or source.bill_no,
                  bill_date=bill_date or posting_date,lotus_procurement_key=key,lotus_procurement_hash=fingerprint))
    apply_line_taxes(d); d.insert(); d.submit()
    posting.record('Purchase Invoice',d.name,'Purchase Invoice',d,amount=d.grand_total,source_hash=source.name)
    return dict(invoice=d.name)


@frappe.whitelist(methods=['POST'])
def refund(company, name, amount, mode, posting_date, reference_no, signers, client_key):
    from lotus_farm.finance import setup, posting, payments
    from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
    setup.require_post(); setup.require_enabled()
    if company!=setup.company(): frappe.throw('Công ty khác cấu hình tài chính.')
    source=document('Purchase Invoice',name,company)
    lock('Company',company); lock('Purchase Invoice',name); source.reload()
    key,fingerprint,old=idempotent('Payment Entry',client_key,['refund',name,amount,mode,posting_date,reference_no,signers],company)
    if old: return dict(doctype='Payment Entry',voucher=old)
    if source.docstatus!=1 or not source.is_return or mode not in ('cash','bank') or mode=='bank' and not reference_no:
        frappe.throw('Chọn hóa đơn điều chỉnh và thông tin hoàn tiền hợp lệ.')
    reserved=frappe.db.sql('''select coalesce(sum(abs(r.allocated_amount)),0) from `tabPayment Entry Reference` r
        join `tabPayment Entry` p on p.name=r.parent where p.docstatus=0 and p.company=%s and p.payment_type='Receive'
        and r.reference_doctype='Purchase Invoice' and r.reference_name=%s''',(company,name))[0][0]
    if flt(amount)<=0 or flt(amount)>-flt(source.outstanding_amount)-flt(reserved)+.5:
        frappe.throw('Số hoàn vượt phần NCC còn phải trả sau các phiếu chờ ký.')
    setup.check_cutover(posting_date); posting.check_open(company,posting_date,'Payment Entry')
    d=get_payment_entry('Purchase Invoice',name,party_amount=-flt(amount),bank_account=setup.mapping()[mode],bank_amount=flt(amount))
    if d.payment_type!='Receive': frappe.throw('Chứng từ không tạo được phiếu thu từ NCC.')
    d.update(dict(posting_date=posting_date,reference_no=reference_no or None,reference_date=posting_date if reference_no else None,
                  lotus_procurement_key=key,lotus_procurement_hash=fingerprint))
    d.insert(); posting.record('Payment Entry',d.name,'Supplier Payment',d,amount=-flt(d.paid_amount),source_hash=name)
    return payments.start_signing(d,signers)
