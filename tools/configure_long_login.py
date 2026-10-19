"""Enable a native one-year inactivity window, without changing passwords or MFA."""
import frappe

frappe.init(site='frontend')
frappe.connect()
try:
    frappe.set_user('Administrator')
    previous=frappe.db.get_single_value('System Settings','session_expiry')
    settings=frappe.get_single('System Settings')
    settings.session_expiry='8760:00:00'
    settings.save()
    frappe.db.commit()
    frappe.clear_cache(doctype='System Settings')
    print('Session inactivity window: '+str(previous)+' -> 8760:00:00 (365 days). Existing sessions retain their original expiry; new logins use the new window.')
finally:
    frappe.destroy()
