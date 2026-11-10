"""Tài chính – Kế toán: giá thành chuối (Thông tư 99, 621/622/627 → 154 → 155).

1. A closed packhouse shift enters stock through receive_shift, as a draft Material Receipt the accountant reviews and
   the warehouse submits: finished and secondary kg per source lô, valued at kg brought in × the lô's provisional cost
   per kg (its last actual cost, else the planned cost in the settings): Nợ 155 / Có 154 of that lô. Until the receipt
   is submitted the shift still waits in Chờ hạch toán, and its month can be neither costed nor closed (waiting).
2. At month end, after the 621/622/627 → 154 transfer, run() costs each lot's harvest: (work in progress at the start +
   costs of the month) × kg received / (kg received + kg the shared forecast still expects from the lot over one crop
   pipeline, put on the basis of the kg received). A lot the forecast expects nothing more from gives all its cost to
   the month's harvest. Farm costs without a lot (crews, packing, overheads) form a farm pool costed the same way on the
   farm's kg. The difference with the provisional rate goes to cost of goods sold (632) for the fruit that left stock;
   the part of the fruit still in stock when the month ends stays in 154 on the lot (rules.costing_rows).
"""
import calendar
from contextlib import contextmanager

import frappe
from frappe.utils import flt, getdate

from lotus_farm import lot_ledger_rules as ledger
from lotus_farm.finance import posting, rules, setup

RUN, ROW = 'Lotus Costing Run', 'Lotus Costing Row'


def _bounds(month):
    year, mon = (int(x) for x in str(month).split('-')[:2])
    return '%04d-%02d-01' % (year, mon), '%04d-%02d-%02d' % (year, mon, calendar.monthrange(year, mon)[1])


def _last_cost(block):
    rows = frappe.db.sql("""select r.cost_per_kg from `tabLotus Costing Row` r join `tabLotus Costing Run` p on p.name=r.parent
        where p.state='Posted' and r.lotus_farm_block=%s and r.cost_per_kg > 0 order by p.month desc limit 1""", block)
    return flt(rows[0][0]) if rows else None


def _receipts(company):
    return frappe.get_all('Stock Entry', filters={'company': company, 'docstatus': 1, 'lotus_receipt_reason': 'Harvest'}, pluck='name') \
        if frappe.get_meta('Stock Entry').has_field('lotus_receipt_reason') else []


def waiting(company, month):
    """The month's packhouse output not in stock yet: closed shifts dated in the month (from the cutover) without a
    receipt, and harvest receipts dated in the month still in draft. Costing and closing the month wait for both."""
    start, end = _bounds(month)
    cutover = setup.settings().cutover_date
    since = max(start, str(cutover)) if cutover else start
    shifts = frappe.db.sql("""select p.name from `tabPackhouse Shift` p left join `tabStock Entry` e on e.name=p.stock_entry and e.docstatus < 2
        where p.docstatus=1 and p.company=%s and p.posting_date between %s and %s and e.name is null order by p.posting_date, p.name""",
                           (company, since, end), pluck=True)
    drafts = frappe.get_all('Stock Entry', filters={'company': company, 'docstatus': 0, 'lotus_receipt_reason': 'Harvest',
                                                    'posting_date': ['between', [start, end]]}, pluck='name', order_by='posting_date asc, name asc') \
        if frappe.get_meta('Stock Entry').has_field('lotus_receipt_reason') else []
    return dict(shifts=list(shifts), drafts=list(drafts))


def waiting_text(left):
    """What waiting() found, for a message: '' when nothing waits."""
    parts = []
    if left['shifts']:
        parts.append('%d ca đóng gói đã đóng chưa lập phiếu nhập kho' % len(left['shifts']))
    if left['drafts']:
        parts.append('%d phiếu nhập kho thành phẩm còn nháp (%s)' % (len(left['drafts']), ', '.join(left['drafts'][:5]) + (', …' if len(left['drafts']) > 5 else '')))
    return ', '.join(parts)


def out_of_date(company, month):
    """A posted costing sheet of the month that no longer matches its harvest receipts: the kg of some lô differ because
    a receipt dated in the month was submitted or cancelled after the run."""
    run = frappe.db.get_value(RUN, {'company': company, 'month': month, 'state': 'Posted'})
    if not run:
        return False
    start, end = _bounds(month)
    costed = dict(frappe.db.sql("""select lotus_farm_block, sum(kg_harvested) from `tabLotus Costing Row` where parenttype=%s and parent=%s
        and ifnull(lotus_farm_block, '')!='' group by lotus_farm_block""", (RUN, run)))
    received = dict(frappe.db.sql("""select d.lotus_farm_block, sum(d.transfer_qty) from `tabStock Entry Detail` d join `tabStock Entry` e on e.name=d.parent
        where e.name in %s and e.posting_date between %s and %s and ifnull(d.lotus_farm_block, '')!='' group by d.lotus_farm_block""",
                                  (tuple(_receipts(company)) or ('',), start, end)))
    return any(round(flt(costed.get(b)) - flt(received.get(b)), 3) for b in set(costed) | set(received))


@frappe.whitelist(methods=['POST'])
def receive_shift(shift, posting_date=None):
    """Draft finished-goods receipt of a closed packhouse shift, for the accountant to review and submit. Each source lô
    hands over kg brought in × its provisional cost per kg, shared between its finished and secondary kg."""
    setup._login()
    if not setup.can_post():
        frappe.throw('Chỉ kế toán lập phiếu nhập kho thành phẩm.', frappe.PermissionError)
    cfg = setup.require_enabled()
    if not (cfg.get('packed_item') and cfg.get('packed_warehouse')):
        frappe.throw('Chọn "Chuối thành phẩm" và "Kho thành phẩm" ở Tài chính – Kế toán › Thiết lập trước khi nhập kho theo ca.')
    from lotus_farm import packout_rules
    from lotus_farm.controls import lock
    lock('Packhouse Shift', shift)
    doc = frappe.get_doc('Packhouse Shift', shift, for_update=True)  # read after the lock: a second caller sees the first receipt
    if doc.docstatus != 1:
        frappe.throw('Ca %s chưa đóng.' % doc.name)
    existing = frappe.db.get_value('Stock Entry', {'lotus_packhouse_shift': doc.name, 'docstatus': ['<', 2]}, 'name')
    if existing:
        frappe.throw('Ca %s đã có phiếu nhập kho %s.' % (doc.name, existing))
    setup.check_fruit_item(cfg.packed_item, 'Chuối thành phẩm')
    if flt(doc.secondary_kg) > 0 and cfg.get('secondary_item'):
        setup.check_fruit_item(cfg.secondary_item, 'Chuối phụ phẩm')
    if flt(doc.secondary_kg) > 0 and not cfg.get('secondary_item'):
        frappe.throw('Ca có phụ phẩm: chọn "Chuối phụ phẩm" ở Tài chính – Kế toán › Thiết lập.')
    posting_date = posting_date or str(doc.posting_date)
    setup.check_cutover(posting_date)
    posting.check_open(doc.company, posting_date, 'Stock Entry')
    m = setup.mapping(cfg)
    _finished_account(cfg.packed_warehouse, m)
    sources = [dict(farm_block=s.farm_block, bunch_tag=s.bunch_tag, bunches=s.bunches, kg=s.kg) for s in doc.sources]
    split = packout_rules.split(sources, doc.finished_kg, doc.secondary_kg, doc.cartons)
    last = {b: _last_cost(b) for b in {s['farm_block'] for s in sources}}
    rates = {b: rules.provisional_rate(cost, cfg.get('harvest_standard_cost')) for b, cost in last.items()}
    lines, missing = packout_rules.receipt_rows(split, rates, per_packed={b for b, cost in last.items() if cost})
    if missing:
        codes = [frappe.db.get_value('Farm Block', b, 'block_code') or b for b in missing]
        frappe.throw('Chưa có giá tạm tính cho lô %s: nhập "Giá thành kế hoạch chuối thu hoạch" ở Tài chính – Kế toán › Thiết lập.' % ', '.join(codes))
    if not lines:
        frappe.throw('Ca không có kg thành phẩm hay phụ phẩm để nhập kho.')
    cost_center = frappe.get_cached_value('Company', doc.company, 'cost_center')
    items = {'finished': cfg.packed_item, 'secondary': cfg.get('secondary_item')}
    rows = []
    for line in lines:
        item = items[line['kind']]
        uom = frappe.db.get_value('Item', item, 'stock_uom')
        rows.append(dict(item_code=item, qty=line['qty'], uom=uom, stock_uom=uom, conversion_factor=1, t_warehouse=cfg.packed_warehouse,
                         basic_rate=line['rate'], set_basic_rate_manually=1, expense_account=m['production_cost'], cost_center=cost_center,
                         lotus_farm=doc.farm, lotus_farm_block=line['farm_block']))
    se = frappe.get_doc(dict(doctype='Stock Entry', company=doc.company, stock_entry_type='Material Receipt', purpose='Material Receipt',
                             posting_date=posting_date, set_posting_time=1, lotus_receipt_reason='Harvest', lotus_packhouse_shift=doc.name,
                             remarks='Nhập kho thành phẩm ca đóng gói %s ngày %s' % (doc.shift_code, getdate(doc.posting_date).strftime('%d/%m/%Y')),
                             items=rows))
    se.flags.ignore_permissions = True
    se.insert()
    doc.db_set('stock_entry', se.name)
    return dict(stock_entry=se.name, kg=round(sum(r['qty'] for r in rows), 3), amount=round(sum(l['value'] for l in lines), 2), docstatus=se.docstatus)


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


@contextmanager
def _whole_farm():
    """Read as the system, not as the accountant: accountants hold no farm scope, and a cost must be the same whoever
    computes it. Only reads may run inside."""
    user = frappe.session.user
    frappe.session.user = 'Administrator'
    frappe.local.user_perms = None
    try:
        yield
    finally:
        frappe.session.user = user
        frappe.local.user_perms = None


def _forecast_kg(farm, end):
    """kg of finished fruit the shared forecast (Dự thu) still expects from each lô of a farm after the month: every
    bunch due after its last day, day by day, up to one crop pipeline later (rules.remaining_kg). The sổ lô counts by the
    work day of its lines, as it stands when the costing runs: what was harvested up to the last day is no longer
    expected, whenever it was confirmed, and what is still due comes in from the next day, or from today while the month
    is still running (block_forecast.bunches_after). A preview or run after a correction of the sổ lô, of the parameter
    sets or of the tree counts uses the corrected figures. The tree-count forecast covers a window that starts in the
    month of the farm's earliest estimated flowering date: when it ends before the last day read, the costing is refused
    (rules.forecast_gap) and names the lô whose date holds the window back, rather than run on a forecast cut short."""
    from lotus_farm import block_forecast
    with _whole_farm():
        cohorts, reach = block_forecast.bunches_after(farm, end)
    gap = rules.forecast_gap(end, reach)
    if gap:
        until, need, last, start = (getdate(d).strftime('%d/%m/%Y') for d in (gap['until'], gap['need'], end, gap['start']))
        lots = ', '.join(gap['blocks'][:10]) + (', …' if len(gap['blocks']) > 10 else '')
        frappe.throw('Chưa tính được giá thành: dự thu theo số cây của vườn %s chỉ tính tới %s, vì khung dự thu bắt đầu từ tháng trổ dự kiến sớm nhất '
                     'của các lô; giá thành cần dự thu tới %s (hết một vòng cây sau ngày %s). Ở Vườn & lô, cập nhật Trổ dự kiến theo vụ đang trồng '
                     '(cùng Vụ hiện tại) cho các lô có Trổ dự kiến trước %s (%s), rồi tính lại.' % (farm, until, need, last, start, lots))
    return rules.remaining_kg(cohorts, end)


def _pools(company, month):
    start, end = _bounds(month)
    m = setup.mapping()
    wip = m['production_cost']
    receipts = tuple(_receipts(company)) or ('',)
    costing = tuple(v for v in frappe.get_all(RUN, filters={'company': company, 'state': 'Posted'}, pluck='voucher') if v) or ('',)
    pools = {}

    def pool(farm, block):
        return pools.setdefault(_key(farm, block), dict(lotus_farm=farm, lotus_farm_block=block or None, wip_open=0, cost_month=0,
                                                         provisional=0, kg_harvested=0, kg_finished=0, kg_remaining=0, kg_mix=1.0))
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
    # kg received: finished + secondary; the finished part is what the forecast counts.
    kg_by_farm, finished_by_farm = {}, {}
    for r in frappe.db.sql("""select d.lotus_farm, d.lotus_farm_block, sum(d.transfer_qty) kg,
            sum(case when d.item_code=%s then d.transfer_qty else 0 end) finished from `tabStock Entry Detail` d
            join `tabStock Entry` e on e.name=d.parent where e.name in %s and e.posting_date between %s and %s
            group by d.lotus_farm, d.lotus_farm_block""", (setup.settings().get('packed_item') or '', receipts, start, end), as_dict=True):
        p = pool(r.lotus_farm, r.lotus_farm_block)
        p['kg_harvested'] += flt(r.kg)
        p['kg_finished'] += flt(r.finished)
        kg_by_farm[r.lotus_farm] = kg_by_farm.get(r.lotus_farm, 0) + flt(r.kg)
        finished_by_farm[r.lotus_farm] = finished_by_farm.get(r.lotus_farm, 0) + flt(r.finished)
    # The forecast only matters where fruit came in: without kg received a pool keeps all its cost in progress.
    remaining = {}
    for farm in sorted(f for f in kg_by_farm if f):
        by_block = _forecast_kg(farm, end)
        remaining.update({_key(farm, block): kg for block, kg in by_block.items()})
        remaining[_key(farm, None)] = sum(by_block.values())
    for k, p in pools.items():
        farm = p['lotus_farm']
        if not p['lotus_farm_block']:
            p['kg_harvested'], p['kg_finished'] = kg_by_farm.get(farm, 0), finished_by_farm.get(farm, 0)
        # The forecast's finished kg on the basis of the kg received: the pool's own mix of the month, else its farm's.
        p['kg_mix'] = rules.kg_mix((p['kg_harvested'], p['kg_finished']), (kg_by_farm.get(farm, 0), finished_by_farm.get(farm, 0)))
        p['kg_remaining'] = round(remaining.get(k, 0) * p['kg_mix'], 3)
    return [p for p in pools.values() if any(abs(p[f]) > .005 for f in ('wip_open', 'cost_month', 'provisional')) or p['kg_harvested']]


def _unsold(company, month):
    """How much of the month's harvest receipts is still in stock when the month ends, by kg. Fruit carries no batch, so
    what is left of an item across every warehouse is taken to be its newest receipts (first in, first out): at most
    the kg received this month."""
    start, end = _bounds(month)
    receipts = _receipts(company)
    received = frappe.db.sql("""select d.item_code, sum(d.transfer_qty) kg from `tabStock Entry Detail` d
        join `tabStock Entry` e on e.name=d.parent where d.parent in %s and e.posting_date between %s and %s
        and d.t_warehouse is not null group by d.item_code""", (tuple(receipts), start, end), as_dict=True) if receipts else []
    kg_received = kg_unsold = 0
    for r in received:
        left = flt(frappe.db.sql("""select sum(actual_qty) from `tabStock Ledger Entry` where company=%s and item_code=%s
            and posting_date<=%s and is_cancelled=0""", (company, r.item_code, end))[0][0])
        kg_received += flt(r.kg)
        kg_unsold += min(max(left, 0), flt(r.kg))
    return dict(kg_received=round(kg_received, 3), kg_unsold=round(kg_unsold, 3),
                share=round(kg_unsold / kg_received, 6) if kg_received > 0 else 0)


def _cycles(month, blocks):
    """{lô: the vụ of the fruit it harvested in the month}, from its confirmed harvest lines dated in the month."""
    if not blocks:
        return {}
    from lotus_farm.lot_ledger import bunch_rows
    start, end = _bounds(month)
    return rules.harvest_cycles(bunch_rows({'event_type': ledger.HARVEST, 'state': ledger.CONFIRMED, 'farm_block': ['in', sorted(blocks)],
                                            'event_date': ['between', [start, end]]}, ['farm_block', 'cycle_no', 'qty']))


@frappe.whitelist()
def preview(month):
    setup.require_view()
    company = setup.company()
    unsold = _unsold(company, month)
    rows = rules.costing_rows(_pools(company, month), unsold['share'])
    names = {r['lotus_farm_block'] for r in rows if r['lotus_farm_block']}
    codes = {b.name: b.block_code for b in frappe.get_all('Farm Block', filters={'name': ['in', sorted(names) or ['']]}, fields=['name', 'block_code'])}
    cycles = _cycles(month, names)
    for r in rows:
        r['label'] = codes.get(r['lotus_farm_block']) or ('Chi phí chung vườn ' + str(r['lotus_farm'] or ''))
        r['cycle_no'] = cycles.get(r['lotus_farm_block'])
    rows.sort(key=lambda r: (r['lotus_farm'] or '', r['lotus_farm_block'] is None, r['label']))
    lines = rules.costing_entry(rows, setup.mapping())
    done = posting.active('Lotus Finance Settings', setup.SETTINGS, 'Costing', month)
    sheet = frappe.db.get_value(RUN, {'company': company, 'month': month, 'state': 'Posted'})
    totals = {k: sum(flt(r[k]) for r in rows) for k in ('wip_open', 'cost_month', 'provisional', 'kg_harvested', 'absorbed', 'adjustment',
                                                         'unsold_adjustment', 'wip_close')}
    # The farm pool row carries its farm's whole kg (it shares the farm's costs over them), the lô rows carry the same kg
    # again: count a farm's kg once.
    pooled = {r['lotus_farm'] for r in rows if not r['lotus_farm_block']}
    totals['kg_harvested'] = sum(flt(r['kg_harvested']) for r in rows if not r['lotus_farm_block'] or r['lotus_farm'] not in pooled)
    left = waiting(company, month)
    return dict(month=month, posting_date=_bounds(month)[1], rows=rows, lines=lines, unsold=unsold, totals=totals,
                waiting=dict(left, text=waiting_text(left)), out_of_date=out_of_date(company, month),
                closed=bool(posting.active('Lotus Finance Settings', setup.SETTINGS, 'Cost Closing', month)),
                posted=dict(voucher=done.voucher_name if done else None, posting=done.name if done else None, run=sheet) if (done or sheet) else None,
                runs=frappe.get_all(RUN, filters={'company': company}, fields=['name', 'month', 'state', 'voucher', 'kg_harvested', 'absorbed', 'adjustment'],
                                    order_by='month desc', limit_page_length=24))


@frappe.whitelist(methods=['POST'])
def run(month):
    """Post the month's costing (chief accountant), after the cost transfer to 154 and before locking the month."""
    setup.require_chief()
    setup.require_enabled()
    from lotus_farm.finance.assets import ensure_settled
    ensure_settled(month)
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
    left = waiting_text(waiting(company, month))
    if left:
        frappe.throw('Tháng %s còn %s. Lập phiếu nhập kho ở Chờ hạch toán và để Kho duyệt (hoặc xóa phiếu nháp sai) trước khi tính giá thành.' % (month, left))
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
                              rows=[{f: r.get(f) for f in ('lotus_farm', 'lotus_farm_block', 'cycle_no', 'wip_open', 'cost_month', 'provisional', 'kg_harvested',
                                                           'kg_remaining', 'absorbed', 'adjustment', 'unsold_adjustment', 'wip_close', 'cost_per_kg',
                                                           'basis')} for r in result['rows']]))
    doc.flags.ignore_permissions = True
    doc.insert()
    return dict(run=doc.name, voucher=voucher, absorbed=t['absorbed'], adjustment=t['adjustment'])


def costing_reversed(doc, method=None):
    """Journal Entry on_cancel: a reversed costing voucher marks its month's sheet Reversed."""
    if doc.doctype == 'Journal Entry':
        for name in frappe.get_all(RUN, filters={'voucher': doc.name, 'state': 'Posted'}, pluck='name'):
            frappe.db.set_value(RUN, name, 'state', 'Reversed')
