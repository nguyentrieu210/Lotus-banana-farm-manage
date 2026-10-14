import unittest
from lotus_farm.warehouse_rules import coverage


class TestCoverage(unittest.TestCase):
    def test_partial_supply_does_not_erase_purchase_shortage(self):
        row=coverage(100,0,60,incoming=25)
        self.assertEqual((row['remaining_qty'],row['shortage_qty'],row['to_buy_qty']),(100,40,15))
        self.assertEqual(row['status'],'Cần mua')

    def test_issued_goods_are_not_requested_again_when_consumption_is_later(self):
        row=coverage(100,40,60)
        self.assertEqual((row['remaining_qty'],row['shortage_qty']),(60,0))

    def test_own_draft_is_part_of_demand_and_must_not_be_deducted_twice(self):
        row=coverage(100,0,100,drafts=70,own_drafts=40)
        self.assertEqual((row['other_hold_qty'],row['available_qty'],row['shortage_qty']),(30,70,30))

    def test_purchase_request_is_not_firm_supply(self):
        row=coverage(100,0,60,requested=40)
        self.assertEqual((row['shortage_qty'],row['to_buy_qty'],row['to_request_qty']),(40,40,0))
        self.assertEqual(row['status'],'Đã đề nghị mua')

    def test_pending_order_can_cover_shortage_but_not_current_stock(self):
        row=coverage(100,0,60,incoming=40)
        self.assertEqual(row['available_qty'],60)
        self.assertEqual(row['status'],'Chờ nhập')

    def test_other_holds_and_negative_inventory_cannot_be_treated_as_zero(self):
        row=coverage(100,0,-5,reserved=10,drafts=5)
        self.assertEqual((row['available_qty'],row['shortage_qty']),(-20,120))

    def test_fulfilled_requirement_does_not_require_another_issue(self):
        self.assertEqual(coverage(100,100,0)['status'],'Đã cấp đủ')
        self.assertEqual(coverage(100,100,0,drafts=50)['to_buy_qty'],0)

    def test_returned_unused_stock_reopens_only_net_issued_quantity(self):
        row=coverage(100,20,80)
        self.assertEqual((row['remaining_qty'],row['shortage_qty']),(80,0))
