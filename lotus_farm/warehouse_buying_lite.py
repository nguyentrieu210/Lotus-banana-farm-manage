"""Minimal supplier, purchase order, quote and arrival workflow for Lotus warehouse."""
import frappe
from frappe.utils import cint, flt, getdate, nowdate
from lotus_farm.warehouse import _company, _warehouse, _number, _text

def _access():
    if frappe.session.user == 'Guest':
        frappe.throw('Vui lòng đăng nhập.', frappe.AuthenticationError)
    for dt in ('Company','Warehouse','Item'):
        if not frappe.has_permission(dt,'read'):
            frappe.throw('Không có quyền đọc '+dt,frappe.PermissionError)
    if not any(frappe.has_permission(dt,'read') for dt in ('Purchase Order','Material Request')):
        frappe.throw('Chưa có quyền xem chứng từ mua hàng.',frappe.PermissionError)


MODES = ('Chủ đầu tư chỉ định', 'Kho tự mua')
DONE = ('Closed', 'Stopped', 'Cancelled')


def install_fields():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    create_custom_fields({'Purchase Order': [
        dict(fieldname='lotus_purchase_mode', label='Cách mua hàng', fieldtype='Select',
             options='\n'.join(MODES), insert_after='supplier'),
        dict(fieldname='lotus_delivery_note', label='Ghi chú giao hàng', fieldtype='Small Text',
             insert_after='lotus_purchase_mode'),
         dict(fieldname='lotus_approval_status',label='Duyệt mua',fieldtype='Select',
              options='\nNháp\nChờ duyệt\nTừ chối',insert_after='lotus_delivery_note',read_only=1),
         dict(fieldname='lotus_requested_by',label='Người trình duyệt',fieldtype='Link',
              options='User',insert_after='lotus_approval_status',read_only=1),
         dict(fieldname='lotus_requested_at',label='Ngày trình duyệt',fieldtype='Datetime',
              insert_after='lotus_requested_by',read_only=1),
         dict(fieldname='lotus_approved_by',label='Người duyệt',fieldtype='Link',
              options='User',insert_after='lotus_requested_at',read_only=1),
         dict(fieldname='lotus_approved_at',label='Ngày duyệt',fieldtype='Datetime',
              insert_after='lotus_approved_by',read_only=1),
         dict(fieldname='lotus_reject_reason',label='Lý do từ chối',fieldtype='Small Text',
              insert_after='lotus_approved_at',read_only=1),
         dict(fieldname='lotus_sent_at',label='Đã gửi nhà cung cấp lúc',fieldtype='Datetime',
              insert_after='lotus_reject_reason',read_only=1),
         dict(fieldname='lotus_sent_by',label='Người gửi đơn',fieldtype='Link',options='User',
              insert_after='lotus_sent_at',read_only=1),
         dict(fieldname='lotus_supplier_confirmed_at',label='NCC xác nhận lúc',fieldtype='Datetime',
              insert_after='lotus_sent_by',read_only=1),
         dict(fieldname='lotus_supplier_confirmed_by',label='Người ghi nhận NCC xác nhận',fieldtype='Link',
              options='User',insert_after='lotus_supplier_confirmed_at',read_only=1),
         dict(fieldname='lotus_revised_delivery_date',label='Ngày NCC hẹn lại',fieldtype='Date',
              insert_after='lotus_supplier_confirmed_by',read_only=1),
         dict(fieldname='lotus_revised_delivery_reason',label='Lý do hẹn lại',fieldtype='Small Text',
              insert_after='lotus_revised_delivery_date',read_only=1),
         dict(fieldname='lotus_close_reason',label='Lý do đóng đơn',fieldtype='Small Text',
              insert_after='lotus_revised_delivery_reason',read_only=1),
         dict(fieldname='lotus_cancel_reason',label='Lý do hủy đơn',fieldtype='Small Text',
              insert_after='lotus_close_reason',read_only=1),
    ],'Supplier':[
         dict(fieldname='lotus_supplier_phone',label='Điện thoại liên hệ',fieldtype='Data',
              insert_after='supplier_name'),
         dict(fieldname='lotus_supplier_contact',label='Người liên hệ',fieldtype='Data',
              insert_after='lotus_supplier_phone'),
         dict(fieldname='lotus_supplier_note',label='Ghi chú mua hàng',fieldtype='Small Text',
              insert_after='lotus_supplier_contact'),
    ]}, update=True)


def _po(name, company=None):
    _access()
    doc = frappe.get_doc('Purchase Order', name)
    doc.check_permission('read')
    _company(doc.company)
    if company and doc.company != company:
        frappe.throw('Đơn mua không thuộc công ty hiện tại.')
    return doc


def _date(value, label):
    if not value:
        frappe.throw('Vui lòng chọn ' + label)
    day = getdate(value)
    if day < getdate(nowdate()) and label == 'ngày giao dự kiến':
        frappe.throw('Ngày giao dự kiến không được trước hôm nay.')
    return day


def _lines(company, warehouse, raw, expected_date):
    if isinstance(raw, str):
        raw = frappe.parse_json(raw)
    if not isinstance(raw, list) or not raw or len(raw) > 100:
        frappe.throw('Cần chọn từ 1 đến 100 dòng vật tư.')
    result = []
    for row in raw:
        if not isinstance(row, dict):
            frappe.throw('Dòng vật tư không hợp lệ.')
        item = frappe.get_doc('Item', row.get('item'))
        item.check_permission('read')
        if item.disabled or not item.is_stock_item:
            frappe.throw('Chỉ được mua vật tư kho đang sử dụng.')
        qty = _number(row.get('qty'), 'Số lượng mua')
        unit = row.get('uom') or item.stock_uom
        if unit == item.stock_uom:
            factor = 1
        else:
            conversion = next((u for u in item.uoms if u.uom == unit), None)
            if not conversion or flt(conversion.conversion_factor) <= 0:
                frappe.throw('ĐVT chưa có quy đổi cho ' + item.item_name)
            factor = flt(conversion.conversion_factor)
        price = _number(row.get('rate') or 0, 'Đơn giá', allow_zero=True)
        store = _warehouse(row.get('warehouse') or warehouse, company)
        schedule = _date(row.get('expected_date') or expected_date, 'ngày giao dự kiến')
        source={}
        if row.get('material_request') or row.get('material_request_item'):
            if not row.get('material_request') or not row.get('material_request_item'):
                frappe.throw('Dòng đề nghị mua phải có đủ phiếu và dòng nguồn.')
            doc=frappe.get_doc('Material Request',row['material_request'])
            doc.check_permission('read')
            if doc.company!=company or doc.docstatus!=1 or doc.material_request_type!='Purchase':
                frappe.throw('Chỉ liên kết đề nghị mua được duyệt cùng công ty.')
            original=next((r for r in doc.items if r.name==row['material_request_item']),None)
            if not original or original.item_code!=item.name or original.warehouse!=store.name:
                frappe.throw('Đề nghị mua và vật tư/kho nhận không khớp.')
            remaining=max(0,flt(original.stock_qty)-flt(original.ordered_qty))
            if qty*factor>remaining+0.000001:
                frappe.throw('Số lượng vượt phần đề nghị mua còn lại.')
            source=dict(material_request=doc.name,material_request_item=original.name)
        result.append(dict(**source,item_code=item.name, item_name=item.item_name, qty=qty,
                           uom=unit, stock_uom=item.stock_uom, conversion_factor=factor,
                           rate=price, warehouse=store.name, schedule_date=schedule))
    return result


@frappe.whitelist()
def request_detail(name, company):
    _access()
    _company(company)
    doc=frappe.get_doc('Material Request',name)
    doc.check_permission('read')
    if doc.company!=company or doc.material_request_type!='Purchase' or doc.docstatus!=1:
        frappe.throw('Chỉ được lấy đề nghị mua đã duyệt trong công ty.')
    rows=[]
    for r in doc.items:
        if not r.warehouse:
            continue
        store=_warehouse(r.warehouse,company)
        item=frappe.get_doc('Item',r.item_code)
        item.check_permission('read')
        factor=flt(r.conversion_factor) or 1
        remaining=max(0,flt(r.stock_qty)-flt(r.ordered_qty))
        if remaining<=0:
            continue
        rows.append(dict(item=item.name,qty=remaining/factor,uom=r.uom,
                         warehouse=store.name,rate=0,material_request=doc.name,
                         material_request_item=r.name))
    return dict(name=doc.name,items=rows)


def _requests(company):
    if not frappe.has_permission('Material Request','read'):
        return []
    docs=frappe.get_list('Material Request',
        filters={'company':company,'material_request_type':'Purchase','docstatus':1,
                 'status':['not in',['Stopped','Closed','Cancelled']]},
        fields=['name','schedule_date'],order_by='modified desc',limit_page_length=200)
    return [dict(name=r.name,schedule_date=str(r.schedule_date)) for r in docs]


def _files(name):
    return [dict(name=f.name, file_name=f.file_name, file_url=f.file_url)
            for f in frappe.get_list('File', filters={'attached_to_doctype':'Purchase Order',
                       'attached_to_name':name,'is_private':1},
                       fields=['name','file_name','file_url'], limit_page_length=100)]


@frappe.whitelist()
def setup(company):
    _access()
    _company(company)
    return dict(
        requests=_requests(company),
        suppliers=frappe.get_list('Supplier', filters={'disabled':0},
                                  fields=['name','supplier_name'], order_by='supplier_name asc', limit_page_length=500)
                if frappe.has_permission('Supplier','read') else [],
        warehouses=frappe.get_list('Warehouse', filters={'company':company,'is_group':0,'disabled':0},
                                    fields=['name','warehouse_name'],limit_page_length=0),
        items=frappe.get_list('Item',filters={'is_stock_item':1,'disabled':0},
                              fields=['name','item_name','stock_uom'],order_by='item_name asc',limit_page_length=2000),
        conversions=frappe.get_all('UOM Conversion Detail',fields=['parent','uom','conversion_factor'], filters={'parenttype':'Item'},limit_page_length=0),
        currency=frappe.get_cached_value('Company',company,'default_currency'),
        can_create=frappe.has_permission('Purchase Order','create'),
        can_request=frappe.has_permission('Material Request','create') and frappe.has_permission('Material Request','submit'),
        can_create_supplier=frappe.has_permission('Supplier','create'),
        today=nowdate())


@frappe.whitelist(methods=['POST'])
def create_supplier(company, name):
    _access()
    _company(company)
    if not frappe.has_permission('Supplier','create'):
        frappe.throw('Không có quyền tạo nhà cung cấp.', frappe.PermissionError)
    supplier_name=_text(name, 'Tên nhà cung cấp')[:140]
    existing=frappe.db.get_value('Supplier',{'supplier_name':supplier_name},'name')
    if existing:
        return dict(name=existing,supplier_name=supplier_name)
    group=frappe.db.get_value('Supplier Group',{'name':'Local','is_group':0},'name') or frappe.db.get_value('Supplier Group',{'is_group':0},'name')
    if not group:
        frappe.throw('Cần thiết lập Nhóm nhà cung cấp trong ERPNext.')
    doc=frappe.get_doc(dict(doctype='Supplier',supplier_name=supplier_name,supplier_type='Company',
                            supplier_group=group))
    doc.insert()
    return dict(name=doc.name,supplier_name=doc.supplier_name)


def _payload(company, data):
    _company(company)
    if isinstance(data,str):
        data=frappe.parse_json(data)
    if not isinstance(data,dict):
        frappe.throw('Dữ liệu đơn mua không hợp lệ.')
    mode=data.get('mode') or MODES[0]
    if mode not in MODES:
        frappe.throw('Cách mua hàng không hợp lệ.')
    supplier=frappe.get_doc('Supplier', data.get('supplier'))
    supplier.check_permission('read')
    if supplier.disabled:
        frappe.throw('NCC không còn hoạt động.')
    warehouse=_warehouse(data.get('warehouse'),company).name
    expected=_date(data.get('expected_date'), 'ngày giao dự kiến')
    lines=_lines(company,warehouse,data.get('items'),expected)
    return dict(mode=mode,supplier=supplier.name,warehouse=warehouse,expected=expected,
                lines=lines,notes=str(data.get('notes') or '')[:500])


@frappe.whitelist(methods=['POST'])
def save_order(company, data, name=None, modified=None):
    _access()
    _company(company)
    info=_payload(company,data)
    if name:
        doc=_po(name, company)
        doc.check_permission('write')
        if doc.get('lotus_approval_status') not in ('',None,'Nháp','Từ chối'):
            frappe.throw('Đơn đang chờ duyệt, không được sửa.')
        if doc.docstatus!=0 or str(doc.modified)!=str(modified):
            frappe.throw('Đơn mua đã thay đổi hoặc không còn là bản nháp. Tải lại trước khi sửa.')
        doc.supplier=info['supplier']
        doc.transaction_date=getdate(nowdate())
    else:
        if not frappe.has_permission('Purchase Order','create'):
            frappe.throw('Không có quyền lập đơn mua.',frappe.PermissionError)
        doc=frappe.new_doc('Purchase Order')
        doc.company=company
        doc.supplier=info['supplier']
        doc.transaction_date=getdate(nowdate())
        doc.currency=frappe.get_cached_value('Company',company,'default_currency')
        doc.lotus_approval_status='Nháp'
    doc.schedule_date=info['expected']
    doc.lotus_purchase_mode=info['mode']
    doc.lotus_delivery_note=info['notes']
    doc.set('items',info['lines'])
    if name:
        doc.save()
    else:
        doc.insert()
    return dict(name=doc.name,modified=str(doc.modified),docstatus=doc.docstatus)


def _state(doc):
    if doc.docstatus==2:
        return 'Đã hủy'
    if doc.docstatus==0:
        return doc.get('lotus_approval_status') or 'Nháp' 
    if doc.status in DONE:
        return 'Đã đóng'
    relevant=[r for r in doc.items if flt(r.qty)>0]
    pending=[r for r in relevant if flt(r.qty) - flt(r.received_qty)>0.000001]
    if not pending:
        return 'Đã nhận đủ'
    eta=doc.get('lotus_revised_delivery_date')
    if (getdate(eta) < getdate(nowdate()) if eta else
            any(getdate(r.schedule_date)<getdate(nowdate()) for r in pending)):
        return 'Quá hẹn'
    if any(flt(r.received_qty)>0 for r in relevant):
        return 'Về một phần'
    return 'Chờ hàng'


def _summary(doc):
    status=_state(doc)
    pending=[r for r in doc.items if flt(r.qty)-flt(r.received_qty)>0.000001]
    day=min((getdate(r.schedule_date) for r in pending),default=getdate(doc.schedule_date or doc.transaction_date))
    names={r.warehouse for r in doc.items if r.warehouse}
    return dict(name=doc.name,supplier=doc.supplier,supplier_name=doc.supplier_name or doc.supplier,
                warehouse=', '.join(sorted(names)),expected_date=str(day),
                mode=doc.get('lotus_purchase_mode') or MODES[0],status=status,
                docstatus=doc.docstatus,lines=len(doc.items),
                remaining_lines=len(pending),modified=str(doc.modified))


@frappe.whitelist()
def orders(company, warehouse=None, search=None, status=None, start=0, column_filters=None, sort_model=None):
    from lotus_farm.table_filters import selections,matches,faceted_distinct,sorted_rows
    _access()
    _company(company)
    if warehouse:
        _warehouse(warehouse,company)
    docs=frappe.get_list('Purchase Order',filters={'company':company},
                         fields=['name'],limit_page_length=0,order_by='modified desc')
    rows=[]
    for r in docs:
        doc=_po(r.name,company)
        if warehouse and not any(x.warehouse==warehouse for x in doc.items):
            continue
        rows.append(_summary(doc))
    query=str(search or '').strip().casefold()[:100]
    if query:
        rows=[r for r in rows if query in ' '.join(str(r[k]) for k in
            ('name','supplier','supplier_name','warehouse','mode','status')).casefold()]
    if status=='pending':
        rows=[r for r in rows if r['status'] in ('Chờ hàng','Về một phần','Quá hẹn')]
    elif status:
        rows=[r for r in rows if r['status']==status]
    fields=['name','supplier_name','mode','warehouse','expected_date','status']
    selected=selections(column_filters,fields)
    choices=faceted_distinct(rows,fields,selected)
    filtered=[r for r in rows if matches(r,selected)]
    filtered=sorted_rows(filtered,sort_model,fields)
    start=max(0,cint(start))
    return dict(rows=filtered[start:start+50],total_count=len(filtered),
                has_more=len(filtered)>start+50,filter_values=choices)


@frappe.whitelist()
def order_detail(name):
    doc=_po(name)
    currency=frappe.get_cached_value('Company',doc.company,'default_currency')
    from lotus_farm.purchasing import can_approve
    return dict(**_summary(doc),company=doc.company,notes=doc.get('lotus_delivery_note') or '',
                can_submit=can_approve(doc),
                can_write=doc.docstatus==0 and doc.has_permission('write'),
                can_receive=doc.docstatus==1 and frappe.has_permission('Purchase Receipt','create'),
                currency=currency,quote_files=_files(doc.name),
                items=[dict(line=r.name,item=r.item_code,item_name=r.item_name,
                            warehouse=r.warehouse,qty=flt(r.qty),received_qty=flt(r.received_qty),
                            remaining_qty=max(0,flt(r.qty)-flt(r.received_qty)),
                            uom=r.uom,stock_uom=r.stock_uom,conversion_factor=flt(r.conversion_factor) or 1,
                            rate=flt(r.rate),expected_date=str(r.schedule_date),
                            material_request=r.material_request or '',
                            material_request_item=r.material_request_item or '') for r in doc.items])


@frappe.whitelist()
def order_receipts(name):
    """Receipt status is always read from actual ERPNext Purchase Receipts."""
    order=_po(name)
    references=frappe.get_all('Purchase Receipt Item',
        filters={'purchase_order':order.name},pluck='parent',limit_page_length=0)
    results=[]
    from lotus_farm.warehouse_planning import _purchase_doc
    for receipt_name in sorted(set(references),reverse=True):
        receipt=_purchase_doc('Purchase Receipt',receipt_name)
        results.append(dict(name=receipt.name,date=str(receipt.posting_date),
            status={0:'Nháp',1:'Đã ghi sổ',2:'Đã hủy'}.get(receipt.docstatus),
            docstatus=receipt.docstatus,modified=str(receipt.modified),
            can_cancel=receipt.docstatus==1 and receipt.has_permission('cancel')))
    return results


@frappe.whitelist(methods=['POST'])
def submit_order(name,modified):
    from lotus_farm.controls import lock
    doc=_po(name)
    doc.check_permission('submit')
    from lotus_farm.purchasing import can_approve
    if not can_approve(doc):
        frappe.throw('Chỉ người duyệt khác người lập mới được xác nhận đơn đã trình duyệt.',frappe.PermissionError)
    lock('Company',doc.company)
    lock('Purchase Order',name)
    doc.reload()
    if doc.docstatus!=0 or str(doc.modified)!=str(modified):
        frappe.throw('Đơn mua đã thay đổi. Tải lại để kiểm tra.')
    if not can_approve(doc):
        frappe.throw('Đơn không còn đủ điều kiện duyệt.',frappe.PermissionError)
    if any(flt(r.rate)<=0 for r in doc.items):
        frappe.throw('Cần xác nhận đơn giá theo báo giá trước khi xác nhận đặt hàng.')
    doc.lotus_approved_by=frappe.session.user
    doc.lotus_approved_at=__import__('frappe.utils',fromlist=['now_datetime']).now_datetime()
    doc.submit()
    return dict(name=doc.name,status=_state(doc))


@frappe.whitelist(methods=['POST'])
def delete_draft(name,modified):
    from lotus_farm.controls import lock
    doc=_po(name)
    doc.check_permission('delete')
    lock('Purchase Order',name)
    doc.reload()
    if doc.docstatus!=0 or str(doc.modified)!=str(modified):
        frappe.throw('Chỉ có thể xóa đơn mua nháp chưa bị sửa.')
    frappe.delete_doc(doc.doctype,doc.name)
    return dict(name=name,deleted=True)