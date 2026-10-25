"""Lotus-owned ERP workspace: native metadata, controllers, reports and workflows.

No Desk HTML/client scripts are embedded or executed. Every operation retains
native DocPerms, User Permissions, field permissions, validation and Lotus hooks.
"""
import hashlib
import json
import re
from copy import deepcopy
from functools import lru_cache

import frappe
from frappe.utils import add_days, add_months, cint, flt, getdate, nowdate
from lotus_farm.controls import lock
from lotus_farm.erpnext_workspace import can_access

SHARED_TYPES = {'Currency', 'Country', 'Address', 'Contact', 'Print Settings', 'System Settings', 'Letter Head', 'Print Heading', 'Email Account'}
BREAKS = {'Tab Break', 'Section Break', 'Column Break'}
FIELD_KEYS = ('fieldname', 'fieldtype', 'options', 'reqd', 'read_only', 'hidden', 'default', 'description', 'depends_on', 'mandatory_depends_on', 'read_only_depends_on', 'allow_on_submit', 'in_list_view', 'in_standard_filter', 'fetch_from', 'fetch_if_empty', 'precision', 'length', 'collapsible', 'non_negative')
MAPPERS = {
 ('Material Request', 'Purchase Order'): 'erpnext.stock.doctype.material_request.material_request.make_purchase_order',
 ('Material Request', 'Request for Quotation'): 'erpnext.stock.doctype.material_request.material_request.make_request_for_quotation',
 ('Supplier Quotation', 'Purchase Order'): 'erpnext.buying.doctype.supplier_quotation.supplier_quotation.make_purchase_order',
 ('Purchase Order', 'Purchase Receipt'): 'erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_receipt',
 ('Purchase Order', 'Purchase Invoice'): 'erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_invoice',
 ('Purchase Receipt', 'Purchase Invoice'): 'erpnext.stock.doctype.purchase_receipt.purchase_receipt.make_purchase_invoice',
 ('Quotation', 'Sales Order'): 'erpnext.selling.doctype.quotation.quotation.make_sales_order',
 ('Sales Order', 'Sales Invoice'): 'erpnext.selling.doctype.sales_order.sales_order.make_sales_invoice',
 ('Sales Order', 'Delivery Note'): 'erpnext.selling.doctype.sales_order.sales_order.make_delivery_note',
 ('Delivery Note', 'Sales Invoice'): 'erpnext.stock.doctype.delivery_note.delivery_note.make_sales_invoice',
}


def _access():
    frappe.local.lang = 'vi'
    if not can_access():
        frappe.throw('Bạn không có quyền sử dụng phân hệ này.', frappe.PermissionError)


def _meta(doctype, permission='read'):
    _access()
    if doctype == 'Bank Account':
        from lotus_farm.finance import setup
        (setup.require_view if permission in ('read', 'print', 'export') else setup.require_post)()
    meta = frappe.get_meta(doctype)
    app = frappe.get_cached_value('Module Def', meta.module, 'app_name')
    if meta.istable or (app not in ('erpnext', 'hrms') and doctype not in SHARED_TYPES):
        frappe.throw('Loại chứng từ không thuộc phân hệ ERP.', frappe.PermissionError)
    if not frappe.has_permission(doctype, permission):
        frappe.throw('Bạn chưa có quyền ' + {'read':'xem','write':'sửa','create':'tạo','submit':'ghi sổ','cancel':'hủy','amend':'sửa đổi','delete':'xóa','print':'in','export':'xuất dữ liệu'}.get(permission,permission) + ' ' + frappe._(doctype), frappe.PermissionError)
    return meta


def _company(company):
    if company:
        frappe.get_doc('Company', company).check_permission('read')


def _scope(doc, company):
    _company(company)
    if company and doc.meta.has_field('company') and doc.get('company') and doc.company != company:
        frappe.throw('Chứng từ không thuộc công ty đang chọn.', frappe.PermissionError)


def _permissions(doc):
    return {p: bool(doc.has_permission(p)) and (bool(doc.meta.is_submittable) if p in ('submit','cancel','amend') else True) for p in ('read', 'create', 'write', 'submit', 'cancel', 'amend', 'delete', 'print', 'export')}


def _fields(meta, parent=None):
    readable = set(meta.get_permitted_fieldnames(parenttype=parent, permission_type='read'))
    writable = set(meta.get_permitted_fieldnames(parenttype=parent, permission_type='write'))
    if not writable:
        writable = set(meta.get_permitted_fieldnames(parenttype=parent, permission_type='create'))
    if meta.name == 'Supplier':
        from lotus_farm.finance import setup
        bank_fields = {f.fieldname for f in meta.fields if 'bank' in f.fieldname}
        if not setup.can_view():
            readable -= bank_fields
        if not setup.can_post():
            writable -= bank_fields
    return [{**{k: f.get(k) for k in FIELD_KEYS}, 'label': frappe._(f.label or f.fieldname), 'can_create': bool(f.fieldtype == 'Link' and f.options in ('Supplier', 'Item') and frappe.has_permission(f.options, 'create')), 'read_only': 1 if f.fieldname not in writable else f.read_only}
            for f in meta.fields if (f.fieldtype in BREAKS or f.fieldname in readable or f.fieldname in writable) and f.fieldtype != 'Password']


@frappe.whitelist()
def schema(doctype):
    meta = _meta(doctype, 'read' if frappe.has_permission(doctype, 'read') else 'create')
    tables = {f.options: dict(doctype=f.options, fields=_fields(frappe.get_meta(f.options), doctype)) for f in meta.fields if f.fieldtype in ('Table', 'Table MultiSelect')}
    return dict(doctype=doctype, title=frappe._(doctype), title_field=meta.title_field, is_submittable=meta.is_submittable,
                issingle=meta.issingle, is_tree=meta.is_tree, autoname=meta.autoname, fields=_fields(meta), tables=tables,
                permissions={p: bool(frappe.has_permission(doctype, p)) for p in ('read', 'create', 'write', 'submit', 'cancel', 'amend', 'delete', 'print', 'export')})


def _loaded(doc):
    if doc.is_new() and doc.doctype == 'Purchase Order' and doc.meta.has_field('lotus_approval_status'):
        from lotus_farm.purchasing import DRAFT
        from lotus_farm.warehouse_buying_lite import MODES
        doc.lotus_approval_status = DRAFT
        doc.lotus_purchase_mode = doc.get('lotus_purchase_mode') or MODES[0]
    permissions = _permissions(doc)
    workflow = []
    if not doc.is_new():
        from frappe.model.workflow import get_transitions, get_workflow_name
        if get_workflow_name(doc.doctype):
            workflow = get_transitions(doc) or []
    actions = []
    if doc.docstatus == 1:
        actions = [dict(target=target, label=frappe._(target)) for (source, target) in MAPPERS if source == doc.doctype and frappe.has_permission(target, 'create')]
        if doc.doctype in ('Purchase Receipt', 'Purchase Invoice', 'Delivery Note', 'Sales Invoice') and not doc.get('is_return') and permissions['create']:
            actions.append(dict(target='Return', label='Trả hàng / điều chỉnh'))
        if doc.doctype in ('Purchase Order', 'Purchase Invoice', 'Sales Order', 'Sales Invoice') and frappe.has_permission('Payment Entry', 'create'):
            actions.append(dict(target='Payment Entry', label='Thanh toán / tạm ứng'))
    editable = None
    if not doc.is_new() and doc.doctype == 'Material Request' and doc.material_request_type == 'Purchase':
        from lotus_farm.purchase_proposal import detail
        editable = detail(doc.name)['edit']
        if not editable:
            permissions['write'] = False
    if not doc.is_new() and doc.doctype == 'Purchase Order' and doc.get('lotus_approval_status') == 'Chờ duyệt':
        permissions['write'] = False
    doc.apply_fieldlevel_read_permissions()
    if doc.doctype == 'Supplier':
        from lotus_farm.finance import setup
        if not setup.can_view():
            for field in doc.meta.fields:
                if 'bank' in field.fieldname:
                    doc.set(field.fieldname, None)
    return dict(doc=doc.as_dict(), permissions=permissions, transitions=workflow, actions=actions, is_new=doc.is_new(), editable=editable)


@frappe.whitelist()
def document(doctype, name=None, company=None, warehouse=None):
    meta = _meta(doctype, 'read' if name or frappe.has_permission(doctype, 'read') else 'create')
    if not name:
        _meta(doctype, 'create')
        doc = frappe.new_doc(doctype)
        _company(company)
        if company and meta.has_field('company'):
            doc.company = company
            if meta.has_field('currency'):
                doc.currency = frappe.get_cached_value('Company', company, 'default_currency')
            if meta.has_field('conversion_rate'):
                doc.conversion_rate = 1
        if warehouse:
            store = frappe.get_doc('Warehouse', warehouse); store.check_permission('read')
            if company and store.company != company:
                frappe.throw('Kho không thuộc công ty đang chọn.')
            for field in ('set_warehouse', 'warehouse'):
                if meta.has_field(field):
                    doc.set(field, warehouse)
    else:
        doc = frappe.get_doc(doctype, name); doc.check_permission('read'); _scope(doc, company)
        from frappe.desk.form.load import run_onload
        run_onload(doc)
    return _loaded(doc)


def _list_fields(meta):
    allowed = set(meta.get_permitted_fieldnames(permission_type='read'))
    selected = ['name']
    if meta.is_submittable:
        selected.append('docstatus')
    for field in [meta.title_field, *[f.fieldname for f in meta.fields if f.in_list_view], 'status', 'company', 'posting_date', 'transaction_date', 'modified']:
        if field and (field in allowed or field == 'modified') and field not in selected and len(selected) < 13:
            f = meta.get_field(field)
            if not f or f.fieldtype not in ('Table', 'Table MultiSelect', 'HTML', 'Password', 'Text Editor'):
                selected.append(field)
    return selected


@frappe.whitelist()
def listing(doctype, company=None, search=None, filters=None, start=0, length=50, sort='modified desc'):
    meta = _meta(doctype); _company(company)
    if meta.issingle:
        return dict(single=True, rows=[], columns=[], total_count=1)
    fields = _list_fields(meta)
    filters = frappe.parse_json(filters) if filters else {}
    if not isinstance(filters, dict):
        frappe.throw('Bộ lọc không hợp lệ.')
    permitted = set(meta.get_permitted_fieldnames(permission_type='read')) | {'name', 'docstatus', 'modified'}
    for field, condition in filters.items():
        if field not in permitted or (isinstance(condition, list) and (len(condition) != 2 or condition[0] not in ('=', '!=', '>', '<', '>=', '<=', 'like', 'in', 'not in', 'between', 'is'))):
            frappe.throw('Trường hoặc điều kiện lọc không hợp lệ.')
    if company and meta.has_field('company'):
        filters['company'] = company
    if not re.fullmatch(r'[a-zA-Z_][a-zA-Z_0-9]* (asc|desc)', sort) or sort.split()[0] not in permitted:
        frappe.throw('Thứ tự sắp xếp không hợp lệ.')
    search_fields = [f for f in dict.fromkeys(['name', meta.title_field, *meta.get_search_fields()]) if f and (f == 'name' or f in permitted)]
    or_filters = [[doctype, field, 'like', '%' + str(search)[:100] + '%'] for field in search_fields] if search else None
    start, length = max(0, cint(start)), min(100, max(1, cint(length)))
    rows = frappe.get_list(doctype, filters=filters, or_filters=or_filters, fields=fields, order_by=sort, start=start, page_length=length + 1)
    count = frappe.get_list(doctype, filters=filters, or_filters=or_filters, fields=[{'COUNT': '*'}], page_length=1)
    columns = [dict(fieldname=f, label=frappe._(meta.get_label(f) or f), fieldtype=meta.get_field(f).fieldtype if meta.get_field(f) else 'Data', options=meta.get_field(f).options if meta.get_field(f) else None) for f in fields]
    return dict(rows=rows[:length], columns=columns, total_count=next(iter(count[0].values())) if count else 0, has_more=len(rows) > length, start=start, length=length)


@frappe.whitelist()
def link_options(doctype, fieldname, search='', company=None, childtype=None, link_type=None):
    parent = _meta(doctype); _company(company)
    meta = frappe.get_meta(childtype) if childtype and any(f.options == childtype and f.fieldtype in ('Table', 'Table MultiSelect') for f in parent.fields) else parent
    field = meta.get_field(fieldname)
    if not field or field.fieldtype not in ('Link', 'Dynamic Link') or field.fieldname not in {f['fieldname'] for f in _fields(meta, doctype if meta.istable else None)}:
        frappe.throw('Trường liên kết không hợp lệ.', frappe.PermissionError)
    target = field.options if field.fieldtype == 'Link' else link_type
    if not target or not frappe.db.exists('DocType', target):
        return []
    if target == 'Bank Account':
        _meta(target)
    from frappe.desk.search import search_link
    filters = {'company': company} if company and frappe.get_meta(target).has_field('company') else {}
    if target == 'Warehouse':
        filters.update(disabled=0, is_group=0)
    if target == 'Account':
        filters.update(disabled=0, is_group=0)
    if fieldname.startswith('parent_') and target == meta.name and frappe.get_meta(target).has_field('is_group'):
        filters['is_group'] = 1
    rows = search_link(doctype=target, txt=str(search)[:100], filters=filters, page_length=50, reference_doctype=doctype)
    return [dict(value=r['value'], label=r.get('label') or r['value'], description=r.get('description')) for r in rows]


@frappe.whitelist()
def tree(doctype, company=None):
    meta = _meta(doctype); _company(company)
    if not meta.is_tree:
        frappe.throw('Danh mục không có cấu trúc cây.')
    allowed = set(meta.get_permitted_fieldnames(permission_type='read'))
    parent_field = meta.get('nsm_parent_field') or next((f.fieldname for f in meta.fields if f.fieldtype == 'Link' and f.options == doctype and (f.fieldname.startswith('parent_') or f.fieldname == 'reports_to')), None)
    if not parent_field or parent_field not in allowed:
        frappe.throw('Bạn không có quyền xem cấu trúc cây.', frappe.PermissionError)
    fields = list(dict.fromkeys(['name', parent_field, *[f for f in (meta.title_field, 'is_group') if f and f in allowed]]))
    records = frappe.get_list(doctype, filters={'company':company} if company and meta.has_field('company') else {}, fields=fields, order_by='lft asc' if meta.has_field('lft') else 'name asc', limit_page_length=0)
    names = {r.name for r in records}
    return dict(parent_field=parent_field, title_field=meta.title_field, rows=[dict(**r, _erp_parent=r.get(parent_field) if r.get(parent_field) in names else '') for r in records])


def _command(client_key, payload, operation):
    token = str(client_key or '')
    if not token or len(token) > 140:
        frappe.throw('Thiếu mã yêu cầu lưu chứng từ.')
    identity = hashlib.sha256((frappe.session.user + ':' + token).encode()).hexdigest()
    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
    existing = frappe.db.get_value('Lotus ERP Command', identity, ['payload_hash', 'result_json'], as_dict=True, for_update=True)
    if existing:
        if existing.payload_hash != fingerprint:
            frappe.throw('Mã yêu cầu đã dùng cho nội dung khác. Mở lại chứng từ trước khi gửi tiếp.')
        return json.loads(existing.result_json)
    frappe.db.savepoint('erp_claim')
    claim = frappe.get_doc(dict(doctype='Lotus ERP Command', request_key=identity, payload_hash=fingerprint, reference_doctype=payload['doctype'], action=payload['action']))
    claim.flags.erp_command = True
    try:
        claim.insert(ignore_permissions=True)
    except frappe.DuplicateEntryError:
        frappe.db.rollback(save_point='erp_claim')
        existing = frappe.db.get_value('Lotus ERP Command', identity, ['payload_hash', 'result_json'], as_dict=True, for_update=True)
        if not existing or existing.payload_hash != fingerprint or not existing.result_json:
            frappe.throw('Yêu cầu đang được xử lý hoặc nội dung đã thay đổi. Kiểm tra lại chứng từ.')
        return json.loads(existing.result_json)
    doc = operation()
    result = dict(doctype=doc.doctype, name=doc.name)
    claim.reference_name = doc.name; claim.result_json = json.dumps(result); claim.save(ignore_permissions=True)
    return result


@frappe.whitelist(methods=['POST'])
def action(doctype, action, client_key, values=None, name=None, modified=None, company=None, transition=None):
    meta = _meta(doctype, 'read' if name else 'create'); _company(company)
    if action in ('submit','cancel') and not meta.is_submittable:
        frappe.throw('Danh mục này không có bước ghi sổ hoặc hủy ghi sổ.')
    if action not in ('save', 'submit', 'cancel', 'workflow'):
        frappe.throw('Thao tác không được hỗ trợ.')
    values = frappe.parse_json(values) if values else {}
    if not isinstance(values, dict) or values.get('doctype', doctype) != doctype:
        frappe.throw('Nội dung chứng từ không hợp lệ.')
    payload = dict(doctype=doctype, action=action, name=name, modified=modified, values=values, company=company, transition=transition)

    def apply():
        if name:
            lock(doctype, name)
            doc = frappe.get_doc(doctype, name); doc.check_permission('read'); _scope(doc, company)
            if not modified or str(doc.modified) != str(modified):
                frappe.throw('Chứng từ đã thay đổi. Tải lại trước khi lưu.', frappe.TimestampMismatchError)
            doc.check_permission('cancel' if action == 'cancel' else 'write')
        else:
            _meta(doctype, 'create'); doc = frappe.new_doc(doctype)
        from lotus_farm import signing, signing_rules
        if name and action == 'save' and doc.doctype == 'Purchase Order' and doc.get('lotus_approval_status') == 'Chờ duyệt':
            frappe.throw('Đơn đang chờ duyệt. Trả lại trước khi sửa.')
        if name and action == 'save' and doc.doctype == 'Material Request' and doc.material_request_type == 'Purchase':
            from lotus_farm.purchase_proposal import detail, EDIT_PRICES
            edit = detail(name)['edit']
            if not edit:
                frappe.throw('Phiếu đang chờ ký, không sửa được ở bước này.', frappe.PermissionError)
            if edit == 'prices':
                permitted_prices = set(EDIT_PRICES)
                for field, value in values.items():
                    if field in {'doctype','name','modified','creation','owner','modified_by','docstatus','__islocal'}:
                        continue
                    if field != 'items' and doc.meta.has_field(field) and value != doc.get(field):
                        frappe.throw('Ở bước này chỉ sửa giá và ghi chú từng dòng.', frappe.PermissionError)
                original = {r.name:r for r in doc.items}
                if len(values.get('items', [])) != len(original):
                    frappe.throw('Không được thêm hoặc xóa dòng ở bước này.', frappe.PermissionError)
                for row in values.get('items', []):
                    source = original.get(row.get('name'))
                    if not source or any(f not in permitted_prices and source.meta.has_field(f) and value != source.get(f) for f,value in row.items()):
                        frappe.throw('Chỉ sửa đơn giá, nhà cung cấp gợi ý và ghi chú.', frappe.PermissionError)
        if action in ('save', 'submit'):
            if doctype == 'Supplier':
                from lotus_farm.finance import setup
                title = str(values.get('supplier_name') or '').strip()
                if not name and title and frappe.db.exists('Supplier', {'supplier_name':title}):
                    frappe.throw('Nhà cung cấp này đã tồn tại. Chọn hồ sơ hiện có.')
                if not setup.can_post() and any('bank' in f.fieldname and f.fieldname in values and values[f.fieldname] != doc.get(f.fieldname) for f in doc.meta.fields):
                    frappe.throw('Chỉ kế toán được sửa thông tin ngân hàng.', frappe.PermissionError)
            allowed = {f.fieldname for f in doc.meta.fields} | {'amended_from'}
            protected = {f.fieldname for f in doc.meta.fields if f.fieldname.startswith('lotus_') and (f.read_only or f.hidden)}
            doc.update({k: v for k, v in values.items() if k in allowed and k not in protected})
            if not name:
                doc.owner = frappe.session.user
                if doctype == 'Purchase Order' and doc.meta.has_field('lotus_approval_status'):
                    from lotus_farm.purchasing import DRAFT
                    from lotus_farm.warehouse_buying_lite import MODES
                    doc.lotus_approval_status = DRAFT
                    doc.lotus_purchase_mode = doc.get('lotus_purchase_mode') or MODES[0]
            from frappe.desk.form.save import set_local_name
            set_local_name(doc)
            _scope(doc, company)
            chain = signing.chain_for(doc)
            if action == 'submit' and chain and signing_rules.chain(chain)['gate']:
                frappe.throw('Chứng từ phải hoàn tất chuỗi ký trước khi duyệt.', frappe.PermissionError)
            if action == 'submit':
                doc.check_permission('submit'); doc.submit()
            else:
                doc.save()
        elif action == 'cancel':
            doc.cancel()
        else:
            chain = signing.chain_for(doc)
            if chain and signing_rules.chain(chain)['gate']:
                frappe.throw('Thực hiện duyệt qua chuỗi ký của chứng từ.', frappe.PermissionError)
            from frappe.model.workflow import apply_workflow, get_transitions, get_workflow_name
            if not get_workflow_name(doctype) or transition not in {r.action for r in (get_transitions(doc) or [])}:
                frappe.throw('Bạn không được thực hiện bước duyệt này.', frappe.PermissionError)
            doc = apply_workflow(doc.as_dict(), transition)
        return doc

    identity = _command(client_key, payload, apply)
    return document(identity['doctype'], identity['name'], company=company)


@frappe.whitelist(methods=['POST'])
def amend(doctype, name, modified, company=None):
    _meta(doctype); source = frappe.get_doc(doctype, name); source.check_permission('amend'); _scope(source, company)
    if source.docstatus != 2 or str(source.modified) != str(modified):
        frappe.throw('Chỉ sửa đổi chứng từ đã hủy và đúng phiên bản.')
    doc = frappe.copy_doc(source); doc.amended_from = source.name; doc.docstatus = 0
    return _loaded(doc)


@frappe.whitelist(methods=['POST'])
def map_document(doctype, name, target, company=None):
    _meta(doctype); source = frappe.get_doc(doctype, name); source.check_permission('read'); _scope(source, company)
    if source.docstatus != 1:
        frappe.throw('Chỉ tạo chứng từ tiếp theo từ chứng từ đã duyệt.')
    if target == 'Return' and doctype in ('Purchase Receipt', 'Purchase Invoice', 'Delivery Note', 'Sales Invoice'):
        _meta(doctype, 'create')
        from erpnext.controllers.sales_and_purchase_return import make_return_doc
        doc = make_return_doc(doctype, name)
    elif target == 'Payment Entry' and doctype in ('Purchase Order', 'Purchase Invoice', 'Sales Order', 'Sales Invoice'):
        _meta(target, 'create')
        from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
        doc = get_payment_entry(doctype, name)
    else:
        method = MAPPERS.get((doctype, target))
        if not method:
            frappe.throw('Liên kết chứng từ không được hỗ trợ.')
        _meta(target, 'create'); doc = frappe.get_attr(method)(source_name=name)
    return _loaded(doc)


@frappe.whitelist(methods=['POST'])
def item_details(doctype, item_code, company, row=None, header=None):
    _meta(doctype, 'read' if frappe.has_permission(doctype, 'read') else 'create'); _company(company)
    item = frappe.get_doc('Item', item_code); item.check_permission('read')
    if doctype not in ('Purchase Order', 'Purchase Receipt', 'Purchase Invoice', 'Supplier Quotation', 'Sales Order', 'Delivery Note', 'Sales Invoice', 'Quotation', 'Material Request', 'Stock Entry','Stock Reconciliation'):
        frappe.throw('Loại chứng từ không hỗ trợ lấy chi tiết hàng.')
    row, header = frappe.parse_json(row) or {}, frappe.parse_json(header) or {}
    args = {k: v for k, v in {**header, **row}.items() if k in ('supplier', 'customer', 'currency', 'conversion_rate', 'price_list', 'buying_price_list', 'selling_price_list', 'price_list_currency', 'plc_conversion_rate', 'warehouse', 'uom', 'qty', 'transaction_date', 'posting_date', 'is_return', 'ignore_pricing_rule', 'schedule_date')}
    args.update(doctype=doctype, company=company, item_code=item_code, conversion_rate=args.get('conversion_rate') or 1)
    if doctype == 'Stock Entry':
        args['warehouse'] = row.get('s_warehouse') or row.get('t_warehouse') or header.get('from_warehouse') or header.get('to_warehouse')
    if args.get('warehouse'):
        store = frappe.get_doc('Warehouse', args['warehouse']); store.check_permission('read')
        if store.company != company:
            frappe.throw('Kho không thuộc công ty đang chọn.', frappe.PermissionError)
    if doctype == 'Stock Entry':
        doc = frappe.new_doc(doctype)
        doc.company=company; doc.purpose=header.get('purpose'); doc.posting_date=header.get('posting_date') or nowdate(); doc.posting_time=header.get('posting_time')
        return doc.get_item_details(frappe._dict(args), for_update=True)
    if doctype == 'Stock Reconciliation':
        from erpnext.stock.utils import get_stock_balance
        qty, rate = get_stock_balance(item_code, args['warehouse'], header.get('posting_date') or nowdate(), header.get('posting_time'), with_valuation_rate=True) if args.get('warehouse') else (0,0)
        return dict(item_name=item.item_name, stock_uom=item.stock_uom, qty=qty, valuation_rate=rate, current_qty=qty, current_valuation_rate=rate)
    from erpnext.stock.get_item_details import get_item_details
    result = get_item_details(args)
    if item.meta.has_field('lotus_default_purchase_kind'):
        result['lotus_purchase_kind'] = item.get('lotus_default_purchase_kind') or ('Asset' if item.is_fixed_asset else 'Material' if item.is_stock_item else 'Service')
    return result


@frappe.whitelist()
def linked_values(doctype, fieldname, value, childtype=None):
    parent = _meta(doctype)
    meta = frappe.get_meta(childtype) if childtype and any(f.options == childtype and f.fieldtype in ('Table', 'Table MultiSelect') for f in parent.fields) else parent
    field = meta.get_field(fieldname)
    if not field or field.fieldtype != 'Link':
        return {}
    target = frappe.get_doc(field.options, value); target.check_permission('read'); target.apply_fieldlevel_read_permissions()
    allowed = set(meta.get_permitted_fieldnames(parenttype=doctype if meta.istable else None, permission_type='read'))
    values = {f.fieldname: target.get(f.fetch_from.split('.', 1)[1]) for f in meta.fields if f.fieldname in allowed and f.fetch_from and f.fetch_from.startswith(fieldname + '.') and '.' in f.fetch_from}
    if doctype == 'Stock Entry' and fieldname == 'stock_entry_type':
        values['purpose'] = target.purpose
    return values


@frappe.whitelist()
def party_details(doctype, party_type, party, company, posting_date=None, currency=None):
    meta = _meta(doctype); _company(company)
    if party_type not in ('Supplier', 'Customer') or not meta.has_field(party_type.lower()):
        frappe.throw('Đối tượng không phù hợp với chứng từ.')
    frappe.get_doc(party_type, party).check_permission('read')
    from erpnext.accounts.party import get_party_details
    return get_party_details(party=party, party_type=party_type, company=company, posting_date=posting_date, currency=currency, doctype=doctype)


@frappe.whitelist(methods=['POST'])
def preview(doctype, values, company):
    _meta(doctype); _company(company)
    if doctype not in ('Purchase Order', 'Purchase Receipt', 'Purchase Invoice', 'Supplier Quotation', 'Sales Order', 'Delivery Note', 'Sales Invoice', 'Quotation'):
        frappe.throw('Chứng từ không có bộ tính thuế và tổng tiền này.')
    values = frappe.parse_json(values)
    if not isinstance(values, dict) or values.get('doctype') != doctype:
        frappe.throw('Nội dung không hợp lệ.')
    values.pop('flags', None)
    doc = frappe.get_doc(values); _scope(doc, company)
    if doc.get('name') and not doc.is_new():
        frappe.get_doc(doctype, doc.name).check_permission('read')
    else:
        _meta(doctype, 'create')
    if doc.get('taxes_and_charges') and not doc.get('taxes'):
        field = doc.meta.get_field('taxes_and_charges')
        template = frappe.get_doc(field.options, doc.taxes_and_charges); template.check_permission('read')
        if template.get('company') and template.company != company:
            frappe.throw('Mẫu thuế không thuộc công ty đang chọn.')
        for row in template.taxes:
            values = row.as_dict(); values.pop('name', None); values.pop('parent', None); values.pop('parenttype', None); values.pop('parentfield', None)
            doc.append('taxes', values)
    doc.run_method('calculate_taxes_and_totals')
    doc.apply_fieldlevel_read_permissions()
    return doc.as_dict()


@frappe.whitelist()
def approval(doctype, name):
    _meta(doctype); doc = frappe.get_doc(doctype, name); doc.check_permission('read')
    from lotus_farm import signing, signing_rules
    key = signing.chain_for(doc)
    if not key:
        return None
    status = signing.status(doc, key, with_images=True)
    result = dict(chain=key, gate=signing_rules.chain(key)['gate'], status=status)
    if doctype == 'Purchase Order':
        from lotus_farm import purchasing
        result['order'] = purchasing.detail(name)
    elif key == 'purchase_proposal':
        from lotus_farm.purchase_proposal import detail
        result['proposal'] = detail(name)
        result['can_start'] = result['proposal']['needs_signers'] and result['proposal']['can_sign']
    elif key == 'payment_voucher':
        from lotus_farm.finance import setup
        result['can_start'] = doc.docstatus == 0 and setup.can_post() and (not status['round'] or status['returned']) and doc.has_permission('write')
    return result


@frappe.whitelist(methods=['POST'])
def approval_action(doctype, name, modified, operation, client_key, values=None):
    _meta(doctype); doc = frappe.get_doc(doctype, name); doc.check_permission('read')
    values = frappe.parse_json(values) or {}
    if not isinstance(values, dict):
        frappe.throw('Nội dung ký không hợp lệ.')

    def apply():
        lock(doctype, name); current = frappe.get_doc(doctype, name)
        if str(current.modified) != str(modified):
            frappe.throw('Chứng từ đã thay đổi. Tải lại trước khi ký.', frappe.TimestampMismatchError)
        from lotus_farm import signing
        if doctype == 'Purchase Order':
            from lotus_farm import purchasing
            methods = {'request_approval': ('approver',), 'approve_order': ('sign_token',), 'reject_order': ('reason',), 'mark_order_sent': (), 'confirm_supplier_order': (), 'reschedule_order': ('expected_date', 'reason'), 'close_order': ('reason',), 'cancel_order': ('reason',)}
            if operation not in methods:
                frappe.throw('Thao tác đơn mua không hợp lệ.')
            getattr(purchasing, operation)(name=name, modified=modified, **{k: values.get(k) for k in methods[operation]})
        elif signing.chain_for(current) == 'purchase_proposal':
            from lotus_farm import purchase_proposal
            if operation == 'sign':
                purchase_proposal.sign(name, modified, values.get('signers'))
            elif operation == 'return':
                purchase_proposal.return_proposal(name, modified, values.get('reason'))
            else:
                frappe.throw('Thao tác đề xuất mua không hợp lệ.')
        elif signing.chain_for(current) == 'payment_voucher':
            from lotus_farm.finance import setup, payments
            if operation == 'start_signing':
                setup.require_post(); current.check_permission('write'); payments.start_signing(current, values.get('signers') or {})
            elif operation == 'sign':
                payments.sign_payment(doctype, name)
            elif operation == 'return':
                signing.send_back(current, values.get('reason'))
            else:
                frappe.throw('Thao tác ký không hợp lệ.')
        else:
            frappe.throw('Quy trình ký không hợp lệ.')
        return frappe.get_doc(doctype, name)

    identity = _command(client_key, dict(doctype=doctype, action=operation, name=name, modified=modified, values=values), apply)
    return document(doctype, identity['name'])


@lru_cache(maxsize=1)
def _report_metadata():
    from pathlib import Path
    return json.loads(Path(frappe.get_app_path('lotus_farm', 'erp_report_metadata.json')).read_text(encoding='utf-8'))['reports']


def _report(name):
    _access()
    from frappe.desk.query_report import get_report_doc
    doc = get_report_doc(name)
    _meta(doc.ref_doctype)
    return doc


def _fiscal(company):
    from erpnext.accounts.utils import get_fiscal_year
    year = get_fiscal_year(nowdate(), company=company, raise_on_missing=False)
    return dict(name=year[0], start=str(year[1]), end=str(year[2])) if year else dict(name=str(getdate().year), start=str(getdate().replace(month=1, day=1)), end=str(getdate().replace(month=12, day=31)))


def _expression(value, company, fiscal, options=False):
    if isinstance(value, list):
        return [_expression(v, company, fiscal, options) for v in value]
    if isinstance(value, dict) and '$expr' not in value:
        return {k:_expression(v, company, fiscal, options) for k,v in value.items()}
    if not isinstance(value, dict) or '$expr' not in value:
        return value
    expr = value['$expr']
    if 'get_presentation_currency_list' in expr:
        return frappe.get_all('Currency', filters={'enabled': 1}, pluck='name', order_by='name', limit_page_length=0)
    if options and 'party_type' in expr:
        return ['Customer', 'Supplier', 'Employee', 'Shareholder']
    if 'get_fiscal_year' in expr:
        return fiscal['start' if '[1]' in expr else 'end' if '[2]' in expr else 'name']
    if 'year_start_date' in expr:
        return fiscal['start']
    if 'year_end_date' in expr:
        return fiscal['end']
    if re.search(r'get_(?:user_|global_)?default\([\'"](?:company|Company)[\'"]', expr):
        return company
    if re.search(r'get_(?:user_|global_)?default\([\'"](?:currency|Currency)[\'"]', expr):
        return frappe.get_cached_value('Company', company, 'default_currency') if company else None
    if 'month_start' in expr:
        return str(getdate().replace(day=1))
    if 'month_end' in expr:
        return str(add_days(add_months(getdate().replace(day=1), 1), -1))
    date = re.search(r'add_(days|months)\(.+,\s*(-?\d+)\s*\)', expr)
    if date:
        return str((add_days if date[1] == 'days' else add_months)(nowdate(), int(date[2])))
    if re.search(r'(get_today|nowdate|now_date)\(', expr):
        return nowdate()
    return None


@frappe.whitelist()
def report_definition(name, company=None):
    report = _report(name); _company(company)
    fiscal = _fiscal(company)
    metadata = deepcopy(_report_metadata().get(report.name, {}))
    fields = metadata.get('filters') or [dict(fieldname=f.fieldname, label=f.label, fieldtype=f.fieldtype, options=f.options, reqd=f.mandatory, default=f.default) for f in (report.get('filters') or [])]
    defaults = {}
    for field in fields:
        field['label'] = frappe._(field.get('label') or field['fieldname'])
        for key in ('default', 'options'):
            field[key] = _expression(field.get(key), company, fiscal, options=key == 'options')
        if isinstance(field.get('default'), list) and field.get('fieldtype') not in ('MultiSelectList', 'DateRange'):
            field['default'] = field['default'][0] if field['default'] else ''
        if field.get('default') is not None:
            defaults[field['fieldname']] = field['default']
        if field.get('fieldtype') in ('MultiSelectList', 'MultiSelect'):
            defaults.setdefault(field['fieldname'], [])
    by_name = {f['fieldname']: f for f in fields}
    if 'party_type' in by_name and not by_name['party_type'].get('options'):
        by_name['party_type']['options'] = ['Customer','Supplier','Employee','Shareholder']
    if 'party_type' in by_name and ('Payable' in name or 'Receivable' in name):
        defaults.setdefault('party_type', 'Supplier' if 'Payable' in name else 'Customer')
    if 'party' in by_name and by_name['party'].get('fieldtype') == 'MultiSelectList' and (not by_name['party'].get('options') or by_name['party'].get('options') == 'party_type'):
        if 'Payable' in name:
            by_name['party']['options'] = 'Supplier'
        elif 'Receivable' in name:
            by_name['party']['options'] = 'Customer'
        elif 'party_type' in by_name:
            by_name['party']['dynamic_options'] = 'party_type'
    if company and 'company' in by_name:
        defaults['company'] = company
    for field in ('from_fiscal_year', 'to_fiscal_year', 'fiscal_year'):
        if field in by_name:
            defaults.setdefault(field, fiscal['name'])
    for field in ('period_start_date', 'year_start_date'):
        if field in by_name:
            defaults.setdefault(field, fiscal['start'])
    for field in ('period_end_date', 'year_end_date'):
        if field in by_name:
            defaults.setdefault(field, fiscal['end'])
    if 'presentation_currency' in by_name and company:
        defaults['presentation_currency'] = frappe.get_cached_value('Company', company, 'default_currency')
    # The native on_change functions toggle these fields. Express that state
    # declaratively so the independent form never evaluates report JavaScript.
    if 'filter_based_on' in by_name:
        for field in fields:
            if field['fieldname'] in ('period_start_date', 'period_end_date', 'from_fiscal_year', 'to_fiscal_year'):
                field['hidden'] = 0
                value = 'Date Range' if field['fieldname'].startswith('period_') else 'Fiscal Year'
                field['depends_on'] = "eval:doc.filter_based_on == '" + value + "'"
                field['mandatory_depends_on'] = field['depends_on']
    return dict(name=name, title=frappe._(name), ref_doctype=report.ref_doctype, report_type=report.report_type, filters=fields,
                defaults=defaults, fiscal=fiscal, tree=metadata.get('tree'), prepared_report=report.prepared_report,
                can_export=bool(frappe.has_permission(report.ref_doctype, 'export')))


@frappe.whitelist()
def report_link_options(name, fieldname, search='', company=None, link_type=None):
    definition = report_definition(name, company)
    field = next((f for f in definition['filters'] if f['fieldname'] == fieldname), None)
    if not field or field.get('fieldtype') not in ('Link', 'Dynamic Link', 'MultiSelectList'):
        frappe.throw('Trường liên kết báo cáo không hợp lệ.')
    target = field.get('options') if field['fieldtype'] != 'Dynamic Link' else link_type
    if field.get('dynamic_options') == 'party_type':
        target = link_type if link_type in ('Customer','Supplier','Employee','Shareholder') else None
    if not target or not isinstance(target, str) or not frappe.db.exists('DocType', target):
        return []
    from frappe.desk.search import search_link
    filters = {'company': company} if company and frappe.get_meta(target).has_field('company') else {}
    rows = search_link(doctype=target, txt=str(search)[:100], filters=filters, page_length=50, reference_doctype=definition['ref_doctype'])
    return [dict(value=r['value'], label=r.get('label') or r['value']) for r in rows]


@frappe.whitelist()
def run_report(name, filters=None, company=None):
    report = _report(name); _company(company)
    values = frappe.parse_json(filters) if filters else {}
    if not isinstance(values, dict):
        frappe.throw('Bộ lọc báo cáo không hợp lệ.')
    if company and values.get('company') and values['company'] != company:
        frappe.throw('Báo cáo không thuộc công ty đang chọn.', frappe.PermissionError)
    if company:
        values.setdefault('company', company)
    selected = values.get('company')
    for scoped_company in selected if isinstance(selected, list) else [selected]:
        _company(scoped_company)
    if frappe.get_meta(report.ref_doctype).has_field('company') and not selected:
        frappe.throw('Chọn công ty trước khi chạy báo cáo.')
    definition = report_definition(name, company)
    if report.report_type == 'Report Builder':
        config = json.loads(report.json or '{}')
        meta = _meta(report.ref_doctype)
        allowed = set(meta.get_permitted_fieldnames(permission_type='read')) | {'name', 'docstatus', 'modified'}
        selected = [r[0] if isinstance(r, list) else r for r in config.get('fields', [])]
        selected = [r for r in selected if r in allowed] or _list_fields(meta)
        native_filters = config.get('filters') or []
        if company and meta.has_field('company'):
            native_filters = [*native_filters, [report.ref_doctype, 'company', '=', company]]
        result = frappe.get_list(report.ref_doctype, fields=selected, filters=native_filters, limit_page_length=0)
        return dict(columns=[dict(fieldname=f, label=frappe._(meta.get_label(f) or f), fieldtype=meta.get_field(f).fieldtype if meta.get_field(f) else 'Data') for f in selected], result=result)
    from frappe.desk.query_report import run
    result = run(report_name=name, filters=json.dumps(values), ignore_prepared_report=True, are_default_filters=False, js_filters=definition['filters'])
    if result.get('message'):
        result['message'] = frappe.utils.strip_html(str(result['message']))
    return result


@frappe.whitelist(methods=['POST'])
def prepare_report(name, filters=None, company=None):
    _report(name); _company(company)
    values = frappe.parse_json(filters) or {}
    if company and values.get('company') and values['company'] != company:
        frappe.throw('Công ty không hợp lệ.', frappe.PermissionError)
    if company:
        values.setdefault('company', company)
    selected = values.get('company')
    for scoped_company in selected if isinstance(selected, list) else [selected]:
        _company(scoped_company)
    from frappe.core.doctype.prepared_report.prepared_report import make_prepared_report
    return make_prepared_report(name, values)


@frappe.whitelist()
def prepared_result(name, company=None):
    _access(); _company(company)
    prepared = frappe.get_doc('Prepared Report', name); prepared.check_permission('read')
    _report(prepared.report_name)
    values = frappe.parse_json(prepared.filters) or {}
    if prepared.owner != frappe.session.user or company and values.get('company') != company:
        frappe.throw('Báo cáo nền không thuộc phạm vi hiện tại.', frappe.PermissionError)
    data = json.loads(prepared.get_prepared_data()) if prepared.status == 'Completed' else None
    if data and data.get('message'):
        data['message'] = frappe.utils.strip_html(str(data['message']))
    return dict(status=prepared.status, result=data, error=frappe.utils.strip_html(prepared.error_message or '') if prepared.status == 'Failed' else None)


@frappe.whitelist()
def export_report(name, filters=None, company=None):
    report = _report(name)
    if not frappe.has_permission(report.ref_doctype, 'export'):
        frappe.throw('Bạn chưa có quyền xuất báo cáo.', frappe.PermissionError)
    result = run_report(name, filters, company)
    columns = [dict(fieldname='col_' + str(i), label=c.split(':')[0]) if isinstance(c, str) else c for i, c in enumerate(result.get('columns') or [])]
    keys = [r.get('fieldname') for r in columns]
    rows = [[r.get('label') or r.get('fieldname') for r in columns]]
    for row in result.get('result') or []:
        rows.append([row.get(k) for k in keys] if isinstance(row, dict) else row)
    from frappe.utils.csvutils import escape_formula_injection
    from frappe.utils.xlsxutils import make_xlsx
    content = make_xlsx([[escape_formula_injection(v) for v in row] for row in rows], 'Báo cáo')
    frappe.response.update(type='binary', filename=frappe.scrub(name) + '.xlsx', filecontent=content.getvalue())


@frappe.whitelist()
def export_list(doctype, company=None, search=None, filters=None, sort='modified desc'):
    _meta(doctype, 'export')
    data = listing(doctype, company=company, search=search, filters=filters, sort=sort, length=100)
    columns, rows = data['columns'], list(data['rows'])
    start = 100
    while data.get('has_more'):
        data = listing(doctype, company=company, search=search, filters=filters, sort=sort, start=start, length=100)
        rows.extend(data['rows']); start += 100
    from frappe.utils.csvutils import escape_formula_injection
    from frappe.utils.xlsxutils import make_xlsx
    values = [[c['label'] for c in columns]] + [[escape_formula_injection(row.get(c['fieldname'])) for c in columns] for row in rows]
    content = make_xlsx(values, 'Danh sách')
    frappe.response.update(type='binary', filename=frappe.scrub(doctype) + '.xlsx', filecontent=content.getvalue())


@frappe.whitelist()
def print_document(doctype, name):
    _meta(doctype); doc = frappe.get_doc(doctype, name); doc.check_permission('print')
    frappe.response.update(type='pdf', filename=frappe.scrub(doctype) + '-' + str(name).replace('/', '-') + '.pdf', filecontent=frappe.get_print(doctype, name, as_pdf=True))


@frappe.whitelist()
def supplier_connections(name, company):
    _meta('Supplier'); _company(company)
    frappe.get_doc('Supplier', name).check_permission('read')
    results = []
    for doctype in ('Supplier Quotation','Purchase Order','Purchase Receipt','Purchase Invoice','Payment Entry'):
        if not frappe.has_permission(doctype, 'read'):
            continue
        filters = dict(company=company, **({'party_type':'Supplier','party':name} if doctype == 'Payment Entry' else {'supplier':name}))
        counts = frappe.get_list(doctype, fields=[{'COUNT':'*'}], filters=filters, page_length=1)
        records = frappe.get_list(doctype, fields=['name','docstatus','modified'], filters=filters, order_by='modified desc', page_length=5)
        results.append(dict(doctype=doctype, count=next(iter(counts[0].values())) if counts else 0, rows=records, filters=filters))
    return results
