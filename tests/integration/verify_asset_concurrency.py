"""Race real approvals on separate database connections in the dedicated test site only."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import uuid

from verify_fixed_assets import SITE, a, accounts, frappe, seed, mi, workbook


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
    number=str(int(tag,16)+9000000000)
    root=frappe.db.get_value('Account',{'company':'Lotus Agritech','root_type':'Asset','parent_account':['is','not set']},'name')
    content=workbook('accounts',[[number,'Tài khoản kiểm thử đồng thời '+tag,root,0,'Fixed Asset']])
    preview=mi.preview('accounts',content);assert preview['valid'],preview
    frappe.db.commit()
    account=race(mi.commit,dict(kind='accounts',content=content,fingerprint=preview['fingerprint']))['names'][0]
    title='Nhóm kiểm thử đồng thời '+tag
    content=workbook('categories',[[title,0,number,'2141','6274','2411']])
    preview=mi.preview('categories',content);assert preview['valid'],preview
    frappe.db.commit()
    category=race(mi.commit,dict(kind='categories',content=content,fingerprint=preview['fingerprint']))['names'][0]
    assert frappe.db.count('Account',{'account_number':number,'company':'Lotus Agritech'})==1
    assert frappe.db.count('Asset Category',{'name':category})==1
    frappe.delete_doc('Asset Category',category,ignore_permissions=True)
    frappe.delete_doc('Account',account,ignore_permissions=True)
    frappe.db.commit()
    accounts_now=accounts()
    values=dict(asset_category_name='Nhóm sửa đồng thời '+tag,fixed_asset_account=accounts_now['211'],
        accumulated_depreciation_account=accounts_now['2141'],depreciation_expense_account=accounts_now['6274'],capital_work_in_progress_account=accounts_now['2411'])
    category=a.save_category(values)['name']
    values.update(name=category,modified=str(frappe.db.get_value('Asset Category',category,'modified')),depreciation_expense_account=accounts_now['6424'])
    frappe.db.commit()
    race(a.save_category,dict(values=values))
    location=a.save_location('Vị trí sửa đồng thời '+tag)['name']
    modified=str(frappe.db.get_value('Location',location,'modified'))
    frappe.db.commit()
    race(a.save_location,dict(name=location,modified=modified,location_name='Nhãn mới '+tag))
    assert frappe.db.get_value('Location',location,'location_name')==location
    frappe.delete_doc('Location',location,ignore_permissions=True)
    frappe.delete_doc('Asset Category',category,ignore_permissions=True)
    frappe.db.commit()
    from unittest.mock import patch
    rows=[['Nhóm nhập lại A '+tag,0,'211','2141','6274','2411'],['Nhóm nhập lại B '+tag,0,'211','2141','6274','2411']]
    content=workbook('categories',rows);preview=mi.preview('categories',content)
    frappe.db.commit()
    original=a.save_category;calls=[];injected=[False]
    def deadlock(values):
        calls.append(values['asset_category_name'])
        if values['asset_category_name']==rows[1][0] and not injected[0]:
            injected[0]=True
            frappe.db.rollback()  # Model MariaDB aborting the whole transaction and dropping savepoints.
            raise frappe.QueryDeadlockError('Injected deadlock after the first category')
        return original(values)
    with patch.object(a,'save_category',side_effect=deadlock):
        result=mi.commit('categories',content,preview['fingerprint'])
    assert result['count']==2,result
    assert calls==[rows[0][0],rows[1][0],rows[0][0],rows[1][0]],calls
    for row in rows:
        assert frappe.db.count('Asset Category',{'name':row[0]})==1
        frappe.delete_doc('Asset Category',row[0],ignore_permissions=True)
    frappe.db.commit()
    print('PASS: six concurrency races and a whole-import deadlock retry; writes occur once and an interrupted import restarts from its first row.')
    frappe.destroy()
