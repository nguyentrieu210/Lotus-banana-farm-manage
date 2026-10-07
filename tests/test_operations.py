import unittest
from lotus_farm.operations_rules import material_needed, labor_needed, labor_summary, remaining_bunches, completion
from lotus_farm.rules import RuleError


class TestDailyRules(unittest.TestCase):
    def test_1250_bunches_need_5000_sheets(self):
        self.assertEqual(material_needed(1250,4,1,1,1),5000)
        self.assertEqual(material_needed(2,15,1,2,0.001),0.06)

    def test_invalid_basis_or_nonfinite_quantity(self):
        for args in [(1250,4,0,1,1),(1250,4,1,0,1),(1250,'nan',1,1,1)]:
            with self.assertRaises(RuleError):material_needed(*args)

    def test_fractional_workdays_and_whole_people(self):
        self.assertEqual(labor_needed(1250,40),{'required_workdays':31.25,'required_people':32})
        with self.assertRaises(RuleError):labor_needed(10,0)

    def test_labor_counts_and_area(self):
        result=labor_summary(40,32,35,31.25,5)
        self.assertEqual(result['absent'],8)
        self.assertEqual(result['staffing_gap'],-3)
        self.assertEqual(result['absence_percent'],20)
        self.assertEqual(result['workdays_per_ha'],6.25)
        self.assertIsNone(labor_summary(0,0,0,0,0)['workdays_per_ha'])
        with self.assertRaises(RuleError):labor_summary(10,11,10,1,1)
        with self.assertRaises(RuleError):labor_summary(10.5,10,10,1,1)

    def test_cancellation_period_net(self):
        self.assertEqual(remaining_bunches(1000,[20,30]),950)
        with self.assertRaises(RuleError):remaining_bunches(100,[101])

    def test_unfinished_work_requires_explanation(self):
        with self.assertRaises(RuleError):completion(1250,1110,' ')
        self.assertEqual(completion(1250,1110,'Thiếu người'),140)
        self.assertEqual(completion(1250,1300,None),0)
