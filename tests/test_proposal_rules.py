import unittest

from lotus_farm import proposal_rules as pr


class ProposalRules(unittest.TestCase):
    def test_four_signatures_in_excel_order(self):
        self.assertEqual([s['title'] for s in pr.STEPS],
                         ['Người đề xuất', 'Phụ trách bộ phận', 'Phòng Kế toán / Mua hàng', 'Giám đốc phê duyệt'])
        self.assertEqual([pr.current_step(s) for s in (pr.DRAFT, *pr.WAITING, pr.APPROVED, pr.RETURNED)], [0, 1, 2, 3, None, 0])
        self.assertEqual([pr.state_after(i) for i in range(4)], [*pr.WAITING, pr.APPROVED])

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

    def test_small_priced_proposals_need_two_signatures(self):
        self.assertEqual(pr.chain_for_lines([dict(qty=10, rate=1_500_000)]), 'purchase_proposal_small')  # 15 triệu
        self.assertEqual(pr.chain_for_lines([dict(qty=10, rate=2_500_000)]), 'purchase_proposal')  # 25 triệu
        self.assertEqual(pr.chain_for_lines([dict(qty=1, rate=pr.SMALL_LIMIT)]), 'purchase_proposal')  # exactly the limit
        # A line without a price cannot prove the proposal is small.
        self.assertEqual(pr.chain_for_lines([dict(qty=1, rate=100), dict(qty=5, rate=0)]), 'purchase_proposal')
        self.assertEqual(pr.chain_for_lines([]), 'purchase_proposal')
        from lotus_farm.signing_rules import chain
        self.assertEqual([s['key'] for s in chain('purchase_proposal_small')['steps']], ['PROPOSE', 'DEPARTMENT'])


if __name__ == '__main__':
    unittest.main()
