"""Regression on a disposable restored site only; every fixture rolls back."""
import json
import os
import uuid
import frappe
from frappe.utils import getdate

os.chdir('/home/frappe/frappe-bench/sites')
frappe.init(site=os.environ.get('LOTUS_HR_TEST_SITE','hr.test'),sites_path='.')
frappe.connect()
assert frappe.conf.lotus_hr_audit_disposable,'Never run this suite on a live site'
frappe.set_user('Administrator')
frappe.in_test=True
frappe.flags.in_test=True
from lotus_farm import attendance_day as ad,hr_operations as ops,hr_period as hp,hr_payroll as pay,hr_workspace as hr,shift_admin as sa,timekeeping as t,signing
from frappe.permissions import add_permission,update_permission_property

tag=uuid.uuid4().hex[:6]
report={}
company=frappe.db.get_value('Company',{},'name')
day='2026-10-10'

def employee(label,org=company,joined='2026-09-01'):
    name=t.create_employee(org,dict(employee_name='AUDIT '+label+' '+tag,gender='Male',date_of_birth='1990-01-01',date_of_joining=joined,designation='AUDIT '+tag))['name']
    frappe.db.set_value('Employee',name,dict(status='Active',lotus_onboarding_state='Ready',lotus_worker_category='Permanent',lotus_payment_basis='Monthly',lotus_base_salary=10400000))
    return name

def rejected(fn,*args,**kwargs):
    try:fn(*args,**kwargs)
    except frappe.ValidationError:return True
    return False

def punch(person,time,kind,date=day):
    return frappe.get_doc(dict(doctype='Employee Checkin',employee=person,time=date+' '+time,log_type=kind)).insert()

try:
    settings=frappe.get_single('HR Settings')
    field=next((f.fieldname for f in settings.meta.fields if 'multiple' in f.fieldname and 'shift' in f.fieldname),None)
    if field:settings.set(field,1);settings.save()
    morning=sa.create_shift(company,'AUDIT AM '+tag,dict(start_time='07:00',end_time='11:00',check_in_before=30,check_out_after=90,half_day_hours=2,absent_hours=1))['name']
    afternoon=sa.create_shift(company,'AUDIT PM '+tag,dict(start_time='13:00',end_time='17:00',check_in_before=30,check_out_after=60,half_day_hours=2,absent_hours=1))['name']
    night=sa.create_shift(company,'AUDIT NIGHT '+tag,dict(start_time='22:00',end_time='06:00',check_in_before=60,check_out_after=120,half_day_hours=4,absent_hours=2))['name']
    a,b,manual,left,no_shift,night_worker=[employee(label) for label in ['two shifts','invalid pair','manual overtime','former','unassigned','night']]
    for person,shifts in [(a,[morning,afternoon]),(b,[morning]),(manual,[morning]),(left,[morning]),(night_worker,[night])]:
        result=sa.set_roster(company,[dict(employee=person,**{'from':day,'to':day},shifts=shifts)])
        assert not result['errors'],result
    for hh,kind in [('07:00','IN'),('11:00','OUT'),('13:00','IN'),('17:00','OUT')]:punch(a,hh,kind)
    for hh in ['07:00','11:00']:punch(b,hh,'IN')
    for hh,kind in [('07:00','IN'),('12:00','OUT')]:punch(manual,hh,kind)
    for hh,kind in [('07:00','IN'),('17:00','OUT')]:punch(no_shift,hh,kind)
    punch(night_worker,'22:00','IN');punch(night_worker,'06:30','OUT','2026-10-11')
    rows=t.staff_day(company,day,shift=afternoon)['rows']
    assert [(r['employee'],r['shift']) for r in rows]==[(a,afternoon)],rows
    board=ad.board(company,day,search=tag,sync=0)
    own={r['row_key']:r for r in board['rows']}
    assert len([r for r in board['rows'] if r['employee']==a])==2
    assert next(r for r in board['rows'] if r['employee']==b)['machine']['needs_review']
    assert not next(r for r in board['rows'] if r['employee']==no_shift)['matches']
    assert next(r for r in board['rows'] if r['employee']==night_worker)['machine']['next_day']
    record=next(r for r in board['rows'] if r['employee']==manual)
    machine=record['machine']
    t.save_staff(company,day,[dict(employee=manual,shift=morning,status=machine['status'],working_hours=machine['working_hours'],overtime_hours=0,in_time=machine['in_time'],out_time=machine['out_time'],late_entry=machine['late_entry'],early_exit=machine['early_exit'])],'manual-'+tag)
    board=ad.board(company,day,search=tag,sync=0)
    record=next(r for r in board['rows'] if r['employee']==manual)
    assert record['manual'] and not record['matches'],record
    approved_rows=[dict(row_key=r['row_key'],review_hash=r['review_hash']) for r in board['rows'] if r['employee']==a]
    changed=frappe.get_doc('Employee Checkin',frappe.db.get_value('Employee Checkin',{'employee':a,'time':day+' 11:00:00'},'name'))
    changed.time=day+' 11:05:00';changed.save()
    assert rejected(ad.approve_matching,company,day,'stale-'+tag,reviewed_rows=approved_rows)
    changed.time=day+' 11:00:00';changed.save()
    board=ad.board(company,day,search=tag,sync=0)
    reviewed=[dict(row_key=r['row_key'],review_hash=r['review_hash']) for r in board['rows'] if r['employee']==a]
    result=ad.approve_matching(company,day,'approve-'+tag,reviewed_rows=reviewed)
    assert result['approved']==2,result
    total=next(r for r in t.monthly(company,'2026-10')['rows'] if r['employee']==a)
    assert total['working_hours']==8 and total['workdays']==1,total
    report['shift_filter_multi_pair_stale_and_manual_ot']='passed'

    # Real permission checks, with read access and no Attendance.create.
    role='AUDIT VIEW '+tag
    frappe.get_doc(dict(doctype='Role',role_name=role)).insert()
    for doctype in ['Attendance','Employee','Employee Checkin','Company','Shift Type']:
        add_permission(doctype,role)
        update_permission_property(doctype,role,0,'read',1)
    add_permission('Employee Checkin',role,permlevel=1)
    update_permission_property('Employee Checkin',role,1,'read',1)
    reader=frappe.get_doc(dict(doctype='User',email='audit-view-'+tag+'@example.invalid',first_name='AUDIT Viewer',send_welcome_email=0,roles=[dict(role=role)])).insert(ignore_permissions=True)
    frappe.set_user(reader.name)
    assert not frappe.has_permission('Attendance','create')
    readable=ad.board(company,day,search=tag,sync=0)
    assert readable['rows'] and readable['machine_readable']
    frappe.set_user('Administrator')
    report['readonly_board']='passed'

    # Former employees retain their historical days and late device identity.
    farm=t.create_farm(company,'AUDIT-'+tag,'AUDIT '+tag)['name']
    device=ops.save_device(company,dict(farm=farm,device_code='AUDIT-'+tag,device_name='AUDIT '+tag))['name']
    identity=frappe.get_doc(dict(doctype='Lotus Attendance Identity',company=company,farm=farm,device=device,device_user_id='LEFT'+tag,employee=left,valid_from='2026-09-01',active=1)).insert()
    person=frappe.get_doc('Employee',left)
    hr.offboard_employee(company,left,'2026-10-15','AUDIT employment ended',str(person.modified))
    saved=t.save_staff(company,day,[dict(employee=left,shift=morning,status='Half Day',working_hours=4,overtime_hours=0)],'left-'+tag)
    doc=frappe.get_doc('Attendance',saved['names'][0]);doc.submit()
    assert doc.docstatus==1
    assert any(r['employee']==left for r in t.staff_day(company,day)['rows'])
    assert rejected(t.save_staff,company,'2026-10-16',[dict(employee=left,status='Present',working_hours=8)],'after-left-'+tag)
    ops.ingest_device_events(company,device,[dict(device_user_id='LEFT'+tag,punched_at=day+' 07:00:00',log_type='IN')])
    ops.sync_ready_checkins(company,day,day)
    assert frappe.db.get_value('Lotus Attendance Punch',{'device':device,'device_user_id':'LEFT'+tag},'state')=='Synced'
    assert frappe.db.exists('Employee Checkin',{'employee':left,'time':day+' 07:00:00'})
    report['historical_attendance_and_late_punch']='passed'

    # Effective wages are used by the real monthly sheet; ordinary edits preserve a future change.
    rate_person=employee('rate')
    pay.setup_payroll(company)
    original=pay.assign_salary(frappe.get_doc('Employee',rate_person),'2026-09-01')
    person=frappe.get_doc('Employee',rate_person)
    hr.save_employee(company,dict(lotus_base_salary=20800000,pay_from_date='2026-11-01'),rate_person,str(person.modified))
    person.reload();hr.save_employee(company,dict(cell_number='0900000001'),rate_person,str(person.modified))
    assert frappe.db.count('Salary Structure Assignment',{'employee':rate_person,'docstatus':1})==2
    t.save_staff(company,'2026-09-10',[dict(employee=rate_person,status='Present',working_hours=8)],'rate-old-'+tag)
    doc=frappe.get_doc('Attendance',frappe.db.get_value('Attendance',{'employee':rate_person,'attendance_date':'2026-09-10'},'name'));doc.submit()
    row=next(r for r in hp.payroll_sheet(company,'2026-09')['employees'] if r['employee']==rate_person)
    assert row['regular_pay']==400000 and row['base']==10400000,row
    assert row['gross']==row['regular_pay']+row['paid_pay'],row
    pay.assign_salary(frappe.get_doc('Employee',rate_person),'2026-09-16')
    t.save_staff(company,'2026-09-21',[dict(employee=rate_person,status='Present',working_hours=8)],'rate-new-'+tag)
    doc=frappe.get_doc('Attendance',frappe.db.get_value('Attendance',{'employee':rate_person,'attendance_date':'2026-09-21'},'name'));doc.submit()
    row=next(r for r in hp.payroll_sheet(company,'2026-09')['employees'] if r['employee']==rate_person)
    assert row['regular_pay']==1200000 and len(row['rate_history'])==2,row
    assert row['paid_pay']==400000,row  # 2 September stays at the old rate.
    assert pay.create_payroll in frappe.whitelisted
    assert pay._finance_posts_payroll not in frappe.whitelisted
    report['effective_salary_and_api_registration']='passed'

    # Complete, real signing state: late drafts/raw punches must stop the last signature.
    org=frappe.get_doc(dict(doctype='Company',company_name='HR Audit '+tag,abbr='HA'+tag[:3],default_currency='VND',country='Vietnam',chart_of_accounts='Standard')).insert().name
    hp.setup_calendar(org,2026,['Sunday'])
    closer=employee('closing',org,'2026-09-30')
    saved=t.save_staff(org,'2026-09-30',[dict(employee=closer,status='Present',working_hours=8)],'close-'+tag)
    doc=frappe.get_doc('Attendance',saved['names'][0]);doc.submit()
    begin,end=hp._month('2026-09')
    assert not hp.blockers(org,begin,end)
    snapshot,digest=hp._frozen(org,'2026-09',begin,end)
    period=frappe.get_doc(dict(doctype=hp.PERIOD,company=org,month='2026-09',status='Open',snapshot=snapshot,snapshot_hash=digest))
    period.flags.lotus_period_action=True;period.insert()
    fingerprint=signing.fingerprint(period)
    for i,(key,state) in enumerate([('PREPARE','Đã ký'),('HR','Đã ký'),('APPROVE','Chờ ký')]):
        frappe.get_doc(dict(doctype='Lotus Sign Request',document_type=hp.PERIOD,document_name=period.name,chain='timekeeping_period',company=org,round=1,step_index=i,step_key=key,title=key,assignee='Administrator',state=state,content_hash=fingerprint)).insert(ignore_permissions=True)
    farm2=t.create_farm(org,'AUDIT-CLOSE-'+tag,'AUDIT Close '+tag)['name']
    team=t.create_team(org,dict(farm=farm2,code='AUDIT-'+tag,name='AUDIT crew '+tag,foreman='AUDIT foreman'))['name']
    crew=t.save_crew(org,dict(farm=farm2,work_team=team,posting_date='2026-09-30',headcount=1,present=1,workdays=1,completed_qty=0,unit_rate=0),'draft-crew-'+tag)
    assert hp._frozen(org,'2026-09',begin,end)[1]==digest
    assert rejected(hp.sign_period,org,'2026-09')
    frappe.delete_doc('Lotus Crew Attendance',crew['name'])
    dev2=ops.save_device(org,dict(farm=farm2,device_code='AUDIT-CLOSE-'+tag,device_name='AUDIT Close '+tag))['name']
    ops.ingest_device_events(org,dev2,[dict(device_user_id='UNKNOWN',punched_at='2026-09-30 08:00:00',log_type='IN')])
    assert hp._frozen(org,'2026-09',begin,end)[1]==digest
    assert rejected(hp.sign_period,org,'2026-09')
    assert frappe.db.get_value(hp.PERIOD,period.name,'status')=='Open'
    raw=frappe.get_all('Lotus Attendance Punch',filters={'device':dev2},pluck='name')
    ad.ignore_punches(org,raw,'AUDIT explicitly ignored test punch')
    hp.sign_period(org,'2026-09')
    assert frappe.db.get_value(hp.PERIOD,period.name,'status')=='Closed'
    report['final_signature_rechecks_real_draft_and_raw_punch']='passed'
finally:
    frappe.set_user('Administrator')
    frappe.db.rollback()
    frappe.clear_cache()
    frappe.destroy()
print(json.dumps(dict(checks=report,rollback=True),ensure_ascii=False))
