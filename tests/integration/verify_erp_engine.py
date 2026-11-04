"""ERP screens end to end on a real site through lotus_farm.erp_workbench (the API the Lotus ERP screens call). Rolled back.
Run in a bench container:  SITE=<site> ../env/bin/python ../apps/lotus_farm/tests/integration/verify_erp_engine.py"""
import json, os, traceback, uuid
import frappe
from frappe.utils import add_days, flt, nowdate

frappe.init(site=os.environ.get('SITE', 'frontend'), sites_path='/home/frappe/frappe-bench/sites'); frappe.connect(); frappe.set_user('Administrator')
R = []
def ok(name, cond, detail=''):
    R.append(('PASS' if cond else 'FAIL', name, str(detail)[:300]))
def step(name, fn):
    try:
        return fn()
    except Exception as e:
        R.append(('ERROR', name, type(e).__name__ + ': ' + str(e)[:400])); return None
def raises(name, fn, kind=frappe.ValidationError, expect=''):
    try:
        fn(); R.append(('FAIL', name, 'not blocked'))
    except kind as e:
        R.append(('PASS' if expect in str(e) else 'FAIL', name, str(e)[:200]))
    except Exception as e:
        R.append(('FAIL', name, type(e).__name__ + ': ' + str(e)[:200]))

from lotus_farm import erp_workbench as e
key = lambda: uuid.uuid4().hex
try:
    tag = uuid.uuid4().hex[:6]; today = nowdate()
    company = frappe.db.get_value('Company', {}, 'name')
    ok('bảng chống gửi trùng đã tạo (migrate)', frappe.db.table_exists('Lotus ERP Command'))
    cat = e.catalog()
    ok('danh mục đủ 8 phân hệ', len(cat['modules']) == 8, [m['label'] for m in cat['modules']])
    ok('danh mục kèm công ty', any(c['name'] == company for c in cat['companies']))

    # ---- Bán hàng: khách → đơn bán → giao → hóa đơn → thu tiền --------------------------------------
    cust = e.document('Customer', company=company)['doc']
    cust.update(customer_name='KH ERP ' + tag, customer_type='Company', customer_group=frappe.db.get_value('Customer Group', {'is_group': 0}, 'name'))
    k = key(); c1 = e.action('Customer', 'save', k, values=cust, company=company); c2 = e.action('Customer', 'save', k, values=cust, company=company)
    customer = c1['doc']['name']
    ok('gửi trùng cùng mã → cùng khách hàng', customer == c2['doc']['name'])
    raises('cùng mã khác nội dung bị chặn', lambda: e.action('Customer', 'save', k, values={**cust, 'customer_name': 'Khác'}, company=company), expect='Mã yêu cầu')
    item = frappe.db.get_value('Item', {'is_stock_item': 1, 'disabled': 0, 'has_batch_no': 0, 'has_serial_no': 0}, 'name')
    store = frappe.db.get_value('Warehouse', {'company': company, 'is_group': 0, 'disabled': 0}, 'name')
    # stock for the delivery
    se = e.document('Stock Entry', company=company)['doc']
    se.update(stock_entry_type='Material Receipt', purpose='Material Receipt', lotus_receipt_reason='Surplus', items=[dict(item_code=item, qty=10, t_warehouse=store, basic_rate=20000, allow_zero_valuation_rate=0)])
    se_res = step('nhập kho bằng màn ERP', lambda: e.action('Stock Entry', 'submit', key(), values=se, company=company))
    ok('phiếu kho ghi sổ', se_res and se_res['doc']['docstatus'] == 1, se_res and se_res['doc']['name'])

    so = e.document('Sales Order', company=company)['doc']
    party = e.party_details('Sales Order', 'Customer', customer, company, posting_date=today)
    so.update({k2: v for k2, v in party.items() if frappe.get_meta('Sales Order').has_field(k2) and not isinstance(v, list)})
    details = e.item_details('Sales Order', item, company, row=json.dumps(dict(qty=3, warehouse=store)), header=json.dumps(dict(customer=customer, transaction_date=today, currency=so.get('currency'))))
    ok('item_details trả đơn vị và tên hàng', details.get('uom') and details.get('item_name'), {k3: details.get(k3) for k3 in ('uom', 'item_name', 'rate')})
    so.update(customer=customer, transaction_date=today, delivery_date=add_days(today, 3), items=[dict(item_code=item, qty=3, rate=50000, warehouse=store, delivery_date=add_days(today, 3), uom=details.get('uom'), conversion_factor=1)])
    pv = e.preview('Sales Order', json.dumps(so, default=str), company)
    ok('tính thử tổng tiền 150.000', abs(flt(pv.get('grand_total')) - 150000) < 1, pv.get('grand_total'))
    so_res = step('lưu + ghi sổ đơn bán', lambda: e.action('Sales Order', 'submit', key(), values=so, company=company))
    if so_res:
        ok('đơn bán đã ghi sổ', so_res['doc']['docstatus'] == 1)
        targets = {a['target'] for a in so_res['actions']}
        ok('đơn bán gợi ý tạo giao hàng / hóa đơn / thu tiền', {'Delivery Note', 'Sales Invoice', 'Payment Entry'} <= targets, targets)
        dn = e.map_document('Sales Order', so_res['doc']['name'], 'Delivery Note', company)
        dn_res = step('tạo + ghi sổ phiếu giao từ đơn bán', lambda: e.action('Delivery Note', 'submit', key(), values=dn['doc'], company=company))
        if dn_res:
            ok('phiếu giao trừ kho', dn_res['doc']['docstatus'] == 1)
            si = e.map_document('Delivery Note', dn_res['doc']['name'], 'Sales Invoice', company)
            si_res = step('tạo + ghi sổ hóa đơn từ phiếu giao', lambda: e.action('Sales Invoice', 'submit', key(), values=si['doc'], company=company))
            if si_res:
                ok('hóa đơn 150.000 còn nợ', abs(flt(si_res['doc']['outstanding_amount']) - 150000) < 1, si_res['doc']['outstanding_amount'])
                pe = e.map_document('Sales Invoice', si_res['doc']['name'], 'Payment Entry', company)
                pe_res = step('thu tiền hóa đơn', lambda: e.action('Payment Entry', 'submit', key(), values={**pe['doc'], 'reference_no': 'CK-' + tag, 'reference_date': today}, company=company))
                if pe_res:
                    ok('thu đủ → hóa đơn hết nợ', flt(frappe.db.get_value('Sales Invoice', si_res['doc']['name'], 'outstanding_amount')) == 0)
                ret = e.map_document('Delivery Note', dn_res['doc']['name'], 'Return', company)
                ok('trả hàng dựng phiếu giao âm', ret['doc'].get('is_return') == 1 and flt(ret['doc']['items'][0]['qty']) < 0, ret['doc']['items'][0]['qty'])
        # hủy + sửa đổi trên đơn bán chưa phát sinh (đơn mới)
        so2 = step('đơn bán thứ hai', lambda: e.action('Sales Order', 'submit', key(), values={**so, 'name': None}, company=company))
        if so2:
            doc2 = so2['doc']
            raises('hủy với phiên bản cũ bị chặn', lambda: e.action('Sales Order', 'cancel', key(), name=doc2['name'], modified='2000-01-01 00:00:00', company=company), frappe.TimestampMismatchError)
            can = e.action('Sales Order', 'cancel', key(), name=doc2['name'], modified=doc2['modified'], company=company)
            ok('hủy đơn bán', can['doc']['docstatus'] == 2)
            am = e.amend('Sales Order', doc2['name'], can['doc']['modified'], company)
            ok('sửa đổi tạo bản nháp mới', am['is_new'] and am['doc']['amended_from'] == doc2['name'])

    # ---- Nhân sự: cấp phép, đơn xin nghỉ, thưởng/khấu trừ, điều chuyển -------------------------------
    emp = frappe.db.get_value('Employee', {'company': company, 'status': 'Active'}, ['name', 'department'], as_dict=True)
    lt = e.document('Leave Type')['doc']; lt.update(leave_type_name='Phép năm ERP ' + tag, max_leaves_allowed=12)
    lt_res = step('tạo loại nghỉ', lambda: e.action('Leave Type', 'save', key(), values=lt))
    if lt_res and emp:
        la = e.document('Leave Allocation', company=company)['doc']
        la.update(employee=emp.name, leave_type=lt_res['doc']['name'], from_date=today[:4] + '-01-01', to_date=today[:4] + '-12-31', new_leaves_allocated=12)
        la_res = step('cấp 12 ngày phép', lambda: e.action('Leave Allocation', 'submit', key(), values=la, company=company))
        ok('cấp phép ghi sổ', la_res and la_res['doc']['docstatus'] == 1)
        lap = e.document('Leave Application', company=company)['doc']
        lap.update(employee=emp.name, leave_type=lt_res['doc']['name'], from_date=today, to_date=today, status='Approved', leave_approver=None)
        lap_res = step('đơn xin nghỉ 1 ngày', lambda: e.action('Leave Application', 'submit', key(), values=lap, company=company))
        ok('đơn xin nghỉ được duyệt', lap_res and lap_res['doc']['docstatus'] == 1, lap_res and lap_res['doc'].get('total_leave_days'))
        bal = e.run_report('Employee Leave Balance', json.dumps(dict(from_date=today[:4] + '-01-01', to_date=today[:4] + '-12-31', employee=emp.name, company=company)), company)
        ok('báo cáo phép còn lại chạy được', isinstance(bal.get('result'), list), len(bal.get('result') or []))
    comp = frappe.db.get_value('Salary Component', {'type': 'Earning', 'disabled': 0}, 'name')
    if comp and emp:
        ad = e.document('Additional Salary', company=company)['doc']
        ad.update(employee=emp.name, salary_component=comp, amount=500000, payroll_date=today, company=company)
        ad_res = step('thưởng / khấu trừ theo kỳ', lambda: e.action('Additional Salary', 'submit', key(), values=ad, company=company))
        ok('Additional Salary ghi sổ', ad_res and ad_res['doc']['docstatus'] == 1, ad_res and ad_res['doc'].get('salary_component'))
    if emp:
        tr = e.document('Employee Transfer', company=company)['doc']
        tr.update(employee=emp.name, transfer_date=add_days(today, 1), company=company, transfer_details=[dict(property='Department', current=emp.department or '', new=emp.department or '', fieldname='department')])
        tr_res = step('điều chuyển nhân viên (nháp)', lambda: e.action('Employee Transfer', 'save', key(), values=tr, company=company))
        ok('điều chuyển lưu được', tr_res and tr_res['doc']['name'], tr_res and tr_res['doc']['name'])

    # ---- Kho: lô hàng, danh sách, cây ------------------------------------------------------------------
    bitem = e.document('Item')['doc']
    bitem.update(item_code='ERP-LOT-' + tag, item_name='Thuốc thử lô ' + tag, item_group=frappe.db.get_value('Item Group', {'is_group': 0}, 'name'), stock_uom='Kg', is_stock_item=1, has_batch_no=1, has_expiry_date=1, shelf_life_in_days=365)
    batches_on = frappe.db.get_single_value('Stock Settings', 'enable_serial_and_batch_no_for_item')
    bi = step('vật tư theo lô có hạn dùng', lambda: e.action('Item', 'save', key(), values=bitem)) if batches_on else None
    if not batches_on:
        R.append(('PASS', 'lô hàng: site đang tắt quản lý lô (Stock Settings) — bỏ qua', ''))
    if bi:
        b = e.document('Batch')['doc']; b.update(batch_id='LOT-' + tag, item=bi['doc']['name'], expiry_date=add_days(today, 180))
        b_res = step('tạo lô', lambda: e.action('Batch', 'save', key(), values=b))
        ok('lô có hạn dùng', b_res and str(b_res['doc']['expiry_date']) == str(add_days(today, 180)))
    lst = e.listing('Stock Entry', company=company, search=se_res['doc']['name'] if se_res else '')
    ok('danh sách tìm theo số phiếu', lst['total_count'] >= 1 and lst['columns'], lst['total_count'])
    tree = e.tree('Account', company)
    ok('cây tài khoản', len(tree['rows']) > 10, len(tree['rows']))
    raises('DocType ngoài ERP bị chặn', lambda: e.schema('Farm'), frappe.PermissionError)
except Exception:
    R.append(('ERROR', 'script', traceback.format_exc()[-1500:]))
finally:
    frappe.db.rollback(); frappe.destroy()
    for r in R:
        print('%-5s | %s | %s' % r)
    bad = [r for r in R if r[0] != 'PASS']
    print('%d checks, %d failed' % (len(R), len(bad)))
    raise SystemExit(1 if bad else 0)
