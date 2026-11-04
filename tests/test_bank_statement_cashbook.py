"""Read-only import of farm cashbooks and cautious bank statement matching."""
import ast
import base64
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]


def extract(relative, name, scope):
    tree = ast.parse((ROOT / relative).read_text(encoding='utf-8'))
    node = next(x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == name)
    node.decorator_list = []
    exec(compile(ast.Module(body=[node], type_ignores=[]), relative, 'exec'), scope)
    return scope[name]


class BankCashbookTests(unittest.TestCase):
    def bank_parser(self):
        frappe = NS(throw=lambda message: (_ for _ in ()).throw(ValueError(message)))
        return extract('lotus_farm/finance/statements.py', '_statement_rows',
                       dict(base64=base64, BytesIO=BytesIO, frappe=frappe, flt=float))

    def book(self, sheet_name='Sổ quỹ'):
        book = Workbook()
        summary = book.active
        summary.title = 'Tổng hợp'
        summary.append(['SỔ QUỸ & ĐỐI CHIẾU SAO KÊ | VƯỜN 222'])
        sheet = book.create_sheet(sheet_name)
        sheet.append(['STT', 'Ngày', 'Thu (Có)', 'Chi (Nợ)', 'Số dư', 'Đối tượng', 'Diễn giải', 'Chứng từ'])
        sheet.append([1, '09/10/2026', 200_000, None, 200_000, 'A', 'Gửi tiền', '070'])
        sheet.append([2, '13/10/2026', None, '1.800.000', 198_200_000, 'B', 'Mua bạt', '060'])
        out = BytesIO(); book.save(out)
        return base64.b64encode(out.getvalue()).decode()

    def test_cashbook_is_found_in_second_sheet_and_has_signed_amounts(self):
        result = self.bank_parser()(self.book())
        self.assertEqual(len(result), 2)
        self.assertEqual([r['amount'] for r in result], [200_000, -1_800_000])
        self.assertEqual([r['reference'] for r in result], ['070', '060'])
        self.assertEqual(result[1]['date'], '2026-10-13')

    def test_invalid_file_is_rejected_without_crash(self):
        with self.assertRaisesRegex(ValueError, 'Excel'):
            self.bank_parser()(base64.b64encode(b'not an xlsx').decode())

    def matching(self):
        return extract('lotus_farm/finance/rules.py', 'match_bank', {})

    def test_exact_ref_outside_window_is_never_matched(self):
        result = self.matching()(
            [dict(date='2026-10-01', amount=200, reference='REF123')],
            [dict(date='2026-10-30', amount=200, reference='REF123', voucher='JE1')],3)
        self.assertEqual(len(result['matched']),0)

    def test_conflicting_references_not_matched(self):
        result = self.matching()(
            [dict(date='2026-10-01', amount=200, reference='REF_A')],
            [dict(date='2026-10-01', amount=200, reference='REF_B', voucher='JE1')],3)
        self.assertEqual(len(result['matched']),0)

    def test_ambiguous_reference_free_payments_not_matched(self):
        result = self.matching()(
            [dict(date='2026-10-01', amount=200, reference='')],
            [dict(date='2026-10-01', amount=200, reference='', voucher='JE1'),
             dict(date='2026-10-01', amount=200, reference='', voucher='JE2')],3)
        self.assertEqual(len(result['matched']),0)

    def test_unique_date_amount_pair_can_match_when_ref_missing(self):
        result = self.matching()(
            [dict(date='2026-10-01', amount=200, reference='ABC')],
            [dict(date='2026-10-02', amount=200, reference='', voucher='JE1')],3)
        self.assertEqual(result['matched'][0]['ledger']['voucher'],'JE1')

    def test_unique_exact_ref_is_matched(self):
        result = self.matching()(
            [dict(date='2026-10-01', amount=200, reference='REF_A')],
            [dict(date='2026-10-02', amount=200, reference='REF_A', voucher='JE1')],3)
        self.assertEqual(len(result['matched']),1)


if __name__ == '__main__':
    unittest.main()
