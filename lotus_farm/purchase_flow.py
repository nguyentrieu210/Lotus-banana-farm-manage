"""Lotus purchase policy and progress derived from native ERPNext documents."""
import frappe
from frappe.utils import flt, get_datetime, now_datetime


def enabled(company):
    return bool(company and company == frappe.conf.get('lotus_purchase_flow_company'))


def install():
    if not frappe.conf.get('lotus_purchase_flow_company') and frappe.db.exists('Company', 'Lotus Agritech'):
        frappe.conf.lotus_purchase_flow_company = 'Lotus Agritech'
        frappe.conf.lotus_purchase_flow_since = str(now_datetime())
        from frappe.installer import update_site_config
        update_site_config('lotus_purchase_flow_company', 'Lotus Agritech')
        update_site_config('lotus_purchase_flow_since', frappe.conf.lotus_purchase_flow_since)
    if frappe.conf.get('lotus_purchase_flow_company'):
        from frappe.permissions import add_permission, update_permission_property
        role = 'Lotus Purchase Requester'
        add_permission('Material Request', role)
        for action in ('read', 'create', 'write'):
            if not frappe.db.get_value('Custom DocPerm', {'parent': 'Material Request', 'role': role, 'permlevel': 0}, action):
                update_permission_property('Material Request', role, 0, action, 1)


def validate(doc, method=None):
    if doc.material_request_type != 'Purchase' or not enabled(doc.company):
        return
    from lotus_farm import signing, signing_rules
    from lotus_farm.controls import lock
    if doc.is_new():
        doc.lotus_proposal_policy = 2
        return
    lock('Material Request', doc.name)
    rows, _ = signing._rows(doc)
    if rows and not any(r.state == signing_rules.RETURNED for r in rows):
        signed = [r for r in rows if r.state == signing_rules.SIGNED]
        if any(r.content_hash != signing.fingerprint(doc) for r in signed):
            frappe.throw('Nội dung đề xuất đã ký đã thay đổi. Trả lại và ký lại từ đầu.')
    if method != 'before_submit':
        return
    expected = signing_rules.chain('purchase_proposal')['steps']
    if (len(rows) != len(expected) or
            any(r.step_index != i or r.step_key != step['key'] or r.state != signing_rules.SIGNED
                or not r.signed_at or not r.signature_file or not r.content_hash
                or r.content_hash != signing.fingerprint(doc)
                for i, (r, step) in enumerate(zip(rows, expected)))):
        frappe.throw('Đề xuất mua phải ký đủ 4 bước trên cùng nội dung trước khi duyệt.')
    if rows[0].assignee != doc.owner:
        frappe.throw('Chữ ký người đề xuất không khớp người lập phiếu.')
    for row, step in zip(rows[1:], expected[1:]):
        signing._validate_person(row.assignee, step, doc.company)


def require_approved(doc):
    if doc.docstatus != 1 or doc.status in ('Stopped', 'Closed', 'Cancelled'):
        frappe.throw('Chỉ lập đơn từ đề xuất mua đã duyệt còn hiệu lực.')


def _legacy_order(doc):
    """Orders created before the purchase flow started may finish without a proposal behind their lines."""
    since = frappe.conf.get('lotus_purchase_flow_since')
    created = frappe.db.get_value('Purchase Order', doc.name, 'creation') if doc.name else None
    return bool(since and created and get_datetime(created) < get_datetime(since))


BLOCKING = ('no_source', 'not_approved', 'mismatch', 'over')


def order_issues(doc):
    """Lines that approval would refuse, without throwing (spec 003, FR-036): [{line, item, code, message}].
    Codes in BLOCKING stop the approval; 'held' only warns that other draft orders already hold part of the
    same proposal line (ERPNext counts submitted orders only)."""
    if not enabled(doc.company):
        return []
    legacy = _legacy_order(doc)
    issues, amounts = [], {}
    lines = [r.material_request_item for r in doc.items if r.material_request_item]
    held = {}
    if lines:
        for row in frappe.db.sql('''select poi.material_request_item item, sum(poi.stock_qty) qty from `tabPurchase Order Item` poi
            join `tabPurchase Order` po on po.name = poi.parent where po.docstatus = 0 and po.name != %(name)s
            and poi.material_request_item in %(lines)s group by poi.material_request_item''', dict(name=doc.name or '', lines=lines), as_dict=True):
            held[row.item] = flt(row.qty)

    def add(index, row, code, text):
        issues.append(dict(line=index, item=row.item_name or row.item_code, code=code,
                           message='Dòng %d (%s): %s' % (index, row.item_name or row.item_code, text)))

    for index, row in enumerate(doc.items, start=1):
        if not row.material_request or not row.material_request_item:
            if not (legacy and not row.material_request and not row.material_request_item):
                add(index, row, 'no_source', 'không lấy từ đề xuất mua đã duyệt. Hàng đã mua lẻ dùng Mua nhanh.')
            continue
        source = frappe.db.get_value('Material Request', row.material_request, ['docstatus', 'status', 'company', 'material_request_type'], as_dict=True)
        if not source or source.docstatus != 1 or source.status in ('Stopped', 'Closed', 'Cancelled'):
            add(index, row, 'not_approved', 'đề xuất %s chưa duyệt hoặc không còn hiệu lực.' % row.material_request)
            continue
        original = frappe.db.get_value('Material Request Item', row.material_request_item, ['parent', 'item_code', 'stock_qty', 'ordered_qty'], as_dict=True)
        if (source.company != doc.company or source.material_request_type != 'Purchase' or not original
                or original.parent != row.material_request or original.item_code != row.item_code):
            add(index, row, 'mismatch', 'không khớp dòng đề xuất mua nguồn.')
            continue
        key = row.material_request_item
        amounts[key] = amounts.get(key, 0) + (flt(row.stock_qty) or flt(row.qty) * (flt(row.conversion_factor) or 1))
        remaining = flt(original.stock_qty) - flt(original.ordered_qty)
        if amounts[key] > remaining + .000001:
            add(index, row, 'over', 'số đặt vượt phần còn lại của đề xuất (còn %s).' % frappe.utils.fmt_money(max(0, remaining), precision=3).rstrip('0').rstrip(',.'))
        elif amounts[key] + held.get(key, 0) > remaining + .000001:
            add(index, row, 'held', 'các đơn nháp khác cũng đang lấy dòng đề xuất này; tổng vượt phần còn lại. Đơn duyệt trước được lấy trước.')
    return issues


def order_guard(doc, method=None):
    """before_submit of Purchase Order: every line comes from an approved proposal and stays within what it still needs."""
    if not enabled(doc.company):
        return
    from lotus_farm.controls import lock
    lock('Company', doc.company)
    for name in sorted({r.material_request for r in doc.items if r.material_request}):
        lock('Material Request', name)
    blocking = [i for i in order_issues(doc) if i['code'] in BLOCKING]
    if blocking:
        if any(i['code'] == 'no_source' for i in blocking):
            frappe.throw('Đơn mua cần lấy từng dòng từ đề xuất mua đã duyệt. Hàng đã mua lẻ dùng Mua nhanh. ' + blocking[0]['message'])
        frappe.throw('; '.join(i['message'] for i in blocking[:5]))


def proposal_totals(names):
    """Per proposal line, in stock units and independent of who is looking (spec 003, R11):
    qty, ordered (every order line, drafts included), received (net of returns), billed, closed
    (unreceived part of closed orders, plus the unordered part once the proposal is stopped).
    Returns {proposal: dict(stopped=bool, lines=[...])} for proposal_rules.stage."""
    names = [n for n in (names or []) if n]
    if not names:
        return {}
    result = {}
    for row in frappe.get_all('Material Request', filters={'name': ['in', names]}, fields=['name', 'status'], limit_page_length=0):
        result[row.name] = dict(stopped=row.status == 'Stopped', lines={})
    for line in frappe.get_all('Material Request Item', filters={'parent': ['in', names], 'parenttype': 'Material Request'},
                               fields=['name', 'parent', 'stock_qty'], limit_page_length=0):
        if line.parent in result:
            result[line.parent]['lines'][line.name] = dict(name=line.name, qty=flt(line.stock_qty), ordered=0.0, received=0.0,
                                                           returned=0.0, billed=0.0, closed=0.0)
    order_lines = frappe.db.sql('''select poi.name, poi.material_request, poi.material_request_item, poi.stock_qty, po.status, po.docstatus
        from `tabPurchase Order Item` poi join `tabPurchase Order` po on po.name = poi.parent
        where poi.material_request in %(names)s and po.docstatus < 2''', dict(names=names), as_dict=True)
    by_order_line = {}
    for o in order_lines:
        line = result.get(o.material_request, {}).get('lines', {}).get(o.material_request_item)
        if not line:
            continue
        line['ordered'] += flt(o.stock_qty)
        by_order_line[o.name] = (line, o)
    if by_order_line:
        keys = list(by_order_line)
        received = {}
        for r in frappe.db.sql('''select pri.purchase_order_item, sum(pri.stock_qty) qty from `tabPurchase Receipt Item` pri
            join `tabPurchase Receipt` pr on pr.name = pri.parent where pr.docstatus = 1 and pri.purchase_order_item in %(keys)s
            group by pri.purchase_order_item''', dict(keys=keys), as_dict=True):
            received[r.purchase_order_item] = flt(r.qty)
        for r in frappe.db.sql('''select pii.po_detail, sum(pii.stock_qty) qty from `tabPurchase Invoice Item` pii
            join `tabPurchase Invoice` pi on pi.name = pii.parent where pi.docstatus = 1 and pii.po_detail in %(keys)s
            group by pii.po_detail''', dict(keys=keys), as_dict=True):
            by_order_line[r.po_detail][0]['billed'] += flt(r.qty)
        for key, (line, order) in by_order_line.items():
            got = received.get(key, 0.0)
            line['received'] += got
            if order.docstatus == 1 and order.status == 'Closed':
                line['closed'] += max(0.0, flt(order.stock_qty) - got)
    for info in result.values():
        if info['stopped']:
            for line in info['lines'].values():
                line['closed'] += max(0.0, line['qty'] - line['ordered'])
        info['lines'] = list(info['lines'].values())
    return result


def proposal_stage(doc, totals=None):
    """Board stage of one proposal (spec 003, FR-026/FR-030)."""
    from lotus_farm import proposal_rules
    lines = (totals or proposal_totals([doc.name])).get(doc.name, {}).get('lines', []) if doc.docstatus == 1 else []
    return proposal_rules.stage(doc.docstatus, doc.get('lotus_proposal_state'), lines)


def proposal_progress(doc):
    """Quantities use the proposal UOM. Each document is permission checked before disclosure."""
    from lotus_farm.procurement import document
    orders, receipts, invoices, payments = {}, {}, {}, {}
    quantities = {r.name: dict(ordered_qty=0.0, received_qty=0.0, billed_qty=0.0) for r in doc.items}
    order_lines = {}
    can_orders = frappe.has_permission('Purchase Order', 'read')
    if can_orders:
        linked_orders = frappe.get_all('Purchase Order Item', filters={'material_request': doc.name}, pluck='parent', distinct=True, limit_page_length=0)
        names = frappe.get_list('Purchase Order', filters={'company': doc.company, 'name': ['in', linked_orders or ['']], 'docstatus': ['<', 2]},
                               pluck='name', limit_page_length=0)
        for name in names:
            order = document('Purchase Order', name, doc.company)
            linked = [r for r in order.items if r.material_request == doc.name and r.material_request_item in quantities]
            if not linked:
                continue
            orders[name] = dict(doctype='Purchase Order', name=name, date=str(order.transaction_date), docstatus=order.docstatus, status=order.status)
            for row in linked:
                source = next(r for r in doc.items if r.name == row.material_request_item)
                factor = flt(source.conversion_factor) or 1
                order_lines[row.name] = (source.name, factor)
                if order.docstatus == 1:
                    quantities[source.name]['ordered_qty'] += flt(row.stock_qty) / factor
    for dt, target, date_field in [('Purchase Receipt', receipts, 'posting_date'), ('Purchase Invoice', invoices, 'posting_date')]:
        if not frappe.has_permission(dt, 'read'):
            continue
        link_field = 'purchase_order_item' if dt == 'Purchase Receipt' else 'po_detail'
        linked_entries = frappe.get_all(dt + ' Item', filters={link_field: ['in', list(order_lines) or ['']]},
                                       pluck='parent', distinct=True, limit_page_length=0)
        for name in frappe.get_list(dt, filters={'company': doc.company, 'name': ['in', linked_entries or ['']], 'docstatus': ['<', 2]}, pluck='name', limit_page_length=0):
            entry = document(dt, name, doc.company)
            linked = [r for r in entry.items if r.get('purchase_order_item' if dt == 'Purchase Receipt' else 'po_detail') in order_lines]
            if not linked:
                continue
            target[name] = dict(doctype=dt, name=name, date=str(entry.get(date_field)), docstatus=entry.docstatus,
                                is_return=entry.is_return)
            key = 'received_qty' if dt == 'Purchase Receipt' else 'billed_qty'
            for row in linked:
                line, factor = order_lines[row.get('purchase_order_item' if dt == 'Purchase Receipt' else 'po_detail')]
                if entry.docstatus == 1:
                    quantities[line][key] += flt(row.stock_qty) / factor
            if dt == 'Purchase Invoice':
                target[name].update(amount=flt(entry.grand_total), outstanding_amount=flt(entry.outstanding_amount))
    if frappe.has_permission('Payment Entry', 'read'):
        refs = [*orders, *invoices]
        for name in frappe.get_all('Payment Entry Reference', filters={'reference_name': ['in', refs or ['']],
                                 'reference_doctype': ['in', ['Purchase Order', 'Purchase Invoice']]}, pluck='parent', distinct=True):
            if not frappe.has_permission('Payment Entry', 'read', name):
                continue
            payment = document('Payment Entry', name, doc.company)
            if payment.docstatus == 2:
                continue
            allocations = sum(flt(r.allocated_amount) for r in payment.references if r.reference_name in refs)
            payments[name] = dict(doctype='Payment Entry', name=name, date=str(payment.posting_date), docstatus=payment.docstatus,
                                 amount=allocations, payment_type=payment.payment_type)
    lines = []
    for row in doc.items:
        q = quantities[row.name]
        lines.append(dict(name=row.name, item_name=row.item_name, uom=row.uom, qty=flt(row.qty), **q,
                          remaining_order_qty=max(0, flt(row.qty) - q['ordered_qty']),
                          remaining_receive_qty=max(0, q['ordered_qty'] - q['received_qty']),
                          source=frappe.parse_json(row.get('lotus_purchase_sources') or '[]')))
    # One stage for every viewer (spec 003, FR-026): computed from totals, not from what this user may read.
    totals = proposal_totals([doc.name]) if doc.docstatus == 1 else {}
    stage = proposal_stage(doc, totals)
    closed = {t['name']: t for t in totals.get(doc.name, {}).get('lines', [])}
    for line in lines:
        factor = flt(next((r.conversion_factor for r in doc.items if r.name == line['name']), 1)) or 1
        line['closed_qty'] = flt(closed.get(line['name'], {}).get('closed')) / factor
    return dict(stage=stage, lines=lines, orders=list(orders.values()), receipts=list(receipts.values()),
                invoices=list(invoices.values()), payments=list(payments.values()),
                receiving_status='Đã nhận đủ' if lines and all(r['received_qty'] >= r['qty'] - .000001 for r in lines) else 'Chưa nhận đủ',
                invoice_status='Đã có hóa đơn đủ' if lines and all(r['billed_qty'] >= r['qty'] - .000001 for r in lines) else 'Chưa có hóa đơn đủ',
                outstanding_amount=sum(r.get('outstanding_amount', 0) for r in invoices.values() if r['docstatus'] == 1)
                if frappe.has_permission('Purchase Invoice', 'read') else None)

def _settled(doctype, names):
    """Posted money against documents: payment vouchers (a supplier refund counts negative) and on-behalf payments."""
    out = {}
    if not names:
        return out
    for name, amount in frappe.db.sql('''select r.reference_name,
            sum(case when p.payment_type='Receive' then -r.allocated_amount else r.allocated_amount end)
        from `tabPayment Entry Reference` r join `tabPayment Entry` p on p.name=r.parent
        where p.docstatus=1 and r.reference_doctype=%s and r.reference_name in %s group by r.reference_name''', (doctype, tuple(names))):
        out[name] = out.get(name, 0) + flt(amount)
    for name, amount in frappe.db.sql('''select a.reference_name, sum(a.debit_in_account_currency-a.credit_in_account_currency)
        from `tabJournal Entry Account` a join `tabJournal Entry` j on j.name=a.parent
        where j.docstatus=1 and ifnull(j.lotus_purchase_funding,'')!='' and a.party_type='Supplier'
        and a.reference_type=%s and a.reference_name in %s group by a.reference_name''', (doctype, tuple(names))):
        out[name] = out.get(name, 0) + flt(amount)
    return out


def order_paid(names):
    """Money paid per purchase order (spec 003, FR-039): what is posted against the order itself (advances) plus what is
    posted against its invoices. An invoice shared by several orders is split by the value of each order's lines on it.
    Returns None when the reader may not see payments."""
    if not frappe.has_permission('Payment Entry', 'read'):
        return None
    names = [n for n in dict.fromkeys(names or []) if n]
    paid = {n: 0.0 for n in names}
    if not names:
        return paid
    lines = frappe.get_all('Purchase Invoice Item', filters={'purchase_order': ['in', names], 'docstatus': 1},
                           fields=['parent', 'purchase_order', 'base_net_amount'], limit_page_length=0)
    invoices = sorted({r.parent for r in lines})
    totals = {}
    for r in frappe.get_all('Purchase Invoice Item', filters={'parent': ['in', invoices or ['']]},
                            fields=['parent', 'base_net_amount'], limit_page_length=0):
        totals[r.parent] = totals.get(r.parent, 0) + abs(flt(r.base_net_amount))
    for name, amount in _settled('Purchase Order', names).items():
        paid[name] += amount
    on_invoice = _settled('Purchase Invoice', invoices)
    for r in lines:
        if totals.get(r.parent) and on_invoice.get(r.parent):
            paid[r.purchase_order] += on_invoice[r.parent] * abs(flt(r.base_net_amount)) / totals[r.parent]
    return paid


def receipt_needs_evidence(doc):
    """Receipts against an order of the purchase-flow company (not returns) need the deliverer's confirmation."""
    return bool(enabled(doc.company) and not doc.get('is_return') and any(r.get('purchase_order') for r in doc.get('items') or []))


def _own_file(doc, url):
    return bool(url and doc.name and frappe.db.exists('File', {'file_url': url, 'attached_to_doctype': doc.doctype, 'attached_to_name': doc.name}))


def receipt_has_evidence(doc):
    """The deliverer's name with the signature drawn on screen, or the photo of the signed delivery note.
    Either file must be an attachment of this receipt."""
    signed = bool(str(doc.get('lotus_deliverer_name') or '').strip()) and _own_file(doc, doc.get('lotus_deliverer_signature'))
    return signed or _own_file(doc, doc.get('lotus_delivery_proof'))


def receipt_evidence(doc, method=None):
    """before_submit of Purchase Receipt (spec 003, FR-042), whichever screen or API posts it."""
    if receipt_needs_evidence(doc) and not receipt_has_evidence(doc):
        frappe.throw('Phiếu nhập theo đơn cần chữ ký kèm họ tên của người giao hàng, hoặc ảnh phiếu giao hàng có chữ ký.')


def receipt_signed(doc, method=None):
    """on_submit of Purchase Receipt (spec 003, FR-043): confirming a receipt against an order is the signature of
    the storekeeper who confirms it. It is recorded with the posting and the signed PDF is stored; a failure
    here undoes the posting."""
    from lotus_farm import signing
    if signing.chain_for(doc, fresh=True) == 'purchase_receipt':
        signing.start(doc, {})
