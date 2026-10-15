"""Approved-source picking and locked quantity limits for warehouse issues."""
from collections import defaultdict

import frappe
from frappe.utils import flt
from lotus_farm.controls import lock


def install_fields():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    create_custom_fields({
        'Stock Entry': [
            dict(fieldname='lotus_issue_mode', label='Lotus Issue Mode', fieldtype='Select',
                 options='\nManual\nPlan\nRequest', read_only=1, no_copy=1, insert_after='stock_entry_type'),
            dict(fieldname='lotus_work_plan', label='Lotus Work Plan', fieldtype='Link',
                 options='Daily Work Plan', read_only=1, no_copy=1, insert_after='lotus_issue_mode'),
            dict(fieldname='lotus_receiver', label='Tên người nhận (HRMS)', fieldtype='Data', read_only=1, insert_after='lotus_work_plan'),
            dict(fieldname='lotus_receiver_employee', label='Người nhận vật tư (HRMS)', fieldtype='Link', options='Employee', insert_after='lotus_receiver'),
        ],
        'Stock Entry Detail': [
            dict(fieldname='lotus_usage_area', label='Khu vực / lô sử dụng', fieldtype='Data', insert_after='item_code'),
            dict(fieldname='lotus_requirement', label='Lotus Material Requirement', fieldtype='Link',
                 options='Material Requirement', read_only=1, no_copy=1, insert_after='lotus_usage_area'),
            dict(fieldname='lotus_requirement_line', label='Lotus Requirement Line', fieldtype='Data',
                 read_only=1, no_copy=1, insert_after='lotus_requirement'),
        ],
        'Material Request Item': [
            dict(fieldname='lotus_usage_area', label='Khu vực / lô sử dụng', fieldtype='Data', insert_after='item_code'),
        ],
    })


def approved(doctype, name, company):
    if doctype not in ('Daily Work Plan', 'Material Requirement', 'Material Request'):
        frappe.throw('Nguồn xuất kho không hợp lệ.')
    doc = frappe.get_doc(doctype, name)
    doc.check_permission('read')
    if doc.docstatus != 1 or doc.company != company:
        frappe.throw('Nguồn phải đã duyệt và thuộc công ty đang chọn.')
    if doctype == 'Material Request' and doc.material_request_type != 'Material Issue':
        frappe.throw('Chỉ dùng yêu cầu cấp vật tư, không dùng đề nghị mua hoặc chuyển kho.')
    if doctype == 'Material Request' and doc.get('status') in ('Stopped', 'Closed', 'Cancelled'):
        frappe.throw('Yêu cầu đã đóng hoặc dừng, không thể cấp thêm.')
    return doc


def source_line(doctype, name, line_name, company, plan=None):
    doc = approved(doctype, name, company)
    if doctype == 'Material Requirement':
        parent = approved('Daily Work Plan', doc.work_plan, company)
        if plan and parent.name != plan:
            frappe.throw('Nhu cầu vật tư không thuộc kế hoạch đã chọn.')
        row = next((r for r in doc.lines if r.name == line_name), None)
        if not row:
            frappe.throw('Dòng nhu cầu không hợp lệ.')
        item = frappe.get_doc('Item', row.item)
        item.check_permission('read')
        from erpnext.stock.get_item_details import get_conversion_factor
        factor = flt(get_conversion_factor(item.name, row.uom).get('conversion_factor'))
        if factor <= 0:
            frappe.throw('Chưa có quy đổi đơn vị cho ' + item.name)
        return dict(item=item.name, item_name=item.item_name, uom=item.stock_uom,
                    required_qty=flt(row.required_qty) * factor,
                    area=' / '.join(filter(None, [doc.farm_block, doc.farm_plot])),
                    requirement=doc.name, requirement_line=row.name, plan=parent.name,warehouse=doc.get('lotus_warehouse'))
    row = next((r for r in doc.items if r.name == line_name), None)
    if not row:
        frappe.throw('Dòng yêu cầu không hợp lệ.')
    item = frappe.get_doc('Item', row.item_code)
    item.check_permission('read')
    if row.get('lotus_requirement'):
        info=source_line('Material Requirement',row.lotus_requirement,row.lotus_requirement_line,company)
        if info['item']!=item.name:frappe.throw('Vật tư không khớp nhu cầu kế hoạch gốc.')
        info.update(material_request=doc.name,material_request_item=row.name)
        return info
    return dict(item=item.name, item_name=item.item_name, uom=item.stock_uom,
                required_qty=flt(row.stock_qty), area=row.get('lotus_usage_area') or '',
                material_request=doc.name, material_request_item=row.name,warehouse=row.warehouse)


def allocation_totals(doctype, name, line_name, exclude=None):
    # The source has already been permission-checked. Count all allocations,
    # including those made by another stock user, without exposing their documents.
    if doctype not in ('Material Requirement','Material Request'):frappe.throw('Nguồn cấp không hợp lệ.')
    if doctype=='Material Request':
        source=frappe.get_doc(doctype,name)
        row=next((r for r in source.items if r.name==line_name),None)
        if row and row.get('lotus_requirement'):
            return allocation_totals('Material Requirement',row.lotus_requirement,row.lotus_requirement_line,exclude)
    fields = ('lotus_requirement', 'lotus_requirement_line') if doctype == 'Material Requirement' else ('material_request', 'material_request_item')
    canonical=''' or d.material_request_item in (select name from `tabMaterial Request Item`
        where lotus_requirement=%(name)s and lotus_requirement_line=%(line)s)
        or d.name in (select c.stock_entry_detail from `tabMaterial Consumption` c
            join `tabMaterial Requirement Line` l on l.parent=c.material_requirement and l.item=c.item
            where c.docstatus=1 and c.material_requirement=%(name)s and l.name=%(line)s)''' if doctype=='Material Requirement' else ''
    condition=f"((d.`{fields[0]}`=%(name)s and d.`{fields[1]}`=%(line)s){canonical})"
    result = frappe.db.sql(f'''select p.docstatus, coalesce(sum(d.qty * d.conversion_factor), 0)
        from `tabStock Entry Detail` d join `tabStock Entry` p on p.name=d.parent
        where p.docstatus < 2 and p.stock_entry_type='Material Issue' and p.name != %(exclude)s and {condition} group by p.docstatus''',
        dict(exclude=exclude or '', name=name, line=line_name))
    recovered=frappe.db.sql(f'''select coalesce(sum(r.recovered_qty),0) from `tabMaterial Recovery` r
        join `tabMaterial Consumption` c on c.name=r.consumption and c.docstatus=1
        join `tabStock Entry Detail` d on d.name=c.stock_entry_detail
        join `tabStock Entry` p on p.name=d.parent and p.docstatus=1 and p.stock_entry_type='Material Issue'
        where r.docstatus=1 and p.name!=%(exclude)s and {condition}''',dict(exclude=exclude or '',name=name,line=line_name))[0][0]
    return dict(draft=sum(flt(r[1]) for r in result if r[0]==0),posted=max(0,sum(flt(r[1]) for r in result if r[0]==1)-flt(recovered)))


def allocated(doctype,name,line_name,exclude=None):
    return sum(allocation_totals(doctype,name,line_name,exclude).values())


def choices(company, mode):
    from lotus_farm.warehouse import _access, _company
    _access()
    _company(company)
    if mode not in ('Plan', 'Request'):
        frappe.throw('Tab nguồn xuất không hợp lệ.')
    dt = 'Daily Work Plan' if mode == 'Plan' else 'Material Request'
    if not frappe.has_permission(dt, 'read'):
        return dict(rows=[], note='Tài khoản chưa có quyền đọc nguồn này.')
    filters = dict(company=company, docstatus=1)
    if mode == 'Request':
        filters['material_request_type'] = 'Material Issue'
        filters['status'] = ['not in', ['Stopped', 'Closed', 'Cancelled']]
    date = 'posting_date' if mode == 'Plan' else 'transaction_date'
    rows = frappe.get_list(dt, filters=filters, fields=['name', date], order_by=date+' desc, modified desc', limit_page_length=100)
    return dict(rows=[dict(name=r.name, date=r[date]) for r in rows], note='Hiển thị tối đa 100 nguồn đã duyệt gần nhất.')


def lines(company, mode, name):
    from lotus_farm.warehouse import _access, _company
    _access()
    _company(company)
    if mode not in ('Plan', 'Request'):
        frappe.throw('Nguồn không hợp lệ.')
    rows = []
    if mode == 'Plan':
        approved('Daily Work Plan', name, company)
        if not frappe.has_permission('Material Requirement', 'read'):
            return dict(rows=[], note='Bạn chưa có quyền đọc nhu cầu vật tư của kế hoạch.')
        sources = [('Material Requirement', n) for n in frappe.get_list('Material Requirement',
                   filters={'work_plan': name, 'docstatus': 1}, pluck='name', limit_page_length=1000)]
    else:
        approved('Material Request', name, company)
        sources = [('Material Request', name)]
    for dt, source in sources:
        doc = approved(dt, source, company)
        for row in (doc.lines if dt == 'Material Requirement' else doc.items):
            info = source_line(dt, source, row.name, company, name if mode == 'Plan' else None)
            info['allocated_qty'] = allocated(dt, source, row.name)
            info['remaining_qty'] = max(0, info['required_qty'] - info['allocated_qty'])
            if info['remaining_qty'] > 0:
                rows.append(info)
    return dict(rows=rows, note='Phần còn cấp đã trừ phiếu nháp và phiếu đã ghi sổ; phiếu hủy không giữ số lượng.')


def validate_issue(doc, method=None):
    mode = doc.get('lotus_issue_mode')
    if doc.docstatus == 2:
        return
    if not mode:
        if doc.get('lotus_work_plan') or any(row.get('lotus_requirement') or row.get('lotus_requirement_line') for row in doc.items):
            frappe.throw('Phiếu liên kết nhu cầu kế hoạch phải có hình thức xuất kho.')
        return
    if mode not in ('Manual', 'Plan', 'Request') or doc.stock_entry_type != 'Material Issue':
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
    if mode == 'Plan':
        lock('Daily Work Plan', doc.lotus_work_plan)
        approved('Daily Work Plan', doc.lotus_work_plan, doc.company)
    refs = []
    for row in doc.items:
        req, request = row.get('lotus_requirement'), row.get('material_request')
        if not str(row.get('lotus_usage_area') or '').strip():
            frappe.throw('Mỗi dòng xuất cần khu vực / lô sử dụng.')
        if mode == 'Manual':
            if req or request:
                frappe.throw('Xuất thủ công không được gắn nguồn yêu cầu.')
            continue
        if mode == 'Plan' and req and not request:
            refs.append(('Material Requirement', req, row.get('lotus_requirement_line'), row))
        elif mode == 'Request' and request and not req:
            refs.append(('Material Request', request, row.get('material_request_item'), row))
        else:
            frappe.throw('Dòng xuất thiếu nguồn hợp lệ của tab đã chọn.')
    for dt, name in sorted({(dt, name) for dt, name, _, _ in refs}):
        lock(dt, name)
    totals = defaultdict(float)
    limits = {}
    for dt, name, line_name, row in refs:
        info = source_line(dt, name, line_name, doc.company, doc.get('lotus_work_plan') if mode == 'Plan' else None)
        if info['item'] != row.item_code or (info['area'] and row.lotus_usage_area != info['area']):
            frappe.throw('Vật tư hoặc khu vực không khớp nguồn đã duyệt.')
        if info.get('warehouse') and info['warehouse']!=row.s_warehouse:
            frappe.throw('Kho xuất không khớp kho đã chỉ định của nhu cầu.')
        qty = flt(row.qty) * flt(row.conversion_factor)
        if qty <= 0:
            frappe.throw('Số lượng cấp phải lớn hơn 0.')
        key = ('Material Requirement',info['requirement'],info['requirement_line']) if info.get('requirement') else (dt, name, line_name)
        if key[0]=='Material Requirement':lock(key[0],key[1])
        totals[key] += qty
        limits[key] = info['required_qty']
    for key, qty in totals.items():
        if qty + allocated(*key, exclude=doc.name) > limits[key] + 0.000001:
            frappe.throw('Số lượng cấp vượt phần còn được cấp của nguồn đã duyệt.')
