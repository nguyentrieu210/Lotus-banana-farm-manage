"""System-manager-only user profiles, role assignments, explicit farm/team grants and the linked employee.

Linking a login to its HR employee (Employee.user_id) is what lets that person be chosen as a named
signer and be notified (lotus_farm.signing)."""
import hashlib
import json
import frappe
from frappe.sessions import get_csrf_token
from frappe.utils import cint, validate_email_address

ROLE_LABELS = {
    'System Manager': 'Quản trị hệ thống', 'HR Manager': 'Quản lý nhân sự', 'HR User': 'Nhân viên nhân sự',
    'Stock Manager': 'Quản lý kho', 'Stock User': 'Nhân viên kho',
    'Purchase Manager': 'Quản lý mua hàng', 'Purchase User': 'Nhân viên mua hàng',
    'Lotus Farm Manager': 'Quản lý vườn', 'Lotus Sales Planner': 'Lập kế hoạch bán hàng',
    'Lotus QC Manager': 'Quản lý chất lượng', 'Lotus Packing Supervisor': 'Giám sát đóng gói',
    'Lotus Integration User': 'Tích hợp dữ liệu', 'Lotus Auditor': 'Kiểm tra và đối soát',
    'Lotus Stock Reviewer': 'Kiểm duyệt kho', 'Lotus Price Approver': 'Duyệt đơn giá',
    'Lotus Team Leader': 'Tổ trưởng', 'Lotus Field Supervisor': 'Giám sát hiện trường',
}
PROFILE_FIELDS = ('first_name', 'last_name', 'username', 'phone', 'mobile_no', 'enabled')
SCOPE_TYPES = ('Farm', 'Work Team')


def require_admin(permission='read'):
    user = frappe.session.user
    if user == 'Guest' or (user != 'Administrator' and 'System Manager' not in frappe.get_roles(user)):
        frappe.throw('Chỉ quản trị hệ thống được quản lý tài khoản và phân quyền.', frappe.PermissionError)
    if not frappe.has_permission('User', permission):
        frappe.throw('Không có quyền quản lý hồ sơ người dùng.', frappe.PermissionError)


def role_choices():
    active = set(frappe.get_all('Role', filters={'disabled': 0}, pluck='name'))
    return [{'name': name, 'label': label} for name, label in ROLE_LABELS.items() if name in active]


def grants(user):
    return frappe.get_all('User Permission', filters={'user': user, 'allow': ['in', SCOPE_TYPES]},
                          fields=['name', 'allow', 'for_value', 'apply_to_all_doctypes', 'applicable_for', 'is_default', 'hide_descendants', 'modified'], order_by='name')


def managed(row):
    return bool(cint(row.get('apply_to_all_doctypes'))) and not row.get('applicable_for') and not cint(row.get('is_default')) and not cint(row.get('hide_descendants'))


def scope_version(rows):
    return hashlib.sha256(json.dumps(rows, default=str, sort_keys=True).encode()).hexdigest()


def detail_data(user):
    doc = frappe.get_doc('User', user)
    doc.check_permission('read')
    rows = grants(user)
    return dict(name=doc.name, email=doc.email, modified=str(doc.modified), full_name=doc.full_name,
                **{key: doc.get(key) for key in PROFILE_FIELDS},
                roles=[row.role for row in doc.roles], role_profile=doc.role_profile_name or bool(doc.get('role_profiles')),
                farms=[r.for_value for r in rows if r.allow == 'Farm' and managed(r)],
                teams=[r.for_value for r in rows if r.allow == 'Work Team' and managed(r)],
                advanced_grants=[dict(doctype=r.allow, value=r.for_value) for r in rows if not managed(r)],
                scope_version=scope_version(rows), protected=user in ('Administrator', 'Guest'),
                employee=frappe.db.get_value('Employee', {'user_id': user}, 'name') or '')


@frappe.whitelist()
def bootstrap():
    require_admin()
    return dict(user=frappe.session.user, csrf_token=get_csrf_token(), roles=role_choices(),
                farms=frappe.get_all('Farm', fields=['name', 'farm_name'], order_by='name', limit_page_length=1000),
                teams=frappe.get_all('Work Team', fields=['name', 'team_name', 'farm'], order_by='name', limit_page_length=2000),
                employees=frappe.get_all('Employee', filters={'status': ['!=', 'Left']}, fields=['name', 'employee_name', 'designation', 'user_id'],
                                         order_by='employee_name', limit_page_length=5000),
                can_create=bool(frappe.has_permission('User', 'create')), can_write=bool(frappe.has_permission('User', 'write')))


@frappe.whitelist()
def users(search='', start=0, status=''):
    require_admin()
    filters = {'name': ['not in', ['Guest']]}
    if status in ('0', '1'): filters['enabled'] = cint(status)
    needle = str(search or '').strip()[:120]
    or_filters = {k: ['like', '%' + needle + '%'] for k in ('name', 'full_name', 'username')} if needle else None
    start = max(0, cint(start))
    rows = frappe.get_list('User', filters=filters, or_filters=or_filters,
                           fields=['name', 'full_name', 'username', 'enabled', 'user_type'],
                           order_by='full_name asc, name asc', start=start, page_length=51)
    return {'rows': rows[:50], 'has_more': len(rows) > 50}


@frappe.whitelist()
def detail(user):
    require_admin()
    return detail_data(user)


@frappe.whitelist(methods=['POST'])
def save(values, user=None):
    require_admin('write' if user else 'create')
    values = frappe.parse_json(values)
    if not isinstance(values, dict): frappe.throw('Hồ sơ không hợp lệ.')
    if user in ('Administrator', 'Guest'): frappe.throw('Tài khoản hệ thống được bảo vệ.', frappe.PermissionError)
    selected = set(values.get('roles') or [])
    allowed = {r['name'] for r in role_choices()}
    if not selected <= allowed: frappe.throw('Vai trò không hợp lệ hoặc đã ngừng sử dụng.')
    farms, teams = set(values.get('farms') or []), set(values.get('teams') or [])
    if len(farms) > 1000 or len(teams) > 2000: frappe.throw('Phạm vi vượt giới hạn.')
    for farm in farms:
        if not frappe.db.exists('Farm', farm): frappe.throw('Vườn không tồn tại: ' + farm)
    for team in teams:
        farm = frappe.db.get_value('Work Team', team, 'farm')
        if not farm or farm not in farms: frappe.throw('Phải chọn vườn tương ứng trước khi cấp tổ: ' + team)
    if user:
        frappe.db.sql('select name from tabUser where name=%s for update', (user,))
        doc = frappe.get_doc('User', user)
        doc.check_permission('write')
        old = grants(user)
        if str(doc.modified) != values.get('modified') or scope_version(old) != values.get('scope_version'):
            frappe.throw('Hồ sơ hoặc phân quyền đã thay đổi. Đóng form và tải lại trước khi lưu.', frappe.TimestampMismatchError)
        current = {r.role for r in doc.roles}
        if (doc.role_profile_name or doc.get('role_profiles')) and selected != current.intersection(allowed):
            frappe.throw('Tài khoản dùng mẫu vai trò. Hãy chỉnh mẫu trong quản trị nâng cao.')
        if user == frappe.session.user and (not cint(values.get('enabled')) or ('System Manager' in current and 'System Manager' not in selected)):
            frappe.throw('Không thể tự khóa tài khoản hoặc gỡ quyền quản trị của chính mình.')
    else:
        email = str(values.get('email') or '').strip().lower()
        validate_email_address(email, throw=True)
        if not email: frappe.throw('Nhập email đăng nhập.')
        doc = frappe.new_doc('User')
        doc.email = email
        doc.user_type = 'System User'
        doc.language = 'vi'
        doc.time_zone = 'Asia/Ho_Chi_Minh'
        old, current = [], set()
    if not str(values.get('first_name') or '').strip(): frappe.throw('Nhập tên người dùng.')
    for key in PROFILE_FIELDS: doc.set(key, cint(values.get(key)) if key == 'enabled' else str(values.get(key) or '').strip())
    # Keep roles outside this screen and profile-managed roles intact.
    if not (doc.role_profile_name or doc.get('role_profiles')):
        doc.set('roles', [{'role': role} for role in sorted((current - allowed) | selected)])
    doc.send_welcome_email = 0
    doc.save()
    desired = {('Farm', f) for f in farms} | {('Work Team', t) for t in teams}
    existing = {(r.allow, r.for_value) for r in old if managed(r)}
    for row in old:
        if managed(row) and (row.allow, row.for_value) not in desired:
            frappe.delete_doc('User Permission', row.name)
    for doctype, value in sorted(desired - existing):
        frappe.get_doc(dict(doctype='User Permission', user=doc.name, allow=doctype, for_value=value,
                             apply_to_all_doctypes=1)).insert()
    link_employee(doc.name, values.get('employee'))
    # The request transaction commits profile, grants and the employee link together.
    return detail_data(doc.name)


def link_employee(user, employee):
    """One employee per login. Empty unlinks; another employee's login is never taken over silently."""
    employee = str(employee or '').strip()
    current = frappe.db.get_value('Employee', {'user_id': user}, 'name')
    if employee == (current or ''):
        return
    if employee:
        row = frappe.db.get_value('Employee', employee, ['name', 'user_id', 'employee_name'], as_dict=True)
        if not row:
            frappe.throw('Nhân sự không tồn tại: ' + employee)
        if row.user_id and row.user_id != user:
            frappe.throw(row.employee_name + ' đã gắn với tài khoản ' + row.user_id + '. Gỡ liên kết đó trước.')
        frappe.get_doc('Employee', employee).check_permission('write')
    if current:
        frappe.db.set_value('Employee', current, 'user_id', None)
    if employee:
        frappe.db.set_value('Employee', employee, 'user_id', user)
