"""The daily attendance board: device punches shown next to each person's day, one-step approval of the
rows the device fully explains, and dismissing stray punches so a month can close.

Device data is synced into HRMS Employee Checkin every 10 minutes (sync_recent) and on opening a day,
so the morning view needs no trip to the device screen. Nothing is approved without the manager's click.
"""
from datetime import timedelta

import frappe
from frappe.utils import add_days, cint, flt, get_datetime, getdate, now_datetime, nowdate

from lotus_farm import timekeeping as t
from lotus_farm.timekeeping_rules import overtime_suggestion

COMPARED = ('status', 'working_hours', 'in_time', 'out_time')


def _minutes(a, b):
    return int(round((get_datetime(a) - get_datetime(b)).total_seconds() / 60))


def _machine_row(day, proposal, shift):
    """Proposal from check-ins plus minutes late / early / after the shift for display and overtime."""
    from lotus_farm.checkin_rules import shift_window
    row = dict(proposal)
    begin, finish = shift_window(day, shift or {})
    row.update(late_minutes=0, early_minutes=0, after_minutes=0, next_day=False)
    if begin and proposal.get('in_time'):
        row['late_minutes'] = max(0, _minutes(proposal['in_time'], begin))
    if finish and proposal.get('out_time'):
        out = get_datetime(proposal['out_time'])
        row['early_minutes'] = max(0, _minutes(finish, out))
        row['after_minutes'] = max(0, _minutes(out, finish))
        row['next_day'] = out.date() > getdate(day)
    row['suggested_overtime'] = overtime_suggestion(row['after_minutes']) if begin else 0
    row['clean'] = bool(proposal.get('status') in ('Present', 'Half Day') and proposal.get('in_time') and proposal.get('out_time')
                        and not proposal.get('needs_review'))
    return row


def _same(saved, machine):
    """A saved draft still equals what the device says (so it was not edited by hand)."""
    for field in COMPARED:
        a, b = saved.get(field), machine.get(field)
        if field in ('in_time', 'out_time'):
            a, b = (str(get_datetime(a))[:16] if a else ''), (str(get_datetime(b))[:16] if b else '')
        elif field == 'working_hours':
            a, b = round(flt(a), 2), round(flt(b), 2)
        if a != b:
            return False
    return True


def _can_sync():
    return bool(frappe.db.exists('DocType', 'Employee Checkin') and frappe.has_permission('Employee Checkin', 'create')
                and frappe.has_permission('Lotus Attendance Punch', 'write'))


def sync_day(company, day):
    """Promote the day's (and the night shift's next morning) device punches; returns the counts."""
    from lotus_farm.hr_operations import _sync_range
    if not _can_sync() or not frappe.db.exists('Lotus Attendance Device', {'company': company, 'active': 1}):
        return None
    return _sync_range(company, day, add_days(day, 1), limit=3000)


@frappe.whitelist()
def board(company, date, shift=None, search=None, sync=1):
    """staff_day rows, each with the device reading next to it (`machine`) and whether it may be approved
    in one step (`matches`: the device fully explains the day and nobody changed it by hand)."""
    t._company(company)
    day = t._date(date)
    synced = sync_day(company, day) if cint(sync) else None
    result = t.staff_day(company, str(day), shift, search)
    machine = {}
    if frappe.has_permission('Employee Checkin', 'read'):
        proposals = t.propose_from_checkins(company, str(day), shift)
        settings = {}
        for row in proposals['rows']:
            name = row.get('shift')
            if name and name not in settings:
                settings[name] = frappe.db.get_value('Shift Type', name, ['start_time', 'end_time'], as_dict=True) or {}
            machine[row['employee']] = _machine_row(day, row, settings.get(name))
    counts = dict(matching=0, review=0, manual=0)
    for row in result['rows']:
        found = machine.get(row['employee'])
        row['machine'] = found
        row['manual'] = bool(found and row.get('name') and row.get('docstatus') == 0 and found.get('clean') and not _same(row, found))
        row['matches'] = bool(found and found['clean'] and row.get('status') != 'On Leave' and row.get('docstatus') == 0
                              and (not row.get('name') or _same(row, found)) and not result['period_closed'])
        counts['matching'] += row['matches']
        counts['review'] += bool(found and found.get('needs_review') and row.get('docstatus') == 0)
        counts['manual'] += row['manual']
    result.update(counts=counts, synced=synced, can_sync=_can_sync())
    return result


@frappe.whitelist(methods=['POST'])
def approve_matching(company, date, client_event_id, shift=None):
    """Save and approve, in one step, every row the device fully explains (see board.matches)."""
    if not (frappe.has_permission('Attendance', 'create') and frappe.has_permission('Attendance', 'submit')):
        frappe.throw('Chưa có quyền lưu và duyệt chấm công.', frappe.PermissionError)
    data = board(company, date, shift, None, sync=0)
    rows = [r for r in data['rows'] if r['matches']]
    if not rows:
        return dict(approved=0)
    payload = []
    for r in rows:
        m = r['machine']
        payload.append(dict(employee=r['employee'], name=r.get('name'), modified=r.get('modified'), status=m['status'],
                            working_hours=m['working_hours'], overtime_hours=m['suggested_overtime'], in_time=m['in_time'],
                            out_time=m['out_time'], late_entry=m['late_entry'], early_exit=m['early_exit'],
                            shift=m.get('shift') or r.get('shift') or None, note=r.get('note') or ''))
    saved = t.save_staff(company, date, payload, client_event_id, shift)
    docs = [frappe.get_doc('Attendance', n) for n in saved['names']]
    t.staff_action(company, [dict(name=d.name, modified=str(d.modified)) for d in docs if d.docstatus == 0], 'submit')
    return dict(approved=len(docs), names=[d.name for d in docs])


# Stray punches ---------------------------------------------------------------------------------------

@frappe.whitelist()
def open_punches(company, from_date, to_date):
    """Punches not in HRMS for a range, with the employee name if one is mapped, for the device screen."""
    t._company(company)
    if not frappe.has_permission('Lotus Attendance Punch', 'read'):
        frappe.throw('Chưa có quyền xem log máy chấm công.', frappe.PermissionError)
    begin, end = getdate(from_date), getdate(to_date)
    if end < begin or (end - begin).days > 62:
        frappe.throw('Chọn khoảng tối đa 62 ngày.')
    rows = frappe.get_list('Lotus Attendance Punch', filters={'company': company, 'state': ['in', ['Unmapped', 'Needs Review', 'Ready']],
                                                              'punched_at': ['between', [str(begin) + ' 00:00:00', str(end) + ' 23:59:59']]},
                           fields=['name', 'device', 'device_user_id', 'punched_at', 'log_type', 'state', 'employee', 'notes', 'modified'],
                           order_by='punched_at desc', limit_page_length=1000)
    names = {e.name: e.employee_name for e in frappe.get_all('Employee', filters={'name': ['in', [r.employee for r in rows if r.employee] or ['']]},
                                                               fields=['name', 'employee_name'])}
    for row in rows:
        row['employee_name'] = names.get(row.employee, '')
        row['punched_at'] = str(row.punched_at)
    return dict(rows=rows)


@frappe.whitelist(methods=['POST'])
def ignore_punches(company, names, reason):
    """Mark punches that will never become attendance (unknown ID, test swipe, left employee) as Ignored."""
    from lotus_farm.shift_admin import _manager
    _manager()
    t._company(company)
    reason = str(reason or '').strip()
    if len(reason) < 5:
        frappe.throw('Ghi lý do bỏ qua (ít nhất 5 ký tự).')
    names = frappe.parse_json(names) if isinstance(names, str) else names
    if not isinstance(names, list) or not 1 <= len(names) <= 500:
        frappe.throw('Chọn từ 1 đến 500 log.')
    stamp = str(now_datetime())[:16] + ' · ' + frappe.session.user + ' bỏ qua: ' + reason[:300]
    done = 0
    for name in names:
        row = frappe.get_doc('Lotus Attendance Punch', name)
        if row.company != company or row.state == 'Synced':
            continue
        row.state = 'Ignored'
        row.notes = ((row.notes or '') + '\n' + stamp).strip()[:2000]
        row.flags.lotus_promotion = True
        row.flags.ignore_permissions = True  # role checked by _manager
        row.save()
        done += 1
    return dict(ignored=done)


def sync_recent():
    """Every 10 minutes: today's and yesterday's punches of companies with an active device -> HRMS."""
    from lotus_farm.hr_operations import _sync_range
    today = getdate(nowdate())
    for company in sorted(set(frappe.get_all('Lotus Attendance Device', filters={'active': 1}, pluck='company'))):
        try:
            _sync_range(company, today - timedelta(days=1), today, limit=3000)
            frappe.db.commit()
        except Exception:
            frappe.db.rollback()
            frappe.log_error(title='Lotus: đồng bộ chấm công trong ngày ' + str(company))
