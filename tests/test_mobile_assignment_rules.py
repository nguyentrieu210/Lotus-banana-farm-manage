import unittest
from lotus_farm.mobile_assignment_rules import split_quantity
from lotus_farm.rules import RuleError


class MobileAssignmentRules(unittest.TestCase):
    def test_block_quantity_is_conserved_across_plots(self):
        self.assertEqual(split_quantity(800, [20,20,20,20], whole=True), [200,200,200,200])
        self.assertEqual(split_quantity(801, [20,20,20,20], whole=True), [201,200,200,200])
        self.assertEqual(split_quantity(101, [1,2], whole=True), [34,67])
        self.assertEqual(sum(split_quantity(1000,[1,3,7],whole=True)),1000)

    def test_area_quantities_are_not_duplicated_or_lost(self):
        parts=split_quantity("1.5",[1,2,3],whole=False)
        self.assertEqual(sum(parts),1.5)
        self.assertEqual(parts,[0.25,0.5,0.75])

    def test_invalid_targets_fail(self):
        for total,areas,whole in [(0,[1],True),(-3,[1],True),
                                  (10,[],True),(10,[0],True),
                                  (2.3,[1,2],True),("1.0001",[1],False)]:
            with self.subTest(total=total,areas=areas):
                with self.assertRaises(RuleError):
                    split_quantity(total,areas,whole)
