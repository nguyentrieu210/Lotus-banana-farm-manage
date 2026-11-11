"""Tài chính – Kế toán: supplier invoices and payments.

A goods invoice is made from submitted Purchase Receipts (ERPNext's make_purchase_invoice, so the billed
quantity stays in step with the receipt): Nợ hàng về chưa có hóa đơn / Có phải trả người bán. A service
invoice (transport, machine hire…) posts its lines to production overhead services (6277, with farm / lot) or to
administrative services (6427). A payment is a draft Payment Entry allocated to open invoices, signed by the
accountant, the chief accountant and the director; the last signature submits it. Each invoice carries one VAT rate
(data/vat_vn.json): input VAT goes to 1331.
"""
import frappe
from frappe.utils import flt, getdate, nowdate

from lotus_farm.finance import posting, rules, setup

PI, PE = 'Purchase Invoice', 'Payment Entry'


def _json(value):
    return frappe.parse_json(value) if isinstance(value, str) else (value or [])


def _due(bill_date, due_date):
    due = getdate(due_date or bill_date)
    if due < getdate(bill_date):
        frappe.throw('Hạn thanh toán không được trước ngày hóa đơn.')
    return due


def apply_vat(doc, code, on_date, account):
    """One VAT rate per invoice: a tax row on the net total to the input (1331) or output (33311) VAT account; KCT / 0% add none."""
    try:
        rate = rules.vat_rate(code, on_date)
    except ValueError as exc:
        frappe.throw(str(exc))
    if doc.meta.has_field('lotus_vat_code'):
        doc.lotus_vat_code = str(code or 'KCT')
    doc.set('taxes', [])
    doc.taxes_and_charges = None
    if rate:
        row = dict(charge_type='On Net Total', account_head=account, rate=rate * 100, description='Thuế GTGT %s%%' % code,
                   cost_center=frappe.get_cached_value('Company', doc.company, 'cost_center'))
        if doc.doctype == PI:
            row.update(category='Total', add_deduct_tax='Add')
        doc.append('taxes', row)


def _duplicate(supplier, bill_no, series=None, exclude_entry=None, linked_entries=()):
    """A supplier invoice is seller + ký hiệu + số: the same number under another series is another invoice. A record that
    has no series yet is treated as the same invoice (cannot tell them apart). Mua nhanh receipts carrying the invoice count
    too, except those being invoiced now (linked_entries) or the receipt being saved (exclude_entry)."""
    series = str(series or '').strip()
    same = lambda other: not series or not str(other or '').strip() or str(other).strip() == series
    with_series = frappe.get_meta(PI).has_field('lotus_einvoice_series')
    for row in frappe.get_all(PI, filters={'supplier': supplier, 'bill_no': bill_no, 'docstatus': ['<', 2]},
                              fields=['name'] + (['lotus_einvoice_series'] if with_series else [])):
        if same(row.get('lotus_einvoice_series')):
            frappe.throw('Hóa đơn %s%s của nhà cung cấp này đã được nhập (%s).' % (series + ' ' if series else '', bill_no, row.name))
    if frappe.get_meta('Stock Entry').has_field('lotus_einvoice_no'):
        for row in frappe.get_all('Stock Entry', filters={'lotus_supplier': supplier, 'lotus_einvoice_no': bill_no, 'docstatus': ['<', 2],
                                                          'name': ['!=', exclude_entry or '']}, fields=['name', 'lotus_einvoice_series']):
            if row.name not in linked_entries and same(row.lotus_einvoice_series):
                frappe.throw('Hóa đơn %s%s của nhà cung cấp này đã ghi ở phiếu nhập %s.' % (series + ' ' if series else '', bill_no, row.name))


# A posted price-only stock reconciliation adjusts the value of an unbilled
# goods receipt without creating additional stock quantity. Corrections can
# raise OR lower the provisional cost; the 3388 liability changes accordingly.
_CORRECTION_KEY = 'lotus-cost-of-receipt:'


def _receipt_cost_corrections(names):
    if not names:
        return {}
    wanted = {str(name) for name in names}
    corrections = frappe.get_all(
        'Stock Reconciliation',
        filters={'company': setup.company(), 'docstatus': 1, 'purpose': 'Stock Reconciliation',
                 'lotus_client_key': ['like', _CORRECTION_KEY + '%'],
                 'expense_account': setup.mapping()['received_not_billed']},
        fields=['name', 'lotus_client_key', 'difference_amount'], limit_page_length=0,
    )
    values = {}
    for row in corrections:
        origin = row.lotus_client_key[len(_CORRECTION_KEY):].split(':v', 1)[0]
        if origin not in wanted:
            continue
        # More than one price correction would require an explicit review.
        if origin in values:
            frappe.throw('Phiếu nhập %s có nhiều lần bổ sung giá. Kế toán kiểm tra lại.' % origin)
        if abs(flt(row.difference_amount)) < 0.01:
            frappe.throw('Phiếu điều chỉnh giá %s không có chênh lệch giá trị.' % row.name)
        values[origin] = flt(row.difference_amount)
    return values


@frappe.whitelist()
def receipts_to_bill(supplier=None):
    """Submitted receipts not fully invoiced, with their unbilled amount: purchase receipts of orders, and goods bought
    without an order that the warehouse received with reason "Mua ngoài" (Stock Entry, credited to 3388)."""
    setup.require_view()
    filters = {'docstatus': 1, 'company': setup.company(), 'per_billed': ['<', 99.99], 'is_return': 0}
    if supplier:
        filters['supplier'] = supplier
    rows = frappe.get_all('Purchase Receipt', filters=filters, fields=['name', 'supplier', 'supplier_name', 'posting_date', 'grand_total', 'per_billed'],
                          order_by='posting_date, name', limit_page_length=500)
    from erpnext.stock.doctype.purchase_receipt.purchase_receipt import get_invoiced_qty_map
    from lotus_farm.finance.invoice_cost import returned_qty_map
    rejected_billable = frappe.db.get_single_value('Buying Settings', 'bill_for_rejected_quantity_in_purchase_invoice')
    for r in rows:
        r['posting_date'] = str(r.posting_date)
        r['doctype'] = 'Purchase Receipt'
        r['source_type'] = 'Nhận theo đơn mua'
        invoiced, returned = get_invoiced_qty_map(r.name), returned_qty_map(r.name)
        receipt = frappe.get_doc('Purchase Receipt', r.name)
        r['unbilled_items'] = []
        # The amount still to invoice is the receipt total for the quantities waiting (received − returned − invoiced):
        # goods returned are not invoiced (the receipt total still includes them). Each line weighs what it brings to the
        # total, its own VAT and freight included, so a waiting line does not carry other lines' VAT (third review).
        conversion = flt(receipt.conversion_rate) or 1

        def own(line):
            try:
                rate = rules.vat_rate(line.get('lotus_line_vat') or 'KCT', receipt.posting_date)
            except ValueError:
                rate = 0.0
            return abs(flt(line.base_net_amount)) * (1 + rate) + abs(flt(line.get('lotus_line_freight'))) * conversion

        weights = {l.name: own(l) for l in receipt.items}
        weight_total = sum(weights.values())
        qty_total = sum(flt(l.qty) for l in receipt.items)
        to_bill = 0.0
        for line in receipt.items:
            quantity = flt(line.received_qty if rejected_billable else line.qty) - flt(invoiced.get(line.name))
            if not rejected_billable:
                quantity -= max(0, flt(returned.get(line.name)) - flt(line.rejected_qty))
            if quantity > .000001:
                r['unbilled_items'].append(dict(item_name=line.item_name, qty=quantity, uom=line.uom))
                share = weights[line.name] / weight_total if weight_total else (flt(line.qty) / qty_total if qty_total else 0)
                to_bill += flt(r.grand_total) * share * quantity / flt(line.qty) if flt(line.qty) else 0
        r['to_bill'] = round(to_bill)
    if frappe.get_meta('Stock Entry').has_field('lotus_purchase_invoice'):
        se_filters = {'docstatus': 1, 'company': setup.company(), 'stock_entry_type': 'Material Receipt', 'lotus_receipt_reason': 'Purchase',
                      'lotus_purchase_invoice': ['in', ['', None]]}
        if supplier:
            se_filters['lotus_supplier'] = supplier
        names = {s_.name: s_.supplier_name for s_ in frappe.get_all('Supplier', fields=['name', 'supplier_name'], limit_page_length=0)}
        stock_receipts = frappe.get_all('Stock Entry', filters=se_filters,
                                       fields=['name', 'lotus_supplier', 'posting_date', 'total_incoming_value'],
                                       order_by='posting_date, name', limit_page_length=500)
        corrections = _receipt_cost_corrections([r.name for r in stock_receipts])
        for e in stock_receipts:
            amount = flt(e.total_incoming_value) + corrections.get(e.name, 0)
            rows.append(dict(name=e.name, doctype='Stock Entry', supplier=e.lotus_supplier, supplier_name=names.get(e.lotus_supplier, e.lotus_supplier),
                             posting_date=str(e.posting_date), grand_total=amount, per_billed=0, to_bill=round(amount),
                             cost_correction=corrections.get(e.name, 0), source_type='Mua nhanh — không qua đề xuất/đơn',
                             unbilled_items=[dict(item_name=line.item_name, qty=flt(line.qty), uom=line.uom)
                                 for line in frappe.get_doc('Stock Entry', e.name).items]))
    return rows


@frappe.whitelist(methods=['POST'])
def make_goods_invoice(receipts, bill_no, bill_date, due_date=None, posting_date=None, vat_code='KCT'):
    """One supplier invoice for one or more receipts of the same supplier (the unbilled quantities). Lớp bọc của
    finance.supplier_invoice.create: thuế theo từng dòng phiếu nhận; hộ kinh doanh không bao giờ ghi 1331 (sửa B4)."""
    from lotus_farm.finance import supplier_invoice
    result = supplier_invoice.create(receipts=_json(receipts), bill_no=bill_no, bill_date=bill_date, due_date=due_date,
                                     posting_date=posting_date, vat_code=vat_code)
    return dict(invoice=result['invoice'], amount=result['amount'])


def _invoice_stock_entries(names, bill_no, bill_date, due_date=None, posting_date=None, vat_code='KCT'):
    """Invoice for goods received without an order: the stock is already in (Nợ 152 / Có 3388), so the invoice only moves
    3388 to the supplier (Nợ 3388 / Có 331) and does not update stock again."""
    docs = [frappe.get_doc('Stock Entry', n) for n in names]
    for d in docs:
        if d.docstatus != 1 or d.stock_entry_type != 'Material Receipt' or d.get('lotus_receipt_reason') != 'Purchase':
            frappe.throw('Phiếu %s không phải phiếu nhập hàng mua ngoài.' % d.name)
        if d.get('lotus_purchase_invoice'):
            frappe.throw('Phiếu nhập %s đã có hóa đơn %s.' % (d.name, d.lotus_purchase_invoice))
    suppliers = {d.lotus_supplier for d in docs}
    if len(suppliers) != 1 or None in suppliers:
        frappe.throw('Các phiếu nhập phải cùng một nhà cung cấp.')
    supplier = docs[0].lotus_supplier
    series = next((d.get('lotus_einvoice_series') for d in docs if d.get('lotus_einvoice_series')), None)
    _duplicate(supplier, bill_no, series=series, linked_entries=names)
    posting_date = posting_date or bill_date
    setup.check_cutover(posting_date)
    posting.check_open(docs[0].company, posting_date, PI)
    m = setup.mapping()
    cost_center = frappe.get_cached_value('Company', docs[0].company, 'cost_center')
    corrections = _receipt_cost_corrections(names)
    # Lowering a receipt to a documented VAT-inclusive payment total must not
    # cause the accountant to accidentally ADD VAT a second time.
    if any(corrections.get(d.name, 0) < 0 for d in docs) and str(vat_code or '').upper() not in ('KCT', '0'):
        frappe.throw('Phiếu nhận đã điều chỉnh giảm theo số tiền thanh toán gồm VAT. Không được tự cộng VAT lần hai. Đối chiếu hóa đơn hợp lệ và tách thuế trước khi ghi sổ.')
    items = []
    for d in docs:
        extra = corrections.get(d.name, 0)
        if extra and len(d.items) != 1:
            frappe.throw('Phiếu nhập %s được bổ sung giá cho nhiều mặt hàng; cần đối chiếu riêng từng dòng.' % d.name)
        for r in d.items:
            amount = (flt(r.get('basic_amount')) or flt(r.amount)) + extra
            if flt(r.transfer_qty) <= 0:
                frappe.throw('Phiếu nhập %s có số lượng quy đổi không hợp lệ.' % d.name)
            items.append(dict(item_code=r.item_code, item_name=r.item_name, qty=r.transfer_qty,
                              uom=r.stock_uom, stock_uom=r.stock_uom, conversion_factor=1,
                              rate=amount / flt(r.transfer_qty), expense_account=m['received_not_billed'],
                              cost_center=cost_center,
                              description='%s (phiếu nhập %s%s)' % (r.item_name or r.item_code, d.name,
                                  ', bổ sung giá qua kiểm kê' if extra else '')))
    pi = frappe.get_doc(dict(doctype=PI, company=docs[0].company, supplier=supplier, bill_no=bill_no, bill_date=bill_date, due_date=_due(bill_date, due_date),
                             posting_date=posting_date, set_posting_time=1, credit_to=m['payable_supplier'], update_stock=0, items=items))
    # VAT recorded per line on the receipts (Mua nhanh): household mode already has it inside the stock value (no tax row,
    # nothing on 1331); otherwise the exact VAT of the invoice lines goes to input VAT, whatever mix of rates. Older receipts
    # without line VAT keep the single rate chosen here.
    line_vat = sum(flt(r.get('lotus_vat_amount')) for d in docs for r in d.items)
    if any(d.get('lotus_vat_in_cost') for d in docs):
        pi.lotus_vat_code = 'KCT'
    elif line_vat:
        pi.append('taxes', dict(charge_type='Actual', account_head=m['input_vat'], tax_amount=line_vat, description='Thuế GTGT theo hóa đơn',
                                category='Total', add_deduct_tax='Add', cost_center=cost_center))
    else:
        apply_vat(pi, vat_code, bill_date, m['input_vat'])
    if pi.meta.has_field('lotus_einvoice_series'):
        pi.lotus_einvoice_series = series
        pi.lotus_invoice_total = sum(flt(d.get('lotus_invoice_total')) for d in docs) or None
    # Rates per stock unit are rounded to the currency precision (26.571,428625 đ/kg → 26.571,43): the cents that leaves go
    # back to 3388 so the invoice clears exactly what the receipts credited there.
    pi.set_missing_values()
    pi.calculate_taxes_and_totals()
    gap = round(sum(flt(r['rate']) * flt(r['qty']) for r in items) - flt(pi.net_total), 2)
    if abs(gap) >= 0.005:
        pi.append('taxes', dict(charge_type='Actual', account_head=m['received_not_billed'], tax_amount=gap, description='Làm tròn theo phiếu nhập',
                                category='Total', add_deduct_tax='Add', cost_center=cost_center))
    pi.flags.ignore_permissions = True
    pi.insert()
    pi.submit()
    for d in docs:
        d.db_set('lotus_purchase_invoice', pi.name)
    posting.record(PI, pi.name, 'Purchase Invoice', pi, amount=pi.grand_total, source_hash=','.join(names))
    return dict(invoice=pi.name, amount=pi.grand_total)


@frappe.whitelist(methods=['POST'])
def make_service_invoice(supplier, bill_no, bill_date, lines, due_date=None, posting_date=None, vat_code='KCT'):
    """lines: [{description, amount, cost: 'production' | 'admin', lotus_farm, lotus_farm_block, lotus_crop_cycle, lotus_work_type}].
    Lớp bọc của finance.supplier_invoice.create: hộ kinh doanh cộng thuế vào chính khoản chi phí, không ghi 1331."""
    from lotus_farm.finance import supplier_invoice
    result = supplier_invoice.create(supplier=supplier, service_lines=_json(lines), bill_no=bill_no, bill_date=bill_date, due_date=due_date,
                                     posting_date=posting_date, vat_code=vat_code)
    return dict(invoice=result['invoice'], amount=result['amount'])


def _dims(row):
    dims = {f: row.get(f) or None for f in rules.DIM_FIELDS}
    if dims.get('lotus_farm_block') and not dims.get('lotus_farm'):
        dims['lotus_farm'] = frappe.db.get_value('Farm Block', dims['lotus_farm_block'], 'farm')
    if dims.get('lotus_farm_block') and dims.get('lotus_farm') and frappe.db.get_value('Farm Block', dims['lotus_farm_block'], 'farm') != dims['lotus_farm']:
        frappe.throw('Lô %s không thuộc vườn %s.' % (dims['lotus_farm_block'], dims['lotus_farm']))
    return {k: v for k, v in dims.items() if v}


@frappe.whitelist()
def open_invoices(supplier=None):
    setup.require_view()
    filters = {'docstatus': 1, 'company': setup.company(), 'outstanding_amount': ['>', 0.5]}
    if supplier:
        filters['supplier'] = supplier
    today = getdate(nowdate())
    rows = frappe.get_all(PI, filters=filters, fields=['name', 'supplier', 'supplier_name', 'bill_no', 'bill_date', 'posting_date', 'due_date', 'grand_total', 'outstanding_amount'],
                          order_by='due_date, posting_date', limit_page_length=1000)
    for r in rows:
        r['aging'] = rules.aging(getdate(r.due_date) if r.due_date else None, today)
        r['paying'] = flt(frappe.db.sql("""select sum(r.allocated_amount) from `tabPayment Entry Reference` r join `tabPayment Entry` p on p.name=r.parent
            where p.docstatus=0 and r.reference_doctype='Purchase Invoice' and r.reference_name=%s""", r.name)[0][0])
        for f in ('bill_date', 'posting_date', 'due_date'):
            r[f] = str(r[f]) if r[f] else ''
    return rows


@frappe.whitelist(methods=['POST'])
def prepare_supplier_payment(supplier, allocations, mode, posting_date, signers, reference_no=None, reference_date=None, remark=None):
    """allocations: [{invoice, amount}] -> draft Payment Entry sent for signatures (submitted by the last signer).
    Lớp bọc của finance.supplier_payment.prepare."""
    from lotus_farm.finance import supplier_payment as core
    return core.prepare(supplier=supplier, allocations=allocations, mode=mode, posting_date=posting_date, signers=signers,
                        reference_no=reference_no, reference_date=reference_date, remark=remark)


def _vnd(value):
    return format(int(round(value)), ',').replace(',', '.') + ' đ'


# Signing (chain payment_voucher: Kế toán lập → Kế toán trưởng → Giám đốc) ------------------------------

def start_signing(voucher, signers):
    from lotus_farm import signing
    return dict(voucher=voucher.name, doctype=voucher.doctype, signing=signing.start(voucher, signers))


def _voucher(doctype, name):
    if doctype not in (PE, 'Journal Entry'):
        frappe.throw('Chứng từ không phải phiếu chi.')
    doc = frappe.get_doc(doctype, name)
    if doctype == 'Journal Entry' and doc.get('lotus_payment_kind') not in setup.SIGNED_JE_KINDS:
        frappe.throw('Bút toán này không phải phiếu chi.')
    return doc


@frappe.whitelist(methods=['POST'])
def sign_payment(doctype, name):
    """The named signer signs (signing checks the person); the last signature submits the voucher."""
    setup._login()
    from lotus_farm import signing
    doc = _voucher(doctype, name)
    if doc.docstatus != 0:
        frappe.throw('Phiếu chi đã ghi sổ hoặc đã hủy.')
    def post():
        posting.check_open(doc.company, doc.posting_date, doc.doctype)
        doc.flags.ignore_permissions = True
        doc.submit()
        posting.mark_posted(doc)

    status = signing.sign(doc, effect=post)
    return dict(signing=status, docstatus=doc.docstatus)


@frappe.whitelist(methods=['POST'])
def return_payment(doctype, name, reason):
    setup._login()
    from lotus_farm import signing
    return signing.send_back(_voucher(doctype, name), reason)


@frappe.whitelist(methods=['POST'])
def cancel_draft(doctype, name, reason):
    """Drop a payment that was not signed yet (the posting link is freed)."""
    setup.require_post()
    doc = _voucher(doctype, name)
    if doc.docstatus != 0:
        frappe.throw('Chỉ hủy được phiếu chi chưa ghi sổ. Phiếu đã ghi sổ thì Kế toán trưởng đảo bút toán.')
    if doctype=='Journal Entry' and doc.get('lotus_purchase_funding'):
        from lotus_farm.purchase_funding import cancel_voucher
        return cancel_voucher(doc,reason)
    p = frappe.db.get_value(posting.POSTING, {'voucher_type': doctype, 'voucher_name': name})
    if p:
        return posting.reverse(p, reason) if setup.is_chief() else _drop(p, doc, reason)
    posting.drop_draft(doc)
    return dict(state='Deleted')


def _drop(p, doc, reason):
    posting.drop_draft(doc)
    from frappe.utils import now_datetime
    frappe.db.set_value(posting.POSTING, p, dict(state='Reversed', active_key=None, reversed_by=frappe.session.user, reversed_at=now_datetime(),
                                                 reason=str(reason or 'Hủy phiếu chi chưa ký')[:500]))
    return dict(state='Deleted')


@frappe.whitelist()
def my_vouchers():
    """Payment vouchers waiting for the current user's signature (directors sign without seeing the ledger)."""
    setup._login()
    from lotus_farm import signing
    rows = frappe.get_all('Lotus Sign Request', filters={'chain': 'payment_voucher', 'assignee': frappe.session.user, 'state': 'Chờ ký'},
                          fields=['document_type', 'document_name'], order_by='creation desc', limit_page_length=100)
    return [_voucher_info(frappe.get_doc(r.document_type, r.document_name), signing) for r in rows
            if frappe.db.get_value(r.document_type, r.document_name, 'docstatus') == 0]


def _voucher_info(doc, signing=None):
    from lotus_farm import signing as sign_module
    signing = signing or sign_module
    if doc.doctype == PE:
        lines = [dict(label=frappe.db.get_value(PI, r.reference_name, 'bill_no') or r.reference_name, amount=flt(r.allocated_amount)) for r in doc.references]
        info = dict(party=doc.party, party_name=frappe.db.get_value('Supplier', doc.party, 'supplier_name') or doc.party, amount=flt(doc.paid_amount),
                    money=doc.paid_to if doc.payment_type=='Receive' else doc.paid_from, reference=doc.reference_no or '', kind='Hoàn tiền từ NCC' if doc.payment_type=='Receive' else 'Trả nhà cung cấp')
    else:
        lines = [dict(label=a.account, amount=flt(a.debit) or -flt(a.credit)) for a in doc.accounts]
        kind = doc.get('lotus_payment_kind')
        party = doc.get('lotus_employee')
        funding=None
        if doc.get('lotus_purchase_funding'):
            funding=frappe.get_doc('Lotus Purchase Funding',doc.lotus_purchase_funding)
            party=funding.payer
        party_name = (frappe.db.get_value('Employee', party, 'employee_name') if party else None) or \
            ('Cơ quan BHXH / thuế / công đoàn' if kind == 'Statutory' else 'Người lao động')
        if funding:
            party_name=frappe.db.get_value(funding.payer_type,party,'employee_name' if funding.payer_type=='Employee' else 'title') or party
        info = dict(party=party or '', party_name=party_name, amount=flt(doc.total_debit), money=next((a.account for a in doc.accounts if a.credit), ''),
                    reference=doc.cheque_no or '', kind={'Advance': 'Tạm ứng lương', 'Statutory': 'Nộp BH, KPCĐ, thuế',
                        'PurchaseFunding':'Cá nhân chi hộ NCC','PurchaseReimbursement':'Hoàn tiền người chi hộ'}.get(kind, 'Chi lương'))
    from urllib.parse import urlencode
    m = setup.mapping()
    return dict(info, doctype=doc.doctype, name=doc.name, posting_date=str(doc.posting_date), remark=doc.get('remarks') or doc.get('user_remark') or '',
                docstatus=doc.docstatus, lines=lines, signing=signing.status(doc), modified=str(doc.modified),
                # Spec 003, US6: how it was paid, the print page, the stored signed copy.
                mode='cash' if info.get('money') == m.get('cash') else 'bank',
                unallocated=flt(doc.get('unallocated_amount')) if doc.doctype == PE else 0,
                print_url='/lotus/in-phieu-chi?' + urlencode(dict(doctype=doc.doctype, name=doc.name)),
                signed_copy=sign_module.copy_info(doc) if doc.docstatus == 1 else None,
                can_reverse=doc.docstatus == 1 and setup.is_chief(), can_cancel_draft=doc.docstatus == 0 and setup.can_post())


@frappe.whitelist()
def vouchers():
    """Payment vouchers made from Lotus (drafts waiting for signatures first), and payroll months ready to be paid."""
    setup.require_view()
    rows = []
    for p in frappe.get_all(posting.POSTING, filters={'purpose': ['in', ['Supplier Payment', 'Salary Payment', 'Salary Advance', 'Statutory Payment']]},
                            fields=['name', 'voucher_type', 'voucher_name', 'state', 'purpose', 'source_name', 'amount', 'posted_by', 'reason'],
                            order_by='creation desc', limit_page_length=200):
        if p.state == 'Reversed' and not frappe.db.exists(p.voucher_type, p.voucher_name):
            rows.append(dict(doctype=p.voucher_type, name=p.voucher_name, state='Đã hủy', amount=flt(p.amount), kind=p.purpose, reason=p.reason or '', lines=[]))
            continue
        info = _voucher_info(frappe.get_doc(p.voucher_type, p.voucher_name))
        info['state'] = {'Draft': 'Chờ ký', 'Posted': 'Đã chi', 'Reversed': 'Đã đảo'}[p.state]
        info['posting'] = p.name
        rows.append(info)
    ready = []
    for p in frappe.get_all(posting.POSTING, filters={'purpose': 'Payroll', 'state': 'Posted'}, fields=['source_name', 'voucher_name']):
        if not posting.active('Lotus Timekeeping Period', p.source_name, 'Salary Payment'):
            from lotus_farm.finance.payroll import pay_list
            period = frappe.get_doc('Lotus Timekeeping Period', p.source_name)
            people = pay_list(period)
            ready.append(dict(period=p.source_name, month=period.month, net=sum(r['net'] for r in people), advance=sum(r['advance'] for r in people),
                              to_pay=sum(r['to_pay'] for r in people), payroll_voucher=p.voucher_name))
    return dict(vouchers=rows, salary_ready=ready)
