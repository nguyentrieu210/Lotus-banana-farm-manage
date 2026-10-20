"""Committed race tests. Run ONLY on the disposable journal clone."""
import os,uuid,threading
from concurrent.futures import ThreadPoolExecutor
import frappe
os.chdir('/home/frappe/frappe-bench/sites')
frappe.init(site='frontend');frappe.connect();frappe.set_user('Administrator')
assert frappe.conf.db_host=='lotus-journal-test-db','Disposable cloned DB required'
from lotus_farm.work_journal import save
farm=frappe.get_all('Farm',pluck='name')[0]
team=frappe.get_all('Work Team',filters={'farm':farm,'active':1},pluck='name')[0]
block=frappe.get_all('Farm Block',filters={'farm':farm,'active':1},pluck='name')[0]
work=frappe.get_all('Work Type',filters={'active':1},pluck='name')[0]
base={'farm':farm,'rows':[{'row_id':str(uuid.uuid4()),'work_team':team,'farm_block':block,'work_type':work,'quantity':10,'workdays':1,'notes':'Disposable concurrency test'}],'expected_user':'Administrator'}
days=[str(frappe.utils.add_days('2026-01-01',i)) for i in range(100) if not frappe.db.exists('Work Daily Journal',{'farm':farm,'posting_date':frappe.utils.add_days('2026-01-01',i)})][:2]
frappe.db.commit();frappe.destroy()

def race(args):
    gate=threading.Barrier(2)
    def run(payload):
        frappe.init(site='frontend');frappe.connect();frappe.set_user('Administrator')
        try:
            gate.wait(timeout=30)
            value=save(**payload);frappe.db.commit()
            return {'ok':True,'value':value}
        except Exception as exc:
            frappe.db.rollback();return {'ok':False,'error':type(exc).__name__,'detail':str(exc)}
        finally:frappe.destroy()
    with ThreadPoolExecutor(2) as pool:return [*pool.map(run,args)]

date=days[0];token=str(uuid.uuid4())
same=race([{**base,'date':date,'request_id':token}]*2)
assert all(r['ok'] for r in same),same
assert same[0]['value']['name']==same[1]['value']['name'],same
separate=race([{**base,'date':days[1],'request_id':str(uuid.uuid4())} for _ in range(2)])
assert sum(r['ok'] for r in separate)==1,separate
assert any(r.get('error')=='TimestampMismatchError' for r in separate),separate
frappe.init(site='frontend');frappe.connect();frappe.set_user('Administrator')
try:
    for day in days:
        assert frappe.db.count('Work Daily Journal',{'farm':farm,'posting_date':day})==1
    print('PASS: concurrent same-request retry returns same journal; competing creates serialize with one conflict and one row per farm/date')
finally:frappe.db.rollback();frappe.destroy()
