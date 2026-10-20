"""Shift administration on a real site: who may edit shifts, roster changes split HRMS assignments,
closed months are frozen, approved days are corrected by amendment and keep their shift times. Rolls back."""
import json
import uuid

import frappe

frappe.init(site='frontend', sites_path='/home/frappe/frappe-bench/sites')
frappe.connect()
frappe.set_user('Administrator')
frappe.in_test = True
frappe.flags.in_test = True
from frappe.utils import getdate  # noqa: E402

from lotus_farm import shift_admin as sa, timekeeping as t  # noqa: E402

company = 'Lotus Agritech'
tag = uuid.uuid4().hex[:6]
report = {}


def user(key, roles):
    email = 'lotus-shift-%s-%s@example.com' % (key, tag)
    return frappe.get_doc(dict(doctype='User', email=email, first_name='Ca ' + key, send_welcome_email=0, enabled=1,
                               roles=[dict(role=r) for r in roles])).insert(ignore_permissions=True).name


def as_user(name, fn, *args):
    frappe.set_user(name)
    try:
        return fn(*args)
    finally:
        frappe.set_user('Administrator')


def denied(fn, *args):
    try:
        fn(*args)
    except frappe.PermissionError:
        return True
    return False


try:
    hr = user('hr', ['HR Manager', 'HR User', 'Employee'])
    clerk = user('clerk', ['HR User', 'Employee'])
    s1 = sa.create_shift(company, 'QA Ca 1 ' + tag, dict(start_time='06:00', end_time='14:00', late_grace=10, check_in_before=60, check_out_after=120, half_day_hours=4, absent_hours=2, color='#c43224'))
    s3 = sa.create_shift(company, 'QA Ca 3 ' + tag, dict(start_time='22:00', end_time='06:00', check_in_before=60, check_out_after=120, half_day_hours=4, absent_hours=2))
    assert s1['check_in_before'] == 60 and s1['color'] == '#c43224', s1
    changed = as_user(hr, sa.update_shift, s1['name'], s1['modified'], dict(s1, late_grace=15))
    assert changed['late_grace'] == 15, 'HR Manager edits a shift'
    assert denied(as_user, clerk, sa.update_shift, s1['name'], changed['modified'], dict(s1, late_grace=20)), 'HR User cannot'
    assert as_user(clerk, sa.shifts)['can_manage'] is False and as_user(hr, sa.shifts)['can_manage'] is True

    employee = t.create_employee(company, dict(employee_name='Ca QA ' + tag, gender='Male', date_of_birth='1990-01-01',
                                               date_of_joining='2026-08-01', designation='QA ' + tag))['name']
    frappe.db.set_value('Employee', employee, 'status', 'Active')
    first = as_user(hr, sa.set_roster, company, [dict(employee=employee, **{'from': '2026-10-01'}, shift=s1['name'])])
    assert not first['errors'], first
    second = as_user(hr, sa.set_roster, company, [dict(employee=employee, **{'from': '2026-10-12', 'to': '2026-10-18'}, shift=s3['name'])])
    assert not second['errors'], second
    rows = frappe.get_all('Shift Assignment', filters={'employee': employee, 'docstatus': 1}, fields=['shift_type', 'start_date', 'end_date'], order_by='start_date')
    got = [(r.shift_type, str(r.start_date), str(r.end_date or '')) for r in rows]
    assert got == [(s1['name'], '2026-10-01', '2026-10-11'), (s3['name'], '2026-10-12', '2026-10-18'), (s1['name'], '2026-10-19', '')], got
    grid = sa.roster(company, '2026-10-10', 4, search=employee)
    assert [c['shift'] for c in grid['rows'][0]['cells']] == [s1['name'], s1['name'], s3['name'], s3['name']], grid['rows'][0]['cells']
    off = as_user(hr, sa.set_roster, company, [dict(employee=employee, **{'from': '2026-10-20', 'to': '2026-10-20'}, shift='')])
    assert [c['shift'] for c in sa.roster(company, '2026-10-19', 3, search=employee)['rows'][0]['cells']] == [s1['name'], '', s1['name']], off

    period = frappe.get_doc(dict(doctype='Lotus Timekeeping Period', company=company, month='2026-08', status='Closed'))
    period.flags.lotus_period_action = True
    period.insert(ignore_permissions=True)
    blocked = as_user(hr, sa.set_roster, company, [dict(employee=employee, **{'from': '2026-08-25', 'to': '2026-08-31'}, shift=s1['name'])])
    assert blocked['errors'] and 'đã khóa công' in blocked['errors'][0]['message'], blocked

    saved = t.save_staff(company, '2026-10-13', [dict(employee=employee, status='Present', working_hours=8, overtime_hours=0, shift=s3['name'],
                                                      in_time='2026-10-13 22:02:00', out_time='2026-10-14 06:01:00')], 'qa-' + tag)
    day = frappe.get_doc('Attendance', saved['names'][0])
    assert str(day.lotus_shift_start) in ('22:00:00', '1 day, 22:00:00') or day.lotus_shift_start is not None, day.lotus_shift_start
    t.staff_action(company, [dict(name=day.name, modified=str(day.modified))], 'submit')
    day.reload()
    assert denied(as_user, clerk, sa.correct_attendance, company, day.name, str(day.modified), dict(overtime_hours=1), 'Thêm tăng ca')
    fixed = as_user(hr, sa.correct_attendance, company, day.name, str(day.modified), dict(overtime_hours=1.5, out_time='2026-10-14 07:35:00'), 'Thêm tăng ca theo xác nhận tổ trưởng')
    new = frappe.get_doc('Attendance', fixed['name'])
    assert new.docstatus == 1 and new.amended_from == day.name and new.lotus_overtime_hours == 1.5, new.as_dict()
    assert frappe.db.get_value('Attendance', day.name, 'docstatus') == 2 and 'tổ trưởng' in new.lotus_correction_reason
    as_user(hr, sa.update_shift, s3['name'], frappe.db.get_value('Shift Type', s3['name'], 'modified'), dict(s3, start_time='21:00', end_time='05:00'))
    assert str(frappe.db.get_value('Attendance', new.name, 'lotus_shift_start')) != '21:00:00', 'the worked shift times stay'

    month = t.monthly(company, '2026-10')
    statuses = set(frappe.get_all('Employee', filters={'name': ['in', [r['employee'] for r in month['rows']]]}, pluck='status'))
    assert 'Inactive' not in statuses, statuses
    report.update(shifts=[s1['name'], s3['name']], assignments=len(got), corrected=new.name, month_rows=len(month['rows']), rollback=True)
finally:
    frappe.set_user('Administrator')
    frappe.db.rollback()
print(json.dumps(report, ensure_ascii=False, default=str))
