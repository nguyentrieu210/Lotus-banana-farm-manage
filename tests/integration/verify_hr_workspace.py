"""Rollback-only integration check: python tests/integration/verify_hr_workspace.py

Run inside the ERPNext container with site "frontend". No real employees are created.
"""
import os
import frappe

os.chdir("/home/frappe/frappe-bench/sites")
frappe.init(site="frontend")
frappe.connect()
frappe.set_user("Administrator")
from lotus_farm import hr_workspace as hr

try:
    company = frappe.db.get_value("Company", {}, "name")
    designation = frappe.db.get_value("Designation", {}, "name")
    gender = frappe.db.get_value("Gender", {}, "name")
    assert company and designation and gender, "Company, Designation and Gender required"

    candidate = hr.save_candidate(company, {
        "applicant_name": "Lotus UAT Worker",
        "phone": "0912345678", "designation": designation,
        "applied_on": "2026-10-15",
    })
    key = candidate["name"]
    for state in ("Screening", "Interview", "Offered"):
        current = frappe.get_doc("Lotus Candidate", key)
        hr.save_candidate(company, {"status": state}, name=key, modified=str(current.modified))

    current = frappe.get_doc("Lotus Candidate", key)
    result = hr.hire_candidate(company, key, {
        "gender": gender,
        "date_of_birth": "1999-01-02",
        "date_of_joining": "2026-10-15",
        "lotus_worker_category": "Seasonal",
        "lotus_payment_basis": "Daywork",
        "cccd": "000000000001",
        "lotus_id_issue_on": "2022-10-01",
        "lotus_id_issue_at": "UAT authority",
        "current_address": "UAT address",
        "lotus_emergency_name": "UAT contact",
        "lotus_emergency_phone": "0987654321",
    }, str(current.modified))
    employee = frappe.get_doc("Employee", result["name"])
    assert employee.status == "Inactive" and employee.lotus_onboarding_state == "Pending"
    assert employee.lotus_cccd_hash and employee.lotus_cccd_last4 == "0001"
    assert "lotus_cccd" not in hr.employee_detail(company, employee.name)

    frappe.set_user("Guest")
    denied = False
    try:
        hr.employee_detail(company, employee.name)
    except (frappe.PermissionError, frappe.AuthenticationError):
        denied = True
    finally:
        frappe.set_user("Administrator")
    assert denied, "Guest can read employee identity"

    hr.set_onboarding_ready(company, employee.name, str(employee.modified))
    employee.reload()
    assert employee.status == "Active" and employee.lotus_onboarding_state == "Ready"
    hr.save_employee(company, {"lotus_emergency_name": "UAT revised contact"},
                     employee=employee.name, modified=str(employee.modified))
    assert frappe.get_doc("Employee", employee.name).lotus_cccd_hash

    rejected_duplicate = False
    try:
        hr.save_employee(company, {
            "employee_name": "Lotus UAT Duplicate",
            "date_of_birth": "1998-02-03", "date_of_joining": "2026-10-15",
            "gender": gender, "lotus_worker_category": "Seasonal",
            "lotus_payment_basis": "Daywork", "cccd": "000000000001",
        })
    except frappe.ValidationError as exc:
        rejected_duplicate = "CCCD" in str(exc)
    assert rejected_duplicate, "Duplicate identification not rejected"

    print("PASS: candidate / onboarding / encrypted ID / access control / duplicate ID")
finally:
    frappe.db.rollback()
    frappe.destroy()
