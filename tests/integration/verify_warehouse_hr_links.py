import os
import frappe

os.chdir('/home/frappe/frappe-bench/sites')
frappe.init(site='frontend')
frappe.connect()
frappe.set_user('Administrator')
from lotus_farm import warehouse, warehouse_masters

try:
    company=frappe.get_all('Company',pluck='name',limit=1)[0]
    root=frappe.db.get_value('Warehouse',{'company':company,'is_group':1},'name')
    assert root, 'No warehouse group'
    suffix=frappe.generate_hash(length=7)
    label='Kho Test '+suffix
    contacts=warehouse_masters.employee_choices(company)
    staff=contacts[0]['value'] if contacts else ''
    created=warehouse.create_master(company,'warehouse',{
        'name':label,'parent':root,'lotus_contact_employee':staff,
        'lotus_address':'Địa chỉ kiểm thử','lotus_default_lead_days':3})
    first=frappe.get_doc('Warehouse',created['name'])
    assert first.name==warehouse_masters.warehouse_code(label,company)
    if staff:
        assert first.lotus_contact_employee==staff
        assert first.lotus_contact_name==contacts[0]['label']
    renamed=warehouse_masters.save_master(company,'warehouse',first.name,str(first.modified),{
        'name':label+' Đổi tên','lotus_contact_employee':staff,
        'lotus_address':'Địa chỉ kiểm thử','lotus_default_lead_days':5})
    expected=warehouse_masters.warehouse_code(label+' Đổi tên',company)
    assert renamed['name']==expected
    assert frappe.get_doc('Warehouse',expected).lotus_default_lead_days==5
    assert not frappe.db.exists('Warehouse',first.name)
    print('PASS create, code-from-name, HRMS link and safe Frappe warehouse rename (rollback)')
finally:
    frappe.db.rollback()
    frappe.destroy()
