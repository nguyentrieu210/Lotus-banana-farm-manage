import sys
import types
import unittest

# lotus_farm.adms imports frappe at module level; the protocol helpers are pure. Without Frappe installed a
# stand-in is used for the import only, so other tests still see the real module (or its absence).
try:
    import frappe  # noqa: F401
    from lotus_farm import adms
except ImportError:
    sys.modules['frappe'] = types.ModuleType('frappe')
    sys.modules['frappe.utils'] = types.ModuleType('frappe.utils')
    sys.modules['frappe.utils'].now_datetime = lambda: None
    try:
        from lotus_farm import adms
    finally:
        del sys.modules['frappe'], sys.modules['frappe.utils']


class AdmsProtocol(unittest.TestCase):
    def test_attlog_lines_become_punches_with_in_out(self):
        body = '12\t2026-10-20 06:58:12\t0\t1\t0\t0\n12\t2026-10-20 14:03:40\t1\t1\n7\t2026-10-20 22:01\t4\t15\n\n'
        events, invalid = adms.parse_attlog(body)
        self.assertEqual(invalid, 0)
        self.assertEqual([(e['device_user_id'], e['punched_at'], e['log_type']) for e in events],
                         [('12', '2026-10-20 06:58:12', 'IN'), ('12', '2026-10-20 14:03:40', 'OUT'), ('7', '2026-10-20 22:01:00', 'IN')])

    def test_unknown_status_keeps_the_punch_without_direction_and_bad_lines_are_counted(self):
        events, invalid = adms.parse_attlog('5\t2026-10-20 07:00:00\t255\t1\ngarbage\n\t2026-10-20 07:00:00\t0\n8\t20-10-2026 07:00\t0')
        self.assertEqual([(e['device_user_id'], e['log_type']) for e in events], [('5', '')])
        self.assertEqual(invalid, 3)

    def test_userinfo_keeps_pin_and_name_never_templates(self):
        body = 'USER PIN=12\tName=Thị Phiêu\tPri=0\tPasswd=\tCard=0012345\tGrp=1\nFP PIN=12\tFID=6\tSize=1184\tValid=1\tTMP=AAAA\nOPLOG 4\t0\t2026-10-20 06:00:00\t0'
        self.assertEqual(adms.parse_userinfo(body), [dict(pin='12', name='Thị Phiêu', privilege='0', card='0012345')])

    def test_handshake_turns_on_realtime_upload_in_vietnam_time(self):
        text = adms.handshake('CQZ7224460123')
        self.assertTrue(text.startswith('GET OPTION FROM: CQZ7224460123\n'))
        for line in ('Realtime=1', 'TimeZone=7', 'ATTLOGStamp=None', 'TransFlag=TransData AttLog\tOpLog\tEnrollUser'):
            self.assertIn(line, text)


if __name__ == '__main__':
    unittest.main()
