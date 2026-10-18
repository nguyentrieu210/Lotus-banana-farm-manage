"""Validate HR Excel/CSV uploads as a preview; never save uploaded files."""
import base64
import csv
import io
from datetime import date, datetime

import frappe
from lotus_farm.hr_operations import _manager, _company, _check_import, IMPORT_KINDS

COLUMNS = {
 "Designation":["designation_name"],
 "Department":["department_name","parent_department"],
 "Work Team":["farm","team_code","team_name"],
 "Staff Assignment":["employee","farm","department","designation","work_team","role_title","valid_from","valid_to","approver"],
 "Shift Type":["shift_name","start_time","end_time"],
 "Shift Assignment":["employee","shift_type","start_date","end_date"],
 "Employee":["employee_name","gender","date_of_birth","date_of_joining","designation","department","lotus_farm","lotus_work_team","attendance_device_id"],
 "Device Mapping":["device","device_user_id","employee","valid_from","valid_to"],
 "Checkin CSV":["device","device_user_id","punched_at","log_type","source_event_id"],
}

def _txt(value):
 if value is None:return ""
 if isinstance(value,datetime):return value.strftime("%Y-%m-%d %H:%M:%S")
 if isinstance(value,date):return str(value)
 if isinstance(value,float) and value.is_integer():return str(int(value))
 return str(value).strip()

@frappe.whitelist()
def import_columns():
 from lotus_farm.hr_operations import _hr
 _hr()
 return COLUMNS

@frappe.whitelist(methods=["POST"])
def parse_upload(company,kind,filename,content_b64):
 _manager()
 _company(company)
 if kind not in IMPORT_KINDS:frappe.throw("Loại danh mục không hỗ trợ.")
 ext=str(filename or "").lower().rsplit(".",1)[-1]
 if ext not in ("csv","xlsx"):frappe.throw("Chỉ nhận CSV UTF-8 hoặc Excel .xlsx.")
 if len(content_b64)>3400000:frappe.throw("Tệp vượt giới hạn 2.5 MB.")
 try:raw=base64.b64decode(content_b64,validate=True)
 except Exception:frappe.throw("Không đọc được tệp.")
 if len(raw)>2500000:frappe.throw("Tệp vượt giới hạn.")
 if ext=="csv":
  try:rows=list(csv.reader(io.StringIO(raw.decode("utf-8-sig"))))
  except Exception:frappe.throw("CSV phải là UTF-8.")
 else:
  import openpyxl
  try:
   wb=openpyxl.load_workbook(io.BytesIO(raw),read_only=True,data_only=True)
   rows=[[_txt(v) for v in row] for idx,row in enumerate(wb.active.iter_rows(values_only=True)) if idx<=501]
   wb.close()
  except Exception:frappe.throw("Tệp Excel lỗi hoặc không đúng định dạng.")
 if len(rows)>501:frappe.throw("Chia tệp tối đa 500 dòng.")
 if not rows:frappe.throw("Tệp trống.")
 if len(rows)>501:frappe.throw('Mỗi tệp tối đa 500 dòng dữ liệu.')
 headers=[_txt(v).lstrip("\ufeff") for v in rows[0]]
 if not headers or any(not c for c in headers) or len(headers)!=len(set(headers)):
  frappe.throw("Tên cột trống hoặc trùng nhau.")
 data=[{key:_txt(v) for key,v in zip(headers,line)} for line in rows[1:] if any(_txt(v) for v in line)]
 if not data:frappe.throw("Tệp không có dòng dữ liệu.")
 preview=_check_import(company,kind,data)
 return {"rows":data,"preview":preview,"columns":COLUMNS[kind],
         "warning":"Các mã có số 0 đầu phải để dạng Text trong Excel."}
