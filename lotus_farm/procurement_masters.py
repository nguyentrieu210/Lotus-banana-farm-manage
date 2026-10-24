"""Shared purchase masters. Supplier/Item remain ERPNext's canonical records."""
import frappe
from frappe.utils import cint, flt
from lotus_farm.procurement import access, parse
from lotus_farm.procurement_rules import digest
from lotus_farm.controls import lock

TYPES = {'suppliers': 'Supplier', 'items': 'Item'}


def text(value, size=140):
    return str(value or '').strip()[:size]


def page_args(start=0, page_length=50):
    return max(0, cint(start)), min(100, max(1, cint(page_length)))


def financial_access(company):
    from lotus_farm.finance import setup
    return company == setup.company() and (setup.can_view() or bool(set(frappe.get_roles()) & {'Lotus Purchase Approver', 'Lotus Farm Manager'}))


def choices(dt, fields=None, filters=None):
    if not frappe.has_permission(dt, 'read'):
        return []
    return frappe.get_list(dt, fields=fields or ['name'], filters=filters or {}, order_by='name', limit_page_length=0)


@frappe.whitelist()
def options(company):
    access(company)
    from lotus_farm.finance import setup
    return dict(supplier_groups=choices('Supplier Group', filters={'is_group': 0}),
                item_groups=choices('Item Group', filters={'is_group': 0}),
                uoms=choices('UOM', filters={'enabled': 1}), countries=choices('Country'),
                payment_terms=choices('Payment Terms Template'), asset_categories=choices('Asset Category'),
                banks=choices('Bank') if setup.can_post() else [], can_bank=setup.can_post(),
                can_create_supplier=frappe.has_permission('Supplier', 'create'),
                can_create_item=frappe.has_permission('Item', 'create'))


@frappe.whitelist()
def listing(company, kind, search=None, state='active', group=None, start=0, page_length=50):
    access(company)
    if kind not in TYPES:
        frappe.throw('Danh mục không hợp lệ.')
    dt = TYPES[kind]
    if not frappe.has_permission(dt, 'read'):
        frappe.throw('Không có quyền xem danh mục.', frappe.PermissionError)
    filters = {}
    if state in ('active', 'disabled'):
        filters['disabled'] = int(state == 'disabled')
    if group:
        filters['supplier_group' if kind == 'suppliers' else 'item_group'] = group
    fields = (['name', 'supplier_name', 'supplier_type', 'supplier_group', 'tax_id', 'lotus_supplier_phone',
               'lotus_supplier_contact', 'email_id', 'disabled'] if kind == 'suppliers' else
              ['name', 'item_name', 'item_group', 'stock_uom', 'is_stock_item', 'is_fixed_asset', 'disabled'])
    term = text(search)
    or_filters = [[dt, f, 'like', '%'+term+'%'] for f in fields if f not in ('disabled', 'is_stock_item', 'is_fixed_asset')] if term else None
    start, length = page_args(start, page_length)
    rows = frappe.get_list(dt, filters=filters, or_filters=or_filters, fields=fields,
                           order_by=('supplier_name' if kind == 'suppliers' else 'item_name')+' asc, name asc',
                           start=start, page_length=length+1)
    total = frappe.get_list(dt, filters=filters, or_filters=or_filters, fields=[{'COUNT':'name','as':'total'}])[0].total
    return dict(rows=rows[:length], total_count=total, has_more=len(rows)>length)


def get_master(kind, name, permission='read'):
    if kind not in TYPES:
        frappe.throw('Danh mục không hợp lệ.')
    doc = frappe.get_doc(TYPES[kind], name)
    doc.check_permission(permission)
    return doc


def linked(doc, field, dt):
    name = doc.get(field)
    if not name:
        return None
    d = frappe.get_doc(dt, name)
    d.check_permission('read')
    return d


@frappe.whitelist()
def detail(company, kind, name):
    access(company)
    d = get_master(kind, name)
    base = dict(name=d.name, modified=str(d.modified), can_write=d.has_permission('write'), disabled=d.disabled)
    if kind == 'items':
        return dict(base, item_code=d.item_code, item_name=d.item_name, group=d.item_group, uom=d.stock_uom,
                    description=d.description, is_stock_item=d.is_stock_item, is_fixed_asset=d.is_fixed_asset,
                    kind=d.get('lotus_default_purchase_kind') or ('Asset' if d.is_fixed_asset else 'Material' if d.is_stock_item else 'Service'),
                    asset_category=d.asset_category, conversions=[dict(uom=r.uom, conversion_factor=r.conversion_factor) for r in d.uoms])
    a = linked(d, 'supplier_primary_address', 'Address')
    c = linked(d, 'supplier_primary_contact', 'Contact')
    result = dict(base, supplier_id=d.name, supplier_name=d.supplier_name, type=d.supplier_type,
                  group=d.supplier_group, tax_id=d.tax_id or '', payment_terms=d.payment_terms or '',
                  contact=c.full_name if c else d.get('lotus_supplier_contact') or '',
                  phone=(c.mobile_no or c.phone) if c else d.get('lotus_supplier_phone') or '',
                  email=c.email_id if c else d.email_id or '', notes=d.get('lotus_supplier_note') or '',
                  address_line1=a.address_line1 if a else '', address_line2=a.address_line2 if a else '',
                  city=a.city if a else '', country=a.country if a else d.country or 'Vietnam',
                  address_modified=str(a.modified) if a else '', contact_modified=str(c.modified) if c else '')
    if financial_access(company) and frappe.has_permission('Bank Account', 'read'):
        b = linked(d, 'default_bank_account', 'Bank Account')
        if b:
            result.update(bank=b.bank, bank_account_no=b.bank_account_no, bank_account_name=b.account_name,
                          bank_modified=str(b.modified))
    return result


def version(doc, expected):
    lock(doc.doctype, doc.name)
    doc.reload()
    if not expected or str(doc.modified) != str(expected):
        frappe.throw('Dữ liệu đã thay đổi. Mở lại hồ sơ trước khi lưu.')


def set_link(doc, field, value, dt):
    if value:
        frappe.get_doc(dt, value).check_permission('read')
    doc.set(field, value or None)


def profile_link(supplier, field, dt, values, modified):
    d = linked(supplier, field, dt)
    if d:
        d.check_permission('write')
        version(d, modified)
    else:
        if not frappe.has_permission(dt, 'create'):
            frappe.throw('Không có quyền tạo '+dt, frappe.PermissionError)
        d = frappe.new_doc(dt)
        d.append('links', dict(link_doctype='Supplier', link_name=supplier.name))
    d.update(values)
    return d


def supplier_profile(d, v):
    for source, target in [('type', 'supplier_type'), ('tax_id', 'tax_id'), ('country', 'country')]:
        if source in v:
            d.set(target, text(v[source]))
    if 'group' in v:
        set_link(d, 'supplier_group', v['group'], 'Supplier Group')
    if 'payment_terms' in v:
        set_link(d, 'payment_terms', v['payment_terms'], 'Payment Terms Template')
    for source, target, size in [('phone', 'lotus_supplier_phone', 60), ('contact', 'lotus_supplier_contact', 140), ('notes', 'lotus_supplier_note', 500)]:
        if source in v:
            d.set(target, text(v[source], size))
    if any(k in v for k in ('contact', 'phone', 'email')) and (v.get('contact') or v.get('phone') or v.get('email') or d.supplier_primary_contact):
        c = profile_link(d, 'supplier_primary_contact', 'Contact', {}, v.get('contact_modified'))
        c.first_name=text(v.get('contact')) or d.supplier_name
        c.middle_name=''; c.last_name=''
        for table, key, value, flags in [('phone_nos', 'phone', text(v.get('phone'), 60), {'is_primary_phone': 1, 'is_primary_mobile_no': 1}),
                                        ('email_ids', 'email_id', text(v.get('email')), {'is_primary': 1})]:
            # Keep secondary contact methods; update only the primary slot.
            primary = next((r for r in c.get(table) if any(r.get(f) for f in flags)), None)
            if primary:
                primary.set(key, value)
                if not value:
                    c.remove(primary)
            elif value:
                c.append(table, {key: value, **flags})
        c.save(); d.supplier_primary_contact=c.name
    if 'address_line1' in v and (v.get('address_line1') or d.supplier_primary_address):
        if not text(v.get('address_line1')) or not text(v.get('city')):
            frappe.throw('Nhập địa chỉ và tỉnh/thành phố; không xóa địa chỉ chính đang dùng.')
        a = profile_link(d, 'supplier_primary_address', 'Address', dict(address_title=d.supplier_name, address_type='Billing',
            address_line1=text(v['address_line1']), address_line2=text(v.get('address_line2')),
            city=text(v.get('city')), country=text(v.get('country')) or 'Vietnam'), v.get('address_modified'))
        a.save(); d.supplier_primary_address=a.name
    if 'bank_account_no' in v:
        from lotus_farm.finance import setup
        if not setup.can_post():
            frappe.throw('Chỉ kế toán được cập nhật tài khoản NCC.', frappe.PermissionError)
        if v.get('bank_account_no'):
            b = linked(d, 'default_bank_account', 'Bank Account')
            if b:
                b.check_permission('write'); version(b, v.get('bank_modified'))
                if b.party_type != 'Supplier' or b.party != d.name or b.is_company_account:
                    frappe.throw('Tài khoản ngân hàng không thuộc NCC.')
            else:
                if not frappe.has_permission('Bank Account', 'create'):
                    frappe.throw('Không có quyền tạo tài khoản ngân hàng.', frappe.PermissionError)
                b=frappe.new_doc('Bank Account')
            frappe.get_doc('Bank', v.get('bank')).check_permission('read')
            b.update(dict(account_name=text(v.get('bank_account_name')) or d.supplier_name, bank=v.get('bank'),
                          bank_account_no=text(v['bank_account_no']), party_type='Supplier', party=d.name, is_company_account=0))
            b.save(); d.default_bank_account=b.name


@frappe.whitelist(methods=['POST'])
def save(company, kind, values, client_key, name=None, modified=None):
    access(company)
    if kind not in TYPES:
        frappe.throw('Danh mục không hợp lệ.')
    v = parse(values)
    if not isinstance(v, dict) or not client_key or len(str(client_key))>140:
        frappe.throw('Thông tin hoặc mã yêu cầu không hợp lệ.')
    lock('Company', company)
    dt = TYPES[kind]
    if name:
        d=get_master(kind, name, 'write'); version(d, modified)
    else:
        token=digest([frappe.session.user, dt, client_key]); fingerprint=digest(v)
        old=frappe.db.get_value(dt, {'lotus_procurement_key': token}, ['name', 'lotus_procurement_hash'], as_dict=True, for_update=True)
        if old:
            get_master(kind, old.name)
            if old.lotus_procurement_hash != fingerprint:
                frappe.throw('Mã yêu cầu đã dùng với nội dung khác.')
            return detail(company, kind, old.name)
        if not frappe.has_permission(dt, 'create'):
            frappe.throw('Không có quyền tạo '+dt, frappe.PermissionError)
        d=frappe.new_doc(dt)
        d.lotus_procurement_key=token; d.lotus_procurement_hash=fingerprint
    if kind == 'suppliers':
        if not name:
            title=text(v.get('supplier_name') or v.get('name'))
            if not title:
                frappe.throw('Nhập tên nhà cung cấp.')
            if frappe.db.exists('Supplier', {'supplier_name': title}):
                frappe.throw('Nhà cung cấp này đã tồn tại. Chọn hồ sơ hiện có.')
            d.supplier_name=title
            d.supplier_type=v.get('type') or 'Company'
            d.supplier_group=v.get('group')
            d.country=v.get('country') or 'Vietnam'
            d.insert()
        supplier_profile(d, v)
    else:
        if not name:
            code=text(v.get('item_code'))
            if not code:
                frappe.throw('Nhập mã hàng.')
            category=v.get('kind')
            if category not in ('Material', 'Tool', 'Asset', 'Service'):
                frappe.throw('Chọn loại mua.')
            d.item_code=code; d.is_stock_item=int(category in ('Material','Tool')); d.is_fixed_asset=int(category=='Asset')
            d.lotus_default_purchase_kind=category
            if d.is_fixed_asset: d.auto_create_assets=0
            d.stock_uom=v.get('uom')
            if d.is_fixed_asset:
                set_link(d, 'asset_category', v.get('asset_category'), 'Asset Category')
        elif v.get('uom') != d.stock_uom or v.get('kind') not in (('Asset',) if d.is_fixed_asset else ('Material','Tool') if d.is_stock_item else ('Service',)):
            frappe.throw('Không đổi loại hàng hoặc đơn vị gốc của mã đã tạo.')
        d.item_name=text(v.get('item_name'))
        if not d.item_name:
            frappe.throw('Nhập tên hàng.')
        set_link(d, 'item_group', v.get('group'), 'Item Group')
        d.description=str(v.get('description') or '').strip()
        conversions=v.get('conversions') or []
        if not isinstance(conversions, list) or any(flt(r.get('conversion_factor'))<=0 for r in conversions):
            frappe.throw('Hệ số quy đổi phải lớn hơn 0.')
        if name and frappe.db.exists('Stock Ledger Entry', {'item_code': d.name}):
            before={r.uom:flt(r.conversion_factor) for r in d.uoms}
            after={r['uom']:flt(r['conversion_factor']) for r in conversions}
            if before != after:
                frappe.throw('Không đổi quy đổi của hàng đã phát sinh sổ kho.')
        d.set('uoms', [])
        for r in conversions:
            frappe.get_doc('UOM', r.get('uom')).check_permission('read')
            d.append('uoms', dict(uom=r['uom'], conversion_factor=flt(r['conversion_factor'])))
    if 'disabled' in v:
        d.disabled=cint(v['disabled'])
    d.save()
    return detail(company, kind, d.name)
