import unittest
from unittest.mock import Mock

from lotus_farm.ai_reports import answer


class FastReportsTest(unittest.TestCase):
    def run_report(self, question, responses):
        def query(doctype, fields, **kwargs):
            return {'rows': responses[doctype]}
        reader = Mock(side_effect=query)
        result = answer([{'role': 'user', 'content': question}], reader, '2026-10-26')
        return result, reader

    def test_active_employees_are_counted_with_permissions_not_a_model(self):
        result, reader = self.run_report('Có bao nhiêu nhân viên đang làm việc?', {'Employee': [{'total': 118}]})
        self.assertIn('118 nhân viên', result['answer'])
        reader.assert_called_once_with('Employee', ['count(name) as total'], filters=[['status', '=', 'Active']])
        self.assertEqual(result['route'], 'direct')

    def test_employee_groups_keep_unassigned_people(self):
        result, _ = self.run_report('Có bao nhiêu nhân viên đang làm việc ở mỗi vườn?',
                                    {'Employee': [{'lotus_farm': 'A', 'total': 4}, {'lotus_farm': None, 'total': 6}]})
        self.assertIn('10 nhân viên', result['answer'])
        self.assertIn('Chưa gán vườn', result['answer'])

    def test_followups_are_not_reinterpreted_without_the_previous_scope(self):
        query = Mock()
        result = answer([{'role': 'user', 'content': 'Chỉ xem vườn 222'},
                         {'role': 'user', 'content': 'Có bao nhiêu nhân viên đang làm việc?'}], query, '2026-10-26')
        self.assertIsNone(result)
        query.assert_not_called()
        self.assertIsNone(answer([{'role': 'user', 'content': 'Tồn kho ở vườn 222 hôm qua'}], query, '2026-10-26'))

    def test_inventory_never_combines_units_or_companies_for_thresholds(self):
        result, _ = self.run_report('Tồn kho hiện tại ở từng kho, vật tư nào sắp hết?', {
            'Bin': [{'warehouse': 'A1', 'item_code': 'I', 'stock_uom': 'Kg', 'actual_qty': 2},
                    {'warehouse': 'A2', 'item_code': 'I', 'stock_uom': 'Kg', 'actual_qty': 3},
                    {'warehouse': 'B1', 'item_code': 'I', 'stock_uom': 'Kg', 'actual_qty': 10},
                    {'warehouse': 'A1', 'item_code': 'J', 'stock_uom': 'Chai', 'actual_qty': 100}],
            'Warehouse': [{'name': 'A1', 'company': 'Công ty A'}, {'name': 'A2', 'company': 'Công ty A'}, {'name': 'B1', 'company': 'Công ty B'}],
            'Item': [{'name': 'I', 'item_name': 'Phân', 'lotus_minimum_stock_global': 6},
                     {'name': 'J', 'item_name': 'Thuốc', 'lotus_minimum_stock_global': 0}],
        })
        self.assertIn('| Công ty A | Phân | Kg | 5 | 6 |', result['answer'])
        self.assertNotIn('| Công ty B | Phân | Kg | 5', result['answer'])
        self.assertNotIn('115', result['answer'])

    def test_capped_inventory_does_not_invent_a_low_stock_conclusion(self):
        result, _ = self.run_report('Tồn kho hiện tại', {
            'Bin': [{'warehouse': 'A', 'item_code': 'I', 'stock_uom': 'Kg', 'actual_qty': 1}] * 500,
            'Warehouse': [{'name': 'A', 'company': 'C'}],
            'Item': [{'name': 'I', 'item_name': 'Phân', 'lotus_minimum_stock_global': 1000}],
        })
        self.assertIn('giới hạn 500', result['answer'])
        self.assertNotIn('ngưỡng tối thiểu đã cấu hình', result['answer'])

    def test_expenses_preserve_company_currency_and_the_exact_period(self):
        result, reader = self.run_report('Chi phí tháng này theo tài khoản là bao nhiêu?', {
            'Account': [{'name': 'E1', 'account_name': 'Chi phí A', 'company': 'A'},
                        {'name': 'E2', 'account_name': 'Chi phí B', 'company': 'B'}],
            'GL Entry': [{'account': 'E1', 'debit': '120.05', 'credit': '20.05'},
                         {'account': 'E2', 'debit': '4', 'credit': '1'}],
            'Company': [{'name': 'A', 'default_currency': 'VND'}, {'name': 'B', 'default_currency': 'USD'}],
        })
        self.assertIn('| A | Chi phí A | 100 | VND |', result['answer'])
        self.assertIn('| B | Chi phí B | 3 | USD |', result['answer'])
        gl = next(call for call in reader.call_args_list if call.args[0] == 'GL Entry')
        self.assertIn(['posting_date', 'between', ['2026-10-01', '2026-10-26']], gl.kwargs['filters'])
        self.assertIn(['is_cancelled', '=', 0], gl.kwargs['filters'])

    def test_orders_exclude_drafts_cancelled_and_closed_documents(self):
        reads = []
        def query(doctype, fields, **kwargs):
            reads.append(kwargs)
            return {'rows': [{'total': 0}] if 'count(name) as total' in fields else []}
        result = answer([{'role': 'user', 'content': 'Đơn mua nào đang chờ nhận hàng?'}], query, '2026-10-26')
        self.assertIn('0 đơn mua', result['answer'])
        self.assertIn(['docstatus', '=', 1], reads[0]['filters'])
        self.assertIn(['status', 'not in', ['Closed', 'Stopped', 'Cancelled']], reads[0]['filters'])

    def test_no_attendance_records_is_not_a_claim_that_everyone_is_absent(self):
        result, reader = self.run_report('Hôm nay có bao nhiêu nhân viên đi làm?', {'Attendance': []})
        self.assertIn('không đồng nghĩa', result['answer'])
        self.assertEqual(reader.call_args.kwargs['group_by'], 'employee')
        self.assertIn(['docstatus', '=', 1], reader.call_args.kwargs['filters'])


if __name__ == '__main__':
    unittest.main()
