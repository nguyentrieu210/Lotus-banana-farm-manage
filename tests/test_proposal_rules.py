import unittest

from lotus_farm import proposal_rules as pr


class ProposalRules(unittest.TestCase):
    def test_four_signatures_in_excel_order(self):
        self.assertEqual([s['title'] for s in pr.STEPS],
                         ['Người đề xuất', 'Phụ trách bộ phận', 'Phòng Kế toán / Mua hàng', 'Giám đốc phê duyệt'])
        self.assertEqual([pr.current_step(s) for s in (pr.DRAFT, *pr.WAITING, pr.APPROVED, pr.RETURNED)], [0, 1, 2, 3, None, 0])
        self.assertEqual([pr.state_after(i) for i in range(4)], [*pr.WAITING, pr.APPROVED])

    def test_who_may_sign(self):
        self.assertTrue(pr.may_sign(0, [], is_owner=True))
        self.assertFalse(pr.may_sign(0, ['Lotus Purchase Approver'], is_owner=False), 'only the proposer sends')
        self.assertTrue(pr.may_sign(1, ['Lotus Field Supervisor'], is_owner=False))
        self.assertFalse(pr.may_sign(2, ['Lotus Field Supervisor'], is_owner=False))
        self.assertTrue(pr.may_sign(3, ['Lotus Purchase Approver'], is_owner=True), 'role-authorized self approval')
        self.assertFalse(pr.may_sign(None, ['Lotus Purchase Approver'], is_owner=True), 'nothing left to sign')
        self.assertTrue(pr.may_sign(2, [], is_owner=False, is_admin=True))

    def test_editing_rules(self):
        self.assertEqual(pr.editable(pr.DRAFT), 'all')
        self.assertEqual(pr.editable(pr.RETURNED), 'all')
        self.assertEqual(pr.editable(pr.WAITING[1], step_roles_match=True), 'prices')
        self.assertIsNone(pr.editable(pr.WAITING[1]))
        self.assertIsNone(pr.editable(pr.WAITING[2], step_roles_match=True))
        self.assertIsNone(pr.editable(pr.APPROVED))

    def test_line_issues(self):
        good = dict(item_code='UREA', qty=32, schedule_date='2026-10-22', rate=0)
        self.assertEqual(pr.line_issues([good]), [])
        issues = pr.line_issues([dict(qty=0), dict(item_code='X', qty='abc', schedule_date='2026-10-22', rate=float('nan'))])
        self.assertIn('Dòng 1: chọn vật tư', issues)
        self.assertIn('Dòng 1: chọn thời gian cần hàng', issues)
        self.assertIn('Dòng 2: số lượng đề xuất phải lớn hơn 0', issues)
        self.assertIn('Dòng 2: đơn giá không hợp lệ', issues)


if __name__ == '__main__':
    unittest.main()
