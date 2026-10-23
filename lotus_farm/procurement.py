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


def apply_line_taxes(doc):
    """Native item tax overrides allow mixed VAT. Freight is an explicit native charge."""
    from lotus_farm.finance import setup, rules as finance_rules
    mapping = setup.mapping()
    account = mapping.get('input_vat')
    shipping = sum(flt(r.get('lotus_line_freight')) for r in doc.items)
    rates = [finance_rules.vat_rate(r.get('lotus_line_vat') or 'KCT', doc.get('bill_date') or doc.get('posting_date') or doc.get('transaction_date')) * 100 for r in doc.items]
    if any(rates) and not account:
        frappe.throw('Thiết lập tài khoản VAT đầu vào tại Tài chính – Kế toán.')
    for row, rate in zip(doc.items, rates):
        # item_tax_rate is an ERPNext output and gets rebuilt during validation.
        # A native Item Tax Template is the durable, per-line input.
        if any(rates):
            title='Lotus purchase VAT '+str(int(rate))+'%'
            template=frappe.db.get_value('Item Tax Template',{'company':doc.company,'title':title},'name')
            if not template:
                template=frappe.get_doc(dict(doctype='Item Tax Template',title=title,company=doc.company,
                    taxes=[dict(tax_type=account,tax_rate=rate)])).insert(ignore_permissions=True).name
            tax=frappe.get_doc('Item Tax Template',template)
            if len(tax.taxes)!=1 or tax.taxes[0].tax_type!=account or flt(tax.taxes[0].tax_rate)!=rate:
                frappe.throw('Mẫu thuế '+template+' đã thay đổi. Kế toán kiểm tra lại cấu hình VAT đầu vào.')
            row.item_tax_template=template
        else:
            row.item_tax_template=None
        row.item_tax_rate = json.dumps({account: rate}) if account else '{}'
    doc.taxes_and_charges = None
    doc.set('taxes', [])
    cc = frappe.get_cached_value('Company', doc.company, 'cost_center')
    if any(rates):
        doc.append('taxes', dict(charge_type='On Net Total', account_head=account, rate=0,
                                description='Thuế GTGT theo dòng', category='Total', add_deduct_tax='Add', cost_center=cc))
    if shipping:
        freight_account = mapping.get('overhead_service')
        if not freight_account:
            frappe.throw('Thiết lập tài khoản dịch vụ vận chuyển tại Tài chính – Kế toán.')
        doc.append('taxes', dict(charge_type='Actual', account_head=freight_account, tax_amount=shipping,
                                description='Vận chuyển', category='Total', add_deduct_tax='Add', cost_center=cc))


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
                farms=frappe.get_list('Farm',filters={'company':company},fields=['name'],limit_page_length=0) if frappe.has_permission('Farm','read') else [])
    return data


@frappe.whitelist()
def needs(company):
    access(company)
    result = []
    for r in frappe.get_list('Material Request', filters={'company': company, 'material_request_type': 'Purchase'}, fields=['name'], limit_page_length=0, order_by='transaction_date desc, name desc'):
        d = document('Material Request', r.name, company)
        result.append(dict(name=d.name, date=str(d.transaction_date), needed=str(d.schedule_date or ''), status=d.status,
                           docstatus=d.docstatus, amount=flt(d.get('grand_total') or d.get('total')),
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
            values = rules.quote_total(x.qty, x.rate, x.conversion_factor or 1, x.get('lotus_line_vat') or 'KCT', x.get('lotus_line_freight') or 0)
            result.append(dict(name=x.name, quotation=d.name, modified=str(d.modified), supplier=d.supplier, docstatus=d.docstatus,
                               item=x.item_code, item_name=x.item_name, qty=flt(x.qty), uom=x.uom, stock_uom=x.stock_uom,
                               rate=flt(x.rate) or None, factor=flt(x.conversion_factor), warehouse=x.warehouse,
                               request=x.material_request, request_line=x.material_request_item,
                               date=str(d.transaction_date), delivery_date=str(d.get('lotus_delivery_date') or ''),
                               valid_till=str(d.valid_till or ''), kind=x.get('lotus_purchase_kind'),
                               vat_code=x.get('lotus_line_vat') or 'KCT', **values))
    return result


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
    d.set('items', _lines(company, data.get('warehouse'), data.get('items'), data.get('expected_date')))
    apply_line_taxes(d)
    d.lotus_procurement_key, d.lotus_procurement_hash = token, fingerprint
    d.save() if name else d.insert()
    return dict(name=d.name, modified=str(d.modified))


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
def select_quotes(company, selections, client_key):
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
    groups, seen = {}, set()
    for chosen in selections:
        if chosen['line'] in seen:
            frappe.throw('Không chọn hai lần cùng dòng báo giá.')
        seen.add(chosen['line'])
        quote = document('Supplier Quotation', chosen['quotation'], company)
        if quote.docstatus != 1 or str(quote.modified) != str(chosen.get('modified')) or quote.valid_till and getdate(quote.valid_till) < getdate(nowdate()):
            frappe.throw('Báo giá chưa xác nhận, đã đổi hoặc hết hiệu lực. So sánh lại.')
        row = next((r for r in quote.items if r.name == chosen['line']), None)
        if not row or flt(row.rate) <= 0 or not str(chosen.get('reason') or '').strip():
            frappe.throw('Báo giá phải có giá và lý do lựa chọn.')
        qty = flt(chosen.get('qty') or row.qty)
        if qty <= 0 or qty > flt(row.qty):
            frappe.throw('Số lượng chọn vượt báo giá.')
        groups.setdefault(quote.supplier, []).append(dict(item=row.item_code, qty=qty, rate=row.rate, uom=row.uom,
            warehouse=row.warehouse, expected_date=str(quote.get('lotus_delivery_date') or nowdate()),
            material_request=row.material_request, material_request_item=row.material_request_item,
            supplier_quotation=quote.name, supplier_quotation_item=row.name, kind=row.get('lotus_purchase_kind'),
            vat_code=row.get('lotus_line_vat'), freight=flt(row.get('lotus_line_freight'))*qty/flt(row.qty), reason=chosen['reason']))
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
                    frappe.throw('Tổng các nhà cung cấp được chọn vượt lượng còn mua của đề nghị '+source.name)
    for supplier, rows in groups.items():
        answer = save_order(company, dict(supplier=supplier, warehouse=rows[0]['warehouse'], expected_date=rows[0]['expected_date'], items=rows))
        d = frappe.get_doc('Purchase Order', answer['name'])
        d.lotus_procurement_key = rules.digest([frappe.session.user, 'quote-selection', client_key])+rules.digest(supplier)[:12]
        d.lotus_procurement_hash = fingerprint
        d.save()
        orders.append(d.name)
    return dict(orders=orders)


@frappe.whitelist()
def chain(name):
    order = document('Purchase Order', name)
    result = dict(order=name, receipts=[], invoices=[], payments=[], funding=[])
    refs = [('Purchase Receipt', 'Purchase Receipt Item', 'purchase_order'), ('Purchase Invoice', 'Purchase Invoice Item', 'purchase_order')]
    for dt, child, link in refs:
        if not frappe.has_permission(dt, 'read'):
            continue
        names = frappe.get_all(child, filters={link: name}, pluck='parent', distinct=True, limit_page_length=0)
        for n in names:
            d = document(dt, n, order.company)
            result['receipts' if dt == 'Purchase Receipt' else 'invoices'].append(dict(name=d.name, date=str(d.posting_date), docstatus=d.docstatus,
                amount=flt(d.base_grand_total), is_return=d.is_return, modified=str(d.modified),
                can_submit=d.docstatus == 0 and d.has_permission('submit')))
    from lotus_farm.finance import setup
    if setup.can_view():
        invoices = [i['name'] for i in result['invoices']]
        names = frappe.get_all('Payment Entry Reference', filters={'reference_name': ['in', [name, *invoices]], 'reference_doctype': ['in', ['Purchase Order', 'Purchase Invoice']]}, pluck='parent', distinct=True, limit_page_length=0)
        for n in names:
            d = document('Payment Entry', n, order.company)
            result['payments'].append(dict(name=n, date=str(d.posting_date), docstatus=d.docstatus, amount=flt(d.paid_amount)))
        from lotus_farm.purchase_funding import list_funding
        result['funding'] = [f for f in list_funding(order.company) if any(a['reference_name'] in [name, *invoices] for a in f['allocations'])]
    return result


@frappe.whitelist(methods=['POST'])
def invoice_receipt(name, bill_no, bill_date, posting_date, client_key, quantities=None, due_date=None):
    """Partial invoices stay linked to the actual PR lines. Old header-VAT API is unchanged."""
    from lotus_farm.finance import setup, posting, payments
    from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice
    setup.require_post()
    setup.require_enabled()
    source = document('Purchase Receipt', name, setup.company())
    lock('Company', source.company)
    lock('Purchase Receipt', name)
    selected = parse(quantities) if quantities else None
    payload = [name, bill_no, bill_date, posting_date, selected, due_date]
    key, fingerprint, old = idempotent('Purchase Invoice', client_key, payload, source.company)
    if old:
        return dict(invoice=old)
    if source.docstatus != 1 or source.is_return or not str(bill_no or '').strip():
        frappe.throw('Chọn phiếu nhận đã xác nhận và nhập số hóa đơn.')
    payments._duplicate(source.supplier, bill_no)
    setup.check_cutover(posting_date)
    posting.check_open(source.company, posting_date, 'Purchase Invoice')
    pi = make_purchase_invoice(name)
    original = {r.name: r for r in source.items}
    kept = []
    for row in pi.items:
        if selected is not None and row.pr_detail not in selected:
            continue
        qty = flt(selected[row.pr_detail]) if selected is not None else flt(row.qty)
        if qty <= 0 or qty > flt(row.qty)+.000001:
            frappe.throw('Số lượng hóa đơn vượt phần chưa lập hóa đơn.')
        row.qty = qty
        row.stock_qty = qty*flt(row.conversion_factor)
        src = original[row.pr_detail]
        row.lotus_line_freight = flt(src.get('lotus_line_freight'))*qty/flt(src.qty)
        if item_kind(frappe.get_cached_doc('Item', row.item_code), src.get('lotus_purchase_kind')) == 'Service':
            row.expense_account = setup.mapping()['overhead_service'] if row.get('lotus_farm') else setup.mapping()['admin_expense']
        kept.append(row)
    if not kept or selected is not None and {r.pr_detail for r in kept} != set(selected):
        frappe.throw('Dòng nghiệm thu đã thay đổi. Tải lại.')
    pi.set('items', kept)
    pi.update(dict(bill_no=str(bill_no).strip(), bill_date=bill_date, posting_date=posting_date, set_posting_time=1,
        due_date=payments._due(bill_date, due_date), credit_to=setup.mapping()['payable_supplier'], update_stock=0,
        lotus_procurement_key=key, lotus_procurement_hash=fingerprint, allocate_advances_automatically=1))
    apply_line_taxes(pi)
    pi.set_missing_values()
    pi.calculate_taxes_and_totals()
    pi.set_advances()
    pi.set('payment_schedule', [])
    pi.insert()
    pi.submit()
    posting.record('Purchase Invoice', pi.name, 'Purchase Invoice', pi, amount=pi.grand_total, source_hash=name)
    return dict(invoice=pi.name, amount=pi.grand_total)


@frappe.whitelist(methods=['POST'])
def supplier_payment(company, reference_type, reference_name, amount, mode, posting_date, signers, client_key, reference_no=None):
    """Native PE supports both PO advances and invoice settlement, with one reservation lock."""
    from lotus_farm.finance import setup, posting, payments
    from lotus_farm.purchase_funding import _remaining_source
    from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
    setup.require_post()
    setup.require_enabled()
    if company != setup.company() or reference_type not in ('Purchase Order', 'Purchase Invoice'):
        frappe.throw('Nguồn thanh toán không hợp lệ.')
    d = document(reference_type, reference_name, company)
    key, fingerprint, old = idempotent('Payment Entry', client_key, [reference_type, reference_name, amount, mode, posting_date, reference_no], company)
    if old:
        return dict(voucher=old, doctype='Payment Entry')
    lock(reference_type, reference_name)
    if d.docstatus != 1 or d.get('is_return') or mode not in ('cash', 'bank') or mode == 'bank' and not reference_no:
        frappe.throw('Chứng từ hoặc phương thức thanh toán không hợp lệ. Chuyển khoản cần số giao dịch.')
    if flt(amount) <= 0 or flt(amount) > _remaining_source(reference_type, reference_name)+.5:
        frappe.throw('Số chi vượt phần còn trả sau các phiếu chờ ký.')
    setup.check_cutover(posting_date)
    posting.check_open(company, posting_date, 'Payment Entry')
    pe = get_payment_entry(reference_type, reference_name, party_amount=flt(amount), bank_account=setup.mapping()[mode], bank_amount=flt(amount))
    pe.posting_date = posting_date
    pe.reference_no, pe.reference_date = reference_no or None, posting_date if reference_no else None
    pe.lotus_procurement_key, pe.lotus_procurement_hash = key, fingerprint
    pe.insert()
    posting.record('Payment Entry', pe.name, 'Supplier Payment', pe, amount=pe.paid_amount, source_hash=reference_name)
    return payments.start_signing(pe, signers)


@frappe.whitelist(methods=['POST'])
def return_receipt(name, posting_date, quantities, client_key):
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
        return dict(name=old.name)
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
    apply_line_taxes(d)
    d.posting_date = posting_date
    d.lotus_client_key, d.lotus_payload_hash = key, fingerprint
    d.insert()
    return dict(name=d.name)


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
            q = document('Supplier Quotation',row.supplier_quotation,doc.company)
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
    return [dict(name=d.name, supplier=d.supplier, date=str(d.posting_date), amount=flt(d.base_grand_total),
        docstatus=d.docstatus, status={0:'Nháp',1:'Đã xác nhận',2:'Đã hủy'}[d.docstatus], modified=str(d.modified))
        for d in frappe.get_list('Purchase Receipt', filters={'company':company},
            fields=['name','supplier','posting_date','base_grand_total','docstatus','modified'], limit_page_length=0, order_by='posting_date desc, name desc')]


@frappe.whitelist()
def receipt(name):
    d = document('Purchase Receipt', name)
    return dict(name=d.name, company=d.company, supplier=d.supplier, date=str(d.posting_date), docstatus=d.docstatus,
        is_return=d.is_return, modified=str(d.modified), can_submit=d.docstatus==0 and d.has_permission('submit'),
        can_cancel=d.docstatus==1 and d.has_permission('cancel'),
        items=[dict(line=r.name,item=r.item_code,item_name=r.item_name,qty=flt(r.qty),uom=r.uom,
            rate=flt(r.rate),amount=flt(r.amount),kind=r.get('lotus_purchase_kind'),warehouse=r.warehouse,
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
    return payments._voucher_info(d)
