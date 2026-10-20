"""ADMS push (ZKTeco / Ronald Jack / Wise Eye "iclock" protocol): the time clock sends its punches to
https://<site>/iclock/cdata by itself; no CSV export, no bridge PC.

Only a device registered in Lotus (Lotus Attendance Device, connection mode ADMS, active) with the
serial number it reports (SN=) is accepted. Punches are stored as the immutable Lotus Attendance Punch,
mapped to the employee when exactly one device-ID mapping covers the time, and promoted to HRMS
Employee Checkin right after (and every 10 minutes). User names sent by the clock (USERINFO) are kept
to help map device IDs to employees. Biometric templates are never accepted.

Protocol: GET cdata?SN=&options=all -> options; POST cdata?SN=&table=ATTLOG|OPERLOG -> "OK: n";
GET getrequest -> "OK" (no commands are pushed to the clock); POST devicecmd -> "OK".
"""
import re
from datetime import datetime, timedelta

import frappe
from frappe.utils import now_datetime

MAX_BODY = 1_000_000
MAX_LINES = 5000
# ATTLOG status: 0 check-in, 1 check-out, 2 break-out, 3 break-in, 4 overtime-in, 5 overtime-out.
STATUS_LOG_TYPE = {'0': 'IN', '3': 'IN', '4': 'IN', '1': 'OUT', '2': 'OUT', '5': 'OUT'}


# Pure protocol helpers (unit-tested in tests/test_adms.py) -------------------------------------------

def parse_attlog(body, limit=MAX_LINES):
    """'PIN\\tYYYY-MM-DD HH:MM:SS\\tstatus\\tverify...' lines -> ([event], invalid_count)."""
    events, invalid = [], 0
    for line in str(body or '').splitlines()[:limit]:
        if not line.strip():
            continue
        parts = line.split('\t')
        if len(parts) < 2 or not parts[0].strip() or not re.fullmatch(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}(:\d{2})?', parts[1].strip()):
            invalid += 1
            continue
        status = parts[2].strip() if len(parts) > 2 else ''
        stamp = parts[1].strip()
        events.append(dict(device_user_id=parts[0].strip()[:80], punched_at=stamp if stamp.count(':') == 2 else stamp + ':00',
                           log_type=STATUS_LOG_TYPE.get(status, ''), source_event_id=''))
    return events, invalid


def parse_userinfo(body, limit=MAX_LINES):
    """OPERLOG / USERINFO 'USER PIN=12\\tName=An\\tPri=0\\tCard=...' lines -> [dict(pin, name, privilege, card)]."""
    users = []
    for line in str(body or '').splitlines()[:limit]:
        line = line.strip()
        if line.startswith('USER '):
            line = line[5:]
        elif not line.startswith('PIN='):
            continue
        fields = dict(part.split('=', 1) for part in line.split('\t') if '=' in part)
        pin = (fields.get('PIN') or '').strip()
        if pin:
            users.append(dict(pin=pin[:80], name=(fields.get('Name') or '').strip()[:140], privilege=(fields.get('Pri') or '0').strip()[:10],
                              card=(fields.get('Card') or '').strip()[:40]))
    return users


def handshake(sn, att_stamp='None', op_stamp='None'):
    """Options the clock asks for on start-up: realtime upload of punches and user info, Vietnam time."""
    return '\n'.join([
        'GET OPTION FROM: ' + sn, 'ATTLOGStamp=' + str(att_stamp or 'None'), 'OPERLOGStamp=' + str(op_stamp or 'None'),
        'ATTPHOTOStamp=None', 'ErrorDelay=30', 'Delay=10', 'TransTimes=00:00;12:00', 'TransInterval=1',
        'TransFlag=TransData AttLog\tOpLog\tEnrollUser', 'TimeZone=7', 'Realtime=1', 'Encrypt=None', ''])


# Frappe side ----------------------------------------------------------------------------------------

def _device(sn):
    sn = str(sn or '').strip()
    if not sn or len(sn) > 80:
        return None
    name = frappe.db.get_value('Lotus Attendance Device', {'serial_number': sn, 'connection_mode': 'ADMS', 'active': 1}, 'name')
    return frappe.get_doc('Lotus Attendance Device', name) if name else None


def _as_service(fn, *args):
    """The clock is authenticated by its registered serial number; the stored punches pass the same
    validation as any other (device farm, employee company), run for that one narrow write."""
    previous = frappe.session.user
    frappe.set_user('Administrator')
    try:
        return fn(*args)
    finally:
        frappe.set_user(previous)


def _store_users(machine, users):
    for user in users:
        name = frappe.db.get_value('Lotus Attendance Device User', {'device': machine.name, 'device_user_id': user['pin']})
        values = dict(name_on_device=user['name'], privilege=user['privilege'], card=user['card'], last_seen_at=now_datetime())
        if name:
            frappe.db.set_value('Lotus Attendance Device User', name, values, update_modified=False)
        else:
            frappe.get_doc(dict(doctype='Lotus Attendance Device User', company=machine.company, device=machine.name,
                                device_user_id=user['pin'], **values)).insert(ignore_permissions=True)
    return len(users)


def handle(path, args, method, body):
    """-> (status, text). Never raises to the clock: it retries on anything but "OK"."""
    endpoint = path.strip('/').split('/', 1)[-1] if '/' in path.strip('/') else ''
    machine = _device(args.get('SN'))
    if not machine:
        return 403, 'UNKNOWN DEVICE'
    frappe.db.set_value('Lotus Attendance Device', machine.name, 'last_seen_at', now_datetime(), update_modified=False)
    if endpoint == 'cdata' and method == 'GET':
        return 200, handshake(machine.serial_number)
    if endpoint == 'cdata' and method == 'POST':
        if len(body or '') > MAX_BODY:
            return 413, 'TOO LARGE'
        table = str(args.get('table') or '').upper()
        if table == 'ATTLOG':
            events, invalid = parse_attlog(body)
            from lotus_farm.hr_operations import _ingest
            result = _as_service(_ingest, machine, events, 'ADMS') if events else dict(created=0)
            if result.get('created'):
                days = sorted({e['punched_at'][:10] for e in events})
                frappe.enqueue('lotus_farm.adms.promote', queue='short', enqueue_after_commit=True, job_id='lotus-adms-' + machine.company,
                               deduplicate=True, company=machine.company, days=days)
            return 200, 'OK: ' + str(len(events) + invalid)
        if table in ('OPERLOG', 'USERINFO'):
            users = parse_userinfo(body)
            _as_service(_store_users, machine, users)
            return 200, 'OK: ' + str(len(str(body or '').splitlines()))
        return 200, 'OK: ' + str(len(str(body or '').splitlines()))
    return 200, 'OK'


def promote(company, days):
    """Background: punches of the given days (and the morning after, for night shifts) -> HRMS."""
    from lotus_farm.hr_operations import _sync_range
    first, last = min(days), max(days)
    end = (datetime.strptime(last, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
    _sync_range(company, first, end, limit=3000)


try:
    from frappe.website.page_renderers.base_renderer import BaseRenderer
except ImportError:  # pragma: no cover - unit tests run without Frappe's website package
    BaseRenderer = object


class ADMSRenderer(BaseRenderer):
    """page_renderer hook: answers /iclock/* in plain text before any website page is looked up."""

    def can_render(self):
        return self.path == 'iclock' or self.path.startswith('iclock/')

    def render(self):
        from werkzeug.wrappers import Response
        request = frappe.local.request
        try:
            status, text = handle(self.path, request.args, request.method, request.get_data(as_text=True))
            frappe.db.commit()
        except Exception:
            frappe.db.rollback()
            frappe.log_error(title='Lotus ADMS: lỗi nhận dữ liệu máy chấm công')
            status, text = 500, 'ERROR'
        return Response(text, status=status, mimetype='text/plain')
