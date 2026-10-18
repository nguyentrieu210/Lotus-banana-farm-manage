"""Explicit HR org setup. Creates only organizational master data on approval."""
import frappe
from lotus_farm.hr_operations import _manager, _company, _farm, IMAGE_STRUCTURE, IMAGE_POSITIONS

AREAS=("A","B","C","D")

def install_fields():
 from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
 create_custom_fields({"Work Team":[
  {"fieldname":"lotus_parent_team","label":"Đội cấp trên","fieldtype":"Link","options":"Work Team","insert_after":"team_name"},
  {"fieldname":"lotus_zone","label":"Khu","fieldtype":"Data","insert_after":"lotus_parent_team"},
  {"fieldname":"lotus_planned_area_ha","label":"Diện tích phụ trách dự kiến (ha)","fieldtype":"Float","insert_after":"lotus_zone"},
 ]},update=True,ignore_validate=True)

@frappe.whitelist(methods=["POST"])
def seed_organization(company,farm):
 """Explicit manager-confirmed, idempotent masters; no employee, wage or permission assignment."""
 _manager();_company(company);_farm(company,farm)
 if not frappe.has_permission("Department","create") or not frappe.has_permission("Work Team","create"):
  frappe.throw("Chưa có quyền tạo bộ phận/đội.",frappe.PermissionError)
 from lotus_farm.controls import lock
 lock("Company",company)
 departments={};results={"departments":0,"teams":0,"skipped":0}
 for code,label,parent in IMAGE_STRUCTURE:
  # The executive parent is a Department group, teams are operational Work Teams.
  if code.startswith("TEAM_"):continue
  rows=frappe.get_all("Department",filters={"company":company,"department_name":label},
                      pluck="name",limit_page_length=10)
  if rows:departments[code]=rows[0];results["skipped"]+=1;continue
  dep=frappe.get_doc({"doctype":"Department","company":company,
    "department_name":label,"is_group":1 if code=="BOARD" else 0,
    "parent_department":departments.get(parent)})
  dep.insert()
  departments[code]=dep.name;results["departments"]+=1
 for zone in AREAS:
  parent_code="TEAM-"+zone
  seed=[(parent_code,"Đội chăm sóc khu "+zone,None,55)]
  seed.extend([("TEAM-"+zone+str(i),"Tổ chăm sóc "+zone+str(i),parent_code,25) for i in (1,2)])
  names={}
  for key,label,parent,area in seed:
   current=frappe.get_all("Work Team",filters={"farm":farm,"team_code":key},
                          pluck="name",limit_page_length=2)
   if current:names[key]=current[0];results["skipped"]+=1;continue
   obj=frappe.get_doc({"doctype":"Work Team","farm":farm,"team_code":key,
    "team_name":label,"active":1,"lotus_team_type":"Internal",
    "lotus_parent_team":names.get(parent),"lotus_zone":zone,
    "lotus_planned_area_ha":area})
   obj.insert();names[key]=obj.name;results["teams"]+=1
 return {**results,"warning":"Mỗi đội mẫu 55 ha nhưng 2 tổ chỉ phụ trách 50 ha; cần xác nhận 5 ha còn lại. Không tạo nhân viên/lương."}


@frappe.whitelist(methods=["POST"])
def save_assignment(company,values):
 _manager();_company(company)
 values=frappe.parse_json(values) if isinstance(values,str) else values
 if not isinstance(values,dict):frappe.throw("Thiếu thông tin phân công.")
 allowed=["employee","farm","department","designation","work_team",
          "role_title","valid_from","valid_to","approver","notes"]
 data={f:values[f] for f in allowed if f in values}
 data["company"]=company
 if not frappe.has_permission("Lotus Staff Assignment","create"):
  frappe.throw("Chưa có quyền phân công.",frappe.PermissionError)
 doc=frappe.get_doc(dict(doctype="Lotus Staff Assignment",**data))
 doc.insert()
 return dict(name=doc.name)
