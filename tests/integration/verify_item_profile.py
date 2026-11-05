"""Vật tư: loại hàng (vật tư · CCDC · TSCĐ · mua dùng ngay như VPP), ngừng dùng, hàng mua / bán, lô & hạn dùng, mặc định mua hàng.
Real site, rolled back at the end:  SITE=<site> /home/frappe/frappe-bench/env/bin/python apps/lotus_farm/tests/integration/verify_item_profile.py"""
import os, traceback, uuid
import frappe
from frappe.utils import nowdate

frappe.init(site=os.environ.get('SITE', 'frontend'), sites_path='/home/frappe/frappe-bench/sites'); frappe.connect(); frappe.set_user('Administrator')
R = []
def ok(name, cond, detail=''):
    R.append(('PASS' if cond else 'FAIL', name, str(detail)[:300]))
def blocked(name, fn, expect):
    try:
        fn(); R.append(('FAIL', name, 'not blocked'))
    except frappe.ValidationError as e:
        R.append(('PASS' if expect in str(e) else 'FAIL', name, str(e)[:300]))

from lotus_farm import warehouse as w, warehouse_masters as m
try:
    company = 'Lotus Agritech'; tag = uuid.uuid4().hex[:6]
    group = frappe.db.get_value('Item Group', {'is_group': 0}, 'name')
    supplier = frappe.db.get_value('Supplier', {'disabled': 0}, 'name')
    wh = frappe.db.get_value('Warehouse', {'company': company, 'is_group': 0, 'disabled': 0}, 'name')
    base = lambda code, **kw: dict(code=code, name=code, group=group, uom='Nos', minimum_stock=0, **kw)
    read = lambda code: m.read_master(company, 'item', code)
    save = lambda code, **kw: m.save_master(company, 'item', code, read(code)['modified'], dict(base(code), **kw))

    # Vật tư mặc định: tồn kho, hàng mua, không bán
    a = 'IP-VT-' + tag
    w.create_master(company, 'item', base(a, is_purchase_item=1, is_sales_item=0))
    r = read(a)
    ok('vật tư: theo dõi tồn kho', r['kind'] == 'Material' and frappe.db.get_value('Item', a, 'is_stock_item') == 1, r)
    ok('vật tư: hàng mua, không bán', r['is_purchase_item'] == 1 and r['is_sales_item'] == 0, r)

    # VPP: mua dùng ngay, không vào kho
    v = 'IP-VPP-' + tag
    w.create_master(company, 'item', base(v, kind='Service'))
    ok('VPP: không theo dõi tồn kho', frappe.db.get_value('Item', v, ['is_stock_item', 'is_fixed_asset']) == (0, 0) and read(v)['kind'] == 'Service')

    # TSCĐ: bắt buộc nhóm tài sản, không vào kho
    blocked('TSCĐ thiếu nhóm tài sản bị chặn', lambda: w.create_master(company, 'item', base('IP-TS0-' + tag, kind='Asset')), 'nhóm tài sản')
    category = frappe.db.get_value('Asset Category', {}, 'name')
    if category:
        t = 'IP-TS-' + tag
        w.create_master(company, 'item', base(t, kind='Asset', asset_category=category))
        ok('TSCĐ: tài sản, không tồn kho', frappe.db.get_value('Item', t, ['is_fixed_asset', 'is_stock_item', 'asset_category']) == (1, 0, category))
    else:
        ok('TSCĐ: chưa có nhóm tài sản trên site (bỏ qua)', True)

    # Sửa: ngừng dùng, hàng bán, lô & hạn dùng, NCC và kho mặc định, thời gian chờ
    save(a, kind='Material', disabled=1, is_purchase_item=1, is_sales_item=1, has_batch_no=1, has_expiry_date=1, shelf_life_in_days=365,
         default_supplier=supplier, default_warehouse=wh, lead_time_days=7, min_order_qty=10)
    r = read(a)
    ok('ngừng dùng lưu được', r['disabled'] == 1, r)
    ok('hàng bán bật', r['is_sales_item'] == 1, r)
    ok('lô + hạn dùng 365 ngày', r['has_batch_no'] == 1 and r['has_expiry_date'] == 1 and r['shelf_life_in_days'] == 365, r)
    ok('NCC + kho mặc định theo công ty', r['default_supplier'] == supplier and r['default_warehouse'] == wh, r)
    ok('chờ hàng 7 ngày, đặt tối thiểu 10', r['lead_time_days'] == 7 and r['min_order_qty'] == 10, r)
    save(a, kind='Tool', disabled=0)
    ok('đổi vật tư ↔ công cụ dụng cụ', read(a)['kind'] == 'Tool' and read(a)['disabled'] == 0)

    # Đã nhập kho: không đổi sang TSCĐ / dịch vụ, không tắt lô
    b = 'IP-VT2-' + tag
    w.create_master(company, 'item', base(b))
    w.create_draft(company, 'receipt', nowdate(), [dict(item=b, qty=1, rate=1000)], target=wh, receipt_reason='Purchase', supplier=supplier, post=1)
    blocked('đã nhập kho: không đổi sang dùng ngay', lambda: save(b, kind='Service'), 'đã phát sinh chứng từ')
    blocked('đã nhập kho: không bật lô', lambda: save(b, kind='Material', has_batch_no=1), 'không bật / tắt quản lý theo lô')
    ok('đã nhập kho: form khóa lô', read(b)['has_ledger'] and read(b)['used'])
    blocked('kho mặc định phải thuộc công ty', lambda: save(b, kind='Material', default_warehouse='Không có kho này'), 'Kho mặc định')

    # Đơn vị tính: sửa được ngay trong app, không phải vào ERPNext
    for name in ('Bao', 'Can'):
        if not frappe.db.exists('UOM', name):
            frappe.get_doc(dict(doctype='UOM', uom_name=name)).insert()
    tonne = 'Tonne' if frappe.db.exists('UOM', 'Tonne') else frappe.get_doc(dict(doctype='UOM', uom_name='Tonne')).insert().name
    u = 'IP-DVT-' + tag
    w.create_master(company, 'item', dict(base(u), uom='Kg', conversions=[dict(uom='Bao', conversion_factor=50), dict(uom=tonne, conversion_factor=1000)]))
    conv = lambda code: {c['uom']: c['conversion_factor'] for c in read(code)['conversions']}
    ok('tạo vật tư với 2 đơn vị quy đổi', conv(u) == {'Bao': 50, tonne: 1000}, conv(u))
    m.save_master(company, 'item', u, read(u)['modified'], dict(base(u), uom=tonne, kind='Material', conversions=[dict(uom='Bao', conversion_factor=0.05)]))
    ok('đổi đơn vị gốc khi chưa nhập xuất, giữ quy đổi', read(u)['uom'] == tonne and conv(u) == {'Bao': 0.05}, (read(u)['uom'], conv(u)))
    m.save_master(company, 'item', u, read(u)['modified'], dict(base(u), uom='Kg', kind='Material', conversions=[dict(uom='Bao', conversion_factor=50)]))
    ok('đổi lại đơn vị gốc Kg', read(u)['uom'] == 'Kg' and conv(u) == {'Bao': 50})
    m.save_master(company, 'item', u, read(u)['modified'], dict(base(u), uom='Kg', kind='Material', conversions=[]))
    ok('bỏ hết đơn vị quy đổi', conv(u) == {})
    m.save_master(company, 'item', u, read(u)['modified'], dict(base(u), uom='Kg', kind='Material', conversions=[dict(uom='Bao', conversion_factor=50)]))
    w.create_draft(company, 'receipt', nowdate(), [dict(item=u, qty=1, uom='Bao', rate=500000)], target=wh, receipt_reason='Purchase', supplier=supplier, post=1)
    blocked('đã nhập xuất: không đổi đơn vị gốc (báo tiếng Việt)', lambda: m.save_master(company, 'item', u, read(u)['modified'], dict(base(u), uom=tonne, kind='Material', conversions=[dict(uom='Bao', conversion_factor=50)])), 'không đổi được đơn vị gốc')
    blocked('đã nhập xuất: giữ hệ số đơn vị đã dùng', lambda: m.save_master(company, 'item', u, read(u)['modified'], dict(base(u), uom='Kg', kind='Material', conversions=[dict(uom='Bao', conversion_factor=25)])), 'giữ hệ số')
    m.save_master(company, 'item', u, read(u)['modified'], dict(base(u), uom='Kg', kind='Material', conversions=[dict(uom='Bao', conversion_factor=50), dict(uom='Can', conversion_factor=20)]))
    ok('đã nhập xuất: vẫn thêm đơn vị mới', conv(u) == {'Bao': 50, 'Can': 20}, conv(u))
    blocked('đơn vị quy đổi trùng đơn vị gốc bị chặn', lambda: m.save_master(company, 'item', u, read(u)['modified'], dict(base(u), uom='Kg', kind='Material', conversions=[dict(uom='Kg', conversion_factor=1)])), 'phải khác đơn vị gốc')

    # Form Hàng mua (Mua hàng): đổi đơn vị gốc và loại hàng khi chưa có chứng từ
    from lotus_farm import procurement_masters as pm
    pcode = 'IP-PM-' + tag
    d = pm.save(company, 'items', dict(item_code=pcode, item_name=pcode, kind='Material', uom='Kg', group=group, conversions=[dict(uom='Bao', conversion_factor=50)]), uuid.uuid4().hex)
    d = pm.save(company, 'items', dict(d, uom=tonne, kind='Tool', conversions=[dict(uom='Bao', conversion_factor=0.05)]), uuid.uuid4().hex, name=pcode, modified=d['modified'])
    item = frappe.get_doc('Item', pcode)
    ok('Hàng mua: đổi đơn vị gốc + loại hàng sau khi tạo', item.stock_uom == tonne and m.item_kind(item) == 'Tool' and {r.uom: r.conversion_factor for r in item.uoms if r.uom != tonne} == {'Bao': 0.05},
       (item.stock_uom, m.item_kind(item), [(r.uom, r.conversion_factor) for r in item.uoms]))

    lst = {r.name: r for r in m.master_lists(company)['items']}
    ok('danh sách có loại hàng', lst[v].kind == 'Service' and lst[b].kind == 'Material', (lst[v].kind, lst[b].kind))
except Exception:
    R.append(('FAIL', 'exception', traceback.format_exc()[-1500:]))
finally:
    frappe.db.rollback()
    for status, name, detail in R:
        print(status, '|', name, '|', detail)
    print('%d/%d passed' % (sum(1 for r in R if r[0] == 'PASS'), len(R)))
    frappe.destroy()
