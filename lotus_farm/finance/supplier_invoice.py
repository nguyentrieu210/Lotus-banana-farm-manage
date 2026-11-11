"""Một lõi lập hóa đơn nhà cung cấp (spec 003, US5; research R16, R17).

Every way of entering a supplier invoice — Mua hàng, Tài chính › Chờ hạch toán, phone — ends in create(): one lock,
one duplicate check (NCC + ký hiệu + số), one tax rule (household business: VAT goes into cost, never 1331), one
printed-total rule (1 đ per goods line). The invoice is typed by hand; attached files are evidence only.
procurement.invoice_receipt, payments.make_goods_invoice and payments.make_service_invoice are thin wrappers.
"""
import json

import frappe
from frappe.utils import cint, flt, getdate, nowdate

from lotus_farm import procurement_rules as rules
from lotus_farm.finance import invoice_cost, posting, setup
from lotus_farm.finance import rules as finance_rules

PI = 'Purchase Invoice'
PR = 'Purchase Receipt'
SE = 'Stock Entry'


def _list(value):
    """A list sent as JSON, or as 'A,B' when a client puts it in the URL of a read."""
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if text[:1] in '[{"':
            value = frappe.parse_json(text)
        else:
            return [v.strip() for v in text.split(',') if v.strip()]
    return list(value or [])


def _vnd(value):
    return '{:,.0f}'.format(flt(value)).replace(',', '.')


def _split(receipts):
    """Names → (purchase receipts, Mua nhanh stock entries), each checked for the company and its state."""
    company = setup.company()
    prs, entries = [], []
    for name in dict.fromkeys(str(r) for r in receipts):
        if frappe.db.exists(PR, name):
            doc = frappe.get_doc(PR, name)
            if doc.company != company or doc.docstatus != 1 or doc.is_return:
                frappe.throw('Phiếu nhận %s chưa xác nhận hoặc là phiếu trả hàng.' % name)
            prs.append(doc)
        elif frappe.db.exists(SE, name):
            doc = frappe.get_doc(SE, name)
            if doc.company != company or doc.docstatus != 1 or doc.stock_entry_type != 'Material Receipt' or doc.get('lotus_receipt_reason') != 'Purchase':
                frappe.throw('Phiếu %s không phải phiếu Mua nhanh đã nhập kho.' % name)
            entries.append(doc)
        else:
            frappe.throw('Không tìm thấy phiếu nhận %s.' % name)
    return prs, entries


def _files(doctype, names):
    if not names:
        return []
    rows = frappe.get_all('File', filters={'attached_to_doctype': doctype, 'attached_to_name': ['in', list(names)]},
                          fields=['name', 'file_name', 'file_url', 'attached_to_name', 'creation'], order_by='creation asc', limit_page_length=0)
    for row in rows:
        row.is_image = str(row.file_name or '').lower().rsplit('.', 1)[-1] in ('jpg', 'jpeg', 'png', 'webp')
        row.creation = str(row.creation)
        # Lotus' own stored copies (signatures, signed PDFs) are not supplier evidence.
        row.own = str(row.file_name or '').startswith(('ky-', 'da-ky-', 'nguoi-giao-ky'))
    seen, out = set(), []
    for r in rows:
        if r.own or (r.attached_to_name, r.file_url) in seen:
            continue
        seen.add((r.attached_to_name, r.file_url))
        out.append(r)
    return out


@frappe.whitelist()
def queue(supplier=None, from_date=None, to_date=None, has_file=None, limit=200, offset=0):
    """Hóa đơn chờ nhập (FR-048): receipts of orders and Mua nhanh receipts that are not fully invoiced, with the
    files attached at receiving (delivery note, invoice photos)."""
    from lotus_farm.finance.payments import receipts_to_bill
    rows = receipts_to_bill(supplier)
    by_type = {}
    for row in rows:
        by_type.setdefault(row['doctype'], []).append(row['name'])
    files = {}
    for doctype, names in by_type.items():
        for file in _files(doctype, names):
            files.setdefault((doctype, file.attached_to_name), []).append(file)
    out = []
    for row in rows:
        day = str(row['posting_date'])
        if from_date and day < str(from_date) or to_date and day > str(to_date):
            continue
        attached = files.get((row['doctype'], row['name']), [])
        if has_file not in (None, '') and bool(cint(has_file)) != bool(attached):
            continue
        out.append(dict(doctype=row['doctype'], name=row['name'], supplier=row['supplier'], supplier_name=row.get('supplier_name') or row['supplier'],
                        date=day, amount=flt(row['to_bill']), total=flt(row['grand_total']), billed_percent=flt(row.get('per_billed')),
                        mua_nhanh=row['doctype'] == SE, source_type='Mua nhanh' if row['doctype'] == SE else 'Nhận theo đơn',
                        lines=row.get('unbilled_items') or [], files=attached))
    out.sort(key=lambda r: (r['date'], r['name']))
    start, size = max(0, cint(offset)), max(1, min(cint(limit) or 200, 500))
    return dict(rows=out[start:start + size], total=len(out), amount=sum(r['amount'] for r in out))


@frappe.whitelist()
def source(receipts):
    """Lines prefilled for the invoice form (FR-049): what each chosen receipt still has to invoice, at the price of
    the order, with the VAT code of the receipt line. Mua nhanh lines are fixed: their value is already in stock."""
    setup.require_view()
    from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice
    prs, entries = _split(_list(receipts))
    suppliers = {d.supplier for d in prs} | {d.get('lotus_supplier') for d in entries}
    if len(suppliers) != 1 or None in suppliers:
        frappe.throw('Các phiếu nhận phải cùng một nhà cung cấp.')
    supplier = suppliers.pop()
    lines = []
    for doc in prs:
        original = {r.name: r for r in doc.items}
        for row in make_purchase_invoice(doc.name).items:
            src = original.get(row.pr_detail)
            if not src or flt(row.qty) <= 0.000001:
                continue
            order_rate = flt(frappe.db.get_value('Purchase Order Item', src.purchase_order_item, 'rate')) if src.purchase_order_item else flt(src.rate)
            lines.append(dict(source_doctype=PR, source_name=doc.name, source_item=src.name, item=src.item_code, item_name=src.item_name,
                              qty=flt(row.qty), received_qty=flt(src.qty), uom=src.uom, rate=flt(src.rate), order_rate=order_rate,
                              vat_code=src.get('lotus_line_vat') or 'KCT', freight=flt(src.get('lotus_line_freight')) * flt(row.qty) / (flt(src.qty) or 1),
                              order=src.purchase_order or '', fixed=False))
    for doc in entries:
        for row in doc.items:
            amount = flt(row.get('basic_amount')) or flt(row.amount)
            lines.append(dict(source_doctype=SE, source_name=doc.name, source_item=row.name, item=row.item_code, item_name=row.item_name,
                              qty=flt(row.transfer_qty), received_qty=flt(row.transfer_qty), uom=row.stock_uom,
                              rate=amount / (flt(row.transfer_qty) or 1), order_rate=None, vat_code='KCT', freight=0, order='', fixed=True))
    # Rates with an end date and the rate that follows (8 % until 31/12/2026, then 10 %): the form moves a line to the
    # rate in force on the invoice date it is given, as _receipt_invoice does (third review, 11/11/2026).
    vat_ends = {r['code']: dict(to=str(r['to']), then=str(r['then'])) for r in finance_rules.load_vat()['rates'] if r.get('to') and r.get('then')}
    return dict(supplier=supplier, supplier_name=frappe.get_cached_value('Supplier', supplier, 'supplier_name') or supplier, lines=lines,
                vat_in_cost=bool(setup.vat_in_cost()), mua_nhanh=bool(entries), vat_ends=vat_ends,
                files=_files(PR, [d.name for d in prs]) + _files(SE, [d.name for d in entries]))


def _service_taxes(pi, on_date):
    """VAT of an invoice made only of service lines. Household business: the VAT joins each line's own expense account
    (never 1331) with the line's farm/lô, still shown as tax rows; otherwise input VAT. Several rates in one invoice are
    kept apart."""
    in_cost = setup.vat_in_cost()
    account = setup.mapping().get('input_vat')
    cost_center = frappe.get_cached_value('Company', pi.company, 'cost_center')
    dims = [f for f in finance_rules.DIM_FIELDS if frappe.get_meta('Purchase Taxes and Charges').has_field(f)] if in_cost else []
    pi.set('taxes', [])
    pi.taxes_and_charges = None
    groups = {}
    for row in pi.items:
        code = str(row.get('lotus_line_vat') or 'KCT')
        try:
            rate = finance_rules.vat_rate(code, on_date)
        except ValueError as exc:
            frappe.throw(str(exc))
        if not rate:
            continue
        key = (code, row.expense_account if in_cost else account) + tuple(row.get(f) or None for f in dims)
        groups[key] = groups.get(key, 0) + flt(row.qty) * flt(row.rate) * rate
    for key, amount in groups.items():
        code, head = key[:2]
        if not head:
            frappe.throw('Thiết lập tài khoản VAT đầu vào tại Tài chính – Kế toán.')
        pi.append('taxes', dict(charge_type='Actual', account_head=head, tax_amount=flt(amount, 0), category='Total', add_deduct_tax='Add',
                                cost_center=cost_center, description='Thuế GTGT %s%%%s' % (code, ' (tính vào chi phí)' if in_cost else ''),
                                **{f: v for f, v in zip(dims, key[2:]) if v}))
    codes = {str(r.get('lotus_line_vat') or 'KCT') for r in pi.items}
    if pi.meta.has_field('lotus_vat_code'):
        pi.lotus_vat_code = codes.pop() if len(codes) == 1 else None


def _printed(pi, printed_total, printed_vat):
    """FR-054: the invoice is recorded at the printed total when the lines differ from it by at most 1 đ per goods
    line; a bigger gap is refused and the lines that could explain it are named."""
    from lotus_farm.procurement import _match_invoice_total
    lines = [dict(line=i, name=r.item_name or r.item_code or '', qty=flt(r.qty), rate=flt(r.rate),
                  vat=finance_rules.vat_rate(r.get('lotus_line_vat') or 'KCT', pi.bill_date or pi.posting_date))
             for i, r in enumerate(pi.items, start=1)]
    if printed_vat not in (None, ''):
        vat = sum(flt(t.tax_amount) for t in pi.taxes if 'GTGT' in str(t.description or ''))
        gap, ok = rules.printed_total_gap(vat, flt(printed_vat), len(lines))
        if not ok:
            frappe.throw('Thuế GTGT tính ra %s đ khác tiền thuế in trên hóa đơn %s đ. Kiểm tra thuế suất từng dòng.' % (_vnd(vat), _vnd(printed_vat)))
    if printed_total in (None, '', 0, '0'):
        return 0
    gap, ok = rules.printed_total_gap(flt(pi.grand_total), flt(printed_total), len(lines))
    if not ok:
        hints = rules.suspect_lines(lines, gap)
        frappe.throw('Tổng các dòng %s đ khác tổng thanh toán in trên hóa đơn %s đ (lệch %s đ, cho phép %d đ). %s' % (
            _vnd(pi.grand_total), _vnd(printed_total), _vnd(gap), max(1, len(lines)),
            'Dòng nghi sai: ' + '; '.join('dòng %d (%s): %s' % (h['line'], h['name'], h['reason']) for h in hints[:3]) + '.'
            if hints else 'Kiểm tra số lượng, đơn giá và thuế suất.'))
    before = flt(pi.grand_total)
    _match_invoice_total(pi, printed_total)
    return round(flt(pi.grand_total) - before, 2)


def _receipt_invoice(prs, picked, vat_code, bill_date):
    """Invoice lines from purchase receipts: the unbilled quantity, the receipt's price unless the invoice says
    otherwise (then a reason is required), the receipt line's VAT code unless the invoice line says otherwise."""
    from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice
    from lotus_farm.procurement import item_kind
    mapping = setup.mapping()
    pi = None
    for doc in prs:
        pi = make_purchase_invoice(doc.name, target_doc=pi)
    original = {r.name: r for doc in prs for r in doc.items}
    header_code = str(vat_code or '').strip()
    receipt_codes = {str(r.get('lotus_line_vat') or 'KCT') for r in original.values()}
    due_codes = set()
    if header_code and header_code != 'KCT':
        # One rate for the whole invoice: compared with the receipts' rates as they stand on the invoice date (8 % gave way
        # to 10 % on 1/1/2027).
        try:
            due_codes = {finance_rules.vat_code_on(c, bill_date) for c in receipt_codes}
        except ValueError as exc:
            frappe.throw(str(exc))
    kept, seen = [], set()
    for row in pi.items:
        src = original.get(row.pr_detail)
        if not src:
            continue
        want = picked.get(row.pr_detail) if picked is not None else {}
        if want is None:
            continue
        seen.add(row.pr_detail)
        qty = flt(want.get('qty')) if want.get('qty') not in (None, '') else flt(row.qty)
        if qty <= 0 or qty > flt(row.qty) + .000001:
            frappe.throw('%s: số lượng hóa đơn vượt phần chưa lập hóa đơn (còn %s).' % (src.item_name or src.item_code, frappe.utils.cstr(flt(row.qty, 3))))
        row.qty = qty
        row.stock_qty = qty * flt(row.conversion_factor)
        if want.get('rate') not in (None, ''):
            rate = flt(want.get('rate'))
            if rate <= 0:
                frappe.throw('%s: đơn giá hóa đơn phải lớn hơn 0.' % (src.item_name or src.item_code))
            if rate > 2 * flt(src.rate) + 0.005:
                # Accounts Settings over_billing_allowance = 100 %: ERPNext would refuse it later, in English.
                frappe.throw('%s: đơn giá hóa đơn %s cao hơn 2 lần giá phiếu nhận %s. Kiểm tra lại đơn giá; nếu đúng, lập đơn mua bổ sung.' % (
                    src.item_name or src.item_code, _vnd(rate), _vnd(src.rate)))
            if abs(rate - flt(src.rate)) > 0.005:
                reason = str(want.get('variance_reason') or '').strip()
                if len(reason) < 3:
                    frappe.throw('%s: đơn giá hóa đơn %s khác giá phiếu nhận %s. Ghi lý do chênh lệch.' % (
                        src.item_name or src.item_code, _vnd(rate), _vnd(src.rate)))
                if row.meta.has_field('lotus_variance_reason'):
                    row.lotus_variance_reason = reason[:500]
                row.rate = rate
        code = str(want.get('vat_code') or '').strip()
        if code:
            row.lotus_line_vat = code
        elif header_code and header_code != 'KCT':
            # A single rate given for the whole invoice (Tài chính › Chờ hạch toán): it must agree with the receipts. A
            # receipt without VAT invoiced with VAT is fine: the VAT goes into the cost (finance.invoice_cost, test_25).
            if due_codes not in ({'KCT'}, {header_code}):
                frappe.throw('Thuế GTGT lấy theo từng dòng phiếu nhận. Phiếu nhận đang ghi thuế %s; hóa đơn khác thì nhập thuế từng dòng.'
                             % ', '.join(sorted(due_codes)))
            row.lotus_line_vat = header_code
        src_code, line_code = str(src.get('lotus_line_vat') or 'KCT'), str(row.get('lotus_line_vat') or 'KCT')
        try:
            in_force = finance_rules.vat_code_on(src_code, bill_date)
        except ValueError as exc:
            frappe.throw('%s: %s' % (src.item_name or src.item_code, exc))
        if line_code == src_code != in_force:
            # The receipt's rate ended before the invoice date (8 % until 31/12/2026): the invoice is at the rate that
            # followed. The form fills each line with the receipt's code; the printed total the person types still has to
            # match (_printed), so a wrong invoice date shows up there.
            row.lotus_line_vat = line_code = in_force
        allowed = {src_code, in_force}
        ordered = str(frappe.db.get_value('Purchase Order Item', src.purchase_order_item, 'lotus_line_vat') or '') if src.get('purchase_order_item') else ''
        if ordered and ordered != src_code:
            # Ordered at 8 %, invoiced in 2026 at 8 %, received in 2027 at 10 %: the invoice keeps the rate of its own date.
            try:
                received_on = frappe.db.get_value('Purchase Receipt', src.parent, 'posting_date')
                if finance_rules.vat_code_on(ordered, bill_date) == ordered and finance_rules.vat_code_on(ordered, received_on) == src_code:
                    allowed.add(ordered)
            except ValueError:
                pass
        if frappe.get_cached_value('Item', row.item_code, 'is_fixed_asset') and (
                abs(flt(row.rate) - flt(src.rate)) > 0.005
                or setup.vat_in_cost() and line_code not in allowed):
            # The asset's value is taken at receipt. A rate that ended in between is the one exception: its VAT difference
            # becomes a cost of the period (finance.invoice_cost). Any other difference would stay on 3388/33881.
            frappe.throw('%s là tài sản cố định: hóa đơn khác giá hoặc thuế suất với phiếu nhận chưa ghi tự động được. Ghi hóa đơn theo '
                         'giá và thuế của phiếu nhận, rồi điều chỉnh nguyên giá ở Tài chính › Tài sản cố định.' % (src.item_name or src.item_code))
        row.lotus_line_freight = flt(src.get('lotus_line_freight')) * qty / (flt(src.qty) or 1)
        if item_kind(frappe.get_cached_doc('Item', row.item_code), src.get('lotus_purchase_kind')) == 'Service':
            row.expense_account = mapping['overhead_service'] if row.get('lotus_farm') else mapping['admin_expense']
        kept.append(row)
    if not kept or picked is not None and seen != {k for k, v in picked.items() if v is not None}:
        frappe.throw('Dòng nghiệm thu đã thay đổi hoặc đã có hóa đơn. Tải lại.')
    pi.set('items', kept)
    return pi


def _service_items(service_lines, company):
    from lotus_farm.finance.payments import _dims
    mapping = setup.mapping()
    cost_center = frappe.get_cached_value('Company', company, 'cost_center')
    uom = frappe.db.get_value('UOM', 'Nos') and 'Nos' or frappe.get_all('UOM', pluck='name', limit_page_length=1)[0]
    items = []
    for index, line in enumerate(service_lines, start=1):
        amount = flt(line.get('amount'))
        if amount <= 0:
            frappe.throw('Dòng chi phí %d: số tiền phải lớn hơn 0.' % index)
        production = line.get('cost') != 'admin'
        dims = _dims(line)
        if production and not dims.get('lotus_farm'):
            frappe.throw('Dòng chi phí %d: chi phí sản xuất phải chọn vườn (và lô nếu có).' % index)
        items.append(dict(item_name=str(line.get('description') or 'Chi phí dịch vụ')[:140], description=line.get('description') or 'Chi phí dịch vụ',
                          qty=1, rate=amount, uom=uom, conversion_factor=1, lotus_line_vat=str(line.get('vat_code') or '').strip() or None,
                          expense_account=mapping['overhead_service'] if production else mapping['admin_expense'], cost_center=cost_center, **dims))
    return items


@frappe.whitelist(methods=['POST'])
def create(receipts=None, lines=None, service_lines=None, supplier=None, bill_no=None, series=None, tax_code=None, bill_date=None,
           due_date=None, posting_date=None, printed_total=None, printed_vat=None, files=None, client_key=None, vat_code=None):
    """Ghi một hóa đơn NCC. receipts: phiếu nhận theo đơn và/hoặc… (xem dưới); lines: [{source_item, qty, rate, vat_code,
    variance_reason}] for receipt lines (omit to invoice everything unbilled); service_lines: [{description, amount,
    cost, vat_code, lotus_farm…}]. Returns {invoice, amount, rounding_adjustment, warnings}.

    One invoice takes purchase receipts (with optional service lines), or Mua nhanh receipts, or service lines only."""
    setup.require_post()
    setup.require_enabled()
    from lotus_farm.controls import lock
    from lotus_farm.finance import payments
    from lotus_farm.procurement import apply_line_taxes, idempotent
    company = setup.company()
    receipts, service_lines, files = _list(receipts), _list(service_lines), _list(files)
    picked = None
    if lines not in (None, ''):
        picked = {}
        for line in _list(lines):
            if not isinstance(line, dict) or not line.get('source_item'):
                frappe.throw('Dòng hóa đơn không hợp lệ.')
            picked[line['source_item']] = line
    bill_no, series = str(bill_no or '').strip(), str(series or '').strip()
    if not bill_no:
        frappe.throw('Nhập số hóa đơn của nhà cung cấp.')
    if not bill_date:
        frappe.throw('Nhập ngày hóa đơn.')
    if not receipts and not service_lines:
        frappe.throw('Chọn ít nhất một phiếu nhận, hoặc nhập dòng chi phí dịch vụ.')
    posting_date = posting_date or bill_date
    lock('Company', company)
    prs, entries = _split(receipts)
    if prs and entries:
        frappe.throw('Một hóa đơn chưa gồm được cả phiếu nhận theo đơn và phiếu Mua nhanh. Chọn riêng từng loại phiếu.')
    if entries and service_lines:
        frappe.throw('Hóa đơn cho phiếu Mua nhanh không kèm dòng dịch vụ. Lập hóa đơn dịch vụ riêng.')
    suppliers = {d.supplier for d in prs} | {d.get('lotus_supplier') for d in entries} | ({supplier} if supplier else set())
    if len(suppliers) != 1 or None in suppliers:
        frappe.throw('Các phiếu nhận phải cùng một nhà cung cấp với hóa đơn.')
    supplier = suppliers.pop()
    payload = [sorted(receipts), sorted(picked.items()) if picked else None, service_lines, supplier, bill_no, series, tax_code, str(bill_date),
               str(due_date or ''), str(posting_date), printed_total, printed_vat, vat_code]
    token, fingerprint, old = idempotent(PI, client_key or 'auto:' + rules.digest(payload), payload, company)
    if old:
        return dict(invoice=old, amount=flt(frappe.db.get_value(PI, old, 'grand_total')), rounding_adjustment=0, warnings=[])
    for doc in prs:
        lock(PR, doc.name)
    for doc in entries:
        lock(SE, doc.name)
    payments._duplicate(supplier, bill_no, series=series or next((d.get('lotus_einvoice_series') for d in entries if d.get('lotus_einvoice_series')), None),
                        linked_entries=[d.name for d in entries])
    setup.check_cutover(posting_date)
    posting.check_open(company, posting_date, PI)
    warnings = []
    if entries:
        # Goods already in stock against 3388: the invoice only moves 3388 to the supplier (payments._invoice_stock_entries).
        result = payments._invoice_stock_entries([d.name for d in entries], bill_no, bill_date, due_date, posting_date, vat_code or 'KCT')
        pi = frappe.get_doc(PI, result['invoice'])
        values = dict(lotus_procurement_key=token, lotus_procurement_hash=fingerprint)
        if pi.meta.has_field('lotus_einvoice_series'):
            values.update(lotus_einvoice_series=series or pi.get('lotus_einvoice_series'), lotus_cqt_code=str(tax_code or '').strip() or None)
            if flt(printed_total):
                gap, ok = rules.printed_total_gap(flt(pi.grand_total), flt(printed_total), len(pi.items))
                if not ok:
                    frappe.throw('Tổng hóa đơn theo phiếu Mua nhanh %s đ khác tổng in %s đ. Bổ sung giá cho phiếu nhập trước khi lập hóa đơn.'
                                 % (_vnd(pi.grand_total), _vnd(printed_total)))
                values.update(lotus_invoice_total=flt(printed_total), lotus_invoice_vat=flt(printed_vat) or None)
        pi.db_set(values, update_modified=False)
        adjustment = 0
    else:
        m = setup.mapping()
        if prs:
            from lotus_farm.procurement import renumber
            pi = _receipt_invoice(prs, picked, vat_code, bill_date)
            for item in _service_items(service_lines, company):
                pi.append('items', item)
            renumber(pi)
        else:
            pi = frappe.get_doc(dict(doctype=PI, company=company, supplier=supplier, update_stock=0, conversion_rate=1,
                                     currency=frappe.get_cached_value('Company', company, 'default_currency'),
                                     items=_service_items(service_lines, company)))
            for row in pi.items:
                row.lotus_line_vat = row.get('lotus_line_vat') or str(vat_code or 'KCT')
        pi.update(dict(bill_no=bill_no, bill_date=bill_date, posting_date=posting_date, set_posting_time=1,
                       due_date=payments._due(bill_date, due_date), credit_to=m['payable_supplier'], update_stock=0,
                       lotus_procurement_key=token, lotus_procurement_hash=fingerprint, allocate_advances_automatically=1))
        if prs:
            apply_line_taxes(pi)  # household: goods on 33881 "Valuation and Total", services into their own cost, never 1331
        else:
            _service_taxes(pi, bill_date)
        pi.set_missing_values()
        pi.calculate_taxes_and_totals()
        adjustment = _printed(pi, printed_total, printed_vat)
        if pi.meta.has_field('lotus_einvoice_series'):
            pi.update(dict(lotus_einvoice_series=series or None, lotus_cqt_code=str(tax_code or '').strip() or None,
                           lotus_invoice_total=flt(printed_total) or None, lotus_invoice_vat=flt(printed_vat) or None))
        pi.set_advances()
        pi.set('payment_schedule', [])
        pi.flags.ignore_permissions = True
        from erpnext.controllers.status_updater import OverAllowanceError
        try:
            pi.insert()
            pi.submit()
        except OverAllowanceError:
            frappe.throw('Giá trị hóa đơn vượt quá mức cho phép so với đơn mua (trên 2 lần). Kiểm tra lại đơn giá; nếu đúng, lập đơn mua bổ sung.')
        posting.record(PI, pi.name, 'Purchase Invoice', pi, amount=pi.grand_total, source_hash=','.join(sorted(receipts)) or bill_no)
        if adjustment:
            warnings.append('Đã ghi theo tổng in trên hóa đơn; phần làm tròn %s đ hiện ở dòng "Làm tròn theo hóa đơn".' % _vnd(adjustment))
    from lotus_farm import stock_attachments
    for url in files:
        stock_attachments.attach_uploaded(pi, url)
    return dict(invoice=pi.name, amount=flt(pi.grand_total), rounding_adjustment=adjustment, warnings=warnings)


def _settlements(doc):
    """Everything that settled (or is about to settle) this invoice from another document."""
    found = []
    for row in frappe.db.sql('''select p.name, p.docstatus, r.allocated_amount from `tabPayment Entry Reference` r
            join `tabPayment Entry` p on p.name = r.parent where r.reference_doctype = %s and r.reference_name = %s and p.docstatus < 2''',
                             (PI, doc.name), as_dict=True):
        found.append(dict(doctype='Payment Entry', name=row.name, docstatus=row.docstatus, amount=flt(row.allocated_amount),
                          kind='Phiếu chi' if row.docstatus == 1 else 'Phiếu chi đang ký'))
    for row in frappe.db.sql('''select j.name, j.docstatus, sum(a.debit_in_account_currency - a.credit_in_account_currency) amount
            from `tabJournal Entry Account` a join `tabJournal Entry` j on j.name = a.parent
            where a.reference_type = %s and a.reference_name = %s and j.docstatus < 2 group by j.name, j.docstatus''', (PI, doc.name), as_dict=True):
        found.append(dict(doctype='Journal Entry', name=row.name, docstatus=row.docstatus, amount=flt(row.amount),
                          kind='Chi hộ / bút toán' if row.docstatus == 1 else 'Chi hộ đang ký'))
    for row in frappe.get_all(PI, filters={'return_against': doc.name, 'docstatus': ['<', 2]}, fields=['name', 'docstatus', 'grand_total']):
        found.append(dict(doctype=PI, name=row.name, docstatus=row.docstatus, amount=abs(flt(row.grand_total)), kind='Hóa đơn điều chỉnh trả hàng'))
    for row in doc.get('advances') or []:
        if flt(row.allocated_amount) > 0:
            found.append(dict(doctype=row.reference_type, name=row.reference_name, docstatus=1, amount=flt(row.allocated_amount), kind='Tạm ứng đã cấn trừ'))
    return found


def cancel_blockers(doc):
    """Why this invoice cannot be cancelled now (R17): payments, vouchers being signed, on-behalf payments,
    adjustment invoices, advances already set off."""
    seen, out = set(), []
    for row in _settlements(doc):
        if (row['doctype'], row['name']) not in seen:
            seen.add((row['doctype'], row['name']))
            out.append('%s %s' % (row['kind'], row['name']))
    return out


def guard_cancel(doc, method=None):
    """before_cancel of Purchase Invoice: the same refusal whichever screen cancels it (Lotus, Desk, REST)."""
    from lotus_farm.finance.native_guards import _enabled_for
    if not _enabled_for(doc):
        return
    blockers = cancel_blockers(doc)
    if blockers:
        frappe.throw('Hóa đơn %s đã có thanh toán hoặc chứng từ liên quan: %s. Đảo phiếu chi trước, hoặc lập hóa đơn điều chỉnh.'
                     % (doc.name, '; '.join(blockers[:5])))


@frappe.whitelist(methods=['POST'])
def cancel(name, reason, modified=None):
    """Hủy hóa đơn chưa có thanh toán, có lý do (FR-055). Mua nhanh receipts it covered wait for an invoice again."""
    setup.require_post()
    from lotus_farm.controls import lock
    reason = str(reason or '').strip()
    if not 3 <= len(reason) <= 500:
        frappe.throw('Ghi lý do hủy hóa đơn (3–500 ký tự).')
    doc = frappe.get_doc(PI, name)
    if doc.company != setup.company():
        frappe.throw('Hóa đơn không thuộc công ty của Tài chính.')
    lock('Company', doc.company)
    lock(PI, name)
    doc.reload()
    if doc.docstatus != 1 or modified and str(doc.modified) != str(modified):
        frappe.throw('Hóa đơn đã thay đổi hoặc chưa ghi sổ. Tải lại.')
    guard_cancel(doc)
    posting.check_open(doc.company, doc.posting_date, PI)
    released = []
    if frappe.get_meta(SE).has_field('lotus_purchase_invoice'):
        # The receipts point at the invoice with a Link field; ERPNext refuses to cancel a linked document.
        for entry in frappe.get_all(SE, filters={'lotus_purchase_invoice': doc.name}, pluck='name'):
            frappe.db.set_value(SE, entry, 'lotus_purchase_invoice', None, update_modified=False)
            released.append(entry)
    doc.flags.ignore_permissions = True
    previous = getattr(frappe.flags, 'lotus_finance_reverse', False)
    frappe.flags.lotus_finance_reverse = True
    try:
        doc.cancel()
    finally:
        frappe.flags.lotus_finance_reverse = previous
    if doc.meta.has_field('lotus_cancel_reason'):
        frappe.db.set_value(PI, doc.name, 'lotus_cancel_reason', reason)
    for record in frappe.get_all(posting.POSTING, filters={'voucher_type': PI, 'voucher_name': doc.name}, pluck='name'):
        frappe.db.set_value(posting.POSTING, record, dict(state='Reversed', active_key=None, reason=reason[:500]), update_modified=False)
    doc.add_comment('Comment', 'Hủy hóa đơn: ' + reason)
    return dict(name=doc.name, state='Đã hủy', released=released)


def _ledger_outstanding(names, as_of):
    """Outstanding of invoices on a closing date from the payment ledger (today's balance is not history)."""
    if not names:
        return {}
    rows = frappe.db.sql('''select against_voucher_no name, sum(amount) amount from `tabPayment Ledger Entry`
        where against_voucher_type = %s and against_voucher_no in %s and delinked = 0 and posting_date <= %s
        group by against_voucher_no''', (PI, tuple(names), getdate(as_of)), as_dict=True)
    return {r.name: flt(r.amount) for r in rows}


@frappe.whitelist()
def invoices(supplier=None, status=None, as_of=None, from_date=None, to_date=None, limit=200, offset=0):
    """Posted and cancelled supplier invoices with their state on the closing date (default today)."""
    setup.require_view()
    from lotus_farm import purchase_status
    day = getdate(as_of or nowdate())
    filters = {'company': setup.company(), 'docstatus': ['in', [1, 2]], 'posting_date': ['<=', day]}
    if supplier:
        filters['supplier'] = supplier
    if from_date:
        filters['posting_date'] = ['between', [getdate(from_date), getdate(to_date) if to_date else day]]
    extra = [f for f in ('lotus_einvoice_series', 'lotus_invoice_total') if frappe.get_meta(PI).has_field(f)]
    rows = frappe.get_all(PI, filters=filters, fields=['name', 'supplier', 'supplier_name', 'bill_no', 'bill_date', 'posting_date', 'due_date', 'grand_total',
                                                       'outstanding_amount', 'docstatus', 'is_return', 'return_against', 'modified', *extra],
                          order_by='posting_date desc, name desc', limit_page_length=0)
    left = _ledger_outstanding([r.name for r in rows if r.docstatus == 1], day)
    out = []
    for r in rows:
        outstanding = left.get(r.name, 0.0) if r.docstatus == 1 else 0.0
        state = purchase_status.invoice_state(r.docstatus, r.grand_total, outstanding, r.due_date, day)
        if status and status not in ('Tất cả', state):
            continue
        out.append(dict(name=r.name, supplier=r.supplier, supplier_name=r.supplier_name or r.supplier, bill_no=r.bill_no or '',
                        series=r.get('lotus_einvoice_series') or '', bill_date=str(r.bill_date or ''), date=str(r.posting_date),
                        due_date=str(r.due_date or ''), amount=flt(r.grand_total), outstanding_amount=outstanding, status=state,
                        docstatus=r.docstatus, is_return=cint(r.is_return), return_against=r.return_against or '', modified=str(r.modified)))
    start, size = max(0, cint(offset)), max(1, min(cint(limit) or 200, 500))
    return dict(rows=out[start:start + size], total=len(out), as_of=str(day),
                outstanding=sum(r['outstanding_amount'] for r in out if not r['is_return']))


@frappe.whitelist()
def detail(name):
    """One invoice as it was printed by the supplier, with its receipts, files, settlements and what may be done."""
    setup.require_view()
    from urllib.parse import urlencode
    from lotus_farm import purchase_status
    doc = frappe.get_doc(PI, name)
    if doc.company != setup.company():
        frappe.throw('Hóa đơn không thuộc công ty của Tài chính.')
    receipts = sorted({r.purchase_receipt for r in doc.items if r.get('purchase_receipt')})
    quick = frappe.get_all(SE, filters={'lotus_purchase_invoice': doc.name}, pluck='name') if frappe.get_meta(SE).has_field('lotus_purchase_invoice') else []
    taxes = [dict(description=t.description, amount=flt(t.tax_amount), account=t.account_head, in_cost=t.category != 'Total',
                  rounding=str(t.description or '').startswith('Làm tròn')) for t in doc.taxes]
    settlements = _settlements(doc)
    can_post = setup.can_post() if hasattr(setup, 'can_post') else True
    return dict(name=doc.name, doctype=PI, supplier=doc.supplier, supplier_name=doc.supplier_name or doc.supplier, company=doc.company,
                bill_no=doc.bill_no or '', series=doc.get('lotus_einvoice_series') or '', tax_code=doc.get('lotus_cqt_code') or '',
                bill_date=str(doc.bill_date or ''), date=str(doc.posting_date), due_date=str(doc.due_date or ''), docstatus=doc.docstatus,
                modified=str(doc.modified), currency=doc.currency, is_return=cint(doc.is_return), return_against=doc.return_against or '',
                net=flt(doc.net_total), vat=sum(t['amount'] for t in taxes if 'GTGT' in str(t['description'] or '')),
                amount=flt(doc.grand_total), outstanding_amount=flt(doc.outstanding_amount) if doc.docstatus == 1 else 0,
                printed_total=flt(doc.get('lotus_invoice_total')), printed_vat=flt(doc.get('lotus_invoice_vat')),
                rounding_adjustment=sum(t['amount'] for t in taxes if t['rounding']),
                status=purchase_status.invoice_state(doc.docstatus, doc.grand_total, doc.outstanding_amount, doc.due_date, nowdate()),
                cancel_reason=doc.get('lotus_cancel_reason') or '', taxes=taxes, settlements=settlements,
                receipts=receipts, quick_receipts=quick, cost_adjustments=invoice_cost.adjustments_of(doc.name),
                files=_files(PI, [doc.name]) + _files(PR, receipts) + _files(SE, quick),
                print_url='/lotus/in-hoa-don?' + urlencode({'name': doc.name}),
                can_cancel=doc.docstatus == 1 and can_post and not settlements, can_pay=doc.docstatus == 1 and can_post and not doc.is_return and flt(doc.outstanding_amount) > 0.5,
                can_credit=doc.docstatus == 1 and can_post and not doc.is_return,
                items=[dict(line=r.name, item=r.item_code or '', item_name=r.item_name, qty=flt(r.qty), uom=r.uom, rate=flt(r.rate), amount=flt(r.amount),
                            vat_code=r.get('lotus_line_vat') or 'KCT', variance_reason=r.get('lotus_variance_reason') or '',
                            receipt=r.get('purchase_receipt') or '', order=r.get('purchase_order') or '') for r in doc.items])
