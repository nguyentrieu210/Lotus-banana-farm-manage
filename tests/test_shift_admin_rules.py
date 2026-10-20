import unittest
from datetime import date

from lotus_farm import timekeeping_rules as tr


def a(name, shift, start, end=None):
    return dict(name=name, shift_type=shift, start_date=start, end_date=end)


class ShiftAdminRules(unittest.TestCase):
    def test_who_manages_shifts(self):
        self.assertTrue(tr.can_manage_shifts([], 'Administrator'))
        self.assertTrue(tr.can_manage_shifts(['HR Manager'], 'hr@lotus'))
        self.assertTrue(tr.can_manage_shifts(['System Manager'], 'it@lotus'))
        self.assertFalse(tr.can_manage_shifts(['HR User', 'Lotus Team Leader'], 'x@lotus'))

    def test_change_in_the_middle_splits_the_open_assignment(self):
        plan = tr.plan_roster([a('SA1', 'Ca 1', date(2026, 10, 1))], date(2026, 10, 12), date(2026, 10, 18), 'Ca 3')
        self.assertEqual(plan['end'], [('SA1', date(2026, 10, 11))])
        self.assertEqual(plan['cancel'], [])
        self.assertEqual(plan['create'], [('Ca 1', date(2026, 10, 19), None), ('Ca 3', date(2026, 10, 12), date(2026, 10, 18))])

    def test_assignment_starting_inside_the_range_is_replaced(self):
        plan = tr.plan_roster([a('SA2', 'Ca 2', date(2026, 10, 14), date(2026, 10, 25))], date(2026, 10, 12), date(2026, 10, 18), 'Ca 1')
        self.assertEqual(plan['cancel'], ['SA2'])
        self.assertEqual(plan['create'], [('Ca 2', date(2026, 10, 19), date(2026, 10, 25)), ('Ca 1', date(2026, 10, 12), date(2026, 10, 18))])

    def test_day_off_removes_only_the_range(self):
        plan = tr.plan_roster([a('SA1', 'Ca 1', date(2026, 10, 1), date(2026, 10, 31))], date(2026, 10, 20), date(2026, 10, 20), None)
        self.assertEqual(plan, dict(end=[('SA1', date(2026, 10, 19))], cancel=[], create=[('Ca 1', date(2026, 10, 21), date(2026, 10, 31))]))

    def test_same_shift_already_covering_is_a_no_op_and_unrelated_rows_are_kept(self):
        rows = [a('SA1', 'Ca 1', date(2026, 10, 1)), a('OLD', 'Ca 2', date(2026, 9, 1), date(2026, 9, 30))]
        self.assertEqual(tr.plan_roster(rows, date(2026, 10, 5), date(2026, 10, 9), 'Ca 1'), dict(end=[], cancel=[], create=[]))
        open_ended = tr.plan_roster(rows, date(2026, 10, 5), None, 'Ca 2')
        self.assertEqual(open_ended['end'], [('SA1', date(2026, 10, 4))])
        self.assertEqual(open_ended['create'], [('Ca 2', date(2026, 10, 5), None)])
        with self.assertRaises(ValueError):
            tr.plan_roster([], date(2026, 10, 5), date(2026, 10, 1), 'Ca 1')

    def test_three_shift_weekly_rotation(self):
        blocks = tr.rotation(date(2026, 10, 5), 4, ['Ca 1', 'Ca 2', 'Ca 3'])
        self.assertEqual([b[0] for b in blocks], ['Ca 1', 'Ca 2', 'Ca 3', 'Ca 1'])
        self.assertEqual(blocks[1][1:], (date(2026, 10, 12), date(2026, 10, 18)))

    def test_overtime_needs_thirty_minutes_and_rounds_down_to_quarters(self):
        self.assertEqual(tr.overtime_suggestion(29), 0)
        self.assertEqual(tr.overtime_suggestion(35), 0.5)
        self.assertEqual(tr.overtime_suggestion(104), 1.5)
        self.assertEqual(tr.overtime_suggestion(-10), 0)


if __name__ == '__main__':
    unittest.main()
