"""Daily presence regression on a disposable restored site; every business fixture rolls back."""
import json
import os
import uuid
import frappe

os.chdir('/home/frappe/frappe-bench/sites')
frappe.init(site=os.environ.get('LOTUS_HR_TEST_SITE','hr.test'),sites_path='.')
frappe.connect()
assert frappe.conf.lotus_hr_audit_disposable,'Never run on live'
frappe.set_user('Administrator');frappe.flags.in_test=True;frappe.in_test=True
from lotus_farm import timekeeping as t,attendance_day as ad,hr_period as hp,shift_admin as sa

tag=uuid.uuid4().hex[:8];company=frappe.db.get_value('Company',{},'name');day='2026-10-28'
report={}


def employee(label):
    name=t.create_employee(company,dict(employee_name='PRESENCE '+label+' '+tag,gender='Male',date_of_birth='1990-01-01',date_of_joining='2026-10-01'))['name']
    frappe.db.set_value('Employee',name,dict(status='Active',lotus_onboarding_state='Ready',lotus_payment_basis='Daywork',lotus_daily_rate=260000))
    return name


def punch(person,clock,kind='IN'):
    return frappe.get_doc(dict(doctype='Employee Checkin',employee=person,time=day+' '+clock,log_type=kind)).insert()


def board():return ad.board(company,day,search=tag,sync=0,daily_presence=1)


def rejected(fn,*args,**kwargs):
    try:fn(*args,**kwargs)
    except frappe.ValidationError:return True
    return False


try:
    a,b,c,d=[employee(label) for label in ('both','morning','afternoon','none')]
    punch(a,'06:46:00');punch(a,'17:01:00')  # Two IN labels are two session presences.
    punch(b,'06:59:59');punch(b,'08:00:00','OUT');punch(b,'11:00:00')
    punch(c,'17:01:00','OUT')
    punch(d,'07:00:00');punch(d,'12:50:00');punch(d,'17:00:00')
    rows={r['employee']:r for r in board()['rows']}
    assert len(rows)==4 and len({r['row_key'] for r in rows.values()})==4
    assert rows[a]['working_hours']==8 and rows[a]['workdays']==1
    assert rows[b]['working_hours']==rows[c]['working_hours']==4
    assert rows[d]['workdays']==0 and not rows[d]['matches']
    assert all(r['machine']['suggested_overtime']==0 for r in rows.values())
    invalid=dict(employee=d,morning_present=1,afternoon_present=0,morning_time=day+' 07:00:00')
    assert rejected(t.save_staff,company,day,[invalid],'invalid-'+tag,daily_presence=1)
    from lotus_farm import daily_attendance as daily
    policy=daily.POLICY
    try:
        daily.POLICY='previous-noon-policy'
        old=next(r for r in board()['rows'] if r['employee']==a)
    finally:daily.POLICY=policy
    assert rejected(ad.approve_matching,company,day,'old-policy-'+tag,
        reviewed_rows=[dict(row_key=old['row_key'],review_hash=old['review_hash'])],daily_presence=1)
    report['strict_0700_1700_policy_and_old_review_rejection']='passed'
    assert rows[a]['morning_time']==day+' 06:46:00' and rows[a]['afternoon_time']==day+' 17:01:00'
    tokens=[dict(row_key=rows[p]['row_key'],review_hash=rows[p]['review_hash']) for p in (a,b)]
    approved=ad.approve_matching(company,day,'presence-'+tag,reviewed_rows=tokens,daily_presence=1)
    assert approved['approved']==2
    for person,hours,status in [(a,8,'Present'),(b,4,'Half Day')]:
        names=frappe.get_all('Attendance',filters={'employee':person,'attendance_date':day,'docstatus':1},pluck='name')
        assert len(names)==1
        doc=frappe.get_doc('Attendance',names[0])
        assert doc.working_hours==hours and doc.status==status and not doc.shift
        assert doc.lotus_presence_mode and not doc.in_time and not doc.out_time
    summary=next(r for r in t.monthly(company,'2026-10')['rows'] if r['employee']==a)
    assert summary['workdays']==1 and summary['working_hours']==8,summary
    wage=next(r for r in hp.payroll_sheet(company,'2026-10')['employees'] if r['employee']==a)
    assert wage['regular_pay']==260000,wage
    report['one_daily_record_and_payroll_credit']='passed'

    token=dict(row_key=rows[c]['row_key'],review_hash=rows[c]['review_hash'])
    punch(c,'06:30:00')
    assert rejected(ad.approve_matching,company,day,'stale-'+tag,reviewed_rows=[token],daily_presence=1)
    current=next(r for r in board()['rows'] if r['employee']==c)
    entry={k:current[k] for k in ('employee','name','modified','morning_present','afternoon_present','morning_time','afternoon_time')}
    entry['overtime_hours']=1
    first=t.save_staff(company,day,[entry],'manual-'+tag,daily_presence=1)
    assert t.save_staff(company,day,[entry],'manual-'+tag,daily_presence=1)==first
    current=next(r for r in board()['rows'] if r['employee']==c)
    assert current['manual'] and not current['matches'] and current['overtime_hours']==1
    report['stale_review_idempotency_and_manual_ot']='passed'

    doc=frappe.get_doc('Attendance',frappe.db.get_value('Attendance',{'employee':a,'docstatus':1},'name'))
    changed=sa.correct_attendance(company,doc.name,str(doc.modified),dict(daily_presence=1,morning_present=1,afternoon_present=0,
        morning_time=day+' 06:46:00',overtime_hours=0),'PRESENCE test half-day correction')
    amended=frappe.get_doc('Attendance',changed['name'])
    assert amended.status=='Half Day' and amended.working_hours==4 and amended.lotus_morning_present and not amended.lotus_afternoon_present
    assert frappe.db.count('Attendance',{'employee':a,'attendance_date':day,'docstatus':1})==1
    report['approved_daily_correction']='passed'

    from frappe.permissions import add_permission,update_permission_property
    role='PRESENCE READ '+tag
    frappe.get_doc(dict(doctype='Role',role_name=role)).insert()
    for dt in ['Attendance','Employee','Company','Employee Checkin']:
        add_permission(dt,role);update_permission_property(dt,role,0,'read',1)
    reader=frappe.get_doc(dict(doctype='User',email='presence-'+tag+'@example.invalid',first_name='Presence reader',send_welcome_email=0,roles=[dict(role=role)])).insert(ignore_permissions=True)
    frappe.set_user(reader.name)
    read=board()
    assert len(read['rows'])==4 and not read['machine_readable']
    assert not frappe.has_permission('Attendance','create')
    report['readonly_and_punch_field_privacy']='passed'
finally:
    frappe.set_user('Administrator');frappe.db.rollback();frappe.clear_cache();frappe.destroy()
print(json.dumps(dict(checks=report,rollback=True)))
