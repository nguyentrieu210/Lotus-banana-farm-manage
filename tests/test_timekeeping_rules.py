import unittest
from lotus_farm.timekeeping_rules import crew_values,status_days


class TestTimekeepingRules(unittest.TestCase):
    def test_partial_crew_days_and_piecework_amount(self):
        row=crew_values(20,18,17.5,125.5,12000)
        self.assertEqual((row['absent'],row['workdays'],row['amount']),(2,17.5,1506000))

    def test_impossible_headcounts_or_days_are_rejected(self):
        for values in [(10,11,10),(10,8,9),(2.5,2,2),(3,2.5,2),(-1,0,0)]:
            with self.subTest(values=values),self.assertRaises(ValueError):crew_values(*values)

    def test_nan_infinity_and_negative_cost_are_rejected(self):
        for qty,rate in [(float('nan'),1),(1,float('inf')),(-1,1),(1,-1),(1e308,1e308)]:
            with self.assertRaises(ValueError):crew_values(1,1,1,qty,rate)

    def test_absence_leave_and_unknown_do_not_become_workdays(self):
        self.assertEqual(status_days('Present'),1)
        self.assertEqual(status_days('Half Day'),.5)
        for status in ('Absent','On Leave','',None):self.assertEqual(status_days(status),0)
