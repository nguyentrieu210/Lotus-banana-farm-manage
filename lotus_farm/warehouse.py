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
                companies=frappe.get_list('Company', fields=['name', 'abbr', 'default_currency'], limit_page_length=1000),
                permissions={dt: frappe.has_permission(dt, 'create') for dt in
                             ('Item', 'Item Group', 'Warehouse', 'UOM', 'Stock Entry', 'Stock Reconciliation', 'Company', 'Purchase Receipt', 'Purchase Order')})


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
    if not isinstance(values, dict) or kind not in ('item', 'group', 'warehouse', 'uom'):
        frappe.throw('Thông tin danh mục không hợp lệ.')
    doctype = {'item': 'Item', 'group': 'Item Group', 'warehouse': 'Warehouse', 'uom': 'UOM'}[kind]
    if not frappe.has_permission(doctype, 'create'):
        frappe.throw('Bạn chưa có quyền thêm danh mục này.', frappe.PermissionError)
    if kind == 'uom':
        label = _text(values.get('name'), 'Tên đơn vị tính')
        if frappe.db.exists('UOM', label):
            frappe.throw('Đơn vị tính đã tồn tại.')
        doc = frappe.get_doc(dict(doctype='UOM', uom_name=label, enabled=1,
                                  must_be_whole_number=cint(values.get('must_be_whole_number')))).insert()
    elif kind == 'group':
        doc = _create_group(values.get('name'), values.get('parent'))
    elif kind == 'warehouse':
        parent = frappe.get_doc('Warehouse', values.get('parent'))
        parent.check_permission('read')
        if parent.company != company or not parent.is_group or parent.disabled:
            frappe.throw('Kho cha phải là nhóm kho đang hoạt động của công ty đã chọn.')
        from lotus_farm.warehouse_masters import warehouse_code
        label=_text(values.get('name'),'Tên kho')
        if frappe.db.exists('Warehouse',warehouse_code(label,company)):
            frappe.throw('Tên kho đã tồn tại trong công ty.')
        doc = frappe.get_doc(dict(doctype='Warehouse', warehouse_name=label,
                                  parent_warehouse=parent.name, company=company, is_group=0))
        from lotus_farm.warehouse_masters import update_warehouse_details
        update_warehouse_details(doc, values)
        doc.insert()
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
                                  description=str(values.get('description') or '')[:2000]))
        from lotus_farm.warehouse_masters import set_minimum, configure_pack
        set_minimum(doc,company,values)
        configure_pack(doc,values)
        doc.insert()
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
    if doc.doctype=='Stock Entry':
        if len({r.get('s_warehouse') for r in doc.items if r.get('s_warehouse')})>1 or len({r.get('t_warehouse') for r in doc.items if r.get('t_warehouse')})>1:
            return False
        if any((flt(r.conversion_factor)!=1 or r.uom!=r.stock_uom) and doc.stock_entry_type!='Material Receipt' for r in doc.items):return False
    elif len({r.warehouse for r in doc.items})>1:return False
    for row in doc.items:
        item = frappe.get_doc('Item', row.item_code)
        item.check_permission('read')
        if item.has_batch_no or item.has_serial_no:
            return False
    return True


@frappe.whitelist()
def document(doctype, name):
    doc = _stock_doc(doctype, name)
    from lotus_farm.warehouse_masters import item_pack
    return dict(name=doc.name, doctype=doc.doctype, company=doc.company, docstatus=doc.docstatus, modified=str(doc.modified),
                receipt_reason=doc.get('lotus_receipt_reason') or '', supplier=doc.get('lotus_supplier') or '',
                posting_date=doc.posting_date, kind=doc.get('stock_entry_type') or doc.purpose,
                notes=doc.get('remarks'), currency=frappe.get_cached_value('Company', doc.company, 'default_currency'),
                issue_mode=doc.get('lotus_issue_mode'), receiver=doc.get('lotus_receiver'),
                receiver_employee=doc.get('lotus_receiver_employee'), work_plan=doc.get('lotus_work_plan'),
                basic_total=sum(flt(row.get('basic_amount')) for row in doc.items),
                additional_total=flt(doc.get('total_additional_costs')),
                incoming_total=flt(doc.get('total_incoming_value')),
                additional_costs=[dict(description=row.description, amount=row.amount, expense_account=row.expense_account)
                                  for row in (doc.get('additional_costs') or [])],
                can_submit=doc.docstatus == 0 and doc.has_permission('submit') and _simple_doc(doc),
                can_write=doc.docstatus == 0 and doc.has_permission('write') and _simple_doc(doc),
                can_delete=doc.docstatus == 0 and doc.has_permission('delete') and _simple_doc(doc),
                items=[dict(item=row.item_code, item_name=row.item_name,
                            uom=(row.get('uom') if doc.doctype=='Stock Entry' and doc.stock_entry_type=='Material Receipt' else row.get('stock_uom') or row.get('uom')),
                            qty=(flt(row.qty) if doc.doctype=='Stock Entry' and doc.stock_entry_type=='Material Receipt' else flt(row.get('transfer_qty')) if doc.doctype=='Stock Entry' else row.qty),
                            stock_uom=row.get('stock_uom'),conversion_factor=flt(row.get('conversion_factor') or 1),
                            **(item_pack(frappe.get_doc('Item',row.item_code)) if doc.doctype=='Stock Entry' and doc.stock_entry_type=='Material Receipt' else {}),
                            source=row.get('s_warehouse'), target=row.get('t_warehouse') or row.get('warehouse'),
                            area=row.get('lotus_usage_area'), requirement=row.get('lotus_requirement'), requirement_line=row.get('lotus_requirement_line'), material_request=row.get('material_request'), material_request_item=row.get('material_request_item'),
                            rate=(flt(row.get('basic_rate'))*flt(row.get('conversion_factor') or 1) if doc.doctype=='Stock Entry' and doc.stock_entry_type=='Material Receipt' else row.get('basic_rate') if doc.doctype=='Stock Entry' else row.get('valuation_rate')),
                            basic_amount=row.get('basic_amount'), additional_cost=row.get('additional_cost'),
                            valuation_rate=row.get('valuation_rate'), amount=row.get('amount'))
                       for row in doc.items])


@frappe.whitelist(methods=['POST'])
def submit_document(doctype, name,modified=None):
    from lotus_farm.controls import lock
    if doctype not in ('Stock Entry','Stock Reconciliation'):frappe.throw('Loại phiếu không hợp lệ.')
    lock(doctype,name)
    doc = _stock_doc(doctype, name)
    doc.check_permission('submit')
    if not _simple_doc(doc):
        frappe.throw('Phiếu có nghiệp vụ nâng cao hoặc lô/serial chưa được hỗ trợ ghi sổ tại màn hình này.')
    if doc.docstatus==1 and modified:return dict(name=doc.name,docstatus=1)
    if not modified or str(doc.modified)!=str(modified):frappe.throw('Phiếu đã thay đổi. Mở lại để kiểm tra trước khi ghi sổ.')
    if doc.docstatus != 0:
        frappe.throw('Chỉ ghi sổ được phiếu nháp.')
    if doctype=='Stock Entry':check_outbound_stock(doc)
    doc.submit()
    return dict(name=doc.name, docstatus=doc.docstatus)


@frappe.whitelist(methods=['POST'])
def delete_draft(doctype,name,modified):
    doc=_stock_doc(doctype,name);doc.check_permission('delete')
    if doc.docstatus!=0 or not _simple_doc(doc):frappe.throw('Chỉ xóa phiếu nháp đơn giản chưa ghi sổ.')
    if str(doc.modified)!=str(modified):frappe.throw('Phiếu đã thay đổi. Mở lại trước khi xóa.')
    frappe.delete_doc(doctype,name)
    return dict(name=name,deleted=True)


@frappe.whitelist()
def documents(company,warehouse=None,from_date=None,to_date=None,search=None,start=0,column_filters=None,sort_model=None,kind=None):
    from lotus_farm.table_filters import faceted_distinct,selections,matches
    _access();_company(company)
    stores=frappe.get_list('Warehouse',filters={'company':company,'is_group':0},pluck='name',limit_page_length=0)
    allowed=set(stores)
    if warehouse:
        record=frappe.get_doc('Warehouse',warehouse);record.check_permission('read')
        if record.company!=company or record.is_group:frappe.throw('Kho không thuộc công ty.')
    if from_date and to_date and getdate(from_date)>getdate(to_date):frappe.throw('Khoảng ngày không hợp lệ.')
    filters={'company':company}
    if from_date and to_date:filters['posting_date']=['between',[getdate(from_date),getdate(to_date)]]
    elif from_date:filters['posting_date']=['>=',getdate(from_date)]
    elif to_date:filters['posting_date']=['<=',getdate(to_date)]
    kinds={'Material Receipt':'Nhập kho','Material Issue':'Xuất dùng','Material Transfer':'Chuyển kho','Repack':'Đóng gói'}
    # Kho menu: one list per kind of document (Nhập kho · Xuất kho · Chuyển kho · Kiểm kê); no kind = every stock document.
    scopes={'receipts':{'Purchase Receipt':None,'Stock Entry':['Material Receipt']},'issues':{'Stock Entry':['Material Issue']},
            'transfers':{'Stock Entry':['Material Transfer']},'counts':{'Stock Reconciliation':None}}
    if kind and kind not in scopes:frappe.throw('Loại phiếu không hợp lệ.')
    scope=scopes.get(kind) or {dt:None for dt in ('Stock Entry','Stock Reconciliation','Purchase Receipt')}
    rows=[]
    for dt,entry_types in scope.items():
        if not frappe.has_permission(dt,'read'):continue
        dt_filters=dict(filters,stock_entry_type=['in',entry_types]) if entry_types else filters
        for entry in frappe.get_list(dt,filters=dt_filters,fields=['name','posting_date','posting_time','docstatus','modified'],order_by='posting_date desc, posting_time desc, modified desc',limit_page_length=0):
            if search and str(search).casefold() not in entry.name.casefold():continue
            doc=frappe.get_doc(dt,entry.name)
            names={r.get(f) for r in doc.items for f in ('s_warehouse','t_warehouse','warehouse') if r.get(f)}
            if not names.issubset(allowed) or (warehouse and warehouse not in names):continue
            entry.doctype=dt;entry.kind=kinds.get(doc.get('stock_entry_type'),doc.get('stock_entry_type')) if dt=='Stock Entry' else ('Nhập mua' if dt=='Purchase Receipt' else 'Kiểm kê')
            entry.warehouses=' · '.join(sorted(names));rows.append(entry)
    rows.sort(key=lambda r:(str(r.posting_date),str(r.posting_time),str(r.modified)),reverse=True)
    fields=['name','kind','posting_date','docstatus','warehouses']
    selected=selections(column_filters,fields);choices=faceted_distinct(rows,fields,selected)
    rows=[r for r in rows if matches(r,selected)]
    from lotus_farm.table_filters import sorted_rows
    rows=sorted_rows(rows,sort_model,fields)
    start=max(0,cint(start))
    return dict(rows=rows[start:start+50],total_count=len(rows),has_more=len(rows)>start+50,filter_values=choices)


@frappe.whitelist()
def stock_summary(company,warehouse=None,from_date=None,to_date=None,search=None):
    """Nhập – xuất – tồn theo số lượng cho màn Kho (giá trị chỉ xem ở Kế toán), chỉ trong các kho người dùng được đọc."""
    from frappe.utils import get_first_day
    from lotus_farm.finance.statements import ledger_summary
    _access();_company(company)
    if not frappe.has_permission('Stock Ledger Entry','read'):
        frappe.throw('Bạn chưa có quyền xem lịch sử nhập xuất.',frappe.PermissionError)
    to_date=getdate(to_date or nowdate());from_date=getdate(from_date or get_first_day(to_date))
    if from_date>to_date:frappe.throw('Từ ngày phải trước hoặc bằng đến ngày.')
    stores=frappe.get_list('Warehouse',filters={'company':company,'is_group':0},pluck='name',limit_page_length=0)
    if warehouse:
        if warehouse not in stores:frappe.throw('Kho không thuộc công ty hoặc bạn chưa có quyền xem.')
        stores=[warehouse]
    query=str(search or '').strip().casefold()[:100]
    quantities=('opening_qty','in_qty','out_qty','closing_qty')
    rows=[]
    for r in ledger_summary(company,from_date,to_date,stores):
        if query and not any(query in str(r.get(k) or '').casefold() for k in ('item_code','item_name','item_group')):continue
        r={k:v for k,v in r.items() if not k.endswith('_value')}
        if any(abs(r[k])>0.0005 for k in quantities):rows.append(r)
    totals={k:sum(r[k] for r in rows) for k in quantities}
    return dict(from_date=str(from_date),to_date=str(to_date),rows=rows,totals=totals,item_count=len({r['item_code'] for r in rows}))


@frappe.whitelist()
def movements(company, warehouse=None, search=None, from_date=None,to_date=None,start=0,column_filters=None,sort_model=None):
    from lotus_farm.table_filters import selections, matches, faceted_distinct
    _access()
    _company(company)
    if not frappe.has_permission('Stock Ledger Entry', 'read'):
        frappe.throw('Bạn chưa có quyền xem lịch sử nhập xuất.', frappe.PermissionError)
    if from_date and to_date and getdate(from_date) > getdate(to_date):
        frappe.throw('Từ ngày phải trước hoặc bằng đến ngày.')
    warehouses = frappe.get_list('Warehouse', filters={'company': company, 'is_group': 0}, fields=['name'], limit_page_length=0)
    names = [row.name for row in warehouses]
    if warehouse:
        doc = frappe.get_doc('Warehouse', warehouse)
        doc.check_permission('read')
        if doc.company != company or doc.is_group:
            frappe.throw('Kho không thuộc công ty đã chọn.')
        names = [warehouse] if warehouse in names else []
    items = frappe.get_list('Item', fields=['name', 'item_name'], limit_page_length=0)
    labels = {row.name: row.item_name for row in items}
    filters = {'company': company, 'is_cancelled': 0, 'warehouse': ['in', names or ['__none__']],
               'item_code': ['in', list(labels) or ['__none__']]}
    if from_date and to_date:
        filters['posting_date'] = ['between', [getdate(from_date), getdate(to_date)]]
    elif from_date:
        filters['posting_date'] = ['>=', getdate(from_date)]
    elif to_date:
        filters['posting_date'] = ['<=', getdate(to_date)]
    rows = frappe.get_list('Stock Ledger Entry', filters=filters,
        fields=['name', 'posting_date', 'posting_time', 'item_code', 'warehouse', 'voucher_type', 'voucher_no',
                'voucher_detail_no', 'actual_qty', 'qty_after_transaction', 'stock_uom'],
        order_by='posting_datetime desc, creation desc, name desc', limit_page_length=0)
    query = str(search or '').strip().casefold()[:100]
    for row in rows:
        row.item_name = labels[row.item_code]
        row.in_qty = max(0, flt(row.actual_qty))
        row.out_qty = max(0, -flt(row.actual_qty))
        row.opening_qty = flt(row.qty_after_transaction)-flt(row.actual_qty)
        row.kind = 'Nhập' if row.actual_qty > 0 else 'Xuất' if row.actual_qty < 0 else 'Điều chỉnh giá trị'
    if query:
        rows = [row for row in rows if any(query in str(row.get(field) or '').casefold()
                for field in ('item_code', 'item_name', 'voucher_no'))]
    # Enrich SLE with the permitted source voucher's purpose and remarks.
    # Never fetch voucher notes without read permission; keep stock quantity privacy unchanged.
    voucher_info = {}
    for doctype in ('Stock Entry', 'Purchase Receipt', 'Stock Reconciliation', 'Delivery Note'):
        ids = list({row.voucher_no for row in rows if row.voucher_type == doctype and row.voucher_no})
        if not ids or not frappe.has_permission(doctype, 'read'):
            continue
        meta = frappe.get_meta(doctype)
        fields_to_read = ['name'] + [field for field in (
            'remarks', 'purpose', 'stock_entry_type', 'lotus_receiver',
            'lotus_work_plan', 'lotus_supplier', 'supplier', 'supplier_name')
            if meta.has_field(field)]
        for offset in range(0, len(ids), 500):
            docs = frappe.get_list(doctype, filters={'name': ['in', ids[offset:offset+500]]},
                                   fields=fields_to_read, limit_page_length=0)
            for doc in docs:
                voucher_info[(doctype, doc.name)] = doc

    stock_purposes = {
        'Material Receipt': 'Nhập kho', 'Material Issue': 'Xuất dùng',
        'Material Transfer': 'Chuyển kho', 'Manufacture': 'Sản xuất',
        'Repack': 'Đóng gói', 'Send to Subcontractor': 'Gửi gia công',
        'Receive at Warehouse': 'Nhập kho', 'Opening Stock': 'Tồn đầu kỳ',
        'Stock Reconciliation': 'Kiểm kê'
    }
    doc_purposes = {'Purchase Receipt': 'Nhập hàng mua', 'Delivery Note': 'Xuất hàng bán',
                    'Stock Reconciliation': 'Kiểm kê'}
    # Child rows have no independent document permission. Only access lines belonging
    # to Stock Entry parents returned by the permission-aware get_list above.
    visible_entries = {name for doctype, name in voucher_info if doctype == 'Stock Entry'}
    detail_ids = list({row.voucher_detail_no for row in rows
                       if row.voucher_type == 'Stock Entry'
                       and row.voucher_no in visible_entries and row.get('voucher_detail_no')})
    usage_by_detail = {}
    if detail_ids and frappe.get_meta('Stock Entry Detail').has_field('lotus_usage_area'):
        for offset in range(0, len(detail_ids), 500):
            details = frappe.get_all('Stock Entry Detail',
                filters={'name': ['in', detail_ids[offset:offset+500]],
                         'parent': ['in', list(visible_entries)]},
                fields=['name', 'lotus_usage_area'], limit_page_length=0)
            usage_by_detail.update({detail.name: detail.lotus_usage_area or '' for detail in details})

    # Only show a team when exactly one team is recorded against the linked plan.
    plan_teams = {}
    plan_names = list({doc.get('lotus_work_plan') for (doctype, name), doc in voucher_info.items()
                       if doctype == 'Stock Entry' and doc.get('lotus_work_plan')})
    if plan_names and frappe.has_permission('Daily Work Plan', 'read'):
        visible_plans = set()
        for offset in range(0, len(plan_names), 500):
            visible_plans.update(frappe.get_list('Daily Work Plan',
                filters={'name': ['in', plan_names[offset:offset+500]]},
                pluck='name', limit_page_length=0))
        if visible_plans:
            for offset in range(0, len(visible_plans), 500):
                batch = list(visible_plans)[offset:offset+500]
                for line in frappe.get_all('Daily Work Plan Line',
                        filters={'parent': ['in', batch]}, fields=['parent', 'work_team'],
                        limit_page_length=0):
                    if line.work_team:
                        plan_teams.setdefault(line.parent, set()).add(line.work_team)

    for row in rows:
        voucher = voucher_info.get((row.voucher_type, row.voucher_no))
        purpose = (voucher.get('stock_entry_type') or voucher.get('purpose')) if voucher else None
        action = stock_purposes.get(purpose, doc_purposes.get(row.voucher_type, row.kind))
        remarks = str(voucher.get('remarks') or '').strip() if voucher else ''
        row.transaction_type = action
        row.content = (action + ' – ' + remarks) if remarks else action
        row.receiver = (voucher.get('lotus_receiver') or voucher.get('supplier_name')
                        or voucher.get('supplier') or voucher.get('lotus_supplier') or '') if voucher else ''
        row.usage_area = usage_by_detail.get(row.get('voucher_detail_no'), '')
        teams = plan_teams.get(voucher.get('lotus_work_plan'), set()) if voucher else set()
        row.work_team = next(iter(teams)) if len(teams) == 1 else ''
    fields = ['posting_date', 'item_code', 'item_name', 'warehouse', 'voucher_no',
              'kind', 'transaction_type', 'content', 'receiver', 'usage_area', 'work_team',
              'in_qty', 'out_qty', 'opening_qty', 'qty_after_transaction', 'stock_uom']
    selected = selections(column_filters, fields)
    choices = faceted_distinct(rows, fields, selected, labels={'item_code': lambda row: row.item_name + ' · ' + row.item_code})
    rows = [row for row in rows if matches(row, selected)]
    from lotus_farm.table_filters import sorted_rows
    rows=sorted_rows(rows,sort_model,fields,{'item_code':'item_name'})
    start = max(0, cint(start))
    return dict(rows=rows[start:start+50], total_count=len(rows), has_more=len(rows)>start+50, filter_values=choices)


@frappe.whitelist()
def overview(company, warehouse=None, search=None, start=0, column_filters=None,from_date=None,to_date=None,sort_model=None):
    from lotus_farm.table_filters import selections, matches, faceted_distinct
    _access()
    company_doc = _company(company)
    warehouses = frappe.get_list('Warehouse', filters={'company': company, 'is_group': 0, 'disabled': 0},
                                fields=['name', 'warehouse_name'], limit_page_length=1000, order_by='name')
    if warehouse:
        _warehouse(warehouse, company)
    all_names = [w.name for w in warehouses]
    names = [warehouse] if warehouse else all_names
    filters = {'disabled': 0, 'is_stock_item': 1}
    or_filters = None
    if search:
        or_filters = [[ 'item_code', 'like', '%' + str(search)[:100] + '%'],
                      [ 'item_name', 'like', '%' + str(search)[:100] + '%']]
    start = max(0, cint(start))
    # Preserve permission scope while keeping counts independent of search/filters.
    catalogue_names = [r.name for r in frappe.get_list('Item', filters=filters, fields=['name'], limit_page_length=0)]
    catalogue_count = len(catalogue_names)
    items = frappe.get_list('Item', filters=filters, or_filters=or_filters,
                            fields=['name', 'item_name', 'item_group', 'stock_uom', 'has_batch_no', 'has_serial_no','lotus_minimum_stock_global'],
                            order_by='item_name, name', limit_page_length=0)
    all_bins = frappe.get_list('Bin', filters={'warehouse': ['in', all_names or ['__none__']],
                          'item_code': ['in', catalogue_names or ['__none__']]},
                          fields=['item_code', 'warehouse', 'actual_qty'],
                          limit_page_length=0)
    bins = [b for b in all_bins if b.warehouse in names]
    actual_by_item = {}
    for balance in bins:
        actual_by_item[balance.item_code] = actual_by_item.get(balance.item_code, 0) + flt(balance.actual_qty)
    stocked_count = sum(qty > 0 for qty in actual_by_item.values())
    from lotus_farm.warehouse_masters import item_pack
    conversions = frappe.get_all('UOM Conversion Detail',
        filters={'parenttype':'Item', 'parent':['in',[i.name for i in items] or ['__none__']]},
        fields=['parent','uom','conversion_factor'],limit_page_length=0)
    for item in items:
        rows = [b for b in bins if b.item_code == item.name]
        item.actual_qty = sum(flt(b.actual_qty) for b in rows)
        global_qty=sum(flt(b.actual_qty) for b in all_bins if b.item_code==item.name)
        item.minimum_stock=flt(item.get('lotus_minimum_stock_global'))
        item.shortage_qty=max(0,item.minimum_stock-global_qty)
        item.company_actual_qty=global_qty
        pack=next((r for r in conversions if r.parent==item.name and r.uom!=item.stock_uom),None)
        item.pack_uom=pack.uom if pack else ''
        item.pack_factor=flt(pack.conversion_factor) if pack else 0
        item.pack_actual_qty=item.actual_qty/item.pack_factor if item.pack_factor else None
        item.pop('lotus_minimum_stock_global',None)
        item.stock_status = 'Dưới tối thiểu' if item.shortage_qty>0 else 'Có tồn' if item.actual_qty > 0 else 'Tồn âm' if item.actual_qty < 0 else 'Chưa có tồn'
    from lotus_farm.warehouse_planning import snapshot
    coverage=snapshot(company,warehouse,from_date,to_date,include_stock=True)
    unknown={r['item'] for r in coverage['unmapped']}
    for item in items:
        rows=[r for r in coverage['rows'] if r['item']==item.name]
        for field,source in [('demand_qty','remaining_qty'),('available_qty','available_qty'),('demand_shortage_qty','shortage_qty'),('incoming_qty','incoming_qty'),('to_buy_qty','to_buy_qty')]:
            item[field]=sum(flt(r.get(source)) for r in rows)
        if coverage['warnings'] or item.name in unknown:
            item.demand_qty=item.demand_shortage_qty=item.to_buy_qty=None
            item.coverage_status='Chưa xác định kho' if item.name in unknown else 'Chưa đủ dữ liệu'
        else:
            item.coverage_status='Đủ hàng' if item.demand_shortage_qty<=0 else 'Chờ nhập' if item.to_buy_qty<=0 else 'Cần mua'
    fields = ['name', 'item_group', 'stock_uom', 'actual_qty','pack_actual_qty','minimum_stock','shortage_qty', 'stock_status','demand_qty','available_qty','demand_shortage_qty','incoming_qty','to_buy_qty','coverage_status']
    selected = selections(column_filters, fields)
    choices = faceted_distinct(items, fields, selected, labels={'name': lambda row: row.item_name + ' · ' + row.name})
    items = [item for item in items if matches(item, selected)]
    from lotus_farm.table_filters import sorted_rows
    items=sorted_rows(items,sort_model,fields,{'name':'item_name'})
    visible_items = items[start:start+50]
    entries = frappe.get_list('Stock Entry', filters={'company': company},
                              fields=['name', 'stock_entry_type', 'posting_date', 'docstatus'],
                              order_by='modified desc', limit_page_length=20)
    reconciliations = (frappe.get_list('Stock Reconciliation', filters={'company': company},
                       fields=['name', 'posting_date', 'docstatus'], order_by='modified desc', limit_page_length=10)
                       if frappe.has_permission('Stock Reconciliation', 'read') else [])
    return dict(warehouses=warehouses, items=visible_items, has_more=len(items) > start+50, filter_values=choices, total_count=len(items),catalogue_count=catalogue_count,stocked_count=stocked_count,
                entries=entries, reconciliations=reconciliations, currency=company_doc.default_currency,coverage_warnings=coverage['warnings'],demand_from=coverage['from_date'],demand_to=coverage['to_date'])


def _number(value, label, allow_zero=False):
    try:
        result = float(value)
    except (TypeError, ValueError):
        frappe.throw(label + ' phải là số.')
    if not math.isfinite(result) or result < 0 or (result == 0 and not allow_zero):
        frappe.throw(label + (' không được âm.' if allow_zero else ' phải lớn hơn 0.'))
    return result


@frappe.whitelist()
def receipt_accounts(company):
    _access()
    company_doc = _company(company)
    if not frappe.has_permission('Account', 'read'):
        return dict(accounts=[], default_account=None)
    accounts = frappe.get_list('Account', filters={'company': company, 'is_group': 0, 'disabled': 0, 'root_type': 'Expense'},
                               fields=['name', 'account_name', 'account_currency'], order_by='account_name', limit_page_length=1000)
    accounts = [a for a in accounts if (a.account_currency or company_doc.default_currency) == company_doc.default_currency]
    default_account = company_doc.get('stock_adjustment_account')
    return dict(accounts=accounts, default_account=default_account if any(a.name == default_account for a in accounts) else None)


def _receipt_costs(company, costs, basic_total):
    _number(basic_total, 'Tổng tiền vật tư', allow_zero=True)
    rows = frappe.parse_json(costs) if costs else []
    if not isinstance(rows, list) or len(rows) > 30:
        frappe.throw('Chi phí nhập kho tối đa 30 dòng.')
    if rows and basic_total <= 0:
        frappe.throw('Nhập đơn giá vật tư trước khi phân bổ chi phí theo giá trị hàng.')
    if not rows:
        return []
    company_doc = _company(company)
    result = []
    for row in rows:
        if not isinstance(row, dict):
            frappe.throw('Dòng chi phí không hợp lệ.')
        amount = _number(row.get('amount'), 'Chi phí')
        description = _text(row.get('description'), 'Khoản chi phí')
        account = frappe.get_doc('Account', row.get('expense_account'))
        account.check_permission('read')
        if account.company != company or account.is_group or account.disabled or account.root_type != 'Expense':
            frappe.throw('Tài khoản chi phí phải đang hoạt động, không phải nhóm và thuộc công ty của phiếu.')
        currency = account.get('account_currency') or company_doc.default_currency
        if currency != company_doc.default_currency:
            frappe.throw('Chi phí nhập tại đây phải dùng tiền tệ của công ty.')
        result.append(dict(expense_account=account.name, description=description, amount=amount,
                           account_currency=currency, exchange_rate=1, base_amount=amount,
                           cost_center=company_doc.get('cost_center')))
    _number(sum(row['amount'] for row in result), 'Tổng chi phí', allow_zero=True)
    return result


@frappe.whitelist(methods=['POST'])
def create_draft(company, kind, posting_date, lines, source=None, target=None, notes=None, count_purpose='Stock Reconciliation', issue_mode='Manual', work_plan=None, receiver=None, receiver_employee=None, additional_costs=None,existing_name=None,base_modified=None,client_event_id=None,receipt_reason=None,supplier=None):
    _access()
    _company(company)
    types = {'receipt': 'Material Receipt', 'issue': 'Material Issue', 'transfer': 'Material Transfer'}
    if kind not in (*types, 'count'):
        frappe.throw('Loại phiếu không hợp lệ.')
    if additional_costs and kind != 'receipt':
        frappe.throw('Chi phí bổ sung ở form này chỉ dành cho nhập kho.')
    dt = 'Stock Reconciliation' if kind == 'count' else 'Stock Entry'
    client_key=payload_hash=None
    if client_event_id and not existing_name:
        import hashlib,json
        from lotus_farm.controls import lock
        event=_text(client_event_id,'Mã yêu cầu')
        client_key=hashlib.sha256((frappe.session.user+':'+event).encode()).hexdigest()
        payload_hash=hashlib.sha256(json.dumps(dict(company=company,kind=kind,posting_date=str(posting_date),lines=frappe.parse_json(lines),source=source,target=target,notes=notes,count_purpose=count_purpose,issue_mode=issue_mode,work_plan=work_plan,receiver_employee=receiver_employee,**(dict(receipt_reason=receipt_reason,supplier=supplier) if kind=='receipt' else {}),additional_costs=frappe.parse_json(additional_costs) if additional_costs else []),sort_keys=True,default=str).encode()).hexdigest()
        lock('Company',company)
        existing=frappe.db.get_value(dt,{'lotus_client_key':client_key},['name','lotus_payload_hash'],as_dict=True)
        if existing:
            doc=_stock_doc(dt,existing.name)
            if existing.lotus_payload_hash!=payload_hash:frappe.throw('Yêu cầu này đã tạo phiếu '+doc.name+'. Mở lại phiếu để sửa, không gửi phiếu mới.')
            return dict(name=doc.name,doctype=dt,docstatus=doc.docstatus)
    if not frappe.has_permission(dt, 'write' if existing_name else 'create'):
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
    if existing_name:
        doc=_stock_doc(dt,existing_name);doc.check_permission('write')
        if doc.company!=company or doc.docstatus!=0 or not _simple_doc(doc):frappe.throw('Chỉ sửa phiếu nháp đơn giản của công ty đã chọn.')
        if dt=='Stock Entry' and doc.stock_entry_type!=types[kind]:frappe.throw('Không đổi nghiệp vụ của phiếu đã tạo. Tạo phiếu mới nếu cần.')
        if dt=='Stock Reconciliation' and doc.purpose!=count_purpose:frappe.throw('Không đổi loại kiểm kê của phiếu đã tạo.')
        if str(doc.modified)!=str(base_modified):frappe.throw('Phiếu đã thay đổi. Mở lại để lấy dữ liệu mới.')
        doc.set('items',[])
        if dt=='Stock Entry':doc.set('additional_costs',[])
    else:
        doc = frappe.new_doc(dt)
    doc.company = company
    if client_key:doc.lotus_client_key=client_key;doc.lotus_payload_hash=payload_hash
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
        if kind == 'receipt' and doc.meta.has_field('lotus_receipt_reason'):
            if receipt_reason and receipt_reason not in ('Purchase', 'Recovery', 'Surplus'):
                frappe.throw('Lý do nhập kho không hợp lệ.')
            # The finance rules (lotus_farm.finance.stock) decide the credited account from the reason.
            # Goods bought without an order still name their supplier and price; other receipts say why they came in.
            if not receipt_reason and not existing_name:
                frappe.throw('Chọn lý do nhập kho: mua lẻ không theo đơn, thu hồi từ lô hay thừa khi kiểm kê.')
            if receipt_reason == 'Purchase' and not supplier:
                frappe.throw('Hàng mua phải chọn nhà cung cấp.')
            doc.lotus_receipt_reason = receipt_reason or None
            doc.lotus_supplier = supplier if receipt_reason == 'Purchase' else None
        if kind == 'issue':
            if issue_mode not in ('Manual', 'Plan', 'Request'):
                frappe.throw('Hình thức xuất kho không hợp lệ.')
            doc.lotus_issue_mode = issue_mode
            doc.lotus_work_plan = work_plan if issue_mode == 'Plan' else None
            from lotus_farm.warehouse_masters import employee_contact
            staff=employee_contact(company,receiver_employee)
            if staff:
                doc.lotus_receiver_employee=staff.name
                doc.lotus_receiver=staff.employee_name
            elif not (existing_name and doc.get('lotus_receiver')):
                frappe.throw('Chọn người nhận vật tư trong danh sách nhân sự HRMS.')
    seen = set()
    basic_total = 0
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
        entry_uom=item.stock_uom
        factor=1.0
        if kind=='receipt':
            entry_uom=str(row.get('uom') or item.stock_uom)
            if entry_uom!=item.stock_uom:
                conversion=next((r for r in item.uoms if r.uom==entry_uom),None)
                if not conversion or flt(conversion.conversion_factor)<=0:
                    frappe.throw('Đơn vị nhập chưa được khai báo quy đổi cho vật tư '+item.name)
                factor=flt(conversion.conversion_factor)
        # Existing clients can omit rates; new receipt forms send explicit prices.
        existing_rate = frappe.db.get_value('Bin', {'item_code': item.name, 'warehouse': target or source}, 'valuation_rate') or item.get('valuation_rate') or 0
        rate = _number(row.get('rate', existing_rate), 'Định giá', allow_zero=True)
        if kind == 'receipt' and receipt_reason == 'Purchase' and rate <= 0:
            frappe.throw('Nhập giá mua cho ' + item.item_name + '.')
        values = dict(item_code=item.name, qty=qty, allow_zero_valuation_rate=1)
        if kind == 'count':
            if count_purpose=='Stock Reconciliation':
                from erpnext.stock.utils import get_stock_balance
                _,rate=get_stock_balance(item.name,target,getdate(posting_date),with_valuation_rate=True)
                values.update(warehouse=target,valuation_rate=flt(rate))
            else:
                if qty>0 and rate<=0:frappe.throw('Tồn đầu kỳ cần đơn giá lớn hơn 0 cho '+item.name)
                values.update(warehouse=target,valuation_rate=rate)
        else:
            values.update(uom=entry_uom, stock_uom=item.stock_uom, conversion_factor=factor)
            if kind in ('issue', 'transfer'):
                values['s_warehouse'] = source
            if kind in ('receipt', 'transfer'):
                values['t_warehouse'] = target
            if kind == 'receipt':
                values['basic_rate'] = rate/factor
                values['set_basic_rate_manually'] = 1
                basic_total += qty * rate
            if kind == 'receipt' and receipt_reason == 'Recovery':
                values['lotus_usage_area'] = _text(row.get('area'), 'Lô thu hồi vật tư')
            if kind == 'issue':
                values['lotus_usage_area'] = _text(row.get('area'), 'Khu vực / lô sử dụng')
                if issue_mode == 'Plan':
                    values['lotus_requirement'] = row.get('requirement')
                    values['lotus_requirement_line'] = row.get('requirement_line')
                elif issue_mode == 'Request':
                    values['material_request'] = row.get('material_request')
                    values['material_request_item'] = row.get('material_request_item')
        doc.append('items', values)
    if kind == 'receipt':
        for cost in _receipt_costs(company, additional_costs, basic_total):
            doc.append('additional_costs', cost)
    if kind in ('issue','transfer'):
        from lotus_farm.controls import lock
        lock('Company',company)
        check_outbound_stock(doc,include_holds=True)
    if existing_name:doc.save()
    else:doc.insert()
    return dict(name=doc.name, doctype=doc.doctype)


def check_outbound_stock(doc,include_holds=False):
    """Reject unsupported quantities before saving a simple warehouse draft."""
    from collections import defaultdict
    from erpnext.stock.utils import get_stock_balance
    requested=defaultdict(float)
    for row in doc.items:
        if row.get('s_warehouse'):
            requested[(row.item_code,row.s_warehouse)]+=flt(row.qty)*flt(row.conversion_factor or 1)
    for (item,store),qty in sorted(requested.items()):
        current=flt(frappe.db.get_value('Bin',{'item_code':item,'warehouse':store},'actual_qty'))
        dated=flt(get_stock_balance(item,store,doc.posting_date,doc.posting_time))
        available=min(current,dated)
        if include_holds:
            held=frappe.db.sql('''select coalesce(sum(d.qty*d.conversion_factor),0) from `tabStock Entry Detail` d
                join `tabStock Entry` p on p.name=d.parent where p.company=%s and p.docstatus=0
                and d.item_code=%s and d.s_warehouse=%s and p.name!=%s''',(doc.company,item,store,doc.name or ''))[0][0]
            reserved=flt(frappe.db.get_value('Bin',{'item_code':item,'warehouse':store},'reserved_stock'))
            available-=flt(held)+reserved
        if qty>available+0.000001:
            label=frappe.db.get_value('Item',item,'item_name') or item
            frappe.throw(f'{label} ({item}) tại {store}: tồn có thể xuất {available:g}, yêu cầu {qty:g}, thiếu {qty-available:g}. Không thể lưu phiếu xuất/chuyển kho khi thiếu hàng.')
