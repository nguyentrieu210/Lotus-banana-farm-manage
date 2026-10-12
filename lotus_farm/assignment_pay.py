"""Prices are agreed on the work plan; acceptance never reprices a task."""
import frappe
from frappe.utils import getdate, now_datetime
from lotus_farm.controls import command_allowed
from lotus_farm.piece_pay import terms
from lotus_farm.rules import quantity, RuleError


def price_for(farm, work_type, uom, date):
    names = frappe.get_list('Work Piece Rate', filters={
        'farm': farm, 'work_type': work_type, 'uom': uom, 'docstatus': 1,
        'valid_from': ['<=', date], 'valid_to': ['>=', date],
    }, pluck='name', limit_page_length=2)
    if len(names) != 1:
        frappe.throw('Cần đúng một đơn giá khoán đã duyệt, còn hiệu lực trong ngày giao.')
    rate = frappe.get_doc('Work Piece Rate', names[0])
    rate.check_permission('read')
    if rate.currency != 'VND':
        frappe.throw('Đơn giá khoán phải tính bằng VND.')
    return rate


def validate_plan_prices(doc):
    before = doc.get_doc_before_save()
    if before and before.docstatus == 1:
        protect_submitted_prices(doc)
        return
    old = {r.name: r for r in before.lines} if before else {}
    pending = False
    for row in doc.lines:
        previous = old.get(row.name)
        same = (previous and before.farm == doc.farm
                and getdate(before.posting_date) == getdate(doc.posting_date)
                and previous.work_type == row.work_type and previous.uom == row.uom)
        work = frappe.get_doc('Work Type', row.work_type)
        row.payment_basis = row.get('payment_basis') or work.get('payment_basis') or 'Daywork'
        if row.payment_basis not in ('Daywork', 'Piece'):
            frappe.throw('Chọn công nhật hoặc khoán sản lượng.')
        row.price_approved_by = None
        row.price_approved_at = None
        if row.payment_basis == 'Daywork':
            row.piece_rate = None
            row.listed_unit_price = row.agreed_unit_price = row.estimated_amount = 0
            row.price_approval_state = 'Not Required'
            continue
        if not row.work_team:
            frappe.throw('Việc khoán phải giao cho một tổ.')
        if not (row.get('acceptance_criteria') or '').strip():
            frappe.throw('Ghi tiêu chuẩn đạt trước khi giao việc khoán.')
        # Stored draft snapshots survive later changes to the price catalog.
        if same and previous.get('piece_rate') and previous.payment_basis == 'Piece':
            row.piece_rate = previous.piece_rate
            row.listed_unit_price = previous.listed_unit_price
        else:
            rate = price_for(doc.farm, row.work_type, row.uom, doc.posting_date)
            row.piece_rate, row.listed_unit_price = rate.name, rate.unit_price
        rate = frappe.get_doc('Work Piece Rate', row.piece_rate)
        if rate.docstatus != 1:
            frappe.throw('Giá niêm yết đã bị hủy; tạo lại dòng giao việc để chọn giá mới.')
        try:
            row.update(terms(row.listed_unit_price, row.get('agreed_unit_price') or None,
                             row.planned_qty, row.get('price_reason')))
        except RuleError as exc:
            frappe.throw(str(exc))
        if row.price_approval_state == 'Pending':
            pending = True
            if doc.docstatus == 1:
                if not command_allowed(doc, 'approve_assignment_price') or frappe.session.user in (doc.owner, before.modified_by if before else doc.owner):
                    frappe.throw('Giá vượt niêm yết cần quản lý khác duyệt trước khi giao.')
                row.price_approval_state = 'Approved'
                row.price_approved_by = frappe.session.user
                row.price_approved_at = now_datetime()
    doc.price_approval_state = 'Approved' if pending and doc.docstatus == 1 else ('Pending' if pending else 'Not Required')


def protect_submitted_prices(doc, method=None):
    before = doc.get_doc_before_save()
    if not before or before.docstatus != 1:
        return
    fields = ('payment_basis', 'piece_rate', 'listed_unit_price', 'agreed_unit_price',
              'estimated_amount', 'price_reason', 'price_approval_state',
              'price_approved_by', 'price_approved_at', 'acceptance_criteria')
    old = {r.name: r for r in before.lines}
    if doc.price_approval_state != before.price_approval_state:
        frappe.throw('Không sửa giá của kế hoạch đã giao. Hủy và lập bản sửa có lý do.')
    for row in doc.lines:
        if row.name not in old or any(row.get(f) != old[row.name].get(f) for f in fields):
            frappe.throw('Không sửa giá của kế hoạch đã giao. Hủy và lập bản sửa có lý do.')
