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

    def test_alert_goes_to_a_phone_app_the_signer_uses(self):
        # Chain app with a phone there, or no phone at all: stays in the chain's app (the bell keeps it).
        self.assertEqual(sr.notify_app('buying', ['buying', 'work']), 'buying')
        self.assertEqual(sr.notify_app('buying', []), 'buying')
        # Phone only in another app: the push goes where it can reach them (most recently used first).
        self.assertEqual(sr.notify_app('buying', ['work', 'warehouse']), 'work')
        # Payment vouchers belong to the desktop Finance app: announced in Mua hàng, never 'finance'.
        self.assertEqual(sr.notify_app('finance', []), 'buying')
        self.assertEqual(sr.notify_app('finance', ['buying']), 'buying')
        self.assertEqual(sr.notify_app('finance', ['warehouse']), 'warehouse')
        self.assertEqual(sr.notify_app('hr', ['work']), 'work')
        self.assertEqual(sr.notify_app('finance', ['finance', 'desk']), 'buying')
        for chain in sr.CHAINS.values():
            self.assertIn(sr.notify_app(chain['app'], []), sr.PHONE_APPS)

    def test_initials_come_from_the_checking_step(self):
        # Proposal: accounting / purchasing (step 3); order: its preparer; voucher: the chief accountant.
        self.assertEqual(sr.chain('purchase_proposal')['steps'][sr.checker_step('purchase_proposal')]['key'], 'PURCHASING')
        self.assertEqual(sr.chain('purchase_order')['steps'][sr.checker_step('purchase_order')]['key'], 'PREPARE')
        self.assertEqual(sr.chain('payment_voucher')['steps'][sr.checker_step('payment_voucher')]['key'], 'CHIEF')
        for key in ('purchase_proposal_small', 'stock_document', 'timekeeping_period', 'issue_proposal', 'unknown'):
            self.assertIsNone(sr.checker_step(key))

    def test_receipt_against_an_order_is_signed_by_the_storekeeper_alone(self):
        chain = sr.chain('purchase_receipt')
        self.assertEqual([s['key'] for s in chain['steps']], ['STOREKEEPER'])
        self.assertTrue(chain['gate'], 'no separate signing step after the goods are in')
        self.assertEqual(sr.validate_assignment('purchase_receipt', {}, lambda user: [], 'kho@lotus'), [])
        rows = [dict(state=sr.WAITING, assignee='kho@lotus')]
        self.assertEqual(sr.after_sign(rows, 0), ([sr.SIGNED], True), 'the one signature completes the round')
        self.assertIsNone(sr.checker_step('purchase_receipt'))
        self.assertEqual(sr.notify_app(chain['app'], []), 'warehouse')

    def test_push_link_stays_inside_the_app_that_shows_it(self):
        self.assertEqual(sr.push_link('buying', '/buying?doc=PUR-ORD-1', 'Purchase Order', 'PUR-ORD-1'), '/buying?doc=PUR-ORD-1')
        self.assertEqual(sr.push_link('buying', '/lotus/tai-chinh?tab=cash&doc=ACC-PAY-1', 'Payment Entry', 'ACC-PAY-1'),
                         '/buying?sign_dt=Payment+Entry&sign_dn=ACC-PAY-1')
        self.assertEqual(sr.push_link('work', '/warehouse?doc=MAT-1&doctype=Stock+Entry', 'Stock Entry', 'MAT-1'),
                         '/work?sign_dt=Stock+Entry&sign_dn=MAT-1')
        self.assertEqual(sr.push_link('hr', '/lotus/in-luong?month=2026-11', 'Lotus Timekeeping Period', 'P-1'),
                         '/hr-mobile?sign_dt=Lotus+Timekeeping+Period&sign_dn=P-1')
        self.assertEqual(sr.sign_link('warehouse', 'Purchase Receipt', 'MAT-PRE/1&x'),
                         '/warehouse?sign_dt=Purchase+Receipt&sign_dn=MAT-PRE%2F1%26x')


if __name__ == '__main__':
    unittest.main()
