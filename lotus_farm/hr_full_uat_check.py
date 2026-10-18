"""Rollback-only HR + clock integration UAT.

Usage after DocType reload:
bench --site frontend execute lotus_farm.hr_full_uat_check.run
All test records are rolled back unconditionally, even on failure.
"""
import base64
import csv
import io
import frappe
from datetime import datetime
from lotus_farm import hr_operations as hr
from lotus_farm import hr_import_file as uploader

def run():
    frappe.set_user("Administrator")
    try:
        company=frappe.db.get_value("Company",{},"name")
        farm=frappe.db.get_value("Farm",{"company":company,"active":1},"name")
        gender=frappe.db.get_value("Gender",{},"name")
        designation=frappe.db.get_value("Designation",{},"name")
        department=frappe.db.get_value("Department",{"company":company,"is_group":0},"name")
        assert all((company,farm,gender,designation,department)), "Thiếu các danh mục HRMS cần thiết"
        for doctype in ("Lotus Attendance Device","Lotus Attendance Identity",
                        "Lotus Attendance Punch","Lotus Staff Assignment"):
            assert frappe.db.table_exists(doctype), doctype+" table missing"
        assert frappe.get_meta("Work Team").has_field("lotus_parent_team")
        assert frappe.get_meta("Work Team").has_field("lotus_planned_area_ha")
        print("HR_SCHEMA_OK")
        org=hr.organization(company)
        assert org["farms"] and org["template_departments"]
        assert len(org["template_positions"])>=15
        print("ORGANIZATION_OK")
        from lotus_farm.hr_setup import seed_organization
        first_seed=seed_organization(company,farm)
        second_seed=seed_organization(company,farm)
        assert first_seed["departments"]>=0 and first_seed["teams"]>=0
        assert second_seed["departments"]==0 and second_seed["teams"]==0
        print("ORG_TEMPLATE_SEED_IDEMPOTENT_OK")

        employee=frappe.get_doc({
            "doctype":"Employee","first_name":"LOTUS HR DEVICE TEST",
            "company":company,"gender":gender,"designation":designation,
            "department":department,"status":"Active",
            "date_of_birth":"1999-01-08","date_of_joining":"2026-01-01",
            "lotus_farm":farm,"lotus_payment_basis":"Daywork",
            "lotus_worker_category":"Seasonal","lotus_onboarding_state":"Pending",
            "create_user_automatically":0,"create_user_permission":0,
        }).insert()
        code="HR-DEVICE-UAT-"+datetime.now().strftime("%H%M%S%f")
        machine=hr.save_device(company,{"farm":farm,"device_code":code,
          "device_name":"UAT – only rollback","active":1,
          "connection_mode":"File CSV","timezone":"Asia/Ho_Chi_Minh"})
        device=machine["name"]
        identity=frappe.get_doc({
            "doctype":"Lotus Attendance Identity","company":company,
            "farm":farm,"device":device,"device_user_id":"000007",
            "employee":employee.name,"active":1,"valid_from":"2026-01-01"
        }).insert()
        assert identity.name
        print("DEVICE_AND_MAPPING_OK")

        rows=[{"device_user_id":"000007","punched_at":"2026-10-17 07:00:00",
               "log_type":"IN","source_event_id":"UAT-001"},
              {"device_user_id":"000008","punched_at":"2026-10-17 08:00:00",
               "log_type":"IN","source_event_id":"UAT-002"}]
        first=hr.ingest_device_events(company,device,rows)
        assert first["created"]==2, first
        repeated=hr.ingest_device_events(company,device,rows)
        assert repeated["created"]==0 and repeated["duplicate"]==2, repeated
        punches=frappe.get_all("Lotus Attendance Punch",filters={"device":device},
             fields=["name","device_user_id","state","event_hash"])
        assert len(punches)==2
        synced=hr.sync_checkins(company,[row.name for row in punches])
        assert synced["synced"]==1 and synced["needs_review"]==1,synced
        assert frappe.db.exists("Employee Checkin",{"employee":employee.name,
              "time":"2026-10-17 07:00:00"})
        assert not frappe.db.exists("Attendance",{"employee":employee.name,
              "attendance_date":"2026-10-17"})
        print("DUPLICATE_RAW_AND_CHECKIN_OK")

        duplicate_rejected=False
        try:
            frappe.get_doc({"doctype":"Lotus Attendance Identity","company":company,
                "farm":farm,"device":device,"device_user_id":"000007",
                "employee":employee.name,"valid_from":"2026-05-01","active":1}).insert()
        except (frappe.ValidationError,frappe.PermissionError):
            duplicate_rejected=True
        assert duplicate_rejected,"Overlapping identity not rejected"
        print("MAPPING_OVERLAP_DENIED_OK")

        assignment=frappe.get_doc({"doctype":"Lotus Staff Assignment",
             "company":company,"farm":farm,"employee":employee.name,
             "department":department,"designation":designation,"valid_from":"2026-01-01",
             "role_title":"Nhân sự UAT"}).insert()
        assert assignment.name
        print("ASSIGNMENT_HISTORY_OK")
        good_csv=("device,device_user_id,punched_at,log_type,source_event_id\n"
            +device+",000007,2026-10-17 07:00:00,IN,UAT-001\n").encode("utf-8")
        preview=uploader.parse_upload(company,"Checkin CSV","test.csv",base64.b64encode(good_csv).decode())
        assert preview["preview"]["ready"]==1
        assert preview["rows"][0]["device_user_id"]=="000007"
        assert preview["preview"]["errors"]==[]
        print("CSV_LEADING_ZERO_PREVIEW_OK")
        import openpyxl
        wb=openpyxl.Workbook()
        ws=wb.active
        ws.append(["device","device_user_id","punched_at","log_type","source_event_id"])
        ws.append([device,"000007","2026-10-17 07:00:00","IN","UAT-001"])
        buffer=io.BytesIO();wb.save(buffer)
        xlsx=uploader.parse_upload(company,"Checkin CSV","test.xlsx",base64.b64encode(buffer.getvalue()).decode())
        assert xlsx["rows"][0]["device_user_id"]=="000007"
        print("XLSX_TEXT_CODE_OK")

        employee_rows=[{"employee_name":"LOTUS HR IMPORT TEST PERSON",
            "gender":gender,"date_of_birth":"1995-05-06",
            "date_of_joining":"2026-01-01","designation":designation,
            "department":department,"lotus_farm":farm}]
        preview=hr.import_preview(company,"Employee",employee_rows)
        assert preview["ready"]==1 and not preview["errors"],preview
        imported=hr.commit_import(company,"Employee",employee_rows,preview["review_hash"])
        assert imported["created"]==1,imported
        imported_doc=frappe.get_last_doc("Employee")
        assert imported_doc.status=="Inactive" and not imported_doc.user_id
        print("EMPLOYEE_IMPORT_INACTIVE_NO_USER_OK")
        assignment_rows=[{"employee":imported_doc.name,"farm":farm,
            "department":department,"designation":designation,
            "role_title":"Nhân viên thử nghiệm","valid_from":"2026-01-01"}]
        checked=hr.import_preview(company,"Staff Assignment",assignment_rows)
        assert checked["ready"]==1 and not checked["errors"],checked
        posted=hr.commit_import(company,"Staff Assignment",assignment_rows,checked["review_hash"])
        assert posted["created"]==1,posted
        print("STAFF_ASSIGNMENT_IMPORT_OK")
        shift_name="HR-UAT-CA-"+datetime.now().strftime("%H%M%S%f")
        shift_rows=[{"shift_name":shift_name,"start_time":"07:00","end_time":"16:00"}]
        checked=hr.import_preview(company,"Shift Type",shift_rows)
        assert checked["ready"]==1 and not checked["errors"],checked
        posted=hr.commit_import(company,"Shift Type",shift_rows,checked["review_hash"])
        assert posted["created"]==1 and frappe.db.exists("Shift Type",shift_name)
        shift_assignment=[{"employee":employee.name,"shift_type":shift_name,
            "start_date":"2026-10-17","end_date":"2026-10-18"}]
        checked=hr.import_preview(company,"Shift Assignment",shift_assignment)
        assert checked["ready"]==1 and not checked["errors"],checked
        posted=hr.commit_import(company,"Shift Assignment",shift_assignment,checked["review_hash"])
        assert posted["created"]==1,posted
        drafted=frappe.get_doc("Shift Assignment",
            frappe.db.get_value("Shift Assignment",{"employee":employee.name,
               "shift_type":shift_name},"name"))
        assert drafted.docstatus==0,"Never auto-submit shift assignments."
        print("SHIFTS_DRAFT_ONLY_IMPORT_OK")

        frappe.set_user("Guest")
        denied=False
        try:hr.organization(company)
        except (frappe.PermissionError,frappe.AuthenticationError):denied=True
        assert denied, "Guest viewed organization"
        denied=False
        try:hr.ingest_device_events(company,device,rows)
        except (frappe.PermissionError,frappe.AuthenticationError):denied=True
        assert denied, "Guest sent device punches"
        print("GUEST_DENIED_OK")
    finally:
        frappe.set_user("Administrator")
        frappe.db.rollback()
        print("UAT_ROLLBACK_COMPLETE")
