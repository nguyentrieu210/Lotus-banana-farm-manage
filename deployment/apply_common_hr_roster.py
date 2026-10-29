"""Apply an explicitly confirmed common schedule atomically; default is rollback/dry run."""
import argparse
import json
import os
import frappe

parser=argparse.ArgumentParser()
parser.add_argument('--site',required=True)
parser.add_argument('--start',required=True)
parser.add_argument('--expected-employees',type=int,required=True)
parser.add_argument('--apply',action='store_true')
args=parser.parse_args()
os.chdir('/home/frappe/frappe-bench/sites')
frappe.init(site=args.site,sites_path='.')
frappe.connect()
frappe.set_user('Administrator')
from frappe.utils import getdate
from lotus_farm import shift_admin,timekeeping
from lotus_farm.controls import lock

try:
    start=getdate(args.start)
    shifts=['Ca sáng','Ca chiều']
    for name,begin,end in [('Ca sáng',7,11),('Ca chiều',13,17)]:
        doc=frappe.get_doc('Shift Type',name)
        from lotus_farm.checkin_rules import _clock
        assert (_clock(doc.start_time).hour,_clock(doc.end_time).hour)==(begin,end),'Shift times changed; review the schedule'
    people=frappe.get_all('Employee',filters={'status':'Active'},fields=['name','company'],limit_page_length=0)
    assert len(people)==args.expected_employees,'Active employee count changed; review before applying'
    companies=sorted({p.company for p in people})
    for company in companies:lock('Company',company)
    before=frappe.db.count('Attendance')
    settings=frappe.get_single('HR Settings')
    settings.allow_multiple_shift_assignments=1
    settings.save()
    changed=0
    for company in companies:
        mine=[p.name for p in people if p.company==company]
        existing=timekeeping._scheduled_shifts(company,start,mine)
        changes=[dict(employee=name,**{'from':str(start)},shifts=shifts) for name in mine if set(existing.get(name,[]))!=set(shifts)]
        if changes:
            result=shift_admin.set_roster(company,changes)
            if result['errors']:raise RuntimeError('Could not apply all employee schedules; transaction rolled back')
            changed+=len(result['applied'])
        coverage=timekeeping._scheduled_shifts(company,start,mine)
        assert all(set(coverage.get(name,[]))==set(shifts) for name in mine),'Incomplete shift coverage'
        board=timekeeping.staff_day(company,str(start))
        assert board['missing_shift_count']==0
        assert len(board['rows'])==2*len(mine),'Unexpected daily rows; check existing attendance first'
    assert frappe.db.count('Attendance')==before,'Scheduling must not create attendance'
    frappe.clear_messages()
    result=dict(site=args.site,start=str(start),employees=len(people),shifts=shifts,employees_updated=changed,
        daily_rows=2*len(people),attendance_unchanged=True,applied=args.apply)
    if args.apply:frappe.db.commit()
    else:frappe.db.rollback()
    print(json.dumps(result,ensure_ascii=False))
finally:
    frappe.db.rollback()
    frappe.destroy()
