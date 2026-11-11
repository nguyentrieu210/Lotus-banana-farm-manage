import frappe
frappe.init(site='mua.test', sites_path='/home/frappe/frappe-bench/sites')
frappe.connect()
# Real users of the site carry no Employee/Company user permission; the UAT accounts got them from HRMS defaults.
users = frappe.get_all('User', filters={'name': ['like', 'uat-%@lotus-uat.invalid']}, pluck='name')
frappe.db.sql("delete from `tabUser Permission` where user in %s", (tuple(users),))
frappe.db.sql("update `tabEmployee` set create_user_permission=0 where user_id in %s", (tuple(users),))
frappe.db.commit()
print('left', frappe.db.count('User Permission', {'user': ['in', users]}))
frappe.clear_cache()
frappe.destroy()
