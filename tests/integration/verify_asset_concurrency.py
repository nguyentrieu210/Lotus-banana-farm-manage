"""Race real approvals on separate database connections in the dedicated test site only."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import uuid

from verify_fixed_assets import SITE, a, accounts, frappe, seed


def race(method, args):
    barrier = Barrier(2)

    def worker(_):
        frappe.init(site=SITE)
        frappe.connect()
        frappe.set_user('asset-chief@example.invalid')
        try:
            barrier.wait(timeout=15)
            result = method(**args)
            frappe.db.commit()
            return dict(ok=True, result=result)
        except Exception as exc:
            frappe.db.rollback()
            return dict(ok=False, error=str(exc), type=type(exc).__name__)
        finally:
            frappe.destroy()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(worker, range(2)))
    assert sum(r['ok'] for r in results) == 1, results
    assert next(r for r in results if not r['ok'])['type'] == 'ValidationError', results
    print(results)
    return next(r['result'] for r in results if r['ok'])


if __name__ == '__main__':
    seed()
    for row in frappe.get_all(a.RUN, filters={'state':'Posted'}, fields=['name']):
        a.depreciation_reverse(row.name, 'Dọn lần kiểm thử đồng thời trước')
    for row in frappe.get_all(a.OP, filters={'kind':'Create','state':['!=','Cancelled']}, fields=['name','payload']):
        if a._json(row.payload,{}).get('code','').startswith('RACE-'):
            a.operation_cancel(row.name, 'Dọn lần kiểm thử đồng thời trước')
    frappe.db.commit()
    tag = uuid.uuid4().hex[:8]
    pending = a.save_asset(dict(code='RACE-'+tag, asset_name='Máy kiểm thử đồng thời '+tag,
        asset_category='Máy tài sản kiểm thử', location='Kho tài sản A', existing=False,
        purchase_date='2026-09-01', available_for_use_date='2026-09-01', posting_date='2026-09-01',
        amount=120000000, months=24, opening_depreciation=0, booked_months=0, salvage_value=0,
        supplier='Nhà cung cấp tài sản kiểm thử', lotus_farm='F-TEST-A'))
    preview = a.operation_preview(pending['name'])
    frappe.db.commit()
    result = race(a.operation_post, dict(name=pending['name'], fingerprint=preview['fingerprint']))
    assert frappe.db.count('Asset', {'lotus_asset_code':'RACE-'+tag}) == 1
    preview = a.depreciation_preview('2026-09')
    assert not preview['errors'], preview
    frappe.db.commit()
    run = race(a.depreciation_post, dict(month='2026-09', fingerprint=preview['fingerprint']))
    assert frappe.db.count(a.RUN, {'state':'Posted', 'month':'2026-09'}) == 1
    a.depreciation_reverse(run['name'], 'Dọn dữ liệu kiểm thử đồng thời')
    a.operation_cancel(result['name'], 'Dọn tài sản kiểm thử đồng thời')
    frappe.db.commit()
    print('PASS: simultaneous operation and month approvals each post exactly once; both reversed cleanly.')
    frappe.destroy()
