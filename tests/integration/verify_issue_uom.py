"""Exercise native issue conversion, stock posting and source caps on a disposable clone."""
import argparse
import math
import frappe
from frappe.utils import flt, nowdate

parser=argparse.ArgumentParser()
parser.add_argument('--site',required=True)
args=parser.parse_args()
assert args.site!='frontend', 'Never run synthetic stock transactions on production'
frappe.init(site=args.site)
frappe.connect()
frappe.set_user('Administrator')
from lotus_farm import warehouse

def close(actual,expected):
    assert math.isclose(flt(actual),expected,rel_tol=1e-9,abs_tol=1e-6),(actual,expected)

def post(result):
    doc=frappe.get_doc('Stock Entry',result['name'])
    return warehouse.submit_document('Stock Entry',doc.name,modified=str(doc.modified))

def rejects(callback, phrase):
    frappe.db.savepoint('invalid_issue')
    try:
        callback()
    except frappe.ValidationError as exc:
        assert phrase in str(exc), str(exc)
    else:
        raise AssertionError('Invalid issue accepted: '+phrase)
    finally:
        frappe.db.rollback(save_point='invalid_issue')

try:
    assert frappe.conf.get('lotus_stock_uom_disposable'), 'Disposable-clone flag required'
    company=frappe.get_all('Company',pluck='name',limit_page_length=1)[0]
    store=frappe.db.get_value('Warehouse',{'company':company,'is_group':0,'disabled':0},'name')
    group=frappe.db.get_value('Item Group',{'is_group':0},'name')
    employee=frappe.db.get_value('Employee',{'company':company,'status':'Active'},'name')
    assert store and group and employee
    from lotus_farm.finance.stock import block_codes
    areas=block_codes(warehouse=store)
    assert areas, 'Warehouse needs a valid usage block in the clone'
    area=areas[0]['code']
    code='UAT-ISSUE-UOM-'+frappe.generate_hash(length=8)
    warehouse.create_master(company,'item',dict(code=code,name='Vật tư thử quy đổi xuất kho',group=group,uom='Kg',pack_uom='Bao',pack_factor=25,minimum_stock=0))
    receipt=warehouse.create_draft(company=company,kind='receipt',posting_date=nowdate(),target=store,
        receipt_reason='Surplus',notes='Disposable stock UOM acceptance',lines=[dict(item=code,qty=20,uom='Bao',rate=25000)])
    post(receipt)
    close(frappe.db.get_value('Bin',{'item_code':code,'warehouse':store},'actual_qty'),500)

    def issue(qty=2,unit='Bao',**overrides):
        values=dict(company=company,kind='issue',posting_date=nowdate(),source=store,receiver_employee=employee,
            issue_mode='Manual',notes='Acceptance only',lines=[dict(item=code,qty=qty,uom=unit,area=area,conversion_factor=999,stock_uom='Nos')])
        values.update(overrides)
        return warehouse.create_draft(**values)

    created=issue(1)
    doc=frappe.get_doc('Stock Entry',created['name'])
    close(doc.items[0].conversion_factor,25)
    close(doc.items[0].transfer_qty,25)
    detail=warehouse.document('Stock Entry',doc.name)
    assert detail['can_submit'] and detail['can_write']
    assert detail['items'][0]['uom']=='Bao'
    close(detail['items'][0]['qty'],1)
    close(detail['items'][0]['stock_qty'],25)
    assert any(u['uom']=='Bao' and u['conversion_factor']==25 for u in detail['items'][0]['uoms'])
    updated=issue(2,existing_name=doc.name,base_modified=str(doc.modified))
    assert updated['name']==doc.name
    doc.reload()
    close(doc.items[0].qty,2)
    close(doc.items[0].transfer_qty,50)
    rejects(lambda:issue(1,'Not-a-configured-unit'),'chưa được khai báo quy đổi')
    rejects(lambda:issue(21),'Không thể lưu phiếu')
    warehouse.submit_document('Stock Entry',doc.name,modified=str(doc.modified))
    ledger=frappe.db.sql('select sum(actual_qty),sum(stock_value_difference) from `tabStock Ledger Entry` where voucher_no=%s and is_cancelled=0',doc.name)[0]
    close(ledger[0],-50)
    close(ledger[1],-50000)
    close(frappe.db.get_value('Bin',{'item_code':code,'warehouse':store},'actual_qty'),450)
    from lotus_farm.www.lotus_stock_print import build
    printed=build('Stock Entry',doc.name)
    close(printed.rows[0]['qty'],2)
    assert printed.rows[0]['uom']=='Bao'
    print('PASS manual issue: item-specific 25 kg/bao, edit/read/print retains bao, ledger -50 kg and correct value; client factor ignored; invalid/overstock rejected')

    request=frappe.get_doc(dict(doctype='Material Request',company=company,material_request_type='Material Issue',
        transaction_date=nowdate(),schedule_date=nowdate(),items=[dict(item_code=code,qty=50,uom='Kg',stock_uom='Kg',conversion_factor=1,
        warehouse=store,schedule_date=nowdate(),lotus_usage_area=area)])).insert()
    request.submit()
    available=warehouse.issue_lines(company,'Request',request.name)['rows'][0]
    close(available['remaining_qty'],50)
    assert available['stock_uom']=='Kg' and any(u['uom']=='Bao' for u in available['uoms'])
    def from_request(qty):
        return warehouse.create_draft(company=company,kind='issue',posting_date=nowdate(),source=store,
            receiver_employee=employee,issue_mode='Request',notes='Request UOM acceptance',lines=[dict(item=code,qty=qty,uom='Bao',area=area,material_request=request.name,material_request_item=request.items[0].name)])
    held=from_request(1)
    close(warehouse.issue_lines(company,'Request',request.name)['rows'][0]['remaining_qty'],25)
    rejects(lambda:from_request(2),'vượt phần còn được cấp')
    post(held)
    close(warehouse.issue_lines(company,'Request',request.name)['rows'][0]['remaining_qty'],25)
    print('PASS request issue: 50 kg cap, 1 bao holds/posts 25 kg, second 2-bao allocation rejected despite sufficient physical stock')

    litre=next((u for u in ('Litre','Liter','Lít') if frappe.db.exists('UOM',u)),None)
    assert litre, 'Missing litre stock unit in fixture'
    liquid=code+'-L'
    warehouse.create_master(company,'item',dict(code=liquid,name='Chất lỏng thử 0,5 lít/can',group=group,uom=litre,pack_uom='Can',pack_factor=0.5,minimum_stock=0))
    liquid_receipt=warehouse.create_draft(company=company,kind='receipt',posting_date=nowdate(),target=store,receipt_reason='Surplus',notes='Liquid fixture',
        lines=[dict(item=liquid,qty=10,uom=litre,rate=10000)])
    post(liquid_receipt)
    liquid_issue=warehouse.create_draft(company=company,kind='issue',posting_date=nowdate(),source=store,receiver_employee=employee,notes='Liquid issue',
        lines=[dict(item=liquid,qty=3,uom='Can',area=area)])
    post(liquid_issue)
    close(frappe.db.get_value('Bin',{'item_code':liquid,'warehouse':store},'actual_qty'),8.5)
    print('PASS fractional conversion: 3 can at 0.5 litre/can deducts 1.5 litres')
finally:
    frappe.db.rollback()
    frappe.destroy()
    print('ROLLBACK_COMPLETE')
