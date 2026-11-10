"""Hóa đơn mua có VAT cho hộ kinh doanh (VAT tính vào giá vốn), on a real site, rolled back at the end.
Run in a bench container:  SITE=<site> /home/frappe/frappe-bench/env/bin/python apps/lotus_farm/tests/integration/verify_vat_in_cost.py
Case from a real invoice: 8 tấn DAP × 26.571.428,571 = 212.571.429, VAT 5% 10.628.571, tổng cộng 223.200.000.
Needs finance switched on (Thông tư 99 mapping) and one Supplier."""
import os, traceback, uuid
import frappe
from frappe.utils import flt, nowdate

frappe.init(site=os.environ.get('SITE', 'frontend'), sites_path='/home/frappe/frappe-bench/sites'); frappe.connect(); frappe.set_user('Administrator')
R = []
def ok(name, cond, detail=''):
    R.append(('PASS' if cond else 'FAIL', name, str(detail)[:300]))
def blocked(name, fn, expect):
    try:
        fn(); R.append(('FAIL', name, 'not blocked'))
    except frappe.ValidationError as e:
        R.append(('PASS' if expect in str(e) else 'FAIL', name, str(e)[:300]))

from lotus_farm import warehouse as w, procurement as p
from lotus_farm.finance import setup, payments
try:
    company = 'Lotus Agritech'; tag = uuid.uuid4().hex[:6]; today = nowdate()
    make = lambda dt, **v: frappe.get_doc(dict(doctype=dt, **v)).insert()
    frappe.db.set_single_value('Lotus Finance Settings', 'vat_in_cost', 1)
    parent = frappe.db.get_value('Warehouse', {'company': company, 'is_group': 1}, 'name')
    A = make('Warehouse', warehouse_name='VAT A ' + tag, company=company, parent_warehouse=parent).name
    tonne = 'Tonne' if frappe.db.exists('UOM', 'Tonne') else make('UOM', uom_name='Tonne').name
    X = make('Item', item_code='VAT-DAP-' + tag, item_name='VAT DAP ' + tag, item_group='All Item Groups', stock_uom='Kg', is_stock_item=1,
             uoms=[dict(uom='Kg', conversion_factor=1), dict(uom=tonne, conversion_factor=1000)]).name
    supplier = frappe.db.get_value('Supplier', {'disabled': 0}, 'name')
    gl = lambda name: frappe.get_all('GL Entry', filters={'voucher_no': name, 'is_cancelled': 0}, fields=['account', 'debit', 'credit'])
    value_in = lambda name: sum(flt(r) for r in frappe.get_all('Stock Ledger Entry', filters={'voucher_no': name, 'is_cancelled': 0}, pluck='stock_value_difference'))
    line = dict(item=X, qty=8, uom=tonne, rate=26571428.571, vat='5')
    buy = lambda total, no, series='1C26TKN', **kw: w.create_draft(company, 'receipt', today, [dict(line)], target=A, receipt_reason='Purchase', supplier=supplier,
                                                                    invoice_series=series, invoice_no=no, invoice_date=today, invoice_total=total, client_event_id=uuid.uuid4().hex, **kw)

    # Mua nhanh theo hóa đơn, hộ kinh doanh: giá vốn = tổng cộng trên hóa đơn
    no = '0004' + tag
    r1 = buy(223200000, no, post=1)
    ok('mua nhanh ghi sổ', r1['docstatus'] == 1, r1)
    d1 = w.document('Stock Entry', r1['name'])
    it = d1['items'][0]
    ok('thành tiền 212.571.429', flt(it['net_amount']) == 212571429, it)
    ok('tiền thuế 10.628.571', flt(it['vat_amount']) == 10628571, it)
    ok('đơn giá giữ như hóa đơn', abs(flt(it['rate']) - 26571428.571) < 1e-3 and it['uom'] == tonne and flt(it['qty']) == 8, it)
    ok('thông tin hóa đơn lưu lại', d1['invoice_series'] == '1C26TKN' and d1['invoice_no'] == no and flt(d1['invoice_total']) == 223200000 and d1['vat_in_cost'], d1)
    ok('giá vốn nhập kho = 223.200.000', abs(value_in(r1['name']) - 223200000) < 0.01, value_in(r1['name']))
    debit152 = sum(flt(g['debit']) for g in gl(r1['name']) if g['account'].startswith('152'))
    ok('Nợ 152 đúng tổng hóa đơn, không có 1331', abs(debit152 - 223200000) < 0.01 and not any(g['account'].startswith('133') for g in gl(r1['name'])), gl(r1['name']))

    # Trùng hóa đơn: cùng NCC + ký hiệu + số bị chặn; cùng số khác ký hiệu là hóa đơn khác
    blocked('trùng ký hiệu + số bị chặn', lambda: buy(223200000, no), 'đã ghi ở phiếu nhập')
    r2 = buy(223200000, no, series='1C26XYZ')
    ok('cùng số khác ký hiệu được nhập', bool(r2.get('name')), r2)

    # Lệch tổng: vài đồng làm tròn được khớp vào tiền thuế; lệch lớn bị chặn
    r3 = buy(223200001, '0005' + tag)
    t3 = w.document('Stock Entry', r3['name'])['items'][0]
    ok('lệch 1 đồng khớp vào tiền thuế', flt(t3['vat_amount']) == 10628572 and flt(t3['net_amount']) == 212571429, t3)
    blocked('lệch lớn bị chặn', lambda: buy(223300000, '0006' + tag), 'Kiểm tra số lượng, đơn giá')

    # Không phải hộ kinh doanh: giá vốn chỉ gồm tiền hàng
    frappe.db.set_single_value('Lotus Finance Settings', 'vat_in_cost', 0)
    r4 = buy(223200000, '0007' + tag, post=1)
    ok('khấu trừ: giá vốn = tiền hàng 212.571.429', abs(value_in(r4['name']) - 212571429) < 0.01, value_in(r4['name']))
    frappe.db.set_single_value('Lotus Finance Settings', 'vat_in_cost', 1)

    # Lập hóa đơn cho phiếu Mua nhanh: hộ kinh doanh không cộng VAT lần hai và không ghi 1331
    inv = payments._invoice_stock_entries([r1['name']], no, today, posting_date=today, vat_code='5')
    pi = frappe.get_doc('Purchase Invoice', inv['invoice'])
    ok('hóa đơn = 223.200.000, không có dòng thuế', abs(flt(pi.grand_total) - 223200000) < 0.02 and not pi.taxes, (pi.grand_total, [t.account_head for t in pi.taxes]))
    ok('hóa đơn mang ký hiệu từ phiếu nhập', pi.get('lotus_einvoice_series') == '1C26TKN', pi.get('lotus_einvoice_series'))
    inv4 = payments._invoice_stock_entries([r4['name']], '0007' + tag, today, posting_date=today, vat_code='KCT')
    pi4 = frappe.get_doc('Purchase Invoice', inv4['invoice'])
    ok('khấu trừ: thuế theo dòng vào 1331', any(t.account_head.startswith('133') and abs(flt(t.tax_amount) - 10628571) < 0.01 for t in pi4.taxes)
       and abs(flt(pi4.grand_total) - 223200000) < 0.02, (pi4.grand_total, [(t.account_head, t.tax_amount) for t in pi4.taxes]))

    # Nhận hàng theo đơn (Purchase Receipt): VAT theo dòng vào giá vốn, không còn 0
    pr = frappe.get_doc(dict(doctype='Purchase Receipt', company=company, supplier=supplier, posting_date=today, set_warehouse=A,
                             items=[dict(item_code=X, qty=8, uom=tonne, conversion_factor=1000, rate=26571428.571, warehouse=A, lotus_line_vat='5')]))
    pr.set_missing_values()
    p.apply_line_taxes(pr)
    pr.calculate_taxes_and_totals()
    pr.update_valuation_rate()
    vat_row = next((t for t in pr.taxes if t.charge_type == 'On Net Total'), None)
    ok('nhận hàng: thuế tính vào giá vốn', vat_row is not None and vat_row.category == 'Valuation and Total' and abs(flt(vat_row.tax_amount) - 10628571.43) < 1, vat_row and (vat_row.category, vat_row.tax_amount, vat_row.account_head))
    ok('nhận hàng: giá trị định giá gồm thuế', abs(flt(pr.items[0].valuation_rate) * 8000 - flt(pr.grand_total)) < 1, (pr.items[0].valuation_rate, pr.grand_total))

    # Hóa đơn mua theo phiếu nhận: khớp từng đồng với tổng cộng trên hóa đơn
    pinv = frappe.get_doc(dict(doctype='Purchase Invoice', company=company, supplier=supplier, posting_date=today, bill_date=today,
                               items=[dict(item_code=X, qty=8, uom=tonne, conversion_factor=1000, rate=26571428.571, lotus_line_vat='5')]))
    pinv.set_missing_values()
    p.apply_line_taxes(pinv)
    pinv.calculate_taxes_and_totals()
    p._match_invoice_total(pinv, 223200000)
    ok('hóa đơn khớp 223.200.000', flt(pinv.grand_total) == 223200000, (pinv.grand_total, [(t.description, t.tax_amount) for t in pinv.taxes]))
    try:
        p._match_invoice_total(pinv, 224000000); R.append(('FAIL', 'hóa đơn lệch lớn bị chặn', 'not blocked'))
    except frappe.ValidationError as e:
        R.append(('PASS' if 'khác tổng cộng' in str(e) else 'FAIL', 'hóa đơn lệch lớn bị chặn', str(e)[:200]))

    # Lỗi B4: Tài chính › Chờ hạch toán lập hóa đơn theo phiếu nhận / hóa đơn dịch vụ cho hộ kinh doanh — không ghi 1331.
    def receipt():
        doc = frappe.get_doc(dict(doctype='Purchase Receipt', company=company, supplier=supplier, posting_date=today, set_warehouse=A,
                                  items=[dict(item_code=X, qty=8, uom=tonne, conversion_factor=1000, rate=26571428.571, warehouse=A, lotus_line_vat='5')]))
        doc.set_missing_values()
        p.apply_line_taxes(doc)
        doc.insert()
        doc.submit()
        return doc
    pr5 = receipt()
    inv5 = payments.make_goods_invoice([pr5.name], '0008' + tag, today, posting_date=today, vat_code='5')
    entries = gl(inv5['invoice'])
    ok('Tài chính: hóa đơn theo phiếu nhận không ghi 1331', entries and not any(g['account'].startswith('133') for g in entries), entries)
    clearing = setup.valuation_tax_account(company)
    left = sum(flt(g['debit']) - flt(g['credit']) for g in gl(pr5.name) + entries if g['account'] == clearing)
    ok('Tài chính: TK thuế tạm về 0 sau phiếu nhận + hóa đơn', abs(left) < 1, left)
    ok('Tài chính: tổng hóa đơn = 223.200.000', abs(flt(inv5['amount']) - 223200000) < 1, inv5)
    pr6 = receipt()
    blocked('Tài chính: thuế suất khác phiếu nhận bị chặn', lambda: payments.make_goods_invoice([pr6.name], '0009' + tag, today, posting_date=today, vat_code='8'),
            'lấy theo từng dòng phiếu nhận')
    svc = payments.make_service_invoice(supplier, '0010' + tag, today, [dict(description='Sửa máy bơm', amount=1000000, cost='admin')],
                                        posting_date=today, vat_code='8')
    entries = gl(svc['invoice'])
    admin = setup.mapping()['admin_expense']
    expense = sum(flt(g['debit']) for g in entries if g['account'] == admin)
    ok('Tài chính: hóa đơn dịch vụ không ghi 1331, thuế vào chi phí', not any(g['account'].startswith('133') for g in entries)
       and abs(flt(svc['amount']) - 1080000) < 0.5 and abs(expense - 1080000) < 0.5, (svc, entries))
except Exception:
    R.append(('FAIL', 'exception', traceback.format_exc()[-1500:]))
finally:
    frappe.db.rollback()
    for status, name, detail in R:
        print(status, '|', name, '|', detail)
    print('%d/%d passed' % (sum(1 for r in R if r[0] == 'PASS'), len(R)))
    frappe.destroy()
