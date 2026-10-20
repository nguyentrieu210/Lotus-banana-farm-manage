"""Time clocks in Lotus: which clock is online, how to point a clock at Lotus (ADMS), and mapping the IDs a
clock uses to employees — including catching up the punches that arrived before the mapping existed."""
import unicodedata
from datetime import timedelta

import frappe
from frappe.utils import get_datetime, get_url, getdate, now_datetime, nowdate

ONLINE_MINUTES = 10


def _plain(text):
    text = unicodedata.normalize('NFD', str(text or '')).replace('đ', 'd').replace('Đ', 'D')
    return ' '.join(''.join(c for c in text if unicodedata.category(c) != 'Mn').lower().split())


def suggest(name_on_device, employees):
    """Employee whose name matches the clock's name (accents and case ignored); last-name match as fallback."""
    wanted = _plain(name_on_device)
    if not wanted:
        return None
    exact = [e for e in employees if _plain(e['employee_name']) == wanted]
    if len(exact) == 1:
        return exact[0]['name']
    tail = [e for e in employees if _plain(e['employee_name']).endswith(' ' + wanted) or _plain(e['employee_name']).split(' ')[-1] == wanted]
    return tail[0]['name'] if len(tail) == 1 else None


def _company(company):
    from lotus_farm.hr_operations import _company as check
    return check(company)


@frappe.whitelist()
def overview(company):
    _company(company)
    now = now_datetime()
    machines = frappe.get_list('Lotus Attendance Device', filters={'company': company},
                               fields=['name', 'modified', 'device_code', 'device_name', 'farm', 'model', 'serial_number', 'connection_mode',
                                       'timezone', 'active', 'notes', 'last_event_at', 'last_seen_at'], order_by='device_code', limit_page_length=500)
    today = str(getdate(nowdate()))
    for m in machines:
        seen = get_datetime(m.last_seen_at) if m.last_seen_at else None
        m['online'] = bool(m.active and m.connection_mode == 'ADMS' and seen and now - seen <= timedelta(minutes=ONLINE_MINUTES))
        m['punches_today'] = frappe.db.count('Lotus Attendance Punch', {'device': m.name, 'punched_at': ['between', [today + ' 00:00:00', today + ' 23:59:59']]})
        m['mapped'] = frappe.db.count('Lotus Attendance Identity', {'device': m.name, 'active': 1})
        m['last_seen_at'] = str(m.last_seen_at or '')
        m['last_event_at'] = str(m.last_event_at or '')
    employees = frappe.get_list('Employee', filters={'company': company, 'status': 'Active'}, fields=['name', 'employee_name', 'designation'],
                                order_by='employee_name', limit_page_length=0)
    mapped = {(i.device, i.device_user_id) for i in frappe.get_all('Lotus Attendance Identity', filters={'company': company, 'active': 1},
                                                                    fields=['device', 'device_user_id'], limit_page_length=0)}
    seen_ids = {}
    for u in frappe.get_all('Lotus Attendance Device User', filters={'company': company}, fields=['device', 'device_user_id', 'name_on_device'], limit_page_length=0):
        seen_ids[(u.device, u.device_user_id)] = dict(device=u.device, device_user_id=u.device_user_id, name_on_device=u.name_on_device or '', punches=0, last_punch='')
    for p in frappe.db.sql("""select device, device_user_id, count(*) n, max(punched_at) last from `tabLotus Attendance Punch`
                              where company=%s and state='Unmapped' group by device, device_user_id""", company, as_dict=True):
        row = seen_ids.setdefault((p.device, p.device_user_id), dict(device=p.device, device_user_id=p.device_user_id, name_on_device='', punches=0, last_punch=''))
        row.update(punches=p.n, last_punch=str(p.last))
    unmapped = []
    for key, row in sorted(seen_ids.items(), key=lambda kv: (-kv[1]['punches'], kv[0])):
        if key in mapped:
            continue
        row['suggested'] = suggest(row['name_on_device'], employees)
        unmapped.append(row)
    url = get_url()
    host = url.split('://', 1)[-1].rstrip('/')
    return dict(machines=machines, unmapped=unmapped[:500], employees=employees,
                adms=dict(server=host, port=443 if url.startswith('https') else 80, https=url.startswith('https'), path='/iclock/cdata'),
                can_manage=__import__('lotus_farm.shift_admin', fromlist=['can_manage']).can_manage())


@frappe.whitelist(methods=['POST'])
def map_device_user(company, device, device_user_id, employee, valid_from=None):
    """Map a clock ID to an employee from `valid_from` and re-read that ID's waiting punches."""
    from lotus_farm.shift_admin import _manager
    from lotus_farm.hr_operations import _mapping, _sync_range
    _manager()
    _company(company)
    machine = frappe.get_doc('Lotus Attendance Device', device)
    if machine.company != company:
        frappe.throw('Máy không thuộc công ty.')
    start = getdate(valid_from) if valid_from else (getdate(frappe.db.get_value('Employee', employee, 'date_of_joining')) or getdate(nowdate()))
    identity = frappe.get_doc(dict(doctype='Lotus Attendance Identity', company=company, farm=machine.farm, device=device,
                                   device_user_id=str(device_user_id).strip(), employee=employee, valid_from=start, active=1))
    identity.flags.ignore_permissions = True  # role checked by _manager
    identity.insert()
    waiting = frappe.get_all('Lotus Attendance Punch', filters={'device': device, 'device_user_id': identity.device_user_id, 'state': 'Unmapped',
                                                                 'punched_at': ['>=', str(start) + ' 00:00:00']},
                             fields=['name', 'punched_at'], order_by='punched_at', limit_page_length=5000)
    days = set()
    for row in waiting:
        found = _mapping(company, device, identity.device_user_id, str(row.punched_at))
        if not found:
            continue
        punch = frappe.get_doc('Lotus Attendance Punch', row.name)
        punch.employee, punch.state = found, 'Ready'
        punch.flags.lotus_promotion = True
        punch.flags.ignore_permissions = True
        punch.save()
        days.add(getdate(row.punched_at))
    synced = _sync_range(company, min(days), max(days) + timedelta(days=1), limit=5000) if days else None
    return dict(identity=identity.name, remapped=len(waiting), synced=synced)


@frappe.whitelist(methods=['POST'])
def end_mapping(company, name, valid_to):
    """A clock ID handed to someone else: the old mapping stops the day before."""
    from lotus_farm.shift_admin import _manager
    _manager()
    _company(company)
    doc = frappe.get_doc('Lotus Attendance Identity', name)
    if doc.company != company:
        frappe.throw('Mã máy không thuộc công ty.')
    doc.valid_to = getdate(valid_to)
    doc.flags.ignore_permissions = True
    doc.save()
    return dict(name=doc.name, valid_to=str(doc.valid_to))
