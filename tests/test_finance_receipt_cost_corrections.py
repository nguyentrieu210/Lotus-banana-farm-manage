import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

source=Path(__file__).resolve().parents[1]/'lotus_farm/finance/payments.py'
tree=ast.parse(source.read_text())
fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='_receipt_cost_corrections')
fn.decorator_list=[]

class FakeFrappe:
  def __init__(self,rows):
    self.rows=rows
  def get_all(self,doctype,filters,fields,limit_page_length):
    assert doctype=='Stock Reconciliation'
    assert filters['docstatus']==1
    assert filters['expense_account']=='3388'
    return self.rows
  def throw(self,msg):
    raise ValueError(msg)

def handler(rows):
    env={'frappe':FakeFrappe(rows),'setup':SimpleNamespace(company=lambda:'Lotus Agritech',mapping=lambda:{'received_not_billed':'3388'}),'flt':float,'_CORRECTION_KEY':'lotus-cost-of-receipt:'}
    exec(compile(ast.Module(body=[fn],type_ignores=[]),str(source),'exec'),env)
    return env['_receipt_cost_corrections']

class CostTests(unittest.TestCase):
  def test_empty(self):
    self.assertEqual(handler([])([]),{})
  def test_single(self):
    row=SimpleNamespace(name='RECO1',lotus_client_key='lotus-cost-of-receipt:MAT-STE-2026-00038',difference_amount=105000000)
    self.assertEqual(handler([row])(['MAT-STE-2026-00038']),{'MAT-STE-2026-00038':105000000.0})
  def test_duplicates_rejected(self):
    rows=[SimpleNamespace(name='a',lotus_client_key='lotus-cost-of-receipt:MAT-STE-2026-00038',difference_amount=100),
          SimpleNamespace(name='b',lotus_client_key='lotus-cost-of-receipt:MAT-STE-2026-00038',difference_amount=200)]
    with self.assertRaisesRegex(ValueError,'nhiều lần'):
      handler(rows)(['MAT-STE-2026-00038'])
  def test_negative_receipt_price_correction_accepted(self):
    row=SimpleNamespace(name='RECO-GREEN',lotus_client_key='lotus-cost-of-receipt:MAT-STE-2026-00029:v1',difference_amount=-8160000)
    self.assertEqual(handler([row])(['MAT-STE-2026-00029']),{'MAT-STE-2026-00029':-8160000.0})
  def test_zero_correction_rejected(self):
    row=SimpleNamespace(name='RECO1',lotus_client_key='lotus-cost-of-receipt:MAT-STE-2026-00038:v1',difference_amount=0)
    with self.assertRaisesRegex(ValueError,'không có chênh lệch'):
      handler([row])(['MAT-STE-2026-00038'])

if __name__=='__main__':
 unittest.main()
