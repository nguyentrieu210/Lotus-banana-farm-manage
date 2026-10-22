"""Bán hàng, phải thu, VAT on the real site, rolled back: a customer, a sales invoice that also ships the bananas
(Nợ 632 / Có 155 at stock value, Nợ 131 / Có 511), one with 8% VAT (Có 33311), duplicate e-invoice numbers and rates not in
force refused, a partial receipt then the rest (131 back to 0 for that customer), a service purchase with 10% input VAT
(Nợ 1331), the monthly VAT listing agreeing with 1331 / 33311 and the reconciliation including receivables.
Needs finance switched on with the Thông tư 99 chart and install_finance."""
import json
import unicodedata
import uuid

import frappe
from frappe.utils import flt, nowdate

frappe.init(site='frontend', sites_path='/home/frappe/frappe-bench/sites')
frappe.connect()
frappe.set_user('Administrator')
from lotus_farm.finance import payments, reports, sales, setup  # noqa: E402

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
    raise AssertionError('expected refusal: %s' % getattr(fn, '__name__', fn))


def gl(voucher):
    return frappe.db.sql("""select account, debit, credit from `tabGL Entry` where voucher_no=%s and is_cancelled=0""", voucher, as_dict=True)


def side(lines, account, f):
    return sum(flt(x[f]) for x in lines if x.account == account)


try:
    cfg = setup.settings()
    assert cfg.finance_enabled and cfg.coa_version, 'finance must be on with the TT99 chart'
    company = setup.company()
    m = setup.mapping()
    for key in ('receivable_customer', 'sales_revenue', 'output_vat', 'input_vat'):
        assert m.get(key), key
    # stock of packed bananas in a fruit warehouse (155)
    wh = frappe.get_doc(dict(doctype='Warehouse', warehouse_name='Kho thành phẩm ' + tag, company=company, account=m['finished_goods'])).insert(ignore_permissions=True).name
    item = frappe.get_doc(dict(doctype='Item', item_code='CHUOI-THUNG-' + tag, item_name='Chuối thùng 13kg ' + tag, item_group='All Item Groups',
                               stock_uom='Nos', is_stock_item=1)).insert(ignore_permissions=True).name
    se = frappe.get_doc(dict(doctype='Stock Entry', company=company, stock_entry_type='Material Receipt', purpose='Material Receipt', posting_date=today,
                             set_posting_time=1, lotus_receipt_reason='Surplus', items=[dict(item_code=item, qty=100, t_warehouse=wh, basic_rate=150000)]))
    se.flags.ignore_permissions = True
    se.insert()
    se.submit()
    assert any(r.item_code == item and r.warehouse == wh for r in sales.stock_for_sale())

    c = sales.save_customer(json.dumps(dict(customer_name='Công ty Xuất khẩu ' + tag, tax_id='0312' + str(int(tag, 16) % 1000000).zfill(6), credit_days=15)))
    refused(sales.save_customer, json.dumps(dict(customer_name='Trùng MST', tax_id=frappe.db.get_value('Customer', c['name'], 'tax_id'))), text='đã có khách hàng')

    first = sales.make_sales_invoice(c['name'], today, json.dumps([dict(item_code=item, warehouse=wh, qty=40, rate=260000)]), 'KCT', None, 'C26TLT', '0000' + tag)
    lines = gl(first['invoice'])
    assert side(lines, m['receivable_customer'], 'debit') == 10_400_000 and side(lines, m['sales_revenue'], 'credit') == 10_400_000, lines
    assert side(lines, m['cost_of_goods_sold'], 'debit') == 6_000_000 and side(lines, m['finished_goods'], 'credit') == 6_000_000, lines
    assert not side(lines, m['output_vat'], 'credit')
    refused(sales.make_sales_invoice, c['name'], today, json.dumps([dict(item_code=item, warehouse=wh, qty=1, rate=1)]), 'KCT', None, 'C26TLT', '0000' + tag,
            text='đã được dùng')
    refused(sales.make_sales_invoice, c['name'], today, json.dumps([dict(item_code=item, warehouse=wh, qty=1, rate=1)]), '7', text='không áp dụng')
    second = sales.make_sales_invoice(c['name'], today, json.dumps([dict(item_code=item, warehouse=wh, qty=10, rate=100000)]), '8')
    lines2 = gl(second['invoice'])
    assert side(lines2, m['output_vat'], 'credit') == 80_000 and side(lines2, m['receivable_customer'], 'debit') == 1_080_000, lines2

    ar = sales.receivables()
    mine = next(r for r in ar['customers'] if r['customer'] == c['name'])
    assert mine['owed'] == 11_480_000 and mine['open_invoices'] == 2, mine
    refused(sales.receive_payment, c['name'], json.dumps([dict(invoice=first['invoice'], amount=10_400_001)]), 'cash', today, text='chỉ còn phải thu')
    part = sales.receive_payment(c['name'], json.dumps([dict(invoice=first['invoice'], amount=4_000_000)]), 'cash', today)
    rest = sales.receive_payment(c['name'], json.dumps([dict(invoice=first['invoice'], amount=6_400_000), dict(invoice=second['invoice'], amount=1_080_000)]),
                                 'bank', today, 'BC-' + tag)
    assert side(gl(rest['receipt']), m['bank'], 'debit') == 7_480_000
    mine = next(r for r in sales.receivables()['customers'] if r['customer'] == c['name'])
    assert mine['owed'] == 0 and mine['received'] == 11_480_000, mine

    supplier = frappe.get_all('Supplier', filters={'disabled': 0}, pluck='name', limit_page_length=1)[0]
    block = frappe.get_all('Farm Block', fields=['name', 'farm'], limit_page_length=1)[0]
    service = payments.make_service_invoice(supplier, 'DV-' + tag, today, json.dumps([dict(description='Thuê máy cày', amount=2_000_000, cost='production',
                                                                                          lotus_farm=block.farm, lotus_farm_block=block.name)]), None, None, '10')
    sl = gl(service['invoice'])
    assert side(sl, m['input_vat'], 'debit') == 200_000 and side(sl, m['payable_supplier'], 'credit') == 2_200_000 and side(sl, m['overhead_service'], 'debit') == 2_000_000, sl

    vat = sales.vat_report(month)
    assert all(ch['ok'] for ch in vat['checks']), vat['checks']
    assert any(s['name'] == second['invoice'] and s['code'] == '8' and flt(s['tax']) == 80_000 for s in vat['sales'])
    assert any(p['name'] == service['invoice'] and p['code'] == '10' for p in vat['purchases'])
    sales.export_vat(month)
    assert frappe.local.response.filecontent
    recon = reports.reconciliation(today)['checks']
    ar_check = next(ch for ch in recon if ch['label'].startswith('Phải thu khách hàng'))
    assert ar_check['ok'], ar_check
    report.update(invoices=[first['invoice'], second['invoice']], receipts=[part['receipt'], rest['receipt']], service=service['invoice'],
                  vat=dict(input=vat['summary']['input_tax'], output=vat['summary']['output_tax'], payable=vat['summary']['payable']), rollback=True)
finally:
    frappe.set_user('Administrator')
    frappe.db.rollback()
print(json.dumps(report, ensure_ascii=False, default=str))
