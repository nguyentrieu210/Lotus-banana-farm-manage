"""Nhóm vật tư và kho dạng cây: tạo nhóm cha / con, chuyển nhánh, chặn vòng lặp, xóa nhóm còn con. Real site, rolled back.
SITE=<site> /home/frappe/frappe-bench/env/bin/python apps/lotus_farm/tests/integration/verify_master_tree.py"""
import os, traceback, uuid
import frappe

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
    company = 'Lotus Agritech'; t = uuid.uuid4().hex[:5]
    root = frappe.db.get_value('Item Group', {'parent_item_group': ['in', ['', None]]}, 'name')
    read = lambda kind, name: m.read_master(company, kind, name)
    save = lambda kind, node, **v: m.save_master(company, kind, node, read(kind, node)['modified'], v)

    # Nhóm vật tư
    A = w.create_master(company, 'group', dict(name='Cây A ' + t, parent=root, is_group=1))['name']
    B = w.create_master(company, 'group', dict(name='Cây B ' + t, parent=root, is_group=1))['name']
    leaf = w.create_master(company, 'group', dict(name='Lá ' + t, parent=A))['name']
    ok('tạo nhóm cha + nhóm con', frappe.db.get_value('Item Group', A, 'is_group') == 1 and frappe.db.get_value('Item Group', leaf, 'parent_item_group') == A)
    blocked('trùng tên nhóm bị chặn', lambda: w.create_master(company, 'group', dict(name='Lá ' + t, parent=B)), 'Đã có nhóm')
    save('group', leaf, name=leaf, parent=B)
    ok('chuyển nhóm con sang nhóm cha khác', frappe.db.get_value('Item Group', leaf, 'parent_item_group') == B)
    C = w.create_master(company, 'group', dict(name='Cây C ' + t, parent=A, is_group=1))['name']
    blocked('không chuyển nhóm vào nhánh con của nó', lambda: save('group', A, name=A, parent=C), 'nhánh con')
    blocked('nhóm cha phải là nhóm', lambda: save('group', C, name=C, parent=leaf), 'phải là nhóm')
    r = save('group', leaf, name='Lá mới ' + t, parent=B)
    ok('đổi tên nhóm', r['name'] == 'Lá mới ' + t and frappe.db.get_value('Item Group', r['name'], 'item_group_name') == 'Lá mới ' + t, r)
    tree = {g['name']: g for g in m.master_lists(company)['group_tree']}
    ok('cây nhóm có nhóm cha và con', tree[A]['is_group'] == 1 and tree['Lá mới ' + t]['parent'] == B and tree[root]['parent'] == '', tree.get(A))
    blocked('xóa nhóm còn nhóm con bị chặn', lambda: m.delete_master(company, 'group', A, read('group', A)['modified']), 'còn mục con')
    blocked('nhóm gốc không sửa được', lambda: read('group', root), 'Nhóm gốc')
    rd = read('group', B)
    ok('đọc nhóm cha: số nhóm con', rd['is_group'] == 1 and rd['child_count'] == 1, rd.get('child_count'))

    # Kho
    wroot = frappe.db.get_value('Warehouse', {'company': company, 'is_group': 1, 'parent_warehouse': ['in', ['', None]]}, 'name')
    G1 = w.create_master(company, 'warehouse', dict(name='Nhóm kho 1 ' + t, parent=wroot, is_group=1))['name']
    G2 = w.create_master(company, 'warehouse', dict(name='Nhóm kho 2 ' + t, parent=wroot, is_group=1))['name']
    K = w.create_master(company, 'warehouse', dict(name='Kho con ' + t, parent=G1))['name']
    ok('tạo nhóm kho + kho con', frappe.db.get_value('Warehouse', G1, 'is_group') == 1 and frappe.db.get_value('Warehouse', K, 'parent_warehouse') == G1)
    save('warehouse', K, name='Kho con ' + t, parent=G2)
    ok('chuyển kho sang nhóm kho khác', frappe.db.get_value('Warehouse', K, 'parent_warehouse') == G2)
    blocked('kho cha phải là nhóm kho', lambda: save('warehouse', G1, name='Nhóm kho 1 ' + t, parent=K), 'phải là nhóm')
    wt = {x['name']: x for x in m.master_lists(company)['warehouse_tree']}
    ok('cây kho có nhóm kho và kho con', wt[G2]['is_group'] == 1 and wt[K]['parent'] == G2 and wt[wroot]['parent'] == '', wt.get(K))
    blocked('xóa nhóm kho còn kho con bị chặn', lambda: m.delete_master(company, 'warehouse', G2, read('warehouse', G2)['modified']), 'còn mục con')
    m.delete_master(company, 'warehouse', G1, read('warehouse', G1)['modified'])
    ok('xóa nhóm kho rỗng', not frappe.db.exists('Warehouse', G1))
except Exception:
    R.append(('FAIL', 'exception', traceback.format_exc()[-1500:]))
finally:
    frappe.db.rollback()
    for status, name, detail in R:
        print(status, '|', name, '|', detail)
    print('%d/%d passed' % (sum(1 for r in R if r[0] == 'PASS'), len(R)))
    frappe.destroy()
