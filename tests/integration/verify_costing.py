"""Giá thành chuối on the real site, rolled back: a lot gets material cost (621), its harvest enters stock at the provisional
rate (Nợ 155 / Có 154), the month's costs move to 154, the costing run absorbs the lot's work in progress into the harvest
and posts the difference to 632, a second run is refused, and reversing the costing voucher marks the sheet Reversed.
Needs finance switched on with the Thông tư 99 chart (as on production)."""
import json
import unicodedata
import uuid

import frappe
from frappe.utils import flt, nowdate

frappe.init(site='frontend', sites_path='/home/frappe/frappe-bench/sites')
frappe.connect()
frappe.set_user('Administrator')
from lotus_farm.finance import closing, costing, posting, setup  # noqa: E402

tag = uuid.uuid4().hex[:6]
today = nowdate()
month = today[:7]
report = {}


def refused(fn, *args, text=None):
    try:
        fn(*args)
    except frappe.ValidationError as exc:
        nfc = lambda t: unicodedata.normalize('NFC', t)
        assert text is None or nfc(text) in nfc(str(exc)), exc
        return
    raise AssertionError('expected refusal')


def gl(voucher):
    return frappe.db.sql("""select account, debit, credit, lotus_farm, lotus_farm_block from `tabGL Entry` where voucher_no=%s and is_cancelled=0""",
                         voucher, as_dict=True)


try:
    cfg = setup.settings()
    assert cfg.finance_enabled and cfg.coa_version, 'finance must be on with the TT99 chart'
    company = setup.company()
    m = setup.mapping()
    frappe.db.set_single_value(setup.SETTINGS, 'harvest_standard_cost', 2000)
    frappe.db.set_single_value('Stock Settings', 'enable_serial_and_batch_no_for_item', 1)  # harvest lots trace by batch
    block = frappe.db.sql("""select b.name, b.farm, b.block_code, p.name plot from `tabFarm Block` b join `tabFarm Plot` p on p.farm_block=b.name
        where b.block_code in (select block_code from `tabFarm Block` group by block_code having count(*)=1) limit 1""", as_dict=True)[0]
    # the ribbon-colour lineage (OneDrive) is not what this check is about
    frappe.db.sql("""update `tabLotus Process Adoption` set approval_state='Draft' where farm=%s""", block.farm)
    variety = frappe.get_all('Banana Variety', pluck='name', limit_page_length=1)
    cycle = frappe.get_doc(dict(doctype='Crop Cycle', farm=block.farm, farm_block=block.name, cycle_no=1, cycle_type='Plant', status='Harvesting',
                                variety=variety[0] if variety else None, planting_date='2026-01-15',
                                farm_plot=block.plot)).insert(ignore_permissions=True)
    raw = frappe.get_doc(dict(doctype='Item', item_code='CHUOI-THO-' + tag, item_name='Chuối thô ' + tag, item_group='All Item Groups', stock_uom='Kg',
                              is_stock_item=1, has_batch_no=1)).insert(ignore_permissions=True).name
    wh = frappe.get_doc(dict(doctype='Warehouse', warehouse_name='Kho chuối ' + tag, company=company)).insert(ignore_permissions=True).name
    batch = frappe.get_doc(dict(doctype='Batch', batch_id='CT-' + tag, item=raw)).insert(ignore_permissions=True).name
    actual = frappe.get_doc(dict(doctype='Harvest Actual', farm=block.farm, farm_block=block.name, crop_cycle=cycle.name, harvest_date=today,
                                 harvested_bunch_qty=12, gross_weight_kg=300, rejected_weight_kg=0)).insert(ignore_permissions=True)
    actual.submit()
    lot = frappe.get_doc(dict(doctype='Harvest Lot', farm=block.farm, company=company, received_date=today, raw_item=raw, raw_warehouse=wh, raw_batch=batch,
                              sources=[dict(harvest_actual=actual.name, contributed_kg=300)])).insert(ignore_permissions=True)
    lot.submit()
    assert any(r['name'] == lot.name for r in costing.lots_to_receive()), 'the harvest lot waits to enter stock'

    # material cost on the lot (621)
    item = frappe.db.sql("""select b.item_code, b.warehouse from tabBin b join tabItem i on i.name=b.item_code
        where b.actual_qty > 5 and b.valuation_rate > 0 and i.has_batch_no=0 and i.has_serial_no=0 limit 1""", as_dict=True)[0]
    issue = frappe.get_doc(dict(doctype='Stock Entry', company=company, stock_entry_type='Material Issue', purpose='Material Issue', posting_date=today,
                                set_posting_time=1, lotus_issue_mode='Manual', lotus_receiver='Kiểm tra giá thành', remarks='Giá thành ' + tag,
                                items=[dict(item_code=item.item_code, qty=2, s_warehouse=item.warehouse, lotus_usage_area=block.block_code)]))
    issue.flags.ignore_permissions = True
    issue.insert()
    issue.submit()
    material = sum(flt(x.debit) for x in gl(issue.name) if x.account == m['material_cost'])
    assert material > 0

    received = costing.receive_harvest(lot.name)
    rec_gl = gl(received['stock_entry'])
    assert any(x.account == m['finished_goods'] and flt(x.debit) == 600000 for x in rec_gl), rec_gl
    assert any(x.account == m['production_cost'] and flt(x.credit) == 600000 and x.lotus_farm_block == block.name for x in rec_gl), rec_gl
    assert frappe.db.get_value('Warehouse', wh, 'account') == m['finished_goods'], 'the fruit warehouse posts to 155'
    refused(costing.receive_harvest, lot.name, text='đã nhập kho')

    refused(costing.run, month, text='Kết chuyển chi phí')
    closing.post(month)
    view = costing.preview(month)
    mine = next(r for r in view['rows'] if r['lotus_farm_block'] == block.name)
    assert mine['kg_harvested'] == 300 and mine['provisional'] == 600000, mine
    assert abs(mine['cost_month'] - round(material)) <= 1, (mine['cost_month'], material)
    assert mine['wip_close'] == mine['wip_open'] + mine['cost_month'] - mine['absorbed']
    done = costing.run(month)
    sheet = frappe.get_doc(costing.RUN, done['run'])
    row = next(r for r in sheet.rows if r.lotus_farm_block == block.name)
    assert flt(row.cost_per_kg) == round(flt(row.absorbed) / 300, 2), row.as_dict()
    if done['voucher']:
        adj = gl(done['voucher'])
        assert abs(sum(flt(x.debit) for x in adj) - sum(flt(x.credit) for x in adj)) < 1
    lot_wip = flt(frappe.db.sql("""select sum(debit-credit) from `tabGL Entry` where is_cancelled=0 and account=%s and lotus_farm_block=%s""",
                                (m['production_cost'], block.name))[0][0])
    assert abs(lot_wip - flt(row.wip_close)) < 1, (lot_wip, row.wip_close)
    if done['voucher']:
        refused(costing.run, month, text='đã tính giá thành')
        p = posting.active('Lotus Finance Settings', setup.SETTINGS, 'Costing', month)
        posting.reverse(p.name, 'Kiểm tra đảo giá thành')
        # hooks are cached from the deployed release; check the wiring in the copied hooks.py and run it if not deployed yet
        from lotus_farm import hooks
        assert 'lotus_farm.finance.costing.costing_reversed' in str(hooks.doc_events['Journal Entry']['on_cancel'])
        if 'lotus_farm.finance.costing.costing_reversed' not in str(frappe.get_hooks('doc_events').get('Journal Entry', {})):
            costing.costing_reversed(frappe.get_doc('Journal Entry', done['voucher']))
        assert frappe.db.get_value(costing.RUN, done['run'], 'state') == 'Reversed'
    report.update(receipt=received, run=done, lot=dict(kg=row.kg_harvested, absorbed=row.absorbed, per_kg=row.cost_per_kg, adjustment=row.adjustment,
                                                       wip_close=row.wip_close), rollback=True)
finally:
    frappe.set_user('Administrator')
    frappe.db.rollback()
print(json.dumps(report, ensure_ascii=False, default=str))
