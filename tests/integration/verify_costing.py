"""Giá thành chuối on a copy of the real site, rolled back. Needs Vườn 222 set up, finance switched on with the Thông tư 99
chart, and a month whose costs are not closed yet (it runs in the current month).

A lô gets material cost (621). Its harvest is confirmed in the sổ lô, a packhouse shift packs it and the accountant's
draft receipt waits in Chờ hạch toán and holds the month (no costing, no result closing) until the warehouse submits it
at the provisional rate (Nợ 155 / Có 154 of the lô). Part of the fruit is sold. The month's costs move to 154; the
costing run absorbs the lô's work in progress into the harvest by the shared forecast (bunches due after the month, day
by day up to one crop pipeline, on the basis of the kg received), posts the difference of the fruit sold to 632 and
leaves the difference of the fruit still in stock in 154, so the sheet closes on the ledger. A month already over reads
the sổ lô by work day. An accountant without any farm scope gets the same figures. A second run is refused, and
reversing the costing voucher marks the sheet Reversed. A lô whose estimated flowering date is so old that the tree-count
forecast stops before one crop pipeline after the month makes the costing refuse, naming that lô.

docker exec -i lotus-vps-test-backend-1 bash -lc 'cd /home/frappe/frappe-bench/sites && ../env/bin/python -' < tests/integration/verify_costing.py
"""
import json
import os
import unicodedata
import uuid

import frappe
from frappe.utils import add_days, cint, flt, getdate, now_datetime, nowdate

frappe.init(site=os.environ.get('SITE', 'frontend'), sites_path='/home/frappe/frappe-bench/sites')
frappe.connect()
frappe.set_user('Administrator')
from lotus_farm import block_forecast, lot_ledger  # noqa: E402
from lotus_farm import field_report as field  # noqa: E402
from lotus_farm import lot_ledger_rules as ledger  # noqa: E402
from lotus_farm import shift as shift_api  # noqa: E402
from lotus_farm.block_forecast_engine import months_after, weight_kg  # noqa: E402
from lotus_farm.finance import api, closing, costing, posting, reports, rules, setup  # noqa: E402

FARM = os.environ.get('FARM', 'LOTUS-222')
ENTRY = 'Lotus Work Entry'
KG_IN, FINISHED_KG, SECONDARY_KG, SOLD_KG, STANDARD = 2000, 1600, 400, 800, 2000
tag = uuid.uuid4().hex[:6]
today = nowdate()
month = today[:7]
report = {}


def refused(fn, *args, text=None, kind=frappe.ValidationError):
    try:
        fn(*args)
    except kind as exc:
        nfc = lambda t: unicodedata.normalize('NFC', t)
        assert text is None or nfc(text) in nfc(str(exc)), exc
        frappe.clear_messages()
        return
    raise AssertionError('expected refusal')


def gl(voucher):
    return frappe.db.sql("""select account, debit, credit, lotus_farm, lotus_farm_block from `tabGL Entry` where voucher_no=%s and is_cancelled=0""",
                         voucher, as_dict=True)


def posted(doc):
    doc.flags.ignore_permissions = True
    if doc.is_new():
        doc.insert()
    doc.submit()
    return doc


def as_user(user, fn, *args):
    frappe.set_user(user)
    try:
        result = fn(*args)
        assert frappe.session.user == user, 'the session is still the caller\'s'
        return result
    finally:
        frappe.set_user('Administrator')


try:
    cfg = setup.settings()
    assert cfg.finance_enabled and cfg.coa_version and not setup.mapping_errors(cfg), 'finance must be on with the TT99 chart'
    company = setup.company()
    assert frappe.db.get_value('Farm', FARM, 'company') == company, 'the farm belongs to the company of the books'
    m = setup.mapping()
    start, end = closing._bounds(month)
    assert not posting.active(setup.SETTINGS, setup.SETTINGS, 'Cost Closing', month), 'run in a month whose costs are not closed yet'
    assert not costing.waiting_text(costing.waiting(company, month)), 'run in a month whose packhouse shifts are all in stock'
    # Fixed assets have their own check (verify_fixed_assets): depreciation still due this month must not stop this one.
    frappe.db.set_single_value(setup.SETTINGS, 'fixed_assets_enabled', 0)

    # A lô whose code names it alone (the issue form reads the lô from "Khu vực / lô sử dụng") and with no fruit received this month.
    block = frappe.db.sql("""select b.name, b.farm, b.block_code from `tabFarm Block` b where b.farm=%s and b.active=1
        and b.block_code in (select block_code from `tabFarm Block` group by block_code having count(*)=1)
        and b.name not in (select ifnull(d.lotus_farm_block, '') from `tabStock Entry Detail` d join `tabStock Entry` e on e.name=d.parent
            where e.docstatus=1 and e.lotus_receipt_reason='Harvest' and e.posting_date between %s and %s)
        order by b.block_code limit 1""", (FARM, start, end), as_dict=True)[0]

    # Fruit items and a warehouse of their own: what they hold at month end is only what this check received.
    finished, secondary = [frappe.get_doc(dict(doctype='Item', item_code=code + tag, item_name=name + ' ' + tag, item_group='All Item Groups',
                                               stock_uom='Kg', is_stock_item=1)).insert(ignore_permissions=True).name
                           for code, name in (('CHUOI-TP-', 'Chuối thành phẩm thử'), ('CHUOI-PP-', 'Chuối phụ phẩm thử'))]
    warehouse = frappe.get_doc(dict(doctype='Warehouse', warehouse_name='Kho thành phẩm thử ' + tag, company=company)).insert(ignore_permissions=True).name
    frappe.db.set_single_value(setup.SETTINGS, {'packed_item': finished, 'secondary_item': secondary, 'packed_warehouse': warehouse,
                                                'harvest_standard_cost': STANDARD})
    unsold_before = costing._unsold(company, month)

    # 1. Material cost on the lô (621) ---------------------------------------------------------------------
    cost_accounts = tuple(closing.cost_accounts(company))

    def lot_costs():
        return flt(frappe.db.sql("""select sum(debit-credit) from `tabGL Entry` where company=%s and is_cancelled=0 and lotus_farm_block=%s
            and posting_date between %s and %s and account in %s""", (company, block.name, start, end, cost_accounts))[0][0])
    costs_before = lot_costs()
    item = frappe.db.sql("""select b.item_code, b.warehouse from tabBin b join tabItem i on i.name=b.item_code join tabWarehouse w on w.name=b.warehouse
        where w.company=%s and b.actual_qty > 5 and b.valuation_rate > 0 and i.disabled=0 and i.has_batch_no=0 and i.has_serial_no=0 limit 1""",
                         company, as_dict=True)[0]
    issue = posted(frappe.get_doc(dict(doctype='Stock Entry', company=company, stock_entry_type='Material Issue', purpose='Material Issue', posting_date=today,
                                       set_posting_time=1, lotus_issue_mode='Manual', lotus_receiver='Kiểm tra giá thành', remarks='Giá thành ' + tag,
                                       items=[dict(item_code=item.item_code, qty=2, s_warehouse=item.warehouse, lotus_usage_area=block.block_code)])))
    on_cost = [x for x in gl(issue.name) if x.account == m['material_cost']]
    material = sum(flt(x.debit) for x in on_cost)
    assert material > 0 and all(x.lotus_farm_block == block.name and x.lotus_farm == FARM for x in on_cost), on_cost

    # 2. Harvest in the sổ lô -> packhouse shift -> the closed shift waits for its stock receipt -------------
    works = {w['stage']: w for w in lot_ledger.works(FARM).values() if w['stage']}
    ribbon = (field.ribbon(FARM, add_days(today, -70)) or frappe._dict(
        name=frappe.get_all('Bunch Tag', filters={'farm': FARM}, pluck='name', order_by='creation asc', limit=1)[0])).name

    def line(stage, qty, on, **values):
        """A confirmed sổ lô line, stored directly (the daily report flow has its own check, verify_field_reports)."""
        doc = frappe.new_doc(ENTRY)
        doc.update(dict({'farm': FARM, 'company': company, 'farm_block': block.name, 'work_type': works[stage]['name'], 'stage': stage,
                         'pay_mode': works[stage]['pay_mode'], 'posting_date': on, 'qty': qty, 'bunch_tag': ribbon, 'state': ledger.CONFIRMED,
                         'source_type': ledger.MANUAL, 'source_key': 'costing:' + frappe.generate_hash(length=12), 'entered_by': 'Administrator',
                         'confirmed_by': 'Administrator', 'confirmed_at': now_datetime(), 'cycle_no': 2}, **values))
        token = field._writing.set(True)
        frappe.flags.lotus_ledger_migrating = True
        try:
            doc.save(ignore_permissions=True)
        finally:
            frappe.flags.lotus_ledger_migrating = False
            field._writing.reset(token)
        return doc
    cut = line(ledger.CUT, 150, add_days(today, -70))
    harvest = line(ledger.HARVEST, 100, today, weight_kg=KG_IN)
    saved = shift_api.save_shift(FARM, json.dumps({
        'shift_code': 'GT-' + tag, 'posting_date': today, 'started_at': today + ' 07:00:00', 'ended_at': today + ' 16:00:00',
        'finished_kg': FINISHED_KG, 'secondary_kg': SECONDARY_KG, 'cartons': 120,
        'sources': [{'farm_block': block.name, 'bunch_tag': ribbon, 'bunches': 100, 'kg': KG_IN, 'harvest_entry': harvest.name}]}))
    shift = shift_api.close_shift(saved['doc']['name'])['doc']
    assert shift['docstatus'] == 1, shift
    listed = lambda: [r for r in reports.pending()['shifts'] if r['name'] == shift['name']]
    assert listed() and listed()[0]['finished_kg'] == FINISHED_KG and not listed()[0]['stock_entry'], 'a closed shift waits for its stock receipt'
    assert costing.waiting(company, month) == dict(shifts=[shift['name']], drafts=[]), costing.waiting(company, month)

    # 3. The accountant's draft receipt holds the month until the warehouse submits it; submitted, it moves the lô's cost
    #    from 154 to 155 at the provisional rate
    rate = costing._last_cost(block.name) or STANDARD  # every kg brought in was packed, so both valuations give kg × rate
    value = KG_IN * rate
    received = costing.receive_shift(shift['name'])
    assert received['kg'] == FINISHED_KG + SECONDARY_KG and abs(received['amount'] - value) < 1 and received['docstatus'] == 0, received
    assert [r['stock_entry'] for r in listed()] == [received['stock_entry']], 'a shift whose receipt is a draft still waits, with its draft'
    assert costing.waiting(company, month) == dict(shifts=[], drafts=[received['stock_entry']]), costing.waiting(company, month)
    assert next(s for s in api.month_checklist(month)['steps'] if s['key'] == 'shifts')['state'] == 'todo', 'the month is not ready'
    assert any(received['stock_entry'] in i for i in closing.result_preview(month)['issues']), 'the result closing waits for the draft'
    refused(costing.receive_shift, shift['name'], text='đã có phiếu nhập kho')
    receipt = frappe.get_doc('Stock Entry', received['stock_entry'])
    assert receipt.lotus_packhouse_shift == shift['name'] and receipt.lotus_receipt_reason == 'Harvest', receipt.as_dict()
    assert {(r.item_code, flt(r.qty), r.lotus_farm_block) for r in receipt.items} == {(finished, FINISHED_KG, block.name), (secondary, SECONDARY_KG, block.name)}
    refused(costing.run, month, text='Kết chuyển chi phí')
    closing.post(month)  # the receipt and the sale below post to 154, 155 and 632, never to 621 / 622 / 627
    refused(costing.run, month, text=received['stock_entry'])
    posted(receipt)
    assert not listed() and not costing.waiting_text(costing.waiting(company, month)), 'a submitted receipt frees the month'
    rec_gl = gl(receipt.name)
    assert abs(sum(flt(x.debit) for x in rec_gl if x.account == m['finished_goods']) - value) < 1, rec_gl
    assert abs(sum(flt(x.credit) for x in rec_gl if x.account == m['production_cost'] and x.lotus_farm_block == block.name) - value) < 1, rec_gl
    assert frappe.db.get_value('Warehouse', warehouse, 'account') == m['finished_goods'], 'the fruit warehouse posts to 155'

    # 4. Part of the fruit leaves stock before month end (Nợ 632 / Có 155) ------------------------------------
    sale = posted(frappe.get_doc(dict(doctype='Stock Entry', company=company, stock_entry_type='Material Issue', purpose='Material Issue', posting_date=today,
                                      set_posting_time=1, lotus_issue_purpose='Sale', remarks='Xuất bán thử ' + tag,
                                      items=[dict(item_code=finished, qty=SOLD_KG, s_warehouse=warehouse)])))
    assert abs(sum(flt(x.debit) for x in gl(sale.name) if x.account == m['cost_of_goods_sold']) - SOLD_KG * rate) < 1, gl(sale.name)
    unsold = costing._unsold(company, month)
    assert abs(unsold['kg_received'] - unsold_before['kg_received'] - (FINISHED_KG + SECONDARY_KG)) < 0.001, (unsold_before, unsold)
    assert abs(unsold['kg_unsold'] - unsold_before['kg_unsold'] - (FINISHED_KG + SECONDARY_KG - SOLD_KG)) < 0.001, (unsold_before, unsold)

    # 5. Month end: costs went to 154 above; the costing sheet --------------------------------------------------
    view = costing.preview(month)
    assert view['unsold'] == unsold and 0 < unsold['share'] < 1, view['unsold']
    assert not view['out_of_date'] and view['waiting'] == dict(shifts=[], drafts=[], text=''), view['waiting']
    mine = next(r for r in view['rows'] if r['lotus_farm_block'] == block.name)
    assert mine['kg_harvested'] == FINISHED_KG + SECONDARY_KG and abs(mine['provisional'] - value) < 1, mine
    assert abs(mine['cost_month'] - (costs_before + material)) <= 1, (mine['cost_month'], costs_before, material)
    # the vụ of the fruit: the one with most bunches on the lô's confirmed harvest lines of the month (the test's: vụ 2)
    harvested = frappe.db.sql("""select cycle_no, sum(qty) from `tabLotus Work Entry` where farm_block=%s and stage=%s and state=%s
        and posting_date between %s and %s and ifnull(cycle_no, 0) > 0 group by cycle_no""", (block.name, ledger.HARVEST, ledger.CONFIRMED, start, end))
    assert mine['cycle_no'] == max(harvested, key=lambda r: (flt(r[1]), cint(r[0])))[0], (mine['cycle_no'], harvested)
    assert all(r['cycle_no'] is None for r in view['rows'] if not r['lotus_farm_block']), 'the farm pool has no vụ'
    # kg still expected from the lô: the shared forecast's bunches due after this (running) month, day by day up to one crop
    # pipeline, on the basis of the kg received (the lô received 1 600 kg finished + 400 kg secondary this month: × 1,25)
    expected = 0
    for c in block_forecast.bunch_summary(FARM)[1]:
        if c['block'] == block.name:
            last = rules.pipeline_end(getdate(end), c['config'])
            expected += sum(n * weight_kg(c['cycle'], c['config']) * c['config']['pack_rate'] for day, n in c['days'] if getdate(end) < day <= last)
    mix = (FINISHED_KG + SECONDARY_KG) / FINISHED_KG
    assert mine['kg_mix'] == mix and abs(mine['kg_remaining'] - round(expected, 3) * mix) < 0.01, (mine['kg_remaining'], expected, mine['kg_mix'])
    pool = mine['wip_open'] + mine['cost_month']
    assert abs(mine['absorbed'] - pool * mine['kg_harvested'] / (mine['kg_harvested'] + mine['kg_remaining'])) <= 1, mine
    difference = mine['absorbed'] - mine['provisional']
    assert abs(mine['unsold_adjustment'] - difference * unsold['share']) <= 1, mine
    assert abs(mine['adjustment'] + mine['unsold_adjustment'] - difference) <= 0.01, mine
    assert abs(mine['wip_close'] - (pool - mine['provisional'] - mine['adjustment'])) <= 0.01, mine

    # A month already over: the sổ lô lines dated up to its last day count whenever they were confirmed (the cut entered
    # today, dated 70 days back, is in; today's harvest is not), and what is still due comes in from the next day. An
    # accountant without farm scope gets the same figures.
    last_month_end = getdate(add_days(start, -1))
    blocks = block_forecast._bunch_scope(FARM)
    dated = [x for x in block_forecast._bunch_lines(FARM, blocks) if getdate(x.event_date) <= last_month_end]
    assert cut.name in {x.name for x in dated} and harvest.name not in {x.name for x in dated}, 'lines by work day, not by confirmation'
    frozen = rules.remaining_kg(block_forecast._bunch_cohorts(FARM, blocks, block_forecast._projection(FARM)[0]['rows'], dated,
                                                              start=add_days(last_month_end, 1)), last_month_end)
    assert costing._forecast_kg(FARM, last_month_end) == frozen
    accountant = 'gia-thanh-%s@example.com' % tag
    frappe.get_doc(dict(doctype='User', email=accountant, first_name='Kế toán thử ' + tag, send_welcome_email=0, enabled=1,
                        roles=[dict(role=setup.ACCOUNTANT)])).insert(ignore_permissions=True)
    frappe.set_user(accountant)
    try:
        refused(block_forecast.bunch_summary, FARM, kind=frappe.PermissionError)
    finally:
        frappe.set_user('Administrator')
    assert as_user(accountant, costing._forecast_kg, FARM, last_month_end) == frozen
    theirs = as_user(accountant, costing.preview, month)
    assert theirs['rows'] == view['rows'] and theirs['totals'] == view['totals'], 'a cost is the same whoever computes it'

    # 6. The run: sheet, adjustment voucher, and the ledger the sheet closes on --------------------------------
    done = costing.run(month)
    sheet = frappe.get_doc(costing.RUN, done['run'])
    row = next(r for r in sheet.rows if r.lotus_farm_block == block.name)
    assert flt(row.cost_per_kg) == round(flt(row.absorbed) / (FINISHED_KG + SECONDARY_KG), 2), row.as_dict()
    assert cint(row.cycle_no) == cint(mine['cycle_no']) and abs(flt(row.unsold_adjustment) - mine['unsold_adjustment']) <= 1, row.as_dict()
    assert not costing.out_of_date(company, month), 'the sheet matches the receipts it costed'
    assert bool(done['voucher']) == any(abs(r['adjustment']) >= 0.01 for r in view['rows']), done
    if done['voucher']:
        adj = gl(done['voucher'])
        assert abs(sum(flt(x.debit) for x in adj) - sum(flt(x.credit) for x in adj)) < 1
        to_cogs = sum(flt(x.debit) - flt(x.credit) for x in adj if x.account == m['cost_of_goods_sold'] and x.lotus_farm_block == block.name)
        assert abs(to_cogs - mine['adjustment']) < 1, (to_cogs, mine['adjustment'])
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

    # 7. The tree-count waves run over a window that starts in the month of the farm's earliest estimated flowering date.
    #    A lô whose date was never moved on ends it before one crop pipeline after the month: the costing is refused, not
    #    run on a forecast cut short, and names that lô.
    stale = frappe.db.sql("""select name, block_code from `tabFarm Block` where farm=%s and active=1 and lotus_tree_count > 0
        and lotus_estimated_flowering_date is not null order by lotus_estimated_flowering_date, block_code limit 1""", FARM, as_dict=True)[0]
    frappe.db.set_value('Farm Block', stale.name, 'lotus_estimated_flowering_date', months_after(start, -36))
    try:
        costing.preview(month)
        raise AssertionError('a forecast that stops before one crop pipeline must refuse the costing')
    except frappe.ValidationError as exc:
        message = unicodedata.normalize('NFC', str(exc))
        frappe.clear_messages()
    assert 'Trổ dự kiến' in message and message.rsplit('(', 1)[1].split(')')[0].split(', ') == [stale.block_code or stale.name], message
    report.update(receipt=received, unsold=unsold, run=done, lot=dict(
        block=block.block_code, kg=row.kg_harvested, kg_remaining=row.kg_remaining, absorbed=row.absorbed, per_kg=row.cost_per_kg, adjustment=row.adjustment,
        unsold_adjustment=row.unsold_adjustment, wip_close=row.wip_close), rollback=True)
finally:
    frappe.set_user('Administrator')
    frappe.db.rollback()
print(json.dumps(report, ensure_ascii=False, default=str))
