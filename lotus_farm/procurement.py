"""Purchase workspace over ERPNext documents, shared by desktop, warehouse and buying PWA."""
import json
from copy import deepcopy
import frappe
from frappe.utils import flt, getdate, nowdate
from lotus_farm import procurement_rules as rules
from lotus_farm.warehouse import _company, _warehouse
from lotus_farm.controls import lock


def parse(value):
    return frappe.parse_json(value) if isinstance(value, str) else deepcopy(value)


def access(company):
    from lotus_farm.purchasing import access as check
    check()
    _company(company)


def document(dt, name, company=None, permission='read', for_update=False):
    doc = frappe.get_doc(dt, name, for_update=for_update)
    doc.check_permission(permission)
    _company(doc.company)
    if company and doc.company != company:
        frappe.throw('Chứng từ không thuộc công ty đang chọn.')
    return doc


def item_kind(item, selected=None):
    try:
        return rules.kind_for(item.as_dict() if hasattr(item, 'as_dict') else item, selected)
    except ValueError as exc:
        frappe.throw(str(exc))


def vat_now(code, day=None):
    """The VAT code that applies today to a price quoted earlier: a rate that ended gives way to the rate that followed
    (8 % until 31/12/2026, then 10 %), so quotes are compared and ordered at the VAT that will be invoiced."""
    from lotus_farm.finance import rules as finance_rules
    try:
        return finance_rules.vat_code_on(code or 'KCT', day or nowdate())
    except ValueError:
        return str(code or 'KCT')


def line_fields(item, row):
    vat = str(row.get('vat_code') or row.get('lotus_line_vat') or 'KCT')
    try:
        rules.quote_total(row.get('qty') or 1, row.get('rate'), 1, vat, row.get('freight') or row.get('lotus_line_freight') or 0)
    except ValueError as exc:
        frappe.throw(str(exc))
    farm=row.get('lotus_farm')
    if farm:frappe.get_doc('Farm',farm).check_permission('read')
    return dict(lotus_farm=farm or None,lotus_purchase_kind=item_kind(item, row.get('kind') or row.get('lotus_purchase_kind')),
                lotus_line_vat=vat, lotus_line_freight=flt(row.get('freight') or row.get('lotus_line_freight')),
                lotus_quote_reason=str(row.get('reason') or row.get('lotus_quote_reason') or '')[:500])


def line_tax_template(company, account, rate, suffix=''):
    """The Item Tax Template of one VAT rate on one account (ERPNext 16 rebuilds every line's tax map from its template
    at each calculation, so the template is the only durable per-line input)."""
    title='Lotus purchase VAT '+str(int(rate))+'%'+suffix
    template=frappe.db.get_value('Item Tax Template',{'company':company,'title':title},'name')
    if not template:
        template=frappe.get_doc(dict(doctype='Item Tax Template',title=title,company=company,
            taxes=[dict(tax_type=account,tax_rate=rate)])).insert(ignore_permissions=True).name
    tax=frappe.get_doc('Item Tax Template',template)
    if len(tax.taxes)!=1 or tax.taxes[0].tax_type!=account or flt(tax.taxes[0].tax_rate)!=rate:
        frappe.throw('Mẫu thuế '+template+' đã thay đổi. Kế toán kiểm tra lại cấu hình VAT đầu vào.')
    return template


def renumber(doc, field='items'):
    """Rows kept, split or added by Lotus keep the idx they came with. ERPNext 16 spreads valuation charges by idx (last
    row takes the remainder; capitalised charges are keyed by idx), so duplicate or missing numbers over-capitalise VAT and
    freight: number the rows 1..n again."""
    for index, row in enumerate(doc.get(field) or [], start=1):
        row.idx = index


def _tax_date(doc):
    """The date whose VAT rates a document uses. A return or credit note keeps the rates of what it reverses: code 8 %
    ends on 31/12/2026, and a 2026 purchase returned in 2027 still carries it."""
    if doc.get('is_return') and doc.get('return_against') and doc.doctype in ('Purchase Receipt', 'Purchase Invoice'):
        fields = ['bill_date', 'posting_date'] if doc.doctype == 'Purchase Invoice' else ['posting_date']
        original = frappe.db.get_value(doc.doctype, doc.return_against, fields, as_dict=True)
        if original:
            return original.get('bill_date') or original.get('posting_date')
    return doc.get('bill_date') or doc.get('posting_date') or doc.get('transaction_date')


def _capital(row):
    """A line whose cost goes into stock or an asset."""
    if not row.get('item_code'):
        return False
    item = frappe.get_cached_value('Item', row.item_code, ['is_stock_item', 'is_fixed_asset'], as_dict=True)
    return bool(item and (item.is_stock_item or item.is_fixed_asset))


def _line_costs(doc, lines, cost_center):
    """VAT and freight that are a cost of the line itself (household business, lines without stock value): one 'Total'
    row per kind, rate, expense account and farm/lô, so they reach the same cost as the line (costing by lô reads those
    dimensions). lines = [(row, 'vat' | 'freight', amount)]."""
    from lotus_farm.finance import setup, rules as finance_rules
    mapping = setup.mapping()
    dims = [f for f in finance_rules.DIM_FIELDS if frappe.get_meta('Purchase Taxes and Charges').has_field(f)]
    groups = {}
    for row, kind, amount in lines:
        if not flt(amount):
            continue
        account = row.get('expense_account') or (mapping.get('overhead_service') if row.get('lotus_farm') else mapping.get('admin_expense'))
        if not account:
            frappe.throw('Thiết lập tài khoản chi phí dịch vụ tại Tài chính – Kế toán.')
        key = (kind, str(row.get('lotus_line_vat') or 'KCT') if kind == 'vat' else '', account) + tuple(row.get(f) or None for f in dims)
        groups[key] = groups.get(key, 0) + flt(amount)
    for key, amount in groups.items():
        kind, code, account = key[:3]
        extra = {f: v for f, v in zip(dims, key[3:]) if v}
        doc.append('taxes', dict(charge_type='Actual', account_head=account, tax_amount=flt(amount, 0), category='Total', add_deduct_tax='Add',
                                 cost_center=cost_center, **extra,
                                 description='Thuế GTGT %s%% (tính vào chi phí)' % code if kind == 'vat' else 'Vận chuyển (tính vào chi phí)'))


def apply_line_taxes(doc):
    """Native item tax overrides allow mixed VAT. Freight is an explicit native charge.

    Household business (Cài đặt Tài chính): VAT and freight are part of what is bought, line by line, the same way on
    the order, the receipt, its returns, the invoice and its credit notes (whatever other lines a document has):
    - Goods and assets carry their VAT on the valuation clearing account 33881 ("Valuation and Total", per-line
      templates) and their freight on 3388, cleared with the goods and wholly into stock.
    - Lines without stock value (services) carry no 33881 template: a receipt credits 33881 and 3388 only for what it
      capitalises, so their VAT and freight are a cost of the line itself (_line_costs).
    - Not on one account: ERPNext 16 rebuilds each line's tax map per account, and a freight row sharing 33881 with the
      per-line VAT row fails "Item Wise Tax Details do not match" as soon as one line is 0 % (VPS test site, 10/11/2026).
    Deductible VAT goes to 1331 per line, freight to 6277."""
    from lotus_farm.finance import setup, rules as finance_rules
    mapping = setup.mapping()
    on_date = _tax_date(doc)
    try:
        if doc.doctype in ('Purchase Receipt', 'Purchase Order') and not doc.get('is_return'):
            # Goods received after a rate ended (8 % until 31/12/2026) carry the rate in force on the receipt date: the
            # receiver has no VAT field, and the signed order cannot change. The invoice brings the actual rate anyway.
            # An order saved after the end (from a 2026 quote, or a December draft) is placed at the rate that followed.
            for row in doc.items:
                row.lotus_line_vat = finance_rules.vat_code_on(row.get('lotus_line_vat') or 'KCT', on_date)
        rates = [finance_rules.vat_rate(r.get('lotus_line_vat') or 'KCT', on_date) * 100 for r in doc.items]
    except ValueError as exc:
        frappe.throw(str(exc))
    in_cost = setup.vat_in_cost() and doc.doctype in ('Purchase Order', 'Purchase Receipt', 'Purchase Invoice')
    capital = [_capital(r) for r in doc.items]
    shipping = sum(flt(r.get('lotus_line_freight')) for r in doc.items)
    cc = frappe.get_cached_value('Company', doc.company, 'cost_center')
    doc.taxes_and_charges = None
    doc.set('taxes', [])
    if in_cost and any(capital):
        account = setup.valuation_tax_account(doc.company)
        goods = any(rate for rate, cap in zip(rates, capital) if cap)
        if goods and not account:
            frappe.throw('Thiết lập tài khoản VAT đầu vào tại Tài chính – Kế toán.')
        for row, rate, cap in zip(doc.items, rates, capital):
            # item_tax_rate is an ERPNext output and gets rebuilt during validation.
            # A native Item Tax Template is the durable, per-line input.
            row.item_tax_template = line_tax_template(doc.company, account, rate, ' (giá vốn)') if cap and goods else None
            row.item_tax_rate = json.dumps({account: rate if cap else 0}) if account else '{}'
        if goods:
            doc.append('taxes', dict(charge_type='On Net Total', account_head=account, rate=0, description='Thuế GTGT theo dòng (tính vào giá vốn)',
                                     category='Valuation and Total', add_deduct_tax='Add', cost_center=cc))
        goods_freight = sum(flt(row.get('lotus_line_freight')) for row, cap in zip(doc.items, capital) if cap)
        if goods_freight:
            freight_account = mapping.get('received_not_billed')
            if not freight_account:
                frappe.throw('Thiết lập tài khoản hàng đã nhận chưa có hóa đơn (3388) tại Tài chính – Kế toán.')
            doc.append('taxes', dict(charge_type='Actual', account_head=freight_account, tax_amount=goods_freight, description='Vận chuyển',
                                     category='Valuation and Total', add_deduct_tax='Add', cost_center=cc, allocate_full_amount_to_stock_items=1))
        _line_costs(doc, [(row, 'vat', flt(row.qty) * flt(row.rate) * rate / 100) for row, rate, cap in zip(doc.items, rates, capital) if not cap]
                    + [(row, 'freight', row.get('lotus_line_freight')) for row, cap in zip(doc.items, capital) if not cap], cc)
        return
    if in_cost:
        for row in doc.items:
            row.item_tax_template = None
            row.item_tax_rate = '{}'
        _line_costs(doc, [(row, 'vat', flt(row.qty) * flt(row.rate) * rate / 100) for row, rate in zip(doc.items, rates)]
                    + [(row, 'freight', row.get('lotus_line_freight')) for row in doc.items], cc)
        return
    else:
        account = mapping.get('input_vat')
        if any(rates) and not account:
            frappe.throw('Thiết lập tài khoản VAT đầu vào tại Tài chính – Kế toán.')
        for row, rate in zip(doc.items, rates):
            row.item_tax_template = line_tax_template(doc.company, account, rate) if any(rates) else None
            row.item_tax_rate = json.dumps({account: rate}) if account else '{}'
        if any(rates):
            doc.append('taxes', dict(charge_type='On Net Total', account_head=account, rate=0, description='Thuế GTGT theo dòng',
                                     category='Total', add_deduct_tax='Add', cost_center=cc))
    if shipping:
        freight_account = mapping.get('overhead_service')
        if not freight_account:
            frappe.throw('Thiết lập tài khoản dịch vụ vận chuyển tại Tài chính – Kế toán.')
        doc.append('taxes', dict(charge_type='Actual', account_head=freight_account, tax_amount=shipping,
                                description='Vận chuyển', category='Total', add_deduct_tax='Add', cost_center=cc))


def _line_rates(row):
    try:
        rates = json.loads(row.get('item_tax_rate') or '{}')
    except ValueError:
        return {}
    return rates if isinstance(rates, dict) else {}


def _match_invoice_total(pi, invoice_total):
    """Make the invoice equal, to the đồng, the total printed by the supplier. Decimal rates leave a few đồng of rounding:
    that goes in an explicit adjustment row with the VAT (into cost for a household, else input VAT). A bigger gap is a
    wrong quantity, price or VAT rate and is refused."""
    if invoice_total in (None, '', 0, '0'):
        return
    target = round(flt(invoice_total))
    diff = round(target - flt(pi.grand_total), 2)
    if abs(diff) < 0.005:
        return
    if abs(diff) > max(5, len(pi.items)):
        vnd = lambda n: '{:,.0f}'.format(n).replace(',', '.')
        frappe.throw('Tổng hóa đơn tính ra {} đ khác tổng cộng in trên hóa đơn {} đ. Kiểm tra số lượng, đơn giá và thuế suất.'.format(vnd(flt(pi.grand_total)), vnd(target)))
    vat = next((t for t in pi.taxes if t.charge_type == 'On Net Total'), None)
    # Deductible VAT: the đồng of rounding is VAT too, when every line is taxed. A line at 0 % (KCT) on the same account
    # makes ERPNext 16 refuse the invoice ("Item Wise Tax Details do not match") once an Actual row shares that account,
    # so the rounding then goes to the round-off account. VAT carried into cost (household): the goods are already valued
    # at receipt, so the rounding is a small cost on the round-off account rather than a stray balance on 33881.
    if vat and vat.category == 'Total' and all(flt(_line_rates(row).get(vat.account_head)) for row in pi.items):
        account, cost_center = vat.account_head, vat.cost_center
    else:
        account = frappe.get_cached_value('Company', pi.company, 'round_off_account')
        cost_center = frappe.get_cached_value('Company', pi.company, 'round_off_cost_center') or frappe.get_cached_value('Company', pi.company, 'cost_center')
    if not account:
        frappe.throw('Thiết lập tài khoản làm tròn của công ty để khớp tổng hóa đơn.')
    pi.append('taxes', dict(charge_type='Actual', account_head=account, tax_amount=diff, description='Làm tròn theo hóa đơn',
                            category='Total', add_deduct_tax='Add', cost_center=cost_center))
    pi.calculate_taxes_and_totals()


def idempotent(dt, key, payload, company):
    if not key or len(str(key)) > 140:
        frappe.throw('Thiếu mã yêu cầu. Tải lại biểu mẫu.')
    token = rules.digest([frappe.session.user, dt, key])
    fingerprint = rules.digest(payload)
    lock('Company', company)
    old = frappe.db.get_value(dt, {'lotus_procurement_key': token}, ['name', 'lotus_procurement_hash'], as_dict=True, for_update=True)
    if old:
        document(dt, old.name, company, for_update=True)
        if old.lotus_procurement_hash != fingerprint:
            frappe.throw('Mã yêu cầu đã dùng với nội dung khác. Mở lại chứng từ '+old.name)
    return token, fingerprint, old.name if old else None


@frappe.whitelist()
def bootstrap(company=None):
    from lotus_farm.purchasing import bootstrap as purchasing_bootstrap
    from lotus_farm.warehouse_buying_lite import setup
    info = purchasing_bootstrap()
    if not company:
        return info
    access(company)
    data = setup(company)
    from lotus_farm.finance import setup as finance
    data.update(session=info, kinds=rules.KIND_LABELS, can_finance=finance.can_post() and company == finance.company(),
                can_view_finance=(finance.can_view() or bool(set(frappe.get_roles()) & {'Lotus Purchase Approver', 'Lotus Farm Manager'})) and company == finance.company(),
                can_quote=frappe.has_permission('Supplier Quotation','create'),
                can_need=frappe.has_permission('Material Request','create'),
                can_invoice=frappe.has_permission('Purchase Invoice','read'),
                can_quick=frappe.has_permission('Stock Entry','create'), vat_in_cost=finance.vat_in_cost(),
                farms=frappe.get_list('Farm',filters={'company':company},fields=['name','farm_name'],limit_page_length=0) if frappe.has_permission('Farm','read') else [])
    return data


@frappe.whitelist()
def quick_purchases(company):
    """Mua nhanh: goods bought and brought in without an order (Material Receipt, reason Purchase). The accountant
    invoices them later from Hóa đơn (finance.payments.make_goods_invoice), which links lotus_purchase_invoice."""
    access(company)
    if not frappe.has_permission('Stock Entry', 'read'):
        return []
    rows = frappe.get_list('Stock Entry', filters={'company': company, 'stock_entry_type': 'Material Receipt', 'lotus_receipt_reason': 'Purchase', 'docstatus': ['<', 2]},
                           fields=['name', 'posting_date', 'lotus_supplier', 'total_incoming_value', 'docstatus', 'remarks', 'owner',
                                   *(['lotus_purchase_invoice'] if frappe.get_meta('Stock Entry').has_field('lotus_purchase_invoice') else [])],
                           order_by='posting_date desc, creation desc', limit_page_length=500)
    names = {s.name: s.supplier_name for s in frappe.get_all('Supplier', filters={'name': ['in', list({r.lotus_supplier for r in rows if r.lotus_supplier})]}, fields=['name', 'supplier_name'])} if rows else {}
    from lotus_farm.warehouse import user_names
    people = user_names(r.owner for r in rows)
    stores = {}
    if rows:
        for r in frappe.get_all('Stock Entry Detail', filters={'parent': ['in', [r.name for r in rows]]}, fields=['parent', 't_warehouse'], limit_page_length=0):
            stores.setdefault(r.parent, set()).add(r.t_warehouse)
    # The stock entry keeps its original amount; posted price-only corrections
    # are separate vouchers in 3388 and must be reflected in Mua nhanh as well.
    corrections = {}
    if rows:
        from lotus_farm.finance import setup as finance_setup
        if company == finance_setup.company():
            from lotus_farm.finance.payments import _receipt_cost_corrections
            corrections = _receipt_cost_corrections([r.name for r in rows if r.docstatus == 1])
    return [dict(name=r.name, date=str(r.posting_date), supplier=r.lotus_supplier, supplier_name=names.get(r.lotus_supplier, r.lotus_supplier),
                 warehouse=', '.join(sorted(w for w in stores.get(r.name, ()) if w)), amount=flt(r.total_incoming_value) + (corrections.get(r.name, 0) if r.docstatus == 1 else 0), docstatus=r.docstatus,
                 price_correction=corrections.get(r.name, 0) if r.docstatus == 1 else 0,
                 source_type='Mua nhanh — không qua đề xuất/đơn',
                 invoice=r.get('lotus_purchase_invoice') or '', notes=r.remarks or '', owner=r.owner, created_by=people.get(r.owner, ''),
                 status='Nháp, chưa nhập kho' if r.docstatus == 0 else ('Đã có hóa đơn' if r.get('lotus_purchase_invoice') else 'Đã nhập kho, chờ hóa đơn'))
            for r in rows]


@frappe.whitelist()
def needs(company):
    access(company)
    result = []
    from lotus_farm import proposal_rules
    from lotus_farm.purchase_flow import proposal_totals
    names = frappe.get_list('Material Request', filters={'company': company, 'material_request_type': 'Purchase'}, pluck='name',
                            limit_page_length=0, order_by='transaction_date desc, name desc')
    totals = proposal_totals(names)
    from lotus_farm.purchase_proposal import _waiting_for_me
    mine = _waiting_for_me()
    for name in names:
        d = document('Material Request', name, company)
        # One board stage for every screen (spec 003, FR-026). Material Request has no document total; the estimate is the sum of its lines.
        stage = proposal_rules.stage(d.docstatus, d.get('lotus_proposal_state'), totals.get(name, {}).get('lines', []))
        result.append(dict(name=d.name, date=str(d.transaction_date), needed=str(d.schedule_date or ''), status=stage, stage=stage,
                           waiting_me=d.docstatus == 0 and d.name in mine,
                           signing_state=d.get('lotus_proposal_state') or '', department=d.get('lotus_department') or '',
                           docstatus=d.docstatus, amount=sum(flt(x.get('amount')) or flt(x.qty) * flt(x.rate) for x in d.items),
                           items=[dict(name=x.name, item=x.item_code, item_name=x.item_name, qty=flt(x.qty), uom=x.uom,
                                       factor=flt(x.conversion_factor), warehouse=x.warehouse, rate=flt(x.rate),
                                       kind=x.get('lotus_purchase_kind'), ordered_qty=flt(x.ordered_qty)) for x in d.items]))
    return result


@frappe.whitelist()
def quotations(company, request=None):
    access(company)
    result = []
    if not frappe.has_permission('Supplier Quotation', 'read'):
        return result
    for ref in frappe.get_list('Supplier Quotation', filters={'company': company, 'docstatus': ['<', 2]}, fields=['name'], limit_page_length=0, order_by='transaction_date desc, name desc'):
        d = document('Supplier Quotation', ref.name, company)
        for x in d.items:
            if request and x.material_request != request:
                continue
            values = rules.quote_total(x.qty, x.rate, x.conversion_factor or 1, vat_now(x.get('lotus_line_vat')), x.get('lotus_line_freight') or 0)
            result.append(dict(name=x.name, quotation=d.name, modified=str(d.modified), supplier=d.supplier, docstatus=d.docstatus,
                               item=x.item_code, item_name=x.item_name, qty=flt(x.qty), uom=x.uom, stock_uom=x.stock_uom,
                               rate=flt(x.rate) or None, factor=flt(x.conversion_factor), warehouse=x.warehouse,
                               request=x.material_request, request_line=x.material_request_item,
                               date=str(d.transaction_date), delivery_date=str(d.get('lotus_delivery_date') or ''),
                               valid_till=str(d.valid_till or ''), kind=x.get('lotus_purchase_kind'),
                               vat_code=x.get('lotus_line_vat') or 'KCT', **values))
    return result


def _offer_key(row):
    """Offers compete for one request line, or for one item when the quote is not tied to a request."""
    return row.get('request_line') or 'item:' + str(row.get('item'))


def _live_offers(company):
    """Priced, not cancelled, not expired quote lines grouped by _offer_key → [unit cost per stock unit]."""
    today, costs = getdate(nowdate()), {}
    for row in quotations(company):
        if row['valid_till'] and getdate(row['valid_till']) < today:
            continue
        costs.setdefault(_offer_key(row), []).append(row['unit_cost'])
    return costs


@frappe.whitelist()
def compare(company, request=None):
    """Price comparison: one row per request line (or item), one offer per supplier quote line.
    unit_cost is the landed cost (VAT and freight included) per stock unit."""
    access(company)
    today, groups, suppliers = getdate(nowdate()), {}, {}
    for r in quotations(company, request):
        if r['valid_till'] and getdate(r['valid_till']) < today:
            continue
        key = _offer_key(r)
        group = groups.setdefault(key, dict(key=key, item=r['item'], item_name=r['item_name'], stock_uom=r['stock_uom'],
                                            request=r['request'] or '', request_line=r['request_line'] or '', offers=[]))
        group['offers'].append(dict(quotation=r['quotation'], line=r['name'], supplier=r['supplier'], docstatus=r['docstatus'],
                                    unit_cost=r['unit_cost'], rate=r['rate'], qty=r['qty'], uom=r['uom'], stock_qty=r['stock_qty'],
                                    gross=r['gross'], vat_code=r['vat_code'], date=r['date'], modified=r['modified']))
        suppliers[r['supplier']] = frappe.get_cached_value('Supplier', r['supplier'], 'supplier_name') or r['supplier']
    requests = {}
    for name in sorted({g['request'] for g in groups.values() if g['request']}):
        d = document('Material Request', name, company)
        requests[name] = dict(name=name, approved=d.docstatus == 1, state='Đã duyệt' if d.docstatus == 1 else (d.get('lotus_proposal_state') or 'Nháp'),
                              lines={x.name: max(0, flt(x.stock_qty) - flt(x.ordered_qty)) for x in d.items},
                              selected={x.name: (x.get('lotus_selected_quote_item') or '', x.get('lotus_selection_reason') or '') for x in d.items})
    rows = []
    for group in groups.values():
        priced = [o for o in group['offers'] if o['unit_cost'] is not None]
        group['best_line'] = min(priced, key=lambda o: o['unit_cost'])['line'] if priced else ''
        info = requests.get(group['request'])
        group['need_qty'] = info['lines'].get(group['request_line']) if info else None
        group['approved'] = bool(info and info['approved'])
        # The quote line chosen earlier for this proposal line (choose_quote / select_quotes), when it is still on offer.
        chosen, why = (info['selected'].get(group['request_line']) if info else None) or ('', '')
        group['selected_line'] = chosen if any(o['line'] == chosen for o in group['offers']) else ''
        group['selected_reason'] = why if group['selected_line'] else ''
        rows.append(group)
    rows.sort(key=lambda g: (g['request'], g['item_name'] or ''))
    return dict(rows=rows, suppliers=[dict(name=k, label=v) for k, v in sorted(suppliers.items(), key=lambda s: s[1])],
                requests=[dict(name=r['name'], approved=r['approved'], state=r['state']) for r in requests.values()])


@frappe.whitelist(methods=['POST'])
def save_quotation(company, data, client_key, name=None, modified=None):
    access(company)
    data = parse(data)
    token, fingerprint, old = idempotent('Supplier Quotation', client_key, [data, name, modified], company)
    if old:
        return dict(name=old)
    from lotus_farm.warehouse_buying_lite import _lines
    supplier = frappe.get_doc('Supplier', data.get('supplier'))
    supplier.check_permission('read')
    if supplier.disabled:
        frappe.throw('Nhà cung cấp đã ngừng sử dụng.')
    d = document('Supplier Quotation', name, company, 'write') if name else frappe.new_doc('Supplier Quotation')
    if name and (d.docstatus or str(d.modified) != str(modified)):
        frappe.throw('Báo giá đã thay đổi hoặc đã xác nhận. Tải lại.')
    d.update(dict(company=company, supplier=supplier.name, transaction_date=data.get('date') or nowdate(),
                  valid_till=data.get('valid_till') or None, lotus_delivery_date=data.get('expected_date'),
                  currency=frappe.get_cached_value('Company', company, 'default_currency')))
    # Prices may be asked while the request is still being signed; orders still need an approved request.
    d.set('items', _lines(company, data.get('warehouse'), data.get('items'), data.get('expected_date'), allow_pending=True))
    apply_line_taxes(d)
    d.lotus_procurement_key, d.lotus_procurement_hash = token, fingerprint
    d.save() if name else d.insert()
    return dict(name=d.name, modified=str(d.modified))


def _remember_choice(request_item, quotation, quotation_item, reason):
    """The chosen quote line stays on the proposal line (outside the signed content), so an order made from the
    proposal later carries the supplier and the price (spec 003, FR-032)."""
    if not frappe.get_meta('Material Request Item').has_field('lotus_selected_quote'):
        return
    frappe.db.set_value('Material Request Item', request_item, dict(
        lotus_selected_quote=quotation or None, lotus_selected_quote_item=quotation_item or None,
        lotus_selection_reason=(str(reason or '').strip() or 'Giá thấp nhất trong các báo giá')[:500] if quotation else None), update_modified=False)


@frappe.whitelist(methods=['POST'])
def choose_quote(company, request, request_item, quotation=None, quotation_item=None, reason=None):
    """Chọn báo giá cho một dòng đề xuất (spec 003, FR-033): a reason is required unless it is the cheapest offer.
    Without a quotation the choice is cleared."""
    access(company)
    if not frappe.has_permission('Purchase Order', 'create'):
        frappe.throw('Chỉ người mua hàng được chọn báo giá.', frappe.PermissionError)
    lock('Material Request', request)
    source = document('Material Request', request, company)
    line = next((r for r in source.items if r.name == request_item), None)
    if source.docstatus == 2 or source.material_request_type != 'Purchase' or not line:
        frappe.throw('Dòng đề xuất mua không hợp lệ.')
    if not quotation:
        _remember_choice(line.name, None, None, None)
        return dict(request=request, request_item=line.name, quotation='', quotation_item='')
    quote = document('Supplier Quotation', quotation, company)
    row = next((r for r in quote.items if r.name == quotation_item), None)
    if quote.docstatus == 2 or quote.valid_till and getdate(quote.valid_till) < getdate(nowdate()):
        frappe.throw('Báo giá đã hủy hoặc hết hiệu lực. So sánh lại.')
    if not row or row.item_code != line.item_code or (row.material_request_item and row.material_request_item != line.name) or flt(row.rate) <= 0:
        frappe.throw('Dòng báo giá không khớp dòng đề xuất hoặc chưa có đơn giá.')
    cost = rules.quote_total(row.qty, row.rate, row.conversion_factor or 1, vat_now(row.get('lotus_line_vat')), row.get('lotus_line_freight') or 0)['unit_cost']
    offers = _live_offers(company).get(_offer_key(dict(request_line=line.name, item=line.item_code)), [])
    reason = str(reason or '').strip()
    if rules.needs_reason(cost, offers + [cost]) and len(reason) < 3:
        frappe.throw('Ghi lý do chọn ' + (row.item_name or row.item_code) + ' vì không phải giá thấp nhất.')
    _remember_choice(line.name, quote.name, row.name, reason)
    return dict(request=request, request_item=line.name, quotation=quote.name, quotation_item=row.name)


def _orders_using(quotation):
    return frappe.db.sql('''select distinct po.name from `tabPurchase Order Item` poi join `tabPurchase Order` po on po.name = poi.parent
        where poi.supplier_quotation = %s and po.docstatus < 2''', quotation, pluck=True)


@frappe.whitelist()
def quotation(name):
    """One quotation as the form edits it (spec 003, FR-034)."""
    d = document('Supplier Quotation', name)
    used = _orders_using(d.name)
    return dict(name=d.name, modified=str(d.modified), docstatus=d.docstatus, company=d.company, supplier=d.supplier,
                date=str(d.transaction_date), valid_till=str(d.valid_till or ''), expected_date=str(d.get('lotus_delivery_date') or ''),
                warehouse=next((r.warehouse for r in d.items if r.warehouse), ''), orders=used,
                can_edit=d.docstatus == 0 and d.has_permission('write'), can_cancel=d.docstatus < 2 and not used and d.has_permission('write'),
                items=[dict(name=r.name, item=r.item_code, item_name=r.item_name, qty=flt(r.qty), uom=r.uom, rate=flt(r.rate), warehouse=r.warehouse,
                            kind=r.get('lotus_purchase_kind'), vat_code=r.get('lotus_line_vat') or 'KCT', freight=flt(r.get('lotus_line_freight')),
                            material_request=r.material_request or '', material_request_item=r.material_request_item or '') for r in d.items])


@frappe.whitelist(methods=['POST'])
def cancel_quotation(name, modified, reason=None, amend=0):
    """Hủy báo giá chưa dùng (spec 003, FR-034). A draft is removed; a confirmed quote is cancelled with a reason.
    amend=1 returns a new draft copy to correct (a confirmed quote is never edited in place)."""
    d = document('Supplier Quotation', name)
    lock('Supplier Quotation', name)
    d.reload()
    if d.docstatus == 2 or str(d.modified) != str(modified):
        frappe.throw('Báo giá đã thay đổi. Tải lại.')
    d.check_permission('write')
    used = _orders_using(d.name)
    if used:
        frappe.throw('Báo giá đang dùng ở đơn mua ' + ', '.join(used) + '. Hủy hoặc xóa đơn đó trước.')
    copy = None
    if frappe.utils.cint(amend) and d.docstatus == 1:
        copy = frappe.copy_doc(d)
        copy.update(dict(amended_from=d.name, docstatus=0, lotus_procurement_key=None, lotus_procurement_hash=None))
    if frappe.get_meta('Material Request Item').has_field('lotus_selected_quote'):
        for line in frappe.get_all('Material Request Item', filters={'lotus_selected_quote': d.name}, pluck='name'):
            _remember_choice(line, None, None, None)
    if d.docstatus == 0:
        frappe.delete_doc('Supplier Quotation', d.name, ignore_permissions=True)
        return dict(name=name, deleted=True)
    reason = str(reason or '').strip()
    if not copy and len(reason) < 3:
        frappe.throw('Ghi lý do hủy báo giá.')
    d.flags.ignore_permissions = True
    d.cancel()
    d.add_comment('Comment', 'Hủy báo giá: ' + (reason or 'sửa lại báo giá'))
    if copy:
        copy.flags.ignore_permissions = True
        copy.insert()
        return dict(name=copy.name, modified=str(copy.modified), amended_from=name)
    return dict(name=name, cancelled=True)


@frappe.whitelist(methods=['POST'])
def confirm_quotation(name, modified):
    d = document('Supplier Quotation', name)
    lock('Supplier Quotation', name)
    d.reload()
    if d.docstatus or str(d.modified) != str(modified):
        frappe.throw('Báo giá đã thay đổi. Tải lại.')
    d.check_permission('submit')
    d.submit()
    return dict(name=d.name)


@frappe.whitelist(methods=['POST'])
def select_quotes(company, selections, client_key, approver=None):
    """Draft orders from the chosen quote lines, one per supplier. Every order waits for the named approver's
    signature (spec 003, FR-020); with `approver` the orders are sent to them at once."""
    access(company)
    selections = parse(selections)
    if not isinstance(selections, list) or not 1 <= len(selections) <= 100:
        frappe.throw('Chọn từ 1 đến 100 dòng báo giá.')
    from lotus_farm.warehouse_buying_lite import save_order
    lock('Company', company)
    existing = frappe.db.sql('''select name,lotus_procurement_hash from `tabPurchase Order` where company=%s
        and lotus_procurement_key like %s for update''',(company,rules.digest([frappe.session.user,'quote-selection',client_key])+'%'),as_dict=True)
    fingerprint = rules.digest(selections)
    if existing:
        for r in existing:document('Purchase Order',r.name,company,for_update=True)
        if any(r.lotus_procurement_hash != fingerprint for r in existing):
            frappe.throw('Lần chọn báo giá này đã dùng với nội dung khác.')
        return dict(orders=[r.name for r in existing])
    groups, seen, drafts = {}, set(), {}
    offers = _live_offers(company)
    for chosen in selections:
        if chosen['line'] in seen:
            frappe.throw('Không chọn hai lần cùng dòng báo giá.')
        seen.add(chosen['line'])
        quote = drafts.get(chosen['quotation']) or document('Supplier Quotation', chosen['quotation'], company)
        if quote.docstatus == 2 or str(quote.modified) != str(chosen.get('modified')) or quote.valid_till and getdate(quote.valid_till) < getdate(nowdate()):
            frappe.throw('Báo giá đã hủy, đã đổi hoặc hết hiệu lực. So sánh lại.')
        row = next((r for r in quote.items if r.name == chosen['line']), None)
        if not row or flt(row.rate) <= 0:
            frappe.throw('Dòng báo giá được chọn phải có đơn giá.')
        if row.material_request and frappe.db.get_value('Material Request', row.material_request, 'docstatus') != 1:
            frappe.throw('Đề xuất ' + row.material_request + ' chưa duyệt xong, chưa tạo đơn được.')
        cost = rules.quote_total(row.qty, row.rate, row.conversion_factor or 1, vat_now(row.get('lotus_line_vat')), row.get('lotus_line_freight') or 0)['unit_cost']
        key = _offer_key(dict(request_line=row.material_request_item, item=row.item_code))
        best = not rules.needs_reason(cost, offers.get(key, []) + [cost])
        reason = str(chosen.get('reason') or '').strip()
        if not best and not reason:
            frappe.throw('Ghi lý do chọn ' + (row.item_name or row.item_code) + ' vì không phải giá thấp nhất.')
        if quote.docstatus == 0:
            drafts[quote.name] = quote  # confirmed together with the order
        qty = flt(chosen.get('qty') or row.qty)
        if qty <= 0 or qty > flt(row.qty):
            frappe.throw('Số lượng chọn vượt báo giá.')
        if row.material_request_item:
            _remember_choice(row.material_request_item, quote.name, row.name, reason)
        groups.setdefault(quote.supplier, []).append(dict(item=row.item_code, qty=qty, rate=row.rate, uom=row.uom,
            warehouse=row.warehouse, expected_date=str(quote.get('lotus_delivery_date') or nowdate()),
            material_request=row.material_request, material_request_item=row.material_request_item,
            supplier_quotation=quote.name, supplier_quotation_item=row.name, kind=row.get('lotus_purchase_kind'),
            vat_code=vat_now(row.get('lotus_line_vat')), freight=flt(row.get('lotus_line_freight'))*qty/flt(row.qty),
            reason=reason or 'Giá thấp nhất trong các báo giá'))
    # Choosing a draft quote confirms it: the person creating the order vouches for the quoted price.
    for quote in drafts.values():
        lock('Supplier Quotation', quote.name)
        quote.check_permission('submit')
        quote.submit()
    orders = []
    requested={}
    for rows in groups.values():
        for row in rows:
            if row.get('material_request'):
                source=document('Material Request',row['material_request'],company,for_update=True)
                original=next(r for r in source.items if r.name==row['material_request_item'])
                item=frappe.get_cached_doc('Item',row['item'])
                factor=1 if row['uom']==item.stock_uom else next(flt(u.conversion_factor) for u in item.uoms if u.uom==row['uom'])
                pair=(source.name,original.name)
                requested[pair]=requested.get(pair,0)+flt(row['qty'])*factor
                if requested[pair]>flt(original.stock_qty)-flt(original.ordered_qty)+.000001:
                    frappe.throw('Tổng các nhà cung cấp được chọn vượt lượng còn mua của đề xuất '+source.name)
    sent = []
    for supplier, rows in groups.items():
        answer = save_order(company, dict(supplier=supplier, warehouse=rows[0]['warehouse'], expected_date=rows[0]['expected_date'], items=rows))
        d = frappe.get_doc('Purchase Order', answer['name'])
        d.lotus_procurement_key = rules.digest([frappe.session.user, 'quote-selection', client_key])+rules.digest(supplier)[:12]
        d.lotus_procurement_hash = fingerprint
        d.save()
        if approver:
            from lotus_farm.purchasing import request_approval
            request_approval(d.name, str(d.modified), approver)
            sent.append(d.name)
        orders.append(d.name)
    return dict(orders=orders, sent=sent)


@frappe.whitelist()
def chain(name):
    order = document('Purchase Order', name)
    result = dict(order=name, proposals=[], receipts=[], invoices=[], payments=[], funding=[])
    for proposal in sorted({r.material_request for r in order.items if r.material_request}):
        if frappe.has_permission('Material Request', 'read', proposal):
            source = document('Material Request', proposal, order.company)
            result['proposals'].append(dict(doctype='Material Request', name=source.name, docstatus=source.docstatus))
    result['progress'] = [dict(item_name=r.item_name, uom=r.uom, qty=flt(r.qty), ordered_qty=flt(r.qty),
        received_qty=flt(r.received_qty), remaining_receive_qty=max(0, flt(r.qty)-flt(r.received_qty))) for r in order.items]
    refs = [('Purchase Receipt', 'Purchase Receipt Item', 'purchase_order'), ('Purchase Invoice', 'Purchase Invoice Item', 'purchase_order')]
    for dt, child, link in refs:
        if not frappe.has_permission(dt, 'read'):
            continue
        names = frappe.get_all(child, filters={link: name}, pluck='parent', distinct=True, limit_page_length=0)
        for n in names:
            d = document(dt, n, order.company)
            result['receipts' if dt == 'Purchase Receipt' else 'invoices'].append(dict(doctype=dt, name=d.name, date=str(d.posting_date), docstatus=d.docstatus,
                amount=flt(d.base_grand_total), is_return=d.is_return, modified=str(d.modified),
                can_submit=d.docstatus == 0 and d.has_permission('submit')))
    from lotus_farm.finance import setup
    if setup.can_view():
        invoices = [i['name'] for i in result['invoices']]
        names = frappe.get_all('Payment Entry Reference', filters={'reference_name': ['in', [name, *invoices]], 'reference_doctype': ['in', ['Purchase Order', 'Purchase Invoice']]}, pluck='parent', distinct=True, limit_page_length=0)
        for n in names:
            d = document('Payment Entry', n, order.company)
            if d.docstatus == 2:
                continue  # a cancelled payment is not progress
            result['payments'].append(dict(doctype='Payment Entry', name=n, date=str(d.posting_date), docstatus=d.docstatus, amount=flt(d.paid_amount)))
        from lotus_farm.purchase_funding import list_funding
        result['funding'] = [f for f in list_funding(order.company) if any(a['reference_name'] in [name, *invoices] for a in f['allocations'])]
    return result


@frappe.whitelist()
def billing_source(company, name, kind='invoice'):
    from lotus_farm.finance import setup
    setup.require_post()
    if company!=setup.company() or kind not in ('invoice','credit'):
        frappe.throw('Nguồn hóa đơn không hợp lệ.')
    if kind=='invoice':
        from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice
        source=document('Purchase Receipt',name,company)
        if source.docstatus!=1 or source.is_return: frappe.throw('Chọn phiếu nhận đã xác nhận.')
        mapped=make_purchase_invoice(name)
        field='pr_detail'
    else:
        from erpnext.controllers.sales_and_purchase_return import make_return_doc
        source=document('Purchase Invoice',name,company)
        if source.docstatus!=1 or source.is_return: frappe.throw('Chọn hóa đơn gốc đã ghi sổ.')
        mapped=make_return_doc('Purchase Invoice',name)
        field='purchase_invoice_item'
    return dict(name=name,items=[dict(line=r.get(field),item_name=r.item_name,uom=r.uom,
                qty=abs(flt(r.qty)),remaining_qty=abs(flt(r.qty))) for r in mapped.items if abs(flt(r.qty))>.000001])


@frappe.whitelist(methods=['POST'])
def invoice_receipt(name, bill_no, bill_date, posting_date, client_key, quantities=None, due_date=None, invoice_series=None, cqt_code=None, invoice_total=None, invoice_vat=None):
    """Hóa đơn cho một phiếu nhận (lớp bọc của finance.supplier_invoice.create, spec 003 R16). quantities: {dòng phiếu nhận: số lượng}."""
    from lotus_farm.finance import supplier_invoice
    selected = parse(quantities) if quantities else None
    lines = [dict(source_item=line, qty=qty) for line, qty in selected.items()] if selected is not None else None
    result = supplier_invoice.create(receipts=[name], lines=lines, bill_no=bill_no, series=invoice_series, tax_code=cqt_code, bill_date=bill_date,
                                     due_date=due_date, posting_date=posting_date, printed_total=invoice_total, printed_vat=invoice_vat, client_key=client_key)
    return dict(invoice=result['invoice'], amount=result['amount'])


@frappe.whitelist(methods=['POST'])
def supplier_payment(company, reference_type, reference_name, amount, mode, posting_date, signers, client_key, reference_no=None):
    """Chi cho một hóa đơn hoặc tạm ứng theo một đơn mua (lớp bọc của finance.supplier_payment.prepare, spec 003 R19)."""
    from lotus_farm.finance import setup, supplier_payment as core
    if company != setup.company() or reference_type not in ('Purchase Order', 'Purchase Invoice'):
        frappe.throw('Nguồn thanh toán không hợp lệ.')
    if flt(amount) <= 0:
        frappe.throw('Số chi phải lớn hơn 0.')
    result = core.prepare(allocations=[dict(doctype=reference_type, name=reference_name, amount=amount)], mode=mode, posting_date=posting_date,
                          signers=signers, client_key=client_key, reference_no=reference_no)
    return result if result.get('signing') else dict(voucher=result['voucher'], doctype=result['doctype'])


@frappe.whitelist(methods=['POST'])
def return_receipt(name, posting_date, quantities, client_key, post=0, reason=None):
    """Trả hàng cho NCC (spec 003, FR-044). post=1 posts the return at once when the user may post receipts.
    needs_credit_note: the received goods already have a supplier invoice, so an adjustment invoice must follow."""
    from erpnext.controllers.sales_and_purchase_return import make_return_doc
    source = document('Purchase Receipt', name)
    quantities = parse(quantities)
    lock('Company', source.company)
    lock('Purchase Receipt', name)
    key = rules.digest([frappe.session.user, 'return', client_key])
    fingerprint = rules.digest([name, posting_date, quantities])
    old = frappe.db.get_value('Purchase Receipt', {'lotus_client_key': key}, ['name', 'lotus_payload_hash'], as_dict=True)
    if old:
        document('Purchase Receipt', old.name, source.company)
        if old.lotus_payload_hash != fingerprint:
            frappe.throw('Yêu cầu trả hàng đã dùng với nội dung khác.')
        return _returned(frappe.get_doc('Purchase Receipt', old.name), source)
    if not client_key or source.docstatus != 1 or source.is_return or not isinstance(quantities, dict) or not quantities:
        frappe.throw('Chọn phiếu nhận và số lượng trả hợp lệ.')
    d = make_return_doc('Purchase Receipt', name)
    kept = []
    for row in d.items:
        if row.purchase_receipt_item not in quantities:
            continue
        qty = flt(quantities[row.purchase_receipt_item])
        if qty <= 0 or qty > abs(flt(row.qty))+.000001:
            frappe.throw('Số trả vượt phần đã nhận chưa trả.')
        row.qty, row.received_qty = -qty, -qty
        original = next(r for r in source.items if r.name==row.purchase_receipt_item)
        row.lotus_line_freight=-flt(original.get('lotus_line_freight'))*qty/flt(original.qty)
        kept.append(row)
    if {r.purchase_receipt_item for r in kept} != set(quantities):
        frappe.throw('Dòng trả hàng không còn hợp lệ.')
    d.set('items', kept)
    renumber(d)
    apply_line_taxes(d)
    d.posting_date = posting_date
    if str(reason or '').strip():
        d.remarks = 'Lý do trả hàng: ' + str(reason).strip()[:400]
    d.lotus_client_key, d.lotus_payload_hash = key, fingerprint
    d.insert()
    if frappe.utils.cint(post) and d.has_permission('submit'):
        d.submit()  # ERPNext checks what is left to return and reverses the stock ledger
    return _returned(d, source)


def _returned(d, source):
    billed = d.docstatus == 1 and bool(frappe.db.exists('Purchase Invoice Item', {'purchase_receipt': source.name, 'docstatus': 1}))
    return dict(name=d.name, docstatus=d.docstatus, modified=str(d.modified), return_against=source.name, needs_credit_note=billed)


def native_guard(doc, method=None):
    """Reject incompatible classifications and stale signed content through Desk too."""
    for row in doc.get('items') or []:
        if row.get('lotus_farm'):
            farm=frappe.get_doc('Farm',row.lotus_farm)
            farm.check_permission('read')
            if farm.company!=doc.company:frappe.throw('Vườn mua hàng phải thuộc công ty của chứng từ.')
        if row.get('lotus_purchase_kind'):
            item_kind(frappe.get_cached_doc('Item', row.item_code), row.lotus_purchase_kind)
        if doc.doctype == 'Purchase Order' and row.get('supplier_quotation'):
            # An integrity check, run for whoever saves or approves the order (the director need not open quotes).
            q = frappe.get_doc('Supplier Quotation', row.supplier_quotation)
            if q.company != doc.company:
                frappe.throw('Báo giá nguồn không thuộc công ty của đơn mua.')
            source = next((r for r in q.items if r.name==row.supplier_quotation_item),None)
            if q.docstatus!=1 or q.supplier!=doc.supplier or not source or source.item_code!=row.item_code:
                frappe.throw('Dòng báo giá nguồn không khớp mặt hàng / nhà cung cấp / công ty.')
    if doc.doctype == 'Purchase Order' and not doc.is_new():
        from lotus_farm import signing, signing_rules
        signed, _ = signing._rows(doc)
        if signed and not any(r.state == signing_rules.RETURNED for r in signed):
            hashes = [r.content_hash for r in signed if r.state == signing_rules.SIGNED]
            if hashes and any(h != signing.fingerprint(doc) for h in hashes):
                frappe.throw('Nội dung đơn mua đã ký không được thay đổi. Trả lại để lập lượt ký mới.')


def receipt_guard(doc, method=None):
    if not any(r.get('lotus_purchase_kind') for r in doc.items):
        return
    lock('Company',doc.company)
    grouped={}
    for r in doc.items:
        if r.purchase_order and r.purchase_order_item:
            key=(r.purchase_order,r.purchase_order_item)
            grouped[key]=grouped.get(key,0)+flt(r.stock_qty)
    if doc.is_return:
        return  # ERPNext validates the receipt-specific remaining return quantity.
    for (name,line),qty in sorted(grouped.items()):
        lock('Purchase Order',name)
        source=document('Purchase Order',name,doc.company)
        original=next((r for r in source.items if r.name==line),None)
        if source.docstatus!=1 or source.status in ('Closed','Stopped','Cancelled') or not original or qty>flt(original.stock_qty)-flt(original.received_qty)*flt(original.conversion_factor)+.000001:
            frappe.throw('Số nhận vượt phần còn lại của đơn mua hoặc đơn đã đóng.')


@frappe.whitelist()
def receipts(company):
    access(company)
    if not frappe.has_permission('Purchase Receipt', 'read'):
        return []
    from lotus_farm import purchase_status
    rows = frappe.get_list('Purchase Receipt', filters={'company':company},
        fields=['name','supplier','supplier_name','posting_date','base_grand_total','docstatus','modified','is_return','per_billed','per_returned','return_against'],
        limit_page_length=0, order_by='posting_date desc, name desc')
    return [dict(name=d.name, supplier=d.supplier, supplier_name=d.supplier_name or d.supplier, date=str(d.posting_date), amount=flt(d.base_grand_total),
        docstatus=d.docstatus, status=purchase_status.receipt_state(d.docstatus), modified=str(d.modified), is_return=d.is_return,
        kind='Trả hàng' if d.is_return else 'Nhập theo đơn', return_against=d.return_against or '',
        billing=purchase_status.billing_state(d.per_billed, per_returned=d.per_returned) if d.docstatus == 1 and not d.is_return else '') for d in rows]


@frappe.whitelist()
def receipt(name):
    d = document('Purchase Receipt', name)
    from lotus_farm.warehouse_planning import receipt_totals, receipt_extras
    from lotus_farm.finance.invoice_cost import returned_qty_map
    # Summed over every submitted return, in the line's own unit (ERPNext 16 leaves returned_qty at 0 for them).
    returned = returned_qty_map(d.name) if d.docstatus == 1 and not d.is_return else {}
    return dict(name=d.name, doctype=d.doctype, company=d.company, supplier=d.supplier,
        supplier_name=d.supplier_name or d.supplier, date=str(d.posting_date), docstatus=d.docstatus,
        currency=frappe.get_cached_value('Company', d.company, 'default_currency'),
        **receipt_totals(d), **receipt_extras(d), modified=str(d.modified),
        items=[dict(line=r.name,item=r.item_code,item_name=r.item_name,qty=flt(r.qty),uom=r.uom,
            rate=flt(r.rate),amount=flt(r.amount),kind=r.get('lotus_purchase_kind'),warehouse=r.warehouse,
            vat_code=r.get('lotus_line_vat'),freight=flt(r.get('lotus_line_freight')),valuation_rate=flt(r.valuation_rate),
            # Already sent back to the supplier, in the line's own unit: what a new return may still take.
            returned_qty=flt(returned.get(r.name)),
            order=r.purchase_order) for r in d.items])


@frappe.whitelist()
def payment_data(company):
    from lotus_farm.finance import setup, payments
    setup.require_post()
    if company != setup.company():
        frappe.throw('Công ty khác cấu hình tài chính.')
    from lotus_farm.purchase_funding import options, list_funding
    result = options(company)
    result['funding'] = list_funding(company)
    result['vouchers'] = []
    for dt, filters in (('Payment Entry', {'party_type':'Supplier','payment_type':'Pay'}),
                        ('Journal Entry', {'lotus_payment_kind':['in',['PurchaseFunding','PurchaseReimbursement']]})):
        for r in frappe.get_list(dt, filters=dict(filters, company=company, docstatus=0), fields=['name'], limit_page_length=0):
            result['vouchers'].append(payments._voucher_info(document(dt,r.name,company)))
    return result


@frappe.whitelist()
def voucher(doctype, name):
    from lotus_farm.finance import payments
    if doctype not in ('Payment Entry','Journal Entry'):
        frappe.throw('Loại phiếu không hợp lệ.')
    d = document(doctype,name)
    result = payments._voucher_info(d)
    if doctype == 'Payment Entry':
        result['references'] = [dict(name=r.reference_name, type='orders' if r.reference_doctype == 'Purchase Order' else 'invoices')
            for r in d.references if r.reference_doctype in ('Purchase Order', 'Purchase Invoice')
            and frappe.has_permission(r.reference_doctype, 'read', r.reference_name)]
    from lotus_farm.finance import posting
    result['posting'] = frappe.db.get_value(posting.POSTING, {'voucher_type': doctype, 'voucher_name': name, 'state': ['!=', 'Reversed']}) or ''
    return result
