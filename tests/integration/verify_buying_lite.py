"""Rollback-only acceptance test for Lotus purchase Lite against ERPNext."""
import os, frappe
from frappe.utils import add_days, nowdate

os.chdir('/home/frappe/frappe-bench/sites')
frappe.init(site='frontend')
frappe.connect()
frappe.set_user('Administrator')

from lotus_farm import warehouse_buying_lite as buying
from lotus_farm import warehouse_planning

try:
    company=frappe.db.get_value('Company',{},'name')
    buying.install_fields()
    assert frappe.get_meta('Purchase Order').has_field('lotus_purchase_mode')
    today=nowdate()
    due=add_days(today,3)
    warehouse=frappe.db.get_value('Warehouse',{'company':company,'is_group':0,'disabled':0},'name')
    item=frappe.db.get_value('Item',{'is_stock_item':1,'disabled':0},'name')
    assert warehouse and item
    unit=frappe.db.get_value('Item',item,'stock_uom')
    supplier=buying.create_supplier(company,'UAT NCC '+frappe.generate_hash(length=9))
    assert supplier['name']
    print('PASS new Supplier:',supplier['name'])

    settings=buying.setup(company)
    assert any(s['name']==supplier['name'] for s in settings['suppliers'])
    assert settings['can_create']
    print('PASS buying setup returns catalogues')

    payload=dict(supplier=supplier['name'],warehouse=warehouse,
        mode='Chủ đầu tư chỉ định',expected_date=due,notes='UAT temporary',
        items=[dict(item=item,qty=12,uom=unit,rate=30000)])
    created=buying.save_order(company,payload)
    detail=buying.order_detail(created['name'])
    assert detail['status']=='Nháp' and detail['can_submit']
    assert detail['items'][0]['qty']==12
    assert detail['mode']=='Chủ đầu tư chỉ định'
    print('PASS draft Purchase Order:',created['name'])

    list_all=buying.orders(company)
    assert any(r['name']==created['name'] for r in list_all['rows'])
    print('PASS list and columns')

    buying.submit_order(created['name'],created['modified'])
    active=buying.order_detail(created['name'])
    assert active['docstatus']==1 and active['status']=='Chờ hàng',active['status']
    assert active['can_receive']
    pending=buying.orders(company,status='pending')
    assert any(r['name']==created['name'] for r in pending['rows'])
    print('PASS submitted PO appears in incoming orders')

    # Existing receiving API must preserve provenance and does not update Bin until posted.
    line=active['items'][0]
    original_stock=frappe.db.get_value('Bin',{'item_code':item,'warehouse':warehouse},'actual_qty') or 0
    event_id=frappe.generate_hash(length=16)
    received=warehouse_planning.receive_order(created['name'],today,
        {line['line']:5},event_id)
    again=warehouse_planning.receive_order(created['name'],today,{line['line']:5},event_id)
    assert again['name']==received['name']
    print('PASS mobile request idempotency')
    receipt=warehouse_planning.purchase_receipt(received['name'])
    assert receipt['docstatus']==0
    print('PASS partial Purchase Receipt draft:',receipt['name'])
    warehouse_planning.receipt_action(receipt['name'],receipt['modified'],'submit')
    frappe.get_doc('Purchase Order',created['name']).reload()
    after=buying.order_detail(created['name'])
    assert after['status']=='Về một phần', after['status']
    assert abs(after['items'][0]['remaining_qty']-7)<0.001,after['items'][0]
    actual=frappe.db.get_value('Bin',{'item_code':item,'warehouse':warehouse},'actual_qty') or 0
    assert abs(actual-original_stock-5)<0.001,(actual,original_stock)
    print('PASS posted partial receipt and outstanding 7',unit)
    listed=buying.order_receipts(created['name'])
    assert any(r['name']==receipt['name'] and r['docstatus']==1 for r in listed)
    posted=warehouse_planning.purchase_receipt(receipt['name'])
    warehouse_planning.receipt_action(receipt['name'],posted['modified'],'cancel')
    reversed_stock=frappe.db.get_value('Bin',{'item_code':item,'warehouse':warehouse},'actual_qty') or 0
    assert abs(reversed_stock-original_stock)<0.001,(reversed_stock,original_stock)
    remaining=buying.order_detail(created['name'])
    assert remaining['status']=='Chờ hàng',remaining['status']
    assert abs(remaining['items'][0]['remaining_qty']-12)<0.001
    print('PASS cancelled receipt reverses Bin and reopens 12',unit)
    assert any(r['docstatus']==2 for r in buying.order_receipts(created['name']))

finally:
    frappe.db.rollback()
    frappe.destroy()
