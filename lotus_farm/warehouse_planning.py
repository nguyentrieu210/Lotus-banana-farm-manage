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
            warnings.append('Chưa có quyền đọc '+dt+'. Chưa xác định đủ phần chờ nhập/đã đề xuất.');continue
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
def overview(company,warehouse=None,from_date=None,to_date=None,search=None,start=0,column_filters=None,sort_model=None,length=50):
    length=max(1,min(cint(length) or 50,100))
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
    start=max(0,cint(start));result.update(rows=rows[start:start+length],total_count=len(rows),has_more=len(rows)>start+length)
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
    if getdate(to_date)<getdate(nowdate()):frappe.throw('Kỳ nhu cầu đã kết thúc. Chọn kỳ hiện tại để lập đề xuất mua cho nhu cầu còn thiếu.')
    if not frappe.has_permission('Material Request','create'):frappe.throw('Chưa có quyền tạo đề xuất mua.',frappe.PermissionError)
    selected=frappe.parse_json(items)
    if not isinstance(selected,list) or not selected or len(selected)>100:frappe.throw('Chọn từ 1 đến 100 vật tư.')
    lock('Company',company)
    result=snapshot(company,warehouse,from_date,to_date)
    if result['warnings'] or result['unmapped']:frappe.throw('Xác định kho và quyền đọc nguồn trước khi tạo đề xuất mua.')
    rows=[r for r in result['rows'] if r['item'] in selected and (r['to_request_qty'] or 0)>0]
    if not rows:return dict(name=None,note='Phần thiếu đã có đề xuất mua hoặc đã đủ hàng. Không tạo thêm phiếu.')
    from lotus_farm.purchase_flow import enabled
    if enabled(company):
        from lotus_farm.purchase_proposal import save_proposal, detail
        proposal = save_proposal(company, dict(reason='Bổ sung vật tư thiếu cho nhu cầu cấp từ '+str(from_date)+' đến '+str(to_date),
            warehouse=warehouse, items=[dict(item_code=r['item'], qty=r['to_request_qty'], uom=r['uom'], warehouse=warehouse,
                schedule_date=max(getdate(to_date), getdate(nowdate()))) for r in rows]))
        doc = frappe.get_doc('Material Request', proposal['name'])
        by_item = {r['item']: r for r in rows}
        for line in doc.items:
            line.lotus_purchase_sources = frappe.as_json([dict(doctype=s['doctype'], name=s['name'], line=s['line'])
                for s in by_item[line.item_code]['sources']])
        doc.save()
        return detail(doc.name)
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
    if doc.material_request_type!='Purchase':frappe.throw('Chọn đề xuất mua vật tư.')
    from lotus_farm.purchase_flow import enabled
    if enabled(doc.company):
        from lotus_farm.purchase_proposal import detail
        from urllib.parse import urlencode
        return dict(detail(name), can_submit=False, can_delete=False,
                    proposal_url='/lotus/mua-hang?'+urlencode(dict(buying_view='needs', purchase_type='needs', purchase_doc=doc.name)))
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
    if info['modified']!=modified:frappe.throw('Đề xuất mua đã thay đổi. Mở lại để kiểm tra.')
    if info['docstatus']!=0:frappe.throw('Chỉ xử lý đề xuất mua nháp tại đây.')
    doc=frappe.get_doc('Material Request',name)
    from lotus_farm.purchase_flow import enabled
    if enabled(doc.company):
        frappe.throw('Mở Đề xuất mua để ký đủ 4 bước hoặc xóa nháp theo quyền người lập.')
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
    from lotus_farm.purchase_flow import enabled
    return dict(name=doc.name,company=doc.company,supplier=doc.supplier,supplier_name=doc.supplier_name or doc.supplier,currency=doc.currency,
        can_receive=frappe.has_permission('Purchase Receipt','create'),can_post=frappe.has_permission('Purchase Receipt','submit'),
        needs_evidence=enabled(doc.company),
        items=[dict(line=r.name,item=r.item_code,item_name=r.item_name,warehouse=r.warehouse,
            ordered_qty=flt(r.stock_qty),received_qty=flt(r.received_qty)*flt(r.conversion_factor),
            draft_qty=held.get(r.name,0),remaining_qty=max(0,flt(r.stock_qty)-flt(r.received_qty)*flt(r.conversion_factor)-held.get(r.name,0)),
            uom=r.stock_uom,rate=flt(r.base_net_rate)/(flt(r.conversion_factor) or 1),date=str(r.schedule_date)) for r in doc.items])


@frappe.whitelist(methods=['POST'])
def receive_order(name,posting_date,quantities,client_event_id,additional_costs=None,post=0,files=None,
                  deliverer_name=None,deliverer_signature=None,delivery_proof=None,notes=None):
    """Nhận hàng theo đơn, một đường cho điện thoại và máy tính (spec 003, FR-041..FR-046).

    post=1 records the goods in one step: the receipt is created with its photos and the deliverer's
    signature, posted to stock, and that confirmation is the storekeeper's signature (the signed PDF is kept).
    Without permission to post, the receipt stays a draft for the storekeeper.
    When someone else has just received against the same order the whole step is undone and the answer says
    how much can still be received."""
    from erpnext.controllers.status_updater import OverAllowanceError
    from lotus_farm.warehouse import _number
    selected=frappe.parse_json(quantities)
    if not isinstance(selected,dict) or not selected or len(selected)>100:frappe.throw('Chọn từ 1 đến 100 dòng nhận hàng.')
    selected={line:_number(qty,'Số thực nhận') for line,qty in selected.items()}
    for attempt in (1,2):
        try:
            return _receive_order(name,posting_date,selected,client_event_id,additional_costs,post,files,
                                  deliverer_name,deliverer_signature,delivery_proof,notes)
        except (frappe.QueryDeadlockError,frappe.QueryTimeoutError,frappe.TimestampMismatchError,OverAllowanceError):
            # Another receipt of this order was committed meanwhile: forget this attempt and read the books again.
            frappe.db.rollback()
            short=_short_lines(name,selected)
            if short or attempt==2:
                frappe.throw('Người khác vừa nhận hàng của đơn này. '+('; '.join(short)+'.' if short else 'Mở lại đơn để nhận phần còn lại.'))


def _left_text(row):
    from lotus_farm import print_kit as pk
    text='%s: còn nhận được %s %s'%(row['item_name'] or row['item'],pk.number(row['remaining_qty']),pk.unit(row['uom']))
    return text+(' (đang giữ %s trên phiếu nháp)'%pk.number(row['draft_qty']) if flt(row['draft_qty'])>0.000001 else '')


def _short_lines(name,selected):
    """Requested lines that no longer fit what the order still waits for, as 'Còn nhận được N' texts."""
    available={r['line']:r for r in purchase_order(name)['items']}
    return [_left_text(available[line]) for line,qty in selected.items() if line in available and qty>available[line]['remaining_qty']+0.000001]


def _receive_order(name,posting_date,selected,client_event_id,additional_costs,post,files,deliverer_name,deliverer_signature,delivery_proof,notes):
    from lotus_farm.controls import lock
    from lotus_farm.warehouse import _text,_warehouse
    from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt
    original=_purchase_doc('Purchase Order',name)
    if getdate(posting_date)<getdate(original.transaction_date):frappe.throw('Ngày nhận không được trước ngày đơn mua.')
    if not frappe.has_permission('Purchase Receipt','create'):frappe.throw('Chưa có quyền lập phiếu nhận hàng.',frappe.PermissionError)
    extra_costs=frappe.parse_json(additional_costs) if additional_costs else []
    if not isinstance(extra_costs,list):frappe.throw('Chi phí nhập hàng phải là danh sách.')
    attachments=frappe.parse_json(files) if files else []
    if not isinstance(attachments,list) or len(attachments)>20 or not all(isinstance(u,str) for u in attachments):
        frappe.throw('Tệp đính kèm không hợp lệ (tối đa 20 tệp).')
    event=_text(client_event_id,'Mã yêu cầu')
    key=hashlib.sha256((frappe.session.user+':'+event).encode()).hexdigest()
    digest=hashlib.sha256(json.dumps(dict(order=name,date=str(posting_date),quantities=selected,additional_costs=extra_costs),sort_keys=True).encode()).hexdigest()
    lock('Company',original.company);lock('Purchase Order',name)
    existing=frappe.db.get_value('Purchase Receipt',{'lotus_client_key':key},['name','lotus_payload_hash'],as_dict=True)
    if existing:
        _purchase_doc('Purchase Receipt',existing.name)
        if existing.lotus_payload_hash!=digest:frappe.throw('Yêu cầu này đã tạo phiếu '+existing.name+'. Mở lại để kiểm tra.')
        return _received(frappe.get_doc('Purchase Receipt',existing.name))
    info=purchase_order(name)
    available={r['line']:r for r in info['items']}
    if any(line not in available for line in selected):frappe.throw('Dòng đơn mua không còn hợp lệ. Mở lại đơn mua.')
    short=[_left_text(available[line]) for line,qty in selected.items() if qty>available[line]['remaining_qty']+0.000001]
    if short:frappe.throw('Lượng nhận vượt phần còn chờ. '+'; '.join(short)+'.')
    for line in selected:
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
    if notes:doc.remarks=str(notes).strip()[:500]
    from lotus_farm.procurement import apply_line_taxes
    apply_line_taxes(doc)
    if extra_costs:
        from lotus_farm.warehouse import _receipt_costs
        currency=frappe.get_cached_value('Company',doc.company,'default_currency')
        if doc.currency!=currency:
            frappe.throw('Chi phí cộng vào giá vốn theo VND chỉ hỗ trợ đơn mua VND. Dùng chứng từ phân bổ chi phí cho đơn ngoại tệ.')
        basic_total=sum(flt(row.qty)*flt(row.rate) for row in kept)
        for extra in _receipt_costs(doc.company,extra_costs,basic_total):
            doc.append('taxes',dict(charge_type='Actual',add_deduct_tax='Add',category='Valuation',
                                    account_head=extra['expense_account'],tax_amount=extra['amount'],
                                    description='Chi phí nhận hàng: '+extra['description']))

    doc.lotus_client_key=key;doc.lotus_payload_hash=digest
    doc.insert()
    # Photos, the delivery note and the deliverer's signature join the receipt in the same transaction (FR-041, FR-042).
    from lotus_farm import stock_attachments
    for url in attachments:stock_attachments.attach_uploaded(doc,url)
    store_evidence(doc,deliverer_name,deliverer_signature,delivery_proof)
    if cint(post) and doc.has_permission('submit'):
        doc.reload()
        receipt_action(doc.name,str(doc.modified),'submit')  # same checks as posting a draft later
        doc.reload()
    return _received(doc)


def _received(doc):
    """Answer of receive_order: the receipt, its state, the signed copy when posted, and what the order still waits for."""
    from lotus_farm import purchase_status,signing
    orders=sorted({r.purchase_order for r in doc.items if r.purchase_order})
    remaining=[dict(order=order,line=r['line'],item_name=r['item_name'],remaining_qty=r['remaining_qty'],uom=r['uom'])
               for order in orders for r in purchase_order(order)['items'] if r['remaining_qty']>0.000001] if doc.docstatus<2 else []
    return dict(name=doc.name,docstatus=doc.docstatus,modified=str(doc.modified),state=purchase_status.receipt_state(doc.docstatus),
                signed_copy=signing.copy_info(doc) if doc.docstatus==1 else None,remaining=remaining)


def store_evidence(doc,deliverer_name=None,deliverer_signature=None,delivery_proof=None):
    """Người giao hàng on a draft receipt: the name with the signature drawn on screen (a PNG data URL, stored as a
    private file of the receipt), and/or the photo of the signed delivery note (a private file just uploaded)."""
    values={}
    if not frappe.get_meta('Purchase Receipt').has_field('lotus_deliverer_name'):
        return values
    if deliverer_name is not None and str(deliverer_name).strip():
        values['lotus_deliverer_name']=str(deliverer_name).strip()[:140]
    if deliverer_signature:
        from lotus_farm import signing
        from lotus_farm.digital_signature import _normalize_image
        file=signing._private_copy(doc,'nguoi-giao-ky.png',_normalize_image(deliverer_signature))
        values['lotus_deliverer_signature']=frappe.db.get_value('File',file,'file_url')
    if delivery_proof:
        from lotus_farm import stock_attachments
        stock_attachments.attach_uploaded(doc,delivery_proof)
        values['lotus_delivery_proof']=delivery_proof
    if values:
        if doc.docstatus!=0:frappe.throw('Chỉ ghi người giao hàng trên phiếu nháp.')
        doc.db_set(values)
    return values


def receipt_totals(doc):
    added_costs=[dict(description=(row.description or '')[len('Chi phí nhận hàng: '):],amount=flt(row.tax_amount),
                      expense_account=row.account_head)
                 for row in doc.taxes if (row.description or '').startswith('Chi phí nhận hàng: ')]
    valuation_charges=sum(flt(row.tax_amount) for row in doc.taxes if row.category in ('Valuation','Valuation and Total'))
    goods_total=sum(flt(row.base_net_amount) for row in doc.items)
    return dict(goods_total=goods_total,added_costs=added_costs,valuation_charges=valuation_charges,incoming_total=goods_total+valuation_charges)


def _may_delete(doc):
    """A draft receipt is removed by its preparer, the receiving roles, or anyone holding the ERPNext delete right."""
    return (doc.owner==frappe.session.user or frappe.session.user=='Administrator'
            or bool({'Lotus Warehouse Receiver','Lotus Warehouse Manager'} & set(frappe.get_roles())) or doc.has_permission('delete'))


def receipt_extras(doc):
    """What every receipt detail shows beside its lines, in Kho and in Mua hàng (spec 003, FR-042..FR-045)."""
    from urllib.parse import urlencode
    from lotus_farm import purchase_flow,purchase_status,signing,stock_attachments
    invoices=[]
    if doc.docstatus==1 and frappe.has_permission('Purchase Invoice','read'):
        invoices=frappe.get_all('Purchase Invoice Item',filters={'purchase_receipt':doc.name,'docstatus':1},pluck='parent',distinct=True,limit_page_length=0)
    # Who signed: on the one-step chain the storekeeper who confirmed; older receipts keep their three-step panel.
    signed=signing.status(doc)
    keeper=next((s for s in signed['steps'] if s['state']=='Đã ký'),None) if signed['chain']=='purchase_receipt' and signed['round'] else None
    return dict(state=purchase_status.receipt_state(doc.docstatus),signing_chain=signed['chain'],
        signed_by=keeper['name'] if keeper else '',signed_at=keeper['signed_at'] if keeper else '',
        billing=purchase_status.billing_state(doc.get('per_billed')) if doc.docstatus==1 and not doc.is_return else '',
        deliverer_name=doc.get('lotus_deliverer_name') or '',deliverer_signed=bool(doc.get('lotus_deliverer_signature')),
        delivery_proof=doc.get('lotus_delivery_proof') or '',needs_evidence=purchase_flow.receipt_needs_evidence(doc),
        has_evidence=purchase_flow.receipt_has_evidence(doc),cancel_reason=doc.get('lotus_cancel_reason') or '',
        notes=frappe.utils.strip_html(doc.get('remarks') or '').strip(),is_return=cint(doc.is_return),return_against=doc.get('return_against') or '',
        files=stock_attachments._rows(doc.doctype,doc.name),invoices=sorted(invoices),
        print_url='/lotus/in-phieu?'+urlencode({'doctype':doc.doctype,'name':doc.name}),
        signed_copy=signing.copy_info(doc) if doc.docstatus==1 else None,
        can_submit=doc.docstatus==0 and doc.has_permission('submit'),can_cancel=doc.docstatus==1 and doc.has_permission('cancel'),
        can_delete=doc.docstatus==0 and _may_delete(doc),
        can_return=doc.docstatus==1 and not doc.is_return and frappe.has_permission('Purchase Receipt','create'))


@frappe.whitelist()
def purchase_receipt(name):
    doc=_purchase_doc('Purchase Receipt',name)
    return dict(name=doc.name,doctype=doc.doctype,company=doc.company,supplier=doc.supplier,currency=frappe.get_cached_value('Company',doc.company,'default_currency'),docstatus=doc.docstatus,
        modified=str(doc.modified),**receipt_totals(doc),**receipt_extras(doc),
        items=[dict(item=r.item_code,item_name=r.item_name,qty=r.stock_qty,uom=r.stock_uom,warehouse=r.warehouse,
            purchase_order=r.purchase_order,rate=r.valuation_rate,amount=flt(r.stock_qty)*flt(r.valuation_rate),date=str(doc.posting_date)) for r in doc.items])


@frappe.whitelist(methods=['POST'])
def receipt_action(name,modified,action,reason=None,deliverer_name=None,deliverer_signature=None,delivery_proof=None):
    """submit: post a draft (the deliverer's signature or delivery note may come with it); cancel: with a reason,
    for people who may cancel receipts; delete: a draft, by its preparer or the receiving roles."""
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
        note=str(reason or '').strip()
        if not 3<=len(note)<=500:frappe.throw('Ghi lý do hủy phiếu nhập (3–500 ký tự).')
        doc.cancel()  # ERPNext reverses Stock Ledger and recalculates PO received_qty
        if frappe.get_meta('Purchase Receipt').has_field('lotus_cancel_reason'):
            frappe.db.set_value('Purchase Receipt',doc.name,'lotus_cancel_reason',note)
        doc.add_comment('Comment','Hủy phiếu nhập: '+note)
        return dict(name=name,action='cancel')
    if doc.docstatus!=0:
        frappe.throw('Phiếu nhận không còn là bản nháp.')
    if action=='submit':
        doc.check_permission('submit')
        if doc.is_return:
            doc.submit()  # Native return validation and ledger reversal; no second stock document.
            return dict(name=name,action=action)
        if store_evidence(doc,deliverer_name,deliverer_signature,delivery_proof):doc.reload()
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
            left=flt(original.stock_qty)-flt(original.received_qty)*flt(original.conversion_factor) if original else 0
            if not original or qty>left+0.000001:
                from lotus_farm import print_kit as pk
                frappe.throw('Lượng nhận vượt phần còn lại của đơn mua. %s: còn nhận được %s %s.'%(
                    (original.item_name if original else line),pk.number(max(0,left)),pk.unit(original.stock_uom) if original else ''))
        doc.submit()  # purchase_flow.receipt_evidence (before_submit) and receipt_signed (on_submit) apply here
    elif action=='delete':
        if not _may_delete(doc):doc.check_permission('delete')
        frappe.delete_doc(doc.doctype,doc.name,ignore_permissions=True)
    else:frappe.throw('Thao tác không hợp lệ.')
    return dict(name=name,action=action)
