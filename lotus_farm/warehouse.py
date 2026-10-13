"""Warehouse console backed exclusively by ERPNext stock documents."""
import math

import frappe
from frappe.utils import cint, flt, getdate, nowdate


@frappe.whitelist()
def issue_sources(company, mode):
    from lotus_farm.warehouse_issue import choices
    return choices(company, mode)


@frappe.whitelist()
def issue_lines(company, mode, name):
    from lotus_farm.warehouse_issue import lines
    return lines(company, mode, name)


def _access():
    if frappe.session.user == 'Guest':
        frappe.throw('Vui lòng đăng nhập.', frappe.AuthenticationError)
    for dt in ('Stock Entry', 'Warehouse', 'Item', 'Bin', 'Company'):
        if not frappe.has_permission(dt, 'read'):
            frappe.throw('Bạn cần quyền đọc ' + dt, frappe.PermissionError)


def _company(name):
    doc = frappe.get_doc('Company', name)
    doc.check_permission('read')
    return doc


def _warehouse(name, company):
    doc = frappe.get_doc('Warehouse', name)
    doc.check_permission('read')
    if doc.company != company or doc.is_group or doc.disabled:
        frappe.throw('Kho phải đang hoạt động và thuộc công ty đã chọn.')
    return doc


@frappe.whitelist()
def bootstrap():
    _access()
    from frappe.sessions import get_csrf_token
    return dict(user=frappe.session.user, csrf_token=get_csrf_token(), today=nowdate(),
                companies=frappe.get_list('Company', fields=['name', 'default_currency'], limit_page_length=1000),
                permissions={dt: frappe.has_permission(dt, 'create') for dt in
                             ('Item', 'Item Group', 'Warehouse', 'Stock Entry', 'Stock Reconciliation', 'Company')})


@frappe.whitelist()
def catalogue(company):
    _access()
    _company(company)
    return dict(
        groups=frappe.get_list('Item Group', fields=['name', 'is_group', 'parent_item_group'], order_by='name', limit_page_length=1000),
        uoms=frappe.get_list('UOM', filters={'enabled': 1}, fields=['name'], order_by='name', limit_page_length=1000),
        parents=frappe.get_list('Warehouse', filters={'company': company, 'is_group': 1, 'disabled': 0},
                               fields=['name', 'warehouse_name'], order_by='name', limit_page_length=1000))


def _text(value, label):
    value = str(value or '').strip()
    if not value or len(value) > 140:
        frappe.throw(label + ' cần từ 1 đến 140 ký tự.')
    return value


def _create_group(name, parent):
    if not frappe.has_permission('Item Group', 'create'):
        frappe.throw('Bạn chưa có quyền thêm nhóm vật tư.', frappe.PermissionError)
    parent_doc = frappe.get_doc('Item Group', parent)
    parent_doc.check_permission('read')
    if not parent_doc.is_group:
        frappe.throw('Nhóm cha phải là nhóm chứa nhóm con.')
    return frappe.get_doc(dict(doctype='Item Group', item_group_name=_text(name, 'Tên nhóm'),
                               parent_item_group=parent, is_group=0)).insert()


@frappe.whitelist(methods=['POST'])
def create_master(company, kind, values):
    _access()
    _company(company)
    values = frappe.parse_json(values)
    if not isinstance(values, dict) or kind not in ('item', 'group', 'warehouse'):
        frappe.throw('Thông tin danh mục không hợp lệ.')
    doctype = {'item': 'Item', 'group': 'Item Group', 'warehouse': 'Warehouse'}[kind]
    if not frappe.has_permission(doctype, 'create'):
        frappe.throw('Bạn chưa có quyền thêm danh mục này.', frappe.PermissionError)
    if kind == 'group':
        doc = _create_group(values.get('name'), values.get('parent'))
    elif kind == 'warehouse':
        parent = frappe.get_doc('Warehouse', values.get('parent'))
        parent.check_permission('read')
        if parent.company != company or not parent.is_group or parent.disabled:
            frappe.throw('Kho cha phải là nhóm kho đang hoạt động của công ty đã chọn.')
        doc = frappe.get_doc(dict(doctype='Warehouse', warehouse_name=_text(values.get('name'), 'Tên kho'),
                                  parent_warehouse=parent.name, company=company, is_group=0)).insert()
    else:
        group = values.get('group')
        if values.get('new_group'):
            group = _create_group(values.get('new_group'), values.get('group_parent')).name
        group_doc = frappe.get_doc('Item Group', group)
        group_doc.check_permission('read')
        uom = frappe.get_doc('UOM', values.get('uom'))
        uom.check_permission('read')
        if not uom.enabled:
            frappe.throw('Đơn vị tính đã bị tắt.')
        doc = frappe.get_doc(dict(doctype='Item', item_code=_text(values.get('code'), 'Mã vật tư'),
                                  item_name=_text(values.get('name'), 'Tên vật tư'), item_group=group,
                                  stock_uom=uom.name, is_stock_item=1, include_item_in_manufacturing=0,
                                  description=str(values.get('description') or '')[:2000])).insert()
    return dict(name=doc.name, kind=kind)


def _stock_doc(doctype, name):
    _access()
    if doctype not in ('Stock Entry', 'Stock Reconciliation'):
        frappe.throw('Loại phiếu không hợp lệ.')
    doc = frappe.get_doc(doctype, name)
    doc.check_permission('read')
    _company(doc.company)
    for row in doc.items:
        for field in ('s_warehouse', 't_warehouse', 'warehouse'):
            if row.get(field):
                warehouse = frappe.get_doc('Warehouse', row.get(field))
                warehouse.check_permission('read')
                if warehouse.company != doc.company:
                    frappe.throw('Kho không thuộc công ty của phiếu.')
    return doc


def _simple_doc(doc):
    if doc.doctype == 'Stock Entry':
        if doc.stock_entry_type not in ('Material Receipt', 'Material Issue', 'Material Transfer') or doc.get('lotus_packout_run'):
            return False
    elif doc.purpose not in ('Opening Stock', 'Stock Reconciliation'):
        return False
    for row in doc.items:
        item = frappe.get_doc('Item', row.item_code)
        item.check_permission('read')
        if item.has_batch_no or item.has_serial_no:
            return False
    return True


@frappe.whitelist()
def document(doctype, name):
    doc = _stock_doc(doctype, name)
    return dict(name=doc.name, doctype=doc.doctype, company=doc.company, docstatus=doc.docstatus,
                posting_date=doc.posting_date, kind=doc.get('stock_entry_type') or doc.purpose,
                notes=doc.get('remarks'), currency=frappe.get_cached_value('Company', doc.company, 'default_currency'),
                issue_mode=doc.get('lotus_issue_mode'), receiver=doc.get('lotus_receiver'), work_plan=doc.get('lotus_work_plan'),
                can_submit=doc.docstatus == 0 and doc.has_permission('submit') and _simple_doc(doc),
                items=[dict(item=row.item_code, item_name=row.item_name, uom=row.get('stock_uom') or row.get('uom'),
                            qty=row.qty, source=row.get('s_warehouse'), target=row.get('t_warehouse') or row.get('warehouse'),
                            area=row.get('lotus_usage_area'), requirement=row.get('lotus_requirement'), material_request=row.get('material_request'),
                            rate=row.get('basic_rate') if doc.doctype == 'Stock Entry' else row.get('valuation_rate'))
                       for row in doc.items])


@frappe.whitelist(methods=['POST'])
def submit_document(doctype, name):
    doc = _stock_doc(doctype, name)
    doc.check_permission('submit')
    if not _simple_doc(doc):
        frappe.throw('Phiếu có nghiệp vụ nâng cao hoặc lô/serial chưa được hỗ trợ ghi sổ tại màn hình này.')
    if doc.docstatus != 0:
        frappe.throw('Chỉ ghi sổ được phiếu nháp.')
    doc.submit()
    return dict(name=doc.name, docstatus=doc.docstatus)


@frappe.whitelist()
def overview(company, warehouse=None, search=None, start=0):
    _access()
    company_doc = _company(company)
    warehouses = frappe.get_list('Warehouse', filters={'company': company, 'is_group': 0, 'disabled': 0},
                                fields=['name', 'warehouse_name'], limit_page_length=1000, order_by='name')
    if warehouse:
        _warehouse(warehouse, company)
    names = [warehouse] if warehouse else [w.name for w in warehouses]
    filters = {'disabled': 0, 'is_stock_item': 1}
    or_filters = None
    if search:
        or_filters = [[ 'item_code', 'like', '%' + str(search)[:100] + '%'],
                      [ 'item_name', 'like', '%' + str(search)[:100] + '%']]
    start = max(0, cint(start))
    items = frappe.get_list('Item', filters=filters, or_filters=or_filters,
                            fields=['name', 'item_name', 'item_group', 'stock_uom', 'has_batch_no', 'has_serial_no'],
                            order_by='item_name, name', limit_start=start, limit_page_length=51)
    visible_items = items[:50]
    bins = frappe.get_list('Bin', filters={'warehouse': ['in', names or ['__none__']],
                          'item_code': ['in', [i.name for i in visible_items] or ['__none__']]},
                          fields=['item_code', 'warehouse', 'actual_qty', 'stock_value', 'valuation_rate'],
                          limit_page_length=0)
    for item in visible_items:
        rows = [b for b in bins if b.item_code == item.name]
        item.actual_qty = sum(flt(b.actual_qty) for b in rows)
        item.stock_value = sum(flt(b.stock_value) for b in rows)
        item.valuation_rate = item.stock_value / item.actual_qty if item.actual_qty else 0
    entries = frappe.get_list('Stock Entry', filters={'company': company},
                              fields=['name', 'stock_entry_type', 'posting_date', 'docstatus'],
                              order_by='modified desc', limit_page_length=20)
    reconciliations = (frappe.get_list('Stock Reconciliation', filters={'company': company},
                       fields=['name', 'posting_date', 'docstatus'], order_by='modified desc', limit_page_length=10)
                       if frappe.has_permission('Stock Reconciliation', 'read') else [])
    return dict(warehouses=warehouses, items=visible_items, has_more=len(items) > 50,
                entries=entries, reconciliations=reconciliations, currency=company_doc.default_currency)


def _number(value, label, allow_zero=False):
    try:
        result = float(value)
    except (TypeError, ValueError):
        frappe.throw(label + ' phải là số.')
    if not math.isfinite(result) or result < 0 or (result == 0 and not allow_zero):
        frappe.throw(label + (' không được âm.' if allow_zero else ' phải lớn hơn 0.'))
    return result


@frappe.whitelist(methods=['POST'])
def create_draft(company, kind, posting_date, lines, source=None, target=None, notes=None, count_purpose='Stock Reconciliation', issue_mode='Manual', work_plan=None, receiver=None):
    _access()
    _company(company)
    types = {'receipt': 'Material Receipt', 'issue': 'Material Issue', 'transfer': 'Material Transfer'}
    if kind not in (*types, 'count'):
        frappe.throw('Loại phiếu không hợp lệ.')
    dt = 'Stock Reconciliation' if kind == 'count' else 'Stock Entry'
    if not frappe.has_permission(dt, 'create'):
        frappe.throw('Bạn chưa có quyền tạo ' + dt, frappe.PermissionError)
    if kind in ('issue', 'transfer'):
        _warehouse(source, company)
    if kind in ('receipt', 'transfer', 'count'):
        _warehouse(target, company)
    if kind == 'transfer' and source == target:
        frappe.throw('Kho xuất và kho nhận phải khác nhau.')
    rows = frappe.parse_json(lines)
    if not isinstance(rows, list) or not 1 <= len(rows) <= 100:
        frappe.throw('Phiếu cần từ 1 đến 100 dòng vật tư.')
    doc = frappe.new_doc(dt)
    doc.company = company
    doc.posting_date = getdate(posting_date)
    doc.set_posting_time = 1
    if kind == 'count':
        if count_purpose not in ('Opening Stock', 'Stock Reconciliation'):
            frappe.throw('Loại kiểm kê không hợp lệ.')
        from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import get_difference_account
        doc.purpose = count_purpose
        doc.expense_account = get_difference_account(count_purpose, company)
    else:
        doc.stock_entry_type = types[kind]
        doc.remarks = str(notes or '')[:2000]
        if kind == 'issue':
            if issue_mode not in ('Manual', 'Plan', 'Request'):
                frappe.throw('Hình thức xuất kho không hợp lệ.')
            doc.lotus_issue_mode = issue_mode
            doc.lotus_work_plan = work_plan if issue_mode == 'Plan' else None
            doc.lotus_receiver = _text(receiver, 'Người nhận')
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            frappe.throw('Dòng vật tư không hợp lệ.')
        item = frappe.get_doc('Item', row.get('item'))
        item.check_permission('read')
        if item.disabled or not item.is_stock_item:
            frappe.throw('Vật tư phải đang hoạt động và có quản lý tồn kho.')
        if item.has_batch_no or item.has_serial_no:
            frappe.throw('Form kho đơn giản hiện chưa hỗ trợ vật tư theo lô/serial.')
        key = (item.name, str(row.get('area') or '').strip(),
               row.get('requirement_line') if issue_mode == 'Plan' else row.get('material_request_item') if issue_mode == 'Request' else None) if kind == 'issue' else item.name
        if key in seen:
            frappe.throw('Gộp các dòng cùng vật tư và cùng khu vực sử dụng.')
        seen.add(key)
        qty = _number(row.get('qty'), 'Số lượng', allow_zero=kind == 'count')
        # No price input is required in the warehouse UI. Preserve an existing
        # valuation where available; explicit zero is supported by native ERPNext.
        existing_rate = frappe.db.get_value('Bin', {'item_code': item.name, 'warehouse': target or source}, 'valuation_rate') or item.get('valuation_rate') or 0
        rate = _number(row.get('rate', existing_rate), 'Định giá', allow_zero=True)
        values = dict(item_code=item.name, qty=qty, allow_zero_valuation_rate=1)
        if kind == 'count':
            values.update(warehouse=target, valuation_rate=rate)
        else:
            values.update(uom=item.stock_uom, stock_uom=item.stock_uom, conversion_factor=1)
            if kind in ('issue', 'transfer'):
                values['s_warehouse'] = source
            if kind in ('receipt', 'transfer'):
                values['t_warehouse'] = target
            if kind == 'receipt':
                values['basic_rate'] = rate
                values['set_basic_rate_manually'] = 1
            if kind == 'issue':
                values['lotus_usage_area'] = _text(row.get('area'), 'Khu vực / lô sử dụng')
                if issue_mode == 'Plan':
                    values['lotus_requirement'] = row.get('requirement')
                    values['lotus_requirement_line'] = row.get('requirement_line')
                elif issue_mode == 'Request':
                    values['material_request'] = row.get('material_request')
                    values['material_request_item'] = row.get('material_request_item')
        doc.append('items', values)
    doc.insert()
    return dict(name=doc.name, doctype=doc.doctype)
