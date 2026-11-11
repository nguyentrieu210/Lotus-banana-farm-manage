"""Approved-request picking and locked quantity limits for warehouse issues."""
from collections import defaultdict

import frappe
from frappe.utils import flt
from lotus_farm.controls import lock


def install_fields():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    create_custom_fields({
        'Stock Entry': [
            dict(fieldname='lotus_issue_mode', label='Lotus Issue Mode', fieldtype='Select',
                 options='\nManual\nRequest', read_only=1, no_copy=1, insert_after='stock_entry_type'),
            dict(fieldname='lotus_receiver', label='Tên người nhận (HRMS)', fieldtype='Data', read_only=1, insert_after='lotus_issue_mode'),
            dict(fieldname='lotus_receiver_employee', label='Người nhận vật tư (HRMS)', fieldtype='Link', options='Employee', insert_after='lotus_receiver'),
        ],
        'Stock Entry Detail': [
            dict(fieldname='lotus_usage_area', label='Khu vực / lô sử dụng', fieldtype='Data', insert_after='item_code'),
        ],
        'Material Request Item': [
            dict(fieldname='lotus_usage_area', label='Khu vực / lô sử dụng', fieldtype='Data', insert_after='item_code'),
        ],
    })


def approved(name, company):
    """The approved material issue request `name` of the company, read with the user's permission."""
    doc = frappe.get_doc('Material Request', name)
    doc.check_permission('read')
    if doc.docstatus != 1 or doc.company != company:
        frappe.throw('Nguồn phải đã duyệt và thuộc công ty đang chọn.')
    if doc.material_request_type != 'Material Issue':
        frappe.throw('Chỉ dùng yêu cầu cấp vật tư, không dùng đề xuất mua hoặc chuyển kho.')
    if doc.get('status') in ('Stopped', 'Closed', 'Cancelled'):
        frappe.throw('Yêu cầu đã đóng hoặc dừng, không thể cấp thêm.')
    return doc


def source_line(name, line_name, company):
    doc = approved(name, company)
    row = next((r for r in doc.items if r.name == line_name), None)
    if not row:
        frappe.throw('Dòng yêu cầu không hợp lệ.')
    item = frappe.get_doc('Item', row.item_code)
    item.check_permission('read')
    return dict(item=item.name, item_name=item.item_name, uom=item.stock_uom,
                required_qty=flt(row.stock_qty), area=row.get('lotus_usage_area') or '',
                material_request=doc.name, material_request_item=row.name,warehouse=row.warehouse)


def allocation_totals(name, line_name, exclude=None):
    # The request has already been permission-checked. Count all allocations,
    # including those made by another stock user, without exposing their documents.
    result = frappe.db.sql('''select p.docstatus, coalesce(sum(d.qty * d.conversion_factor), 0)
        from `tabStock Entry Detail` d join `tabStock Entry` p on p.name=d.parent
        where p.docstatus < 2 and p.stock_entry_type='Material Issue' and p.name != %(exclude)s
        and d.material_request=%(name)s and d.material_request_item=%(line)s group by p.docstatus''',
        dict(exclude=exclude or '', name=name, line=line_name))
    return dict(draft=sum(flt(r[1]) for r in result if r[0]==0),posted=sum(flt(r[1]) for r in result if r[0]==1))


def allocated(name,line_name,exclude=None):
    return sum(allocation_totals(name,line_name,exclude).values())


def choices(company, mode):
    from lotus_farm.warehouse import _access, _company
    _access()
    _company(company)
    if mode != 'Request':
        frappe.throw('Tab nguồn xuất không hợp lệ.')
    if not frappe.has_permission('Material Request', 'read'):
        return dict(rows=[], note='Tài khoản chưa có quyền đọc nguồn này.')
    filters = dict(company=company, docstatus=1, material_request_type='Material Issue',
                   status=['not in', ['Stopped', 'Closed', 'Cancelled']])
    rows = frappe.get_list('Material Request', filters=filters, fields=['name', 'transaction_date'],
                           order_by='transaction_date desc, modified desc', limit_page_length=100)
    return dict(rows=[dict(name=r.name, date=r.transaction_date) for r in rows], note='Hiển thị tối đa 100 nguồn đã duyệt gần nhất.')


def lines(company, mode, name):
    from lotus_farm.warehouse import _access, _company
    from lotus_farm.warehouse_masters import item_uoms
    _access()
    _company(company)
    if mode != 'Request':
        frappe.throw('Nguồn không hợp lệ.')
    rows = []
    for row in approved(name, company).items:
        info = source_line(name, row.name, company)
        item = frappe.get_doc('Item', info['item'])
        info.update(stock_uom=item.stock_uom, uoms=item_uoms(item))
        info['allocated_qty'] = allocated(name, row.name)
        info['remaining_qty'] = max(0, info['required_qty'] - info['allocated_qty'])
        if info['remaining_qty'] > 0:
            rows.append(info)
    return dict(rows=rows, note='Phần còn cấp đã trừ phiếu nháp và phiếu đã ghi sổ; phiếu hủy không giữ số lượng.')


def validate_issue(doc, method=None):
    mode = doc.get('lotus_issue_mode')
    if doc.docstatus == 2 or not mode:
        return
    if mode not in ('Manual', 'Request') or doc.stock_entry_type != 'Material Issue':
        frappe.throw('Hình thức xuất kho không hợp lệ.')
    if doc.get('lotus_receiver_employee'):
        from lotus_farm.warehouse_masters import employee_contact
        staff=employee_contact(doc.company,doc.lotus_receiver_employee)
        # Name is a display snapshot; HRMS remains the source of truth.
        doc.lotus_receiver=staff.employee_name
    if not str(doc.get('lotus_receiver') or '').strip():
        frappe.throw('Cần nhập người nhận vật tư.')
    if mode == 'Manual' and not str(doc.remarks or '').strip():
        frappe.throw('Xuất thủ công cần lý do xuất.')
    refs = []
    for row in doc.items:
        request = row.get('material_request')
        if not str(row.get('lotus_usage_area') or '').strip():
            frappe.throw('Mỗi dòng xuất cần khu vực / lô sử dụng.')
        if mode == 'Manual':
            if request:
                frappe.throw('Xuất thủ công không được gắn nguồn yêu cầu.')
            continue
        if not request:
            frappe.throw('Dòng xuất thiếu nguồn hợp lệ của tab đã chọn.')
        refs.append((request, row.get('material_request_item'), row))
    for name in sorted({name for name, _, _ in refs}):
        lock('Material Request', name)
    totals = defaultdict(float)
    limits = {}
    for name, line_name, row in refs:
        info = source_line(name, line_name, doc.company)
        if info['item'] != row.item_code or (info['area'] and row.lotus_usage_area != info['area']):
            frappe.throw('Vật tư hoặc khu vực không khớp nguồn đã duyệt.')
        if info.get('warehouse') and info['warehouse']!=row.s_warehouse:
            frappe.throw('Kho xuất không khớp kho đã chỉ định của nhu cầu.')
        qty = flt(row.qty) * flt(row.conversion_factor)
        if qty <= 0:
            frappe.throw('Số lượng cấp phải lớn hơn 0.')
        key = (name, line_name)
        totals[key] += qty
        limits[key] = info['required_qty']
    for key, qty in totals.items():
        if qty + allocated(*key, exclude=doc.name) > limits[key] + 0.000001:
            frappe.throw('Số lượng cấp vượt phần còn được cấp của nguồn đã duyệt.')
