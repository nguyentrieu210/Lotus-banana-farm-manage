"""Committed synthetic concurrency scenarios, exclusively on procurement.test."""
import os
import runpy
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import uuid

assert os.environ.get('LOTUS_PROCUREMENT_TEST_ONLY')=='1'
m=runpy.run_path('/home/frappe/frappe-bench/apps/lotus_farm/tests/integration/verify_procurement.py',run_name='fixtures')
m['seed']()
g=m['seed'].__globals__
import frappe
from lotus_farm import procurement as p, signing, purchase_funding as funding


def connection(fn):
    def execute(*args):
        frappe.init(site='procurement.test',force=True)
        frappe.connect()
        assert frappe.local.site=='procurement.test'
        frappe.set_user(g['ACC'])
        try:
            for attempt in range(3):
                try:
                    result=fn(*args)
                    frappe.db.commit()
                    return ('ok',result)
                except frappe.QueryDeadlockError:
                    frappe.db.rollback()
                    if attempt==2:raise
        except frappe.ValidationError as exc:
            frappe.db.rollback()
            return ('refused',str(exc))
        finally:
            frappe.destroy()
    return execute


@connection
def payment(invoice,amount,key):
    return p.supplier_payment(g['C'],'Purchase Invoice',invoice,amount,'cash',g['DAY'],{'CHIEF':g['CHIEF'],'APPROVE':g['DIR']},key)


@connection
def refund(name,amount,key):
    return funding.reimburse(name,amount,g['DAY'],'cash',{'CHIEF':g['CHIEF'],'APPROVE':g['DIR']},key)


def invoice():
    case=m['ProcurementIntegration']()
    case.tag=uuid.uuid4().hex[:10]
    doc=case.invoice(case.receive(case.order(),10))
    frappe.db.commit()
    return case,doc


try:
    with patch.object(signing,'_notify',return_value=None):
        with ThreadPoolExecutor(max_workers=2) as pool:
            _,doc=invoice()
            token=uuid.uuid4().hex
            results=list(pool.map(lambda args:payment(*args),[(doc.name,300000,token)]*2))
            assert all(r[0]=='ok' for r in results),results
            assert len({r[1]['voucher'] for r in results})==1,results
            print('PASS: concurrent identical payment creates one native voucher')
            _,doc=invoice()
            results=list(pool.map(lambda args:payment(*args),[(doc.name,700000,uuid.uuid4().hex) for _ in range(2)]))
            assert sorted(r[0] for r in results)==['ok','refused'],results
            print('PASS: concurrent invoice reservations cannot exceed outstanding')
            case,doc=invoice()
            result,_=case.fund(doc,400000)
            m['signed'](result)
            frappe.db.commit()
            results=list(pool.map(lambda args:refund(*args),[(result['name'],300000,uuid.uuid4().hex) for _ in range(2)]))
            assert sorted(r[0] for r in results)==['ok','refused'],results
            print('PASS: concurrent reimbursement reservations cannot exceed funding')
    print('3 concurrency scenarios passed on procurement.test')
finally:
    frappe.db.rollback()
    frappe.destroy()
