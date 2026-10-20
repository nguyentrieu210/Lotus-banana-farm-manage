"""Permission-checked SPA data, paging, metadata and document actions."""
import json
from copy import deepcopy
import frappe
from frappe.utils import cint, getdate, nowdate, flt, add_days
from lotus_farm.controls import lock, require_role, command, command_allowed
from lotus_farm.daily_operations import day_guard
from lotus_farm.scoping import land_scope, land_filters

MODULES={
 'alerts':['Lotus Alert'],
 'farms':['Farm','Farm Block','Farm Plot','Crop Cycle','Sucker Selection Batch'],
 'plans':['Daily Work Plan','Supply Reconciliation'],'forecast':['Harvest Forecast'],
 'work':['Daily Work Plan','Daily Work Result','Planting Event','Disease Observation','Bunch Operation'],
 'labor':['Daily Labor Summary','Labor Allocation'],
 'materials':['Material Requirement','Material Consumption','Material Recovery'],
 'losses':['Bunch Cancellation'], 'measurements':['Fruit Measurement'],
 'harvest':['Harvest Actual','Harvest Lot'], 'incoming-qc':['Incoming Quality Inspection'],
 'packhouse':['Packhouse Shift','Packout Run','Material Recovery','Secondary Product Movement','Supply Reconciliation'],
 'daily-close':['Daily Production Close'],'cycle-close':['Cycle Closing Report'],
 'trace':['Harvest Lot','Packout Run','Farm Plot'],'map':['Plot Geometry'],'settings':['Lotus Farm Settings'],
 'masters':['Plan Cohort','Work Category','Work Type','Work Team','Material Norm Profile','Norm Basis','Harvest Profile','Packout Profile','Cancellation Reason Group','Cancellation Reason','Cancellation Reason Alias','Disease','Defect Reason','Product Grade','Market','Pack Specification','Secondary Product Type','Bunch Tag','Warehouse Mapping','Work Schedule Rule','Plot Geometry','Scale Device'],
 'imports':['Source File Registry','Source Import Mapping','Source Import Batch','Integration Task','Source Inventory Item','OneDrive Feed','Legacy Organization Map','Legacy Cycle Plot Mapping']}
MODULES['process']=['Lotus Handover Cohort','Lotus Process Adoption','Bunch Tag','Sucker Selection Batch','Plan Cohort']
ALLOWED={d for names in MODULES.values() for d in names}
MODULES['masters'].append('Banana Variety')
ALLOWED.add('Banana Variety')
DATES={'Harvest Forecast':'period_start_date','Harvest Actual':'harvest_date','Harvest Lot':'received_date','Packout Run':'packing_date','Bunch Operation':'operation_date','Sucker Selection Batch':'selection_date'}


def allowed(doctype,permission='read'):
    if doctype not in ALLOWED:frappe.throw('Unsupported Lotus document.')
    if not frappe.has_permission(doctype,permission):frappe.throw('Permission denied for '+doctype,frappe.PermissionError)
    return frappe.get_meta(doctype)


@frappe.whitelist()
def bootstrap():
    from lotus_farm.field import session_info
    session=session_info()
    session['farms']=frappe.get_list('Farm',fields=['name','farm_name','company'],limit_page_length=1000) if frappe.has_permission('Farm','read') else []
    session['modules']={k:[t for t in types if frappe.has_permission(t,'read')] for k,types in MODULES.items()}
    session['modules']={k:v for k,v in session['modules'].items() if v}
    session['creatable']={t:frappe.has_permission(t,'create') for t in ALLOWED}
    roles=set(frappe.get_roles());admin=frappe.session.user=='Administrator'
    has_role=lambda *names:admin or bool(roles.intersection(names))
    from lotus_farm.mobile_access import abilities, allowed_teams, can_assign, can_capture
    session["abilities"] = abilities()
    session["scopes"] = {"farms": [f["name"] for f in session["farms"]]}
    session["scopes"]["teams"] = {f["name"]: sorted(allowed_teams(f["name"])) for f in session["farms"]}
    session['commands']={
        'work':can_assign(),
        'rate_approve':has_role('Lotus Price Approver'),
        'capture':can_capture() or has_role('Lotus Integration User'),
        'preview_close':has_role('Lotus Farm Manager','Lotus Auditor'),
        'sales':has_role('Lotus Sales Planner'),
        'forecast_release':has_role('Lotus Farm Manager'),
        'imports':has_role('Lotus Integration User'),
        'repack':has_role('Lotus Packing Supervisor','Lotus Stock Reviewer'),
        'reconcile':has_role('Lotus Packing Supervisor','Lotus Sales Planner','Lotus Auditor'),
        'calibrate_harvest':has_role('Lotus Farm Manager'),
        'calibrate_packout':has_role('Lotus Packing Supervisor'),
        'qc':has_role('Lotus QC Manager'),
    }
    session['today']=nowdate()
    session.setdefault('capabilities',{})['user_admin']=has_role('System Manager') and bool(frappe.has_permission('User','read'))
    session.setdefault('capabilities',{})['hr']=has_role('HR Manager','HR User')
    from lotus_farm.hr_workspace import _is_hr_manager
    session['capabilities']['hr_manage']=session['capabilities']['hr'] and _is_hr_manager()
    session.setdefault('capabilities',{})['attendance']=bool(frappe.db.exists('DocType','Attendance') and frappe.has_permission('Attendance','read')) or bool(frappe.db.exists('DocType','Lotus Crew Attendance') and frappe.has_permission('Lotus Crew Attendance','read'))
    from lotus_farm.work_journal import capabilities as journal_capabilities
    session['capabilities'].update(journal_capabilities())
    if session['capabilities']['work_journal.read']:
        from lotus_farm.work_journal import farm_names
        existing = {f['name'] for f in session['farms']}
        session['farms'] += frappe.get_all('Farm', filters={'name': ['in', [f for f in farm_names() if f not in existing] or ['']]}, fields=['name','farm_name','company'])
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
def listing(doctype,farm=None,company=None,block=None,plot=None,cycle=None,status=None,date=None,from_date=None,to_date=None,search=None,start=0,length=50,sort='modified desc',column_filters=None,include_filter_values=False,zone=None):
    meta=allowed(doctype)
    selected=land_scope(company,farm,block,plot,cycle,zone=zone)
    filters=land_filters(meta,selected)
    # Source-linked xưởng records have no direct Plot/Cycle field.
    if doctype not in ('Farm','Farm Block') and (zone or plot or cycle or block) and meta.has_field('farm') and not any(meta.has_field(f) for f in ('farm_plot','farm_block','crop_cycle')):
        names=_source_scope_names(doctype,selected)
        if names is None:frappe.throw('This document supports Farm scope only; clear Block/Plot/Cycle filters.')
        filters['name']=['in',names or ['__no_matching_source__']]
    date_field=DATES.get(doctype,'posting_date')
    if doctype=='Harvest Forecast':
        filters['period_start_date']=['<=',getdate(to_date or add_days(date or nowdate(),56))]
        filters['period_end_date']=['>=',getdate(from_date or date or nowdate())]
    elif meta.has_field(date_field):
        if from_date and to_date:filters[date_field]=['between',[getdate(from_date),getdate(to_date)]]
        elif from_date:filters[date_field]=['>=',getdate(from_date)]
        elif to_date:filters[date_field]=['<=',getdate(to_date)]
        elif date:filters[date_field]=getdate(date)
    if from_date and to_date and getdate(from_date)>getdate(to_date):frappe.throw('From date cannot follow To date.')
    status_field=next((f for f in ('supply_state','approval_state','status') if meta.has_field(f)), 'docstatus')
    if status not in (None,''):
        choices=(meta.get_field(status_field).options or '').split('\n') if status_field!='docstatus' else ['0','1','2']
        if str(status) not in choices:frappe.throw('Unsupported status for this document.')
        filters[status_field]=cint(status) if status_field=='docstatus' else status
    if search:filters=[[k,*(v if isinstance(v,list) else ['=',v])] for k,v in filters.items()]+[['name','like','%'+search[:100]+'%']]
    candidates=['name','docstatus','modified',meta.title_field,'company','farm','farm_block','farm_plot','crop_cycle',date_field,'supply_state','approval_state','status','shift_code','bunch_qty','harvested_bunch_qty','gross_weight_kg','completed_qty','present','absent','required_workdays','accepted_kg','rejected_kg','finished_kg','packout_percent','input_kg','output_kg','stock_entry','source_status','row_count','resolved_percent','retry_count','sync_error','area_ha','variety','planting_date','plot_code','block_code']
    columns=list(dict.fromkeys(f for f in candidates if f and (f in ('name','docstatus','modified') or meta.has_field(f))))
    if sort not in ('modified desc','modified asc','name asc','name desc'):frappe.throw('Unsupported sort.')
    from lotus_farm.table_filters import selections, distinct, matches
    selected_columns=selections(column_filters,columns)
    all_rows=frappe.get_list(doctype,filters=filters,fields=columns,order_by=sort+', name',limit_page_length=0) if cint(include_filter_values) or selected_columns else None
    filter_values=distinct(all_rows,columns) if cint(include_filter_values) else None
    length=max(1,min(cint(length),100));start=max(cint(start),0)
    rows=([row for row in all_rows if matches(row,selected_columns)][start:start+length+1] if all_rows is not None else
          frappe.get_list(doctype,filters=filters,fields=columns,order_by=sort+', name',limit_start=start,limit_page_length=length+1))
    choices=(meta.get_field(status_field).options or '').split('\n') if status_field!='docstatus' else ['0','1','2']
    return dict(rows=rows[:length],columns=columns,filter_values=filter_values,has_more=len(rows)>length,start=start,length=length,status_options=[c for c in choices if c])


def _source_scope_names(doctype,selected):
    from lotus_farm.reporting import records
    if doctype=='Daily Work Plan':
        names=[]
        for row in records(doctype,{'farm':selected['farm'],'docstatus':['<',2]},['name']):
            doc=frappe.get_doc(doctype,row.name)
            if any((not selected.get('zone_blocks') or line.farm_block in selected['zone_blocks']) and all(not selected[k] or line.get(f)==selected[k] for k,f in [('block','farm_block'),('plot','farm_plot'),('cycle','crop_cycle')]) for line in doc.lines):names.append(row.name)
        return names
    if doctype not in ('Harvest Lot','Incoming Quality Inspection','Packout Run','Packhouse Shift'):return None
    actuals=records('Harvest Actual',{**land_filters(frappe.get_meta('Harvest Actual'),selected),'docstatus':1},['name'])
    actual_names={a.name for a in actuals}
    lots=[r.name for r in records('Harvest Lot',{'farm':selected['farm'],'docstatus':['<',2]},['name'])
        if any(s.harvest_actual in actual_names for s in frappe.get_doc('Harvest Lot',r.name).sources)]
    if doctype=='Harvest Lot':return lots
    if doctype=='Incoming Quality Inspection':return [r.name for r in records(doctype,{'harvest_lot':['in',lots or ['__none__']]},['name'])]
    runs=[r.name for r in records('Packout Run',{'farm':selected['farm'],'docstatus':['<',2]},['name'])
        if any(s.harvest_lot in lots for s in frappe.get_doc('Packout Run',r.name).sources)] if doctype in ('Packout Run','Packhouse Shift') else []
    if doctype=='Packout Run':return runs
    if doctype=='Packhouse Shift':return list({frappe.db.get_value('Packout Run',name,'packhouse_shift') for name in runs}-{None,''})
    return None


@frappe.whitelist()
def scope_options(company=None,farm=None,block=None,plot=None,cycle=None,zone=None):
    selected=land_scope(company,farm,block,plot,cycle,zone=zone)
    from lotus_farm.reporting import records
    result={'scope':{k:v for k,v in selected.items() if k!='zone_blocks'},'zones':[],'blocks':[],'plots':[],'cycles':[]}
    if selected['farm']:
        result['zones']=sorted({b.farm_zone for b in records('Farm Block',{'farm':selected['farm']},['farm_zone']) if b.farm_zone}) if frappe.has_permission('Farm Block','read') else []
        result['blocks']=records('Farm Block',{'farm':selected['farm'],**({'farm_zone':zone} if zone else {})},['name','block_name','block_code','farm_zone']) if frappe.has_permission('Farm Block','read') else []
        result['plots']=records('Farm Plot',{'farm':selected['farm'],**({'farm_block':selected['block']} if selected['block'] else {})},['name','plot_name','farm_block']) if frappe.has_permission('Farm Plot','read') else []
        result['cycles']=records('Crop Cycle',land_filters(frappe.get_meta('Crop Cycle'),selected),['name','cycle_no','farm_plot']) if frappe.has_permission('Crop Cycle','read') else []
    return result


@frappe.whitelist()
def detail(doctype,name):
    allowed(doctype);doc=frappe.get_doc(doctype,name);doc.check_permission('read')
    return doc.as_dict()


@frappe.whitelist()
def link_options(doctype,search='',farm=None,company=None,context_field=None,block=None,cycle=None,on_date=None,operation_type=None):
    if not frappe.has_permission(doctype,'read'):frappe.throw('Link read permission required.',frappe.PermissionError)
    meta=frappe.get_meta(doctype);filters={}
    if farm and meta.has_field('farm'):filters['farm']=farm
    if company and meta.has_field('company'):filters['company']=company
    if doctype=='Bunch Operation' and context_field=='source_cut_operation':
        selected=land_scope(company=company,farm=farm,block=block,cycle=cycle)
        filters.update(land_filters(meta,selected));filters.update(operation_type='Cut Bud',docstatus=1)
        rows=frappe.get_list(doctype,filters=filters,or_filters={'name':['like','%'+search[:80]+'%']} if search else None,
            fields=['name','farm','farm_block','farm_plot','crop_cycle','sucker_selection_batch','operation_date','bunch_tag','net_bunch_qty'],limit_page_length=30,order_by='operation_date desc, name desc')
        result=[]
        for r in rows:
            tag_title=frappe.db.get_value('Bunch Tag',r.bunch_tag,'display_name') if r.bunch_tag and frappe.has_permission('Bunch Tag','read') else r.bunch_tag
            result.append(dict(value=r.name,label=f"{r.name} · {r.operation_date} · {r.net_bunch_qty} buồng",subtitle=tag_title,
                context={**{key:r.get(key) for key in ('farm','farm_block','farm_plot','crop_cycle','sucker_selection_batch')},'tag':r.bunch_tag,'tag_title':tag_title}))
        return result
    if doctype=='Bunch Tag':
        filters['enabled']=1
        if on_date and operation_type in ('Cut Bud','Bud Injection'):
            day=getdate(add_days(on_date,14 if operation_type=='Bud Injection' else 0))
            filters.update(valid_from=['<=',day],valid_to=['>=',day])
    title=meta.title_field or 'name'
    rows=frappe.get_list(doctype,filters=filters,or_filters={'name':['like','%'+search[:80]+'%'],title:['like','%'+search[:80]+'%']} if search else None,fields=list(dict.fromkeys(['name',title])),limit_page_length=500 if doctype=='UOM' else 30,order_by='name')
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
    from lotus_farm.mobile_access import is_manager, require_farm, require_team
    require_role('Lotus Farm Manager', 'Lotus Field Supervisor')
    doc=frappe.get_doc('Daily Work Plan',plan)
    if is_manager():
        doc.check_permission('write')
    else:
        require_farm(doc.farm)
    day_guard(doc);lock('Daily Work Plan',plan);doc.reload()
    if doc.docstatus!=1:frappe.throw('Submit the work plan first.')
    row=next((r for r in doc.lines if r.name==line),None)
    if not row:frappe.throw('Task does not belong to this plan.')
    if not is_manager():
        require_team(doc.farm, row.work_team)
        doc.flags.ignore_permissions = True
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
def material_status(farm,posting_date,block=None,plot=None,cycle=None,zone=None):
    from lotus_farm.reporting import records
    from lotus_farm.warehouse_planning import snapshot
    selected=land_scope(farm=farm,block=block,plot=plot,cycle=cycle,zone=zone)
    result=snapshot(frappe.db.get_value('Farm',farm,'company'),from_date=posting_date,to_date=posting_date,farm=farm)
    usage=[]
    for req in records('Material Requirement',{**land_filters(frappe.get_meta('Material Requirement'),selected),'posting_date':posting_date,'docstatus':1},['name','work_plan_line']):
        doc=frappe.get_doc('Material Requirement',req.name)
        actuals=records('Material Consumption',{'material_requirement':req.name,'docstatus':1},['item','consumed_qty'])
        used={}
        for c in actuals:used[c.item]=used.get(c.item,0)+flt(c.consumed_qty)
        result=frappe.get_list('Daily Work Result',filters={'work_plan_line':req.work_plan_line,'docstatus':1},fields=['completed_qty'],limit_page_length=1)
        line=frappe.db.get_value('Daily Work Plan Line',req.work_plan_line,['planned_qty'],as_dict=True)
        ratio=flt(result[0].completed_qty)/flt(line.planned_qty) if result and line and line.planned_qty else None
        for r in doc.lines:
            expected=flt(r.required_qty)*ratio if ratio is not None else None
            usage.append(dict(requirement=doc.name,item=r.item,uom=r.uom,planned_qty=r.required_qty,used_qty=used.get(r.item,0),expected_for_actual=expected,variance_qty=used.get(r.item,0)-expected if expected is not None else None))
    # Scope the sources before recomputing coverage; filtering an aggregated row
    # afterwards would leave demand from other plots in the selected plot.
    filtered=[]
    for row in result['rows']:
        matching=[s for s in row['sources'] if any(u['requirement']==s['name'] for u in usage)]
        if not matching:continue
        from lotus_farm.warehouse_rules import coverage
        amounts=coverage(sum(s['required_qty'] for s in matching),sum(min(s['issued_qty'],s['required_qty']) for s in matching),
            row['actual_qty'],row['native_reserved_qty'],row['draft_qty'],sum(s['draft_qty'] for s in matching),row['incoming_qty'],row['requested_qty'])
        amounts.update(item=row['item'],uom=row['uom'],warehouse=row['warehouse'])
        if result['warnings']:amounts['shortage_qty']=None
        filtered.append(amounts)
    missing=[dict(item=s['item'],uom=s['uom'],required_qty=s['remaining_qty'],actual_qty=None,available_qty=None,shortage_qty=None) for s in result['unmapped'] if any(u['requirement']==s['name'] for u in usage)]
    return dict(rows=filtered+missing,usage=usage,warehouses=sorted({r['warehouse'] for r in filtered}),
        note='; '.join(result['warnings']+(['Chọn kho cấp cho nhu cầu chưa xác định kho.'] if missing else [])))


@frappe.whitelist()
def quality_matrix(farm,posting_date,block=None,plot=None,cycle=None,zone=None):
    from lotus_farm.reporting import records,scope,trace_lot
    selected=land_scope(farm=farm,block=block,plot=plot,cycle=cycle,zone=zone);lots=[];defects={};cells=[]
    linked={'name':['in',_source_scope_names('Incoming Quality Inspection',selected) or ['__none__']]} if zone or block or plot or cycle else {}
    for q in records('Incoming Quality Inspection',{'farm':farm,'posting_date':posting_date,'docstatus':1,**linked},['name','harvest_lot','received_kg','rejected_kg']):
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
def loss_analysis(farm=None,from_date=None,to_date=None,company=None,block=None,plot=None,cycle=None,zone=None):
    from lotus_farm.reporting import records
    filters={'docstatus':1,'posting_date':['between',[from_date or nowdate(),to_date or nowdate()]]}
    filters.update(land_filters(frappe.get_meta('Bunch Cancellation'),land_scope(company,farm,block,plot,cycle,zone=zone)))
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
