"""Shift administration: define shifts, change the roster day by day, correct approved attendance.

Allowed for Administrator, System Manager and HR Manager (timekeeping_rules.can_manage_shifts).
A closed timekeeping month is never changed here, not even by Administrator: reopen the period first.
Approved attendance stores the shift times it was worked under (lotus_shift_start / lotus_shift_end),
so editing a shift later never changes pay already earned.
"""
import re

import frappe
from frappe.utils import add_days, cint, flt, get_datetime, getdate, nowdate

from lotus_farm import timekeeping_rules as rules

ROSTER_LIMIT = 500


def install_fields():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    from frappe.permissions import add_permission, update_permission_property
    fields = {}
    if frappe.db.exists('DocType', 'Attendance'):
        fields['Attendance'] = [
            dict(fieldname='lotus_shift_start', label='Lotus · Giờ bắt đầu ca khi chấm', fieldtype='Time', read_only=1, insert_after='shift'),
            dict(fieldname='lotus_shift_end', label='Lotus · Giờ kết thúc ca khi chấm', fieldtype='Time', read_only=1, insert_after='lotus_shift_start'),
            dict(fieldname='lotus_correction_reason', label='Lotus · Lý do sửa công', fieldtype='Small Text', read_only=1, insert_after='lotus_shift_end'),
        ]
    if frappe.db.exists('DocType', 'Shift Type'):
        fields['Shift Type'] = [dict(fieldname='lotus_color', label='Lotus · Màu ca trên lịch', fieldtype='Data', insert_after='end_time')]
    create_custom_fields(fields, update=True, ignore_validate=True)
    if frappe.db.exists('Role', 'HR Manager'):
        for doctype, actions in (('Shift Type', ('read', 'write', 'create')),
                                 ('Shift Assignment', ('read', 'write', 'create', 'submit', 'cancel')),
                                 ('Attendance', ('read', 'write', 'create', 'submit', 'cancel', 'amend'))):
            if frappe.db.exists('DocType', doctype):
                add_permission(doctype, 'HR Manager')
                for action in actions:
                    update_permission_property(doctype, 'HR Manager', 0, action, 1)


def can_manage():
    return frappe.session.user != 'Guest' and rules.can_manage_shifts(frappe.get_roles(), frappe.session.user)


def _manager():
    if frappe.session.user == 'Guest':
        frappe.throw('Vui lòng đăng nhập.', frappe.AuthenticationError)
    if not can_manage():
        frappe.throw('Chỉ Quản trị viên, Quản trị hệ thống hoặc Quản lý nhân sự được sửa ca và sửa công đã duyệt.', frappe.PermissionError)


def _company(name):
    from lotus_farm.timekeeping import _company as check
    return check(name)


def _closed_months(company, begin, end=None):
    """Closed timekeeping months touching [begin, end]; an open end reaches every later month."""
    from lotus_farm.hr_period import PERIOD
    filters = {'company': company, 'status': 'Closed', 'month': ['>=', getdate(begin).strftime('%Y-%m')]}
    if end:
        filters['month'] = ['between', [getdate(begin).strftime('%Y-%m'), getdate(end).strftime('%Y-%m')]]
    return frappe.get_all(PERIOD, filters=filters, pluck='month', order_by='month')


def _guard(company, begin, end=None):
    closed = _closed_months(company, begin, end)
    if closed:
        frappe.throw('Tháng ' + ', '.join(closed) + ' đã khóa công. Mở lại kỳ trước khi đổi ca hoặc sửa công.')


def assignment_guard(doc, method=None):
    """doc_events on Shift Assignment: the roster of a closed month stays as it was paid."""
    if doc.flags.get('lotus_period_reopen') or not doc.get('start_date'):
        return
    before = doc.get_doc_before_save() if method == 'validate' else None
    if method == 'validate' and before and str(before.end_date or '') != str(doc.end_date or ''):
        old, new = before.end_date, doc.end_date
        # Only the days whose coverage changes matter: between the old and the new end.
        begin = add_days(min(getdate(old), getdate(new)), 1) if old and new else add_days(old or new, 1)
        _guard(doc.company, begin, max(getdate(old), getdate(new)) if old and new else None)
    elif method in ('before_submit', 'before_cancel'):
        _guard(doc.company, doc.start_date, doc.end_date)


# Shift types ---------------------------------------------------------------------------------------

def _clock(value, label):
    text = str(value or '').strip()
    if not re.fullmatch(r'([01]?\d|2[0-3]):[0-5]\d(:[0-5]\d)?', text):
        frappe.throw(label + ' cần dạng giờ:phút, ví dụ 06:00.')
    return text if text.count(':') == 2 else text + ':00'


def _minutes(values, key, label, limit):
    value = cint(values.get(key) or 0)
    if not 0 <= value <= limit:
        frappe.throw(label + ' từ 0 đến ' + str(limit) + ' phút.')
    return value


def _shift_values(values):
    values = frappe.parse_json(values) if isinstance(values, str) else (values or {})
    result = dict(start_time=_clock(values.get('start_time'), 'Giờ bắt đầu'), end_time=_clock(values.get('end_time'), 'Giờ kết thúc'),
                  late_entry_grace_period=_minutes(values, 'late_grace', 'Cho phép đi muộn', 240),
                  early_exit_grace_period=_minutes(values, 'early_grace', 'Cho phép về sớm', 240),
                  begin_check_in_before_shift_start_time=_minutes(values, 'check_in_before', 'Nhận lượt chấm trước ca', 720),
                  allow_check_out_after_shift_end_time=_minutes(values, 'check_out_after', 'Nhận lượt chấm sau ca', 720),
                  working_hours_threshold_for_half_day=flt(values.get('half_day_hours')),
                  working_hours_threshold_for_absent=flt(values.get('absent_hours')))
    if result['start_time'] == result['end_time']:
        frappe.throw('Giờ bắt đầu và kết thúc ca phải khác nhau.')
    if not 0 <= result['working_hours_threshold_for_absent'] <= result['working_hours_threshold_for_half_day'] <= 24:
        frappe.throw('Ngưỡng vắng phải nhỏ hơn hoặc bằng ngưỡng nửa ngày (tối đa 24 giờ).')
    color = str(values.get('color') or '').strip()
    if color and not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
        frappe.throw('Màu ca cần dạng #RRGGBB.')
    result['lotus_color'] = color
    return result


def _row(doc):
    return dict(name=doc.name, modified=str(doc.modified), start_time=str(doc.start_time), end_time=str(doc.end_time),
                late_grace=cint(doc.late_entry_grace_period), early_grace=cint(doc.early_exit_grace_period),
                check_in_before=cint(doc.begin_check_in_before_shift_start_time), check_out_after=cint(doc.allow_check_out_after_shift_end_time),
                half_day_hours=flt(doc.working_hours_threshold_for_half_day), absent_hours=flt(doc.working_hours_threshold_for_absent),
                color=doc.get('lotus_color') or '', holiday_list=doc.holiday_list or '',
                assigned=frappe.db.count('Shift Assignment', {'shift_type': doc.name, 'docstatus': 1, 'status': 'Active'}))


@frappe.whitelist()
def shifts():
    if frappe.session.user == 'Guest':
        frappe.throw('Vui lòng đăng nhập.', frappe.AuthenticationError)
    names = frappe.get_list('Shift Type', pluck='name', order_by='start_time asc', limit_page_length=0)
    return dict(rows=[_row(frappe.get_doc('Shift Type', n)) for n in names], can_manage=can_manage())


@frappe.whitelist(methods=['POST'])
def create_shift(company, name, values):
    _manager()
    _company(company)
    from lotus_farm.warehouse import _text
    data = _shift_values(values)
    # Lotus builds attendance drafts from check-ins itself; HRMS auto attendance would submit them unreviewed.
    doc = frappe.get_doc(dict(doctype='Shift Type', enable_auto_attendance=0,
                              holiday_list=frappe.get_cached_value('Company', company, 'default_holiday_list'), **data))
    doc.flags.ignore_permissions = True  # role checked by _manager
    doc.insert(set_name=_text(name, 'Tên ca'))
    return _row(doc)


@frappe.whitelist(methods=['POST'])
def update_shift(name, modified, values):
    """Change a shift's times and rules. Approved days keep the times they were worked under."""
    _manager()
    from lotus_farm.controls import lock
    lock('Shift Type', name)
    doc = frappe.get_doc('Shift Type', name)
    if str(doc.modified) != str(modified):
        frappe.throw('Ca vừa được người khác sửa. Tải lại trước khi lưu.')
    doc.update(_shift_values(values))
    doc.flags.ignore_permissions = True
    doc.save()
    row = _row(doc)
    # Drafts in open months are recomputed from the device when the manager fetches again.
    row['open_drafts'] = frappe.db.count('Attendance', {'shift': name, 'docstatus': 0})
    return row


# Roster ---------------------------------------------------------------------------------------------

def _assignments(company, employee):
    return frappe.get_all('Shift Assignment', filters={'company': company, 'employee': employee, 'docstatus': 1, 'status': 'Active'},
                          fields=['name', 'shift_type', 'start_date', 'end_date'], order_by='start_date asc', limit_page_length=0)


def _apply(company, employee, plan):
    for name, end in plan['end']:
        doc = frappe.get_doc('Shift Assignment', name)
        doc.end_date = end
        doc.flags.ignore_permissions = True
        doc.save()
    for name in plan['cancel']:
        doc = frappe.get_doc('Shift Assignment', name)
        doc.flags.ignore_permissions = True
        doc.cancel()
    for shift, begin, end in plan['create']:
        doc = frappe.get_doc(dict(doctype='Shift Assignment', company=company, employee=employee, shift_type=shift,
                                  start_date=begin, end_date=end, status='Active'))
        doc.flags.ignore_permissions = True
        doc.insert()
        doc.submit()


@frappe.whitelist(methods=['POST'])
def set_roster(company, changes):
    """changes: [{employee, from, to?, shift?}] — shift empty means no shift (day off). Each employee is
    applied on its own: one failing change never undoes the others. Returns applied, errors, warnings."""
    _manager()
    _company(company)
    changes = frappe.parse_json(changes) if isinstance(changes, str) else changes
    if not isinstance(changes, list) or not 1 <= len(changes) <= ROSTER_LIMIT:
        frappe.throw('Mỗi lần đổi từ 1 đến ' + str(ROSTER_LIMIT) + ' ô lịch ca.')
    from lotus_farm.controls import lock
    from lotus_farm.timekeeping import _employee
    lock('Company', company)
    shift_names = set(frappe.get_all('Shift Type', pluck='name'))
    applied, errors, warnings = [], [], []
    for index, change in enumerate(changes):
        label = str(change.get('employee') or '')
        savepoint = 'lotus_roster_' + str(index)
        frappe.db.savepoint(savepoint)
        try:
            employee = _employee(change.get('employee'), company)
            label = employee.employee_name
            begin = getdate(change.get('from'))
            end = getdate(change['to']) if change.get('to') else None
            shift = change.get('shift') or None
            if shift and shift not in shift_names:
                frappe.throw('Ca không tồn tại: ' + str(shift))
            _guard(company, begin, end)
            plan = rules.plan_roster(_assignments(company, employee.name), begin, end, shift)
            _apply(company, employee.name, plan)
            worked = frappe.get_all('Attendance', filters={'employee': employee.name, 'docstatus': ['<', 2],
                                                           'attendance_date': ['between', [begin, end or add_days(nowdate(), 1)]]},
                                    fields=['attendance_date', 'shift'], limit_page_length=0)
            different = [r for r in worked if (r.shift or None) != shift]
            if different:
                warnings.append(dict(employee=employee.name, employee_name=label, days=len(different),
                                     message=label + ': ' + str(len(different)) + ' ngày đã có công theo ca cũ — kiểm tra lại công các ngày đó.'))
            applied.append(dict(employee=employee.name, employee_name=label, shift=shift or '', start=str(begin), end=str(end or '')))
        except Exception as exc:  # report per employee, keep the rest
            frappe.db.rollback(save_point=savepoint)
            frappe.clear_messages()
            errors.append(dict(employee=change.get('employee'), employee_name=label, message=str(exc) or exc.__class__.__name__))
    return dict(applied=applied, errors=errors, warnings=warnings)


@frappe.whitelist()
def roster(company, start, days=7, search=None, department=None):
    """Grid for [start, start+days): employees x days -> shift name or ''. Readable by attendance readers."""
    _company(company)
    if not frappe.has_permission('Shift Assignment', 'read') and not can_manage():
        frappe.throw('Chưa có quyền xem lịch ca.', frappe.PermissionError)
    begin = getdate(start)
    days = max(1, min(cint(days) or 7, 42))
    end = add_days(begin, days - 1)
    filters = {'company': company, 'status': 'Active'}
    if department:
        filters['department'] = department
    people = frappe.get_list('Employee', filters=filters, fields=['name', 'employee_name', 'department', 'designation'],
                             order_by='employee_name', limit_page_length=0)
    if search:
        needle = str(search).casefold()
        people = [p for p in people if needle in (p.name + ' ' + p.employee_name).casefold()]
    names = [p.name for p in people] or ['']
    assignments = frappe.get_all('Shift Assignment', filters={'company': company, 'employee': ['in', names], 'docstatus': 1, 'status': 'Active',
                                                              'start_date': ['<=', end]},
                                 fields=['name', 'employee', 'shift_type', 'start_date', 'end_date'], order_by='start_date desc', limit_page_length=0)
    worked = frappe.get_all('Attendance', filters={'employee': ['in', names], 'attendance_date': ['between', [begin, end]], 'docstatus': 1},
                            fields=['employee', 'attendance_date'], limit_page_length=0)
    done = {(r.employee, str(r.attendance_date)) for r in worked}
    dates = [add_days(begin, i) for i in range(days)]
    rows = []
    for person in people:
        cells = []
        mine = [a for a in assignments if a.employee == person.name]
        for day in dates:
            hit = next((a for a in mine if getdate(a.start_date) <= getdate(day) and (not a.end_date or getdate(a.end_date) >= getdate(day))), None)
            cells.append(dict(date=str(day), shift=hit.shift_type if hit else '', worked=(person.name, str(day)) in done))
        rows.append(dict(employee=person.name, employee_name=person.employee_name, department=person.department or '',
                         designation=person.designation or '', cells=cells))
    from lotus_farm.hr_period import holiday_map
    holidays = holiday_map(company, begin, end)
    closed = set(_closed_months(company, begin, end))
    return dict(start=str(begin), days=[dict(date=str(d), off=bool(holidays and getdate(d) in holidays.days),
                                             closed=getdate(d).strftime('%Y-%m') in closed) for d in dates],
                rows=rows, can_manage=can_manage())


# Correcting approved attendance --------------------------------------------------------------------

def shift_times(shift):
    """(start, end) of a Shift Type as stored on Attendance when the day is recorded."""
    if not shift:
        return None, None
    values = frappe.db.get_value('Shift Type', shift, ['start_time', 'end_time'], as_dict=True)
    return (values.start_time, values.end_time) if values else (None, None)


@frappe.whitelist(methods=['POST'])
def correct_attendance(company, name, modified, values, reason):
    """Replace an approved day by an amended one (HRMS cancel + amend), with the reason kept on both."""
    _manager()
    _company(company)
    reason = str(reason or '').strip()
    if len(reason) < 5:
        frappe.throw('Ghi lý do sửa công (ít nhất 5 ký tự).')
    from lotus_farm.controls import lock
    lock('Attendance', name)
    doc = frappe.get_doc('Attendance', name)
    if doc.company != company or doc.docstatus != 1:
        frappe.throw('Chỉ sửa được phiếu công đã duyệt của công ty này.')
    if str(doc.modified) != str(modified):
        frappe.throw('Phiếu công đã thay đổi. Tải lại trước khi sửa.')
    day = getdate(doc.attendance_date)
    _guard(company, day, day)
    values = frappe.parse_json(values) if isinstance(values, str) else (values or {})
    status = values.get('status') or doc.status
    if status not in ('Present', 'Absent', 'Half Day', 'Work From Home'):
        frappe.throw('Chọn trạng thái công hợp lệ.')
    hours, overtime = flt(values.get('working_hours', doc.working_hours)), flt(values.get('overtime_hours', doc.get('lotus_overtime_hours')))
    if not 0 <= hours <= 24 or not 0 <= overtime <= 16 or (status == 'Absent' and (hours or overtime)):
        frappe.throw('Giờ làm hoặc giờ tăng ca không hợp lệ cho trạng thái đã chọn.')
    clock = {}
    for field in ('in_time', 'out_time'):
        value = values.get(field, doc.get(field))
        if value:
            moment = get_datetime(value)
            if not day <= moment.date() <= getdate(add_days(day, 1)):
                frappe.throw('Giờ vào/ra phải thuộc ngày công (ca đêm được sang ngày hôm sau).')
            clock[field] = moment
        else:
            clock[field] = None
    if clock['in_time'] and clock['out_time'] and clock['out_time'] <= clock['in_time']:
        frappe.throw('Giờ ra phải sau giờ vào.')
    shift = values.get('shift', doc.shift) or None
    if shift and not frappe.db.exists('Shift Type', shift):
        frappe.throw('Ca không tồn tại.')
    doc.lotus_cancel_reason = ('Sửa công: ' + reason)[:2000]
    doc.flags.ignore_permissions = True  # role checked by _manager
    doc.save()
    doc.cancel()
    amended = frappe.copy_doc(doc)
    start, end = shift_times(shift)
    amended.update(dict(docstatus=0, amended_from=doc.name, status=status, working_hours=hours, lotus_overtime_hours=overtime, shift=shift,
                        in_time=clock['in_time'], out_time=clock['out_time'], late_entry=cint(values.get('late_entry', doc.late_entry)),
                        early_exit=cint(values.get('early_exit', doc.early_exit)), lotus_note=str(values.get('note', doc.get('lotus_note')) or '')[:2000],
                        lotus_correction_reason=reason[:2000], lotus_cancel_reason=None, lotus_client_key=None, lotus_payload_hash=None,
                        lotus_shift_start=start, lotus_shift_end=end))
    amended.flags.ignore_permissions = True
    amended.insert()
    amended.submit()
    return dict(name=amended.name, amended_from=doc.name, modified=str(amended.modified))
