import os,frappe
os.chdir('/home/frappe/frappe-bench/sites')
frappe.init(site='frontend');frappe.connect();frappe.set_user('Administrator')
try:
 row=frappe.db.get_value('Custom DocPerm',{'parent':'Stock Ledger Entry','role':'Lotus Warehouse Operator','permlevel':0},['read','create','write'],as_dict=True)
 assert row and row.read and not row.create and not row.write,row
 print('PASS operator sees Stock Ledger Entry read only')
finally:
 frappe.db.rollback()
 frappe.destroy()
