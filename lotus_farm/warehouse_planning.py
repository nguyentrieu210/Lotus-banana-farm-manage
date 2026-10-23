"""One permission-scoped material coverage view for warehouse and farm screens."""
from collections import defaultdict
import hashlib
import json
import frappe
from frappe.utils import flt, getdate, nowdate, cint
from lotus_farm.warehouse_rules import coverage


def install_fields():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    create_custom_fields({
        'Company':[dict(fieldname='lotus_print_farm',label='Nông trường trên phiếu in',fieldtype='Data'),
                   dict(fieldname='lotus_print_project',label='Vườn chuối trên phiếu in',fieldtype='Data')],
        'Material Requirement':[dict(fieldname='lotus_warehouse',label='Kho cấp vật tư',fieldtype='Link',options='Warehouse',allow_on_submit=1)],
        'Material Request Item':[
            dict(fieldname='lotus_requirement',label='Nhu cầu kế hoạch gốc',fieldtype='Link',options='Material Requirement'),
            dict(fieldname='lotus_requirement_line',label='Dòng nhu cầu gốc',fieldtype='Data')],
        **{dt:[dict(fieldname='lotus_client_key',label='Lotus request key',fieldtype='Data',hidden=1,read_only=1,no_copy=1,unique=1),
               dict(fieldname='lotus_payload_hash',label='Lotus request content',fieldtype='Data',hidden=1,read_only=1,no_copy=1)]
           for dt in ('Stock Entry','Stock Reconciliation','Purchase Receipt')}
    },update=True,ignore_validate=True)


def stock_quantity(item,uom,qty):
    if not uom or uom==item.stock_uom:return flt(qty)
    from erpnext.stock.get_item_details import get_conversion_factor
    factor=flt(get_conversion_factor(item.name,uom).get('conversion_factor'))
    if factor<=0:frappe.throw('Chưa có quy đổi đơn vị cho '+item.name)
    return flt(qty)*factor


def validate_requirement_warehouse(doc,method=None):
    store=doc.get('lotus_warehouse')
    if not store:return
    from lotus_farm.warehouse import _warehouse
    _warehouse(store,doc.company)
    before=doc.get_doc_before_save()
    if before and before.docstatus==1 and before.get('lotus_warehouse')!=store:
        if any(sum(source_allocations('Material Requirement',doc.name,r.name).values()) for r in doc.lines):
            frappe.throw('Xử lý phiếu cấp trước khi đổi kho của nhu cầu đã duyệt.')


def validate_request_lineage(doc,method=None):
    from lotus_farm.warehouse_issue import source_line
    for row in doc.items:
        if not row.get('lotus_requirement') and not row.get('lotus_requirement_line'):continue
        if doc.material_request_type!='Material Issue' or not row.get('lotus_requirement') or not row.get('lotus_requirement_line'):
            frappe.throw('Nguồn kế hoạch chỉ gắn trên dòng yêu cầu cấp có đủ nhu cầu và dòng gốc.')
        info=source_line('Material Requirement',row.lotus_requirement,row.lotus_requirement_line,doc.company)
        if info['item']!=row.item_code:frappe.throw('Vật tư không khớp nhu cầu kế hoạch gốc.')
        if info.get('warehouse') and info['warehouse']!=row.warehouse:frappe.throw('Kho không khớp nhu cầu gốc.')


def source_allocations(kind,name,line):
    from lotus_farm.warehouse_issue import allocation_totals
    return allocation_totals(kind,name,line)


def _sources(company,from_date,to_date,farm=None):
    sources=[];warnings=[]
    for dt in ('Material Requirement','Material Request'):
        if not frappe.has_permission(dt,'read'):
            warnings.append('Chưa có quyền đọc '+dt+'. Nhu cầu chưa đầy đủ.');continue
        filters={'company':company,'docstatus':1}
        if dt=='Material Requirement':
            filters['posting_date']=['between',[from_date,to_date]]
            if farm:filters['farm']=farm
        else:
            filters.update(material_request_type='Material Issue',status=['not in',['Stopped','Closed','Cancelled']])
        for name in frappe.get_list(dt,filters=filters,pluck='name',limit_page_length=0):
            doc=frappe.get_doc(dt,name);doc.check_permission('read')
            if dt=='Material Requirement':
                plan=frappe.get_doc('Daily Work Plan',doc.work_plan);plan.check_permission('read')
                if plan.docstatus!=1:continue
                mapping=[]
                if not doc.get('lotus_warehouse') and frappe.has_permission('Warehouse Mapping','read'):
                    mapping=frappe.get_list('Warehouse Mapping',filters={'farm':doc.farm,'enabled':1,'warehouse_role':'Field Store'},pluck='warehouse',limit_page_length=0)
                assigned=doc.get('lotus_warehouse') or (mapping[0] if len(set(mapping))==1 else '')
            for row in doc.lines if dt=='Material Requirement' else doc.items:
                if dt=='Material Request' and row.get('lotus_requirement'):
                    # Linked release requests are another view of the canonical plan demand.
                    continue
                date=doc.posting_date if dt=='Material Requirement' else row.schedule_date or doc.schedule_date or doc.transaction_date
                if not from_date<=getdate(date)<=to_date:continue
                if farm and dt=='Material Request':continue # No farm provenance: do not assign it to a farm by guessing.
                code=row.item if dt=='Material Requirement' else row.item_code
                item=frappe.get_doc('Item',code);item.check_permission('read')
                required=stock_quantity(item,row.uom,row.required_qty) if dt=='Material Requirement' else flt(row.stock_qty)
                amounts=source_allocations(dt,doc.name,row.name)
                sources.append(dict(doctype=dt,name=doc.name,line=row.name,item=code,item_name=item.item_name,uom=item.stock_uom,
                    warehouse=assigned if dt=='Material Requirement' else row.warehouse or '',date=str(date),
                    farm=doc.get('farm') or '',area=' / '.join(filter(None,[doc.get('farm_block'),doc.get('farm_plot')])) if dt=='Material Requirement' else row.get('lotus_usage_area') or '',
                    work_plan=doc.get('work_plan') or '',required_qty=required,issued_qty=amounts['posted'],draft_qty=amounts['draft'],
                    remaining_qty=max(0,required-amounts['posted']),can_assign=dt=='Material Requirement' and doc.has_permission('write')))
    if frappe.has_permission('Daily Work Plan','read') and frappe.has_permission('Material Requirement','read'):
        filters={'company':company,'docstatus':1,'posting_date':['between',[from_date,to_date]]}
        if farm:filters['farm']=farm
        approved_requirements=frappe.get_list('Material Requirement',filters={'company':company,'docstatus':1,'posting_date':['between',[from_date,to_date]]},fields=['work_plan_line'],limit_page_length=0)
        approved_plan_lines={r.work_plan_line for r in approved_requirements}
        for name in frappe.get_list('Daily Work Plan',filters=filters,pluck='name',limit_page_length=0):
            plan=frappe.get_doc('Daily Work Plan',name)
            if any(r.norm_profile and r.name not in approved_plan_lines for r in plan.lines):
                warnings.append('Kế hoạch '+name+' còn dòng chưa có nhu cầu vật tư đã duyệt.')
    return sources,warnings


def _draft_holds(company,warehouses):
    # Aggregate quantities only. Hidden drafts must also hold stock, without leaking document names.
    rows=frappe.db.sql('''select d.item_code,d.s_warehouse warehouse,sum(d.qty*d.conversion_factor) qty
        from `tabStock Entry Detail` d join `tabStock Entry` p on p.name=d.parent
        where p.company=%(company)s and p.docstatus=0 and d.s_warehouse in %(warehouses)s
        group by d.item_code,d.s_warehouse''',
        {'company':company,'warehouses':tuple(warehouses) or ('__none__',)},as_dict=True)
    return {(r.item_code,r.warehouse):flt(r.qty) for r in rows}


def _supply(company,warehouses,to_date):
    incoming=defaultdict(float);requested=defaultdict(float);late=defaultdict(float);warnings=[];orders=[];requests=[]
    for dt in ('Purchase Order','Material Request'):
        if not frappe.has_permission(dt,'read'):
            warnings.append('Chưa có quyền đọc '+dt+'. Chưa xác định đủ phần chờ nhập/đã đề nghị.');continue
        filters={'company':company,'docstatus':1 if dt=='Purchase Order' else ['<',2],
                 'status':['not in',['Closed','Stopped','Cancelled','Completed']]}
        if dt=='Material Request':filters['material_request_type']='Purchase'
        for name in frappe.get_list(dt,filters=filters,pluck='name',limit_page_length=0):
            doc=frappe.get_doc(dt,name);doc.check_permission('read')
            for row in doc.items:
                if row.warehouse not in warehouses:continue
                item=frappe.get_doc('Item',row.item_code);item.check_permission('read')
                factor=flt(row.conversion_factor) or 1
                remaining=max(0,flt(row.stock_qty)-(flt(row.received_qty)*factor if dt=='Purchase Order' else flt(row.ordered_qty)))
                if not remaining:continue
                date=getdate(row.schedule_date or doc.schedule_date or doc.transaction_date)
                key=(row.item_code,row.warehouse)
                if dt=='Purchase Order':
                    if date<=to_date:incoming[key]+=remaining
                    else:late[key]+=remaining
                    orders.append(dict(name=doc.name,item=row.item_code,item_name=item.item_name,warehouse=row.warehouse,
                        uom=item.stock_uom,qty=remaining,date=str(date),overdue=date<getdate(nowdate()),supplier=doc.supplier))
                elif date<=to_date:
                    requested[key]+=remaining
                    requests.append(dict(name=doc.name,item=row.item_code,item_name=item.item_name,warehouse=row.warehouse,uom=item.stock_uom,qty=remaining,date=str(date),docstatus=doc.docstatus,status='Nháp' if doc.docstatus==0 else 'Đã duyệt'))
    # Like Bin projected quantities, aggregate commitments for permitted
    # warehouses even when another user's individual document is hidden.
    # Names/suppliers above remain strictly permission-scoped.
    for dt,field in (('Purchase Order','received_qty'),('Material Request','ordered_qty')):
        if not frappe.has_permission(dt,'read'):continue
        condition="p.docstatus=1" if dt=='Purchase Order' else "p.docstatus<2 and p.material_request_type='Purchase'"
        totals=frappe.db.sql(f'''select d.item_code,d.warehouse,
            sum(case when coalesce(d.schedule_date,p.schedule_date,p.transaction_date)<=%(end)s
                then greatest(d.stock_qty-coalesce(d.`{field}`,0)*{'d.conversion_factor' if dt=='Purchase Order' else '1'},0) else 0 end) qty,
            sum(case when coalesce(d.schedule_date,p.schedule_date,p.transaction_date)>%(end)s
                then greatest(d.stock_qty-coalesce(d.`{field}`,0)*{'d.conversion_factor' if dt=='Purchase Order' else '1'},0) else 0 end) later_qty
            from `tab{dt} Item` d join `tab{dt}` p on p.name=d.parent
            where p.company=%(company)s and {condition}
            and p.status not in ('Closed','Stopped','Cancelled','Completed')
            and d.warehouse in %(warehouses)s group by d.item_code,d.warehouse''',
            dict(company=company,end=to_date,warehouses=tuple(warehouses) or ('__none__',)),as_dict=True)
        if dt=='Purchase Order':
            incoming=defaultdict(float,{(r.item_code,r.warehouse):flt(r.qty) for r in totals})
            late=defaultdict(float,{(r.item_code,r.warehouse):flt(r.later_qty) for r in totals})
        else:requested=defaultdict(float,{(r.item_code,r.warehouse):flt(r.qty) for r in totals})
    return incoming,requested,late,warnings,orders,requests


def snapshot(company,warehouse=None,from_date=None,to_date=None,farm=None,include_stock=False):
    from lotus_farm.warehouse import _access,_company,_warehouse
    _access();_company(company)
    begin=getdate(from_date or nowdate());end=getdate(to_date or begin)
    if begin>end:frappe.throw('Từ ngày phải trước hoặc bằng đến ngày.')
    stores=frappe.get_list('Warehouse',filters={'company':company,'is_group':0,'disabled':0},fields=['name','warehouse_name'],limit_page_length=0)
    names={r.name for r in stores}
    if warehouse:_warehouse(warehouse,company);names &= {warehouse}
    if farm:
        doc=frappe.get_doc('Farm',farm);doc.check_permission('read')
        if doc.company!=company:frappe.throw('Nông trường không thuộc công ty.')
    sources,warnings=_sources(company,begin,end,farm)
    unmapped=[r for r in sources if not r['warehouse']]
    # A warehouse restriction never exposes demand assigned to another/inaccessible warehouse.
    sources=[r for r in sources if r['warehouse'] in names]
    holds=_draft_holds(company,names)
    incoming,requested,late,supply_warnings,orders,requests=_supply(company,names,end)
    warnings+=supply_warnings
    bins=frappe.get_list('Bin',filters={'warehouse':['in',list(names) or ['__none__']]},fields=['item_code','warehouse','actual_qty','reserved_stock'],limit_page_length=0)
    balances={(r.item_code,r.warehouse):r for r in bins}
    grouped={}
    for r in sources:
        key=(r['item'],r['warehouse'])
        bucket=grouped.setdefault(key,dict(item=r['item'],item_name=r['item_name'],uom=r['uom'],warehouse=r['warehouse'],sources=[],required=0,issued=0,own_drafts=0))
        bucket['required']+=r['required_qty'];bucket['issued']+=min(r['issued_qty'],r['required_qty']);bucket['own_drafts']+=r['draft_qty'];bucket['sources'].append(r)
    rows=[]
    if include_stock:
        labels={r.name:r for r in frappe.get_list('Item',fields=['name','item_name','stock_uom'],limit_page_length=0)}
        for key in set(balances)|set(holds)|set(incoming)|set(requested):
            if key[0] in labels:
                item=labels[key[0]]
                grouped.setdefault(key,dict(item=item.name,item_name=item.item_name,uom=item.stock_uom,warehouse=key[1],sources=[],required=0,issued=0,own_drafts=0))
    for key,b in grouped.items():
        balance=balances.get(key,{})
        result=coverage(b.pop('required'),b.pop('issued'),flt(balance.get('actual_qty')),flt(balance.get('reserved_stock')),holds.get(key,0),b.pop('own_drafts'),incoming[key],requested[key])
        result.update(b);result['name']=key[0]+' @ '+key[1];result['later_incoming_qty']=late[key]
        if warnings:result['status']='Chưa đủ dữ liệu';result['to_buy_qty']=None;result['to_request_qty']=None
        rows.append(result)
    return dict(rows=rows,sources=sources,unmapped=unmapped,warnings=warnings,orders=orders,requests=requests,from_date=str(begin),to_date=str(end),warehouses=stores)


@frappe.whitelist()
def overview(company,warehouse=None,from_date=None,to_date=None,search=None,start=0,column_filters=None,sort_model=None):
    from lotus_farm.table_filters import selections,matches,faceted_distinct
    result=snapshot(company,warehouse,from_date,to_date)
    rows=result['rows'];query=str(search or '').casefold()[:100]
    if query:rows=[r for r in rows if query in (r['item']+' '+r['item_name']).casefold()]
    fields=['item','warehouse','uom','required_qty','issued_qty','remaining_qty','available_qty','shortage_qty','incoming_qty','requested_qty','to_buy_qty','to_request_qty','status']
    selected=selections(column_filters,fields)
    result['filter_values']=faceted_distinct(rows,fields,selected,labels={'item':lambda r:r['item_name']+' · '+r['item']})
    rows=[r for r in rows if matches(r,selected)]
    from lotus_farm.table_filters import sorted_rows
    rows=sorted_rows(rows,sort_model,fields,{'item':'item_name'})
    start=max(0,cint(start));result.update(rows=rows[start:start+50],total_count=len(rows),has_more=len(rows)>start+50)
    result['can_request']=frappe.has_permission('Material Request','create') and not result['warnings']
    return result


@frappe.whitelist(methods=['POST'])
def assign_warehouse(company,requirement,warehouse):
    from lotus_farm.warehouse import _access,_company,_warehouse
    from lotus_farm.controls import lock
    from lotus_farm.daily_operations import day_guard
    _access();_company(company);_warehouse(warehouse,company)
    lock('Material Requirement',requirement)
    doc=frappe.get_doc('Material Requirement',requirement);doc.check_permission('write');day_guard(doc)
    if doc.company!=company or doc.docstatus!=1:frappe.throw('Chọn nhu cầu đã duyệt thuộc công ty.')
    if any(sum(source_allocations('Material Requirement',doc.name,r.name).values()) for r in doc.lines):
        frappe.throw('Nhu cầu đã lập phiếu cấp. Xử lý phiếu cấp trước khi đổi kho.')
    doc.lotus_warehouse=warehouse;doc.save()
    return dict(name=doc.name,warehouse=warehouse)


@frappe.whitelist(methods=['POST'])
def create_purchase_request(company,warehouse,from_date,to_date,items):
    from lotus_farm.warehouse import _access,_company,_warehouse
    from lotus_farm.controls import lock
    _access();_company(company);_warehouse(warehouse,company)
    if getdate(to_date)<getdate(nowdate()):frappe.throw('Kỳ nhu cầu đã kết thúc. Chọn kỳ hiện tại để lập đề nghị mua cho nhu cầu còn thiếu.')
    if not frappe.has_permission('Material Request','create'):frappe.throw('Chưa có quyền tạo đề nghị mua.',frappe.PermissionError)
    selected=frappe.parse_json(items)
    if not isinstance(selected,list) or not selected or len(selected)>100:frappe.throw('Chọn từ 1 đến 100 vật tư.')
    lock('Company',company)
    result=snapshot(company,warehouse,from_date,to_date)
    if result['warnings'] or result['unmapped']:frappe.throw('Xác định kho và quyền đọc nguồn trước khi tạo đề nghị mua.')
    rows=[r for r in result['rows'] if r['item'] in selected and (r['to_request_qty'] or 0)>0]
    if not rows:return dict(name=None,note='Phần thiếu đã có đề nghị mua hoặc đã đủ hàng. Không tạo thêm phiếu.')
    doc=frappe.get_doc(dict(doctype='Material Request',company=company,material_request_type='Purchase',
        transaction_date=nowdate(),schedule_date=max(getdate(to_date),getdate(nowdate())),
        items=[dict(item_code=r['item'],qty=r['to_request_qty'],uom=r['uom'],stock_uom=r['uom'],conversion_factor=1,
            warehouse=warehouse,schedule_date=max(getdate(to_date),getdate(nowdate())),description='Nhu cầu kho '+str(from_date)+' → '+str(to_date)) for r in rows])).insert()
    return dict(name=doc.name,doctype=doc.doctype,docstatus=doc.docstatus)


@frappe.whitelist()
def purchase_request(name):
    from lotus_farm.warehouse import _access,_company
    _access()
    doc=frappe.get_doc('Material Request',name);doc.check_permission('read');_company(doc.company)
    if doc.material_request_type!='Purchase':frappe.throw('Chọn đề nghị mua vật tư.')
    for row in doc.items:
        frappe.get_doc('Item',row.item_code).check_permission('read')
        if row.warehouse:frappe.get_doc('Warehouse',row.warehouse).check_permission('read')
    return dict(name=doc.name,company=doc.company,docstatus=doc.docstatus,modified=str(doc.modified),
        can_submit=doc.docstatus==0 and doc.has_permission('submit'),can_delete=doc.docstatus==0 and doc.has_permission('delete'),
        items=[dict(item=r.item_code,item_name=r.item_name,qty=r.qty,uom=r.uom,warehouse=r.warehouse,date=str(r.schedule_date)) for r in doc.items])


@frappe.whitelist(methods=['POST'])
def purchase_action(name,modified,action):
    from lotus_farm.controls import lock
    lock('Material Request',name)
    info=purchase_request(name)
    if info['modified']!=modified:frappe.throw('Đề nghị mua đã thay đổi. Mở lại để kiểm tra.')
    if info['docstatus']!=0:frappe.throw('Chỉ xử lý đề nghị mua nháp tại đây.')
    doc=frappe.get_doc('Material Request',name)
    if action=='submit':doc.check_permission('submit');doc.submit()
    elif action=='delete':doc.check_permission('delete');frappe.delete_doc(doc.doctype,doc.name)
    else:frappe.throw('Thao tác không hợp lệ.')
    return dict(name=name,action=action)


def _purchase_doc(doctype,name):
    from lotus_farm.warehouse import _access,_company
    _access()
    doc=frappe.get_doc(doctype,name);doc.check_permission('read');_company(doc.company)
    for row in doc.items:
        frappe.get_doc('Item',row.item_code).check_permission('read')
        if row.warehouse:frappe.get_doc('Warehouse',row.warehouse).check_permission('read')
    return doc


@frappe.whitelist()
def purchase_order(name):
    doc=_purchase_doc('Purchase Order',name)
    if doc.docstatus!=1 or doc.status in ('Closed','Cancelled','Stopped'):frappe.throw('Đơn mua chưa duyệt hoặc đã đóng.')
    holds=frappe.db.sql('''select d.purchase_order_item line,sum(d.stock_qty) qty
        from `tabPurchase Receipt Item` d join `tabPurchase Receipt` p on p.name=d.parent
        where d.purchase_order=%s and p.docstatus=0 and p.is_return=0 group by d.purchase_order_item''',doc.name,as_dict=True)
    held={r.line:flt(r.qty) for r in holds}
    return dict(name=doc.name,company=doc.company,supplier=doc.supplier,currency=doc.currency,
        can_receive=frappe.has_permission('Purchase Receipt','create'),
        items=[dict(line=r.name,item=r.item_code,item_name=r.item_name,warehouse=r.warehouse,
            ordered_qty=flt(r.stock_qty),received_qty=flt(r.received_qty)*flt(r.conversion_factor),
            draft_qty=held.get(r.name,0),remaining_qty=max(0,flt(r.stock_qty)-flt(r.received_qty)*flt(r.conversion_factor)-held.get(r.name,0)),
            uom=r.stock_uom,date=str(r.schedule_date)) for r in doc.items])


@frappe.whitelist(methods=['POST'])
def receive_order(name,posting_date,quantities,client_event_id):
    from lotus_farm.controls import lock
    from lotus_farm.warehouse import _number,_text,_warehouse
    from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt
    original=_purchase_doc('Purchase Order',name)
    if getdate(posting_date)<getdate(original.transaction_date):frappe.throw('Ngày nhận không được trước ngày đơn mua.')
    if not frappe.has_permission('Purchase Receipt','create'):frappe.throw('Chưa có quyền lập phiếu nhận hàng.',frappe.PermissionError)
    selected=frappe.parse_json(quantities)
    if not isinstance(selected,dict) or not selected or len(selected)>100:frappe.throw('Chọn từ 1 đến 100 dòng nhận hàng.')
    selected={line:_number(qty,'Số thực nhận') for line,qty in selected.items()}
    event=_text(client_event_id,'Mã yêu cầu')
    key=hashlib.sha256((frappe.session.user+':'+event).encode()).hexdigest()
    digest=hashlib.sha256(json.dumps(dict(order=name,date=str(posting_date),quantities=selected),sort_keys=True).encode()).hexdigest()
    lock('Company',original.company);lock('Purchase Order',name)
    existing=frappe.db.get_value('Purchase Receipt',{'lotus_client_key':key},['name','lotus_payload_hash'],as_dict=True)
    if existing:
        _purchase_doc('Purchase Receipt',existing.name)
        if existing.lotus_payload_hash!=digest:frappe.throw('Yêu cầu này đã tạo phiếu '+existing.name+'. Mở lại để kiểm tra.')
        return dict(name=existing.name)
    info=purchase_order(name)
    available={r['line']:r for r in info['items']}
    for line,qty in selected.items():
        if line not in available or qty>available[line]['remaining_qty']+0.000001:frappe.throw('Lượng nhận vượt phần còn nhận hoặc đang giữ trên phiếu nháp.')
        row=available[line]
        item=frappe.get_doc('Item',row['item'])
        if item.is_stock_item:_warehouse(row['warehouse'],original.company)
        if item.has_batch_no or item.has_serial_no:frappe.throw('Nhận theo lô/serial cần quy trình nhận hàng chuyên dụng.')
    doc=make_purchase_receipt(name)
    kept=[]
    for row in doc.items:
        if row.purchase_order_item not in selected:continue
        factor=flt(row.conversion_factor)
        if factor<=0:frappe.throw('Đơn mua thiếu quy đổi đơn vị.')
        row.qty=selected[row.purchase_order_item]/factor
        row.received_qty=row.qty;row.rejected_qty=0;row.stock_qty=selected[row.purchase_order_item]
        source=next(r for r in original.items if r.name==row.purchase_order_item)
        ratio=flt(row.qty)/flt(source.qty)
        row.lotus_line_freight=flt(source.get('lotus_line_freight'))*ratio
        item=frappe.get_cached_doc('Item',row.item_code)
        if item.is_fixed_asset:
            if abs(flt(row.qty)-round(flt(row.qty)))>0.000001 or factor!=1:
                frappe.throw('Tài sản nhận theo từng chiếc, quy đổi bằng 1.')
            for _ in range(round(flt(row.qty))):
                piece=frappe._dict(row.as_dict())
                piece.pop('name',None)
                piece.update(qty=1,received_qty=1,stock_qty=1,lotus_line_freight=flt(row.lotus_line_freight)/flt(row.qty))
                kept.append(piece)
        else:kept.append(row)
    if {r.get('purchase_order_item') for r in kept}!=set(selected):frappe.throw('Dòng đơn mua không còn hợp lệ. Mở lại đơn mua.')
    doc.set('items',kept);doc.posting_date=getdate(posting_date);doc.set_posting_time=1
    from lotus_farm.procurement import apply_line_taxes
    apply_line_taxes(doc)
    doc.lotus_client_key=key;doc.lotus_payload_hash=digest
    doc.insert()
    return dict(name=doc.name)


@frappe.whitelist()
def purchase_receipt(name):
    doc=_purchase_doc('Purchase Receipt',name)
    return dict(name=doc.name,doctype=doc.doctype,company=doc.company,supplier=doc.supplier,currency=frappe.get_cached_value('Company',doc.company,'default_currency'),docstatus=doc.docstatus,
        modified=str(doc.modified),can_submit=doc.docstatus==0 and doc.has_permission('submit'),can_delete=doc.docstatus==0 and doc.has_permission('delete'),
        items=[dict(item=r.item_code,item_name=r.item_name,qty=r.stock_qty,uom=r.stock_uom,warehouse=r.warehouse,
            purchase_order=r.purchase_order,rate=r.valuation_rate,amount=flt(r.stock_qty)*flt(r.valuation_rate),date=str(doc.posting_date)) for r in doc.items])


@frappe.whitelist(methods=['POST'])
def receipt_action(name,modified,action):
    from lotus_farm.controls import lock
    doc=_purchase_doc('Purchase Receipt',name)
    lock('Company',doc.company)
    for order in sorted({r.purchase_order for r in doc.items if r.purchase_order}):lock('Purchase Order',order)
    lock('Purchase Receipt',name);doc.reload()
    if str(doc.modified)!=modified:
        frappe.throw('Phiếu đã thay đổi hoặc không hợp lệ. Tải lại trước khi thao tác.')
    if action=='cancel':
        if doc.docstatus!=1:
            frappe.throw('Chỉ được hủy phiếu đã ghi sổ.')
        doc.check_permission('cancel')
        doc.cancel()  # ERPNext reverses Stock Ledger and recalculates PO received_qty
        return dict(name=name,action='cancel')
    if doc.docstatus!=0:
        frappe.throw('Phiếu nhận không còn là bản nháp.')
    if action=='submit':
        doc.check_permission('submit')
        if doc.is_return:
            doc.submit()  # Native return validation and ledger reversal; no second stock document.
            return dict(name=name,action=action)
        from lotus_farm.warehouse import _warehouse
        for row in doc.items:
            if frappe.get_cached_value('Item',row.item_code,'is_stock_item'):_warehouse(row.warehouse,doc.company)
        # Keep the same no-overreceipt rule at posting, after reloading the order.
        totals=defaultdict(float)
        for row in doc.items:
            if not row.purchase_order or not row.purchase_order_item:frappe.throw('Phiếu nhận thiếu nguồn đơn mua.')
            totals[(row.purchase_order,row.purchase_order_item)]+=flt(row.stock_qty)
        for (order,line),qty in totals.items():
            source=_purchase_doc('Purchase Order',order)
            if source.docstatus!=1 or source.status in ('Closed','Cancelled','Stopped'):frappe.throw('Đơn mua đã dừng hoặc đóng.')
            original=next((r for r in source.items if r.name==line),None)
            if not original or qty>flt(original.stock_qty)-flt(original.received_qty)*flt(original.conversion_factor)+0.000001:
                frappe.throw('Lượng nhận vượt phần còn lại của đơn mua.')
        doc.submit()
    elif action=='delete':doc.check_permission('delete');frappe.delete_doc(doc.doctype,doc.name)
    else:frappe.throw('Thao tác không hợp lệ.')
    return dict(name=name,action=action)
