"""Approved Excel mappings, reviewable staging, and transactional imports."""
import hashlib
import json
import frappe
from frappe.utils import now_datetime
from lotus_farm.controls import require_role, lock, command
from lotus_farm.extraction import read_workbook
from lotus_farm.rules import RuleError, canonical_hash

# These are explicit business fields, never arbitrary DocTypes or document flags.
SCOPE=('farm_block','farm_plot','crop_cycle','sucker_selection_batch','posting_date')
IMPORT_FIELDS={
 'Farm Plot':('farm_block','plot_code','plot_name','area_ha','active'),
 'Crop Cycle':('farm_block','farm_plot','cycle_no','cycle_type','parent_cycle','variety','planting_date','status','notes'),
 'Sucker Selection Batch':('farm_block','crop_cycle','selection_date','selected_sucker_qty','notes'),
 'Planting Event':SCOPE+('event_type','plant_qty','area_ha','notes'),
 'Disease Observation':SCOPE+('disease','affected_plants','severity','action_taken'),
 'Fruit Measurement':SCOPE+('row_code','sample_count','average_length','average_diameter','uom','notes','ribbon_color','measurer','samples'),
 'Bunch Cancellation':SCOPE+('expected_harvest_date','bunch_qty','reason','source_operation','notes'),
 'Bunch Operation':('farm_block','crop_cycle','sucker_selection_batch','operation_date','operation_type','bunch_qty','rejected_qty','harvest_profile','notes'),
 'Harvest Actual':('farm_block','crop_cycle','sucker_selection_batch','harvest_date','harvested_bunch_qty','gross_weight_kg','rejected_weight_kg','forecast','notes','ribbon_color','harvest_team','started_at','ended_at','receiving_packhouse','scale_reading'),
 'Daily Labor Summary':('posting_date','work_category','work_area','headcount','present','absent','staffing_target','area_ha','actual_workdays'),
 'Daily Work Plan':('posting_date','lines'),
 'Daily Work Result':SCOPE+('work_plan','work_plan_line','completed_qty','actual_workdays','unfinished_reason','actual_labor'),
 'Incoming Quality Inspection':('posting_date','harvest_lot','accepted_kg','defects','notes'),
 'Harvest Lot':('received_date','sources','raw_item','raw_warehouse','raw_batch'),
 'Packout Run':('packing_date','sources','outputs','target_warehouse','quality_standard','reject_kg','other_loss_kg','loss_details','packhouse_shift'),
 'Material Norm Profile':('profile_name','version','work_type','valid_from','valid_to','lines'),
}


def file_bytes(url):
    names=frappe.get_all('File',filters={'file_url':url},pluck='name')
    if not names:frappe.throw('Select an uploaded File.')
    file=frappe.get_doc('File',names[0]);file.check_permission('read')
    data=file.get_content()
    return data.encode() if isinstance(data,str) else data


@frappe.whitelist(methods=['POST'])
def stage_workbook(source_file,mapping,farm,file_url):
    require_role('Lotus Integration User')
    frappe.get_doc('Farm',farm).check_permission('read')
    source=frappe.get_doc('Source File Registry',source_file);source.check_permission('read')
    profile=frappe.get_doc('Source Import Mapping',mapping);profile.check_permission('read')
    if profile.approval_state!='Approved':frappe.throw('Approve the import mapping first.')
    if source.migration_tier not in ('A','B'):frappe.throw('Only Tier A/B sources create detailed transactions; archive Tier C/D separately.')
    data=file_bytes(file_url)
    if hashlib.sha256(data).hexdigest()!=source.sha256:frappe.throw('Uploaded bytes do not match the registered SHA-256.')
    config=profile.as_dict();config['source_key']=source.source_key;config['source_family']=source.source_family or source.source_path
    try:result=read_workbook(data,config)
    except (RuleError,ValueError,KeyError) as exc:frappe.throw(str(exc))
    if not result['rows']:frappe.throw('No source data rows were found.')
    batch_key=canonical_hash([source.name,profile.name,farm])
    existing=frappe.db.get_value('Source Import Batch',{'batch_key':batch_key,'docstatus':['<',2]},'name')
    if existing:
        batch=frappe.get_doc('Source Import Batch',existing);batch.check_permission('read')
        return dict(batch=batch.name,row_count=len(batch.rows),invalid_count=sum(bool(r.validation_error) for r in batch.rows),profile=result['profile'])
    doc=frappe.get_doc(dict(doctype='Source Import Batch',farm=farm,source_file=source.name,mapping=profile.name,batch_key=batch_key,
        rows=result['rows'],source_attachment=file_url,control_totals_json=json.dumps(dict(source=result['control_totals'],profile=result['profile']),default=str))).insert()
    return dict(batch=doc.name,row_count=len(doc.rows),invalid_count=sum(bool(r.validation_error) for r in doc.rows),profile=result['profile'])


def _target(batch,row):
    mapping=frappe.get_doc('Source Import Mapping',batch.mapping);mapping.check_permission('read')
    if mapping.approval_state!='Approved':frappe.throw('Mapping is no longer approved.')
    if row.validation_error:frappe.throw('Resolve source validation before importing: '+row.validation_error)
    matches=frappe.get_all('Legacy Organization Map',filters={'legacy_key':row.legacy_org_key,'farm':batch.farm,'approval_state':'Approved'},pluck='name')
    if not matches:frappe.throw('No approved organization mapping to this Farm.')
    payload=json.loads(row.normalized_json or '{}')
    if any(k not in IMPORT_FIELDS[mapping.target_doctype] for k in payload):frappe.throw('Staged target contains an unauthorized field.')
    meta=frappe.get_meta(mapping.target_doctype)
    for field in meta.fields:
        if field.fieldtype=='Table' and field.fieldname in payload and payload[field.fieldname] is not None:
            allowed={f.fieldname for f in frappe.get_meta(field.options).fields if not f.read_only and f.fieldtype not in ('Section Break','Column Break','Tab Break')}
            if not isinstance(payload[field.fieldname],list) or any(not isinstance(r,dict) or set(r)-allowed for r in payload[field.fieldname]):
                frappe.throw('Imported child rows contain unauthorized or computed fields.')
    doc=frappe.get_doc(dict(doctype=mapping.target_doctype,**payload,farm=batch.farm))
    if doc.meta.has_field('company'):doc.company=frappe.db.get_value('Farm',batch.farm,'company')
    if doc.meta.has_field('source_import_batch'):doc.source_import_batch=batch.name
    if doc.meta.has_field('legacy_source_key'):doc.legacy_source_key=row.row_key
    return doc


@frappe.whitelist(methods=['POST'])
def preview_import(batch):
    require_role('Lotus Integration User')
    doc=frappe.get_doc('Source Import Batch',batch);doc.check_permission('write')
    verify_staging(doc)
    result=[]
    for row in doc.rows:
        if row.row_status!='Pending':continue
        frappe.db.savepoint('lotus_import_preview')
        try:
            target=_target(doc,row);target.insert()
            result.append(dict(row=row.name,status='Ready',target_doctype=target.doctype))
        except frappe.ValidationError as exc:result.append(dict(row=row.name,status='Error',error=str(exc)))
        finally:frappe.db.rollback(save_point='lotus_import_preview')
    return result


@frappe.whitelist(methods=['POST'])
def import_rows(batch):
    require_role('Lotus Integration User')
    doc=frappe.get_doc('Source Import Batch',batch);doc.check_permission('write')
    lock('Farm',doc.farm);lock('Source File Registry',doc.source_file);lock('Source Import Batch',doc.name)
    doc.reload()
    if doc.docstatus!=0:frappe.throw('Only draft import batches can be processed.')
    verify_staging(doc)
    if frappe.db.get_value('Source File Registry',doc.source_file,'source_status')!='Active':frappe.throw('Confirm this source is authoritative and mark it Active before creating targets.')
    totals={};imported=[]
    for row in doc.rows:
        if row.row_status!='Pending':continue
        ensure_business_identity(doc,row)
        duplicate=frappe.db.sql("select r.name from `tabSource Import Row` r join `tabSource Import Batch` b on b.name=r.parent where b.source_file=%s and b.docstatus<2 and r.row_key=%s and r.row_status='Imported' and b.name!=%s FOR UPDATE",(doc.source_file,row.row_key,doc.name))
        if duplicate:frappe.throw('Source row already exists in another active batch.')
        target=_target(doc,row).insert()
        # Imported transactions remain drafts for normal role review and submit.
        row.row_status='Imported';row.target_doctype=target.doctype;row.target_name=target.name
        imported.append(target.name)
        for k,v in json.loads(row.normalized_json).items():
            if isinstance(v,(int,float)) and not isinstance(v,bool):totals[k]=totals.get(k,0)+float(v)
    controls=json.loads(doc.control_totals_json or '{}');controls.update(reconcile_totals(doc))
    doc.control_totals_json=json.dumps(controls,default=str);doc.save()
    return dict(batch=doc.name,created_drafts=imported,resolved_percent=doc.resolved_percent,control_totals=controls)


@frappe.whitelist(methods=['POST'])
def run_task(task):
    require_role('Lotus Integration User')
    doc=frappe.get_doc('Integration Task',task);doc.check_permission('write')
    lock('Farm',doc.farm);lock('Integration Task',doc.name);doc.reload()
    if doc.status=='Completed':return dict(task=doc.name,batch=doc.source_import_batch,status=doc.status)
    frappe.db.savepoint('lotus_integration')
    try:
        result=stage_workbook(doc.source_file,doc.mapping,doc.farm,doc.file)
        doc.source_import_batch=result['batch'];doc.status='Completed';doc.sync_error=''
    except Exception as exc:
        frappe.db.rollback(save_point='lotus_integration')
        # Do not log tokens, file URLs, request headers or external response bodies.
        doc.status='Failed';doc.sync_error=type(exc).__name__+': source validation failed; review mapping and registered file.'
    doc.retry_count=int(doc.retry_count or 0)+1;doc.last_sync_at=now_datetime()
    with command(doc,'run_integration'):doc.save()
    return dict(task=doc.name,batch=doc.source_import_batch,status=doc.status,error=doc.sync_error)


def verify_staging(batch):
    if not batch.mapping or not batch.source_attachment:frappe.throw('Mapped imports require the original uploaded source.')
    source=frappe.get_doc('Source File Registry',batch.source_file);source.check_permission('read')
    data=file_bytes(batch.source_attachment)
    if hashlib.sha256(data).hexdigest()!=source.sha256:frappe.throw('Original source bytes changed.')
    mapping=frappe.get_doc('Source Import Mapping',batch.mapping);mapping.check_permission('read')
    config=mapping.as_dict();config['source_key']=source.source_key;config['source_family']=source.source_family or source.source_path
    expected=read_workbook(data,config)['rows']
    if {r['row_key'] for r in expected}!={r.row_key for r in batch.rows}:frappe.throw('Staging rows no longer match the approved source scope.')
    lookup={r['row_key']:r for r in expected}
    for row in batch.rows:
        for key in ('business_key','normalized_hash','source_hash','normalized_json','validation_error','legacy_org_key','source_sheet','source_row'):
            if row.get(key)!=lookup[row.row_key][key]:frappe.throw('Staged source or transformation changed; register a reviewed source/mapping version.')


def reconcile_totals(batch):
    mapping=frappe.get_doc('Source Import Mapping',batch.mapping);mapping.check_permission('read')
    numeric=[f.target_field for f in mapping.fields if f.value_type in ('Number','Integer')]
    target_totals={k:0 for k in numeric}
    for row in batch.rows:
        if row.row_status=='Imported':
            target=frappe.get_doc(row.target_doctype,row.target_name);target.check_permission('read')
            for key in numeric:target_totals[key]+=float(target.get(key) or 0)
    controls=json.loads(batch.control_totals_json or '{}')
    source=controls.get('source',{})
    return dict(target_totals=target_totals,variance={k:target_totals[k]-float(source.get(k) or 0) for k in numeric},
                rejected_rows=sum(r.row_status=='Rejected' for r in batch.rows),pending_rows=sum(r.row_status=='Pending' for r in batch.rows))


@frappe.whitelist()
def reconciliation(batch):
    require_role('Lotus Integration User')
    doc=frappe.get_doc('Source Import Batch',batch);doc.check_permission('read')
    return reconcile_totals(doc)


def ensure_business_identity(batch, row):
    if not row.business_key or not row.normalized_hash:
        frappe.throw('Approve a mapping with stable business key columns and restage the source before importing.')
    mapping=frappe.get_doc('Source Import Mapping',batch.mapping)
    prior=frappe.db.sql("""select r.normalized_hash, r.target_name from `tabSource Import Row` r
        join `tabSource Import Batch` b on b.name=r.parent
        join `tabSource Import Mapping` m on m.name=b.mapping
        where b.farm=%s and m.target_doctype=%s and b.docstatus<2
        and r.business_key=%s and r.row_status='Imported' and b.name!=%s FOR UPDATE""",
        (batch.farm,mapping.target_doctype,row.business_key,batch.name),as_dict=True)
    if prior:
        if any(p.normalized_hash!=row.normalized_hash for p in prior):
            frappe.throw('This business transaction changed in a later source version. Review and cancel/amend the existing target; do not import a second actual.')
        frappe.throw('This business transaction was already imported, including in another workbook version.')
