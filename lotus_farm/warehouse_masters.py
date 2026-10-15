import json
import frappe


def install_fields():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    create_custom_fields({'Item':[dict(fieldname='lotus_minimum_stock',label='Lotus minimum stock by warehouse',fieldtype='Code',options='JSON',hidden=1,read_only=1)]},update=True)


def levels(item):
    try:
        value=frappe.parse_json(item.get('lotus_minimum_stock') or '{}')
        return value if isinstance(value,dict) else {}
    except (ValueError,TypeError):
        return {}


def set_minimum(item,company,values):
    from lotus_farm.warehouse import _warehouse,_number
    if 'minimum_stock' not in values or not values.get('minimum_warehouse'):
        return
    warehouse=_warehouse(values['minimum_warehouse'],company)
    minimum=_number(values.get('minimum_stock',0),'Tồn tối thiểu',allow_zero=True)
    current=levels(item)
    if minimum:current[warehouse.name]=minimum
    else:current.pop(warehouse.name,None)
    item.lotus_minimum_stock=json.dumps(current)


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
    permitted_warehouses={row.name for row in frappe.get_list('Warehouse',filters={'company':company,'is_group':0},fields=['name'],limit_page_length=0)} if kind=='item' else set()
    return dict(id=doc.name,modified=str(doc.modified),name=doc.get('item_name') or doc.get('warehouse_name') or doc.get('item_group_name'),code=doc.name,
                group=doc.get('item_group'),uom=doc.get('stock_uom'),description=doc.get('description'),
                parent=doc.get('parent_warehouse') or doc.get('parent_item_group'),minimum_levels={key:value for key,value in levels(doc).items() if key in permitted_warehouses} if kind=='item' else {},
                default_item_count=frappe.db.count('Item Default',{'default_warehouse':doc.name}) if kind=='warehouse' else 0,
                stock_default=frappe.db.get_single_value('Stock Settings','default_warehouse')==doc.name if kind=='warehouse' else False,
                ledger_count=frappe.db.count('Stock Ledger Entry',{'warehouse':doc.name}) if kind=='warehouse' else 0,
                can_write=doc.has_permission('write'),can_delete=doc.has_permission('delete'))


@frappe.whitelist()
def master_lists(company):
    from lotus_farm.warehouse import _access,_company
    _access();_company(company)
    return dict(groups=frappe.get_list('Item Group',filters={'is_group':0},fields=['name','parent_item_group'],limit_page_length=0),
                warehouses=frappe.get_list('Warehouse',filters={'company':company,'is_group':0,'disabled':0},fields=['name','warehouse_name'],limit_page_length=0))


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
        set_minimum(doc,company,values);doc.save()
    elif kind=='warehouse':
        doc.warehouse_name=_text(values.get('name'),'Tên kho');doc.save()
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
