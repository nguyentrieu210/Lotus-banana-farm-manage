"""Regression tests for finance review b1bf718 (without a running Frappe site).

These isolate the exact server functions with fake DB/actions. Integration tests
on ERPNext are additionally required before production deployment.
"""
import ast
import base64
from io import BytesIO
import json
from pathlib import Path
from types import SimpleNamespace as NS
import unittest

ROOT = Path(__file__).resolve().parents[1]


def extract(relative, function, env):
    tree = ast.parse((ROOT / relative).read_text(encoding='utf-8'))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == function)
    node.decorator_list = []
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(relative), 'exec'), env)
    return env[function]


class Doc:
    def __init__(self, doctype, **fields):
        self.doctype = doctype
        self.__dict__.update(fields)

    def get(self, name, default=None):
        return getattr(self, name, default)


class DummyDB:
    def __init__(self):
        self.updated = []
        self.links = []

    def exists(self, *args, **kwargs):
        return True

    def set_value(self, *args, **kwargs):
        self.updated.append((args, kwargs))


class FinanceSecurityTests(unittest.TestCase):
    def env(self, active=None):
        db = DummyDB()
        flags = NS(in_install=False, in_migrate=False, lotus_finance_reverse=False)
        frappe = NS(db=db, flags=flags, session=NS(user='accountant'),
                    get_all=lambda *a, **kw: db.links,
                    throw=lambda message, *a: (_ for _ in ()).throw(ValueError(message)))
        setup = NS(SETTINGS='Lotus Finance Settings', SIGNED_JE_KINDS=('Salary', 'Advance', 'Statutory'),
                   settings=lambda: NS(company='LOTUS', finance_enabled=1),
                   mapping=lambda: {'cash': '111', 'bank': '112'})
        posting = NS(POSTING='Lotus Accounting Posting', active=lambda *a: active)
        env = dict(frappe=frappe, setup=setup, posting=posting, flt=float,
                   getdate=lambda s: str(s), now_datetime=lambda: '2026-10-23T10:00:00')
        env['_enabled_for'] = extract('lotus_farm/finance/native_guards.py', '_enabled_for', env)
        env['payment_approved'] = lambda doc: False
        return env, db

    def test_native_payment_cannot_post_without_signatures(self):
        env, _ = self.env()
        guard = extract('lotus_farm/finance/native_guards.py', 'guard', env)
        with self.assertRaisesRegex(ValueError, 'chưa ký đủ'):
            guard(Doc('Payment Entry', company='LOTUS', posting_date='2026-10-12', payment_type='Pay'), 'before_submit')

    def test_direct_cash_journal_cannot_bypass_payment_approval(self):
        env, _ = self.env()
        guard = extract('lotus_farm/finance/native_guards.py', 'guard', env)
        voucher = Doc('Journal Entry', company='LOTUS', posting_date='2026-10-12', accounts=[
            NS(account='331', credit_in_account_currency=0),
            NS(account='112', credit_in_account_currency=50000),
        ])
        with self.assertRaisesRegex(ValueError, 'bút toán trực tiếp'):
            guard(voucher, 'before_submit')

    def test_result_closing_blocks_late_cost_entry(self):
        env, _ = self.env(active=NS(voucher_name='CLOSE-01'))
        guard = extract('lotus_farm/finance/native_guards.py', 'guard', env)
        with self.assertRaisesRegex(ValueError, 'đã kết chuyển'):
            guard(Doc('Purchase Invoice', company='LOTUS', posting_date='2026-10-12'), 'before_submit')

    def test_result_closing_cannot_be_undone_from_native_desk(self):
        env, db = self.env(active=NS(voucher_name='CLOSE-01'))
        db.links = [NS(purpose='Result Closing')]
        guard = extract('lotus_farm/finance/native_guards.py', 'guard', env)
        with self.assertRaisesRegex(ValueError, 'đã kết chuyển'):
            guard(Doc('Journal Entry', name='CLOSE-01', company='LOTUS', posting_date='2026-10-31'), 'before_cancel')

    def test_native_cancel_releases_unique_posting_key(self):
        env, db = self.env()
        db.links = ['LINK-01']
        cancelled = extract('lotus_farm/finance/native_guards.py', 'sync_cancel', env)
        cancelled(Doc('Payment Entry', company='LOTUS', name='PE-01'), 'on_cancel')
        self.assertEqual(len(db.updated), 1)
        values = db.updated[0][0][2]
        self.assertEqual(values['state'], 'Reversed')
        self.assertIsNone(values['active_key'])

    def test_a_changed_amount_blocks_the_next_signature(self):
        env = dict(chain_for=lambda doc: 'payment_voucher',
                   _rows=lambda doc: ([NS(state='Đã ký', content_hash='50k'), NS(state='Chờ ký')], 1),
                   _admin=lambda: False,
                   _validate_person=lambda *a: None, _company=lambda doc: 'LOTUS', fingerprint=lambda doc: '75k',
                   rules=NS(SIGNED='Đã ký', RETURNED='Trả lại', current=lambda rows: 1,
                            may_act=lambda *a: True, chain=lambda *a: {'steps': [None, NS()]}),
                   frappe=NS(session=NS(user='director'),
                             throw=lambda message, *a: (_ for _ in ()).throw(ValueError(message))))
        sign = extract('lotus_farm/signing.py', 'sign', env)
        with self.assertRaisesRegex(ValueError, 'ký lại'):
            sign(Doc('Payment Entry', name='PE-01'))

    def test_bad_opening_row_disables_entire_import_token(self):
        cache = NS(calls=[], set_value=lambda *a, **k: cache.calls.append(a))
        frappe = NS(session=NS(user='chief'), cache=cache, generate_hash=lambda length: 'TOKEN',
                    whitelist=lambda *a, **k: lambda f: f)
        setup = NS(require_chief=lambda: None, settings=lambda: NS(cutover_date='2026-10-01'),
                   company=lambda: 'LOTUS', SETTINGS='Lotus Finance Settings')
        env = dict(frappe=frappe, setup=setup, posting=NS(active=lambda *a: None),
                   _opening_rows=lambda *a: [dict(debit=100, credit=0, errors=[]),
                                               dict(debit=0, credit=100, errors=['TK sai'])],
                   base64=base64, json=json)
        preview = extract('lotus_farm/finance/api.py', 'opening_preview', env)
        result = preview(base64.b64encode(b'dummy').decode())
        self.assertEqual(result['token'], '')
        self.assertEqual(result['errors'], 1)
        self.assertEqual(cache.calls, [])

    def test_receivable_opening_requires_customer(self):
        from openpyxl import Workbook
        wb = Workbook()
        wb.active.append(['Số tài khoản', 'Mã nhà cung cấp', 'Dư Nợ', 'Dư Có', 'Mã lô', 'Ghi chú', 'Mã khách hàng'])
        wb.active.append(['131', '', 50000, '', '', '', 'KH-01'])
        out = BytesIO()
        wb.save(out)
        db = NS(exists=lambda doctype, name: doctype == 'Customer' and name == 'KH-01')
        frappe = NS(db=db, get_all=lambda *a, **k: [NS(name='131 - LOTUS', account_number='131',
                                                       is_group=0, account_type='Receivable', root_type='Asset')])
        env = dict(frappe=frappe, BytesIO=BytesIO, flt=lambda x: float(x or 0),
                   OPENING_COLUMNS=('Số tài khoản',))
        parse = extract('lotus_farm/finance/api.py', '_opening_rows', env)
        rows = parse(out.getvalue(), 'LOTUS')
        self.assertEqual(rows[0]['errors'], [])
        self.assertEqual(rows[0]['customer'], 'KH-01')
        self.assertEqual(rows[0]['account'], '131 - LOTUS')

    def test_unsold_harvest_never_generates_cogs_adjustment(self):
        responses = [[NS(item_code='BANANA', warehouse='FINISHED')],
                     [(10,)]]
        db = NS(sql=lambda *a, **k: responses.pop(0))
        frappe = NS(db=db)
        env = dict(frappe=frappe, _bounds=lambda m: ('2026-10-01', '2026-10-31'),
                   _receipts=lambda company: ['SE-01'], flt=lambda x: float(x or 0))
        check = extract('lotus_farm/finance/costing.py', '_unsold_inventory_issues', env)
        issues = check('LOTUS', '2026-10', [dict(adjustment=100000)])
        self.assertEqual(len(issues), 1)
        self.assertIn('632', issues[0])

    def test_historical_reconciliation_uses_payment_ledger_and_date(self):
        source = (ROOT / 'lotus_farm/finance/reports.py').read_text(encoding='utf-8')
        body = ast.get_source_segment(source, next(n for n in ast.parse(source).body
                             if isinstance(n, ast.FunctionDef) and n.name == 'reconciliation'))
        self.assertIn('tabPayment Ledger Entry', body)
        self.assertIn('posting_date<=%s', body)
        self.assertNotIn('sum(outstanding_amount)', body)
        # ERPNext PLE uses credit - debit for Payable, so payable PLE sums are positive.
        self.assertIn("source=as_of_party(m['payable_supplier'], 'Supplier')", body)


if __name__ == '__main__':
    unittest.main()