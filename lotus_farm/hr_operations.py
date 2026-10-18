"""Lotus HR organization, guarded imports and attendance-device staging.

HRMS Employee, Department, Designation, Shift Type, Employee Checkin and
Attendance remain the source of truth. A device punch is evidence, not paid time.
No biometric templates or device credentials are stored in this module.
"""
from __future__ import annotations
import hashlib
import json
import re
from datetime import timedelta

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, get_datetime, now_datetime, nowdate

DEVICE_MODES = ("File CSV", "ADMS", "LAN SDK", "Vendor Cloud")
IMPORT_KINDS = ("Department", "Designation", "Work Team", "Employee", "Staff Assignment", "Shift Type", "Shift Assignment", "Device Mapping", "Checkin CSV")
IMAGE_STRUCTURE = [
    ("BOARD", "Ban quản lý vườn", None),
    ("TECH", "Bộ phận kỹ thuật", "BOARD"),
    ("SUPPLY", "Bộ phận vật tư", "BOARD"),
    ("OFFICE", "Bộ phận văn phòng", "BOARD"),
    ("PACK", "Xưởng đóng gói", "BOARD"),
    ("MAINT", "Cơ giới - Cơ khí - Điện nước - Bảo vệ", "BOARD"),
    ("TEAM_A", "Đội chăm sóc khu A", "BOARD"),
    ("TEAM_B", "Đội chăm sóc khu B", "BOARD"),
    ("TEAM_C", "Đội chăm sóc khu C", "BOARD"),
    ("TEAM_D", "Đội chăm sóc khu D", "BOARD"),
]
IMAGE_POSITIONS = [
    ("DIR", "Giám đốc vườn"), ("DEP", "Phó giám đốc vườn"),
    ("TECH", "Kỹ sư nông nghiệp"), ("TECHNICIAN", "Kỹ thuật viên"),
    ("STORE", "Thủ kho"), ("SUPPLY", "Nhân viên vật tư"),
    ("PLAN", "Nhân viên kế hoạch"), ("ACCOUNT", "Kế toán nội bộ"),
    ("HR", "Nhân viên hành chính nhân sự"),
    ("PACK", "Quản lý xưởng đóng gói"), ("QC", "Nhân viên QC"),
    ("HARVEST", "Công nhân thu hoạch"), ("SORT", "Công nhân sơ chế - đóng gói"),
    ("MECH", "Nhân viên cơ khí điện nước"), ("GUARD", "Bảo vệ"),
    ("LEAD", "Đội trưởng chăm sóc"), ("FOREMAN", "Tổ trưởng chăm sóc"),
    ("WORKER", "Công nhân chăm sóc chuối"), ("SEASON", "Công nhân thời vụ"),
]


def _hr():
    from lotus_farm.hr_workspace import _hr_access
    _hr_access()


def _manager():
    from lotus_farm.hr_workspace import _manager
    _manager()


def _company(company):
    _hr()
    if not company:
        frappe.throw("Chọn công ty.")
    doc = frappe.get_doc("Company", company)
    doc.check_permission("read")
    return doc


def _farm(company, farm):
    if not farm:
        frappe.throw("Chọn vườn.")
    doc = frappe.get_doc("Farm", farm)
    doc.check_permission("read")
    if doc.company != company or not doc.active:
        frappe.throw("Vườn không thuộc công ty hoặc đã ngừng.")
    return doc


def _device(company, device):
    doc = frappe.get_doc("Lotus Attendance Device", device)
    doc.check_permission("read")
    _farm(company, doc.farm)
    if doc.company != company:
        frappe.throw("Máy chấm công không thuộc công ty.")
    return doc


def _text(raw, field, limit=140):
    value = str(raw or "").strip()
    if not value or len(value) > limit:
        raise ValueError(field + " không hợp lệ.")
    return value


def _date(raw, field):
    if not raw:
        raise ValueError('Thiếu ngày '+field+'.')
    try:
        return str(getdate(raw))
    except Exception as exc:
        raise ValueError("Sai ngày " + field + ".") from exc


def _moment(raw):
    value = str(raw or "").strip().replace("T", " ")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2} \d\d:\d\d(?::\d\d)?", value):
        raise ValueError("Thời điểm quẹt phải là YYYY-MM-DD HH:MM:SS.")
    result = get_datetime(value)
    if result > now_datetime() + timedelta(minutes=5):
        raise ValueError("Log máy có thời gian ở tương lai.")
    return result.strftime("%Y-%m-%d %H:%M:%S")


def _scope_read(dt, filters=None, fields=None, limit=3000):
    if not frappe.has_permission(dt, "read"):
        return []
    return frappe.get_list(dt, filters=filters or {}, fields=fields or ["name"],
                           order_by="modified desc", limit_page_length=limit)


def _same_company_employee(company, employee):
    doc = frappe.get_doc("Employee", employee)
    doc.check_permission("read")
    if doc.company != company:
        frappe.throw("Nhân viên không thuộc công ty.")
    return doc


class LotusAttendanceDevice(Document):
    def validate(self):
        _farm(self.company, self.farm)
        self.device_code = _text(self.device_code, "Mã máy", 40)
        self.device_name = _text(self.device_name, "Tên máy", 140)
        if self.connection_mode not in DEVICE_MODES:
            frappe.throw("Chưa chọn cách kết nối hợp lệ.")
        if self.timezone and self.timezone != "Asia/Ho_Chi_Minh":
            frappe.throw("Máy chấm công phải dùng múi giờ Asia/Ho_Chi_Minh hoặc để trống.")
        existing = frappe.db.exists("Lotus Attendance Device", {
            "device_code": self.device_code, "name": ["!=", self.name or ""]})
        if existing:
            frappe.throw("Mã máy đã tồn tại.")
    def on_trash(self):
        if frappe.db.exists("Lotus Attendance Punch", {"device":self.name}):
            frappe.throw("Không xóa máy đã có nhật ký quẹt; hãy tắt Đang sử dụng.")


class LotusAttendanceIdentity(Document):
    def validate(self):
        d = _device(self.company, self.device)
        if d.farm != self.farm:
            frappe.throw("Vườn gắn mã máy phải trùng vườn đặt máy.")
        person = _same_company_employee(self.company, self.employee)
        if person.status != "Active":
            frappe.throw("Chỉ liên kết mã máy với nhân viên đang làm việc.")
        if person.get("lotus_farm") and person.lotus_farm != self.farm:
            frappe.throw("Nhân viên không thuộc vườn của máy.")
        self.device_user_id = _text(self.device_user_id, "Mã chấm công", 80)
        if self.valid_to and getdate(self.valid_to) < getdate(self.valid_from):
            frappe.throw("Khoảng hiệu lực mã máy không hợp lệ.")
        conflicts = frappe.get_all("Lotus Attendance Identity", filters={
            "device":self.device, "device_user_id":self.device_user_id,
            "name":["!=",self.name or ""], "active":1
        }, fields=["valid_from", "valid_to"], limit_page_length=200)
        start, end = getdate(self.valid_from), getdate(self.valid_to) if self.valid_to else None
        for old in conflicts:
            previous_start = getdate(old.valid_from)
            previous_end = getdate(old.valid_to) if old.valid_to else None
            if (not end or end >= previous_start) and (not previous_end or start <= previous_end):
                frappe.throw("Mã chấm công bị trùng thời gian hiệu lực trên cùng máy.")


class LotusAttendancePunch(Document):
    RAW = ("company","farm","device","device_user_id","punched_at","log_type",
           "source_event_id","event_hash","source")
    def validate(self):
        machine = _device(self.company, self.device)
        if machine.farm != self.farm:
            frappe.throw('Vườn của log không trùng với máy.')
        self.device_user_id = _text(self.device_user_id, "Mã trên máy", 80)
        self.punched_at = _moment(self.punched_at)
        if self.log_type not in ("IN","OUT","",None):
            frappe.throw("Log phải là IN hoặc OUT (hoặc chưa rõ).")
        old = self.get_doc_before_save()
        if old:
            for field in self.RAW:
                if str(self.get(field) or "") != str(old.get(field) or ""):
                    frappe.throw("Không được sửa nhật ký gốc từ máy.")
            if not self.flags.get('lotus_promotion') and any(self.get(field)!=old.get(field) for field in ('state','employee','employee_checkin')):
                frappe.throw('Không sửa kết quả ghép log trực tiếp; phải dùng bước đối chiếu HRMS.')
            if old.state == "Synced" and (self.state != old.state or self.employee_checkin != old.employee_checkin):
                frappe.throw("Không đổi log đã đưa sang HRMS.")
        if self.event_hash != _signature(self.device, {k:self.get(k) for k in self.RAW}):
            frappe.throw('Mã chống trùng không khớp log gốc.')
        if not old and (self.state not in ('Ready','Unmapped') or self.employee_checkin):
            frappe.throw('Log mới chỉ nhận Ready hoặc Unmapped, chưa có HRMS Checkin.')
        if old and any(self.get(f)!=old.get(f) for f in ('state','employee','employee_checkin')) and not self.flags.get('lotus_promotion'):
            frappe.throw('Chỉ xử lý log qua chức năng đối chiếu chấm công.')
        if self.employee:
            _same_company_employee(self.company, self.employee)
    def on_trash(self):
        frappe.throw("Không xóa log quẹt gốc; chỉ được đối chiếu trạng thái.")


class LotusStaffAssignment(Document):
    def validate(self):
        _farm(self.company, self.farm)
        person = _same_company_employee(self.company,self.employee)
        if person.get("lotus_farm") and person.lotus_farm != self.farm:
            frappe.throw("Phân công khác vườn hiện có; hãy điều chuyển nhân sự qua HRMS trước.")
        if self.department:
            dep=frappe.get_doc("Department",self.department)
            dep.check_permission("read")
            if dep.company != self.company:frappe.throw("Bộ phận khác công ty.")
        if self.work_team:
            team=frappe.get_doc("Work Team",self.work_team)
            team.check_permission("read")
            if team.farm != self.farm or team.get("lotus_team_type")=="Contractor":
                frappe.throw("Tổ/đội không thuộc vườn hoặc là nhà thầu.")
        if self.designation:
            frappe.get_doc("Designation",self.designation).check_permission("read")
        if self.approver:
            _same_company_employee(self.company,self.approver)
            if self.approver == self.employee:frappe.throw("Không được tự làm cấp trên.")
        start = getdate(self.valid_from)
        end = getdate(self.valid_to) if self.valid_to else None
        if end and end < start:frappe.throw("Thời gian phân công không hợp lệ.")
        others=frappe.get_all("Lotus Staff Assignment",filters={
            "employee":self.employee,"name":["!=",self.name or ""]},
            fields=["valid_from","valid_to"],limit_page_length=200)
        for prior in others:
            pstart=getdate(prior.valid_from)
            pend=getdate(prior.valid_to) if prior.valid_to else None
            if (not end or pstart <= end) and (not pend or pend >= start):
                frappe.throw("Nhân viên đã có một phân công khác trong khoảng thời gian này.")


@frappe.whitelist()
def organization(company):
    _company(company)
    farms=_scope_read("Farm",{"company":company,"active":1},["name","farm_name"])
    departments=_scope_read("Department",{"company":company},
        ["name","department_name","parent_department","is_group"])
    teams=_scope_read("Work Team",{"farm":["in",[f.name for f in farms] or ["__none__"]]},
        ["name","farm","team_code","team_name","lotus_team_type","active"])
    employees=_scope_read("Employee",{"company":company},
        ["name","employee_name","designation","department","reports_to","lotus_farm",
         "lotus_work_team","status"],limit=5000)
    assignments=_scope_read("Lotus Staff Assignment",{"company":company},
        ["name","employee","farm","department","designation","work_team",
         "role_title","valid_from","valid_to","approver"],limit=5000)
    designations=_scope_read("Designation",{},["name","designation_name"],limit=500)
    return dict(farms=farms,departments=departments,designations=designations,teams=teams,
        employees=employees,assignments=assignments,
        template_departments=[dict(code=x,name=y,parent=z) for x,y,z in IMAGE_STRUCTURE],
        template_positions=[dict(code=x,name=y) for x,y in IMAGE_POSITIONS],
        notes=["Ảnh mẫu: 4 đội × 55 ha = 220 ha, nhưng mỗi đội 2 tổ × 25 ha = 50 ha; cần chốt phần 5 ha còn lại.",
               "Phòng ban, tổ/đội, chức danh, chức vụ và quyền đăng nhập là các thông tin khác nhau.",
               "Sơ đồ mẫu không tự tạo nhân viên hoặc gán mức lương."])


@frappe.whitelist()
def devices(company, farm=None):
    _company(company)
    if farm:_farm(company,farm)
    filters={"company":company}
    if farm:filters["farm"]=farm
    machines=_scope_read("Lotus Attendance Device",filters,
        ["name","device_code","device_name","farm","model","connection_mode",
         "active","last_event_at"],limit=1000)
    identities=_scope_read("Lotus Attendance Identity",filters,
        ["name","device","device_user_id","employee","valid_from","valid_to","active"],limit=5000)
    recent=_scope_read("Lotus Attendance Punch",filters,
        ["name","device","device_user_id","punched_at","employee",
         "log_type","state","source","employee_checkin"],limit=300)
    return dict(machines=machines,mappings=identities,punches=recent,
                counts={state:sum(p.state==state for p in recent) for state in ("Unmapped","Ready","Synced","Needs Review")},
                note="Máy kết nối LAN/ADMS/Cloud chỉ được bật khi đã có model, giao thức và xác minh bảo mật. CSV hoạt động ngay.")


def _mapping(company, device, device_user_id, time):
    matches=frappe.get_all("Lotus Attendance Identity",filters={
        "company":company,"device":device,"device_user_id":str(device_user_id),"active":1,
        "valid_from":["<=",time[:10]]},fields=["employee","valid_to"],limit_page_length=50)
    items=[x.employee for x in matches if not x.valid_to or str(x.valid_to)>=time[:10]]
    return items[0] if len(items)==1 else None


def _signature(device, event):
    fields=[device,str(event["device_user_id"]),str(event["punched_at"]),
            str(event.get("log_type") or ""),str(event.get("source_event_id") or "")]
    return hashlib.sha256(json.dumps(fields,ensure_ascii=False).encode()).hexdigest()


def _checkin_normalize(row):
    result={
        "device":_text(row.get("device"),"Máy"),
        "device_user_id":_text(row.get("device_user_id"),"Mã trên máy",80),
        "punched_at":_moment(row.get("punched_at")),
        "log_type":str(row.get("log_type") or "").upper().strip(),
        "source_event_id":str(row.get("source_event_id") or "").strip()[:140],
    }
    if result["log_type"] not in ("","IN","OUT"):
        raise ValueError("Vào/ra chỉ nhận IN, OUT hoặc trống.")
    return result


def _parse_rows(rows,maximum=500):
    rows=frappe.parse_json(rows) if isinstance(rows,str) else rows
    if not isinstance(rows,list) or not 1<=len(rows)<=maximum:
        frappe.throw("Chọn từ 1 đến %s dòng trong mỗi lần nhập."%maximum)
    if any(not isinstance(row,dict) for row in rows):
        frappe.throw("Các dòng nhập phải là bảng dữ liệu.")
    return rows


def _check_import(company,kind,rows):
    _company(company)
    if kind not in IMPORT_KINDS:
        frappe.throw("Loại danh mục nhập không hợp lệ.")
    errors=[];normalized=[];seen=set()
    for i,row in enumerate(rows):
        try:
            if kind=="Designation":
                item={"designation_name":_text(row.get("designation_name"),"Chức danh")}
                key=item["designation_name"].casefold()
            elif kind=="Department":
                item={"department_name":_text(row.get("department_name"),"Bộ phận"),
                      "parent_department":str(row.get("parent_department") or "").strip()}
                key=item["department_name"].casefold()
                if item["parent_department"] and not frappe.db.exists("Department",item["parent_department"]):
                    raise ValueError("Bộ phận cha phải tồn tại trước khi nhập.")
            elif kind=="Work Team":
                item={"team_code":_text(row.get("team_code"),"Mã tổ",40),
                      "team_name":_text(row.get("team_name"),"Tên tổ"),
                      "farm":_text(row.get("farm"),"Vườn"),
                      "lotus_team_type":"Internal"}
                _farm(company,item["farm"])
                key=item["farm"]+":"+item["team_code"]
            elif kind=="Employee":
                item={"employee_name":_text(row.get("employee_name"),"Họ tên"),
                      "gender":_text(row.get("gender"),"Giới tính",20),
                      "date_of_birth":_date(row.get("date_of_birth"),"sinh"),
                      "date_of_joining":_date(row.get("date_of_joining"),"vào làm"),
                      "designation":_text(row.get("designation"),"Chức danh"),
                      "department":_text(row.get("department"),"Bộ phận"),
                      "lotus_farm":_text(row.get("lotus_farm"),"Vườn"),
                      "lotus_work_team":str(row.get("lotus_work_team") or "").strip(),
                      "attendance_device_id":str(row.get("attendance_device_id") or "").strip()}
                _farm(company,item["lotus_farm"])
                if getdate(item["date_of_birth"]) >= getdate(nowdate()):
                    raise ValueError('Ngày sinh phải trước ngày hiện tại.')
                if not frappe.db.exists('Gender',item['gender']):
                    raise ValueError('Giới tính không nằm trong danh mục HRMS.')
                if frappe.db.exists('Employee',{'company':company,'employee_name':item['employee_name'],
                     'date_of_birth':item['date_of_birth']}):
                    raise ValueError('Nhân viên trùng tên và ngày sinh đã có trong công ty; hãy đối chiếu trước.')
                for link,value in [("Designation",item["designation"]),("Department",item["department"])]:
                    if not frappe.db.exists(link,value):raise ValueError(link+" chưa có: "+value)
                if frappe.db.get_value('Department',item['department'],'company')!=company:
                    raise ValueError('Bộ phận không thuộc công ty.')
                if item["lotus_work_team"]:
                    team=frappe.get_doc("Work Team",item["lotus_work_team"])
                    team.check_permission('read')
                    if team.farm!=item["lotus_farm"] or team.lotus_team_type=="Contractor":
                        raise ValueError("Tổ không thuộc vườn hoặc là đội khoán.")
                if item["attendance_device_id"] and frappe.db.exists("Employee",{"attendance_device_id":item["attendance_device_id"]}):
                    raise ValueError("Mã chấm công đã dùng cho nhân viên khác.")
                key="emp:"+item["employee_name"].casefold()+":"+item["date_of_birth"]
            elif kind=="Staff Assignment":
                item={
                    "employee":_text(row.get("employee"),"Nhân viên"),
                    "farm":_text(row.get("farm"),"Vườn"),
                    "department":str(row.get("department") or "").strip(),
                    "designation":str(row.get("designation") or "").strip(),
                    "work_team":str(row.get("work_team") or "").strip(),
                    "role_title":str(row.get("role_title") or "").strip()[:140],
                    "valid_from":_date(row.get("valid_from"),"bắt đầu"),
                    "valid_to":str(row.get("valid_to") or "").strip(),
                    "approver":str(row.get("approver") or "").strip(),
                }
                _farm(company,item["farm"])
                person=_same_company_employee(company,item["employee"])
                if person.get("lotus_farm") and person.lotus_farm!=item["farm"]:
                    raise ValueError("Nhân viên chưa điều chuyển đến vườn này.")
                if item["valid_to"]:
                    item["valid_to"]=_date(item["valid_to"],"kết thúc")
                    if item["valid_to"]<item["valid_from"]:
                        raise ValueError("Ngày kết thúc trước ngày bắt đầu.")
                if item["department"] and frappe.db.get_value("Department",item["department"],"company")!=company:
                    raise ValueError("Bộ phận không thuộc công ty.")
                if item["designation"] and not frappe.db.exists("Designation",item["designation"]):
                    raise ValueError("Chưa tạo chức danh.")
                if item["work_team"]:
                    team=frappe.get_doc("Work Team",item["work_team"]);team.check_permission("read")
                    if team.farm!=item["farm"] or team.get("lotus_team_type")=="Contractor":
                        raise ValueError("Tổ/đội không thuộc vườn hoặc là nhà thầu.")
                if item["approver"]:
                    boss=_same_company_employee(company,item["approver"])
                    if boss.name==person.name:raise ValueError("Không tự làm cấp trên.")
                key="assignment:"+item["employee"]+":"+item["valid_from"]
            elif kind=="Shift Type":
                item={
                    "shift_name":_text(row.get("shift_name"),"Tên ca"),
                    "start_time":_text(row.get("start_time"),"Giờ bắt đầu",8),
                    "end_time":_text(row.get("end_time"),"Giờ kết thúc",8)
                }
                if not all(re.fullmatch(r"\d{2}:\d{2}(?::\d{2})?",v) for v in (item["start_time"],item["end_time"])):
                    raise ValueError("Giờ ca phải là HH:MM hoặc HH:MM:SS.")
                if item["start_time"]==item["end_time"]:
                    raise ValueError("Giờ bắt đầu và kết thúc không được bằng nhau.")
                key="shift:"+item["shift_name"].casefold()
            elif kind=="Shift Assignment":
                item={
                    "employee":_text(row.get("employee"),"Nhân viên"),
                    "shift_type":_text(row.get("shift_type"),"Ca làm"),
                    "start_date":_date(row.get("start_date"),"bắt đầu"),
                    "end_date":str(row.get("end_date") or "").strip(),
                }
                person=_same_company_employee(company,item["employee"])
                if not frappe.db.exists("Shift Type",item["shift_type"]):
                    raise ValueError("Ca làm chưa được tạo.")
                if item["end_date"]:
                    item["end_date"]=_date(item["end_date"],"kết thúc")
                    if item["end_date"]<item["start_date"]:
                        raise ValueError("Ngày kết thúc trước ngày bắt đầu.")
                key="shift-assignment:"+item["employee"]+":"+item["start_date"]
            elif kind=="Device Mapping":
                item={"device":_text(row.get("device"),"Máy"),
                      "device_user_id":_text(row.get("device_user_id"),"Mã trên máy",80),
                      "employee":_text(row.get("employee"),"Mã nhân viên"),
                      "valid_from":_date(row.get("valid_from"),"bắt đầu"),
                      "valid_to":str(row.get("valid_to") or "").strip(),"active":1}
                machine=_device(company,item["device"])
                if not machine.active: raise ValueError('Máy không còn hoạt động.')
                item["farm"]=machine.farm
                employee=_same_company_employee(company,item["employee"])
                if employee.status!="Active":raise ValueError("Nhân viên chưa kích hoạt.")
                if item["valid_to"] and item["valid_to"]<item["valid_from"]:
                    raise ValueError("Ngày hết hiệu lực trước ngày bắt đầu.")
                if employee.get('lotus_farm') and employee.lotus_farm!=machine.farm:
                    raise ValueError('Nhân viên không thuộc vườn đặt máy.')
                existing_maps=frappe.get_all('Lotus Attendance Identity',
                    filters={'device':item['device'],'device_user_id':item['device_user_id'],'active':1},
                    fields=['valid_from','valid_to'],limit_page_length=100)
                for x in existing_maps:
                    if (not item['valid_to'] or str(x.valid_from)<=item['valid_to']) and (not x.valid_to or str(x.valid_to)>=item['valid_from']):
                        raise ValueError('Mã trên máy đã gán trong giai đoạn này.')
                key=item["device"]+":"+item["device_user_id"]+":"+item["valid_from"]
            else:
                item=_checkin_normalize(row)
                machine=_device(company,item["device"])
                if machine.active!=1:raise ValueError("Máy đã tắt.")
                item["farm"]=machine.farm
                item["event_hash"]=_signature(item["device"],item)
                key=item["event_hash"]
            if key in seen:raise ValueError("Trùng dòng trong tệp.")
            seen.add(key)
            normalized.append({"row":i+1,"values":item,"status":"ready"})
        except (ValueError,frappe.ValidationError,frappe.PermissionError) as exc:
            errors.append({"row":i+1,"error":str(exc)})
    digest=hashlib.sha256(json.dumps({"company":company,"kind":kind,"rows":rows},
                   ensure_ascii=False,sort_keys=True,default=str).encode()).hexdigest()
    return dict(kind=kind,ready=len(normalized),errors=errors,normalized=normalized,
        review_hash=digest,preview_only=True)


@frappe.whitelist()
def import_preview(company,kind,rows):
    _hr()
    return _check_import(company,kind,_parse_rows(rows))


@frappe.whitelist(methods=["POST"])
def commit_import(company,kind,rows,review_hash):
    _manager()
    raw=_parse_rows(rows)
    review=_check_import(company,kind,raw)
    if review["errors"] or review["review_hash"]!=review_hash:
        frappe.throw("Dữ liệu đã đổi hoặc có lỗi. Xem trước lại; chưa ghi dòng nào.")
    doctype={"Device Mapping":"Lotus Attendance Identity","Checkin CSV":"Lotus Attendance Punch",
        "Staff Assignment":"Lotus Staff Assignment"}.get(kind,kind)
    if not frappe.has_permission(doctype,"create"):
        frappe.throw("Chưa có quyền tạo "+doctype,frappe.PermissionError)
    if kind == 'Employee' and not frappe.has_permission('Employee','create'):
        frappe.throw('Chưa có quyền thêm hồ sơ nhân viên.',frappe.PermissionError)
    counts=dict(created=0,skipped=0,unmapped=0)
    from lotus_farm.controls import lock
    lock("Company",company)
    for r in review["normalized"]:
        v=dict(r["values"])
        if kind=="Designation":
            if frappe.db.exists("Designation",{"designation_name":v["designation_name"]}):
                counts["skipped"]+=1;continue
        elif kind=="Department":
            if frappe.db.exists("Department",{"department_name":v["department_name"],"company":company}):
                counts["skipped"]+=1;continue
            v["company"]=company
        elif kind=="Work Team":
            if frappe.db.exists("Work Team",{"farm":v["farm"],"team_code":v["team_code"]}):
                counts["skipped"]+=1;continue
            v["active"]=1
        elif kind=="Employee":
            # HRMS Employee requires first_name. Never generate a User on import.
            v['first_name']=v.pop('employee_name')
            v['last_name']=''
            v['create_user_automatically']=0
            v['create_user_permission']=0
            v["company"]=company;v["status"]="Inactive";v["lotus_onboarding_state"]="Pending"
        elif kind=="Staff Assignment":
            v["company"]=company
            if frappe.db.exists("Lotus Staff Assignment",{"employee":v["employee"],
                    "valid_from":v["valid_from"],"farm":v["farm"]}):
                counts["skipped"]+=1;continue
        elif kind=="Shift Type":
            if frappe.db.exists("Shift Type",v["shift_name"]):
                counts["skipped"]+=1;continue
            frappe.get_doc({"doctype":"Shift Type","start_time":v["start_time"],
                "end_time":v["end_time"],"enable_auto_attendance":0}).insert(
                set_name=v["shift_name"])
            counts["created"]+=1
            continue
        elif kind=="Shift Assignment":
            v["company"]=company
            if frappe.db.exists("Shift Assignment",{"employee":v["employee"],
                    "shift_type":v["shift_type"],"start_date":v["start_date"],"docstatus":["<",2]}):
                counts["skipped"]+=1;continue
            # Keep HRMS Shift Assignment in draft: submitting is a separate approval.
        elif kind=="Device Mapping":
            if frappe.db.exists("Lotus Attendance Identity",{"device":v["device"],
                    "device_user_id":v["device_user_id"],"valid_from":v["valid_from"]}):
                counts["skipped"]+=1;continue
            v["company"]=company
        else:
            if frappe.db.exists("Lotus Attendance Punch",{"event_hash":v["event_hash"]}):
                counts["skipped"]+=1;continue
            v["company"]=company
            v["employee"]=_mapping(company,v["device"],v["device_user_id"],v["punched_at"])
            v["state"]="Ready" if v["employee"] else "Unmapped"
            v["source"]="CSV";v["received_at"]=now_datetime()
            if not v["employee"]:counts["unmapped"]+=1
        doc=frappe.get_doc(dict(doctype=doctype,**v))
        doc.insert()
        counts["created"]+=1
    return dict(**counts,message="Đã nhập bản ghi; chấm công máy chưa được tính thành công hay lương.")


@frappe.whitelist(methods=["POST"])
def ingest_device_events(company,device,events):
    """Secure integration-user endpoint for a farm-side CSV/LAN/cloud bridge.

    Requires a real authenticated Frappe API User with Lotus Integration User
    (or HR Manager) and User Permissions for the farm and device. The bridge
    sends structured punches only, never facial/fingerprint templates.
    """
    roles = frappe.get_roles()
    if frappe.session.user == 'Guest' or not (
        frappe.session.user == 'Administrator'
        or 'HR Manager' in roles
        or 'Lotus Integration User' in roles
    ):
        frappe.throw('Không có quyền nhận dữ liệu máy.', frappe.PermissionError)
    _company(company)
    machine = _device(company,device)
    if not machine.active:
        frappe.throw('Máy chấm công đã tắt.')
    if not frappe.has_permission('Lotus Attendance Punch','create'):
        frappe.throw('Tài khoản không có quyền nhận log.',frappe.PermissionError)
    batch = _parse_rows(events,maximum=500)
    from lotus_farm.controls import lock
    lock('Company',company)
    result = {'created':0,'duplicate':0}
    for line in batch:
        item = _checkin_normalize(dict(line,device=device))
        digest = _signature(device,item)
        if frappe.db.exists('Lotus Attendance Punch',{'event_hash':digest}):
            result['duplicate']+=1
            continue
        doc=frappe.get_doc(dict(doctype='Lotus Attendance Punch',
            company=company,farm=machine.farm,device=device,
            **{k:v for k,v in item.items() if k!='device'},
            event_hash=digest,state='Unmapped',source=(
                'CSV' if machine.connection_mode=='File CSV'
                else machine.connection_mode),
            received_at=now_datetime()))
        doc.insert()
        result['created']+=1
    return {**result,'warning':'Log chỉ được lưu làm bằng chứng; chưa tự duyệt công hay tính lương.'}


@frappe.whitelist(methods=["POST"])
def save_device(company,values,name=None,modified=None):
    _manager();_company(company)
    data=frappe.parse_json(values) if isinstance(values,str) else values
    if not isinstance(data,dict):frappe.throw("Thiếu thông tin máy.")
    safe=["farm","device_code","device_name","model","serial_number","connection_mode","timezone","active","notes"]
    fields={x:data[x] for x in safe if x in data}
    _farm(company,fields.get("farm") or (frappe.db.get_value("Lotus Attendance Device",name,"farm") if name else ""))
    if name:
        doc=_device(company,name);doc.check_permission("write")
        if str(doc.modified)!=str(modified):frappe.throw("Máy đã thay đổi, tải lại.")
        doc.update(fields);doc.save()
    else:
        defaults=dict(active=1,connection_mode="File CSV",timezone="Asia/Ho_Chi_Minh")
        defaults.update(fields)
        doc=frappe.get_doc(dict(doctype="Lotus Attendance Device",company=company,**defaults))
        doc.insert()
    return dict(name=doc.name)


@frappe.whitelist(methods=["POST"])
def sync_checkins(company,names):
    """Explicitly approved promotion from raw immutable punches to HRMS Employee Checkin.

    Never marks Attendance, payroll or salaries; Frappe Shift Type settings decide
    whether HRMS auto attendance subsequently runs.
    """
    _manager();_company(company)
    names=frappe.parse_json(names) if isinstance(names,str) else names
    if not isinstance(names,list) or not 1<=len(names)<=100:
        frappe.throw("Chọn 1 đến 100 log đã đối chiếu.")
    if not frappe.has_permission("Employee Checkin","create"):
        frappe.throw("Không có quyền ghi Employee Checkin.",frappe.PermissionError)
    from lotus_farm.controls import lock
    lock("Company",company)
    result={"synced":0,"skipped":0,"needs_review":0}
    for name in set(names):
        row=frappe.get_doc("Lotus Attendance Punch",name);row.check_permission("write")
        if row.company!=company:frappe.throw("Có log ngoài công ty.")
        if row.state=="Synced":result["skipped"]+=1;continue
        emp=_mapping(company,row.device,row.device_user_id,str(row.punched_at))
        if not emp:
            row.employee=None;row.state="Unmapped";row.flags.lotus_promotion=True;row.save()
            result["needs_review"]+=1;continue
        person=_same_company_employee(company,emp)
        if person.status!="Active":
            row.state="Needs Review";row.flags.lotus_promotion=True;row.save()
            result["needs_review"]+=1;continue
        existing=frappe.db.exists("Employee Checkin",{
            "employee":emp,"time":row.punched_at,"log_type":row.log_type or ["is","not set"]})
        if existing:
            row.employee=emp;row.employee_checkin=existing;row.state="Synced";row.flags.lotus_promotion=True;row.save()
            result["skipped"]+=1;continue
        checkin=frappe.get_doc({"doctype":"Employee Checkin","employee":emp,
            "time":row.punched_at,"log_type":row.log_type or "",
            "device_id":row.device})
        checkin.insert()
        row.employee=emp;row.employee_checkin=checkin.name;row.state="Synced";row.flags.lotus_promotion=True;row.save()
        result["synced"]+=1
    return result
