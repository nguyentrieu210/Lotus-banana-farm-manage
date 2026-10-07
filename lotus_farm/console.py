"""Permission-checked SPA data, paging, metadata and document actions."""
import json
from copy import deepcopy
import frappe
from frappe.utils import cint, getdate, nowdate, flt, add_days
from lotus_farm.controls import lock, require_role, command, command_allowed
from lotus_farm.daily_operations import day_guard

MODULES={
 'alerts':['Lotus Alert'],
 'farms':['Farm','Farm Block','Farm Plot','Crop Cycle','Sucker Selection Batch'],
 'plans':['Harvest Forecast','Daily Work Plan','Supply Reconciliation'],
 'work':['Daily Work Plan','Daily Work Result','Planting Event','Disease Observation','Bunch Operation'],
 'labor':['Daily Labor Summary','Labor Allocation'],
 'materials':['Material Requirement','Material Consumption','Material Recovery'],
 'losses':['Bunch Cancellation'], 'measurements':['Fruit Measurement'],
 'harvest':['Harvest Actual','Harvest Lot'], 'incoming-qc':['Incoming Quality Inspection'],
 'packhouse':['Packhouse Shift','Packout Run','Material Recovery','Secondary Product Movement','Supply Reconciliation'],
 'daily-close':['Daily Production Close'],'cycle-close':['Cycle Closing Report'],
 'trace':['Harvest Lot','Packout Run','Farm Plot'],'map':['Plot Geometry'],'settings':['Lotus Farm Settings'],
 'masters':['Work Category','Work Type','Work Team','Material Norm Profile','Norm Basis','Harvest Profile','Packout Profile','Cancellation Reason Group','Cancellation Reason','Cancellation Reason Alias','Disease','Defect Reason','Product Grade','Market','Pack Specification','Secondary Product Type','Bunch Tag','Warehouse Mapping','Work Schedule Rule','Plot Geometry','Scale Device'],
 'imports':['Source File Registry','Source Import Mapping','Source Import Batch','Integration Task','Source Inventory Item','OneDrive Feed','Legacy Organization Map','Legacy Cycle Plot Mapping']}
ALLOWED={d for names in MODULES.values() for d in names}
DATES={'Harvest Forecast':'period_start_date','Harvest Actual':'harvest_date','Harvest Lot':'received_date','Packout Run':'packing_date','Bunch Operation':'operation_date','Sucker Selection Batch':'selection_date'}


def allowed(doctype,permission='read'):
    if doctype not in ALLOWED:frappe.throw('Unsupported Lotus document.')
    if not frappe.has_permission(doctype,permission):frappe.throw('Permission denied for '+doctype,frappe.PermissionError)
    return frappe.get_meta(doctype)


@frappe.whitelist()
def bootstrap():
    from lotus_farm.field import session_info
    session=session_info()
    session['farms']=frappe.get_list('Farm',fields=['name','farm_name','company'],limit_page_length=1000)
    session['modules']={k:[t for t in types if frappe.has_permission(t,'read')] for k,types in MODULES.items()}
    session['modules']={k:v for k,v in session['modules'].items() if v}
    session['creatable']={t:frappe.has_permission(t,'create') for t in ALLOWED}
    session['today']=nowdate()
    return session


@frappe.whitelist()
def schema(doctype):
    meta=allowed(doctype)
    def fields(m):
        return [{k:f.get(k) for k in ('fieldname','label','fieldtype','options','reqd','read_only','default','description','depends_on')} for f in m.fields if f.fieldtype not in ('Section Break','Column Break','Tab Break','HTML','Button')]
    from lotus_farm.field import CAPTURE_TYPES
    from lotus_farm.importing import IMPORT_FIELDS
    capture_fields=sorted(IMPORT_FIELDS.get(doctype,())) if doctype in CAPTURE_TYPES else []
    return dict(doctype=doctype,title_field=meta.title_field,is_submittable=meta.is_submittable,fields=fields(meta),
        tables={f.options:fields(frappe.get_meta(f.options)) for f in meta.fields if f.fieldtype=='Table'},capture_fields=capture_fields,
        permissions={p:frappe.has_permission(doctype,p) for p in ('create','write','submit','cancel','amend')})


@frappe.whitelist()
def listing(doctype,farm=None,company=None,block=None,plot=None,date=None,from_date=None,to_date=None,search=None,start=0,length=50,sort='modified desc'):
    meta=allowed(doctype);filters={}
    if meta.has_field('farm') and farm:filters['farm']=farm
    if doctype=='Farm' and farm:filters['name']=farm
    if meta.has_field('company') and company:filters['company']=company
    if meta.has_field('farm_block') and block:filters['farm_block']=block
    if meta.has_field('farm_plot') and plot:filters['farm_plot']=plot
    date_field=DATES.get(doctype,'posting_date')
    if doctype=='Harvest Forecast':
        filters['period_start_date']=['<=',getdate(to_date or add_days(date or nowdate(),56))]
        filters['period_end_date']=['>=',getdate(from_date or date or nowdate())]
    elif meta.has_field(date_field):
        if from_date and to_date:filters[date_field]=['between',[getdate(from_date),getdate(to_date)]]
        elif date:filters[date_field]=getdate(date)
    if search:filters['name']=['like','%'+search[:100]+'%']
    candidates=['name','docstatus','modified',meta.title_field,'company','farm','farm_block','farm_plot','crop_cycle',date_field,'supply_state','approval_state','status','shift_code','bunch_qty','harvested_bunch_qty','gross_weight_kg','completed_qty','present','absent','required_workdays','accepted_kg','rejected_kg','finished_kg','packout_percent','input_kg','output_kg','stock_entry','source_status','row_count','resolved_percent','retry_count','sync_error','area_ha','variety','planting_date','plot_code','block_code']
    columns=list(dict.fromkeys(f for f in candidates if f and (f in ('name','docstatus','modified') or meta.has_field(f))))
    if sort not in ('modified desc','modified asc','name asc','name desc'):frappe.throw('Unsupported sort.')
    length=max(1,min(cint(length),100));start=max(cint(start),0)
    rows=frappe.get_list(doctype,filters=filters,fields=columns,order_by=sort+', name',limit_start=start,limit_page_length=length+1)
    return dict(rows=rows[:length],columns=columns,has_more=len(rows)>length,start=start,length=length)


@frappe.whitelist()
def detail(doctype,name):
    allowed(doctype);doc=frappe.get_doc(doctype,name);doc.check_permission('read')
    return doc.as_dict()


@frappe.whitelist()
def link_options(doctype,search='',farm=None,company=None):
    if not frappe.has_permission(doctype,'read'):frappe.throw('Link read permission required.',frappe.PermissionError)
    meta=frappe.get_meta(doctype);filters={}
    if farm and meta.has_field('farm'):filters['farm']=farm
    if company and meta.has_field('company'):filters['company']=company
    title=meta.title_field or 'name'
    rows=frappe.get_list(doctype,filters=filters,or_filters={'name':['like','%'+search[:80]+'%'],title:['like','%'+search[:80]+'%']} if search else None,fields=list(dict.fromkeys(['name',title])),limit_page_length=30,order_by='name')
    return [dict(value=r.name,label=r.get(title) or r.name) for r in rows]


def payload_fields(meta,values):
    if not isinstance(values,dict):frappe.throw('Document fields must be an object.')
    editable={f.fieldname:f for f in meta.fields if not f.read_only and f.fieldtype not in ('Section Break','Column Break','Tab Break','HTML','Button')}
    if set(values)-set(editable):frappe.throw('Payload includes protected or unsupported fields.')
    result={}
    for key,value in values.items():
        field=editable[key]
        if field.fieldtype=='Table':
            if not isinstance(value,list):frappe.throw('Child table must be a list.')
            if len(value)>1000:frappe.throw('Split child tables above 1,000 rows.')
            result[key]=[payload_fields(frappe.get_meta(field.options),v) for v in value]
        else:result[key]=value
    return result


def _settings_result(doc,meta):
    from lotus_farm.rules import canonical_hash
    result=doc.as_dict()
    result['_settings_token']=canonical_hash([[f.fieldname,doc.get(f.fieldname)] for f in meta.fields])
    return result


@frappe.whitelist()
def settings():
    meta=allowed('Lotus Farm Settings')
    doc=frappe.get_single('Lotus Farm Settings');doc.check_permission('read')
    return _settings_result(doc,meta)


@frappe.whitelist(methods=['POST'])
def save_settings(values,base_token=None):
    meta=allowed('Lotus Farm Settings','write')
    values=frappe.parse_json(values) if isinstance(values,str) else values
    clean=payload_fields(meta,values)
    doc=frappe.get_single('Lotus Farm Settings');doc.check_permission('write')
    frappe.db.sql("select field from tabSingles where doctype=%s for update",('Lotus Farm Settings',))
    doc.reload()
    current=_settings_result(doc,meta)
    if base_token and current['_settings_token']!=base_token:frappe.throw('Settings changed. Reload before saving; your input has not overwritten it.')
    doc.update(clean);doc.save()
    return _settings_result(doc,meta)


@frappe.whitelist(methods=['POST'])
def save(doctype,values,name=None,base_modified=None):
    meta=allowed(doctype,'write' if name else 'create')
    values=frappe.parse_json(values) if isinstance(values,str) else values
    clean=payload_fields(meta,values)
    if name:
        doc=frappe.get_doc(doctype,name);doc.check_permission('write')
        if doc.get('farm'):lock('Farm',doc.farm)
        lock(doctype,name);doc.reload()
        if str(doc.modified)!=str(base_modified):frappe.throw('Document changed. Reload before saving; your input has not overwritten it.')
        if doc.docstatus!=0:frappe.throw('Submitted documents require cancel/amend with a reason.')
        doc.update(clean);doc.save()
    else:
        doc=frappe.get_doc(dict(doctype=doctype,**clean));doc.insert()
    return doc.as_dict()


@frappe.whitelist(methods=['POST'])
def document_action(doctype,name,action,reason=None,base_modified=None):
    allowed(doctype);doc=frappe.get_doc(doctype,name);doc.check_permission('read')
    if doc.get('farm'):lock('Farm',doc.farm)
    lock(doctype,name);doc.reload()
    if base_modified and str(doc.modified)!=str(base_modified):frappe.throw('Document changed. Reload before taking this action.')
    if action=='submit':doc.check_permission('submit');doc.submit()
    elif action=='cancel':
        doc.check_permission('cancel')
        if not (reason or '').strip():frappe.throw('Cancellation/reopening requires a reason.')
        if doc.meta.has_field('reopen_reason'):doc.reopen_reason=reason
        doc.add_comment('Comment',text='Cancel/reopen reason: '+frappe.utils.escape_html(reason))
        if doc.meta.has_field('reopen_reason'):doc.save()
        doc.cancel()
    elif action=='amend':
        doc.check_permission('amend')
        if doc.docstatus!=2 or not (reason or '').strip():frappe.throw('Cancel the document and provide an amendment reason first.')
        amended=frappe.copy_doc(doc);amended.docstatus=0;amended.amended_from=doc.name
        if amended.meta.has_field('amendment_reason'):amended.amendment_reason=reason
        # Never copy idempotency/capture identifiers from a cancelled actual.
        for field in ('client_event_id','client_payload_hash','field_capture','legacy_source_key','source_import_batch'):
            if amended.meta.has_field(field):amended.set(field,None)
        amended.insert();return amended.as_dict()
    else:frappe.throw('Unsupported document action.')
    return doc.as_dict()


@frappe.whitelist()
def audit(doctype,name):
    allowed(doctype);doc=frappe.get_doc(doctype,name);doc.check_permission('read')
    return dict(owner=doc.owner,created=doc.creation,modified_by=doc.modified_by,modified=doc.modified,
        versions=frappe.get_all('Version',filters={'ref_doctype':doctype,'docname':name},fields=['name','creation','owner','data'],order_by='creation desc',limit_page_length=100),
        comments=frappe.get_all('Comment',filters={'reference_doctype':doctype,'reference_name':name,'comment_type':'Comment'},fields=['creation','owner','content'],order_by='creation desc',limit_page_length=100))


@frappe.whitelist(methods=['POST'])
def work_state(plan,line,state,reason=None):
    require_role('Lotus Farm Manager');doc=frappe.get_doc('Daily Work Plan',plan);doc.check_permission('write');day_guard(doc);lock('Daily Work Plan',plan);doc.reload()
    if doc.docstatus!=1:frappe.throw('Submit the work plan first.')
    row=next((r for r in doc.lines if r.name==line),None)
    if not row:frappe.throw('Task does not belong to this plan.')
    if frappe.db.exists('Daily Work Result',{'work_plan_line':line,'docstatus':1}):frappe.throw('Completed actual requires cancel/amend.')
    transitions={'Planned':{'Ready','Blocked'},'Ready':{'In Progress','Blocked'},'In Progress':{'Blocked'},'Blocked':{'Ready','In Progress'}}
    if state not in transitions.get(row.execution_state or 'Planned',set()):frappe.throw('Unsupported task transition.')
    if state=='Blocked' and not (reason or '').strip():frappe.throw('Blocked work requires a reason.')
    if state=='Ready':
        allocated=sum(flt(v) for v in frappe.get_all('Labor Allocation',filters={'work_plan_line':line,'docstatus':1},pluck='allocated_workdays'))
        if allocated+0.000001<flt(row.required_workdays):frappe.throw('Allocate required labor before marking Ready.')
        if row.norm_profile and not frappe.db.exists('Material Requirement',{'work_plan_line':line,'docstatus':1}):frappe.throw('Submit material requirements before marking Ready.')
        if row.norm_profile:
            materials=material_status(doc.farm,doc.posting_date)
            if not materials['warehouses'] or any(r['shortage_qty'] is None or r['shortage_qty']>0.000001 for r in materials['rows']):
                frappe.throw('Resolve Farm material shortages and map Field Store stock before marking Ready.')
    before=deepcopy(doc)
    version_filters={'ref_doctype':doc.doctype,'docname':doc.name}
    version_count=frappe.db.count('Version',version_filters)
    row.execution_state=state;row.blocked_reason=reason if state=='Blocked' else ''
    doc.flags.ignore_version=False
    with command(doc,'work_state'):doc.save()
    if frappe.db.count('Version',version_filters)==version_count:
        version=frappe.new_doc('Version')
        if version.set_diff(before,doc):version.insert(ignore_permissions=True)
    return dict(line=line,state=state)


def work_state_guard(doc,method=None):
    before=doc.get_doc_before_save()
    if before and before.docstatus==1:
        old={r.name:r for r in before.lines}
        for row in doc.lines:
            prior=old.get(row.name)
            if prior and any(row.get(f)!=prior.get(f) for f in ('execution_state','blocked_reason')) and not command_allowed(doc,'work_state'):
                frappe.throw('Use the work transition command.')
    for row in doc.lines:
        if doc.docstatus==0 and (row.execution_state or 'Planned')!='Planned':frappe.throw('Draft task state starts Planned; use transitions after submitting the plan.')
        if row.work_team:
            team=frappe.get_doc('Work Team',row.work_team);team.check_permission('read')
            if team.farm!=doc.farm:frappe.throw('Responsible team must belong to this Farm.')
        if row.start_at and row.due_at and frappe.utils.get_datetime(row.due_at)<frappe.utils.get_datetime(row.start_at):frappe.throw('Due time cannot precede start.')


@frappe.whitelist()
def material_status(farm,posting_date):
    from lotus_farm.reporting import scope,records
    from lotus_farm.daily_api import material_availability
    scope(farm)
    warehouses=records('Warehouse Mapping',{'farm':farm,'enabled':1,'warehouse_role':'Field Store'},['warehouse'])
    rows=[];demand={};usage=[]
    for req in records('Material Requirement',{'farm':farm,'posting_date':posting_date,'docstatus':1},['name','work_plan_line']):
        doc=frappe.get_doc('Material Requirement',req.name)
        actuals=records('Material Consumption',{'material_requirement':req.name,'docstatus':1},['item','consumed_qty'])
        used={}
        for c in actuals:used[c.item]=used.get(c.item,0)+flt(c.consumed_qty)
        result=frappe.get_list('Daily Work Result',filters={'work_plan_line':req.work_plan_line,'docstatus':1},fields=['completed_qty'],limit_page_length=1)
        line=frappe.db.get_value('Daily Work Plan Line',req.work_plan_line,['planned_qty'],as_dict=True)
        ratio=flt(result[0].completed_qty)/flt(line.planned_qty) if result and line and line.planned_qty else None
        for r in doc.lines:
            outstanding=max(flt(r.required_qty)-used.get(r.item,0),0)
            key=(r.item,r.uom);demand[key]=demand.get(key,0)+outstanding
            expected=flt(r.required_qty)*ratio if ratio is not None else None
            usage.append(dict(requirement=doc.name,item=r.item,uom=r.uom,planned_qty=r.required_qty,used_qty=used.get(r.item,0),expected_for_actual=expected,variance_qty=used.get(r.item,0)-expected if expected is not None else None))
    for (item,uom),qty in demand.items():
        actual=reserved=0
        if warehouses and not frappe.has_permission('Stock Ledger Entry','read'):frappe.throw('Stock Ledger read permission is required.',frappe.PermissionError)
        for warehouse in {w.warehouse for w in warehouses}:
            from lotus_farm.controls import validate_warehouse
            validate_warehouse(warehouse,frappe.db.get_value('Farm',farm,'company'))
            frappe.get_doc('Item',item).check_permission('read')
            b=frappe.db.get_value('Bin',{'item_code':item,'warehouse':warehouse},['actual_qty','reserved_stock'],as_dict=True) or {}
            actual+=flt(b.get('actual_qty'));reserved+=flt(b.get('reserved_stock'))
        available=max(actual-reserved,0) if warehouses else None
        rows.append(dict(item=item,uom=uom,required_qty=qty,actual_qty=actual if warehouses else None,available_qty=available,shortage_qty=max(qty-available,0) if available is not None else None))
    return dict(rows=rows,usage=usage,warehouses=[w.warehouse for w in warehouses],note='Map Field Store warehouses to calculate physical shortage.' if not warehouses else '')


@frappe.whitelist()
def quality_matrix(farm,posting_date):
    from lotus_farm.reporting import records,scope,trace_lot
    scope(farm);lots=[];defects={};cells=[]
    for q in records('Incoming Quality Inspection',{'farm':farm,'posting_date':posting_date,'docstatus':1},['name','harvest_lot','received_kg','rejected_kg']):
        doc=frappe.get_doc('Incoming Quality Inspection',q.name)
        lots.append(dict(name=q.harvest_lot,inspection=q.name,received_kg=q.received_kg,rejected_kg=q.rejected_kg))
        for d in doc.defects:
            defects[d.defect_reason]=frappe.db.get_value('Defect Reason',d.defect_reason,'defect_name')
            cells.append(dict(lot=q.harvest_lot,inspection=q.name,defect=d.defect_reason,weight_kg=d.weight_kg,affected_units=d.affected_units,occurrences=d.occurrences))
    return dict(lots=lots,defects=[dict(name=k,label=v) for k,v in defects.items()],cells=cells)


@frappe.whitelist()
def shift_detail(name):
    from lotus_farm.shift import shift_summary
    doc=frappe.get_doc('Packhouse Shift',name);doc.check_permission('read')
    result=shift_summary(doc)
    result['shift']=doc.as_dict()
    result['recovery']=frappe.get_list('Material Recovery',filters={'packhouse_shift':name},fields=['name','consumption','recovered_qty','stock_entry','docstatus'],limit_page_length=1000)
    result['secondary']=frappe.get_list('Secondary Product Movement',filters={'packhouse_shift':name},fields=['name','item','quantity_kg','stock_entry','docstatus'],limit_page_length=1000)
    return result


@frappe.whitelist()
def evidence(doctype,name):
    allowed(doctype);doc=frappe.get_doc(doctype,name);doc.check_permission('read')
    if not doc.get('field_capture'):return None
    capture=frappe.get_doc('Field Capture',doc.field_capture);capture.check_permission('read')
    if capture.target_doctype!=doctype or capture.target_name!=name:frappe.throw('Capture lineage mismatch.')
    return {k:capture.get(k) for k in ('captured_by','captured_at','latitude','longitude','gps_accuracy_m','photo')}


@frappe.whitelist()
def loss_analysis(farm=None,from_date=None,to_date=None):
    from lotus_farm.reporting import records
    filters={'docstatus':1,'posting_date':['between',[from_date or nowdate(),to_date or nowdate()]]}
    if farm:filters['farm']=farm
    rows=records('Bunch Cancellation',filters,['name','farm','farm_block','farm_plot','crop_cycle','posting_date','reason','bunch_qty'])
    groups={}
    for row in rows:
        key=(row.farm,row.farm_block,row.reason)
        if key not in groups:groups[key]=dict(farm=row.farm,farm_block=row.farm_block,reason=row.reason,bunch_qty=0)
        groups[key]['bunch_qty']+=cint(row.bunch_qty)
    return dict(rows=rows,by_reason=sorted(groups.values(),key=lambda r:-r['bunch_qty']))


@frappe.whitelist()
def order_lines(sales_order):
    order=frappe.get_doc('Sales Order',sales_order);order.check_permission('read')
    return [dict(name=r.name,item=r.item_code,qty=r.qty,delivered_qty=r.delivered_qty,delivery_date=r.delivery_date) for r in order.items]
