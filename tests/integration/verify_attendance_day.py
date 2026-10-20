"""Daily attendance board on a real site: punches -> board shows the device reading with minutes late /
overtime -> one-step approval of matching rows only -> stray punches ignored so the month can close. Rolls back."""
import json
import uuid

import frappe

frappe.init(site='frontend', sites_path='/home/frappe/frappe-bench/sites')
frappe.connect()
frappe.set_user('Administrator')
frappe.in_test = True
frappe.flags.in_test = True

from lotus_farm import attendance_day as ad, hr_operations as ops, hr_period as hp, shift_admin as sa, timekeeping as t  # noqa: E402

company, day = 'Lotus Agritech', '2026-10-15'
tag = uuid.uuid4().hex[:6]
report = {}
try:
    shift = sa.create_shift(company, 'QA Ngày ' + tag, dict(start_time='06:00', end_time='14:00', late_grace=5, early_grace=5,
                                                            check_in_before=60, check_out_after=180, half_day_hours=4, absent_hours=2))['name']
    people = []
    for i in range(3):
        name = t.create_employee(company, dict(employee_name='Máy QA %d %s' % (i, tag), gender='Male', date_of_birth='1990-01-01',
                                               date_of_joining='2026-08-01', designation='QA ' + tag))['name']
        people.append(name)
    sa.set_roster(company, [dict(employee=p, **{'from': '2026-10-01'}, shift=shift) for p in people])
    farm = t.create_farm(company, 'DAY-QA-' + tag, 'Day QA ' + tag)['name']
    device = ops.save_device(company, dict(farm=farm, device_code='QA-' + tag, device_name='QA ' + tag))['name']
    for i, person in enumerate(people):
        frappe.get_doc(dict(doctype='Lotus Attendance Identity', company=company, farm=farm, device=device, device_user_id='9%d%s' % (i, tag[:3]),
                            employee=person, valid_from='2026-08-01', active=1)).insert()
    punches = [('90', '06:12', 'IN'), ('90', '14:50', 'OUT'),   # 12′ late, 50′ after -> 0.75 h overtime
               ('91', '05:55', 'IN'), ('91', '14:02', 'OUT'),   # clean
               ('92', '06:00', 'IN'),                           # missing out -> review
               ('77', '07:00', 'IN')]                           # unknown id -> stray
    ops.ingest_device_events(company, device, [dict(device_user_id=(p + tag[:3]) if p != '77' else '77x', punched_at=day + ' ' + hhmm + ':00', log_type=kind)
                                                for p, hhmm, kind in punches])

    data = ad.board(company, day)
    assert data['synced'] and data['synced']['synced'] == 5, data['synced']
    rows = {r['employee']: r for r in data['rows'] if r['employee'] in people}
    late = rows[people[0]]['machine']
    assert (late['late_minutes'], late['after_minutes'], late['suggested_overtime']) == (12, 50, 0.75), late
    assert rows[people[0]]['matches'] and rows[people[1]]['matches'] and not rows[people[2]]['matches'], [r['matches'] for r in rows.values()]
    assert rows[people[2]]['machine']['needs_review'], rows[people[2]]['machine']

    # A draft edited by hand is no longer "matching" and is left for the manager.
    edited = t.save_staff(company, day, [dict(employee=people[1], status='Present', working_hours=7, overtime_hours=0, shift=shift,
                                              in_time=day + ' 05:55:00', out_time=day + ' 14:02:00')], 'manual-' + tag)
    data = ad.board(company, day, sync=0)
    rows = {r['employee']: r for r in data['rows'] if r['employee'] in people}
    assert rows[people[1]]['manual'] and not rows[people[1]]['matches'], rows[people[1]]
    result = ad.approve_matching(company, day, 'approve-' + tag)
    assert result['approved'] >= 1 and people[0] in [frappe.db.get_value('Attendance', n, 'employee') for n in result['names']], result
    approved = frappe.get_doc('Attendance', next(n for n in result['names'] if frappe.db.get_value('Attendance', n, 'employee') == people[0]))
    assert approved.docstatus == 1 and approved.lotus_overtime_hours == 0.75 and approved.late_entry == 1, approved.as_dict()
    assert frappe.db.get_value('Attendance', edited['names'][0], 'docstatus') == 0, 'the hand-edited draft waits'

    stray = frappe.get_all('Lotus Attendance Punch', filters={'device': device, 'state': ['!=', 'Synced']}, pluck='name')
    assert len(stray) == 1, stray
    month = '2026-10'
    begin, end = hp._month(month)
    before = {b['code']: b['count'] for b in hp.blockers(company, begin, end)}
    ad.ignore_punches(company, stray, 'Mã 77x không phải nhân viên (thẻ thử máy)')
    after = {b['code']: b['count'] for b in hp.blockers(company, begin, end)}
    assert after.get('open_punches', 0) == before['open_punches'] - 1, (before, after)
    assert 'bỏ qua' in frappe.db.get_value('Lotus Attendance Punch', stray[0], 'notes')
    report.update(synced=data['synced'], approved=result['approved'], blockers_before=before.get('open_punches'), blockers_after=after.get('open_punches', 0), rollback=True)
finally:
    frappe.set_user('Administrator')
    frappe.db.rollback()
print(json.dumps(report, ensure_ascii=False, default=str))
