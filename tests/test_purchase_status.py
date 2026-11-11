import unittest

from lotus_farm import purchase_status as ps


class PurchaseStatus(unittest.TestCase):
    def test_order_before_approval(self):
        self.assertEqual(ps.order_state(0), 'Nháp')
        self.assertEqual(ps.order_state(0, 'Nháp'), 'Nháp')
        self.assertEqual(ps.order_state(0, 'Chờ duyệt'), 'Chờ duyệt')
        self.assertEqual(ps.order_state(0, 'Từ chối'), 'Bị trả lại')  # stored by older releases
        self.assertEqual(ps.order_state(0, 'Bị trả lại'), 'Bị trả lại')
        self.assertEqual(ps.order_state(2, 'Chờ duyệt', 'Cancelled'), 'Đã hủy')

    def test_order_after_approval_follows_precedence(self):
        self.assertEqual(ps.order_state(1, status='To Receive and Bill', ordered=10), 'Đã duyệt')
        self.assertEqual(ps.order_state(1, status='To Receive and Bill', sent=True, ordered=10), 'Đã gửi NCC')
        self.assertEqual(ps.order_state(1, status='To Receive and Bill', sent=True, confirmed=True, ordered=10), 'NCC đã xác nhận')
        self.assertEqual(ps.order_state(1, status='To Receive and Bill', sent=True, confirmed=True, ordered=10, received=4), 'Đang nhận')
        self.assertEqual(ps.order_state(1, status='To Bill', ordered=10, received=10), 'Đã nhận đủ')
        self.assertEqual(ps.order_state(1, status='Completed', ordered=10, received=9), 'Đã nhận đủ')
        self.assertEqual(ps.order_state(1, status='Closed', ordered=10, received=10), 'Đã đóng')
        self.assertEqual(ps.order_state(1, status='Closed', ordered=10, received=3), 'Đã đóng')
        for state in (ps.order_state(d, a) for d in (0, 1, 2) for a in ('', 'Chờ duyệt', 'Từ chối')):
            self.assertIn(state, ps.ORDER_STATES)

    def test_overdue_is_a_flag_for_open_orders_only(self):
        self.assertTrue(ps.order_overdue(1, 'To Receive', '2026-11-01', '2026-11-10', 10, 4))
        self.assertFalse(ps.order_overdue(1, 'To Receive', '2026-11-10', '2026-11-10', 10, 4))
        self.assertFalse(ps.order_overdue(1, 'Closed', '2026-11-01', '2026-11-10', 10, 4))
        self.assertFalse(ps.order_overdue(1, 'To Bill', '2026-11-01', '2026-11-10', 10, 10))
        self.assertFalse(ps.order_overdue(0, 'Draft', '2026-11-01', '2026-11-10', 10, 0))

    def test_receipt_and_billing(self):
        self.assertEqual([ps.receipt_state(d) for d in (0, 1, 2)], ['Nháp', 'Đã nhập kho', 'Đã hủy'])
        self.assertEqual(ps.billing_state(0), 'Chưa có hóa đơn')
        self.assertEqual(ps.billing_state(40), 'Có hóa đơn một phần')
        self.assertEqual(ps.billing_state(100), 'Đã có hóa đơn')
        self.assertEqual(ps.billing_state(None, invoiced=True), 'Đã có hóa đơn')
        self.assertEqual(ps.billing_state('x'), 'Chưa có hóa đơn')
        # Everything went back: nothing to invoice, whatever per_billed says (Lotus counts it 100 % over what is kept).
        self.assertEqual(ps.billing_state(100, per_returned=100), 'Đã trả hết hàng')
        self.assertEqual(ps.billing_state(0, per_returned=40), 'Chưa có hóa đơn')

    def test_invoice(self):
        self.assertEqual(ps.invoice_state(1, 1000000, 1000000, '2026-12-01', '2026-11-10'), 'Chưa trả')
        self.assertEqual(ps.invoice_state(1, 1000000, 400000, '2026-12-01', '2026-11-10'), 'Trả một phần')
        self.assertEqual(ps.invoice_state(1, 1000000, 400000, '2026-11-01', '2026-11-10'), 'Quá hạn')
        self.assertEqual(ps.invoice_state(1, 1000000, 0.4, '2026-11-01', '2026-11-10'), 'Đã trả')
        self.assertEqual(ps.invoice_state(2, 1000000, 1000000), 'Đã hủy')
        self.assertEqual(ps.invoice_state(1, -200000, -200000), 'Chưa trả')  # a debit note owed back to us

    def test_voucher_and_quote(self):
        self.assertEqual(ps.voucher_state(0), 'Nháp')
        self.assertEqual(ps.voucher_state(0, round_started=True), 'Đang ký')
        self.assertEqual(ps.voucher_state(0, round_started=True, returned=True), 'Bị trả lại')
        self.assertEqual(ps.voucher_state(1, True), 'Đã chi')
        self.assertEqual(ps.voucher_state(2, True), 'Đã đảo')
        self.assertEqual([ps.quote_state(0), ps.quote_state(1), ps.quote_state(1, True), ps.quote_state(2)],
                         ['Nháp', 'Đã xác nhận', 'Đã chọn', 'Đã hủy'])


if __name__ == '__main__':
    unittest.main()
