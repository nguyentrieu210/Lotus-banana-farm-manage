"""Public read-only forecast (dự thu) by lô and khu.

Only Farm Block census, approved Plan Cohort, observed/estimated plant stages.
NO use of cut-mother journals, uploads or synthetic mother-cut dates.
"""
from __future__ import annotations

import datetime as dt
import frappe
from frappe.utils import nowdate
from lotus_farm.block_forecast_engine import forecast, date, months_after, source_rows, projection_config
from lotus_farm.forecast_parameters import DEFAULTS, approved_version, validate
from lotus_farm import bunch_flow_rules, bunch_forecast_engine
from lotus_farm import forecast_snapshot_rules as snapshot_rules


def _farm(farm, permission="read"):
    if not farm:
        frappe.throw("Chọn vườn.")
    doc=frappe.get_doc("Farm",farm)
    doc.check_permission(permission)
    return doc

def _sources(farm,zone=None,block=None):
    """All records are filtered through Frappe read permissions and farm scope."""
    _farm(farm)
    meta=frappe.get_meta("Farm Block")
    fields=["name","farm","block_code","block_name","farm_zone","area_ha","active","variety","modified","forecast_count_source"]
    for optional in ("lotus_tree_count","lotus_estimated_flowering_date","lotus_estimation_basis"):
        if meta.has_field(optional):
            fields.append(optional)
    filters={"farm":farm,"active":1}
    if block:
        filters["name"]=block
    if zone:
        filters["farm_zone"]=zone
    blocks=frappe.get_list("Farm Block",filters=filters,fields=fields,limit_page_length=1000)
    names={b.name for b in blocks}
    co=[]
    if names and frappe.has_permission("Plan Cohort","read"):
        co=frappe.get_list("Plan Cohort",
            filters={"farm":farm,"approval_state":"Approved","farm_block":["in",list(names)]},
            fields=["name","farm_block","crop_cycle","cohort_code","cohort_name",
                    "anchor","anchor_date","quantity_basis","planned_qty",
                    "version","approval_state","modified","forecast_distribution_mode"],limit_page_length=2000)
    cycle_names={c.crop_cycle for c in co if c.crop_cycle}
    cycles={}
    if cycle_names and frappe.has_permission("Crop Cycle","read"):
        cycles={c.name:c for c in frappe.get_list("Crop Cycle",
            filters={"name":["in",list(cycle_names)],"farm":farm},
            fields=["name","farm_block","cycle_no"],limit_page_length=2000)}
    for c in co:
        c["cycle_no"]=cycles[c.crop_cycle].cycle_no if c.crop_cycle in cycles else None
    return blocks,co

def _profiles(farm,as_of=None):
    """Approved parameter sets; as_of: only those already approved at that moment (a weekly copy rebuilt later)."""
    if not frappe.has_permission("Lotus Block Forecast Profile","read"):
        return []
    rows=frappe.get_list("Lotus Block Forecast Profile",
        filters={"farm":farm,"approval_state":"Approved","active":1},
        fields=["*"],limit_page_length=1000)
    return snapshot_rules.profiles_as_of(rows,as_of) if as_of else rows

def _observations(farm,block=None):
    """Actual field observations are reported separately; not counted twice."""
    if not frappe.has_permission("Bunch Operation","read"):
        return []
    filters={"farm":farm,"docstatus":1,
             "operation_type":["in",["Shooting","Bud Injection","Cut Bud"]]}
    if block:filters["farm_block"]=block
    records=frappe.get_list("Bunch Operation",filters=filters,
        fields=["name","farm_block","crop_cycle","operation_date","operation_type",
                "bunch_qty","net_bunch_qty","modified"],
        order_by="operation_date desc",limit_page_length=1000)
    return records


def _projection(farm,zone=None,block=None,include_daily=False,as_of=None):
    """All readers use the same farm-wide 36-month window and lot source. Tree counts and flowering dates are always
    today's values, also for a copy rebuilt as of an earlier Monday (written in its limits)."""
    all_blocks,all_cohorts=_sources(farm)
    profiles=_profiles(farm,as_of)
    all_sources,_=source_rows(all_blocks,all_cohorts)
    anchors=[projection_config(s,profiles)[2] for s in all_sources]
    start=min(anchors).replace(day=1) if anchors else None
    blocks=[b for b in all_blocks if (not zone or b.farm_zone==zone) and (not block or b.name==block)]
    names={b.name for b in blocks}
    cohorts=[c for c in all_cohorts if c.farm_block in names]
    result=forecast(blocks,cohorts,profiles=profiles,from_date=start,horizon_months=36,include_daily=include_daily)
    labels={b.name:(b.block_name or b.block_code or b.name) for b in blocks}
    varieties={v.name:v.variety_name or v.name for v in frappe.get_all('Banana Variety',fields=['name','variety_name'])}
    by_name={b.name:b for b in blocks}
    for row in result['rows']+result.get('daily_rows',[]):
        row['farm_block_label']=labels.get(row['farm_block'],row['farm_block'])
        row['variety_label']=varieties.get(by_name[row['farm_block']].variety,by_name[row['farm_block']].variety or '')
    result['warnings']=[next((w.replace(name,label,1) for name,label in labels.items() if w.startswith(name+':')),w) for w in result['warnings']]
    result['input_tree_count']=sum(int(b.get('lotus_tree_count') or 0) for b in blocks)
    result['input_block_count']=len(blocks)
    result['zones']=sorted({b.farm_zone for b in all_blocks if b.farm_zone})
    return result,blocks,cohorts,profiles

def _can_import_opening():
    from lotus_farm.field_report import is_manager
    return is_manager()

LINE_FIELDS=["name","farm_block","bunch_tag","cycle_no","event_type","event_date","qty","reject_stage","weight_kg","reason","source_type",
             "source_name","confirmed_by"]

def _bunch_lines(farm,blocks=None,as_of=None):
    """Confirmed lines of the sổ lô. Drafts stay out of the forecast until the đội trưởng confirms them (FR-021).
    as_of: the sổ lô as it stood then (confirmed before, not voided before)."""
    from lotus_farm.lot_ledger import bunch_rows
    filters={"farm":farm,"state":"Confirmed"}
    if blocks is not None:
        filters["farm_block"]=["in",list(blocks) or [""]]
    if not as_of:
        return bunch_rows(filters,LINE_FIELDS)
    filters.update(state=["in",["Confirmed","Voided"]],confirmed_at=["<",as_of])
    return snapshot_rules.lines_as_of(bunch_rows(filters,LINE_FIELDS+["confirmed_at","voided_at"]),as_of)

def _today(as_of=None):
    return str(as_of.date()) if as_of else nowdate()

def _bunch_params(profiles):
    def params_for(block,cut_day):
        # The approved set in force when the bunch comes in, not when it was cut.
        when=cut_day+dt.timedelta(days=int(DEFAULTS["cut_to_harvest_days"]))
        profile=approved_version(profiles,block,when)
        return (profile.get("name") if profile else None),validate(profile or DEFAULTS)
    return params_for

def _bunch_scope(farm,zone=None,block=None):
    filters={"farm":farm,"active":1}
    if zone:filters["farm_zone"]=zone
    if block:filters["name"]=block
    return {b.name:{"code":b.block_code,"zone":b.farm_zone or "","cycle":int(b.lotus_current_cycle_no or 0)} for b in frappe.get_all("Farm Block",filters=filters,fields=["name","block_code","farm_zone","lotus_current_cycle_no"],limit_page_length=0)}

def _tag_labels(farm):
    return {t.name:t.color_label or t.name for t in frappe.get_all("Bunch Tag",filters={"farm":farm},fields=["name","color_label"],limit_page_length=0)}

def _bunch_cohorts(farm,blocks,waves,lines=None,as_of=None):
    """Every bunch of these lô, once, at the stage nearest to harvest."""
    today=_today(as_of)
    lines=_bunch_lines(farm,blocks,as_of) if lines is None else lines
    params=_bunch_params(_profiles(farm,as_of))
    cut=bunch_flow_rules.cut_cohorts(lines,params,today)
    injected,observed=bunch_flow_rules.inject_cohorts(lines,params,today)
    suckers,claimed=bunch_flow_rules.sucker_cohorts(lines,observed,params,today)
    trees=bunch_flow_rules.tree_cohorts(waves,observed,claimed,{name:b["cycle"] for name,b in blocks.items()},today)
    return cut+injected+suckers+trees

def _unconfirmed(farm,blocks):
    """Entered but not confirmed: shown apart, never in the forecast."""
    from lotus_farm.lot_ledger import bunch_rows
    rows=bunch_rows({"farm":farm,"state":"Draft","farm_block":["in",list(blocks) or [""]]},["event_type","qty"])
    totals={}
    for r in rows:totals[r.event_type]=totals.get(r.event_type,0)+int(r.qty)
    return totals

def _bunch_weekly(farm,waves,zone=None,block=None,as_of=None):
    today=_today(as_of)
    blocks=_bunch_scope(farm,zone,block)
    lines=_bunch_lines(farm,blocks,as_of)
    cohorts=_bunch_cohorts(farm,blocks,waves,lines,as_of)
    result=bunch_forecast_engine.summarize(cohorts,blocks,_tag_labels(farm),today)
    result["unconfirmed"]={} if as_of else _unconfirmed(farm,blocks)
    result["pace"]=bunch_forecast_engine.cut_pace(cohorts,lines,today)
    result["coverage"]={"with_data":len({l.farm_block for l in lines if l.event_type in ("Cut Bud","Bud Injection")}),"total":len(blocks)}
    # Crops years ahead are outside every approved set for now; only what is on the screen deserves a warning.
    shown=months_after(date(today).replace(day=1),bunch_forecast_engine.MONTHS)
    if any(not c["profile"] and c["days"] and c["days"][0][0]<shown for c in cohorts):
        result["warnings"].append("Một số lô đang dùng thông số mặc định, chưa có bộ thông số được duyệt.")
    return result,cohorts

def bunch_summary(farm,as_of=None):
    """The whole farm, for a frozen copy of the forecast: now, or as the sổ lô stood at a moment."""
    result,_,_,_=_projection(farm,as_of=as_of)
    return _bunch_weekly(farm,result["rows"],as_of=as_of)

LAYER_NOTES={"cut":"Mức tin cậy cao: buồng đã cắt bắp.","inject":"Mức tin cậy khá: đã chích bắp, chưa cắt.","sucker":"Mức tin cậy thấp: số chồi ước tính từ diện tích đã chọn, mốc thời gian theo ngày chọn thật.",
    "tree":"Mức tin cậy thấp: tính từ số cây và ngày trổ ước tính theo khu."}

def _trace_facts(layer,g,c):
    dm=lambda d:str(d)[8:10]+"/"+str(d)[5:7] if d else ""
    window=dm(c["window_start"])+" – "+dm(c["window_end"])
    if layer=="cut":
        return [["Đã cắt bắp",g["cut"]],["Hủy sau cắt",g["rejected"]],["Đã thu",g["harvested"]],["Dự kiến còn thu",g["left"]],["Thu từ – đến",window]]
    if layer=="inject":
        return [["Đã chích",g["injected"]],["Đã cắt từ số chích",g["cut"]],["Còn chờ cắt",g["uncut"]],["Hủy trước cắt",g["rejected"]],["Dự kiến thu",g["left"]]]
    if layer=="sucker":
        return [["Ngày chọn chồi",dm(g["selected"])],["Số chồi ước tính",g["suckers"]],["Dự kiến thu",g["left"]],["Thu từ – đến",window]]
    return [["Số cây của đợt",g["trees"]],["Đợt trổ",g["wave"]],["Trổ ước tính từ",dm(g["flower"])],["Đã có số thực tế",g["seen"]],["Dự kiến thu",g["left"]],["Thu từ – đến",window]]

@frappe.whitelist()
def trace(farm,block,week,layer="cut",tag=None,cycle=None):
    """Where a number on the weekly forecast comes from: the ledger lines behind it and the parameters used."""
    _farm(farm)
    blocks=_bunch_scope(farm,block=block)
    if block not in blocks:
        frappe.throw("Lô không thuộc vườn đã chọn.")
    lines=_bunch_lines(farm,blocks)
    result,_,_,_=_projection(farm,block=block)
    labels=_tag_labels(farm)
    empty=dict(week=week,block=block,block_code=blocks[block]["code"],layer=layer,note=LAYER_NOTES.get(layer,""),groups=[],lines=[],params=None)
    picked=[]
    for c in _bunch_cohorts(farm,blocks,result["rows"],lines):
        if c["layer"]!=layer or (tag and c["tag"]!=tag) or (cycle and c["cycle"]!=int(cycle)):
            continue
        here=sum(n for day,n in c["days"] if bunch_forecast_engine.week_key(day)==week)
        if here:
            picked.append((c,here))
    if not picked:
        return empty
    groups={}
    for c,here in picked:
        key=c["tag"] or (str(c["cycle"])+"|"+str(c["group"].get("wave") or c["event"] or ""))
        slot=groups.setdefault(key,dict(key=key,ribbon=labels.get(c["tag"],""),in_week=0,facts=_trace_facts(layer,c["group"],c)))
        slot["in_week"]+=here
    types={"cut":("Cut Bud","Reject","Harvest"),"inject":("Bud Injection","Cut Bud","Reject"),"sucker":("Sucker Select",),"tree":()}[layer]
    tags={c["tag"] for c,_ in picked if c["tag"]}
    cycles={c["cycle"] for c,_ in picked}
    rows=[dict(line,event_date=str(line.event_date),ribbon=labels.get(line.bunch_tag,"")) for line in lines
          if line.event_type in types and ((line.bunch_tag in tags) if layer=="cut" else line.cycle_no in cycles)]
    config,profile=picked[0][0]["config"],picked[0][0]["profile"]
    version=frappe.db.get_value("Lotus Block Forecast Profile",profile,"version") if profile else None
    return dict(week=week,block=block,block_code=blocks[block]["code"],layer=layer,note=LAYER_NOTES.get(layer,""),groups=list(groups.values()),lines=rows,
        params=dict(profile=profile,version=version,min_days=config["cut_to_harvest_min_days"],max_days=config["cut_to_harvest_max_days"],
                    harvest_rate=config["harvest_rate"],pack_rate=config["pack_rate"],kg_cycle_2=config["kg_cycle_2"],kg_per_carton=config["kg_per_carton"]))

@frappe.whitelist()
def board(farm=None,zone=None,block=None):
    farms=frappe.get_list("Farm",fields=["name","farm_name"],limit_page_length=0)
    chosen=farm or (farms[0].name if farms else None)
    if not chosen:
        return dict(farms=[],farm=None,rows=[],months=[],warnings=["Không có vườn được cấp quyền."])
    result,blocks,cohorts,profiles=_projection(chosen,zone,block)
    bunch,_=_bunch_weekly(chosen,result["rows"],zone,block)
    actuals=_observations(chosen,block=block)
    block_labels={b.name:b.block_name or b.block_code or b.name for b in blocks}
    for item in actuals:item['farm_block_label']=block_labels.get(item.farm_block,item.farm_block)
    if zone:
        selected_blocks={b.name for b in blocks}
        actuals=[a for a in actuals if a.farm_block in selected_blocks]
    zones=result['zones']
    return dict(farms=farms,farm=chosen,zone=zone or "",block=block or "",
        zone_list=zones,blocks=blocks,cohorts=cohorts,rows=result["rows"],
        months=result["monthly"],warnings=result["warnings"],
        source_count=result["source_count"], rule=result["rule"],
        input_tree_count=result['input_tree_count'],input_block_count=result['input_block_count'],
        horizon_months=36,window_start=result['window_start'],window_end=result['window_end'],
        actuals=actuals,
        profiles=[dict(name=p.name,version=p.version,farm_block=p.farm_block,
                       valid_from=p.valid_from,valid_to=p.valid_to,
                       approved_by=p.approved_by,approval_state=p.approval_state)
                  for p in profiles],
        can_create=frappe.has_permission("Daily Work Plan","create"),
        bunch=bunch,can_import_opening=_can_import_opening(),
        params=validate(DEFAULTS))


def sync_block_dates(doc,method=None):
    """Select the successor at this crop's flowering, not 94 days before."""
    if doc.meta.has_field('lotus_estimated_sucker_selection_date'):
        doc.lotus_estimated_sucker_selection_date=doc.get('lotus_estimated_flowering_date') or None
