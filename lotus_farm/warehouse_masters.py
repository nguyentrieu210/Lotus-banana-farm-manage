import json
import frappe


def install_fields():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    create_custom_fields({'Item':[
      dict(fieldname='lotus_minimum_stock',label='Legacy minimum by warehouse',fieldtype='Code',options='JSON',hidden=1,read_only=1),
      dict(fieldname='lotus_minimum_stock_global',label='Global minimum stock',fieldtype='Float',insert_after='stock_uom')
    ],
        'Warehouse': [
            dict(fieldname='lotus_address',label='Địa chỉ nhận hàng',fieldtype='Small Text'),
            dict(fieldname='lotus_contact_employee',label='Người phụ trách (HRMS)',fieldtype='Link',options='Employee',insert_after='lotus_address'),
            dict(fieldname='lotus_contact_name',label='Tên người phụ trách (HRMS)',fieldtype='Data',read_only=1),
            dict(fieldname='lotus_contact_phone',label='Điện thoại người phụ trách (HRMS)',fieldtype='Data',read_only=1),
            dict(fieldname='lotus_receiving_hours',label='Giờ nhận hàng',fieldtype='Data'),
            dict(fieldname='lotus_default_lead_days',label='Số ngày chờ hàng mặc định',fieldtype='Int'),
            dict(fieldname='lotus_delivery_note',label='Ghi chú giao hàng',fieldtype='Small Text'),
        ]},update=True)
    # Packaging unit is defined once globally; each Item owns its conversion factor.
    for name in ('Bao', 'Can'):
        if frappe.db.exists('UOM', name):
            continue
        frappe.get_doc(dict(doctype='UOM', uom_name=name, must_be_whole_number=1)).insert(ignore_permissions=True)


WAREHOUSE_DETAIL_FIELDS = {
    'lotus_address': 500,


    'lotus_receiving_hours': 140,
    'lotus_delivery_note': 500,
}



def warehouse_code(name, company):
    """Same naming scheme as ERPNext Warehouse.autoname."""
    from lotus_farm.warehouse import _text
    label = _text(name, 'Tên kho')
    abbr = frappe.get_cached_value('Company', company, 'abbr')
    if not abbr:
        frappe.throw('Chưa cấu hình mã viết tắt công ty.')
    suffix = ' - ' + abbr
    return label if label.endswith(suffix) else label + suffix


def employee_contact(company, employee, active_only=True):
    if not employee:
        return None
    info = frappe.db.get_value('Employee', employee,
        ['name', 'employee_name', 'cell_number', 'company', 'status'], as_dict=True)
    if not info or info.company != company or (active_only and info.status != 'Active'):
        frappe.throw('Người phụ trách phải là nhân viên HRMS đang làm việc trong công ty.')
    return info


@frappe.whitelist()
def employee_choices(company):
    from lotus_farm.warehouse import _access, _company
    _access()
    _company(company)
    # Only operational display names, never CCCD, salary or private addresses.
    rows = frappe.get_all('Employee', filters={'company': company, 'status': 'Active'},
        fields=['name', 'employee_name'], order_by='employee_name asc', limit_page_length=500)
    return [dict(value=r.name, label=r.employee_name) for r in rows]


def warehouse_contact(doc):
    employee = employee_contact(doc.company, doc.get('lotus_contact_employee'), active_only=False)
    return dict(
        lotus_contact_employee=employee.name if employee else '',
        lotus_contact_name=employee.employee_name if employee else doc.get('lotus_contact_name') or '',
        lotus_contact_phone=(employee.cell_number or '') if employee else doc.get('lotus_contact_phone') or '',
    )


def update_warehouse_details(doc, values):
    """Operational warehouse address and receiving defaults; not supplier accounting."""
    if not isinstance(values, dict):
        frappe.throw('Thông tin kho không hợp lệ.')
    if 'lotus_contact_employee' in values:
        info = employee_contact(doc.company, values.get('lotus_contact_employee'))
        if info:
            doc.lotus_contact_employee = info.name
            doc.lotus_contact_name = info.employee_name
            doc.lotus_contact_phone = info.cell_number or ''
        elif doc.get('lotus_contact_employee'):
            doc.lotus_contact_employee = None
            doc.lotus_contact_name = ''
            doc.lotus_contact_phone = ''
    for field, limit in WAREHOUSE_DETAIL_FIELDS.items():
        value = str(values.get(field) or '').strip()
        if len(value) > limit:
            frappe.throw('Thông tin kho quá dài: ' + field)
        doc.set(field, value)
    try:
        days = int(str(values.get('lotus_default_lead_days') or 0))
    except (TypeError, ValueError, OverflowError):
        frappe.throw('Số ngày chờ hàng phải là số nguyên không âm.')
    if days < 0 or days > 365:
        frappe.throw('Số ngày chờ hàng mặc định từ 0 đến 365.')
    doc.lotus_default_lead_days = days


def warehouse_details(doc):
    return {**{field:doc.get(field) or '' for field in WAREHOUSE_DETAIL_FIELDS},
            **warehouse_contact(doc),
            'lotus_default_lead_days':doc.get('lotus_default_lead_days') or 0}


def levels(item):
    try:
        value=frappe.parse_json(item.get('lotus_minimum_stock') or '{}')
        return value if isinstance(value,dict) else {}
    except (ValueError,TypeError):
        return {}


def set_minimum(item, company, values):
    """Global stock minimum is measured in the stock UOM, across all company warehouses."""
    from lotus_farm.warehouse import _number
    if 'minimum_stock' in values:
        item.lotus_minimum_stock_global = _number(
            values.get('minimum_stock', 0), 'Tồn tối thiểu toàn bộ kho', allow_zero=True)


def item_pack(item):
    """Secondary UOM is stored in ERPNext's native Item UOM conversion table."""
    for row in item.get('uoms') or []:
        if row.uom != item.stock_uom:
            return dict(pack_uom=row.uom, pack_factor=float(row.conversion_factor or 0))
    return dict(pack_uom='', pack_factor=0)


def configure_pack(item, values):
    if 'pack_uom' not in values and 'pack_factor' not in values:
        return
    from lotus_farm.warehouse import _number
    pack = str(values.get('pack_uom') or '').strip()
    if not pack:
        if values.get('pack_factor'):
            frappe.throw('Chọn đơn vị đóng gói trước khi nhập hệ số quy đổi.')
        if item.get('uoms') and any(r.uom != item.stock_uom for r in item.uoms):
            frappe.throw('Đã có đơn vị phụ; muốn xóa phải dùng thiết lập ERPNext.')
        return
    if pack == item.stock_uom:
        frappe.throw('Đơn vị đóng gói phải khác đơn vị tồn kho gốc.')
    uom = frappe.get_doc('UOM', pack)
    uom.check_permission('read')
    if not uom.enabled:
        frappe.throw('Đơn vị đóng gói đã ngừng sử dụng.')
    factor = _number(values.get('pack_factor'), 'Hệ số quy đổi')
    existing = next((r for r in item.get('uoms') or [] if r.uom == pack), None)
    if existing and abs(float(existing.conversion_factor or 0) - factor) < 1e-9:
        return
    if not item.is_new():
        old = item_pack(item)
        if old['pack_uom'] and (old['pack_uom'] != pack or abs(old['pack_factor'] - factor) > 1e-9):
            if frappe.db.exists('Stock Ledger Entry', {'item_code': item.name}):
                frappe.throw('Vật tư đã có nhập xuất: không được thay đổi quy đổi cũ.')
    if not item.is_new():
        old = item_pack(item)
        if old['pack_uom'] and old['pack_uom'] != pack:
            previous = next((r for r in item.uoms if r.uom == old['pack_uom']), None)
            if previous:
                item.remove(previous)
    if existing:
        existing.conversion_factor = factor
    else:
        item.append('uoms', dict(uom=pack, conversion_factor=factor))


def _doc(company,kind,name):
    from lotus_farm.warehouse import _access,_company
    _access();_company(company)
    types={'item':'Item','group':'Item Group','warehouse':'Warehouse'}
    if kind not in types:frappe.throw('Loại danh mục không hợp lệ.')
    doc=frappe.get_doc(types[kind],name);doc.check_permission('read')
    if kind=='warehouse' and (doc.company!=company or doc.is_group):frappe.throw('Chỉ sửa kho thuộc công ty đã chọn.')
    if kind=='group' and doc.is_group:frappe.throw('Nhóm cha được quản lý bằng cấu hình hệ thống.')
    return doc


@frappe.whitelist()
def read_master(company,kind,name):
    doc=_doc(company,kind,name)
    return dict(id=doc.name,modified=str(doc.modified),name=doc.get('item_name') or doc.get('warehouse_name') or doc.get('item_group_name'),code=doc.name,
                group=doc.get('item_group'),uom=doc.get('stock_uom'),description=doc.get('description'),
                parent=doc.get('parent_warehouse') or doc.get('parent_item_group'),
                **(warehouse_details(doc) if kind=='warehouse' else {}),
                **(dict(minimum_stock=doc.get('lotus_minimum_stock_global') or 0,**item_pack(doc)) if kind=='item' else {}),
                default_item_count=frappe.db.count('Item Default',{'default_warehouse':doc.name}) if kind=='warehouse' else 0,
                stock_default=frappe.db.get_single_value('Stock Settings','default_warehouse')==doc.name if kind=='warehouse' else False,
                ledger_count=frappe.db.count('Stock Ledger Entry',{'warehouse':doc.name}) if kind=='warehouse' else 0,
                can_write=doc.has_permission('write'),can_delete=doc.has_permission('delete'))


@frappe.whitelist()
def master_lists(company):
    from lotus_farm.warehouse import _access,_company
    _access();_company(company)
    return dict(groups=frappe.get_list('Item Group',filters={'is_group':0},fields=['name','parent_item_group'],limit_page_length=0),
                warehouses=[dict(row, **warehouse_contact(row)) for row in frappe.get_list('Warehouse',filters={'company':company,'is_group':0,'disabled':0},
                    fields=['name','company','warehouse_name','lotus_address','lotus_contact_employee','lotus_contact_name','lotus_contact_phone','lotus_default_lead_days'],limit_page_length=0)])


@frappe.whitelist(methods=['POST'])
def save_master(company,kind,name,modified,values):
    from lotus_farm.warehouse import _text
    doc=_doc(company,kind,name);doc.check_permission('write')
    if str(doc.modified)!=str(modified):frappe.throw('Danh mục đã thay đổi. Mở lại để lấy dữ liệu mới.')
    values=frappe.parse_json(values)
    if not isinstance(values,dict):frappe.throw('Thông tin không hợp lệ.')
    if kind=='item':
        group=frappe.get_doc('Item Group',values.get('group'));group.check_permission('read')
        uom=frappe.get_doc('UOM',values.get('uom'));uom.check_permission('read')
        if not uom.enabled:frappe.throw('Đơn vị tính đã bị tắt.')
        doc.item_name=_text(values.get('name'),'Tên vật tư');doc.item_group=group.name;doc.stock_uom=uom.name
        doc.description=str(values.get('description') or '')[:2000]
        set_minimum(doc,company,values)
        configure_pack(doc,values)
        doc.save()
    elif kind=='warehouse':
        label=_text(values.get('name'),'Tên kho')
        expected=warehouse_code(label,company)
        rename_needed=(label!=doc.warehouse_name and expected!=doc.name)
        if rename_needed and frappe.db.exists('Warehouse',expected):
            frappe.throw('Mã kho từ tên này đã tồn tại.')
        doc.warehouse_name=label
        update_warehouse_details(doc,values)
        doc.save()
        if rename_needed:
            frappe.rename_doc('Warehouse',doc.name,expected,merge=False,force=True)
            doc=frappe.get_doc('Warehouse',expected)
    else:
        new_name=_text(values.get('name'),'Tên nhóm')
        if new_name!=doc.name:
            new_name=frappe.rename_doc('Item Group',doc.name,new_name,merge=False)
            return dict(name=new_name)
    return dict(name=doc.name)


@frappe.whitelist(methods=['POST'])
def delete_master(company,kind,name,modified,clear_defaults=False):
    doc=_doc(company,kind,name);doc.check_permission('delete')
    if str(doc.modified)!=str(modified):frappe.throw('Danh mục đã thay đổi. Mở lại trước khi xóa.')
    if kind=='warehouse':
        if frappe.db.count('Stock Ledger Entry',{'warehouse':name}):
            frappe.throw('Kho đã có lịch sử nhập xuất nên không thể xóa. Có thể ngừng sử dụng kho để giữ lịch sử.')
        defaults=frappe.get_all('Item Default',filters={'default_warehouse':name},pluck='parent',limit_page_length=0)
        stock_default=frappe.db.get_single_value('Stock Settings','default_warehouse')==name
        if (defaults or stock_default) and not frappe.utils.cint(clear_defaults):
            frappe.throw('Kho đang là kho mặc định của '+str(len(set(defaults)))+' vật tư. Chọn gỡ kho mặc định trước khi xóa.')
        if stock_default:
            settings=frappe.get_single('Stock Settings');settings.check_permission('write')
            settings.default_warehouse=None;settings.save()
        if defaults:
            # All changes remain in the same transaction as native deletion. Any
            # remaining link blocker rolls back the default changes as well.
            for code in sorted(set(defaults)):
                item=frappe.get_doc('Item',code);item.check_permission('write')
                for row in item.item_defaults:
                    if row.default_warehouse==name:row.default_warehouse=None
                item.save()
    try:frappe.delete_doc(doc.doctype,doc.name)
    except frappe.LinkExistsError as exc:
        from frappe.utils import strip_html
        frappe.throw('Danh mục còn được sử dụng: '+strip_html(str(exc.__context__ or exc)),frappe.LinkExistsError)
    return dict(name=name,deleted=True)
