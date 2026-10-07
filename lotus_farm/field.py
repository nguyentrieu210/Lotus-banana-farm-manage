"""Small, retry-safe field commands and explicit work suggestions."""
import json
import frappe
from frappe.utils import getdate, add_days, now_datetime, flt
from lotus_farm.controls import require_role, lock, command, local_timestamp
from lotus_farm.rules import canonical_hash
from lotus_farm.promax_rules import coordinates, point_in_geometry
from lotus_farm.importing import IMPORT_FIELDS

CAPTURE_TYPES=('Daily Work Result','Bunch Cancellation','Disease Observation','Fruit Measurement','Planting Event','Harvest Actual','Bunch Operation')


@frappe.whitelist()
def bootstrap(farm,posting_date):
    from lotus_farm.daily_api import daily_overview
    from lotus_farm.reporting import records
    result=daily_overview(farm,posting_date)
    result.update(user=frappe.session.user,
        reasons=frappe.get_list('Cancellation Reason',filters={'active':1},fields=['name','reason_name'],limit_page_length=1000),
        diseases=frappe.get_list('Disease',filters={'active':1},fields=['name','disease_name'],limit_page_length=1000),
        cycles=records('Crop Cycle',{'farm':farm,'status':['!=','Closed']},['name','farm_block','farm_plot','cycle_type']),
        cohorts=records('Sucker Selection Batch',{'farm':farm},['name','crop_cycle']),
        geometries=map_data(farm)['features'])
    return result


@frappe.whitelist()
def map_data(farm):
    from lotus_farm.reporting import records,scope
    scope(farm)
    versions=records('Plot Geometry',{'farm':farm,'approval_state':'Approved'},['name','farm_plot','version','geojson'])
    latest={}
    for r in versions:
        if r.farm_plot not in latest or r.version>latest[r.farm_plot].version:latest[r.farm_plot]=r
    return dict(type='FeatureCollection',features=[dict(type='Feature',geometry=json.loads(r.geojson),properties=dict(plot=r.farm_plot,version=r.version,document=r.name)) for r in latest.values()])


@frappe.whitelist(methods=['POST'])
def capture(client_event_id,farm,target_doctype,values,captured_at,latitude=None,longitude=None,gps_accuracy_m=None,photo=None):
    require_role('Lotus Farm Manager','Lotus Integration User')
    frappe.get_doc('Farm',farm).check_permission('read');lock('Farm',farm)
    if not client_event_id or target_doctype not in CAPTURE_TYPES:frappe.throw('Select a supported field event and an event ID.')
    values=json.loads(values) if isinstance(values,str) else values
    if not isinstance(values,dict) or any(k not in IMPORT_FIELDS[target_doctype] for k in values):frappe.throw('Unsupported field event fields.')
    if (latitude is None)!=(longitude is None):frappe.throw('Provide both GPS coordinates, or neither.')
    if latitude is not None:coordinates(latitude,longitude)
    captured_at=str(local_timestamp(captured_at))
    if photo:
        names=frappe.get_all('File',filters={'file_url':photo,'owner':frappe.session.user,'is_private':1},pluck='name')
        if not names:frappe.throw('Use a private photo uploaded by the signed-in user.')
        frappe.get_doc('File',names[0]).check_permission('read')
    payload=dict(target_doctype=target_doctype,values=values,farm=farm,captured_at=captured_at,latitude=latitude,longitude=longitude,gps_accuracy_m=gps_accuracy_m,photo=photo)
    key=canonical_hash([frappe.session.user,client_event_id]);hashed=canonical_hash(payload)
    existing=frappe.db.get_value('Field Capture',{'event_key':key},'name')
    if existing:
        previous=frappe.get_doc('Field Capture',existing);previous.check_permission('read')
        if previous.payload_hash!=hashed:frappe.throw('Event ID already has a different payload; preserve the original event or use a new ID.')
        return dict(capture=previous.name,document=previous.target_name,replayed=True)
    doc=frappe.get_doc(dict(doctype=target_doctype,**values,farm=farm)).insert()
    doc.submit()
    evidence=frappe.get_doc(dict(doctype='Field Capture',farm=farm,client_event_id=client_event_id,captured_by=frappe.session.user,
        captured_at=captured_at,latitude=latitude,longitude=longitude,gps_accuracy_m=gps_accuracy_m,photo=photo,
        payload_json=json.dumps(payload,sort_keys=True,default=str),target_doctype=doc.doctype,target_name=doc.name))
    with command(evidence,'field_capture'):evidence.insert()
    frappe.db.set_value(doc.doctype,doc.name,'field_capture',evidence.name,update_modified=False)
    warning=None
    if latitude is not None and doc.get('farm_plot'):
        match=next((g for g in map_data(farm)['features'] if g['properties']['plot']==doc.farm_plot),None)
        if match and not point_in_geometry(latitude,longitude,match['geometry']):warning='GPS is outside the approved Plot boundary; review the capture.'
    return dict(capture=evidence.name,document=doc.name,replayed=False,warning=warning)


@frappe.whitelist()
def suggest_work(farm,posting_date):
    from lotus_farm.reporting import records,scope
    scope(farm);date=getdate(posting_date);suggestions=[]
    rules=records('Work Schedule Rule',{'farm':farm,'approval_state':'Approved','valid_from':['<=',date],'valid_to':['>=',date]},['name','work_type','anchor','offset_days','repeat_days','quantity_basis','norm_profile'])
    for c in records('Crop Cycle',{'farm':farm,'status':['in',['Active','Harvesting']]},['name','farm_block','farm_plot','cycle_type','planting_date']):
        if not c.farm_plot:continue
        cohorts=records('Sucker Selection Batch',{'crop_cycle':c.name},['name','selection_date','selected_sucker_qty'])
        contexts=cohorts if c.cycle_type=='Ratoon' else [frappe._dict(name=None,selection_date=None,selected_sucker_qty=None)]
        for cohort in contexts:
            for rule in rules:
                anchors=[]
                if rule.anchor=='Planting' and c.planting_date:anchors=[(str(c.planting_date),c.name,None)]
                elif rule.anchor=='Selection' and cohort.selection_date:anchors=[(str(cohort.selection_date),cohort.name,cohort.selected_sucker_qty)]
                elif rule.anchor in ('Shooting','Cut Bud'):
                    anchors=[(str(o.operation_date),o.name,o.net_bunch_qty) for o in records('Bunch Operation',{'crop_cycle':c.name,'sucker_selection_batch':cohort.name or '', 'operation_type':rule.anchor,'docstatus':1},['name','operation_date','net_bunch_qty'])]
                for anchor,key,qty in anchors:
                    due=getdate(add_days(anchor,rule.offset_days));days=(date-due).days
                    if days<0 or (days and (not rule.repeat_days or days%rule.repeat_days)):continue
                    if rule.quantity_basis=='Area':qty=frappe.db.get_value('Farm Plot',c.farm_plot,'area_ha')
                    elif rule.quantity_basis=='Selected Suckers':qty=cohort.selected_sucker_qty
                    elif rule.quantity_basis=='Trees':
                        qty=sum(flt(p.plant_qty) for p in records('Planting Event',{'crop_cycle':c.name,'docstatus':1,'posting_date':['<=',date]},['plant_qty']))
                    if not qty:continue
                    schedule_key=canonical_hash([rule.name,key,str(date),cohort.name])
                    # Permission-filtered parents prevent an inaccessible plan from leaking.
                    planned=False
                    for p in records('Daily Work Plan',{'farm':farm,'posting_date':date,'docstatus':['<',2]},['name']):
                        if any(l.schedule_key==schedule_key for l in frappe.get_doc('Daily Work Plan',p.name).lines):planned=True
                    if not planned:suggestions.append(dict(farm_block=c.farm_block,farm_plot=c.farm_plot,crop_cycle=c.name,sucker_selection_batch=cohort.name,
                        work_type=rule.work_type,planned_qty=qty,norm_profile=rule.norm_profile,schedule_key=schedule_key,rule=rule.name))
    return suggestions


@frappe.whitelist(methods=['POST'])
def make_suggested_plan(farm,posting_date):
    require_role('Lotus Farm Manager');lock('Farm',farm)
    suggestions=suggest_work(farm,posting_date)
    if not suggestions:frappe.throw('No unplanned due tasks for this day.')
    doc=frappe.get_doc(dict(doctype='Daily Work Plan',farm=farm,posting_date=posting_date,
        lines=[{k:v for k,v in r.items() if k!='rule'} for r in suggestions])).insert()
    return dict(plan=doc.name,docstatus=doc.docstatus,tasks=len(doc.lines))


@frappe.whitelist()
def available_labor(farm,posting_date):
    from lotus_farm.reporting import scope,records
    company=scope(farm).company;date=getdate(posting_date)
    employees=frappe.get_list('Employee',filters={'company':company,'status':'Active'},fields=['name','employee_name'],limit_page_length=10000)
    attendance_available=bool(frappe.db.exists('DocType','Attendance')) and frappe.has_permission('Attendance','read')
    result=[]
    for e in employees:
        attendance=frappe.get_list('Attendance',filters={'employee':e.name,'attendance_date':date,'docstatus':1},fields=['name','status','shift'],limit_page_length=100) if attendance_available else []
        used=sum(flt(v) for v in frappe.get_all('Labor Allocation',filters={'employee':e.name,'posting_date':date,'docstatus':1},pluck='allocated_workdays'))
        statuses={a.status for a in attendance}
        capacity=0 if statuses.intersection({'Absent','On Leave'}) else (0.5 if 'Half Day' in statuses else 1)
        result.append(dict(employee=e.name,employee_name=e.employee_name,attendance=attendance,
            attendance_known=bool(attendance),remaining_workdays=max(capacity-used,0)))
    return dict(farm=farm,date=str(date),attendance_installed=attendance_available,employees=result,
        note='No attendance record means unknown presence; remaining workdays is allocation capacity, not verified attendance.')


@frappe.whitelist()
def session_info():
    if frappe.session.user=='Guest':frappe.throw('Sign in before opening Lotus field capture.',frappe.AuthenticationError)
    from frappe.sessions import get_csrf_token
    return dict(user=frappe.session.user,csrf_token=get_csrf_token(),capabilities=dict(
        field=frappe.has_permission('Daily Work Result','create'),
        home=all(frappe.has_permission(t,'read') for t in ('Daily Work Plan','Daily Work Result','Labor Allocation','Daily Labor Summary','Bunch Cancellation','Disease Observation','Harvest Actual','Incoming Quality Inspection','Packout Run','Material Requirement','Material Consumption','Harvest Forecast')),
        packhouse=frappe.has_permission('Harvest Lot','read'),
        imports=frappe.has_permission('Source Import Mapping','read'),map=frappe.has_permission('Plot Geometry','read'),
        qc=frappe.has_permission('Incoming Quality Inspection','create'),
        scale=(frappe.session.user=='Administrator' or 'Lotus Integration User' in frappe.get_roles())),farms=frappe.get_list('Farm',fields=['name','farm_name'],limit_page_length=1000))


@frappe.whitelist(methods=['POST'])
def preview_kml(file_url):
    require_role('Lotus Farm Manager')
    from lotus_farm.importing import file_bytes
    from lotus_farm.promax_rules import kml_geometries
    return kml_geometries(file_bytes(file_url))


@frappe.whitelist()
def lot_qr(harvest_lot):
    frappe.get_doc('Harvest Lot',harvest_lot).check_permission('read')
    import base64
    import qrcode
    from qrcode.image.svg import SvgPathImage
    from urllib.parse import quote
    from frappe.utils import get_url
    url=get_url('/app/harvest-lot/'+quote(harvest_lot,safe=''))
    image=qrcode.make(url,image_factory=SvgPathImage)
    return dict(harvest_lot=harvest_lot,url=url,image='data:image/svg+xml;base64,'+base64.b64encode(image.to_string()).decode())


@frappe.whitelist()
def capture_status(client_event_id):
    require_role('Lotus Farm Manager','Lotus Integration User')
    name=frappe.db.get_value('Field Capture',{'event_key':canonical_hash([frappe.session.user,client_event_id])},'name')
    if not name:return dict(received=False)
    doc=frappe.get_doc('Field Capture',name);doc.check_permission('read')
    return dict(received=True,capture=doc.name,document=doc.target_name)
