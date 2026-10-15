import os
import frappe
os.chdir('/home/frappe/frappe-bench/sites')
frappe.init(site='frontend');frappe.connect();frappe.set_user('Administrator')
from lotus_farm import hr_workspace as hr
try:
    c=frappe.db.get_value('Company',{},'name')
    d=frappe.db.get_value('Designation',{},'name')
    g=frappe.db.get_value('Gender',{},'name')
    assert c and d and g
    candidate=hr.save_candidate(c,{'applicant_name':'Lotus UAT Worker','phone':'0912345678','designation':d,'applied_on':'2026-10-15'})
    key=candidate['name']
    for state in ('Screening','Interview','Offered'):
        current=frappe.get_doc('Lotus Candidate',key)
        hr.save_candidate(c,{'status':state},name=key,modified=str(current.modified))
    current=frappe.get_doc('Lotus Candidate',key)
    result=hr.hire_candidate(c,key,{'date_of_birth':'1999-01-02','date_of_joining':'2026-10-15','gender':g,'lotus_worker_category':'Seasonal','lotus_payment_basis':'Daywork','cccd':'000000000001','lotus_id_issue_on':'2022-10-01','lotus_id_issue_at':'UAT authority','current_address':'UAT address','lotus_emergency_name':'UAT contact','lotus_emergency_phone':'0987654321'},str(current.modified))
    e=frappe.get_doc('Employee',result['name'])
    assert e.status=='Inactive' and e.lotus_onboarding_state=='Pending'
    assert frappe.get_doc('Lotus Candidate',key).status=='Hired'
    assert e.lotus_cccd_hash and e.lotus_cccd_last4=='0001'
    assert 'lotus_cccd' not in hr.employee_detail(c,e.name)
    frappe.set_user('Guest')
    denied=False
    try:
        hr.employee_detail(c,e.name)
    except (frappe.PermissionError, frappe.AuthenticationError):
        denied=True
    finally:
        frappe.set_user('Administrator')
    assert denied, 'Guest must never access identity detail'
    hr.set_onboarding_ready(c,e.name,str(e.modified))
    e=frappe.get_doc('Employee',e.name)
    assert e.status=='Active'
    hr.save_employee(c,{'lotus_emergency_name':'UAT updated contact'},employee=e.name,modified=str(e.modified))
    assert frappe.get_doc('Employee',e.name).lotus_cccd_hash
    rejected_duplicate=False
    try:
        hr.save_employee(c,{'employee_name':'Lotus UAT Duplicate','date_of_birth':'1998-02-03','date_of_joining':'2026-10-15','gender':g,'lotus_worker_category':'Seasonal','lotus_payment_basis':'Daywork','cccd':'000000000001'})
    except frappe.ValidationError as exc:
        rejected_duplicate='CCCD' in str(exc)
    assert rejected_duplicate, 'Duplicate identity must be rejected'
    print('PASS candidate stages / encrypted ID / onboarding activation / duplicate rejection')
finally:
    frappe.db.rollback();frappe.destroy()
