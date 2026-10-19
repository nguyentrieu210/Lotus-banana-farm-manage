"""Lotus farm HR intake. Native HRMS is the source of truth for Employee and Payroll.

Lotus Candidate is intentionally limited to the phone-first recruitment channel because
the installed HRMS Job Applicant requires an email address. Never generate dummy email IDs.
CCCD values use Frappe's encrypted Password storage and a keyed duplicate-detection digest.
"""
import hashlib
import hmac

import frappe
from frappe.utils import getdate, nowdate

from lotus_farm.hr_rules import (
    PAYMENT_BASES, WORKER_CATEGORIES, normalize_cccd,
    normalized_phone, onboarding_gaps, transition_allowed,
)

DESIGNATION_GROUPS = {
    "Điều hành": (
        "Giám đốc nông trường", "Phó giám đốc nông trường",
        "Quản lý vùng", "Trợ lý điều hành", "Giám sát nông trường",
    ),
    "Trồng và chăm sóc": (
        "Quản lý lô", "Đội trưởng chăm sóc", "Tổ trưởng chăm sóc",
        "Công nhân chăm sóc chuối", "Công nhân thời vụ",
        "Công nhân tuyển chồi", "Công nhân phun buồng", "Công nhân bao buồng",
        "Công nhân tưới", "Công nhân thu hoạch", "Công nhân vận chuyển",
    ),
    "Đóng gói và chất lượng": (
        "Quản lý nhà đóng gói", "Tổ trưởng đóng gói", "Nhân viên QC đóng gói",
        "Công nhân sơ chế", "Công nhân phân loại", "Công nhân đóng thùng",
    ),
    "Kho, mua hàng và tài chính": (
        "Quản lý kho", "Thủ kho", "Nhân viên thu mua", "Kế toán kho", "Kế toán nội bộ",
    ),
    "Kỹ thuật và hỗ trợ": (
        "Kỹ thuật nông học", "Tổ trưởng điện nước cơ khí", "Kỹ thuật cơ điện",
        "Nhân viên vận hành UAV", "Lái máy nông nghiệp", "Nhân viên nhân sự",
        "Nhân viên hành chính", "Bảo vệ", "Nhân viên bếp ăn",
    ),
}


def _is_hr_manager():
    return frappe.session.user == "Administrator" or "HR Manager" in frappe.get_roles()


def _hr_access():
    if frappe.session.user == "Guest":
        frappe.throw("Vui lòng đăng nhập.", frappe.AuthenticationError)
    if not (_is_hr_manager() or "HR User" in frappe.get_roles()):
        frappe.throw("Chỉ nhân sự được ủy quyền mới sử dụng phân hệ này.", frappe.PermissionError)


def _manager():
    _hr_access()
    if not _is_hr_manager():
        frappe.throw("Cần vai trò HR Manager để xử lý hồ sơ cá nhân và tiếp nhận.", frappe.PermissionError)


def _company(name):
    doc = frappe.get_doc("Company", name)
    doc.check_permission("read")
    return doc


def _farm(farm, company):
    if not farm:
        return
    doc = frappe.get_doc("Farm", farm)
    doc.check_permission("read")
    if doc.company != company or not doc.active:
        frappe.throw("Nông trường không thuộc công ty hoặc đã ngừng hoạt động.")


def _choose(doctype, name, company=None):
    if not name:
        return None
    doc = frappe.get_doc(doctype, name)
    doc.check_permission("read")
    if company and doc.get("company") and doc.company != company:
        frappe.throw(doctype + " không thuộc công ty.")
    return doc


def _candidate_company_guard(doc):
    _company(doc.company)
    _farm(doc.farm, doc.company)
    if doc.job_opening:
        opening = _choose("Job Opening", doc.job_opening, doc.company)
        if opening.designation != doc.designation:
            frappe.throw("Chức danh ứng tuyển phải khớp tin tuyển dụng.")
    if doc.employee:
        employee = _choose("Employee", doc.employee, doc.company)
        if not employee:
            frappe.throw("Không tìm thấy nhân viên đã tiếp nhận.")


def candidate_guard(doc, method=None):
    _candidate_company_guard(doc)
    if doc.phone:
        try:
            doc.phone = normalized_phone(doc.phone)
        except ValueError as exc:
            frappe.throw(str(exc))
    if doc.status not in ("New", "Screening", "Interview", "Offered", "Rejected", "Hold", "Hired"):
        frappe.throw("Trạng thái tuyển dụng không hợp lệ.")
    if not doc.phone:
        frappe.throw("Ứng viên phải có số điện thoại liên hệ.")
    if doc.status == "Hired" and not doc.employee:
        frappe.throw("Chỉ chuyển Đã tiếp nhận sau khi tạo Employee.")
    old = doc.get_doc_before_save()
    if old:
        if old.status == "Hired" and any(
            doc.get(field) != old.get(field) for field in
            ("applicant_name", "company", "designation", "employee", "phone")
        ):
            frappe.throw("Ứng viên đã tiếp nhận: không sửa thông tin gốc.")
        if not transition_allowed(old.status, doc.status):
            frappe.throw("Chuyển trạng thái ứng viên không hợp lệ.")
    elif doc.status != "New":
        frappe.throw("Hồ sơ ứng viên mới phải bắt đầu ở trạng thái Mới.")


def _id_digest(value):
    from frappe.utils.password import get_encryption_key
    secret = get_encryption_key()
    return hmac.new(str(secret).encode(), value.encode(), hashlib.sha256).hexdigest()


def employee_identity_guard(doc, method=None):
    """Enforce ID uniqueness and farm scope even for Employee writes made in Desk."""
    company = doc.get("company")
    if company:
        _farm(doc.get("lotus_farm"), company)
    team = doc.get("lotus_work_team")
    if team:
        if not doc.get("lotus_farm"):
            frappe.throw("Phải chọn nông trường trước khi chọn tổ/đội.")
        group = frappe.get_doc("Work Team", team)
        group.check_permission("read")
        if group.farm != doc.lotus_farm or group.get("lotus_team_type") == "Contractor":
            frappe.throw("Tổ/đội nhân viên không thuộc nông trường hoặc là đội nhà thầu.")
    payment = doc.get("lotus_payment_basis")
    if payment and payment not in PAYMENT_BASES:
        frappe.throw("Hình thức tính lương không hợp lệ.")
    category = doc.get("lotus_worker_category")
    if category and category not in WORKER_CATEGORIES:
        frappe.throw("Loại nhân sự không hợp lệ.")
    supplied = str(doc.get("lotus_cccd") or "").strip()
    # Frappe Password fields may be masked with asterisks in existing documents.
    if supplied and set(supplied) != {"*"}:
        _manager()
        try:
            value = normalize_cccd(supplied)
        except ValueError as exc:
            frappe.throw(str(exc))
        digest = _id_digest(value)
        duplicated = frappe.db.exists(
            "Employee", {"lotus_cccd_hash": digest, "name": ["!=", doc.name or ""]}
        )
        if duplicated:
            frappe.throw("CCCD đã được đăng ký trong hồ sơ nhân viên khác.")
        doc.lotus_cccd = value
        doc.lotus_cccd_hash = digest
        doc.lotus_cccd_last4 = value[-4:]
    old = doc.get_doc_before_save()
    if not old and not supplied and (doc.get("lotus_cccd_hash") or doc.get("lotus_cccd_last4")):
        frappe.throw("Không được tạo dấu vân tay CCCD thủ công.")
    if old and not (supplied and set(supplied) != {"*"}) and (
        doc.get("lotus_cccd_hash") != old.get("lotus_cccd_hash")
        or doc.get("lotus_cccd_last4") != old.get("lotus_cccd_last4")
    ):
        frappe.throw("Không được sửa dấu vân tay CCCD trực tiếp.")


def install_fields():
    if not frappe.db.exists("DocType", "Employee"):
        return
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    values = [
        dict(fieldname="lotus_farm", label="Lotus · Nông trường", fieldtype="Link",
             options="Farm", insert_after="department"),
        dict(fieldname="lotus_work_team", label="Lotus · Tổ/đội nội bộ", fieldtype="Link",
             options="Work Team", insert_after="lotus_farm"),
        dict(fieldname="lotus_worker_category", label="Lotus · Loại lao động",
             fieldtype="Select", options="\n" + "\n".join(WORKER_CATEGORIES),
             insert_after="employment_type"),
        dict(fieldname="lotus_payment_basis", label="Lotus · Cơ chế công/lương",
             fieldtype="Select", options="\n" + "\n".join(PAYMENT_BASES),
             insert_after="lotus_worker_category"),
        dict(fieldname="lotus_onboarding_state", label="Lotus · Tiếp nhận",
             fieldtype="Select", options="\nPending\nReady", default="Pending",
             read_only=1, insert_after="lotus_payment_basis"),
        dict(fieldname="lotus_cccd", label="Lotus · CCCD (mã hóa)", fieldtype="Password",
             permlevel=1, insert_after="passport_number"),
        dict(fieldname="lotus_cccd_hash", label="Lotus · CCCD digest", fieldtype="Data",
             hidden=1, read_only=1, permlevel=1, insert_after="lotus_cccd"),
        dict(fieldname="lotus_cccd_last4", label="Lotus · 4 số CCCD cuối",
             fieldtype="Data", read_only=1, permlevel=1, insert_after="lotus_cccd_hash"),
        dict(fieldname="lotus_id_issue_on", label="Lotus · Ngày cấp CCCD",
             fieldtype="Date", permlevel=1, insert_after="lotus_cccd_last4"),
        dict(fieldname="lotus_id_issue_at", label="Lotus · Nơi cấp CCCD",
             fieldtype="Data", permlevel=1, insert_after="lotus_id_issue_on"),
        dict(fieldname="lotus_emergency_name", label="Lotus · Liên hệ khẩn cấp",
             fieldtype="Data", permlevel=1, insert_after="lotus_id_issue_at"),
        dict(fieldname="lotus_emergency_phone", label="Lotus · Số khẩn cấp",
             fieldtype="Data", permlevel=1, insert_after="lotus_emergency_name"),
        dict(fieldname="lotus_tax_code", label="Lotus · Mã số thuế cá nhân",
             fieldtype="Data", permlevel=1, insert_after="lotus_emergency_phone"),
        dict(fieldname="lotus_social_insurance_no", label="Lotus · Mã số BHXH",
             fieldtype="Data", permlevel=1, insert_after="lotus_tax_code"),
        # Pay rates feed the monthly payroll sheet (lotus_farm.hr_period); HR Manager only.
        dict(fieldname="lotus_base_salary", label="Lotus · Lương cơ bản tháng",
             fieldtype="Currency", permlevel=1, insert_after="lotus_social_insurance_no"),
        dict(fieldname="lotus_daily_rate", label="Lotus · Đơn giá công nhật",
             fieldtype="Currency", permlevel=1, insert_after="lotus_base_salary"),
    ]
    create_custom_fields({"Employee": values}, update=True, ignore_validate=True)
    # Database uniqueness protects against parallel registrations bypassing API prechecks.
    frappe.db.add_unique("Employee", ["lotus_cccd_hash"], "lotus_cccd_hash_unique")
    from frappe.permissions import add_permission, update_permission_property
    if frappe.db.exists("Role", "HR Manager"):
        add_permission("Employee", "HR Manager", permlevel=1)
        for right in ("read", "write"):
            update_permission_property("Employee", "HR Manager", 1, right, 1)


def _cap(doctype, rights=("read", "create", "write")):
    if not frappe.db.exists("DocType", doctype):
        return {}
    return {right: bool(frappe.has_permission(doctype, right)) for right in rights}


@frappe.whitelist()
def bootstrap():
    _hr_access()
    from frappe.sessions import get_csrf_token
    companies = frappe.get_list("Company", fields=["name", "default_currency"], limit_page_length=0)
    return {
        "user": frappe.session.user, "csrf_token": get_csrf_token(),
        "today": nowdate(), "companies": companies, "is_hr_manager": _is_hr_manager(),
        "capabilities": {dt: _cap(dt) for dt in (
            "Employee", "Lotus Candidate", "Designation", "Department",
            "Job Opening", "Job Applicant", "Employee Grade",
            "Salary Structure Assignment", "Employee Onboarding",
        )},
    }


@frappe.whitelist()
def catalogue(company):
    _hr_access()
    _company(company)
    def rows(dt, filters, fields):
        return frappe.get_list(dt, filters=filters, fields=fields,
                               limit_page_length=0, order_by="name") if frappe.has_permission(dt, "read") else []
    farms = rows("Farm", {"company": company, "active": 1}, ["name", "farm_name"])
    departments = rows("Department", {"company": company, "is_group": 0}, ["name", "department_name"])
    designations = rows("Designation", {}, ["name", "designation_name"])
    teams = rows("Work Team", {"active": 1, "farm": ["in", [f.name for f in farms]]},
                 ["name", "team_name", "farm", "lotus_team_type"])
    employment_types = rows("Employment Type", {}, ["name"])
    grades = rows("Employee Grade", {}, ["name"])
    genders = rows("Gender", {}, ["name"])
    openings = rows("Job Opening", {"company": company, "status": "Open"},
                    ["name", "job_title", "designation", "vacancies"])
    return dict(farms=farms, departments=departments, designations=designations,
                teams=teams, employment_types=employment_types, grades=grades,
                genders=genders, openings=openings, designation_groups=DESIGNATION_GROUPS,
                worker_categories=WORKER_CATEGORIES, payment_bases=PAYMENT_BASES)


@frappe.whitelist()
def overview(company):
    _hr_access()
    _company(company)
    people = frappe.get_list(
        "Employee", filters={"company": company},
        fields=["name", "employee_name", "status", "department", "designation",
                "employment_type", "lotus_worker_category", "lotus_payment_basis",
                "lotus_farm", "lotus_work_team", "lotus_onboarding_state",
                "date_of_joining", "contract_end_date"],
        order_by="employee_name asc", limit_page_length=0,
    )
    candidates = frappe.get_list(
        "Lotus Candidate", filters={"company": company},
        fields=["name", "applicant_name", "phone", "designation", "farm", "source",
                "applied_on", "status", "employee", "modified"],
        order_by="modified desc", limit_page_length=0,
    )
    return dict(employees=people, candidates=candidates)


@frappe.whitelist()
def candidate_detail(company, candidate):
    _hr_access()
    _company(company)
    doc = _choose('Lotus Candidate', candidate, company)
    doc.check_permission('read')
    return {key: doc.get(key) for key in (
        'name', 'applicant_name', 'phone', 'email', 'company', 'farm', 'designation',
        'job_opening', 'applied_on', 'source', 'status', 'interview_on', 'notes',
        'employee', 'modified'
    )}


@frappe.whitelist()
def employee_detail(company, employee):
    _manager()
    _company(company)
    doc = _choose("Employee", employee, company)
    doc.check_permission("read")
    fields = [
        "name", "employee_name", "gender", "date_of_birth", "date_of_joining",
        "status", "department", "designation", "reports_to", "grade",
        "employment_type", "lotus_worker_category", "lotus_payment_basis",
        "lotus_farm", "lotus_work_team", "lotus_onboarding_state",
        "cell_number", "personal_email", "current_address", "permanent_address",
        "lotus_cccd_last4", "lotus_id_issue_on", "lotus_id_issue_at",
        "lotus_emergency_name", "lotus_emergency_phone", "lotus_tax_code",
        "lotus_social_insurance_no", "health_insurance_no",
        "contract_end_date", "job_applicant", "relieving_date", "reason_for_leaving",
        "lotus_base_salary", "lotus_daily_rate",
    ]
    return {k: doc.get(k) for k in fields} | {
        "cccd_recorded": bool(doc.get("lotus_cccd_hash")),
        "onboarding_gaps": onboarding_gaps(doc),
        "modified": str(doc.modified),
    }


def _apply_employee(doc, values, company, new):
    # Explicit allowlist: never accept docstatus, linked user or role data. Pay rates are permlevel 1
    # (HR Manager) and every caller of this function already requires HR Manager.
    for field, label in (("lotus_base_salary", "Lương cơ bản"), ("lotus_daily_rate", "Đơn giá công nhật")):
        if field in values:
            from lotus_farm.warehouse import _number
            amount = _number(values[field] or 0, label, allow_zero=True)
            if amount > 1_000_000_000:
                frappe.throw(label + " vượt giới hạn hợp lệ.")
            doc.set(field, amount)
    simple = (
        "gender", "date_of_birth", "date_of_joining", "designation", "department",
        "employment_type", "grade", "reports_to", "cell_number", "personal_email",
        "current_address", "permanent_address", "contract_end_date",
        "lotus_worker_category", "lotus_payment_basis",
        "lotus_farm", "lotus_work_team", "lotus_id_issue_on", "lotus_id_issue_at",
        "lotus_emergency_name", "lotus_emergency_phone", "lotus_tax_code",
        "lotus_social_insurance_no", "health_insurance_no",
    )
    for field in simple:
        if field in values:
            doc.set(field, values[field] or None)
    if "employee_name" in values:
        name = str(values["employee_name"] or "").strip()
        if len(name) < 2 or len(name) > 140:
            frappe.throw("Nhập họ và tên nhân viên (2–140 ký tự).")
        doc.first_name = name
        doc.last_name = ""
    doc.company = company
    for doctype, name in (("Designation", doc.designation),
                          ("Employment Type", doc.employment_type),
                          ("Employee Grade", doc.grade)):
        _choose(doctype, name)
    if doc.department:
        _choose("Department", doc.department, company)
    if doc.reports_to:
        boss = _choose("Employee", doc.reports_to, company)
        if not new and boss.name == doc.name:
            frappe.throw("Không thể tự làm người quản lý của mình.")
    if doc.cell_number:
        try:
            doc.cell_number = normalized_phone(doc.cell_number)
        except ValueError as exc:
            frappe.throw(str(exc))
    if doc.lotus_emergency_phone:
        try:
            doc.lotus_emergency_phone = normalized_phone(doc.lotus_emergency_phone)
        except ValueError as exc:
            frappe.throw(str(exc))
    if doc.date_of_birth and getdate(doc.date_of_birth) >= getdate(nowdate()):
        frappe.throw("Ngày sinh phải trước ngày hiện tại.")
    if doc.contract_end_date and doc.date_of_joining and getdate(doc.contract_end_date) < getdate(doc.date_of_joining):
        frappe.throw("Ngày hết hạn hợp đồng không được trước ngày vào làm.")
    if "cccd" in values and str(values["cccd"] or "").strip():
        try:
            doc.lotus_cccd = normalize_cccd(values["cccd"])
        except ValueError as exc:
            frappe.throw(str(exc))
    if new:
        doc.status = "Inactive"
        doc.lotus_onboarding_state = "Pending"
        doc.create_user_automatically = 0
        doc.create_user_permission = 0


@frappe.whitelist(methods=["POST"])
def check_cccd(company, cccd, employee=None):
    """Preflight duplicate check; never return another employee's details."""
    _manager()
    _company(company)
    if not frappe.has_permission("Employee", "read"):
        frappe.throw("Không có quyền kiểm tra CCCD.", frappe.PermissionError)
    try:
        value = normalize_cccd(cccd)
    except ValueError as exc:
        frappe.throw(str(exc))
    if employee:
        current = _choose("Employee", employee, company)
        current.check_permission("read")
    duplicate = frappe.db.exists(
        "Employee", {"lotus_cccd_hash": _id_digest(value), "name": ["!=", employee or ""]}
    )
    return {"duplicate": bool(duplicate)}


@frappe.whitelist(methods=["POST"])
def save_employee(company, values, employee=None, modified=None):
    _manager()
    _company(company)
    values = frappe.parse_json(values)
    if not isinstance(values, dict):
        frappe.throw("Dữ liệu nhân viên không hợp lệ.")
    new = not bool(employee)
    doc = frappe.new_doc("Employee") if new else _choose("Employee", employee, company)
    doc.check_permission("create" if new else "write")
    if not new and str(doc.modified) != str(modified):
        frappe.throw("Hồ sơ đã thay đổi. Tải lại trước khi cập nhật.")
    _apply_employee(doc, values, company, new)
    doc.save() if not new else doc.insert()
    return dict(name=doc.name, onboarding_state=doc.lotus_onboarding_state)


@frappe.whitelist(methods=["POST"])
def set_onboarding_ready(company, employee, modified):
    _manager()
    _company(company)
    doc = _choose("Employee", employee, company)
    doc.check_permission("write")
    if str(doc.modified) != str(modified):
        frappe.throw("Hồ sơ đã thay đổi. Tải lại trước khi duyệt tiếp nhận.")
    if doc.lotus_onboarding_state == "Ready":
        frappe.throw("Nhân viên đã hoàn tất tiếp nhận.")
    if doc.status not in ("Inactive", "Active"):
        frappe.throw("Không thể duyệt tiếp nhận nhân viên đã nghỉ hoặc bị đình chỉ.")
    gaps = onboarding_gaps(doc)
    if gaps:
        frappe.throw("Chưa đủ hồ sơ tiếp nhận: " + ", ".join(gaps))
    doc.lotus_onboarding_state = "Ready"
    doc.status = "Active"
    doc.save()
    return dict(name=doc.name, status=doc.status)


@frappe.whitelist(methods=["POST"])
def save_candidate(company, values, name=None, modified=None):
    _hr_access()
    _company(company)
    values = frappe.parse_json(values)
    if not isinstance(values, dict):
        frappe.throw("Dữ liệu ứng viên không hợp lệ.")
    if not frappe.has_permission("Lotus Candidate", "create" if not name else "write"):
        frappe.throw("Chưa có quyền ghi ứng viên.", frappe.PermissionError)
    doc = frappe.new_doc("Lotus Candidate") if not name else _choose("Lotus Candidate", name, company)
    doc.check_permission("create" if not name else "write")
    if name and str(doc.modified) != str(modified):
        frappe.throw("Ứng viên đã có thay đổi. Tải lại trước khi sửa.")
    fields = ("applicant_name", "phone", "email", "farm", "designation", "job_opening",
              "applied_on", "source", "interview_on", "notes", "status")
    for key in fields:
        if key in values:
            doc.set(key, values[key] or None)
    doc.applicant_name = str(doc.applicant_name or "").strip()
    if len(doc.applicant_name) < 2 or len(doc.applicant_name) > 140:
        frappe.throw("Nhập họ tên ứng viên từ 2 đến 140 ký tự.")
    if not doc.applied_on:
        doc.applied_on = nowdate()
    if not name:
        doc.status = "New"
    elif doc.status == "Hired":
        frappe.throw("Chuyển Đã tiếp nhận phải thông qua bước tạo Employee.")
    doc.company = company
    doc.save() if name else doc.insert()
    return dict(name=doc.name, status=doc.status)


@frappe.whitelist(methods=["POST"])
def hire_candidate(company, candidate, values, modified):
    _manager()
    _company(company)
    lead = _choose("Lotus Candidate", candidate, company)
    lead.check_permission("write")
    if str(lead.modified) != str(modified) or lead.status != "Offered" or lead.employee:
        frappe.throw("Ứng viên phải ở trạng thái Đã mời nhận việc và chưa được tiếp nhận. Tải lại.")
    values = frappe.parse_json(values)
    if not isinstance(values, dict):
        frappe.throw("Dữ liệu tiếp nhận không hợp lệ.")
    frappe.db.sql("SELECT name FROM `tabLotus Candidate` WHERE name=%s FOR UPDATE", (lead.name,))
    # Re-read after taking row lock to prevent concurrent hires of the same candidate.
    lead.reload()
    if lead.status != "Offered" or lead.employee or str(lead.modified) != str(modified):
        frappe.throw("Ứng viên đã được tiếp nhận hoặc có thay đổi.")
    doc = frappe.new_doc("Employee")
    doc.check_permission("create")
    values = {**values, "employee_name": lead.applicant_name,
              "designation": lead.designation, "lotus_farm": lead.farm,
              "cell_number": values.get("cell_number") or lead.phone}
    _apply_employee(doc, values, company, True)
    doc.insert()
    lead.employee = doc.name
    lead.status = "Hired"
    lead.save()
    return dict(name=doc.name, candidate=lead.name)


@frappe.whitelist(methods=["POST"])
def seed_designations(company):
    _manager()
    _company(company)
    if not frappe.has_permission("Designation", "create"):
        frappe.throw("Chưa có quyền tạo chức danh.", frappe.PermissionError)
    created = []
    existing = {r.name for r in frappe.get_all("Designation", fields=["name"], limit_page_length=0)}
    for group, names in DESIGNATION_GROUPS.items():
        for name in names:
            if name not in existing:
                doc = frappe.get_doc({
                    "doctype": "Designation", "designation_name": name,
                    "description": "Lotus · " + group,
                })
                doc.insert()
                existing.add(name)
                created.append(name)
    return dict(created=created, count=len(created))



@frappe.whitelist()
def payroll_readiness(company, month):
    """Read-only pre-payroll checks. Never posts salary slips or converts crew costs to wages."""
    _manager()
    _company(company)
    if not (frappe.has_permission("Employee", "read")
            and frappe.has_permission("Attendance", "read")):
        frappe.throw("Chưa có quyền xem dữ liệu đối soát lương.", frappe.PermissionError)
    from lotus_farm.timekeeping_rules import month_range
    text = str(month or "")
    try:
        begin, end = month_range(text)
    except ValueError:
        frappe.throw("Tháng đối soát cần ở dạng YYYY-MM.")
    people = frappe.get_list(
        "Employee", filters={"company": company, "status": "Active", "date_of_joining": ["<=", end]},
        fields=["name", "employee_name", "lotus_payment_basis", "lotus_base_salary", "lotus_daily_rate",
                "lotus_onboarding_state"], limit_page_length=0,
    )

    def rate_gap(person):
        basis = person.lotus_payment_basis
        if not basis:
            return "Chưa chọn cơ chế lương"
        if basis in ("Monthly", "Mixed") and not person.lotus_base_salary:
            return "Thiếu lương cơ bản"
        if basis in ("Daywork", "Mixed") and not person.lotus_daily_rate:
            return "Thiếu đơn giá công"
        return None

    missing = [dict(name=e.name, employee_name=e.employee_name, issue=rate_gap(e)) for e in people if rate_gap(e)]
    pending = [dict(name=e.name, employee_name=e.employee_name) for e in people if e.lotus_onboarding_state != "Ready"]
    drafts = frappe.get_list(
        "Attendance",
        filters={"company": company, "attendance_date": ["between", [begin, end]], "docstatus": 0},
        fields=["name"], limit_page_length=0,
    )
    crew_rows = []
    if frappe.has_permission("Lotus Crew Attendance", "read"):
        crew_rows = frappe.get_list(
            "Lotus Crew Attendance",
            filters={"company": company, "posting_date": ["between", [begin, end]],
                     "docstatus": ["<", 2]},
            fields=["name", "work_team", "work_type", "amount", "docstatus"],
            limit_page_length=0,
        )
    return dict(month=text, employees=len(people), employees_without_salary=missing,
                attendance_draft_count=len(drafts),
                crew_pending_count=sum(1 for c in crew_rows if c.docstatus == 0),
                crew_submitted_count=sum(1 for c in crew_rows if c.docstatus == 1),
                crew_approved_amount=sum(float(c.amount or 0) for c in crew_rows if c.docstatus == 1),
                onboarding_pending=pending,
                open_punches=frappe.db.count("Lotus Attendance Punch", {
                    "company": company, "state": ["!=", "Synced"],
                    "punched_at": ["between", [str(begin) + " 00:00:00", str(end) + " 23:59:59"]]}),
                note="Giá trị khoán đội là khoản phải trả cho đội, không phải lương người lao động.")


@frappe.whitelist(methods=["POST"])
def offboard_employee(company, employee, relieving_date, reason, modified):
    """Mark an employee as left and close the open staff assignment and device identity."""
    _manager()
    _company(company)
    doc = _choose("Employee", employee, company)
    doc.check_permission("write")
    if str(doc.modified) != str(modified):
        frappe.throw("Hồ sơ đã thay đổi. Tải lại trước khi cập nhật.")
    if doc.status == "Left":
        frappe.throw("Nhân viên đã nghỉ việc.")
    last_day = getdate(relieving_date) if relieving_date else None
    reason = str(reason or "").strip()
    if not last_day or not reason:
        frappe.throw("Nhập ngày nghỉ việc và lý do.")
    if doc.date_of_joining and last_day < getdate(doc.date_of_joining):
        frappe.throw("Ngày nghỉ việc không được trước ngày vào làm.")
    later = frappe.db.count("Attendance", {"employee": doc.name, "attendance_date": [">", last_day], "docstatus": ["<", 2]})
    if later:
        frappe.throw("Còn " + str(later) + " phiếu công sau ngày nghỉ việc. Hủy hoặc xóa các phiếu đó trước.")
    from lotus_farm.controls import lock
    lock("Employee", doc.name)
    doc.status = "Left"
    doc.relieving_date = last_day
    doc.reason_for_leaving = reason[:500]
    doc.save()
    closed = 0
    for doctype, start in (("Lotus Staff Assignment", "valid_from"), ("Lotus Attendance Identity", "valid_from")):
        for name in frappe.get_all(doctype, filters={"employee": doc.name, "valid_to": ["is", "not set"]}, pluck="name"):
            item = frappe.get_doc(doctype, name)
            item.valid_to = max(last_day, getdate(item.get(start))) if item.get(start) else last_day
            if doctype == "Lotus Attendance Identity":
                item.active = 0
            item.save()
            closed += 1
    return dict(name=doc.name, status=doc.status, closed=closed)

@frappe.whitelist()
def payroll_overview(company):
    _manager()
    _company(company)
    if not (frappe.has_permission("Employee Grade", "read")
            and frappe.has_permission("Salary Structure Assignment", "read")):
        frappe.throw("Chưa có quyền xem cấu hình lương.", frappe.PermissionError)
    grades = frappe.get_list("Employee Grade",
        fields=["name", "default_salary_structure", "default_base_pay", "currency"],
        limit_page_length=0)
    assignments = frappe.get_list(
        "Salary Structure Assignment",
        filters={"company": company, "docstatus": 1},
        fields=["employee", "salary_structure", "base", "currency", "from_date"],
        order_by="from_date desc", limit_page_length=0,
    )
    latest = {}
    for item in assignments:
        latest.setdefault(item.employee, item)
    return dict(grades=grades, assignments=list(latest.values()))
