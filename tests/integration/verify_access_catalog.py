"""Real-site access catalog and signer validation. All temporary records roll back; no messages sent."""
import json
import uuid
import frappe

frappe.init(site='frontend', sites_path='/home/frappe/frappe-bench/sites')
frappe.connect()
frappe.set_user('Administrator')
frappe.in_test = True
frappe.flags.in_test = True
from lotus_farm import user_admin, signing, signing_rules
from lotus_farm.localization import ROLE_LABELS, install_translations
from tools.verify_user_admin import run as verify_user_admin

checks = []
def rejected(name, fn):
    try:
        fn()
    except (frappe.PermissionError, frappe.ValidationError):
        checks.append(name)
    else:
        raise AssertionError(name)

try:
    report = verify_user_admin()
    checks.extend(report['checks'])
    install_translations()
    assert frappe._('Lotus Purchase Approver', lang='vi') == ROLE_LABELS['Lotus Purchase Approver']
    assert frappe._('Accounts - LT', lang='vi') == 'Kế toán - LT'
    assert frappe.get_meta('Department').translated_doctype
    assert frappe.get_meta('Designation').get_field('designation_name').translatable
    checks.append('native_erpnext_translations_without_renaming')
    choices = user_admin.role_choices()
    assert {r['name'] for r in choices} == set(frappe.get_all('Role', pluck='name'))
    assert all(r['label'] != r['name'] for r in choices if r['name'] in ROLE_LABELS)
    assert not next(r for r in choices if r['name'] == 'All')['assignable']
    assert next(r for r in choices if r['name'] == 'Lotus Purchase Approver')['assignable']
    checks.append('all_roles_including_previously_hidden_approvers')
    rejected('automatic_role_cannot_be_assigned', lambda: user_admin.save({'roles': ['Administrator']}))
    rejected('malformed_roles_rejected', lambda: user_admin.save({'roles': 'Stock User'}))
    tag = uuid.uuid4().hex[:7]
    company = 'Lotus Agritech'
    def person(key, roles):
        email = 'audit-' + key + '-' + tag + '@example.invalid'
        frappe.get_doc(dict(doctype='User', email=email, first_name='Audit ' + key, enabled=1,
                            send_welcome_email=0, roles=[dict(role=r) for r in roles])).insert(ignore_permissions=True)
        employee = frappe.get_doc(dict(doctype='Employee', first_name='Audit ' + key, gender='Male',
                                       date_of_birth='1990-01-01', date_of_joining='2024-01-01',
                                       company=company, status='Active', user_id=email)).insert(ignore_permissions=True)
        return email, employee
    approver, manager = person('manager', ['Lotus Purchase Approver', 'Lotus Farm Manager'])
    requester, employee = person('requester', ['Lotus Purchase Requester'])
    employee.reports_to = manager.name
    employee.save(ignore_permissions=True)
    frappe.set_user(requester)
    options = signing.candidates('purchase_proposal', company)
    assert options['suggested']['DEPARTMENT'] == approver
    assert any(r['user'] == approver for r in options['candidates']['APPROVE'])
    assert not any(r['user'] == requester for r in options['candidates']['APPROVE'])
    assert options['diagnostics']['PURCHASING']['required_roles']
    checks.append('eligible_manager_suggested_and_wrong_role_excluded')
    step = signing_rules.CHAINS['purchase_order']['steps'][1]
    signing._validate_person(approver, step, company)
    rejected('cross_company_signer_rejected', lambda: signing._validate_person(approver, step, 'Different Company'))
    frappe.set_user('Administrator')
    frappe.db.set_value('User', approver, 'enabled', 0)
    rejected('disabled_signer_rejected_at_submission', lambda: signing._validate_person(approver, step, company))
    assert not any(r['user'] == approver for r in signing.candidates('purchase_order', company)['candidates']['APPROVE'])
    checks.append('disabled_account_removed_from_candidates')
    audit = user_admin.permission_audit(requester)
    assert not any(r['read'] for r in audit['farms'])
    assert not any(r['ready'] for r in audit['signing'] if r['step'] == 'APPROVE')
    checks.append('effective_farm_and_signing_audit')
    rejected('employee_login_cannot_be_taken_over', lambda: user_admin.link_employee(approver, employee.name))
    user_admin.link_employee(requester, '')
    assert not frappe.db.get_value('Employee', employee.name, 'user_id')
    user_admin.link_employee(requester, employee.name)
    assert frappe.db.get_value('Employee', employee.name, 'user_id') == requester
    checks.append('employee_login_link_and_unlink')
    # Roles created after release are discovered without editing a hard-coded allow list.
    role_name = 'Audit Dynamic ' + tag
    frappe.get_doc(dict(doctype='Role', role_name=role_name, desk_access=1)).insert()
    assert role_name in {r['name'] for r in user_admin.role_choices()}
    checks.append('new_role_is_discovered_dynamically')
    user = frappe.get_doc('User', requester)
    user.append('roles', {'role': role_name})
    user.save()
    frappe.db.set_value('Role', role_name, 'disabled', 1)
    detail = user_admin.detail(requester)
    assignable = {r['name'] for r in user_admin.role_choices() if r['assignable']}
    detail['roles'] = [r for r in detail['roles'] if r in assignable]
    updated = user_admin.save(detail, requester)
    assert role_name not in updated['roles'] and role_name in updated['removed_disabled_roles']
    checks.append('native_disabled_role_cleanup_is_reported')
    print(json.dumps(dict(checks=checks, role_count=len(choices), rolled_back=True), ensure_ascii=False))
finally:
    frappe.set_user('Administrator')
    frappe.db.rollback()
    frappe.clear_cache()
    frappe.destroy()
