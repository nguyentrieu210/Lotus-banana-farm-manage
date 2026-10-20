"""ADMS push on a real site, as the time clock calls it (Guest session): handshake, unknown serial refused,
ATTLOG stored and mapped, promoted to HRMS, USERINFO kept for mapping, duplicates skipped. Rolls back."""
import json
import uuid

import frappe

frappe.init(site='frontend', sites_path='/home/frappe/frappe-bench/sites')
frappe.connect()
frappe.set_user('Administrator')
frappe.in_test = True
frappe.flags.in_test = True

from lotus_farm import adms, device_admin as da, hr_operations as ops, timekeeping as t  # noqa: E402

company, day = 'Lotus Agritech', '2026-10-16'
tag = uuid.uuid4().hex[:6]
sn = 'QA' + tag.upper()
report = {}
try:
    person = t.create_employee(company, dict(employee_name='ADMS QA ' + tag, gender='Female', date_of_birth='1992-02-02',
                                             date_of_joining='2026-08-01', designation='QA ' + tag))['name']
    farm = t.create_farm(company, 'ADMS-QA-' + tag, 'ADMS QA ' + tag)['name']
    try:
        ops.save_device(company, dict(farm=farm, device_code='ADMS-NOSN-' + tag, device_name='No SN', connection_mode='ADMS'))
        raise AssertionError('an ADMS clock needs its serial number')
    except frappe.ValidationError as exc:
        assert 'serial' in str(exc), exc
    device = ops.save_device(company, dict(farm=farm, device_code='ADMS-' + tag, device_name='Cổng QA', connection_mode='ADMS', serial_number=sn))['name']
    frappe.get_doc(dict(doctype='Lotus Attendance Identity', company=company, farm=farm, device=device, device_user_id='501',
                        employee=person, valid_from='2026-08-01', active=1)).insert()

    frappe.set_user('Guest')
    status, text = adms.handle('iclock/cdata', {'SN': sn, 'options': 'all', 'pushver': '2.4.1'}, 'GET', '')
    assert status == 200 and text.startswith('GET OPTION FROM: ' + sn) and 'Realtime=1' in text, (status, text)
    assert adms.handle('iclock/cdata', {'SN': 'NOT-REGISTERED'}, 'GET', '') == (403, 'UNKNOWN DEVICE')
    body = '501\t%s 06:02:10\t0\t1\t0\t0\n501\t%s 14:07:00\t1\t1\t0\t0\n999\t%s 06:30:00\t0\t15\nbroken line\n' % (day, day, day)
    status, text = adms.handle('iclock/cdata', {'SN': sn, 'table': 'ATTLOG', 'Stamp': '1'}, 'POST', body)
    assert (status, text) == (200, 'OK: 4'), (status, text)
    assert frappe.session.user == 'Guest', 'the service user is dropped after the write'
    again = adms.handle('iclock/cdata', {'SN': sn, 'table': 'ATTLOG'}, 'POST', body)
    users = adms.handle('iclock/cdata', {'SN': sn, 'table': 'OPERLOG'}, 'POST', 'USER PIN=501\tName=Thi Sre\tPri=0\tCard=\nUSER PIN=999\tName=Khach\tPri=0\n')
    assert adms.handle('iclock/getrequest', {'SN': sn}, 'GET', '') == (200, 'OK')
    frappe.set_user('Administrator')

    rows = frappe.get_all('Lotus Attendance Punch', filters={'device': device}, fields=['device_user_id', 'state', 'employee', 'log_type', 'source'], order_by='punched_at')
    assert [(r.device_user_id, r.state, r.log_type) for r in rows] == [('501', 'Ready', 'IN'), ('999', 'Unmapped', 'IN'), ('501', 'Ready', 'OUT')], rows
    assert all(r.source == 'ADMS' for r in rows) and again == (200, 'OK: 4') and len(rows) == 3, 'duplicates are skipped'
    adms.promote(company, [day])
    checkins = frappe.get_all('Employee Checkin', filters={'employee': person, 'time': ['between', [day + ' 00:00:00', day + ' 23:59:59']]}, pluck='log_type')
    assert sorted(checkins) == ['IN', 'OUT'], checkins
    known = frappe.get_all('Lotus Attendance Device User', filters={'device': device}, fields=['device_user_id', 'name_on_device'], order_by='device_user_id')
    assert [(k.device_user_id, k.name_on_device) for k in known] == [('501', 'Thi Sre'), ('999', 'Khach')], known
    seen = frappe.db.get_value('Lotus Attendance Device', device, ['last_seen_at', 'last_event_at'], as_dict=True)
    assert seen.last_seen_at and seen.last_event_at, seen
    view = da.overview(company)
    machine = next(m for m in view['machines'] if m['name'] == device)
    assert machine['online'] and machine['mapped'] == 1, machine
    waiting = next(u for u in view['unmapped'] if u['device'] == device and u['device_user_id'] == '999')
    assert waiting['name_on_device'] == 'Khach' and waiting['punches'] == 1, waiting
    guest = t.create_employee(company, dict(employee_name='Khách QA ' + tag, gender='Male', date_of_birth='1990-01-01',
                                            date_of_joining='2026-10-01', designation='QA ' + tag))['name']
    mapped = da.map_device_user(company, device, '999', guest, '2026-10-01')
    assert mapped['remapped'] == 1 and mapped['synced']['synced'] == 1, mapped
    assert frappe.db.count('Employee Checkin', {'employee': guest}) == 1
    assert not [u for u in da.overview(company)['unmapped'] if u['device'] == device], 'nothing left to map'
    report.update(device=device, punches=len(rows), checkins=len(checkins), users=len(known), rollback=True)
finally:
    frappe.set_user('Administrator')
    frappe.db.rollback()
print(json.dumps(report, ensure_ascii=False, default=str))
