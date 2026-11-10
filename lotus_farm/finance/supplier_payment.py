"""Một lõi lập phiếu chi trả nhà cung cấp (spec 003, US6; research R19).

prepare() makes one draft Payment Entry for one supplier — several invoices, advances against orders, and an extra
amount explicitly marked as an advance — then starts the payment_voucher signing chain. The last signature posts it
(finance.payments.sign_payment). procurement.supplier_payment and payments.prepare_supplier_payment are wrappers.
"""
import frappe
from frappe.utils import flt

from lotus_farm import procurement_rules as rules
from lotus_farm.finance import posting, setup

PE = 'Payment Entry'
PI = 'Purchase Invoice'
PO = 'Purchase Order'


def _vnd(value):
    return '{:,.0f}'.format(flt(value)).replace(',', '.')


def _allocations(raw):
    """[{doctype, name, amount}] (older callers send {invoice, amount}); zero amounts are dropped."""
    raw = frappe.parse_json(raw) if isinstance(raw, str) else (raw or [])
    out = []
    for row in raw:
        if not isinstance(row, dict):
            frappe.throw('Dòng phân bổ không hợp lệ.')
        doctype = row.get('doctype') or (PI if row.get('invoice') else None)
        name = row.get('name') or row.get('invoice')
        if doctype not in (PI, PO) or not name:
            frappe.throw('Phiếu chi chỉ trả cho hóa đơn hoặc tạm ứng theo đơn mua.')
        if flt(row.get('amount')) > 0:
            out.append(dict(doctype=doctype, name=str(name), amount=flt(row.get('amount'))))
    if len({(a['doctype'], a['name']) for a in out}) != len(out):
        frappe.throw('Mỗi hóa đơn hoặc đơn mua chỉ xuất hiện một lần trên phiếu chi.')
    return out


@frappe.whitelist(methods=['POST'])
def prepare(supplier=None, allocations=None, advance_amount=0, mode='bank', reference_no=None, reference_date=None, files=None,
            signers=None, client_key=None, posting_date=None, remark=None):
    """Draft payment voucher sent for signatures. Nothing is paid above what is owed after the vouchers already
    waiting for signatures, except the part given as advance_amount (tạm ứng)."""
    setup.require_post()
    setup.require_enabled()
    from lotus_farm.controls import lock
    from lotus_farm.finance import payments
    from lotus_farm.procurement import document, idempotent
    from lotus_farm.purchase_funding import _remaining_source
    company = setup.company()
    rows = _allocations(allocations)
    advance = flt(advance_amount)
    if advance < 0 or not rows and advance <= 0:
        frappe.throw('Chọn hóa đơn và số tiền trả, hoặc nhập số tiền tạm ứng.')
    if mode not in ('cash', 'bank'):
        frappe.throw('Hình thức chi không hợp lệ.')
    if mode == 'bank' and not str(reference_no or '').strip():
        frappe.throw('Chuyển khoản cần số ủy nhiệm chi / số giao dịch ngân hàng.')
    posting_date = posting_date or frappe.utils.nowdate()
    files = frappe.parse_json(files) if isinstance(files, str) else (files or [])
    payload = [supplier, sorted((a['doctype'], a['name'], a['amount']) for a in rows), advance, mode, str(posting_date), reference_no]
    token, fingerprint, old = idempotent(PE, client_key or 'auto:' + rules.digest(payload), payload, company)
    if old:
        return dict(voucher=old, doctype=PE, signing=None)
    setup.check_cutover(posting_date)
    posting.check_open(company, posting_date, PE)
    refs, total = [], 0.0
    for a in sorted(rows, key=lambda r: (r['doctype'], r['name'])):
        source = document(a['doctype'], a['name'], company)
        lock(a['doctype'], a['name'])
        source.reload()
        supplier = supplier or source.supplier
        if source.docstatus != 1 or source.supplier != supplier or source.get('is_return'):
            frappe.throw('%s không thuộc nhà cung cấp này hoặc chưa ghi sổ.' % a['name'])
        left = _remaining_source(a['doctype'], a['name'])
        if a['amount'] > left + .5:
            label = (source.get('bill_no') or a['name']) if a['doctype'] == PI else a['name']
            frappe.throw('%s chỉ còn trả được %s đ sau các phiếu đang chờ ký. Phần trả thêm ghi vào ô tạm ứng.' % (label, _vnd(left)))
        if a['doctype'] == PI:
            refs.append(dict(reference_doctype=PI, reference_name=source.name, total_amount=source.grand_total,
                             outstanding_amount=source.outstanding_amount, allocated_amount=a['amount'], due_date=source.due_date))
        else:
            refs.append(dict(reference_doctype=PO, reference_name=source.name, total_amount=source.grand_total,
                             outstanding_amount=flt(source.grand_total) - flt(source.advance_paid), allocated_amount=a['amount']))
        total += a['amount']
    if not supplier or not frappe.db.exists('Supplier', supplier):
        frappe.throw('Chọn nhà cung cấp nhận tiền.')
    total += advance
    m = setup.mapping()
    money = m['bank'] if mode == 'bank' else m['cash']
    currency = frappe.get_cached_value('Company', company, 'default_currency')
    note = str(remark or '').strip() or ('Trả tiền nhà cung cấp' if refs else 'Tạm ứng cho nhà cung cấp')
    if advance and refs:
        note += ' (gồm tạm ứng %s đ)' % _vnd(advance)
    pe = frappe.get_doc(dict(doctype=PE, payment_type='Pay', company=company, posting_date=posting_date, party_type='Supplier', party=supplier,
                             paid_from=money, paid_to=m['payable_supplier'], paid_from_account_currency=currency, paid_to_account_currency=currency,
                             paid_amount=total, received_amount=total, source_exchange_rate=1, target_exchange_rate=1,
                             reference_no=str(reference_no or '').strip() or None,
                             reference_date=reference_date or (posting_date if reference_no else None),
                             mode_of_payment=None, remarks=note[:500], references=refs,
                             lotus_procurement_key=token, lotus_procurement_hash=fingerprint))
    pe.flags.ignore_permissions = True
    pe.insert()
    posting.record(PE, pe.name, 'Supplier Payment', pe, amount=total, source_hash=','.join(a['name'] for a in rows) or 'advance')
    from lotus_farm import stock_attachments
    for url in files:
        stock_attachments.attach_uploaded(pe, url)
    return payments.start_signing(pe, signers)


@frappe.whitelist()
def open_items(supplier):
    """What can be paid to one supplier now: open invoices and approved orders (for an advance), each with the amount
    still payable after the vouchers waiting for signatures."""
    setup.require_view()
    from lotus_farm.purchase_funding import _remaining_source
    company = setup.company()
    items = []
    for r in frappe.get_all(PI, filters={'company': company, 'supplier': supplier, 'docstatus': 1, 'is_return': 0, 'outstanding_amount': ['>', 0.5]},
                            fields=['name', 'bill_no', 'posting_date', 'due_date', 'grand_total', 'outstanding_amount'], order_by='due_date, posting_date'):
        left = _remaining_source(PI, r.name, lock_rows=False)
        items.append(dict(doctype=PI, name=r.name, label=r.bill_no or r.name, date=str(r.posting_date), due_date=str(r.due_date or ''),
                          total=flt(r.grand_total), outstanding=flt(r.outstanding_amount), payable=left, waiting=max(0, flt(r.outstanding_amount) - left)))
    for r in frappe.get_all(PO, filters={'company': company, 'supplier': supplier, 'docstatus': 1, 'status': ['not in', ['Closed', 'Completed', 'Stopped']],
                                         'per_billed': ['<', 99.99]},
                            fields=['name', 'transaction_date', 'grand_total', 'advance_paid'], order_by='transaction_date'):
        left = _remaining_source(PO, r.name, lock_rows=False)
        if left > 0.5:
            items.append(dict(doctype=PO, name=r.name, label='Tạm ứng theo đơn ' + r.name, date=str(r.transaction_date), due_date='',
                              total=flt(r.grand_total), outstanding=flt(r.grand_total) - flt(r.advance_paid), payable=left, waiting=0))
    return dict(supplier=supplier, supplier_name=frappe.get_cached_value('Supplier', supplier, 'supplier_name') or supplier, items=items,
                owed=sum(i['outstanding'] for i in items if i['doctype'] == PI))
