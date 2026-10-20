import unittest

from lotus_farm import signing_rules as sr


def rows(*states, assignees=('an', 'binh', 'chi', 'dung')):
    return [dict(state=s, assignee=a) for s, a in zip(states, assignees)]


class SigningRules(unittest.TestCase):
    def test_chains_follow_the_paper_forms(self):
        self.assertEqual([s['title'] for s in sr.chain('purchase_proposal')['steps']],
                         ['Người đề xuất', 'Phụ trách bộ phận', 'Phòng Kế toán / Mua hàng', 'Giám đốc phê duyệt'])
        self.assertEqual([s['title'] for s in sr.chain('stock_document')['steps']],
                         ['Người lập phiếu', 'Người giao / nhận', 'Thủ kho / người kiểm tra'])
        self.assertEqual(len(sr.chain('timekeeping_period')['steps']), 3)
        self.assertTrue(sr.chain('purchase_order')['gate'])
        with self.assertRaises(KeyError):
            sr.chain('unknown')

    def test_assignment_needs_a_permitted_person_for_every_later_step(self):
        roles = {'binh': ['Lotus Field Supervisor'], 'chi': ['Accounts User'], 'dung': ['Lotus Purchase Approver'], 'x': []}
        ok = dict(DEPARTMENT='binh', PURCHASING='chi', APPROVE='dung')
        self.assertEqual(sr.validate_assignment('purchase_proposal', ok, roles.get, 'an'), [])
        issues = sr.validate_assignment('purchase_proposal', dict(DEPARTMENT='x', PURCHASING='chi'), roles.get, 'an')
        self.assertIn('Phụ trách bộ phận: người được chọn không có quyền ký bước này', issues)
        self.assertIn('Chọn người ký: Giám đốc phê duyệt', issues)
        self.assertEqual(sr.validate_assignment('stock_document', dict(HANDOVER='x', STOREKEEPER='dung'), lambda u: ['Stock Manager'], 'an'), [],
                         'the person handing goods over needs no special role')

    def test_turns_move_one_named_person_at_a_time(self):
        chain = rows(sr.SIGNED, sr.WAITING, sr.PENDING, sr.PENDING)
        self.assertEqual(sr.current(chain), 1)
        self.assertTrue(sr.may_act(chain, 1, 'binh'))
        self.assertFalse(sr.may_act(chain, 1, 'chi'), 'another eligible person cannot sign someone else’s turn')
        self.assertFalse(sr.may_act(chain, 2, 'chi'), 'not their turn yet')
        self.assertTrue(sr.may_act(chain, 1, 'zz', is_admin=True))
        states, done = sr.after_sign(chain, 1)
        self.assertEqual((states, done), ([sr.SIGNED, sr.SIGNED, sr.WAITING, sr.PENDING], False))
        states, done = sr.after_sign(rows(sr.SIGNED, sr.SIGNED, sr.SIGNED, sr.WAITING), 3)
        self.assertTrue(done)
        self.assertIsNone(sr.current(rows(sr.SIGNED, sr.SIGNED)))

    def test_fingerprint_covers_quantities_and_prices_not_notes(self):
        lines = [dict(item_code='PHAN', qty=5.0, uom='Kg', rate=12000.0, warehouse='Kho A', lotus_notes='gấp')]
        base = sr.fingerprint(dict(company='LT'), lines)
        self.assertEqual(base, sr.fingerprint(dict(company='LT'), [dict(lines[0], lotus_notes='khác')]), 'notes are not signed content')
        self.assertNotEqual(base, sr.fingerprint(dict(company='LT'), [dict(lines[0], qty=6.0)]))
        self.assertNotEqual(base, sr.fingerprint(dict(company='LT'), [dict(lines[0], rate=12500.0)]))
        self.assertEqual(base, sr.fingerprint(dict(company='LT'), [dict(lines[0], qty=5.0000000001)]), 'float noise is ignored')

    def test_verify_token_is_per_document_and_round(self):
        token = sr.verify_token('k', 'Stock Entry', 'MAT-STE-1', 1)
        self.assertEqual(len(token), 40)
        self.assertEqual(token, sr.verify_token('k', 'Stock Entry', 'MAT-STE-1', 1))
        self.assertNotEqual(token, sr.verify_token('k', 'Stock Entry', 'MAT-STE-1', 2))
        self.assertNotEqual(token, sr.verify_token('other', 'Stock Entry', 'MAT-STE-1', 1))

    def test_verdict_for_the_paper_copy(self):
        self.assertEqual(sr.verdict([sr.SIGNED, sr.SIGNED], True), 'Đã ký đủ')
        self.assertIn('1/3', sr.verdict([sr.SIGNED, sr.WAITING, sr.PENDING], True))
        self.assertIn('thay đổi', sr.verdict([sr.SIGNED, sr.SIGNED], False))
        self.assertIn('trả lại', sr.verdict([sr.SIGNED, sr.RETURNED], True))
        self.assertIn('hủy', sr.verdict([sr.SIGNED], True, cancelled=True))


if __name__ == '__main__':
    unittest.main()
