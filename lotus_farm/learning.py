"""Measured proposals only. Publishing assumptions remains a human approval."""

import json
import frappe
from lotus_farm.controls import require_role
from lotus_farm.rules import calibration, RuleError, canonical_hash


@frappe.whitelist()
def propose_profile(farm, farm_block, crop_cycle, from_date, to_date):
    require_role("Lotus Farm Manager")
    cycle = frappe.get_doc("Crop Cycle", crop_cycle)
    cycle.check_permission("read")
    if cycle.farm != farm or cycle.farm_block != farm_block:
        frappe.throw("Select matching Farm, Block and Crop Cycle.")
    rows = frappe.get_list(
        "Harvest Actual",
        filters={
            "farm": farm,
            "farm_block": farm_block,
            "crop_cycle": crop_cycle,
            "docstatus": 1,
            "harvest_date": ["between", [from_date, to_date]],
        },
        fields=["name", "harvested_bunch_qty", "gross_weight_kg", "saleable_weight_kg"],
        limit_page_length=10000,
    )
    minimum = frappe.db.get_single_value("Lotus Farm Settings", "minimum_calibration_samples") or 10
    try:
        result = calibration(rows, minimum)
    except RuleError as exc:
        frappe.throw(str(exc))
    result.update(
        farm=farm,
        farm_block=farm_block,
        crop_cycle=crop_cycle,
        source_documents=[r.name for r in rows],
        source_hash=canonical_hash(rows),
        source_date_from=from_date,
        source_date_to=to_date,
        algorithm_version="lotus-weighted-actual/1",
        approval_state="Draft",
    )
    # Do not infer survival or packout without matched source-bunch/raw input denominators.
    return result


@frappe.whitelist()
def propose_complete_profile(farm, crop_cycle, from_date, to_date):
    """Only fully received, QC-inspected and stock-posted source actuals are calibrated."""
    from frappe.utils import getdate, flt
    from lotus_farm.reporting import records, _actual_fully_processed, packout_lineage
    from lotus_farm.promax_rules import weighted_packout
    cycle=frappe.get_doc('Crop Cycle',crop_cycle);cycle.check_permission('read')
    if cycle.farm!=farm or getdate(from_date)>getdate(to_date):frappe.throw('Select the matching Farm and a valid sample period.')
    require_role('Lotus Farm Manager','Lotus Packing Supervisor')
    rows=records('Harvest Actual',{'farm':farm,'crop_cycle':crop_cycle,'docstatus':1,'harvest_date':['between',[from_date,to_date]]},['name','harvested_bunch_qty','gross_weight_kg','saleable_weight_kg'])
    complete=[r for r in rows if _actual_fully_processed(r.name)]
    minimum=int(frappe.db.get_single_value('Lotus Farm Settings','minimum_calibration_samples') or 10)
    try:result=calibration(complete,minimum)
    except RuleError as exc:frappe.throw(str(exc))
    selected={r.name for r in complete};samples=[];accepted=received=0;sources=[]
    for r in records('Packout Run',{'farm':farm,'docstatus':1},['name','stock_entry']):
        run=frappe.get_doc('Packout Run',r.name)
        if not r.stock_entry or frappe.db.get_value('Stock Entry',r.stock_entry,'docstatus')!=1:continue
        share=sum(s['fraction'] for s in packout_lineage(run) if s['harvest_actual'] in selected)
        if share:
            samples.append(dict(input_kg=flt(run.input_kg)*share,finished_kg=sum(flt(o.net_kg) for o in run.outputs if o.output_type=='Finished')*share))
            sources.append(run.name)
    for r in records('Harvest Lot',{'farm':farm,'docstatus':1},['name']):
        lot=frappe.get_doc('Harvest Lot',r.name)
        fraction=sum(flt(s.contributed_kg) for s in lot.sources if s.harvest_actual in selected)/flt(lot.released_raw_kg)
        if fraction:
            for q in records('Incoming Quality Inspection',{'harvest_lot':lot.name,'docstatus':1},['name','received_kg','accepted_kg']):
                received+=flt(q.received_kg)*fraction;accepted+=flt(q.accepted_kg)*fraction;sources.append(q.name)
    try:packed=weighted_packout(samples,1)
    except RuleError as exc:frappe.throw(str(exc))
    result['quality_pass_rate_percent']*=accepted/received if received else 0
    result.update(packout_rate_percent=packed['packout_rate_percent'],farm=farm,crop_cycle=crop_cycle,
        source_date_from=str(getdate(from_date)),source_date_to=str(getdate(to_date)),
        source_documents=sorted([r.name for r in complete]+sources),excluded_incomplete=[r.name for r in rows if r.name not in selected],
        algorithm_version='lotus-complete-lineage/1')
    result['source_hash']=canonical_hash(result)
    return result


@frappe.whitelist(methods=['POST'])
def create_calibrated_profile(base_profile,crop_cycle,from_date,to_date,valid_from,valid_to):
    require_role('Lotus Farm Manager')
    base=frappe.get_doc('Harvest Profile',base_profile);base.check_permission('read')
    if base.approval_state!='Approved':frappe.throw('Select an approved base profile.')
    result=propose_complete_profile(base.farm,crop_cycle,from_date,to_date)
    from lotus_farm.controls import lock
    lock('Farm',base.farm)
    versions=frappe.get_all('Harvest Profile',filters={'profile_name':base.profile_name},pluck='version')
    values={f:base.get(f) for f in ('profile_name','farm','farm_block','variety','cycle_type','sucker_to_harvest_days','shooting_to_harvest_days','cut_bud_to_harvest_days','bunch_survival_rate_percent','safety_buffer_percent')}
    doc=frappe.get_doc(dict(doctype='Harvest Profile',**values,version=max(versions or [0])+1,
        valid_from=valid_from,valid_to=valid_to,approval_state='Draft',active=1,
        avg_bunch_weight_kg=result['avg_bunch_weight_kg'],quality_pass_rate_percent=result['quality_pass_rate_percent'],
        packout_rate_percent=result['packout_rate_percent'],calibration_json=json.dumps(result,default=str),calibration_hash=result['source_hash'])).insert()
    return dict(profile=doc.name,approval_state=doc.approval_state,proposal=result)


@frappe.whitelist(methods=['POST'])
def create_calibrated_packout(base_profile,crop_cycle,from_date,to_date,valid_from,valid_to):
    require_role('Lotus Packing Supervisor')
    base=frappe.get_doc('Packout Profile',base_profile);base.check_permission('read')
    if base.approval_state!='Approved':frappe.throw('Select an approved base Packout Profile.')
    result=propose_complete_profile(base.farm,crop_cycle,from_date,to_date)
    from lotus_farm.reporting import records,packout_lineage
    from frappe.utils import flt
    selected=set(result['source_documents']);raw=finished=0
    for r in records('Packout Run',{'farm':base.farm,'docstatus':1},['name']):
        run=frappe.get_doc('Packout Run',r.name)
        if run.name not in selected:continue
        share=sum(s['fraction'] for s in packout_lineage(run) if s['harvest_actual'] in selected)
        raw+=flt(run.input_kg)*share
        finished+=sum(flt(o.net_kg) for o in run.outputs if o.item==base.item and o.output_type=='Finished')*share
    if not raw or not finished:frappe.throw('No complete matched finished output for this Item.')
    from lotus_farm.controls import lock
    lock('Farm',base.farm)
    versions=frappe.get_all('Packout Profile',filters={'profile_name':base.profile_name},pluck='version')
    values={f:base.get(f) for f in ('profile_name','farm','variety','item','quality_standard')}
    proof=dict(proposal=result,item=base.item,input_kg=raw,finished_kg=finished,algorithm_version='lotus-item-yield/1')
    doc=frappe.get_doc(dict(doctype='Packout Profile',**values,version=max(versions or [0])+1,valid_from=valid_from,valid_to=valid_to,
        approval_state='Draft',yield_percent=finished/raw*100,calibration_json=json.dumps(proof,default=str),calibration_hash=canonical_hash(proof))).insert()
    return dict(profile=doc.name,approval_state=doc.approval_state,yield_percent=doc.yield_percent)
