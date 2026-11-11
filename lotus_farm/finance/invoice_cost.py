"""Giá vốn theo hóa đơn nhà cung cấp (spec 003 FR-051, research R16).

Phiếu nhận ghi Có 3388 theo giá của phiếu. Với hộ kinh doanh, phiếu nhận ghi thêm Có 33881 theo thuế suất của phiếu
(thuế vào giá vốn) và Có 3388 phí vận chuyển của hàng. Hóa đơn có thể khác giá (phải có lý do) hoặc khác thuế suất.

Cơ chế của ERPNext (Buying Settings `set_landed_cost_based_on_purchase_invoice_rate`) có ba chỗ hụt:
- trải phần chênh lên toàn bộ số đã nhận, kể cả hàng đã trả và phần chưa có hóa đơn;
- bỏ qua phần thuế chênh;
- tính "đã có hóa đơn" theo tiền.

Thử trên bản sao site thật ngày 10/11/2026, cơ chế đó để lại 3388 và 33881 khác 0. Lotus tắt nó (procurement_setup) và tự
ghi theo từng hóa đơn, cho đúng số lượng trên hóa đơn. Hai vòng rà soát độc lập (11/11/2026) đã đi qua cách ghi này.

Khi kỳ của phiếu nhận còn mở:
- Phần chênh của từng dòng (giá, cộng thuế với hộ kinh doanh) vào giá vốn bằng một Landed Cost Voucher (Nợ hàng tồn kho,
  Có 3388). Chỉ dùng một tài khoản, nên không có hai phiếu bù trừ nhau trên hai tài khoản: ERPNext bỏ qua bút toán của
  mọi phiếu khi tổng của dòng bằng 0.
- Phần thuế chênh chuyển từ 3388 sang 33881 bằng một bút toán ngày hóa đơn. ERPNext đã tự chuyển thuế sang 3388 khi
  phiếu nhận không có bút toán thuế nào; những dòng đó được bỏ qua ở bước này.
- Phiếu chia lại (rebalance, gắn với phiếu nhận) giữ cho mỗi dòng hàng mang đúng phí vận chuyển của nó (ERPNext chia phí
  theo giá trị dòng), và chia phần chênh giữa dòng nhận và các dòng trả để hàng trả ra khỏi kho đúng giá vốn. Phần chênh
  của hàng đã có hóa đơn rồi mới trả nằm lại trên 3388 (khoản đòi nhà cung cấp) cho đến hóa đơn điều chỉnh.

Khi kỳ của phiếu nhận đã khóa, đã kết chuyển hoặc đã khóa kho, sổ kỳ đó không đổi: phần chênh ghi vào chi phí của dòng
bằng bút toán ngày hóa đơn. Dòng tài sản cố định (chỉ khi thuế suất của phiếu nhận hết hiệu lực vào ngày hóa đơn) cũng đi
đường này. Hóa đơn điều chỉnh đi theo cách hóa đơn gốc đã ghi.

Mọi chứng từ này gắn với hóa đơn qua `lotus_purchase_invoice` và hủy cùng hóa đơn; phiếu chia lại gắn với phiếu nhận qua
`lotus_cost_receipt`. Không hủy hay sửa riêng được chúng (guard).

3388 + 33881 luôn bằng phần chưa có hóa đơn tính theo phiếu nhận (procurement_queries.unbilled), và về 0 khi phiếu nhận có
hóa đơn đủ. Phiếu nhận "đã có hóa đơn" đo trên phần còn giữ: số đã có hóa đơn, mỗi dòng theo giá trị của dòng.
"""
import frappe
from frappe.utils import flt, getdate

LCV = 'Landed Cost Voucher'
JE = 'Journal Entry'
PR = 'Purchase Receipt'
PI = 'Purchase Invoice'
PO = 'Purchase Order'
LINK = 'lotus_purchase_invoice'   # Landed Cost Voucher / Journal Entry made for one supplier invoice
RECEIPT = 'lotus_cost_receipt'    # Landed Cost Voucher that re-splits a receipt (freight per line, returns)
FLAG = 'lotus_invoice_cost'


def _active():
    return not (getattr(frappe.flags, 'in_install', False) or getattr(frappe.flags, 'in_migrate', False))


def _ready():
    return (frappe.db.exists('DocType', LCV) and frappe.get_meta(LCV).has_field(LINK) and frappe.get_meta(LCV).has_field(RECEIPT)
            and frappe.get_meta(JE).has_field(LINK))


class _own:
    """Lotus posts or cancels its own adjustment documents: the guard lets them through."""
    def __enter__(self):
        self.before = getattr(frappe.flags, FLAG, False)
        setattr(frappe.flags, FLAG, True)

    def __exit__(self, *exc):
        setattr(frappe.flags, FLAG, self.before)


def _dims():
    from lotus_farm.finance import rules
    return [f for f in rules.DIM_FIELDS if frappe.get_meta('Purchase Receipt Item').has_field(f)]


def _item(code):
    return frappe.get_cached_value('Item', code, ['is_stock_item', 'is_fixed_asset'], as_dict=True) if code else None


def _vat_date(pi):
    """VAT rates of an invoice line are those of the invoice it adjusts (a credit note of a 2026 purchase keeps 2026 rates)."""
    if pi.get('is_return') and pi.get('return_against'):
        original = frappe.db.get_value(PI, pi.return_against, ['bill_date', 'posting_date'], as_dict=True)
        if original:
            return original.bill_date or original.posting_date
    return pi.get('bill_date') or pi.posting_date


def adjustments(pi):
    """One entry per invoice line billing a receipt line of a stock item or an asset:
    net = price difference for the billed quantity (what 3388 keeps after the invoice);
    vat = VAT difference of a household business (what 33881 keeps);
    swapped = ERPNext itself moved this line's invoice VAT from 33881 to 3388 (its receipt has no ledger line on the
    invoice's valuation-tax accounts: purchase_invoice.make_item_gl_entries, stock items only);
    asset = a fixed-asset line (its value is taken at receipt: the difference becomes a cost)."""
    from lotus_farm.finance import rules, setup
    household = setup.vat_in_cost()
    billed_on = _vat_date(pi)
    valuation = [t.account_head for t in pi.taxes
                 if t.category in ('Valuation', 'Valuation and Total') and flt(t.base_tax_amount_after_discount_amount)]
    fields = ['name', 'parent', 'item_code', 'item_name', 'qty', 'net_rate', 'base_net_amount', 'lotus_line_vat', 'cost_center',
              'expense_account', *_dims()]
    receipts, swapped, found = {}, {}, []
    for row in pi.items:
        if not row.get('pr_detail') or not row.item_code:
            continue
        item = _item(row.item_code)
        if not item or not (item.is_stock_item or item.is_fixed_asset):
            continue  # services carry no stock value
        line = frappe.db.get_value('Purchase Receipt Item', row.pr_detail, fields, as_dict=True)
        if not line or not flt(line.qty):
            continue
        if line.parent not in receipts:
            receipts[line.parent] = frappe.db.get_value(PR, line.parent, ['posting_date', 'conversion_rate', 'company'], as_dict=True)
        receipt = receipts[line.parent]
        receipt_net = flt(line.base_net_amount) * flt(row.qty) / flt(line.qty)
        net = flt(row.base_net_amount) - receipt_net
        if (flt(receipt.conversion_rate) and flt(pi.conversion_rate) != flt(receipt.conversion_rate)
                and flt(row.net_rate) == flt(line.net_rate)):
            net = 0.0  # same price, another exchange rate: ERPNext books the exchange difference itself
        vat = 0.0
        if household:
            try:
                vat = (flt(row.base_net_amount) * rules.vat_rate(row.get('lotus_line_vat') or 'KCT', billed_on)
                       - receipt_net * rules.vat_rate(line.get('lotus_line_vat') or 'KCT', receipt.posting_date))
            except ValueError as exc:
                frappe.throw(str(exc))
        if line.parent not in swapped:
            swapped[line.parent] = bool(valuation) and not frappe.db.sql(
                "select name from `tabGL Entry` where voucher_type='Purchase Receipt' and voucher_no=%s and account in %s limit 1",
                (line.parent, tuple(valuation)))
        net, vat = flt(net, 0), flt(vat, 0)
        if abs(net) >= 1 or abs(vat) >= 1:
            found.append(frappe._dict(line=line, receipt=line.parent, received_on=getdate(receipt.posting_date), net=net, vat=vat,
                                      asset=bool(item.is_fixed_asset),
                                      swapped=bool(item.is_stock_item and swapped[line.parent] and flt(row.item_tax_amount))))
    return found


def _closed(company, day):
    """Why the books of `day` may not change any more, or None."""
    from lotus_farm.finance import posting, setup
    from lotus_farm.finance.native_guards import _enabled_for
    day = getdate(day)
    frozen = frappe.get_cached_value('Company', company, 'accounts_frozen_till_date') if frappe.get_meta('Company').has_field('accounts_frozen_till_date') else None
    if frozen and day <= getdate(frozen):
        return 'sổ đã khóa đến ngày %s' % getdate(frozen).strftime('%d/%m/%Y')
    period = frappe.db.sql('''select ap.period_name from `tabAccounting Period` ap join `tabClosed Document` cd on cd.parent=ap.name
        where ap.company=%s and ap.disabled=0 and %s between ap.start_date and ap.end_date and cd.document_type=%s and cd.closed=1 limit 1''',
                           (company, day, PR))
    if period:
        return 'kỳ %s đã khóa sổ' % period[0][0]
    if frappe.db.exists('DocType', 'Period Closing Voucher'):
        end = frappe.db.sql("select max(period_end_date) from `tabPeriod Closing Voucher` where company=%s and docstatus=1", company)[0][0]
        if end and day <= getdate(end):
            return 'sổ đã kết chuyển cuối kỳ đến ngày %s' % getdate(end).strftime('%d/%m/%Y')
    if frappe.db.exists('DocType', 'Stock Closing Entry'):
        meta = frappe.get_meta('Stock Closing Entry')
        if meta.has_field('to_date') and meta.has_field('status'):
            # ERPNext 16 freezes every stock posting on or before the latest completed closing (stock_ledger.validate_stock_frozen_by_closing_entry).
            end = frappe.db.sql("select max(to_date) from `tabStock Closing Entry` where company=%s and docstatus=1 and status='Completed'", company)[0][0]
            if end and day <= getdate(end):
                return 'kho đã khóa sổ đến ngày %s' % getdate(end).strftime('%d/%m/%Y')
    if _enabled_for(frappe._dict(company=company)) and posting.active(setup.SETTINGS, setup.SETTINGS, 'Result Closing', str(day)[:7]):
        return 'tháng %s đã kết chuyển' % str(day)[:7]
    return None


class _orders_open:
    """ERPNext refuses to repost a receipt whose order is closed (BuyingController.update_ordered_and_reserved_qty: "is
    cancelled or closed", returns excepted), and a Landed Cost Voucher reposts its receipts on submit and on cancel.
    Lotus closes the rest of an order with purchasing.close_order, and the goods received still take their invoice. The
    order reads open for that moment only; closed again, its ordered quantity is computed again (get_ordered_qty leaves
    closed orders out). Third review, 11/11/2026."""

    def __init__(self, receipts):
        self.receipts = tuple(dict.fromkeys(r for r in receipts if r))
        self.orders = []

    def __enter__(self):
        if self.receipts:
            self.orders = [r[0] for r in frappe.db.sql('''select distinct po.name from `tabPurchase Receipt Item` pri
                join `tabPurchase Receipt` pr on pr.name=pri.parent join `tabPurchase Order` po on po.name=pri.purchase_order
                where pri.parent in %s and pr.is_return=0 and po.docstatus=1 and po.status='Closed' ''', (self.receipts,))]
        for name in self.orders:
            frappe.db.set_value(PO, name, 'status', 'To Bill', update_modified=False)
        return self

    def __exit__(self, *exc):
        for name in self.orders:
            frappe.db.set_value(PO, name, 'status', 'Closed', update_modified=False)
            frappe.get_doc(PO, name).update_ordered_qty()


def _cancel(doctype, name):
    """Cancel a document Lotus made for an invoice or a receipt (the guard lets it through)."""
    other = frappe.get_doc(doctype, name)
    other.flags.ignore_permissions = True
    if doctype == LCV:
        with _orders_open([r.receipt_document for r in other.purchase_receipts]):
            other.cancel()
    else:
        other.cancel()


def _lcv(company, posting_date, account, part, description, marks):
    """One Landed Cost Voucher on one account; part = [(receipt line, amount)], every amount with the same sign."""
    cost_center = frappe.get_cached_value('Company', company, 'cost_center')
    receipts = list(dict.fromkeys(line.parent for line, _ in part))
    heads = {name: frappe.db.get_value(PR, name, ['supplier', 'posting_date', 'base_grand_total'], as_dict=True) for name in receipts}
    doc = frappe.get_doc(dict(
        doctype=LCV, company=company, posting_date=posting_date, distribute_charges_based_on='Distribute Manually',
        purchase_receipts=[dict(receipt_document_type=PR, receipt_document=name, supplier=heads[name].supplier,
                                posting_date=heads[name].posting_date, grand_total=heads[name].base_grand_total) for name in receipts],
        items=[dict(item_code=line.item_code, description=line.item_name or line.item_code, receipt_document_type=PR,
                    receipt_document=line.parent, purchase_receipt_item=line.name, qty=flt(line.qty),
                    rate=flt(line.base_net_amount) / flt(line.qty) if flt(line.qty) else 0, amount=flt(line.base_net_amount),
                    applicable_charges=amount, cost_center=line.cost_center or cost_center) for line, amount in part],
        taxes=[dict(description=description, expense_account=account, amount=sum(amount for _, amount in part), cost_center=cost_center)]))
    doc.update(marks)
    doc.flags.ignore_permissions = True
    doc.insert()
    with _orders_open(receipts):
        doc.submit()
    return doc.name


def _journal(pi, rows, remark):
    """A Journal Entry at the invoice date, linked to it; rows = [(account, amount, cost_center, dims)], amount > 0 is Nợ."""
    rows = [r for r in rows if abs(flt(r[1], 0)) >= 1]
    if not rows:
        return None
    gap = flt(sum(flt(r[1], 0) for r in rows), 0)
    if gap:  # đồng of rounding go to the first row so the entry balances exactly
        account, amount, cost_center, dims = rows[0]
        rows[0] = (account, amount - gap, cost_center, dims)
    accounts = []
    meta = frappe.get_meta('Journal Entry Account')
    for account, amount, cost_center, dims in rows:
        amount = flt(amount, 0)
        accounts.append(dict(account=account, debit_in_account_currency=max(amount, 0), credit_in_account_currency=max(-amount, 0),
                             cost_center=cost_center, **{k: v for k, v in (dims or {}).items() if v and meta.has_field(k)}))
    doc = frappe.get_doc(dict(doctype=JE, voucher_type='Journal Entry', company=pi.company, posting_date=pi.posting_date,
                              user_remark=remark, accounts=accounts))
    doc.set(LINK, pi.name)
    doc.flags.ignore_permissions = True
    doc.insert()
    doc.submit()
    return doc.name


def _original_booking(pi):
    """For a credit note: the receipt lines its original invoice moved into stock, and whether it booked any as a cost."""
    if not (pi.get('is_return') and pi.get('return_against')):
        return None
    lines = {r[0] for r in frappe.db.sql('''select i.purchase_receipt_item from `tabLanded Cost Item` i join `tabLanded Cost Voucher` v on v.name=i.parent
        where v.docstatus=1 and v.lotus_purchase_invoice=%s''', pi.return_against)}
    expense = bool(frappe.db.sql('''select a.name from `tabJournal Entry Account` a join `tabJournal Entry` j on j.name=a.parent
        join `tabAccount` acc on acc.name=a.account where j.docstatus=1 and j.lotus_purchase_invoice=%s and acc.root_type='Expense' limit 1''',
                                 pi.return_against))
    return frappe._dict(lines=lines, expense=expense)


def follow(doc, method=None):
    """on_submit of Purchase Invoice: the invoice difference goes into the cost of the goods, then billing is measured."""
    if not _active() or doc.get('update_stock') or not _ready():
        return
    if doc.get('is_return'):
        _refuse_parked(doc)
    found = adjustments(doc)
    if found:
        from lotus_farm.finance import setup
        received_not_billed = frappe.get_cached_value('Company', doc.company, 'stock_received_but_not_billed')
        clearing = setup.valuation_tax_account(doc.company)
        cost_center = frappe.get_cached_value('Company', doc.company, 'cost_center')
        label = '%s (%s)' % (doc.get('bill_no') or doc.name, doc.name)
        original = _original_booking(doc)
        stock, expense = [], []
        for a in found:
            to_cost = a.asset or bool(_closed(doc.company, a.received_on))
            if original is not None and not to_cost:
                # A credit note reverses the way its invoice booked the line: into stock only if the invoice did.
                to_cost = a.line.name not in original.lines and original.expense
            (expense if to_cost else stock).append(a)
        with _own():
            if stock:
                lines = [(a.line, a.net + a.vat) for a in stock if abs(a.net + a.vat) >= 1]
                for up in (True, False):
                    part = [(line, amount) for line, amount in lines if (amount > 0) == up]
                    if part:
                        _lcv(doc.company, doc.posting_date, received_not_billed, part,
                             'Chênh lệch giá và thuế theo hóa đơn %s, vào giá vốn' % label, {LINK: doc.name})
                moved = flt(sum(a.vat for a in stock if not a.swapped), 0)
                if moved:
                    _journal(doc, [(received_not_billed, moved, cost_center, None), (clearing, -moved, cost_center, None)],
                             'Hộ kinh doanh: thuế GTGT chênh theo hóa đơn %s đã vào giá vốn; chuyển từ 3388 về 33881.' % label)
            if expense:
                # The receipt's books are closed (or the line is an asset): the difference becomes a cost of this period.
                default = frappe.get_cached_value('Company', doc.company, 'default_expense_account')
                rows, credit_3388, credit_clearing = [], 0.0, 0.0
                for a in expense:
                    dims = {f: a.line.get(f) for f in _dims()}
                    account = default if a.asset else (a.line.expense_account or default)
                    rows.append((account, a.net + a.vat, a.line.cost_center or cost_center, dims))
                    credit_3388 += a.net + (a.vat if a.swapped else 0)
                    credit_clearing += 0 if a.swapped else a.vat
                rows += [(received_not_billed, -credit_3388, cost_center, None), (clearing, -credit_clearing, cost_center, None)]
                _journal(doc, rows, 'Chênh lệch giá và thuế theo hóa đơn %s ghi vào chi phí kỳ này (kỳ của phiếu nhận đã khóa, '
                                    'hoặc tài sản cố định).' % label)
    # Every receipt the invoice billed is split again: the quantity invoiced decides what the kept goods carry, even when
    # this invoice brings no difference of its own (rebalance does nothing when the split is unchanged).
    for receipt in dict.fromkeys(r.purchase_receipt for r in doc.items if r.get('purchase_receipt')):
        rebalance(receipt)
    billed_by_qty(doc)


def _billed_qty(lines, exclude_invoice=None):
    """{receipt line: quantity invoiced, net of credit notes}, leaving out an invoice being cancelled (its docstatus is
    still 1 in before_cancel)."""
    lines = tuple(lines)
    if not lines:
        return {}
    return {k: flt(v) for k, v in frappe.db.sql('''select pii.pr_detail, sum(pii.qty) from `tabPurchase Invoice Item` pii
        join `tabPurchase Invoice` pi on pi.name=pii.parent where pi.docstatus=1 and pi.name!=%s and pii.pr_detail in %s
        group by pii.pr_detail''', (exclude_invoice or '', lines))}


def _parked_claim(line):
    """The part of a receipt line's invoice difference that its returns carry out of stock onto 3388 (the claim on the
    supplier when more was invoiced than kept), as the split vouchers left it: split vouchers on the line and on its return
    lines, less the own-freight shares those vouchers also carry. 0 when invoiced ≤ kept (the split then balances)."""
    returns = frappe.db.sql('''select ri.name, ri.parent from `tabPurchase Receipt Item` ri join `tabPurchase Receipt` r on r.name=ri.parent
        where r.docstatus=1 and r.is_return=1 and ri.purchase_receipt_item=%s''', line.name, as_dict=True)
    if not returns:
        return 0.0
    pairs = [(line.parent, line.name)] + [(r.parent, r.name) for r in returns]
    split = frappe.db.sql('''select i.receipt_document, i.purchase_receipt_item, sum(i.applicable_charges) from `tabLanded Cost Item` i
        join `tabLanded Cost Voucher` v on v.name=i.parent where v.docstatus=1 and ifnull(v.lotus_cost_receipt, '')!=''
        and i.purchase_receipt_item in %s group by i.receipt_document, i.purchase_receipt_item''', (tuple(n for _, n in pairs),))
    total = sum(flt(amount) for _, _, amount in split)
    # A document's freight shares are in its split vouchers only if it was split at all.
    for document in dict.fromkeys(d for d, _, _ in split):
        shares = _freight_shares(document)
        total -= sum(flt(shares.get(n)) for d, n in pairs if d == document)
    return flt(total, 0)


def _refuse_parked(doc, cancelling=False):
    """A credit note, or cancelling an invoice, changes what is invoiced on its receipt lines. Where a line's returns carry
    part of the invoice difference onto 3388 as the claim on the supplier, the split must change with it, and in closed
    books it cannot: the claim on 3388 would be left wrong, or a gain shown (reviews 2 and 3, 11/11/2026). Refuse, with the
    way out."""
    for row in doc.get('items') or []:
        if not row.get('pr_detail'):
            continue
        line = frappe.db.get_value('Purchase Receipt Item', row.pr_detail, ['name', 'parent'], as_dict=True)
        if not line:
            continue
        day = getdate(frappe.db.get_value(PR, line.parent, 'posting_date'))
        why = _closed(doc.company, day)
        if why and abs(_parked_claim(line)) >= 1:
            action = 'hủy hóa đơn %s' % doc.name if cancelling else 'ghi hóa đơn điều chỉnh này'
            frappe.throw('Hàng của phiếu nhận %s đã trả sau khi có hóa đơn, và phần chênh giá của hàng trả đang chờ trên 3388 (khoản NCC phải '
                         'hoàn). Kỳ của phiếu nhận ngày %s đã khóa (%s), nên Lotus không %s tự động được mà không làm sai khoản đó. '
                         'Mở lại kỳ đó, %s, rồi khóa lại.' % (line.parent, day.strftime('%d/%m/%Y'), why, action, action))


def _lotus_lcv_items(receipt):
    """Submitted Lotus Landed Cost Voucher lines on a receipt and its returns: (voucher, receipt_document, line, amount, kind)."""
    return frappe.db.sql('''select v.name voucher, i.receipt_document, i.purchase_receipt_item line, i.applicable_charges amount,
            if(ifnull(v.lotus_purchase_invoice, '')!='', 'invoice', 'split') kind
        from `tabLanded Cost Item` i join `tabLanded Cost Voucher` v on v.name=i.parent
        where v.docstatus=1 and (ifnull(v.lotus_purchase_invoice, '')!='' or ifnull(v.lotus_cost_receipt, '')!='')
          and i.receipt_document_type='Purchase Receipt'
          and (i.receipt_document=%(r)s or i.receipt_document in (select name from `tabPurchase Receipt` where return_against=%(r)s))''',
                         dict(r=receipt), as_dict=True)


def _freight_shares(name):
    """{line: own freight − what ERPNext capitalised} for the goods lines of a household receipt or return. ERPNext spreads
    the freight row (allocate_full_amount_to_stock_items) over the goods by value, while each line's own freight is what its
    invoice relieves and its return reverses. Assets cannot take a voucher before they are registered: such documents keep
    ERPNext's spread."""
    from lotus_farm.finance import setup
    if not setup.vat_in_cost():
        return {}
    doc = frappe.get_doc(PR, name)
    account = setup.mapping().get('received_not_billed')
    row = next((t for t in doc.taxes if t.charge_type == 'Actual' and t.account_head == account
                and t.category in ('Valuation', 'Valuation and Total') and flt(t.base_tax_amount_after_discount_amount)), None)
    goods = [r for r in doc.items if (_item(r.item_code) or {}).get('is_stock_item') or (_item(r.item_code) or {}).get('is_fixed_asset')]
    if not row or len(goods) < 2 or any((_item(r.item_code) or {}).get('is_fixed_asset') for r in goods):
        return {}
    # The same spread as BuyingController._spread_charge_over_items (ERPNext 16): by net amount (else quantity), in row
    # order, the rounding left on the last goods line.
    total = flt(row.base_tax_amount_after_discount_amount)
    precision = frappe.get_precision('Purchase Receipt Item', 'item_tax_amount') or 0
    value, count = sum(flt(r.base_net_amount) for r in goods), sum(flt(r.qty) for r in goods)
    if not value and not count:
        return {}
    spread, left = {}, total
    for r in goods[:-1]:
        share = flt((flt(r.base_net_amount) / value if value else flt(r.qty) / count) * total, precision)
        spread[r.name] = share
        left -= share
    spread[goods[-1].name] = flt(left, precision)
    rate = flt(doc.get('conversion_rate')) or 1
    shares = {r.name: flt(flt(r.get('lotus_line_freight')) * rate - spread[r.name], 0) for r in goods}
    gap = flt(sum(shares.values()), 0)
    if gap:  # own freight and the row are the same total: keep the split at nothing on 3388 to the đồng
        shares[goods[-1].name] = flt(shares[goods[-1].name] - gap, 0)
    return {k: v for k, v in shares.items() if abs(v) >= 1}


def rebalance(receipt, exclude=None, exclude_invoice=None):
    """Make the receipt's split vouchers again so that:
    - each goods line of the receipt and of its returns carries its own freight (_freight_shares);
    - for a line with returns, the invoice difference C (Lotus vouchers of its invoices) is split by what was invoiced:
      with Q received, r returned, K kept, b invoiced (net of credit notes), the kept goods carry C·min(b, K)/b (the line
      gets that·Q/K − C, each return −r·that/K); what was invoiced beyond K stays on 3388 as the claim on the supplier
      until its credit note. Returned goods then leave at what they cost, without a "divisional loss" to expense.
    exclude = a return being cancelled; exclude_invoice = an invoice or credit note being cancelled. Nothing is done
    while a touched receipt or return is in closed books.

    One document at a time, the receipt first: a return is valued at the receipt's rate when its own voucher posts, so
    each return's last repost comes after the receipt's final valuation. A document whose split is unchanged is left
    alone (second review, 11/11/2026)."""
    if not _ready() or not frappe.db.exists(PR, receipt):
        return
    head = frappe.db.get_value(PR, receipt, ['company', 'posting_date', 'docstatus', 'is_return'], as_dict=True)
    if head.docstatus != 1 or head.is_return:
        return
    every = _lotus_lcv_items(receipt)
    items = [i for i in every if i.receipt_document != exclude]
    invoiced = {}
    for i in items:
        if i.kind == 'invoice':
            invoiced[i.line] = invoiced.get(i.line, 0.0) + flt(i.amount)
    returns = frappe.db.sql('''select ri.name, ri.parent, ri.purchase_receipt_item, ri.item_code, ri.item_name, ri.qty, ri.base_net_amount,
            ri.cost_center, r.posting_date
        from `tabPurchase Receipt Item` ri join `tabPurchase Receipt` r on r.name=ri.parent
        where r.docstatus=1 and r.is_return=1 and r.return_against=%s and r.name!=%s''', (receipt, exclude or ''), as_dict=True)
    rows = {l.name: l for l in frappe.get_all('Purchase Receipt Item', filters={'parent': receipt},
                                                fields=['name', 'parent', 'item_code', 'item_name', 'qty', 'base_net_amount', 'cost_center'])}
    rows.update({r.name: r for r in returns})
    target = {}

    def add(row, amount):
        if abs(amount) >= 1:
            target[(row.parent, row.name)] = target.get((row.parent, row.name), 0.0) + amount

    for document in [receipt] + list(dict.fromkeys(r.parent for r in returns)):
        for line, amount in _freight_shares(document).items():
            add(rows[line], amount)
    billed = _billed_qty(invoiced, exclude_invoice)
    for name, amount in invoiced.items():
        line = rows.get(name)
        mine = [r for r in returns if r.purchase_receipt_item == name]
        b = flt(billed.get(name))
        if not line or not mine or abs(amount) < 1 or b <= 0:
            continue
        returned = sum(abs(flt(r.qty)) for r in mine)
        kept = flt(line.qty) - returned
        if kept <= 0:
            # Everything went back: the difference leaves with it (the last return takes the rounding) and what was
            # invoiced stays on 3388 as the claim on the supplier until the credit note.
            parts, left = [], amount
            for r in mine[:-1]:
                part = flt(amount * abs(flt(r.qty)) / returned, 0)
                parts.append((r, part))
                left -= part
            parts.append((mine[-1], flt(left, 0)))
            for r, part in parts:
                add(r, -part)
            continue
        share = amount * min(b, kept) / b
        parts = [(r, -flt(share * abs(flt(r.qty)) / kept, 0)) for r in mine]
        add(line, flt(share - amount, 0) - sum(p for _, p in parts) if b <= kept else flt(share * flt(line.qty) / kept - amount, 0))
        for r, part in parts:
            add(r, part)
    current, vouchers = {}, {}
    for i in every:
        if i.kind == 'split':
            vouchers.setdefault(i.receipt_document, [])
            if i.voucher not in vouchers[i.receipt_document]:
                vouchers[i.receipt_document].append(i.voucher)
            if i.receipt_document != exclude:
                current[(i.receipt_document, i.line)] = current.get((i.receipt_document, i.line), 0.0) + flt(i.amount)

    def part_of(split, document):
        return {line: amount for (doc, line), amount in split.items() if doc == document}

    def same(a, b):
        return set(a) == set(b) and all(abs(a[k] - b[k]) < 1 for k in b)

    documents = [receipt] + sorted((set(vouchers) | {k[0] for k in target}) - {receipt})
    changed = [d for d in documents if d == exclude and vouchers.get(d) or not same(part_of(current, d), part_of(target, d))]
    if not changed:
        return  # already split this way
    # Every receipt or return whose ledger the split rewrites must still be open, and the receipt itself.
    days = {getdate(frappe.db.get_value(PR, name, 'posting_date')) for name in {receipt, *changed} if frappe.db.exists(PR, name)}
    if any(_closed(head.company, d) for d in days):
        return  # closed books stay as they are; a return then leaves at the line's average cost
    account = frappe.get_cached_value('Company', head.company, 'stock_received_but_not_billed')
    with _own():
        for document in documents:
            if document not in changed:
                continue
            for name in vouchers.get(document, []):
                _cancel(LCV, name)
            for up in (True, False):
                part = [(rows[line], amount) for line, amount in part_of(target, document).items() if (amount > 0) == up]
                if part:
                    _lcv(head.company, frappe.utils.nowdate(), account, part,
                         'Chia lại chênh lệch của phiếu nhận %s: phí vận chuyển theo từng dòng, hàng còn lại và hàng đã trả' % receipt,
                         {RECEIPT: receipt})


def release(doc, method=None):
    """before_cancel of Purchase Invoice: its adjustments are cancelled first (they link to it). An adjustment that
    rewrote a receipt now in closed books is not undone: the invoice is then reversed by an adjustment invoice."""
    if not _ready():
        return
    _refuse_parked(doc, cancelling=True)
    vouchers = frappe.get_all(LCV, filters={LINK: doc.name, 'docstatus': 1}, pluck='name', order_by='creation desc')
    journals = frappe.get_all(JE, filters={LINK: doc.name, 'docstatus': 1}, pluck='name', order_by='creation desc')
    receipts = []
    for name in vouchers:
        for row in frappe.get_all('Landed Cost Purchase Receipt', filters={'parent': name}, fields=['receipt_document', 'posting_date']):
            why = _closed(doc.company, row.posting_date)
            if why:
                frappe.throw('Hóa đơn %s đã đưa phần chênh giá vào giá vốn của phiếu nhận %s ngày %s, nhưng %s: hủy hóa đơn sẽ sửa sổ '
                             'kỳ đó. Lập hóa đơn điều chỉnh (trả lại) cho hóa đơn này thay vì hủy, hoặc mở lại kỳ trước.'
                             % (doc.name, row.receipt_document, getdate(row.posting_date).strftime('%d/%m/%Y'), why))
            receipts.append(row.receipt_document)
    with _own():
        for doctype, names in ((JE, journals), (LCV, vouchers)):
            for name in names:
                _cancel(doctype, name)
    # Every receipt the invoice billed: what it invoiced no longer counts in the split, with or without a difference.
    for receipt in dict.fromkeys(receipts + [r.purchase_receipt for r in doc.items if r.get('purchase_receipt')]):
        rebalance(receipt, exclude_invoice=doc.name)


def guard(doc, method=None):
    """Landed Cost Vouchers and Journal Entries Lotus made move with their invoice or receipt only."""
    if getattr(frappe.flags, FLAG, False):
        return
    invoice, receipt = doc.get(LINK), doc.get(RECEIPT)
    if not (invoice or receipt) and doc.get('amended_from') and doc.meta.has_field(LINK):
        fields = [LINK, RECEIPT] if doc.doctype == LCV else [LINK]
        marks = frappe.db.get_value(doc.doctype, doc.amended_from, fields, as_dict=True) or {}
        invoice, receipt = marks.get(LINK), marks.get(RECEIPT)
    if invoice:
        frappe.throw('%s %s do Lotus lập cho hóa đơn %s (chênh lệch giá và thuế theo hóa đơn). Phiếu này đi cùng hóa đơn: muốn '
                     'bỏ thì hủy hóa đơn ở Mua hàng › Hóa đơn (không dùng "Hủy tất cả"), không hủy hay sửa riêng phiếu này.'
                     % (doc.doctype, doc.name, invoice), frappe.PermissionError)
    if receipt:
        frappe.throw('%s %s do Lotus lập cho phiếu nhận %s (phí vận chuyển theo dòng, chênh lệch với hàng đã trả). Lotus tự lập '
                     'lại phiếu này mỗi khi có hóa đơn hoặc trả hàng; không hủy hay sửa riêng.' % (doc.doctype, doc.name, receipt),
                     frappe.PermissionError)


def settings_guard(doc, method=None):
    """validate of Buying Settings: two ERPNext switches would count the invoice difference twice, or invoice goods
    already returned, next to what Lotus posts (R16)."""
    if not _active() or not _ready():
        return
    if doc.get('set_landed_cost_based_on_purchase_invoice_rate') or doc.get('bill_for_rejected_quantity_in_purchase_invoice'):
        frappe.throw('Lotus tự đưa phần chênh giá và thuế theo hóa đơn vào giá vốn (Mua hàng). Không bật "Set Landed Cost Based on '
                     'Purchase Invoice Rate" hay "Bill for Rejected Quantity in Purchase Invoice": phần chênh sẽ bị tính hai lần, '
                     'hoặc hàng đã trả bị tính lại vào hóa đơn.')


def adjustments_of(invoice):
    """The adjustments an invoice made, for its detail screen: kind cost (into the goods' cost), vat (VAT moved from 3388
    to 33881) or expense (a cost of the period), with signed amounts."""
    if not _ready():
        return []
    from lotus_farm.finance import setup
    out = []
    for row in frappe.get_all(LCV, filters={LINK: invoice, 'docstatus': 1}, fields=['name', 'total_taxes_and_charges'], order_by='creation'):
        tax = frappe.get_all('Landed Cost Taxes and Charges', filters={'parent': row.name}, fields=['description'], limit=1)
        out.append(dict(doctype=LCV, name=row.name, kind='cost', amount=flt(row.total_taxes_and_charges),
                        description=tax[0].description if tax else ''))
    for row in frappe.get_all(JE, filters={LINK: invoice, 'docstatus': 1}, fields=['name', 'company', 'user_remark'], order_by='creation'):
        lines = frappe.db.sql('''select a.account, a.debit - a.credit amount, acc.root_type from `tabJournal Entry Account` a
            join `tabAccount` acc on acc.name=a.account where a.parent=%s''', row.name, as_dict=True)
        cost = [l for l in lines if l.root_type == 'Expense']
        if cost:
            out.append(dict(doctype=JE, name=row.name, kind='expense', amount=sum(flt(l.amount) for l in cost), description=row.user_remark or ''))
        else:
            clearing = setup.valuation_tax_account(row.company)
            out.append(dict(doctype=JE, name=row.name, kind='vat', amount=-sum(flt(l.amount) for l in lines if l.account == clearing),
                            description=row.user_remark or ''))
    return out


def returned_qty_map(receipt):
    """{receipt line: quantity returned by submitted returns}, summed over every return. ERPNext's get_returned_qty_map
    keeps one return per line (a dict built from rows), and ERPNext 16 leaves returned_qty / per_returned of the receipt
    at 0 for these returns (VPS test stack, 11/11/2026)."""
    return {line: flt(qty) for line, qty in frappe.db.sql('''select ri.purchase_receipt_item, sum(abs(ri.qty)) from `tabPurchase Receipt Item` ri
        join `tabPurchase Receipt` r on r.name=ri.parent where r.docstatus=1 and r.is_return=1 and r.return_against=%s
        group by ri.purchase_receipt_item''', receipt)}


def _receipt_billing(name):
    """per_billed of a receipt over what it keeps: for each line still held (received − returned), the share invoiced,
    weighted by the value kept. Fully returned lines need no invoice; a receipt returned in full counts as done.
    per_returned (share of the quantity received that went back) is kept right too: screens read 100 as 'Đã trả hết hàng'."""
    from erpnext.stock.doctype.purchase_receipt.purchase_receipt import get_invoiced_qty_map
    receipt = frappe.get_doc(PR, name)
    if receipt.docstatus != 1 or receipt.is_return:
        return
    invoiced, returned = get_invoiced_qty_map(name), returned_qty_map(name)
    held = []
    for row in receipt.items:
        kept = flt(row.qty) - flt(returned.get(row.name))
        if flt(row.qty) > 0 and kept > 0.000001:
            held.append((row, kept))
    by_value = sum(abs(flt(r.base_net_amount)) for r, _ in held) > 0
    total = done = 0.0
    for row, kept in held:
        weight = abs(flt(row.base_net_amount)) * kept / flt(row.qty) if by_value else kept
        total += weight
        done += weight * min(1.0, max(0.0, flt(invoiced.get(row.name)) / kept))
    # 100 only when every kept line with a value is invoiced in full; ERPNext and the screens read 99.99 as done, and a
    # small line must not drop out of "chờ hóa đơn" (third review, 11/11/2026).
    complete = all(flt(invoiced.get(r.name)) >= kept - 0.000001 for r, kept in held if not by_value or flt(r.base_net_amount))
    percent = 100.0 if complete else min(round(100 * done / total, 6) if total else 0.0, 99.98)
    received = sum(flt(r.qty) for r in receipt.items if flt(r.qty) > 0)
    back = sum(min(flt(r.qty), flt(returned.get(r.name))) for r in receipt.items if flt(r.qty) > 0)
    # Quantities of different units are not added up into "everything went back": 100 only when nothing is kept.
    gone = 100.0 if received and not held else min(round(100 * back / received, 6) if received else 0.0, 99.98)
    changed = False
    for field, value in (('per_billed', percent), ('per_returned', gone)):
        if receipt.meta.has_field(field) and abs(value - flt(receipt.get(field))) > 1e-6:
            receipt.db_set(field, value, update_modified=False)
            changed = True
    if changed:
        receipt.set_status(update=True, update_modified=False)


def _order_billing(name):
    """per_billed of an order measured in quantities against what was ordered, each line by its value."""
    order = frappe.get_doc(PO, name)
    if order.docstatus != 1:
        return
    lines = [r.name for r in order.items]
    billed = dict(frappe.db.sql('''select pii.po_detail, sum(pii.qty) from `tabPurchase Invoice Item` pii join `tabPurchase Invoice` pi on pi.name=pii.parent
        where pi.docstatus=1 and pii.po_detail in %s group by pii.po_detail''', (tuple(lines) or ('',),))) if lines else {}
    rows = [r for r in order.items if flt(r.qty) > 0]
    by_value = sum(abs(flt(r.base_net_amount)) for r in rows) > 0
    total = done = 0.0
    for row in rows:
        weight = abs(flt(row.base_net_amount)) if by_value else flt(row.qty)
        total += weight
        done += weight * min(1.0, max(0.0, flt(billed.get(row.name)) / flt(row.qty)))
    complete = bool(rows) and all(flt(billed.get(r.name)) >= flt(r.qty) - 0.000001 for r in rows if not by_value or flt(r.base_net_amount))
    percent = 100.0 if complete else min(round(100 * done / total, 6) if total else 0.0, 99.98)
    if abs(percent - flt(order.per_billed)) > 1e-6:
        order.db_set('per_billed', percent, update_modified=False)
        order.set_status(update=True, update_modified=False)


def billed_by_qty(doc, method=None):
    """ERPNext measures billing in money, so an invoice below the receipt price leaves the receipt and the order "partly
    billed" for ever. The difference is already in the cost (above), so billing is measured in quantities. Runs after
    ERPNext's own update, on submit and on cancel of the invoice."""
    if not _active():
        return
    for name in dict.fromkeys(r.purchase_receipt for r in doc.items if r.get('purchase_receipt')):
        _receipt_billing(name)
    for name in dict.fromkeys(r.purchase_order for r in doc.items if r.get('purchase_order')):
        _order_billing(name)


def receipt_posted(doc, method=None):
    """on_submit / on_cancel of Purchase Receipt. A return changes what the original still has to bill and how its
    adjustments are split; a household receipt's goods lines take their own freight."""
    if not _active():
        return
    if doc.get('is_return') and doc.get('return_against'):
        _receipt_billing(doc.return_against)
        rebalance(doc.return_against)
    elif method == 'on_submit' and not doc.get('is_return'):
        rebalance(doc.name)


def return_cancelling(doc, method=None):
    """before_cancel of a Purchase Receipt. A return: the split vouchers that point at it are made again without it.
    A receipt: its split vouchers go first (an invoice must already have been cancelled)."""
    if not _active() or not _ready():
        return
    if not doc.get('is_return'):
        with _own():
            for name in frappe.get_all(LCV, filters={RECEIPT: doc.name, 'docstatus': 1}, pluck='name'):
                _cancel(LCV, name)
        return
    if not doc.get('return_against'):
        return
    linked = frappe.db.sql('''select distinct v.name from `tabLanded Cost Item` i join `tabLanded Cost Voucher` v on v.name=i.parent
        where v.docstatus=1 and ifnull(v.lotus_cost_receipt,'')!='' and i.receipt_document=%s''', doc.name)
    if not linked:
        return
    rebalance(doc.return_against, exclude=doc.name)
    if frappe.db.sql('''select v.name from `tabLanded Cost Item` i join `tabLanded Cost Voucher` v on v.name=i.parent
            where v.docstatus=1 and ifnull(v.lotus_cost_receipt,'')!='' and i.receipt_document=%s limit 1''', doc.name):
        frappe.throw('Phiếu trả %s đã được tính lại giá vốn cùng phiếu nhận %s, mà kỳ của chúng đã khóa: hủy phiếu trả sẽ sửa sổ '
                     'kỳ đó. Lập phiếu nhận bổ sung thay vì hủy, hoặc mở lại kỳ trước.' % (doc.name, doc.return_against))
