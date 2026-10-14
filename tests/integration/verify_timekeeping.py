"""Run in bench with HRMS installed; all temporary business data rolls back."""
import frappe,uuid,json
from frappe.utils import nowdate,add_days
frappe.init(site='frontend',sites_path='/home/frappe/frappe-bench/sites');frappe.connect();frappe.set_user('Administrator')
from lotus_farm import timekeeping as t
make=lambda dt,**v:frappe.get_doc(dict(doctype=dt,**v)).insert()
user=None
try:
    tag=uuid.uuid4().hex[:8];company='Lotus Agritech';today=nowdate();month=today[:7]
    employee=t.create_employee(company,dict(employee_name='Timekeeping QA '+tag,gender='Male',date_of_birth=add_days(today,-10000),date_of_joining=today,designation='QA '+tag))['name']
    shift=t.create_shift('QA '+tag,'08:00','16:00')['name']
    rows=[dict(employee=employee,status='Present',working_hours=8,note='QA')]
    saved=t.save_staff(company,today,rows,'staff-'+tag,shift=shift)
    retry=t.save_staff(company,today,rows,'staff-'+tag,shift=shift)
    assert saved==retry,'Attendance retry duplicated records'
    assert t.monthly(company,month)['rows'][0]['workdays']==0,'Draft attendance contributed to payroll totals'
    doc=frappe.get_doc('Attendance',saved['names'][0]);old_modified=str(doc.modified);doc.lotus_note='Changed';doc.save()
    try:t.staff_action(company,[dict(name=doc.name,modified=old_modified)],'submit')
    except frappe.ValidationError:pass
    else:raise AssertionError('Stale staff approval accepted')
    t.staff_action(company,[dict(name=doc.name,modified=str(doc.modified))],'submit')
    summary=next(r for r in t.monthly(company,month)['rows'] if r['employee']==employee)
    assert summary['workdays']==1 and summary['working_hours']==8,summary
    doc.reload()
    t.staff_action(company,[dict(name=doc.name,modified=str(doc.modified))],'cancel','QA correction')
    assert next(r for r in t.monthly(company,month)['rows'] if r['employee']==employee)['workdays']==0
    rows=[dict(employee=employee,status='Half Day',working_hours=4,note='QA half day')]
    half=t.save_staff(company,today,rows,'half-'+tag,shift=shift)
    half_doc=frappe.get_doc('Attendance',half['names'][0]);t.staff_action(company,[dict(name=half_doc.name,modified=str(half_doc.modified))],'submit')
    assert next(r for r in t.monthly(company,month)['rows'] if r['employee']==employee)['workdays']==.5
    try:t.save_staff(company,add_days(today,1),rows,'future-'+tag,shift=shift)
    except frappe.ValidationError:pass
    else:raise AssertionError('Future attendance accepted')
    farm=t.create_farm(company,'TIME-QA-'+tag,'QA farm '+tag)['name']
    team=t.create_team(company,dict(farm=farm,code='QA-'+tag,name='QA contractor '+tag,foreman='QA foreman',phone=''))['name']
    other=t.create_team(company,dict(farm=farm,code='OTHER-'+tag,name='Other contractor '+tag,foreman='Other foreman',phone=''))['name']
    values=dict(farm=farm,work_team=team,posting_date=today,headcount=10,present=8,workdays=7.5,completed_qty=100,uom='Kg',unit_rate=2000,notes='QA')
    record=t.save_crew(company,values,'crew-'+tag)
    assert record==t.save_crew(company,values,'crew-'+tag),'Crew retry duplicated records'
    assert next(r for r in t.crew_monthly(company,month,farm)['rows'] if r['team']==team)['workdays']==0
    crew=frappe.get_doc('Lotus Crew Attendance',record['name']);assert crew.absent==2 and crew.amount==200000
    t.crew_action(company,crew.name,str(crew.modified),'submit');crew.reload()
    summary=next(r for r in t.crew_monthly(company,month,farm)['rows'] if r['team']==team)
    assert summary['workdays']==7.5 and summary['amount']==200000,summary
    t.crew_action(company,crew.name,str(crew.modified),'cancel','QA correction')
    recreated=t.save_crew(company,values,'new-crew-'+tag);assert recreated['name']!=crew.name
    t.save_crew(company,{**values,'work_team':other},'other-crew-'+tag)
    # A crew leader gets only the assigned farm/team, and cannot approve attendance or read HR files.
    user=make('User',email='timekeeping-'+tag+'@example.invalid',first_name='QA foreman',send_welcome_email=0,enabled=1,user_type='System User',roles=[dict(role='Lotus Crew Leader')]).name
    for dt,value in [('Company',company),('Farm',farm),('Work Team',team)]:make('User Permission',user=user,allow=dt,for_value=value,apply_to_all_doctypes=1)
    frappe.set_user(user)
    visible=t.crew_day(company,today,farm)
    assert {r.work_team for r in visible['rows']}=={team},visible
    own=frappe.get_doc('Lotus Crew Attendance',recreated['name'])
    try:t.crew_action(company,own.name,str(own.modified),'submit')
    except frappe.PermissionError:pass
    else:raise AssertionError('Foreman could approve own contractor costs')
    try:t.staff_day(company,today,shift)
    except frappe.PermissionError:pass
    else:raise AssertionError('Foreman read official personnel attendance')
    try:t.save_crew(company,{**values,'work_team':other},'denied-'+tag)
    except frappe.PermissionError:pass
    else:raise AssertionError('Foreman wrote another team')
    frappe.set_user('Administrator')
    from lotus_farm.www.lotus_timekeeping_print import get_context,download_pdf
    for kind in ('staff','crew'):
        context=frappe._dict();get_context(context,company,month,kind,farm)
        rendered=frappe.render_template('lotus_farm/www/lotus_timekeeping_print.html',context)
        assert 'BẢNG CÔNG THÁNG' in rendered
        download_pdf(company,month,kind,farm);assert frappe.local.response.filecontent.startswith(b'%PDF')
        import os
        if os.environ.get('QA_ARTIFACT_DIR'):
            from pathlib import Path
            Path(os.environ['QA_ARTIFACT_DIR'],kind+'-timekeeping.pdf').write_bytes(frappe.local.response.filecontent)
        t.export_month(company,month,kind,farm);assert frappe.local.response.filecontent.startswith(b'\xef\xbb\xbf')
    print(json.dumps(dict(staff_days=.5,crew_days=7.5,crew_amount=200000,retry='pass',approval_versions='pass',permissions='pass',pdf_csv='pass',rollback=True)))
finally:
    frappe.set_user('Administrator');frappe.db.rollback()
    if user:frappe.clear_cache(user=user)
    frappe.destroy()
