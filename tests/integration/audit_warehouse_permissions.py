import frappe,uuid,json
frappe.init(site='frontend',sites_path='/home/frappe/frappe-bench/sites');frappe.connect();frappe.set_user('Administrator')
user=None
try:
 from lotus_farm import warehouse as w
 from lotus_farm.www.lotus_stock_print import get_context,download_pdf
 tag=uuid.uuid4().hex[:8];company='Lotus Agritech'
 make=lambda dt,**v:frappe.get_doc(dict(doctype=dt,**v)).insert()
 a=make('Warehouse',warehouse_name='Allowed '+tag,company=company).name;b=make('Warehouse',warehouse_name='Denied '+tag,company=company).name
 item=make('Item',item_code='PERMISSION-'+tag,item_name='Permission review',item_group='All Item Groups',stock_uom='Kg',is_stock_item=1).name
 draft=w.create_draft(company,'receipt',frappe.utils.nowdate(),[dict(item=item,qty=1,rate=1)],target=b)
 user=make('User',email='warehouse-review-'+tag+'@example.invalid',first_name='Permission review',enabled=1,send_welcome_email=0,user_type='System User',roles=[dict(role='Stock User')]).name
 make('User Permission',user=user,allow='Company',for_value=company,apply_to_all_doctypes=1)
 make('User Permission',user=user,allow='Warehouse',for_value=a,apply_to_all_doctypes=1)
 frappe.set_user(user);out={}
 operations=dict(read_hidden=lambda:w.document('Stock Entry',draft['name']),write_hidden=lambda:w.create_draft(company,'receipt',frappe.utils.nowdate(),[dict(item=item,qty=1,rate=1)],target=b),list_hidden=lambda:w.overview(company,warehouse=b),print_hidden=lambda:get_context(frappe._dict(),'Stock Entry',draft['name']),pdf_hidden=lambda:download_pdf('Stock Entry',draft['name']))
 for name,fn in operations.items():
  try:fn()
  except frappe.PermissionError:out[name]='blocked'
  else:out[name]='UNEXPECTED ALLOWED'
 assert all(v=='blocked' for v in out.values()),out
 frappe.set_user('Guest')
 try:w.bootstrap()
 except frappe.AuthenticationError:out['guest']='blocked'
 print(json.dumps(out))
finally:
 frappe.set_user('Administrator');frappe.db.rollback()
 if user:frappe.clear_cache(user=user)
 frappe.destroy()
