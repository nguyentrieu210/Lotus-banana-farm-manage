"""Read-only UAT of the supplied private workbook, on the disposable site only."""
import os
import runpy
from collections import Counter
assert os.environ.get('LOTUS_PROCUREMENT_TEST_ONLY')=='1'
m=runpy.run_path('/home/frappe/frappe-bench/apps/lotus_farm/tests/integration/verify_procurement.py',run_name='source_check')
import frappe
from lotus_farm.procurement_import import workbook_rows
try:
    rows=workbook_rows(open('/tmp/procurement-source.xlsx','rb').read())
    counts=Counter((r['sheet'],r['type'],r['month']) for r in rows)
    assert {r['month'] for r in rows if r['sheet']=='Vật tư'}=={'2026-11'}
    assert {r['month'] for r in rows if r['sheet'] in ('Phân bón','Thuốc')}=={'2026-10'}
    first=next(r for r in rows if r['sheet']=='Phân bón' and r['row']==6)
    assert first['qty']==660 and first['rate']==82000,first
    assert any(r['type']=='Quotation' and r['price_basis']=='Gross' for r in rows)
    print(dict((str(k),v) for k,v in counts.items()))
    print('PASS: original workbook months, pack conversion, and VAT-inclusive quotes preserved; no documents imported')
finally:
    frappe.db.rollback()
    frappe.destroy()
