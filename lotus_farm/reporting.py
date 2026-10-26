"""Permission-filtered management data and source-level drill-downs."""
from collections import defaultdict
import frappe
from frappe.utils import flt, getdate, add_days, nowdate
from lotus_farm.scoping import land_scope, land_filters
from lotus_farm.rules import forecast_accuracy
from lotus_farm.promax_rules import work_completion, vintage_choice


def records(doctype,filters,fields):
    if not frappe.has_permission(doctype,'read'):
        frappe.throw('Cần quyền xem '+frappe._(doctype),frappe.PermissionError)
    result=frappe.get_list(doctype,filters=filters,fields=fields,limit_page_length=10000)
    if len(result)==10000 and frappe.get_list(doctype,filters=filters,fields=['name'],limit_start=10000,limit_page_length=1):
        frappe.throw('Phạm vi báo cáo vượt 10.000 bản ghi cho '+frappe._(doctype)+'; hãy thu hẹp vườn/khoảng ngày.')
    return result


def scope(farm):
    doc=frappe.get_doc('Farm',farm);doc.check_permission('read');return doc


def packout_lineage(run):
    """Weights are attributed by explicit source input, never by output Item guesswork."""
    run.check_permission('read')
    total=sum(flt(r.input_kg) for r in run.sources)
    sources=[]
    for r in run.sources:
        lot=frappe.get_doc('Harvest Lot',r.harvest_lot);lot.check_permission('read')
        for s in lot.sources:
            actual=frappe.get_doc('Harvest Actual',s.harvest_actual);actual.check_permission('read')
            fraction=flt(r.input_kg)/total*flt(s.contributed_kg)/flt(lot.released_raw_kg) if total and lot.released_raw_kg else 0
            sources.append(dict(harvest_actual=actual.name,harvest_lot=lot.name,farm=actual.farm,
                farm_block=actual.farm_block,farm_plot=actual.farm_plot or frappe.db.get_value("Crop Cycle",actual.crop_cycle,"farm_plot"),crop_cycle=actual.crop_cycle,
                cohort=actual.sucker_selection_batch,harvest_date=str(actual.harvest_date),fraction=fraction))
    return sources


@frappe.whitelist()
def trace_packout(packout):
    run=frappe.get_doc('Packout Run',packout);run.check_permission('read')
    return dict(packout=run.name,farm=run.farm,company=run.company,packing_date=str(run.packing_date),
        sources=packout_lineage(run),outputs=[dict(item=r.item,batch=r.batch,net_kg=r.net_kg,output_type=r.output_type,grade=r.grade,market=r.market) for r in run.outputs],
        stock_entry=run.stock_entry)


@frappe.whitelist()
def trace_item(item,batch=None):
    frappe.get_doc('Item',item).check_permission('read')
    names=records('Packout Run',{'docstatus':1},['name'])
    result=[]
    for r in names:
        run=frappe.get_doc('Packout Run',r.name)
        if any(o.item==item and (not batch or o.batch==batch) for o in run.outputs):result.append(trace_packout(run.name))
    return result


@frappe.whitelist()
def plot_history(farm_plot,from_date=None,to_date=None,crop_cycle=None):
    plot=frappe.get_doc('Farm Plot',farm_plot);plot.check_permission('read')
    selected=land_scope(plot=farm_plot,cycle=crop_cycle)
    cycles=records('Crop Cycle',{'farm_plot':plot.name,**({'name':crop_cycle} if crop_cycle else {})},['name','cycle_no','status','planting_date','variety'])
    result=[]
    definitions=[('Planting Event','posting_date'),('Sucker Selection Batch','selection_date'),('Bunch Operation','operation_date'),
        ('Daily Work Result','posting_date'),('Disease Observation','posting_date'),('Bunch Cancellation','posting_date'),
        ('Fruit Measurement','posting_date'),('Harvest Actual','harvest_date'),('Cycle Closing Report','posting_date'),('Material Consumption','posting_date'),('Labor Allocation','posting_date')]
    for t,date_field in definitions:
        filters={'farm_plot':plot.name,**({'crop_cycle':crop_cycle} if crop_cycle else {})}
        if frappe.get_meta(t).is_submittable:filters['docstatus']=1
        if from_date and to_date:filters[date_field]=['between',[from_date,to_date]]
        elif from_date:filters[date_field]=['>=',from_date]
        elif to_date:filters[date_field]=['<=',to_date]
        for r in records(t,filters,['name',date_field,'crop_cycle']):result.append(dict(doctype=t,name=r.name,date=str(r[date_field]),crop_cycle=r.crop_cycle))
    actual_names={e['name'] for e in result if e['doctype']=='Harvest Actual'}
    lot_names=set()
    for row in records('Harvest Lot',{'farm':plot.farm,'docstatus':1},['name','received_date']):
        lot=frappe.get_doc('Harvest Lot',row.name)
        if any(s.harvest_actual in actual_names for s in lot.sources):
            lot_names.add(lot.name);result.append(dict(doctype='Harvest Lot',name=lot.name,date=str(lot.received_date),crop_cycle=None))
            for q in records('Incoming Quality Inspection',{'harvest_lot':lot.name,'docstatus':1},['name','posting_date']):
                result.append(dict(doctype='Incoming Quality Inspection',name=q.name,date=str(q.posting_date),crop_cycle=None))
    for row in records('Packout Run',{'farm':plot.farm,'docstatus':1},['name','packing_date']):
        run=frappe.get_doc('Packout Run',row.name)
        if any(s.harvest_lot in lot_names for s in run.sources):result.append(dict(doctype='Packout Run',name=run.name,date=str(run.packing_date),crop_cycle=None))
    forecasts=records('Harvest Forecast',{'farm_plot':plot.name,**({'crop_cycle':crop_cycle} if crop_cycle else {})},['name','supply_state','period_start_date','period_end_date','packed_forecast_kg','snapshot_hash','released_at'])
    return dict(plot=plot.name,farm=plot.farm,block=plot.farm_block,cycles=cycles,events=sorted(result,key=lambda r:(r['date'],r['doctype'],r['name'])),forecasts=forecasts)


def _matches_land(source,selected):
    return (not selected.get('zone_blocks') or source.get('farm_block') in selected['zone_blocks']) and all(not selected[key] or source.get(field)==selected[key] for key,field in [('farm','farm'),('block','farm_block'),('plot','farm_plot'),('cycle','crop_cycle')])


def _lot_fraction(name,selected):
    lot=frappe.get_doc('Harvest Lot',name);lot.check_permission('read')
    weight=0
    for source in lot.sources:
        actual=frappe.get_doc('Harvest Actual',source.harvest_actual);actual.check_permission('read')
        values=actual.as_dict()
        values['farm_plot']=actual.farm_plot or frappe.db.get_value('Crop Cycle',actual.crop_cycle,'farm_plot')
        if _matches_land(values,selected):weight+=flt(source.contributed_kg)
    return weight/flt(lot.released_raw_kg) if lot.released_raw_kg else 0


@frappe.whitelist()
def dashboard(from_date,to_date,farm=None,company=None,block=None,plot=None,cycle=None,zone=None):
    start,end=getdate(from_date),getdate(to_date)
    if start>end or (end-start).days>93:frappe.throw('Chọn kỳ báo cáo tối đa 94 ngày.')
    selected=land_scope(company,farm,block,plot,cycle,zone=zone)
    farm=selected['farm'];company=selected['company']
    farms=records('Farm',land_filters(frappe.get_meta('Farm'),selected),['name','company','farm_name'])
    summaries=[]
    settings=frappe.get_single('Lotus Farm Settings')
    for f in farms:
        from lotus_farm.daily_api import daily_overview
        tasks=[];unclosed_dates=[];day=start
        while day<=end:
            overview=daily_overview(f.name,day,block=block,plot=plot,cycle=cycle,zone=zone);tasks.extend(overview['tasks'])
            if not overview['closed']:unclosed_dates.append(str(day))
            day=getdate(add_days(day,1))
        filters={**land_filters(frappe.get_meta('Bunch Cancellation'),{**selected,'farm':f.name}),'docstatus':1,'posting_date':['between',[start,end]]}
        cancels=records('Bunch Cancellation',filters,['name','farm_block','farm_plot','reason','bunch_qty'])
        disease=records('Disease Observation',filters,['name','affected_plants'])
        actuals=records('Harvest Actual',{**land_filters(frappe.get_meta('Harvest Actual'),{**selected,'farm':f.name}),'docstatus':1,'harvest_date':['between',[start,end]]},['name','gross_weight_kg','saleable_weight_kg','harvested_bunch_qty'])
        linked={}
        if zone or block or plot or cycle:
            from lotus_farm.console import _source_scope_names
            linked={'name':['in',_source_scope_names('Incoming Quality Inspection',{**selected,'farm':f.name}) or ['__none__']]}
        qc=records('Incoming Quality Inspection',{'farm':f.name,'docstatus':1,'posting_date':['between',[start,end]],**linked},['name','harvest_lot','received_kg','accepted_kg'])
        runs=records('Packout Run',{'farm':f.name,'docstatus':1,'packing_date':['between',[start,end]],**({'name':['in',_source_scope_names('Packout Run',{**selected,'farm':f.name}) or ['__none__']]} if zone or block or plot or cycle else {})},['name','input_kg','reject_kg','other_loss_kg'])
        finished=secondary=0;fractions={}
        for r in runs:
            run=frappe.get_doc('Packout Run',r.name)
            fraction=sum(s['fraction'] for s in packout_lineage(run) if _matches_land(s,selected)) if zone or block or plot or cycle else 1
            fractions[r.name]=fraction
            finished+=fraction*sum(flt(o.net_kg) for o in run.outputs if o.output_type=='Finished')
            secondary+=fraction*sum(flt(o.net_kg) for o in run.outputs if o.output_type=='Secondary')
        gross=sum(flt(r.gross_weight_kg) for r in actuals);bunches=sum(flt(r.harvested_bunch_qty) for r in actuals)
        qc_fractions={r.name:_lot_fraction(r.harvest_lot,selected) if zone or block or plot or cycle else 1 for r in qc}
        incoming=sum(qc_fractions[r.name]*flt(r.received_kg) for r in qc);accepted=sum(qc_fractions[r.name]*flt(r.accepted_kg) for r in qc)
        raw=sum(fractions[r.name]*flt(r.input_kg) for r in runs)
        shortages=[]
        for r in records('Material Requirement',filters,['name']):
            requirement=frappe.get_doc('Material Requirement',r.name)
            consumption=records('Material Consumption',{'material_requirement':r.name,'docstatus':1},['item','consumed_qty'])
            used=defaultdict(float)
            for c in consumption:used[c.item]+=flt(c.consumed_qty)
            # Outstanding required quantity, not a fake physical stock balance.
            for line in requirement.lines:
                remaining=max(flt(line.required_qty)-used[line.item],0)
                if remaining:shortages.append(dict(requirement=r.name,item=line.item,uom=line.uom,outstanding_qty=remaining))
        labor_gap=sum(flt(t['allocated_workdays'])-flt(t['required_workdays']) for t in tasks)
        loss=sum(fractions[r.name]*(flt(r.reject_kg)+flt(r.other_loss_kg)) for r in runs)
        cancelled=sum(flt(r.bunch_qty) for r in cancels)
        alerts=[]
        if labor_gap<0:alerts.append(dict(kind='Labor',value=labor_gap))
        if settings.dashboard_cancellation_threshold and cancelled>=settings.dashboard_cancellation_threshold:alerts.append(dict(kind='Cancellation',value=cancelled))
        yield_percent=finished/raw*100 if raw else None
        if yield_percent is not None and settings.dashboard_packout_min_percent and yield_percent<settings.dashboard_packout_min_percent:alerts.append(dict(kind='Packout',value=yield_percent))
        affected=sum(flt(r.affected_plants) for r in disease)
        if settings.dashboard_disease_threshold and affected>=settings.dashboard_disease_threshold:alerts.append(dict(kind='Disease observations',value=affected))
        integration=records('Integration Task',{'farm':f.name,'status':'Failed'},['name','sync_error']) if frappe.has_permission('Integration Task','read') else None
        if integration:alerts.append(dict(kind='Integration',value=len(integration)))
        summaries.append(dict(farm=f.name,company=f.company,integration_errors=integration,work_completion_percent=work_completion(tasks),labor_gap_workdays=labor_gap,
            unclosed_dates=unclosed_dates,closed=not unclosed_dates,actual_workdays=sum(flt(t['actual_workdays']) for t in tasks),cancelled_bunches=cancelled,harvest_kg=gross,
            kg_per_bunch=gross/bunches if bunches else None,incoming_defect_percent=(incoming-accepted)/incoming*100 if incoming else None,
            finished_kg=finished,secondary_kg=secondary,loss_kg=loss,packout_input_kg=raw,packout_percent=yield_percent,
            secondary_percent=secondary/raw*100 if raw else None,loss_percent=loss/raw*100 if raw else None,
            outstanding_material=shortages,cancellations=cancels,tasks=tasks,alerts=alerts))
    from lotus_farm.api import availability
    supply=availability(str(start),str(getdate(add_days(end,56))),farm)
    supply=[s for s in supply if (not selected.get('zone_blocks') or s.get('farm_block') in selected['zone_blocks']) and any(f.name==s['farm'] for f in farms) and all(not selected[k] or s.get(field)==selected[k] for k,field in [('block','farm_block'),('plot','farm_plot'),('cycle','crop_cycle')])]
    return dict(from_date=str(start),to_date=str(end),farms=summaries,forecast=supply,metric_note='Tỷ lệ hoàn thành tính bình quân theo công việc. Vật tư còn thiếu là nhu cầu chưa dùng, không phải thiếu tồn kho. Khối lượng QC/đóng gói trong phạm vi được phân bổ theo nguồn đóng góp đã khai báo.')


@frappe.whitelist()
def forecast_vintages(from_date,to_date,farm=None,company=None,block=None,plot=None,cycle=None,zone=None):
    start,end=getdate(from_date),getdate(to_date)
    if start>end or (end-start).days>366:frappe.throw('Chọn tối đa một năm.')
    filters={'period_start_date':['>=',start],'period_end_date':['<=',end],'supply_state':['!=','Draft']}
    selected=land_scope(company,farm,block,plot,cycle,zone=zone)
    filters.update(land_filters(frappe.get_meta('Harvest Forecast'),selected))
    snapshots=records('Harvest Forecast',filters,['name','farm','farm_plot','crop_cycle','sucker_selection_batch','period_start_date','period_end_date','released_at','revision_no','packed_forecast_kg','snapshot_hash'])
    groups=defaultdict(list)
    for s in snapshots:
        if s.released_at:groups[(s.farm,s.farm_plot,s.crop_cycle,s.sucker_selection_batch,str(s.period_start_date),str(s.period_end_date))].append(s)
    rows=[]
    for key,versions in groups.items():
        f,plot,cycle,cohort,begin,finish=key
        if getdate(finish)>=getdate(nowdate()):continue
        actuals=records('Harvest Actual',{'farm':f,'crop_cycle':cycle,'sucker_selection_batch':cohort or '', 'docstatus':1,'harvest_date':['between',[begin,finish]]},['name'])
        names={a.name for a in actuals};actual_finished=0;matched=set()
        for r in records('Packout Run',{'farm':f,'docstatus':1},['name']):
            run=frappe.get_doc('Packout Run',r.name)
            if not run.stock_entry or frappe.db.get_value('Stock Entry',run.stock_entry,'docstatus')!=1:continue
            amount=sum(flt(o.net_kg) for o in run.outputs if o.output_type=='Finished')
            for s in packout_lineage(run):
                if s['harvest_actual'] in names:actual_finished+=amount*s['fraction'];matched.add(s['harvest_actual'])
        # Explicitly do not call missing or unfinished receiving/packout a zero actual.
        complete=(bool(names) and matched==names) or (not names and bool(records('Cycle Closing Report',{'crop_cycle':cycle,'docstatus':1},['name'])))
        for a in actuals:
            if not _actual_fully_processed(a.name):complete=False
        for horizon in (8,4,2,1):
            selected=vintage_choice(versions,begin,horizon)
            if not selected:continue
            previous=sorted(versions,key=lambda s:(str(s.released_at),s.name))
            index=next(i for i,s in enumerate(previous) if s.name==selected['name'])
            forecast=flt(selected['packed_forecast_kg'])
            rows.append(dict(farm=f,farm_plot=plot,crop_cycle=cycle,cohort=cohort,period_start=begin,period_end=finish,
                variety=frappe.db.get_value('Crop Cycle',cycle,'variety'),horizon_weeks=horizon,forecast=selected['name'],snapshot_hash=selected['snapshot_hash'],forecast_kg=forecast,
                actual_kg=actual_finished if complete else None,absolute_error_kg=abs(forecast-actual_finished) if complete else None,
                signed_error_kg=forecast-actual_finished if complete else None,
                change_kg=forecast-flt(previous[index-1].packed_forecast_kg) if index else None,
                status='Complete' if complete else 'Incomplete actual lineage'))
    metrics={str(h):forecast_accuracy([(r['forecast_kg'],r['actual_kg']) for r in rows if r['horizon_weeks']==h and r['actual_kg'] is not None]) for h in (8,4,2,1)}
    return dict(rows=rows,metrics=metrics)


def _actual_fully_processed(name):
    actual=frappe.get_doc('Harvest Actual',name);actual.check_permission('read')
    received=0
    for l in records('Harvest Lot',{'farm':actual.farm,'docstatus':1},['name']):
        lot=frappe.get_doc('Harvest Lot',l.name)
        contribution=sum(flt(s.contributed_kg) for s in lot.sources if s.harvest_actual==name)
        if not contribution:continue
        qc=records('Incoming Quality Inspection',{'harvest_lot':lot.name,'docstatus':1},['accepted_kg'])
        if not qc:return False
        packed=0
        for r in records('Packout Run',{'farm':actual.farm,'docstatus':1},['name','stock_entry']):
            run=frappe.get_doc('Packout Run',r.name)
            if r.stock_entry and frappe.db.get_value('Stock Entry',r.stock_entry,'docstatus')==1:
                packed+=sum(flt(s.input_kg) for s in run.sources if s.harvest_lot==lot.name)
        if abs(packed-sum(flt(q.accepted_kg) for q in qc))>0.0005:return False
        received+=contribution
    return abs(received-flt(actual.saleable_weight_kg))<=0.0005


@frappe.whitelist()
def dataset(from_date,to_date,farm=None,company=None,block=None,plot=None,cycle=None,zone=None):
    """Authenticated JSON dataset for Power BI; permission checks are the same as Desk."""
    return dashboard(from_date,to_date,farm=farm,company=company,block=block,plot=plot,cycle=cycle,zone=zone)


@frappe.whitelist()
def delivery_progress(farm):
    scope(farm)
    result=[]
    for f in records('Harvest Forecast',{'farm':farm},['name']):
        forecast=frappe.get_doc('Harvest Forecast',f.name)
        for a in forecast.allocations:
            order=frappe.get_doc('Sales Order',a.sales_order);order.check_permission('read')
            line=next((i for i in order.items if i.name==a.sales_order_item),None)
            if not line:continue
            reservation=None
            if a.stock_reservation:
                doc=frappe.get_doc('Stock Reservation Entry',a.stock_reservation);doc.check_permission('read')
                reservation=dict(name=doc.name,reserved_kg=doc.reserved_qty,delivered_kg=doc.delivered_qty,docstatus=doc.docstatus)
            result.append(dict(forecast=f.name,allocation=a.name,state=a.allocation_state,allocated_kg=a.reserved_qty_kg,
                sales_order=order.name,sales_order_item=line.name,item=line.item_code,ordered_kg=line.stock_qty,
                delivered_kg=flt(line.delivered_qty)*flt(line.conversion_factor),remaining_demand_kg=max(flt(line.stock_qty)-flt(line.delivered_qty)*flt(line.conversion_factor),0),
                stock_reservation=reservation))
    return result


@frappe.whitelist()
def trace_lot(harvest_lot):
    lot=frappe.get_doc('Harvest Lot',harvest_lot);lot.check_permission('read')
    sources=[]
    for s in lot.sources:
        actual=frappe.get_doc('Harvest Actual',s.harvest_actual);actual.check_permission('read')
        cycle=frappe.get_doc('Crop Cycle',actual.crop_cycle);cycle.check_permission('read')
        sources.append(dict(harvest_actual=actual.name,contributed_kg=s.contributed_kg,company=lot.company,farm=actual.farm,
            farm_block=actual.farm_block,farm_plot=actual.farm_plot or cycle.farm_plot,crop_cycle=cycle.name,cohort=actual.sucker_selection_batch))
    qc=records('Incoming Quality Inspection',{'harvest_lot':lot.name,'docstatus':1},['name','received_kg','accepted_kg','rejected_kg'])
    runs=[]
    for r in records('Packout Run',{'farm':lot.farm,'docstatus':1},['name']):
        if any(s.harvest_lot==lot.name for s in frappe.get_doc('Packout Run',r.name).sources):runs.append(r.name)
    return dict(lot=lot.name,sources=sources,qc=qc,packout=runs,packout_documents=[dict(name=n,**frappe.db.get_value('Packout Run',n,['packing_date','stock_entry'],as_dict=True)) for n in runs])


@frappe.whitelist()
def packhouse_day(farm,posting_date):
    scope(farm);date=getdate(posting_date);lots=[]
    for row in records('Harvest Lot',{'farm':farm,'docstatus':1,'received_date':['between',[add_days(date,-30),date]]},['name','received_date','released_raw_kg']):
        qc=records('Incoming Quality Inspection',{'harvest_lot':row.name,'docstatus':1},['name','accepted_kg','rejected_kg'])
        processed=0
        for r in records('Packout Run',{'farm':farm,'docstatus':1},['name']):
            processed+=sum(flt(s.input_kg) for s in frappe.get_doc('Packout Run',r.name).sources if s.harvest_lot==row.name)
        row.update(qc=qc[0].name if qc else None,accepted_kg=qc[0].accepted_kg if qc else None,
            remaining_to_pack_kg=max(flt(qc[0].accepted_kg)-processed,0) if qc else None)
        lots.append(row)
    return dict(lots=lots,runs=records('Packout Run',{'farm':farm,'docstatus':['<',2],'packing_date':date},['name','docstatus','input_kg','output_kg','mass_variance_kg','stock_entry']),
        defects=frappe.get_list('Defect Reason',filters={'active':1},fields=['name','defect_name'],limit_page_length=1000))


def _section(build):
    """One chart section; a missing read permission hides that section instead of failing the page."""
    try:
        return dict(allowed=True,**build())
    except frappe.PermissionError:
        frappe.clear_messages()
        return dict(allowed=False)


@frappe.whitelist()
def charts(from_date,to_date,farm=None,company=None,block=None,plot=None,cycle=None,zone=None,report_filters=None):
    """Aggregated series for the report charts. Same land scope and permissions as dashboard()."""
    from lotus_farm import report_charts as rc
    start,end=getdate(from_date),getdate(to_date)
    if start>end or (end-start).days>365:frappe.throw('Chọn kỳ báo cáo tối đa 366 ngày.')
    selected=land_scope(company,farm,block,plot,cycle,zone=zone)
    farms=[f.name for f in records('Farm',land_filters(frappe.get_meta('Farm'),selected),['name'])]
    in_farms={'farm':['in',farms or ['__none__']]}
    land_only=bool(zone or block or plot or cycle)
    report_filters=frappe.parse_json(report_filters or '{}')
    if not isinstance(report_filters,dict):frappe.throw('Bộ lọc báo cáo không hợp lệ')
    def choices(rows,field):return sorted({r.get(field) for r in rows if r.get(field)})
    def matching(rows,fields):
        return [r for r in rows if all(not report_filters.get(key) or r.get(field)==report_filters[key] for key,field in fields.items())]

    def land():
        meta=frappe.get_meta('Farm Block')
        fields=['name','farm_zone','area_ha']+[f for f in ('lotus_tree_count','lotus_estimated_flowering_date') if meta.has_field(f)]
        blocks=records('Farm Block',{**land_filters(meta,selected),**({} if selected['farm'] else in_farms)},fields)
        return dict(zones=rc.land_by_zone(blocks),flowering=rc.flowering_by_month(blocks),blocks=len(blocks),
            area_ha=sum(flt(b.area_ha) for b in blocks),trees=sum(flt(b.get('lotus_tree_count')) for b in blocks),
            counted_blocks=sum(1 for b in blocks if flt(b.get('lotus_tree_count'))>0))

    def work():
        # daily_overview is per farm and day; keep the window small like dashboard().
        if (end-start).days>93:return dict(days=None,types=None,note='Chọn tối đa 94 ngày để xem công việc theo ngày.')
        from lotus_farm.daily_api import daily_overview
        days,all_tasks=[],[]
        day=start
        while day<=end:
            tasks=[t for f in farms for t in daily_overview(f,day,block=block,plot=plot,cycle=cycle,zone=zone)['tasks']]
            days.append((day,tasks));all_tasks.extend(tasks)
            day=getdate(add_days(day,1))
        return dict(days=rc.work_by_day(days),types=rc.work_by_type(all_tasks))

    def harvest():
        actuals=records('Harvest Actual',{**land_filters(frappe.get_meta('Harvest Actual'),selected),**in_farms,'docstatus':1,'harvest_date':['between',[start,end]]},['harvest_date','gross_weight_kg','saleable_weight_kg'])
        result=dict(harvest=rc.weekly(actuals,'harvest_date',['gross_weight_kg','saleable_weight_kg'],start,end),packout=None,qc=None)
        if land_only:
            # QC and packout mix lots from many plots; dashboard() attributes them by lineage, charts stay at farm level.
            result['note']='QC và đóng gói chỉ xem theo vườn, không chia theo lô/thửa.'
            return result
        qc=records('Incoming Quality Inspection',{**in_farms,'docstatus':1,'posting_date':['between',[start,end]]},['posting_date','received_kg','accepted_kg'])
        result['qc']=rc.weekly(qc,'posting_date',['received_kg','accepted_kg'],start,end)
        runs=records('Packout Run',{**in_farms,'docstatus':1,'packing_date':['between',[start,end]]},['name','packing_date','input_kg'])
        rows=[]
        for r in runs:
            run=frappe.get_doc('Packout Run',r.name)
            rows.append(dict(packing_date=r.packing_date,input_kg=r.input_kg,finished_kg=sum(flt(o.net_kg) for o in run.outputs if o.output_type=='Finished')))
        result['packout']=rc.weekly(rows,'packing_date',['input_kg','finished_kg'],start,end)
        return result

    def losses():
        rows=records('Bunch Cancellation',{**land_filters(frappe.get_meta('Bunch Cancellation'),selected),**in_farms,'docstatus':1,'posting_date':['between',[start,end]]},['reason','bunch_qty'])
        return dict(reasons=rc.top_totals(rows,'reason','bunch_qty'),total=sum(flt(r.bunch_qty) for r in rows))

    def stock():
        filters={'docstatus':1,'posting_date':['between',[start,end]],**({'company':selected['company']} if selected['company'] else {})}
        if selected['farm'] and not selected['company']:
            filters['company']=frappe.db.get_value('Farm',selected['farm'],'company')
        rows=records('Stock Entry',filters,['posting_date','stock_entry_type'])
        options=dict(stock_type=choices(rows,'stock_entry_type'))
        return dict(scope_label='Toàn công ty',options=options,months=rc.stock_by_month(matching(rows,{'stock_type':'stock_entry_type'})))

    def people():
        companies={frappe.db.get_value('Farm',f,'company') for f in farms}
        employees=records('Employee',{'company':['in',list(companies)],
            **({'lotus_farm':farm} if farm else {})},['name','status','lotus_onboarding_state','lotus_worker_category','department'])
        options=dict(department=choices(employees,'department'),worker_category=choices(employees,'lotus_worker_category'))
        employees=matching(employees,{'department':'department','worker_category':'lotus_worker_category'})
        names=[e.name for e in employees]
        attendance=records('Attendance',{'employee':['in',names or ['__none__']],
            'docstatus':1,'attendance_date':['between',[start,end]]},['status'])
        slips=records('Salary Slip',{'employee':['in',names or ['__none__']],
            'docstatus':1,'start_date':['<=',end],'end_date':['>=',start]},['currency','net_pay'])
        payroll={}
        for slip in slips:payroll[slip.currency]=payroll.get(slip.currency,0)+flt(slip.net_pay)
        from collections import Counter
        return dict(scope_label='Theo vườn' if farm else 'Toàn công ty',options=options,employees=len(employees),active=sum(e.status=='Active' for e in employees),
            pending=sum(e.lotus_onboarding_state!='Ready' for e in employees),
            attendance=[dict(status=k,count=v) for k,v in Counter(a.status for a in attendance).items()],
            payroll=[dict(currency=k,net=v) for k,v in payroll.items()],salary_slips=len(slips))

    def orders(doctype):
        companies={frappe.db.get_value('Farm',f,'company') for f in farms}
        kind='buying' if doctype=='Purchase Order' else 'sales'
        party='supplier' if kind=='buying' else 'customer'
        rows=records(doctype,{'company':['in',list(companies)],'docstatus':1,
            'transaction_date':['between',[start,end]]},['name','status','currency','grand_total',party])
        options={kind+'_status':choices(rows,'status'),party:choices(rows,party)}
        rows=matching(rows,{kind+'_status':'status',party:party})
        from collections import Counter
        totals={}
        for row in rows:totals[row.currency]=totals.get(row.currency,0)+flt(row.grand_total)
        return dict(scope_label='Toàn công ty',options=options,count=len(rows),statuses=[dict(status=k,count=v) for k,v in Counter(r.status for r in rows).items()],
                    totals=[dict(currency=k,value=v) for k,v in totals.items()])

    return dict(from_date=str(start),to_date=str(end),farms=farms,land=_section(land),work=_section(work),
        harvest=_section(harvest),losses=_section(losses),stock=_section(stock),people=_section(people),
        buying=_section(lambda:orders('Purchase Order')),sales=_section(lambda:orders('Sales Order')))
