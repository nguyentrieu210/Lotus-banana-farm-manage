"""Kho end to end on a real site, rolled back at the end: nhập / xuất / chuyển / kiểm kê / hủy and the views that read them.
Run in a bench container:  SITE=<site> /home/frappe/frappe-bench/env/bin/python apps/lotus_farm/tests/integration/verify_kho_e2e.py
Needs finance switched on (Thông tư 99 mapping), one active Employee, one Supplier and one Farm Block."""
import os, traceback, uuid
import frappe
from frappe.utils import add_days, flt, nowdate

frappe.init(site=os.environ.get('SITE', 'frontend'), sites_path='/home/frappe/frappe-bench/sites'); frappe.connect(); frappe.set_user('Administrator')
R = []
def ok(name, cond, detail=''):
    R.append(('PASS' if cond else 'FAIL', name, str(detail)[:300]))
def blocked(name, fn, expect):
    try:
        fn(); R.append(('FAIL', name, 'not blocked'))
    except frappe.ValidationError as e:
        R.append(('PASS' if expect in str(e) else 'FAIL', name, str(e)[:300]))

from lotus_farm import warehouse as w
try:
    company = 'Lotus Agritech'; tag = uuid.uuid4().hex[:6]; today = nowdate()
    make = lambda dt, **v: frappe.get_doc(dict(doctype=dt, **v)).insert()
    parent = frappe.db.get_value('Warehouse', {'company': company, 'is_group': 1}, 'name')
    A = make('Warehouse', warehouse_name='E2E A ' + tag, company=company, parent_warehouse=parent).name
    B = make('Warehouse', warehouse_name='E2E B ' + tag, company=company, parent_warehouse=parent).name
    if not frappe.db.exists('UOM', 'Bao'):
        make('UOM', uom_name='Bao')
    X = make('Item', item_code='E2E-X-' + tag, item_name='E2E phân ' + tag, item_group='All Item Groups', stock_uom='Kg', is_stock_item=1,
             uoms=[dict(uom='Kg', conversion_factor=1), dict(uom='Bao', conversion_factor=50)]).name
    Y = make('Item', item_code='E2E-Y-' + tag, item_name='E2E thuốc ' + tag, item_group='All Item Groups', stock_uom='Kg', is_stock_item=1).name
    Z = make('Item', item_code='E2E-Z-' + tag, item_name='E2E mới ' + tag, item_group='All Item Groups', stock_uom='Kg', is_stock_item=1).name
    supplier = frappe.db.get_value('Supplier', {'disabled': 0}, 'name')
    emp = frappe.db.get_value('Employee', {'company': company, 'status': 'Active'}, 'name')
    area = frappe.db.get_value('Farm Block', {}, 'block_code')
    qty = lambda item, wh: flt(frappe.db.get_value('Bin', {'item_code': item, 'warehouse': wh}, 'actual_qty'))
    rate = lambda item, wh: flt(frappe.db.get_value('Bin', {'item_code': item, 'warehouse': wh}, 'valuation_rate'))
    post = lambda dt, n: w.submit_document(dt, n, modified=w.document(dt, n)['modified'])
    issue = lambda q, **kw: w.create_draft(company, 'issue', kw.pop('date', today), [dict(item=X, qty=q, area=area, **kw)], source=A, receiver_employee=emp, notes='E2E xuất')
    gl = lambda name: frappe.get_all('GL Entry', filters={'voucher_no': name, 'is_cancelled': 0}, fields=['account', 'debit', 'credit'])

    # Nhập mua theo bao, ghi sổ ngay (Mua nhanh)
    r1 = w.create_draft(company, 'receipt', today, [dict(item=X, qty=2, uom='Bao', rate=1000000)], target=A, receipt_reason='Purchase', supplier=supplier, post=1)
    ok('mua nhanh ghi sổ', r1['docstatus'] == 1, r1)
    ok('2 bao = 100 kg @ 20.000', abs(qty(X, A) - 100) < 1e-6 and abs(rate(X, A) - 20000) < 0.01, (qty(X, A), rate(X, A)))
    line = w.document('Stock Entry', r1['name'])['items'][0]
    ok('chi tiết giữ 2 Bao @ 1.000.000', line['qty'] == 2 and line['uom'] == 'Bao' and abs(flt(line['rate']) - 1000000) < 0.01, line)
    ok('Nợ 152 / Có 3388', sorted(a['account'][:4] for a in gl(r1['name'])) == ['152 ', '3388'], gl(r1['name']))
    acc = w.receipt_accounts(company)
    r2 = w.create_draft(company, 'receipt', today, [dict(item=Y, qty=10, rate=50000)], target=A, receipt_reason='Purchase', supplier=supplier,
                        additional_costs=[dict(description='Vận chuyển', amount=100000, expense_account=acc['default_account'] or acc['accounts'][0]['name'])])
    post('Stock Entry', r2['name'])
    ok('chi phí vận chuyển vào giá vốn', abs(rate(Y, A) - 60000) < 0.01, rate(Y, A))
    blocked('hàng mua phải có NCC', lambda: w.create_draft(company, 'receipt', today, [dict(item=X, qty=1, rate=1)], target=A, receipt_reason='Purchase'), 'nhà cung cấp')
    blocked('hàng mua phải có giá', lambda: w.create_draft(company, 'receipt', today, [dict(item=X, qty=1, rate=0)], target=A, receipt_reason='Purchase', supplier=supplier), 'giá mua')

    # Thu hồi / thừa không giá: vào theo giá vốn hiện tại, không làm loãng giá
    r3 = w.create_draft(company, 'receipt', today, [dict(item=X, qty=1, uom='Bao')], target=A, receipt_reason='Surplus')
    ok('bỏ trống giá + đơn vị bao: 20.000/kg', abs(flt(frappe.get_doc('Stock Entry', r3['name']).items[0].basic_rate) - 20000) < 0.01,
       frappe.get_doc('Stock Entry', r3['name']).items[0].basic_rate)
    frappe.delete_doc('Stock Entry', r3['name'])
    r4 = w.create_draft(company, 'receipt', today, [dict(item=X, qty=10, rate=0, area=area)], target=A, receipt_reason='Recovery')
    post('Stock Entry', r4['name'])
    ok('thu hồi giá 0 giữ giá vốn 20.000', abs(rate(X, A) - 20000) < 0.01, rate(X, A))
    ok('thu hồi ghi Có 621', any(a['account'].startswith('621') and a['credit'] > 0 for a in gl(r4['name'])), gl(r4['name']))
    blocked('thừa của vật tư chưa từng có giá phải nhập giá', lambda: w.create_draft(company, 'receipt', today, [dict(item=Z, qty=1, rate=0)], target=A, receipt_reason='Surplus'), 'Chưa có giá vốn')

    # Xuất kho: 110 kg
    i1 = issue(30); post('Stock Entry', i1['name'])
    se = frappe.get_doc('Stock Entry', i1['name'])
    ok('xuất vào 621 của lô', se.items[0].expense_account.startswith('621') and se.items[0].get('lotus_farm_block'), (se.items[0].expense_account, se.items[0].get('lotus_farm_block')))
    i2 = issue(1, uom='Bao'); post('Stock Entry', i2['name'])
    ok('xuất 1 bao trừ 50 kg', abs(qty(X, A) - 30) < 1e-6, qty(X, A))
    blocked('xuất quá tồn', lambda: issue(40), 'thiếu')
    blocked('xuất lùi ngày trước khi có hàng', lambda: issue(5, date=add_days(today, -3)), 'thiếu')
    blocked('xuất thiếu người nhận', lambda: w.create_draft(company, 'issue', today, [dict(item=X, qty=1, area=area)], source=A, notes='x'), 'người nhận')
    d1 = issue(20)
    blocked('nháp thứ hai vượt phần đã giữ', lambda: issue(15), 'thiếu')
    doc = w.document('Stock Entry', d1['name'])
    blocked('sửa bản cũ bị chặn', lambda: w.create_draft(company, 'issue', today, [dict(item=X, qty=19, area=area)], source=A, receiver_employee=emp, notes='x', existing_name=d1['name'], base_modified='2000-01-01'), 'thay đổi')
    e = w.create_draft(company, 'issue', today, [dict(item=X, qty=19, area=area)], source=A, receiver_employee=emp, notes='x', existing_name=d1['name'], base_modified=doc['modified'])
    ok('sửa nháp giữ số phiếu', e['name'] == d1['name'], e)
    w.delete_draft('Stock Entry', d1['name'], w.document('Stock Entry', d1['name'])['modified'])
    ok('xóa nháp', not frappe.db.exists('Stock Entry', d1['name']))

    # Mục đích xuất: hủy không cần lô / người nhận nhưng cần lý do; ghi chi phí khác, không vào 621 của lô
    blocked('xuất hủy cần lý do', lambda: w.create_draft(company, 'issue', today, [dict(item=Y, qty=1)], source=A, issue_purpose='Disposal'), 'lý do')
    h = w.create_draft(company, 'issue', today, [dict(item=Y, qty=1)], source=A, issue_purpose='Disposal', notes='E2E hàng hỏng')
    post('Stock Entry', h['name'])
    hd = frappe.get_doc('Stock Entry', h['name'])
    ok('xuất hủy ghi sổ, không lô, mục đích Disposal', hd.docstatus == 1 and hd.get('lotus_issue_purpose') == 'Disposal' and not hd.get('lotus_issue_mode'), (hd.get('lotus_issue_purpose'), hd.get('lotus_issue_mode')))
    ok('xuất hủy không vào 621', not hd.items[0].expense_account.startswith('621'), hd.items[0].expense_account)
    ok('chi tiết + danh sách thấy mục đích', w.document('Stock Entry', h['name'])['issue_purpose'] == 'Disposal' and any(r.name == h['name'] and r.purpose.startswith('Xuất hủy') for r in w.documents(company, kind='issues', warehouse=A)['rows']))
    blocked('xuất sản xuất vẫn bắt chọn lô', lambda: w.create_draft(company, 'issue', today, [dict(item=X, qty=1)], source=A, receiver_employee=emp, notes='x'), 'Khu vực')
    blocked('mục đích khác chỉ xuất thủ công', lambda: w.create_draft(company, 'issue', today, [dict(item=X, qty=1)], source=A, issue_purpose='Sale', issue_mode='Request', notes='x'), 'yêu cầu')
    # Chuyển kho + chống gửi trùng
    ev = 'e2e-' + tag
    t1 = w.create_draft(company, 'transfer', today, [dict(item=X, qty=5)], source=A, target=B, client_event_id=ev)
    t2 = w.create_draft(company, 'transfer', today, [dict(item=X, qty=5)], source=A, target=B, client_event_id=ev)
    ok('gửi trùng trả về cùng phiếu', t1['name'] == t2['name'], (t1, t2))
    blocked('cùng mã yêu cầu khác nội dung', lambda: w.create_draft(company, 'transfer', today, [dict(item=X, qty=6)], source=A, target=B, client_event_id=ev), 'đã tạo phiếu')
    post('Stock Entry', t1['name'])
    ok('A=25 B=5, giá B 20.000', abs(qty(X, A) - 25) < 1e-6 and abs(qty(X, B) - 5) < 1e-6 and abs(rate(X, B) - 20000) < 0.01, (qty(X, A), qty(X, B), rate(X, B)))

    # Kiểm kê
    c1 = w.create_draft(company, 'count', today, [dict(item=X, qty=22)], target=A)
    post('Stock Reconciliation', c1['name'])
    ok('kiểm kê thiếu 3 kg -> 1381', abs(qty(X, A) - 22) < 1e-6 and frappe.db.get_value('Stock Reconciliation', c1['name'], 'expense_account').startswith('1381'), qty(X, A))
    blocked('kiểm kê lẫn thừa và thiếu', lambda: post('Stock Reconciliation', w.create_draft(company, 'count', today, [dict(item=X, qty=23), dict(item=Y, qty=8)], target=A)['name']), 'riêng')
    c2 = w.create_draft(company, 'count', today, [dict(item=Y, qty=3)], target=B)
    ok('thừa ở kho chưa có giá lấy giá kho khác', abs(flt(frappe.get_doc('Stock Reconciliation', c2['name']).items[0].valuation_rate) - 60000) < 0.01,
       frappe.get_doc('Stock Reconciliation', c2['name']).items[0].valuation_rate)
    post('Stock Reconciliation', c2['name'])
    ok('thừa kiểm kê ghi 3381', frappe.db.get_value('Stock Reconciliation', c2['name'], 'expense_account').startswith('3381'), frappe.db.get_value('Stock Reconciliation', c2['name'], 'expense_account'))
    blocked('thừa của vật tư chưa từng có giá', lambda: w.create_draft(company, 'count', today, [dict(item=Z, qty=2)], target=A), 'Chưa có giá vốn')
    blocked('tồn đầu kỳ cần giá', lambda: w.create_draft(company, 'count', today, [dict(item=X, qty=5, rate=0)], target=A, count_purpose='Opening Stock'), 'đơn giá')

    # Sổ kho: kiểm kê hiện đúng số thiếu / thừa
    mv = w.movements(company, warehouse=A)
    row = next(r for r in mv['rows'] if r.voucher_no == c1['name'] and r.item_code == X)
    ok('sổ kho: kiểm kê xuất 3, đầu 25 cuối 22', abs(row.out_qty - 3) < 1e-6 and row.in_qty == 0 and abs(row.opening_qty - 25) < 1e-6 and row.kind == 'Xuất', dict(kind=row.kind, in_qty=row.in_qty, out_qty=row.out_qty, opening=row.opening_qty))
    ok('sổ kho: số dư từng dòng khớp', all(abs(r.opening_qty + r.in_qty - r.out_qty - r.qty_after_transaction) < 1e-6 for r in mv['rows']), mv['total_count'])
    mvb = w.movements(company, warehouse=B)
    row = next(r for r in mvb['rows'] if r.voucher_no == c2['name'])
    ok('sổ kho: kiểm kê thừa nhập 3', abs(row.in_qty - 3) < 1e-6 and row.kind == 'Nhập', dict(in_qty=row.in_qty, out_qty=row.out_qty))
    mvd = w.movements(company, warehouse=A, from_date=today, to_date=today)
    ok('sổ kho lọc ngày: kiểm kê vẫn đúng', any(r.voucher_no == c1['name'] and abs(r.out_qty - 3) < 1e-6 for r in mvd['rows']))

    # Tồn kho / NXT
    ov = w.overview(company, search=tag)
    rx = next(r for r in ov['items'] if r.name == X)
    ok('tồn kho X = A + B', abs(rx.actual_qty - (qty(X, A) + qty(X, B))) < 1e-6, rx.actual_qty)
    ok('tồn quy đổi theo bao', rx.pack_uom == 'Bao' and abs(flt(rx.pack_actual_qty) - rx.actual_qty / 50) < 1e-6, (rx.pack_uom, rx.pack_actual_qty))
    ss = w.stock_summary(company, search=tag)
    ok('NXT: đầu + nhập - xuất = cuối', all(abs(r['opening_qty'] + r['in_qty'] - r['out_qty'] - r['closing_qty']) < 1e-6 for r in ss['rows']), ss['rows'])
    ok('NXT khớp tồn', abs(sum(r['closing_qty'] for r in ss['rows'] if r['item_code'] == X) - rx.actual_qty) < 1e-6)

    # Danh sách phiếu
    for kind, names in (('receipts', [r1['name'], r2['name'], r4['name']]), ('issues', [i1['name'], i2['name']]), ('transfers', [t1['name']]), ('counts', [c1['name'], c2['name']])):
        got = {r.name: r for r in w.documents(company, kind=kind, warehouse=A if kind != 'counts' else None)['rows']}
        ok('danh sách %s' % kind, all(n in got for n in names if kind != 'counts' or n == c1['name']), [n for n in names if n not in got])
    row = next(r for r in w.documents(company, kind='transfers')['rows'] if r.name == t1['name'])
    ok('danh sách: loại + kho', row.kind == 'Chuyển kho' and row.warehouses == ' · '.join(sorted([A, B])), (row.kind, row.warehouses))
    ok('lọc theo kho B', all(B in r.warehouses for r in w.documents(company, warehouse=B)['rows']))

    # Cột nghiệp vụ của từng danh sách phiếu
    rec = next(r for r in w.documents(company, kind='receipts', warehouse=A)['rows'] if r.name == r1['name'])
    ok('phiếu nhập: lý do + NCC', rec.reason == 'Mua ngoài' and rec.supplier == supplier, (rec.reason, rec.supplier))
    rec4 = next(r for r in w.documents(company, kind='receipts', warehouse=A)['rows'] if r.name == r4['name'])
    ok('phiếu thu hồi: lý do', rec4.reason == 'Thu hồi từ lô', rec4.reason)
    iss = next(r for r in w.documents(company, kind='issues', warehouse=A)['rows'] if r.name == i1['name'])
    ok('phiếu xuất: người nhận + lô + ghi chú', iss.receiver and iss.areas == area and iss.notes == 'E2E xuất', (iss.receiver, iss.areas, iss.notes))
    cnt = next(r for r in w.documents(company, kind='counts')['rows'] if r.name == c1['name'])
    ok('kiểm kê: loại', cnt.kind == 'Kiểm kê', cnt.kind)
    got = w.documents(company, kind='issues', column_filters=frappe.as_json({'receiver': [iss.receiver]}))['rows']
    ok('lọc theo người nhận', got and all(r.receiver == iss.receiver for r in got), len(got))
    # Chi tiết kiểm kê: tồn sổ sách + thực đếm
    line = w.document('Stock Reconciliation', c1['name'])['items'][0]
    ok('chi tiết kiểm kê có tồn sổ sách', abs(flt(line['current_qty']) - 25) < 1e-6 and abs(flt(line['qty']) - 22) < 1e-6, (line['current_qty'], line['qty']))
    # Sổ kho sắp ngày tăng dần: trong cùng ngày theo giờ, số dư nối tiếp nhau
    asc = [r for r in w.movements(company, warehouse=A, sort_model=frappe.as_json([{'colId': 'posting_date', 'sort': 'asc'}]))['rows'] if r.item_code == X]
    ok('sổ kho tăng dần: tồn trước = tồn sau dòng trước', all(abs(asc[i].opening_qty - asc[i - 1].qty_after_transaction) < 1e-6 for i in range(1, len(asc))),
       [(r.voucher_no, r.opening_qty, r.qty_after_transaction) for r in asc])
    # Hủy phiếu đã ghi sổ
    blocked('hủy cần lý do', lambda: w.cancel_document('Stock Entry', t1['name'], w.document('Stock Entry', t1['name'])['modified'], ''), 'Lý do hủy')
    ok('chi tiết báo được hủy', w.document('Stock Entry', t1['name'])['can_cancel'])
    w.cancel_document('Stock Entry', t1['name'], w.document('Stock Entry', t1['name'])['modified'], 'E2E chuyển nhầm')
    ok('hủy chuyển kho đảo tồn', frappe.db.get_value('Stock Entry', t1['name'], 'docstatus') == 2 and abs(qty(X, B) - 0) < 1e-6, qty(X, B))
    ok('lý do hủy lưu bình luận', frappe.db.exists('Comment', {'reference_name': t1['name'], 'content': ['like', '%E2E chuyển nhầm%']}))
    blocked('không hủy phiếu nháp', lambda: w.cancel_document('Stock Entry', (d := issue(1))['name'], w.document('Stock Entry', d['name'])['modified'], 'x'), 'đã ghi sổ')
except Exception:
    R.append(('ERROR', 'script', traceback.format_exc()[-1500:]))
finally:
    frappe.db.rollback(); frappe.destroy()
    for r in R:
        print('%-5s | %s | %s' % r)
    failed = [r for r in R if r[0] != 'PASS']
    print('%d checks, %d failed' % (len(R), len(failed)))
    raise SystemExit(1 if failed else 0)
