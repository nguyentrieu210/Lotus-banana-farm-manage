"""OneDrive cut evidence shared by planning, publication and physical stock."""
import json
from collections import defaultdict
from datetime import timedelta

import frappe
from frappe.utils import cint, flt, getdate
from lotus_farm.controls import command, lock, require_role, validate_item
from lotus_farm.cut_supply import window_balance, interval_quantity, overlaps
from lotus_farm.onedrive_protocol import forecast_quantities
from lotus_farm.rules import canonical_hash

FORMULA = 'lotus-onedrive/1'
CLAIM_FIELDS = ('source_cut_operation', 'process_adoption', 'window_start', 'window_end',
                'slice_start', 'slice_end', 'capacity_bunch_qty', 'source_bunch_qty', 'source_hash')


def blank_filter(value):
    return value if value else ['is', 'not set']


def adopted(farm):
    lock('Farm', farm)
    table = frappe.qb.DocType('Lotus Process Adoption')
    return bool(frappe.qb.from_(table).select(table.name).where((table.farm == farm) & (table.approval_state == 'Approved')).for_update().run())


def source_cut(name, fresh=False):
    cut = frappe.get_doc('Bunch Operation', name)
    cut.check_permission('read')
    if fresh:
        lock('Farm', cut.farm)
        lock('Crop Cycle', cut.crop_cycle)
        cut = frappe.get_doc('Bunch Operation', name, for_update=True)
        cut.check_permission('read')
    if cut.docstatus != 1 or cut.operation_type != 'Cut Bud' or not cut.bunch_tag:
        frappe.throw('Nguồn cung phải là đợt cắt bắp đã xác nhận, có màu dây.')
    tag = frappe.get_doc('Bunch Tag', cut.bunch_tag)
    tag.check_permission('read')
    if not tag.process_adoption:
        frappe.throw('Đợt cắt bắp chưa có phiên bản quy trình OneDrive.')
    adoption = frappe.get_doc('Lotus Process Adoption', tag.process_adoption)
    adoption.check_permission('read')
    if adoption.approval_state != 'Approved' or adoption.farm != cut.farm:
        frappe.throw('Phiên bản nguồn cắt bắp không hợp lệ.')
    start, end = getdate(tag.valid_from)+timedelta(days=55), getdate(tag.valid_to)+timedelta(days=70)
    events = []
    def event_rows(doctype, field, fields):
        if not fresh:
            return frappe.get_all(doctype, filters={field: cut.name, 'docstatus': 1}, fields=fields)
        table = frappe.qb.DocType(doctype)
        return (frappe.qb.from_(table).select(*(table[f] for f in fields))
                .where((table[field] == cut.name) & (table.docstatus == 1)).for_update().run(as_dict=True))
    for row in event_rows('Harvest Actual', 'source_cut_operation', ['name', 'harvest_date', 'harvested_bunch_qty', 'modified']):
        events.append(dict(key='harvest:'+row.name, date=str(row.harvest_date), quantity=float(row.harvested_bunch_qty), modified=str(row.modified)))
    for row in event_rows('Bunch Cancellation', 'source_operation', ['name', 'posting_date', 'bunch_qty', 'modified']):
        events.append(dict(key='cancel:'+row.name, date=str(row.posting_date), quantity=float(row.bunch_qty), modified=str(row.modified)))
    try:
        balance = window_balance(start, end, cut.net_bunch_qty, events)
    except ValueError as exc:
        frappe.throw(str(exc))
    params = {key: adoption.get(key) for key in ('cut_rate', 'harvest_rate', 'processed_rate', 'gross_bunch_kg', 'processed_bunch_kg')}
    params['cut_rate'] = 1
    evidence = dict(cut=cut.name, modified=str(cut.modified), net_bunch_qty=cut.net_bunch_qty,
                    farm=cut.farm, farm_block=cut.farm_block, farm_plot=cut.farm_plot,
                    crop_cycle=cut.crop_cycle, sucker_selection_batch=cut.sucker_selection_batch or '',
                    tag=tag.name, window_start=str(start), window_end=str(end),
                    process_adoption=adoption.name, source_version=adoption.source_version,
                    parameter_hash=adoption.source_hash, parameters=params,
                    events=sorted(events, key=lambda r: (r['date'], r['key'])))
    return dict(cut=cut, adoption=adoption, balance=balance, parameters=params,
                evidence=evidence, source_hash=canonical_hash(evidence))


def cut_slice(source, start, end):
    balance = source['balance']
    start, end = max(getdate(start), getdate(balance['start'])), min(getdate(end), getdate(balance['end']))
    if end < start:
        return None
    qty = interval_quantity(balance, start, end)
    share = ((end-start).days+1)/((getdate(balance['end'])-getdate(balance['start'])).days+1)
    return dict(window_start=balance['start'], window_end=balance['end'], slice_start=str(start), slice_end=str(end),
                share=share, capacity_bunch_qty=balance['capacity']*share, source_bunch_qty=qty,
                **forecast_quantities(qty, source['parameters']))


def source_rows(source):
    """Monthly remaining cut supply using the same calendar as publication."""
    cut = source['cut']
    result = []
    months = sorted({day[:7] for day in source['balance']['days']})
    for month in months:
        first = getdate(month+'-01')
        next_month = (first.replace(day=28)+timedelta(days=4)).replace(day=1)
        part = cut_slice(source, first, next_month-timedelta(days=1))
        if part['source_bunch_qty'] <= 0.00000001:
            continue
        result.append(dict(farm=cut.farm, farm_block=cut.farm_block, farm_plot=cut.farm_plot,
                           crop_cycle=cut.crop_cycle, sucker_selection_batch=cut.sucker_selection_batch or '',
                           source=cut.name, source_kind='Observed Cut', month=month,
                           process_adoption=source['adoption'].name, source_hash=source['source_hash'],
                           remaining_bunch_qty=part['source_bunch_qty'], **part))
    return result


def hydrate_draft(doc):
    if len(doc.source_claims or []) != 1:
        frappe.throw('Mỗi dự thu OneDrive phải truy về đúng một đợt cắt bắp; dùng bảng thành phẩm cho nhiều Item.')
    source = source_cut(doc.source_claims[0].source_cut_operation, fresh=True)
    cut = source['cut']
    if frappe.db.get_value('Crop Cycle', cut.crop_cycle, 'status', for_update=True) == 'Closed':
        frappe.throw('Vụ đã kết thúc; mở lại báo cáo kết vụ trước khi lập dự thu.')
    before = doc.get_doc_before_save()
    if doc.supply_state == 'Released' and before and before.supply_state == 'Draft':
        old = before.get('source_claims') or []
        if not old or old[0].source_hash != source['source_hash']:
            frappe.throw('Nguồn buồng đã đổi từ lúc lập nháp. Lưu tính lại và kiểm tra trước khi phát hành.')
    for field in ('farm', 'farm_block', 'farm_plot', 'crop_cycle', 'sucker_selection_batch'):
        if (doc.get(field) or '') != (cut.get(field) or ''):
            frappe.throw('Dự thu phải cùng phạm vi với đợt cắt bắp gốc.')
    part = cut_slice(source, doc.period_start_date, doc.period_end_date)
    if not part or part['slice_start'] != str(getdate(doc.period_start_date)) or part['slice_end'] != str(getdate(doc.period_end_date)):
        frappe.throw('Kỳ dự thu phải nằm trong cửa sổ màu dây E+55/F+70.')
    if part['source_bunch_qty'] <= 0.00000001:
        frappe.throw('Đợt cắt bắp không còn nguồn buồng trong kỳ này.')
    doc.process_adoption = source['adoption'].name
    doc.forecast_basis = 'Cut Bud Operations'
    claim = dict(source_cut_operation=cut.name, process_adoption=doc.process_adoption,
                 source_hash=source['source_hash'], **{key: part[key] for key in CLAIM_FIELDS if key in part})
    doc.set('source_claims', [claim])
    doc.source_bunch_qty = doc.net_source_bunch_qty = part['source_bunch_qty']
    doc.cancellation_bunch_qty = 0  # All submitted source losses already removed by the shared ledger.
    doc.bunch_survival_rate_percent = flt(source['parameters']['harvest_rate'])*100
    doc.avg_bunch_weight_kg = source['parameters']['gross_bunch_kg']
    doc.quality_pass_rate_percent = 100
    doc.source_snapshot = json.dumps(dict(formula=FORMULA, evidence=source['evidence'], slice=part), default=str, sort_keys=True)
    doc.formula_version = FORMULA
    if doc.safety_buffer_percent in (None, ''):
        doc.safety_buffer_percent = frappe.db.get_single_value('Lotus Farm Settings', 'safety_buffer_percent') or 0
    if not 0 <= flt(doc.safety_buffer_percent) <= 100:
        frappe.throw('Dự phòng phải từ 0 đến 100%.')
    return part


def calculate(doc):
    part = json.loads(doc.source_snapshot)['slice']
    doc.expected_harvest_bunch_qty = part['harvest_bunches']
    doc.gross_forecast_kg = doc.saleable_forecast_kg = part['gross_kg']
    if not doc.output_plan or doc.item or doc.packout_profile:
        frappe.throw('Chọn bảng thành phẩm và tỷ phần kg sơ chế được duyệt cho dự thu OneDrive.')
    for row in doc.output_plan:
        row.expected_packed_kg = flt(part['processed_kg']*flt(row.source_share_percent)/100, 3)
        row.safe_commit_kg = flt(row.expected_packed_kg*(1-flt(doc.safety_buffer_percent)/100), 3)
    doc.packed_forecast_kg = flt(sum(flt(r.expected_packed_kg) for r in doc.output_plan), 3)
    doc.safe_saleable_kg = flt(sum(flt(r.safe_commit_kg) for r in doc.output_plan), 3)
    doc.packout_rate_percent = doc.packed_forecast_kg/doc.gross_forecast_kg*100 if doc.gross_forecast_kg else 0


def remaining_fraction(doc):
    original = sum(flt(row.source_bunch_qty) for row in doc.source_claims or [])
    remaining = 0
    for row in doc.source_claims or []:
        source = source_cut(row.source_cut_operation, fresh=True)
        remaining += min(flt(row.source_bunch_qty), interval_quantity(source['balance'], row.slice_start, row.slice_end))
    return max(min(remaining/original, 1), 0) if original else 0


def assert_source_ownership(doc):
    """Claim physical date capacity across all periods, bases and Items."""
    for row in doc.source_claims:
        lock('Bunch Operation', row.source_cut_operation)
        # Locking reads see publications committed while this request waited.
        forecast = frappe.qb.DocType('Harvest Forecast')
        others = (frappe.qb.from_(forecast).select(forecast.name, forecast.sucker_selection_batch, forecast.process_adoption)
                  .where((forecast.crop_cycle == doc.crop_cycle) & (forecast.supply_state == 'Released')
                         & forecast.name.notin([doc.name or '', doc.supersedes or ''])).for_update().run(as_dict=True))
        for other in others:
            if (other.sucker_selection_batch or '') == (doc.sucker_selection_batch or '') and not other.process_adoption:
                frappe.throw('Đối soát dự thu cũ của cùng đợt sinh học trước khi phát hành theo OneDrive.')
        table = frappe.qb.DocType('Forecast Source Claim')
        claims = (frappe.qb.from_(table).join(forecast).on(table.parent == forecast.name)
                  .select(table.parent, table.slice_start, table.slice_end)
                  .where((table.source_cut_operation == row.source_cut_operation) & (table.parenttype == 'Harvest Forecast')
                         & (forecast.supply_state == 'Released') & forecast.name.notin([doc.name or '', doc.supersedes or '']))
                  .for_update().run(as_dict=True))
        for claim in claims:
            if overlaps(row.slice_start, row.slice_end, claim.slice_start, claim.slice_end):
                frappe.throw('Đợt cắt bắp đã phát hành trong kỳ này: '+claim.parent)


def _mapping(value):
    rows = frappe.parse_json(value) if isinstance(value, str) else value
    if not isinstance(rows, list) or not 1 <= len(rows) <= 30:
        frappe.throw('Cần từ 1 đến 30 dòng ánh xạ thành phẩm.')
    result = []
    for row in rows:
        if not isinstance(row, dict) or not row.get('item') or not row.get('packout_profile'):
            frappe.throw('Mỗi dòng cần Item và hồ sơ đóng gói được duyệt.')
        result.append(dict(item=row['item'], packout_profile=row['packout_profile'], source_share_percent=flt(row.get('share_percent'))))
    return result


@frappe.whitelist(methods=['POST'])
def prepare_cut_forecasts(source_cuts, period_start, period_end, output_mapping, client_event_id=None,
                          preview=1, expected_source_hash=None):
    require_role('Lotus Farm Manager')
    if not frappe.has_permission('Harvest Forecast', 'create'):
        frappe.throw('Không có quyền tạo dự thu.', frappe.PermissionError)
    names = frappe.parse_json(source_cuts) if isinstance(source_cuts, str) else source_cuts
    if not isinstance(names, list) or not 1 <= len(names) <= 50 or any(not isinstance(n, str) for n in names):
        frappe.throw('Chọn từ 1 đến 50 đợt cắt bắp.')
    names = sorted(set(names))
    outputs = _mapping(output_mapping)
    if getdate(period_end) < getdate(period_start):
        frappe.throw('Ngày kết thúc phải sau ngày bắt đầu.')
    request_hash = canonical_hash(dict(names=names, start=str(getdate(period_start)), end=str(getdate(period_end)), outputs=outputs,
                                       expected_source_hash=expected_source_hash))
    event_key = canonical_hash(['onedrive-prepare', frappe.session.user, client_event_id]) if client_event_id else None
    cuts = [frappe.get_doc('Bunch Operation', name) for name in names]
    for cut in cuts: cut.check_permission('read')
    if len({(cut.farm, cut.crop_cycle) for cut in cuts}) != 1:
        frappe.throw('Mỗi lần lập nháp chọn các đợt cắt bắp trong cùng vườn và vụ.')
    lock('Farm', cuts[0].farm)
    lock('Crop Cycle', cuts[0].crop_cycle)
    sources = [source_cut(name, fresh=True) for name in names]
    if not cint(preview):
        if not client_event_id:
            frappe.throw('Cần mã yêu cầu để chống tạo dự thu trùng.')
        table = frappe.qb.DocType('Integration Event')
        saved = frappe.qb.from_(table).select(table.name, table.payload_hash, table.result_json).where(table.event_key == event_key).for_update().run(as_dict=True)
        existing = saved[0] if saved else None
        if existing:
            if existing.payload_hash != request_hash:
                frappe.throw('Mã yêu cầu đã dùng với nội dung khác.')
            result = json.loads(existing.result_json)
            for name in result['documents']:
                frappe.get_doc('Harvest Forecast', name).check_permission('read')
            return result
    source_hash = canonical_hash([s['source_hash'] for s in sources])
    if not cint(preview) and (not expected_source_hash or expected_source_hash != source_hash):
        frappe.throw('Nguồn buồng đã đổi hoặc chưa xem trước. Tính lại trước khi tạo nháp.')
    documents, drafts = [], []
    for source in sources:
        cut = source['cut']
        part = cut_slice(source, period_start, period_end)
        if not part or part['source_bunch_qty'] <= 0.00000001:
            frappe.throw('Nguồn không còn buồng trong kỳ: '+cut.name)
        doc = frappe.get_doc(dict(doctype='Harvest Forecast', farm=cut.farm, farm_block=cut.farm_block,
            farm_plot=cut.farm_plot, crop_cycle=cut.crop_cycle, sucker_selection_batch=cut.sucker_selection_batch or '',
            process_adoption=source['adoption'].name, source_claims=[dict(source_cut_operation=cut.name)],
            forecast_basis='Cut Bud Operations', period_start_date=part['slice_start'], period_end_date=part['slice_end'],
            planning_granularity='Custom', supply_state='Draft', output_plan=outputs))
        doc.run_method('before_validate')
        doc.validate()
        assert_source_ownership(doc)
        drafts.append(dict(source_cut_operation=cut.name, farm=cut.farm, farm_block=cut.farm_block, crop_cycle=cut.crop_cycle,
            period_start_date=doc.period_start_date, period_end_date=doc.period_end_date, source_bunch_qty=doc.source_bunch_qty,
            gross_forecast_kg=doc.gross_forecast_kg, packed_forecast_kg=doc.packed_forecast_kg, source_hash=source['source_hash']))
        if not cint(preview):
            doc.insert()
            documents.append(doc.name)
    result = dict(drafts=drafts, documents=documents, source_hash=source_hash, issues=[])
    if not cint(preview):
        event = frappe.get_doc(dict(doctype='Integration Event', farm=sources[0]['cut'].farm, event_key=event_key,
                                  payload_hash=request_hash, result_json=json.dumps(result, default=str)))
        with command(event, 'integration_event'):
            event.insert(ignore_permissions=True)
    return result


def matching_forecasts(actual):
    if not actual.get('source_cut_operation'):
        return []
    claim, forecast = frappe.qb.DocType('Forecast Source Claim'), frappe.qb.DocType('Harvest Forecast')
    return (frappe.qb.from_(claim).join(forecast).on(claim.parent == forecast.name)
            .select(forecast.name, forecast.period_start_date, forecast.period_end_date)
            .where((claim.source_cut_operation == actual.source_cut_operation) & (claim.parenttype == 'Harvest Forecast')
                   & (forecast.supply_state == 'Released')).orderby(forecast.period_start_date, forecast.name).for_update().run(as_dict=True))


def actual_forecast_shares(actual):
    """Attribute physical output to all published slices consumed by this actual."""
    if not actual.get('source_cut_operation'):
        return None
    tag = frappe.db.get_value('Bunch Operation', actual.source_cut_operation, 'bunch_tag')
    if not tag or not frappe.db.get_value('Bunch Tag', tag, 'process_adoption'):
        return None
    source = source_cut(actual.source_cut_operation, fresh=True)
    table = frappe.qb.DocType('Forecast Source Claim')
    claims = (frappe.qb.from_(table).select(table.parent, table.slice_start, table.slice_end)
              .where((table.source_cut_operation == actual.source_cut_operation) & (table.parenttype == 'Harvest Forecast'))
              .for_update().run(as_dict=True))
    result = []
    for row in claims:
        supply = frappe.get_doc('Harvest Forecast', row.parent, for_update=True)
        if supply.supply_state == 'Draft':
            continue
        snapshot = json.loads(supply.source_snapshot or '{}')
        if any(event['key'] == 'harvest:'+actual.name for event in snapshot.get('evidence', {}).get('events', [])):
            continue  # This residual publication was prepared after that harvest.
        # Retired claims are kept only for actuals explicitly attached to them.
        if supply.supply_state != 'Released' and actual.forecast != supply.name:
            continue
        qty = interval_quantity(source['balance'], row.slice_start, row.slice_end, 'harvest:'+actual.name)
        if qty:
            result.append((supply, qty/float(actual.harvested_bunch_qty)))
    return result


def refresh_cut_forecasts(doc, method=None):
    cut_name = doc.get('source_cut_operation') or doc.get('source_operation')
    if not cut_name:
        return
    table = frappe.qb.DocType('Forecast Source Claim')
    names = [row[0] for row in frappe.qb.from_(table).select(table.parent)
             .where((table.source_cut_operation == cut_name) & (table.parenttype == 'Harvest Forecast')).for_update().run()]
    for name in sorted(set(names)):
        lock('Harvest Forecast', name)
        supply = frappe.get_doc('Harvest Forecast', name, for_update=True)
        if supply.supply_state != 'Draft':
            with command(supply, 'supply'):
                supply.save(ignore_permissions=True)


@frappe.whitelist(methods=['POST'])
def close_forecast(forecast, reason, base_modified=None):
    require_role('Lotus Farm Manager')
    doc = frappe.get_doc('Harvest Forecast', forecast)
    doc.check_permission('write')
    lock('Farm', doc.farm)
    doc = frappe.get_doc('Harvest Forecast', forecast, for_update=True)
    if doc.supply_state == 'Closed':
        return dict(forecast=doc.name, supply_state='Closed')
    if doc.supply_state != 'Released':
        frappe.throw('Chỉ kết thúc dự thu đã phát hành.')
    if base_modified and str(doc.modified) != str(base_modified):
        frappe.throw('Dự thu đã thay đổi. Tải lại trước khi kết thúc.')
    if not (reason or '').strip():
        frappe.throw('Ghi lý do kết thúc dự thu.')
    if any(row.allocation_state == 'Reserved' for row in doc.allocations or []):
        frappe.throw('Giải phóng hoặc chuyển các lượng giữ hàng sang tồn kho trước khi kết thúc.')
    doc.supply_state = 'Closed'
    with command(doc, 'supply'):
        doc.save()
    doc.add_comment('Comment', text='Kết thúc dự thu: '+frappe.utils.escape_html(reason.strip()))
    return dict(forecast=doc.name, supply_state=doc.supply_state)
