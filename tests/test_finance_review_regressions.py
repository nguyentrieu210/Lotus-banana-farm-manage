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
        # 1 200 kg came in this month; 250 kg of the first item are still on hand at month end, the second is sold out.
        responses = [[NS(item_code='BANANA', kg=1000), NS(item_code='SECOND', kg=200)], [(250,)], [(None,)]]
        db = NS(sql=lambda *a, **k: responses.pop(0))
        env = dict(frappe=NS(db=db), _bounds=lambda m: ('2026-10-01', '2026-10-31'),
                   _receipts=lambda company: ['SE-01'], flt=lambda x: float(x or 0))
        unsold = extract('lotus_farm/finance/costing.py', '_unsold', env)
        measured = unsold('LOTUS', '2026-10')
        self.assertEqual((measured['kg_received'], measured['kg_unsold'], measured['share']), (1200, 250, round(250 / 1200, 6)))
        # Older stock of the item on top of this month's: never more than the month's own kg.
        responses[:] = [[NS(item_code='BANANA', kg=1000)], [(1500,)]]
        self.assertEqual(unsold('LOTUS', '2026-10')['share'], 1)
        env['_receipts'] = lambda company: []
        self.assertEqual(unsold('LOTUS', '2026-10'), dict(kg_received=0, kg_unsold=0, share=0), 'no harvest receipt, nothing to measure')
        from lotus_farm.finance import rules
        pool = dict(lotus_farm='F', lotus_farm_block='A1', wip_open=0, cost_month=900_000, provisional=600_000, kg_harvested=300, kg_remaining=0)
        row = rules.costing_rows([pool], measured['share'])[0]
        self.assertEqual((row['adjustment'], row['unsold_adjustment'], row['wip_close']), (237_500, 62_500, 62_500),
                         'the difference of the fruit still in stock is not cost of goods sold: it stays in 154')

    def test_remaining_kg_come_from_the_shared_forecast_after_the_month(self):
        import datetime
        from contextlib import contextmanager
        from unittest.mock import patch
        import lotus_farm
        from lotus_farm.block_forecast_engine import date
        from lotus_farm.finance import rules
        from lotus_farm.forecast_parameters import DEFAULTS, validate
        session, asked = NS(user='accountant'), []

        @contextmanager
        def whole_farm():
            session.user = 'Administrator'
            try:
                yield
            finally:
                session.user = 'accountant'
        config = validate(DEFAULTS)
        cohorts = [dict(block='A1', cycle=2, config=config, days=[(datetime.date(2026, 11, 30), 7), (datetime.date(2026, 12, 1), 10)])]
        # The tree-count waves run 36 months from November 2026, the month of the farm's earliest estimated flowering date.
        reach = dict(until=datetime.date(2029, 10, 31), since=datetime.date(2026, 11, 1), waves=[(datetime.date(2029, 10, 31), config)],
                     flowering={'A-1': datetime.date(2026, 11, 1), 'B-1': datetime.date(2026, 12, 1)})
        forecast = NS(bunches_after=lambda farm, day: (asked.append((farm, day, session.user)), (cohorts, reach))[1])
        frappe = NS(session=session, throw=lambda message, *a: (_ for _ in ()).throw(ValueError(message)))
        forecast_kg = extract('lotus_farm/finance/costing.py', '_forecast_kg', dict(frappe=frappe, _whole_farm=whole_farm, rules=rules, getdate=date))
        with patch.object(lotus_farm, 'block_forecast', forecast, create=True):
            self.assertEqual(forecast_kg('F', '2026-11-30'), {'A1': round(10 * 20 * .98, 3)}, 'only the bunches due after the last day of the month')
            with self.assertRaises(ValueError) as short:
                forecast_kg('F', '2029-01-31')
            self.assertEqual(str(short.exception),
                             'Chưa tính được giá thành: dự thu theo số cây của vườn F chỉ tính tới 31/10/2029, vì khung dự thu bắt đầu từ tháng trổ dự kiến '
                             'sớm nhất của các lô; giá thành cần dự thu tới 23/11/2029 (hết một vòng cây sau ngày 31/01/2029). Ở Vườn & lô, cập nhật Trổ dự '
                             'kiến theo vụ đang trồng (cùng Vụ hiện tại) cho các lô có Trổ dự kiến trước 01/12/2026 (A-1), rồi tính lại.',
                             'January 2029 needs the forecast up to 23/11/2029: refused, not costed on a forecast cut short')
            reach['flowering'] = {'A-%02d' % i: datetime.date(2026, 11, i) for i in range(1, 13)}
            with self.assertRaises(ValueError) as short:
                forecast_kg('F', '2029-01-31')
            self.assertIn('(A-01, A-02, A-03, A-04, A-05, A-06, A-07, A-08, A-09, A-10, …), rồi tính lại.', str(short.exception))
        self.assertEqual(asked, [('F', '2026-11-30', 'Administrator')] + [('F', '2029-01-31', 'Administrator')] * 2, 'the whole farm, up to the month end')
        self.assertEqual(session.user, 'accountant')

    def test_costing_reads_the_lot_ledger_by_work_day_and_brings_the_rest_in_from_the_next_day(self):
        import datetime as dt
        from lotus_farm.block_forecast_engine import date, projection_config, source_rows
        calls, today = {}, ['2026-12-03']

        def lines(farm, blocks, until=None):
            calls['lines'] = (farm, blocks, until)
            return ['LINE']

        def cohorts(farm, blocks, waves, lines, start=None):
            calls['cohorts'] = (waves, lines, start)
            return ['COHORT']
        wave = dict(farm_block='FB-1', timing='PARAMETERS', harvest_window_end='2027-03-30')
        projected = [dict(name='FB-1', block_code='A-1', active=1, lotus_tree_count=1000, lotus_estimated_flowering_date='2026-11-15'),
                     dict(name='FB-2', block_code='', active=1, lotus_tree_count=500, lotus_estimated_flowering_date='2027-01-01'),
                     dict(name='FB-3', block_code='C-1', active=1, lotus_tree_count=0, lotus_estimated_flowering_date='2025-01-01')]
        env = dict(dt=dt, date=date, nowdate=lambda: today[0], source_rows=source_rows, projection_config=projection_config,
                   _projection=lambda farm: (dict(rows=[wave], window_start='2026-11-01', window_end='2029-10-31'), projected, []),
                   _bunch_scope=lambda farm: {'A1': {}}, _bunch_lines=lines, _bunch_cohorts=cohorts)
        after = extract('lotus_farm/block_forecast.py', 'bunches_after', env)
        found, reach = after('F', '2026-11-30')
        self.assertEqual(found, ['COHORT'])
        self.assertEqual(calls['lines'], ('F', {'A1': {}}, dt.date(2026, 11, 30)), 'the lines of work days up to the month end, whenever confirmed')
        self.assertEqual(calls['cohorts'], ([wave], ['LINE'], dt.date(2026, 12, 1)), 'a month already over: what is left comes in from the next day')
        self.assertEqual(reach, dict(until=dt.date(2029, 10, 31), since=dt.date(2026, 11, 1), waves=[(dt.date(2027, 3, 30), 'PARAMETERS')],
                                     flowering={'A-1': dt.date(2026, 11, 15), 'FB-2': dt.date(2027, 1, 1)}),
                         'how far the tree-count waves go, when each wave ends and by which parameters, and the flowering dates of the lô '
                         'the window starts from (a lô without a tree count has no waves)')
        today[0] = '2026-11-20'
        after('F', '2026-11-30')
        self.assertEqual(calls['cohorts'][2], dt.date(2026, 11, 20), 'a month still running: from today')

    def test_a_month_waits_for_its_shifts_and_draft_receipts(self):
        text = extract('lotus_farm/finance/costing.py', 'waiting_text', {})
        self.assertEqual(text(dict(shifts=[], drafts=[])), '')
        self.assertEqual(text(dict(shifts=['PS-1', 'PS-2'], drafts=['MAT-STE-9'])),
                         '2 ca đóng gói đã đóng chưa lập phiếu nhập kho, 1 phiếu nhập kho thành phẩm còn nháp (MAT-STE-9)')
        self.assertIn(', …', text(dict(shifts=[], drafts=['D%d' % i for i in range(7)])))

    def test_forecast_is_read_for_the_whole_farm_and_the_session_comes_back(self):
        from contextlib import contextmanager
        session, local = NS(user='accountant'), NS(user_perms='cached')
        whole_farm = contextmanager(extract('lotus_farm/finance/costing.py', '_whole_farm', dict(frappe=NS(session=session, local=local))))
        with self.assertRaises(RuntimeError):
            with whole_farm():
                self.assertEqual(session.user, 'Administrator')
                raise RuntimeError('the forecast failed')
        self.assertEqual((session.user, local.user_perms), ('accountant', None))

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