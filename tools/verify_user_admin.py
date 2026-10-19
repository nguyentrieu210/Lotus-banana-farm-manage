"""Run inside an initialized Frappe site; all test data is rolled back."""
import copy
import uuid
import frappe
from lotus_farm import user_admin as api


def run():
    original_user = frappe.session.user
    email = 'ui-audit-' + uuid.uuid4().hex + '@example.invalid'
    checks = []
    def rejected(label, fn, exception):
        try: fn()
        except exception: checks.append(label)
        else: raise AssertionError(label)
    try:
        frappe.set_user('Guest')
        for name, args in [('bootstrap', {}), ('users', {}), ('detail', {'user': 'Administrator'}), ('save', {'values': {}})]:
            rejected('guest_' + name, lambda: getattr(api, name)(**args), frappe.PermissionError)
        frappe.set_user('Administrator')
        rejected('protected_administrator', lambda: api.save({}, 'Administrator'), frappe.PermissionError)
        rejected('unknown_role', lambda: api.save({'roles': ['unknown-role']}), frappe.ValidationError)
        rejected('unknown_farm', lambda: api.save({'farms': ['unknown-farm']}), frappe.ValidationError)
        farms = frappe.get_all('Farm', pluck='name', limit_page_length=1)
        team_rows = frappe.get_all('Work Team', filters={'farm': ['in', farms]}, fields=['name', 'farm'], limit_page_length=1) if farms else []
        if team_rows:
            rejected('team_requires_farm', lambda: api.save({'teams': [team_rows[0].name]}), frappe.ValidationError)
        created = api.save({'email': email, 'first_name': 'UI Audit', 'enabled': 0, 'roles': ['Lotus Auditor'], 'farms': farms, 'teams': [t.name for t in team_rows]})
        assert created['name'] == email and not created['enabled']
        assert 'Lotus Auditor' in created['roles'] and set(created['farms']) == set(farms)
        checks.append('create_disabled_profile_with_roles_and_scope')
        assert not frappe.get_doc('User', email).send_welcome_email
        checks.append('no_welcome_email')
        stale = copy.deepcopy(created)
        created['first_name'] = 'Updated UI Audit'
        updated = api.save(created, email)
        assert updated['first_name'] == 'Updated UI Audit'
        checks.append('edit_profile')
        rejected('stale_profile', lambda: api.save(stale, email), frappe.TimestampMismatchError)
        if farms:
            # Preserve advanced, document-specific grants while managing ordinary scope.
            advanced = frappe.get_doc(dict(doctype='User Permission', user=email, allow='Farm', for_value=farms[0], apply_to_all_doctypes=0, applicable_for='Daily Work Plan')).insert()
            rejected('stale_scope', lambda: api.save(updated, email), frappe.TimestampMismatchError)
            updated = api.detail(email)
            updated.update(farms=[], teams=[])
            api.save(updated, email)
            assert frappe.db.exists('User Permission', advanced.name)
            assert not [r for r in api.grants(email) if api.managed(r)]
            checks.append('scope_diff_preserves_advanced_grants')
        admin_doc = frappe.get_doc('User', email)
        admin_doc.append('roles', {'role': 'System Manager'})
        admin_doc.save()
        frappe.set_user(email)
        own = api.detail(email)
        rejected('self_disable', lambda: api.save(dict(own, enabled=0), email), frappe.ValidationError)
        rejected('self_demote', lambda: api.save(dict(own, enabled=1, roles=['Lotus Auditor']), email), frappe.ValidationError)
        frappe.set_user('Administrator')
        admin_doc = frappe.get_doc('User', email)
        admin_doc.set('roles', [{'role': 'Lotus Auditor'}])
        admin_doc.save()
        # A business role cannot access user administration.
        frappe.set_user(email)
        rejected('business_role_denied', api.users, frappe.PermissionError)
    finally:
        frappe.set_user('Administrator')
        frappe.db.rollback()
        assert not frappe.db.exists('User', email)
        frappe.set_user(original_user)
    return {'checks': checks, 'rolled_back': True}
