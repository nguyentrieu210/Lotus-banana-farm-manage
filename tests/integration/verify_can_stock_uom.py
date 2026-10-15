"""Rollback-only verification for Can as the stock unit in Lotus."""
import os
import frappe
os.chdir('/home/frappe/frappe-bench/sites')
frappe.init(site='frontend')
frappe.connect()
frappe.set_user('Administrator')
from lotus_farm import warehouse, warehouse_masters

try:
    company=frappe.db.get_value('Company',{},'name')
    group=frappe.db.get_value('Item Group',{'is_group':0},'name')
    assert frappe.db.exists('UOM','Can')
    assert frappe.db.get_value('UOM','Can','enabled')
    assert company and group
    row=warehouse.create_master(company,'item',{
        'code':'CAN-UAT-'+frappe.generate_hash(length=7),
        'name':'Can kiểm thử (tự rollback)',
        'group':group,'uom':'Can','minimum_stock':10,
        'description':'Dữ liệu kiểm thử, không lưu thật'
    })
    item=frappe.get_doc('Item',row['name'])
    assert item.stock_uom=='Can'
    assert item.lotus_minimum_stock_global==10
    opts=warehouse.catalogue(company)
    assert any(u['name']=='Can' for u in opts['uoms'])
    print('PASS: Can usable as base stock UOM in Item and master catalogue')
finally:
    frappe.db.rollback()
    frappe.destroy()
