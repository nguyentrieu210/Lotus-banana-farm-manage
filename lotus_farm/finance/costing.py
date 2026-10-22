"""Tài chính – Kế toán: giá thành chuối (Thông tư 99, 621/622/627 → 154 → 155).

1. A submitted Harvest Lot enters stock through receive_harvest: one Material Receipt row per harvest source (lot), at a
   provisional cost per kg (the lot's last actual cost, else the planned cost in the settings): Nợ 155 / Có 154 on that
   lot. This replaces the hand-made receipt in Desk.
2. At month end, after the 621/622/627 → 154 transfer, run() costs each lot's harvest: (work in progress at the start +
   costs of the month) × kg harvested / (kg harvested + kg still expected from the lot's forecast). Farm costs without a
   lot (crews, packing, overheads) form a farm pool costed the same way on the farm's kg. The difference with the
   provisional rate goes to cost of goods sold (632) — bananas are sold within days — and the month's sheet is kept.
"""
import calendar

import frappe
from frappe.utils import flt, getdate, now_datetime, nowdate

from lotus_farm.finance import posting, rules, setup

RUN, ROW = 'Lotus Costing Run', 'Lotus Costing Row'
STOCK_ROLES = ('Lotus Warehouse Manager', 'Lotus Warehouse Receiver', 'Stock Manager', 'Lotus Packing Supervisor')
OPEN_FORECAST = ('Draft', 'Released')


def _bounds(month):
    year, mon = (int(x) for x in str(month).split('-')[:2])
    return '%04d-%02d-01' % (year, mon), '%04d-%02d-%02d' % (year, mon, calendar.monthrange(year, mon)[1])


def _may_receive():
    setup._login()
    if not (setup.can_post() or set(STOCK_ROLES) & set(frappe.get_roles())):
        frappe.throw('Chỉ kho, xưởng đóng gói hoặc kế toán được nhập kho lô thu hoạch.', frappe.PermissionError)


def _last_cost(block):
    rows = frappe.db.sql("""select r.cost_per_kg from `tabLotus Costing Row` r join `tabLotus Costing Run` p on p.name=r.parent
        where p.state='Posted' and r.lotus_farm_block=%s and r.cost_per_kg > 0 order by p.month desc limit 1""", block)
    return flt(rows[0][0]) if rows else None


def _receipts(company):
    return frappe.get_all('Stock Entry', filters={'company': company, 'docstatus': 1, 'lotus_receipt_reason': 'Harvest'}, pluck='name') \
        if frappe.get_meta('Stock Entry').has_field('lotus_harvest_lot') else []


@frappe.whitelist()
def lots_to_receive():
    """Submitted harvest lots whose fruit is not in stock yet."""
    setup._login()
    company = setup.company()
    done = set(frappe.get_all('Stock Entry', filters={'docstatus': 1, 'lotus_harvest_lot': ['is', 'set']}, pluck='lotus_harvest_lot')) \
        if frappe.get_meta('Stock Entry').has_field('lotus_harvest_lot') else set()
    out = []
    for lot in frappe.get_all('Harvest Lot', filters={'docstatus': 1, 'company': company}, fields=['name', 'farm', 'received_date', 'released_raw_kg',
                                                                                                    'raw_item', 'raw_warehouse', 'raw_batch'],
                              order_by='received_date desc', limit_page_length=300):
        if lot.name not in done:
            out.append(dict(lot, received_date=str(lot.received_date or ''), kind='harvest',
                            reason='Lô thu hoạch chưa nhập kho' + ('' if lot.raw_item and lot.raw_warehouse and lot.raw_batch else ' (thiếu vật tư / kho / batch)')))
    return out


@frappe.whitelist(methods=['POST'])
def receive_harvest(harvest_lot, posting_date=None):
    """Material Receipt of a harvest lot at the provisional cost per kg of each source lot (Nợ 155 / Có 154 of that lot)."""
    _may_receive()
    cfg = setup.require_enabled()
    lot = frappe.get_doc('Harvest Lot', harvest_lot)
    if lot.docstatus != 1:
        frappe.throw('Lô thu hoạch %s chưa hoàn tất.' % lot.name)
    if not (lot.raw_item and lot.raw_warehouse and lot.raw_batch):
        frappe.throw('Lô thu hoạch %s chưa có vật tư, kho hoặc batch nhận chuối.' % lot.name)
    from lotus_farm.controls import lock
    lock('Harvest Lot', lot.name)
    if frappe.db.exists('Stock Entry', {'lotus_harvest_lot': lot.name, 'docstatus': 1}):
        frappe.throw('Lô thu hoạch %s đã nhập kho.' % lot.name)
    posting_date = posting_date or str(lot.received_date or nowdate())
    setup.check_cutover(posting_date)
    posting.check_open(lot.company, posting_date, 'Stock Entry')
    m = setup.mapping(cfg)
    _finished_account(lot.raw_warehouse, m)
    cost_center = frappe.get_cached_value('Company', lot.company, 'cost_center')
    stock_uom = frappe.db.get_value('Item', lot.raw_item, 'stock_uom')
    rows, missing = [], []
    for s in lot.sources:
        if not flt(s.contributed_kg):
            continue
        actual = frappe.db.get_value('Harvest Actual', s.harvest_actual, ['farm', 'farm_block', 'crop_cycle'], as_dict=True)
        rate = rules.provisional_rate(_last_cost(actual.farm_block), cfg.get('harvest_standard_cost'))
        if not rate:
            missing.append(actual.farm_block)
            continue
        rows.append(dict(item_code=lot.raw_item, qty=flt(s.contributed_kg), uom=stock_uom, stock_uom=stock_uom, conversion_factor=1, t_warehouse=lot.raw_warehouse,
                         batch_no=lot.raw_batch, use_serial_batch_fields=1, basic_rate=rate, set_basic_rate_manually=1,
                         expense_account=m['production_cost'], cost_center=cost_center,
                         lotus_farm=actual.farm, lotus_farm_block=actual.farm_block, lotus_crop_cycle=actual.crop_cycle))
    if missing:
        frappe.throw('Chưa có giá tạm tính cho lô %s: nhập "Giá thành kế hoạch chuối thu hoạch" ở Tài chính – Kế toán › Thiết lập.' % ', '.join(sorted({str(b) for b in missing})))
    if not rows:
        frappe.throw('Lô thu hoạch không có kg để nhập kho.')
    se = frappe.get_doc(dict(doctype='Stock Entry', company=lot.company, stock_entry_type='Material Receipt', purpose='Material Receipt', posting_date=posting_date,
                             set_posting_time=1, lotus_receipt_reason='Harvest', lotus_harvest_lot=lot.name,
                             remarks='Nhập kho chuối thu hoạch ' + lot.name, items=rows))
    se.flags.ignore_permissions = True
    se.insert()
    se.submit()
    posting.record('Harvest Lot', lot.name, 'Harvest Receipt', se, amount=se.total_incoming_value, source_hash=lot.name)
    return dict(stock_entry=se.name, kg=sum(r['qty'] for r in rows), amount=se.total_incoming_value)


def _finished_account(warehouse, m):
    """The fruit warehouse posts to 155 (Sản phẩm). A warehouse still on the materials account with no stock value is moved;
    one holding value must be moved by the chief accountant (it would need a transfer journal)."""
    current = frappe.db.get_value('Warehouse', warehouse, 'account') or frappe.get_cached_value('Company', frappe.db.get_value('Warehouse', warehouse, 'company'),
                                                                                                'default_inventory_account')
    if current == m['finished_goods']:
        return
    value = flt(frappe.db.sql("select sum(stock_value_difference) from `tabStock Ledger Entry` where warehouse=%s and is_cancelled=0", warehouse)[0][0])
    if abs(value) > 0.5:
        frappe.throw('Kho %s đang ghi vào %s và còn giá trị %s. Kế toán trưởng chuyển kho này sang TK 155 trước khi nhập chuối.' % (
            warehouse, current, format(round(value), ',').replace(',', '.')))
    frappe.db.set_value('Warehouse', warehouse, 'account', m['finished_goods'])
    frappe.flags.pop('warehouse_account_map', None)


# Month-end costing -------------------------------------------------------------------------------------

def _key(farm, block):
    return (farm or '', block or '')


def _pools(company, month):
    start, end = _bounds(month)
    m = setup.mapping()
    wip = m['production_cost']
    receipts = tuple(_receipts(company)) or ('',)
    costing = tuple(v for v in frappe.get_all(RUN, filters={'company': company, 'state': 'Posted'}, pluck='voucher') if v) or ('',)
    pools = {}

    def pool(farm, block):
        return pools.setdefault(_key(farm, block), dict(lotus_farm=farm, lotus_farm_block=block or None, lotus_crop_cycle=None, wip_open=0, cost_month=0,
                                                         provisional=0, kg_harvested=0, kg_remaining=0))
    for r in frappe.db.sql("""select lotus_farm, lotus_farm_block, sum(debit-credit) v from `tabGL Entry` where company=%s and is_cancelled=0
            and account=%s and posting_date < %s group by lotus_farm, lotus_farm_block""", (company, wip, start), as_dict=True):
        pool(r.lotus_farm, r.lotus_farm_block)['wip_open'] += flt(r.v)
    for r in frappe.db.sql("""select lotus_farm, lotus_farm_block, voucher_no in %s harvest, sum(debit-credit) v from `tabGL Entry`
            where company=%s and is_cancelled=0 and account=%s and posting_date between %s and %s and voucher_no not in %s
            group by lotus_farm, lotus_farm_block, voucher_no in %s""", (receipts, company, wip, start, end, costing, receipts), as_dict=True):
        p = pool(r.lotus_farm, r.lotus_farm_block)
        if r.harvest:
            p['provisional'] += -flt(r.v)
        else:
            p['cost_month'] += flt(r.v)
    kg_by_farm = {}
    for r in frappe.db.sql("""select d.lotus_farm, d.lotus_farm_block, max(d.lotus_crop_cycle) cycle, sum(d.transfer_qty) kg from `tabStock Entry Detail` d
            join `tabStock Entry` e on e.name=d.parent where e.name in %s and e.posting_date between %s and %s
            group by d.lotus_farm, d.lotus_farm_block""", (receipts, start, end), as_dict=True):
        p = pool(r.lotus_farm, r.lotus_farm_block)
        p['kg_harvested'] += flt(r.kg)
        p['lotus_crop_cycle'] = r.cycle
        kg_by_farm[r.lotus_farm] = kg_by_farm.get(r.lotus_farm, 0) + flt(r.kg)
    remaining = {}
    for r in frappe.db.sql("""select farm, farm_block, sum(gross_forecast_kg) kg from `tabHarvest Forecast` where docstatus < 2 and supply_state in %s
            and period_start_date > %s group by farm, farm_block""", (OPEN_FORECAST, end), as_dict=True):
        remaining[_key(r.farm, r.farm_block)] = flt(r.kg)
        remaining[_key(r.farm, None)] = remaining.get(_key(r.farm, None), 0) + flt(r.kg)
    for k, p in pools.items():
        if not p['lotus_farm_block']:
            p['kg_harvested'] = kg_by_farm.get(p['lotus_farm'], 0)
        closed = p['lotus_crop_cycle'] and frappe.db.get_value('Crop Cycle', p['lotus_crop_cycle'], 'status') == 'Closed'
        p['kg_remaining'] = 0 if closed else remaining.get(k, 0)
    return [p for p in pools.values() if any(round(p[f]) for f in ('wip_open', 'cost_month', 'provisional')) or p['kg_harvested']]


@frappe.whitelist()
def preview(month):
    setup.require_view()
    company = setup.company()
    rows = rules.costing_rows(_pools(company, month))
    labels = {b.name: b.block_code for b in frappe.get_all('Farm Block', filters={'name': ['in', [r['lotus_farm_block'] for r in rows if r['lotus_farm_block']] or ['']]},
                                                           fields=['name', 'block_code'])}
    for r in rows:
        r['label'] = labels.get(r['lotus_farm_block']) or ('Chi phí chung vườn ' + str(r['lotus_farm'] or ''))
    rows.sort(key=lambda r: (r['lotus_farm'] or '', r['lotus_farm_block'] is None, r['label']))
    lines = rules.costing_entry(rows, setup.mapping())
    done = posting.active('Lotus Finance Settings', setup.SETTINGS, 'Costing', month)
    sheet = frappe.db.get_value(RUN, {'company': company, 'month': month, 'state': 'Posted'})
    totals = {k: sum(flt(r[k]) for r in rows) for k in ('wip_open', 'cost_month', 'provisional', 'kg_harvested', 'absorbed', 'adjustment', 'wip_close')}
    return dict(month=month, posting_date=_bounds(month)[1], rows=rows, lines=lines, totals=totals,
                closed=bool(posting.active('Lotus Finance Settings', setup.SETTINGS, 'Cost Closing', month)),
                posted=dict(voucher=done.voucher_name if done else None, posting=done.name if done else None, run=sheet) if (done or sheet) else None,
                runs=frappe.get_all(RUN, filters={'company': company}, fields=['name', 'month', 'state', 'voucher', 'kg_harvested', 'absorbed', 'adjustment'],
                                    order_by='month desc', limit_page_length=24))


@frappe.whitelist(methods=['POST'])
def run(month):
    """Post the month's costing (chief accountant), after the cost transfer to 154 and before locking the month."""
    setup.require_chief()
    setup.require_enabled()
    company = setup.company()
    if posting.active('Lotus Finance Settings', setup.SETTINGS, 'Costing', month):
        frappe.throw('Tháng %s đã tính giá thành. Đảo bút toán giá thành trước nếu cần tính lại.' % month)
    from lotus_farm.finance.closing import require_no_result
    require_no_result(month)
    # a sheet without adjustment voucher left nothing in the ledger: computing again replaces it
    for name in frappe.get_all(RUN, filters={'company': company, 'month': month, 'state': 'Posted'}, pluck='name'):
        frappe.db.set_value(RUN, name, 'state', 'Reversed')
    if not posting.active('Lotus Finance Settings', setup.SETTINGS, 'Cost Closing', month):
        frappe.throw('Kết chuyển chi phí 621 / 622 / 627 sang 154 của tháng %s trước khi tính giá thành.' % month)
    result = preview(month)
    if not result['rows']:
        frappe.throw('Tháng %s không có chi phí dở dang hay sản lượng thu hoạch.' % month)
    voucher = None
    if result['lines']:
        errors = rules.check_entry(result['lines'])
        if errors:
            frappe.throw('<br>'.join(errors))
        posting.check_open(company, result['posting_date'])
        from lotus_farm.finance.payroll import journal
        je = journal(company, result['posting_date'], result['lines'], 'Giá thành chuối tháng %s: chênh lệch giá thành thực tế so với giá tạm tính' % month)
        je.submit()
        voucher = je.name
        posting.record('Lotus Finance Settings', setup.SETTINGS, 'Costing', je, amount=sum(abs(r['adjustment']) for r in result['rows']), source_hash=month,
                       key_suffix=month)
    t = result['totals']
    doc = frappe.get_doc(dict(doctype=RUN, company=company, month=month, state='Posted', voucher=voucher, kg_harvested=t['kg_harvested'],
                              absorbed=t['absorbed'], adjustment=t['adjustment'], wip_close=t['wip_close'],
                              rows=[{f: r.get(f) for f in ('lotus_farm', 'lotus_farm_block', 'lotus_crop_cycle', 'wip_open', 'cost_month', 'provisional', 'kg_harvested',
                                                           'kg_remaining', 'absorbed', 'adjustment', 'wip_close', 'cost_per_kg', 'basis')} for r in result['rows']]))
    doc.flags.ignore_permissions = True
    doc.insert()
    return dict(run=doc.name, voucher=voucher, absorbed=t['absorbed'], adjustment=t['adjustment'])


def costing_reversed(doc, method=None):
    """Journal Entry on_cancel: a reversed costing voucher marks its month's sheet Reversed."""
    if doc.doctype == 'Journal Entry':
        for name in frappe.get_all(RUN, filters={'voucher': doc.name, 'state': 'Posted'}, pluck='name'):
            frappe.db.set_value(RUN, name, 'state', 'Reversed')
