"""Lotus purchase policy and progress derived from native ERPNext documents."""
import frappe
from frappe.utils import flt, now_datetime


def enabled(company):
    return bool(company and company == frappe.conf.get('lotus_purchase_flow_company'))


def install():
    if not frappe.conf.get('lotus_purchase_flow_company') and frappe.db.exists('Company', 'Lotus Agritech'):
        frappe.conf.lotus_purchase_flow_company = 'Lotus Agritech'
        frappe.conf.lotus_purchase_flow_since = str(now_datetime())
        frappe.update_site_config('lotus_purchase_flow_company', 'Lotus Agritech')
        frappe.update_site_config('lotus_purchase_flow_since', frappe.conf.lotus_purchase_flow_since)


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


def order_guard(doc, method=None):
    if not enabled(doc.company):
        return
    from lotus_farm.controls import lock
    lock('Company', doc.company)
    amounts = {}
    for row in doc.items:
        if not row.material_request or not row.material_request_item:
            frappe.throw('Đơn mua cần lấy từng dòng từ đề xuất mua đã duyệt. Hàng đã mua lẻ dùng Mua nhanh.')
        lock('Material Request', row.material_request)
        source = frappe.get_doc('Material Request', row.material_request)
        source.check_permission('read')
        require_approved(source)
        original = next((r for r in source.items if r.name == row.material_request_item), None)
        if source.company != doc.company or source.material_request_type != 'Purchase' or not original or original.item_code != row.item_code:
            frappe.throw('Dòng đơn mua không khớp đề xuất mua nguồn.')
        key = original.name
        amounts[key] = amounts.get(key, 0) + flt(row.stock_qty)
        if amounts[key] > flt(original.stock_qty) - flt(original.ordered_qty) + .000001:
            frappe.throw('Số đặt mua vượt phần còn lại của đề xuất.')


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
            orders[name] = dict(name=name, date=str(order.transaction_date), docstatus=order.docstatus, status=order.status)
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
            target[name] = dict(name=name, date=str(entry.get(date_field)), docstatus=entry.docstatus,
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
            payments[name] = dict(name=name, date=str(payment.posting_date), docstatus=payment.docstatus,
                                 amount=allocations, payment_type=payment.payment_type)
    lines = []
    for row in doc.items:
        q = quantities[row.name]
        lines.append(dict(name=row.name, item_name=row.item_name, uom=row.uom, qty=flt(row.qty), **q,
                          remaining_order_qty=max(0, flt(row.qty) - q['ordered_qty']),
                          remaining_receive_qty=max(0, q['ordered_qty'] - q['received_qty']),
                          source=frappe.parse_json(row.get('lotus_purchase_sources') or '[]')))
    if doc.docstatus == 0:
        stage = 'Nháp' if (doc.get('lotus_proposal_state') or 'Nháp') in ('Nháp', 'Trả lại') else 'Chờ ký'
    elif not can_orders:
        stage = 'Đã duyệt'
    elif not orders:
        stage = 'Đã duyệt chờ mua'
    else:
        complete = all(q['received_qty'] >= flt(r.qty) - .000001 for r in doc.items for q in [quantities[r.name]])
        stage = 'Hoàn tất' if complete else 'Đang mua'
    return dict(stage=stage, lines=lines, orders=list(orders.values()), receipts=list(receipts.values()),
                invoices=list(invoices.values()), payments=list(payments.values()),
                receiving_status='Đã nhận đủ' if lines and all(r['received_qty'] >= r['qty'] - .000001 for r in lines) else 'Chưa nhận đủ',
                invoice_status='Đã có hóa đơn đủ' if lines and all(r['billed_qty'] >= r['qty'] - .000001 for r in lines) else 'Chưa có hóa đơn đủ',
                outstanding_amount=sum(r.get('outstanding_amount', 0) for r in invoices.values() if r['docstatus'] == 1)
                if frappe.has_permission('Purchase Invoice', 'read') else None)
