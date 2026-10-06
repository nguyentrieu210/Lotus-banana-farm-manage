"""Requires a disposable ERPNext v16 site. Never run against production data."""
import unittest
from uuid import uuid4

import frappe
from frappe.utils import add_days, today

from lotus_farm.api.v1.allocations import release, reserve
from lotus_farm.api.v1.operations import create
from lotus_farm.stock import create_stock_entry
from lotus_farm.supply import availability


class LotusIntegrationTest(unittest.TestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.tag = uuid4().hex[:8]
        self.company = frappe.get_doc({"doctype": "Company", "company_name": f"Lotus Test {self.tag}",
                                       "abbr": self.tag, "country": "Vietnam", "default_currency": "VND"}).insert()
        self.item = frappe.get_doc({"doctype": "Item", "item_code": f"BAN-{self.tag}",
                                    "item_name": "Banana", "item_group": "All Item Groups", "stock_uom": "Kg",
                                    "is_stock_item": 1, "has_batch_no": 1}).insert()
        self.customer = frappe.get_doc({"doctype": "Customer", "customer_name": f"Buyer {self.tag}",
                                        "customer_type": "Company", "customer_group": "All Customer Groups",
                                        "territory": "All Territories"}).insert()
        self.farm = frappe.get_doc({"doctype": "Farm", "farm_name": "Test Farm", "farm_code": f"F-{self.tag}",
                                    "company": self.company.name, "area_ha": 1}).insert()
        self.block = frappe.get_doc({"doctype": "Farm Block", "farm": self.farm.name, "block_name": "A1",
                                     "block_code": "A1", "area_ha": 1}).insert()
        self.cycle = frappe.get_doc({"doctype": "Crop Cycle", "farm": self.farm.name, "farm_block": self.block.name,
                                     "cycle_no": 1, "planting_date": today()}).insert()
        self.profile = frappe.get_doc({"doctype": "Harvest Profile", "profile_name": f"P-{self.tag}",
                                       "profile_version": 1, "farm": self.farm.name, "valid_from": today(),
                                       "avg_bunch_weight_kg": 10, "bunch_survival_rate_percent": 100,
                                       "quality_pass_rate_percent": 100, "packout_rate_percent": 100,
                                       "safety_buffer_percent": 0, "active": 1}).insert()
        self.profile.submit()
        self.payload = {"client_event_id": uuid4().hex, "farm": self.farm.name, "farm_block": self.block.name,
                        "crop_cycle": self.cycle.name, "operation_type": "Cut Bud", "operation_date": today(),
                        "bunch_qty": 1000, "rejected_qty": 0, "expected_harvest_date": today()}
        self.operation = create(self.payload)
        self.forecast = frappe.get_doc({"doctype": "Harvest Forecast", "farm": self.farm.name,
                                        "farm_block": self.block.name, "crop_cycle": self.cycle.name,
                                        "item_code": self.item.name, "harvest_profile": self.profile.name,
                                        "forecast_basis": "Cut Bud Operations", "period_start_date": today(),
                                        "period_end_date": add_days(today(), 7)}).insert()
        self.forecast.submit()
        self.so = frappe.get_doc({"doctype": "Sales Order", "company": self.company.name,
                                  "customer": self.customer.name, "transaction_date": today(),
                                  "delivery_date": today(), "currency": "VND", "selling_price_list": "Standard Selling",
                                  "items": [{"item_code": self.item.name, "qty": 10000, "rate": 100,
                                             "delivery_date": today()}]}).insert()
        self.so.submit()

    def tearDown(self):
        frappe.db.rollback()
        frappe.set_user("Administrator")

    def test_snapshot_and_retry_safety(self):
        self.assertEqual(create(self.payload)["name"], self.operation["name"])
        changed = dict(self.payload, bunch_qty=999)
        with self.assertRaises(frappe.ValidationError):
            create(changed)
        self.profile.avg_bunch_weight_kg = 20
        with self.assertRaises(frappe.ValidationError):
            self.profile.save()
        self.forecast.reload()
        self.assertEqual(self.forecast.safe_saleable_kg, 10000)
        self.assertIn(self.operation['name'], self.forecast.source_snapshot)

    def test_allocation_capacity_and_release(self):
        key = uuid4().hex
        args = (self.forecast.name, self.so.name, self.so.items[0].name, 8000, key)
        first = reserve(*args)
        self.assertEqual(reserve(*args)['name'], first['name'])
        with self.assertRaises(frappe.ValidationError):
            reserve(self.forecast.name, self.so.name, self.so.items[0].name, 3000, uuid4().hex)
        self.assertEqual(availability(self.forecast)['available_to_promise_kg'], 2000)
        release(first['name'], 'Test release')
        self.assertEqual(availability(self.forecast)['available_to_promise_kg'], 10000)

    def test_harvest_packout_receipt_and_reversal(self):
        actual = frappe.get_doc({"doctype": "Harvest Actual", "farm": self.farm.name,
                                 "farm_block": self.block.name, "crop_cycle": self.cycle.name,
                                 "forecast": self.forecast.name, "harvest_date": today(),
                                 "harvested_bunch_qty": 1000, "gross_weight_kg": 10000,
                                 "rejected_weight_kg": 0}).insert()
        actual.submit()
        lot = frappe.get_doc('Harvest Lot', frappe.db.get_value('Harvest Lot', {'harvest_actual': actual.name}, 'name'))
        self.assertEqual(lot.qc_status, 'Hold')
        lot.qc_status = 'Released'
        lot.save()
        lot.submit()
        warehouse = frappe.get_doc({"doctype": "Warehouse", "warehouse_name": f"Pack-{self.tag}",
                                    "company": self.company.name}).insert()
        run = frappe.get_doc({"doctype": "Packout Run", "farm": self.farm.name, "company": self.company.name,
                              "packing_date": today(), "target_warehouse": warehouse.name, "qc_status": "Released",
                              "sources": [{"harvest_lot": lot.name, "source_kg": 8000}],
                              "outputs": [{"output_type": "Saleable", "item_code": self.item.name,
                                           "net_kg": 7800, "valuation_rate": 100},
                                          {"output_type": "Waste", "net_kg": 100}], "recorded_loss_kg": 100}).insert()
        run.submit()
        entry_name = create_stock_entry(run.name)
        self.assertEqual(create_stock_entry(run.name), entry_name)
        self.assertEqual(availability(self.forecast)['available_to_promise_kg'], 10000)
        entry = frappe.get_doc('Stock Entry', entry_name)
        entry.submit()
        self.assertEqual(availability(self.forecast)['available_to_promise_kg'], 2000)
        self.assertTrue(frappe.db.exists('Stock Ledger Entry', {'voucher_no': entry_name, 'is_cancelled': 0}))
        self.assertTrue(frappe.db.exists('Forecast Materialization', {'stock_entry': entry_name, 'docstatus': 1}))
        entry.cancel()
        self.assertEqual(availability(self.forecast)['available_to_promise_kg'], 10000)
