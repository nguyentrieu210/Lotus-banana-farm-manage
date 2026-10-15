"""Rollback-only ERPNext Item/UOM/warehouse receipt acceptance checks."""
import os, frappe
os.chdir('/home/frappe/frappe-bench/sites')
frappe.init(site='frontend')
frappe.connect()
frappe.set_user('Administrator')
from lotus_farm import warehouse
from lotus_farm import warehouse_masters

try:
    company=frappe.get_all('Company',pluck='name',limit_page_length=1)[0]
    store=frappe.db.get_value('Warehouse',{'company':company,'is_group':0,'disabled':0},'name')
    group=frappe.db.get_value('Item Group',{'is_group':0},'name')
    assert store and group
    assert frappe.db.exists('UOM','Bao')
    assert frappe.get_meta('Item').has_field('lotus_minimum_stock_global')
    code='LOTUS-UAT-UOM-'+frappe.generate_hash(length=8)
    created=warehouse.create_master(company,'item',{
        'code':code,'name':'Phân UAT 25kg / bao','group':group,
        'uom':'Kg','pack_uom':'Bao','pack_factor':25,'minimum_stock':2000,
        'description':'Synthetic test only, rolled back.'
    })
    item=frappe.get_doc('Item',created['name'])
    assert item.stock_uom=='Kg'
    assert item.lotus_minimum_stock_global==2000
    pack=warehouse_masters.item_pack(item)
    assert pack==dict(pack_uom='Bao',pack_factor=25)
    print('PASS new Item: global min 2000 kg; 1 Bao = 25 kg')

    overview=warehouse.overview(company,warehouse=store)
    found=next(x for x in overview['items'] if x['name']==item.name)
    assert found['minimum_stock']==2000
    assert found['shortage_qty']==2000
    assert found['pack_uom']=='Bao' and found['pack_factor']==25
    print('PASS global minimum does not require choosing an Item warehouse')

    result=warehouse.create_draft(company=company,kind='receipt',posting_date='2026-10-15',
        lines=[{'item':item.name,'qty':4000,'uom':'Bao','rate':125000}],
        target=store,notes='UAT only')
    doc=frappe.get_doc('Stock Entry',result['name'])
    line=doc.items[0]
    assert line.uom=='Bao',line.uom
    assert float(line.conversion_factor)==25
    assert float(line.qty)==4000
    assert abs(float(line.transfer_qty)-100000)<0.001
    assert abs(float(line.basic_rate)-5000)<0.01
    assert abs(float(line.basic_amount)-500000000)<0.01
    detail=warehouse.document('Stock Entry',doc.name)
    assert detail['items'][0]['uom']=='Bao'
    assert abs(detail['items'][0]['rate']-125000)<0.01
    assert detail['items'][0]['qty']==4000
    assert detail['can_submit'], 'Receipt with alternative UOM must be submittable'
    assert detail['can_write'], 'Receipt with alternative UOM must be editable'
    print('PASS 4000 Bao * 25 kg = 100000 kg; receipt total 500,000,000 VND')
    doc.submit()
    assert doc.docstatus == 1
    posted=frappe.db.sql('select sum(actual_qty) from `tabStock Ledger Entry` where voucher_no=%s',(doc.name,))[0][0]
    assert abs(float(posted or 0)-100000)<0.001, posted
    print('PASS posted ledger: +100000 Kg from 4000 Bao (rollback)')
finally:
    frappe.db.rollback()
    frappe.destroy()
