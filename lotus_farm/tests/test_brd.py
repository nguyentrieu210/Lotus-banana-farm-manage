"""Run inside a disposable ERPNext site; these are NOT part of pure unit checks."""

import unittest
import frappe
from frappe.utils import add_days, nowdate
from lotus_farm.allocations import reserve, release
from lotus_farm.api import create_operation, ingest_scale


class TestBRDOnSite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        from erpnext.setup.setup_wizard.operations.install_fixtures import install

        install("India")
        year = int(nowdate()[:4])
        if not frappe.db.exists("Fiscal Year", str(year)):
            frappe.get_doc(dict(
                doctype="Fiscal Year", year=str(year),
                year_start_date=f"{year}-01-01", year_end_date=f"{year}-12-31",
            )).insert()
        if not frappe.db.exists("Price List", "Standard Selling"):
            frappe.get_doc(dict(
                doctype="Price List", price_list_name="Standard Selling",
                enabled=1, selling=1, currency="INR",
            )).insert()
        if not frappe.db.exists("Customer Group", "Lotus Test Buyers"):
            frappe.get_doc(dict(
                doctype="Customer Group", customer_group_name="Lotus Test Buyers",
                parent_customer_group="All Customer Groups", is_group=0,
            )).insert()
        if not frappe.db.exists("Territory", "Lotus Test Market"):
            frappe.get_doc(dict(
                doctype="Territory", territory_name="Lotus Test Market",
                parent_territory="All Territories", is_group=0,
            )).insert()
        settings = frappe.get_single("Stock Settings")
        settings.enable_serial_and_batch_no_for_item = 1
        settings.save()
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")
        frappe.db.savepoint("lotus_brd_test")
        self.tag = frappe.generate_hash(length=8)
        self.company = self.make(
            "Company",
            company_name="Lotus Test " + self.tag,
            abbr=self.tag,
            country="India",
            default_currency="INR",
            create_chart_of_accounts_based_on="Standard Template",
            chart_of_accounts="Standard",
            enable_perpetual_inventory=1,
        ).name
        self.farm = self.make("Farm", farm_code="F-" + self.tag, farm_name="Test", company=self.company).name
        self.variety = self.make("Banana Variety", variety_code="V-" + self.tag, variety_name="Test").name
        self.block = self.make(
            "Farm Block", farm=self.farm, block_code="A12", block_name="A12", area_ha=1, variety=self.variety
        ).name
        self.parent = self.make(
            "Crop Cycle",
            farm=self.farm,
            farm_block=self.block,
            cycle_no=1,
            planting_date=add_days(nowdate(), -500),
            variety=self.variety,
        ).name
        self.cycle = self.make(
            "Crop Cycle",
            farm=self.farm,
            farm_block=self.block,
            cycle_no=2,
            parent_cycle=self.parent,
            variety=self.variety,
        ).name
        self.cohort = self.make(
            "Sucker Selection Batch",
            farm=self.farm,
            farm_block=self.block,
            crop_cycle=self.cycle,
            selection_date=add_days(nowdate(), -100),
            selected_sucker_qty=1000,
        ).name
        self.item = self.make(
            "Item",
            item_code="EXP-" + self.tag,
            item_name="Test",
            item_group="All Item Groups",
            stock_uom="Kg",
            is_stock_item=1,
            has_batch_no=1,
        ).name
        self.standard = self.make(
            "Quality Standard",
            standard_code="QS-" + self.tag,
            version=1,
            item=self.item,
            approval_state="Approved",
            valid_from=add_days(nowdate(), -500),
            max_defective_percent=15,
        ).name
        self.pack_profile = self.make(
            "Packout Profile",
            profile_name="PP-" + self.tag,
            version=1,
            farm=self.farm,
            variety=self.variety,
            item=self.item,
            quality_standard=self.standard,
            approval_state="Approved",
            valid_from=add_days(nowdate(), -500),
            yield_percent=84,
        ).name
        self.profile = self.make(
            "Harvest Profile",
            profile_name="HP-" + self.tag,
            version=1,
            farm=self.farm,
            variety=self.variety,
            approval_state="Approved",
            valid_from=add_days(nowdate(), -500),
            cut_bud_to_harvest_days=30,
            avg_bunch_weight_kg=25,
            bunch_survival_rate_percent=97,
            quality_pass_rate_percent=92,
            packout_rate_percent=84,
            safety_buffer_percent=5,
        ).name
        self.start = add_days(nowdate(), 30)
        self.customer = self.make(
            "Customer",
            customer_name="Buyer " + self.tag,
            customer_group="Lotus Test Buyers",
            territory="Lotus Test Market",
            customer_type="Company",
        ).name

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback(save_point="lotus_brd_test")

    @staticmethod
    def make(doctype, **values):
        return frappe.get_doc(dict(doctype=doctype, **values)).insert()

    def forecast(self):
        create_operation(
            "op-" + self.tag,
            self.farm,
            self.block,
            self.cycle,
            nowdate(),
            "Cut Bud",
            1000,
            sucker_selection_batch=self.cohort,
            harvest_profile=self.profile,
        )
        return self.make(
            "Harvest Forecast",
            farm=self.farm,
            farm_block=self.block,
            crop_cycle=self.cycle,
            sucker_selection_batch=self.cohort,
            harvest_profile=self.profile,
            packout_profile=self.pack_profile,
            item=self.item,
            forecast_basis="Cut Bud Operations",
            period_start_date=self.start,
            period_end_date=add_days(self.start, 6),
            supply_state="Released",
        )

    def order(self, qty):
        warehouse = self.make("Warehouse", warehouse_name="Sales " + self.tag, company=self.company).name
        doc = self.make(
            "Sales Order",
            company=self.company,
            customer=self.customer,
            transaction_date=nowdate(),
            delivery_date=self.start,
            currency="INR",
            conversion_rate=1,
            selling_price_list="Standard Selling",
            items=[
                dict(
                    item_code=self.item,
                    qty=qty,
                    uom="Kg",
                    conversion_factor=1,
                    rate=1,
                    delivery_date=self.start,
                    warehouse=warehouse,
                )
            ],
        )
        doc.submit()
        return doc

    def test_golden_release_atomic_limits_and_history(self):
        supply = self.forecast()
        self.assertAlmostEqual(supply.safe_saleable_kg, 17803.38, places=2)
        original_hash = supply.snapshot_hash
        order = self.order(20000)
        first = reserve(supply.name, order.name, order.items[0].name, 15000, "alloc-1-" + self.tag)
        retry = reserve(supply.name, order.name, order.items[0].name, 15000, "alloc-1-" + self.tag)
        self.assertEqual(first, retry)
        with self.assertRaises(frappe.ValidationError):
            reserve(supply.name, order.name, order.items[0].name, 5000, "alloc-2-" + self.tag)
        supply.reload()
        self.assertAlmostEqual(supply.available_to_promise_kg, 2803.38, places=2)
        self.assertEqual(supply.snapshot_hash, original_hash)
        supply.avg_bunch_weight_kg = 100
        with self.assertRaises(frappe.ValidationError):
            supply.save()
        release(supply.name, first["allocation"])
        supply.reload()
        self.assertAlmostEqual(supply.available_to_promise_kg, 17803.38, places=2)

    def test_idempotent_operations_and_scales(self):
        args = ("event-" + self.tag, self.farm, self.block, self.cycle, nowdate(), "Cut Bud", 1000)
        first = create_operation(*args, sucker_selection_batch=self.cohort, harvest_profile=self.profile)
        again = create_operation(*args, sucker_selection_batch=self.cohort, harvest_profile=self.profile)
        self.assertEqual(first["document"], again["document"])
        with self.assertRaises(frappe.ValidationError):
            create_operation(
                *args[:-1], 999, sucker_selection_batch=self.cohort, harvest_profile=self.profile
            )
        scale = ingest_scale(self.farm, "scale", self.tag, nowdate() + " 00:00:00", 100, 10)
        retry = ingest_scale(self.farm, "scale", self.tag, nowdate() + " 00:00:00", 100, 10)
        self.assertEqual(scale["document"], retry["document"])
        reading = frappe.get_doc("Scale Reading", scale["document"])
        reading.gross_kg = 101
        with self.assertRaises(frappe.ValidationError):
            reading.save()

    def test_harvest_lot_packout_and_overspend(self):
        supply = self.forecast()
        actual = self.make(
            "Harvest Actual",
            farm=self.farm,
            farm_block=self.block,
            crop_cycle=self.cycle,
            sucker_selection_batch=self.cohort,
            harvest_date=nowdate(),
            forecast=supply.name,
            harvested_bunch_qty=970,
            gross_weight_kg=24250,
            rejected_weight_kg=1940,
        )
        actual.submit()
        lot = self.make(
            "Harvest Lot",
            farm=self.farm,
            received_date=nowdate(),
            sources=[dict(harvest_actual=actual.name, contributed_kg=22310)],
        )
        lot.submit()
        over = frappe.get_doc(
            dict(
                doctype="Harvest Lot",
                farm=self.farm,
                received_date=nowdate(),
                sources=[dict(harvest_actual=actual.name, contributed_kg=1)],
            )
        )
        with self.assertRaises(frappe.ValidationError):
            over.insert()
        warehouse = self.make("Warehouse", warehouse_name="Finished " + self.tag, company=self.company).name
        run = self.make(
            "Packout Run",
            farm=self.farm,
            company=self.company,
            packing_date=nowdate(),
            quality_standard=self.standard,
            target_warehouse=warehouse,
            sources=[dict(harvest_lot=lot.name, input_kg=22310)],
            outputs=[dict(item=self.item, net_kg=18740.4)],
            reject_kg=3569.6,
            other_loss_kg=0,
            qc_state="Released",
        )
        run.submit()
        self.assertAlmostEqual(run.mass_variance_kg, 0, places=3)
        bad = frappe.copy_doc(run)
        bad.sources[0].input_kg = 1
        bad.outputs[0].net_kg = 1
        bad.reject_kg = 0
        bad.qc_state = "Hold"
        with self.assertRaises(frappe.ValidationError):
            bad.insert()

    def test_profile_version_is_immutable(self):
        profile = frappe.get_doc("Harvest Profile", self.profile)
        profile.avg_bunch_weight_kg = 999
        with self.assertRaises(frappe.ValidationError):
            profile.save()

    def test_farm_permission_denies_other_farm(self):
        from lotus_farm.controls import farm_allowed

        user = self.make(
            "User",
            email=self.tag + "@example.invalid",
            first_name="Operator",
            send_welcome_email=0,
            roles=[dict(role="Lotus Farm Manager")],
        ).name
        self.assertFalse(farm_allowed(self.farm, user))
        self.make("User Permission", user=user, allow="Farm", for_value=self.farm)
        self.assertTrue(farm_allowed(self.farm, user))
        supply = self.forecast()
        other = self.make("Farm", farm_code="F2-" + self.tag, farm_name="Other", company=self.company)
        self.assertFalse(farm_allowed(other.name, user))
        frappe.set_user(user)
        self.assertTrue(frappe.get_doc("Harvest Forecast", supply.name).has_permission("read"))
        with self.assertRaises(frappe.PermissionError):
            other.check_permission("read")

    def test_two_connections_cannot_overreserve(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier

        supply = self.forecast()
        order = self.order(24000)
        site, sites_path = frappe.local.site, frappe.local.sites_path
        forecast_name, order_name, line_name = supply.name, order.name, order.items[0].name
        # Both independent connections need committed fixtures on a disposable site.
        frappe.db.commit()
        frappe.db.savepoint("lotus_brd_test")
        barrier = Barrier(2)

        def worker(index):
            frappe.init(site=site, sites_path=sites_path)
            frappe.connect()
            frappe.set_user("Administrator")
            try:
                barrier.wait(timeout=20)
                result = reserve(forecast_name, order_name, line_name, 12000, "race-" + self.tag + str(index))
                frappe.db.commit()
                return ("accepted", result)
            except frappe.ValidationError:
                frappe.db.rollback()
                return ("rejected", None)
            finally:
                frappe.destroy()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(worker, [1, 2]))
        self.assertEqual(sorted(r[0] for r in results), ["accepted", "rejected"])
        supply.reload()
        self.assertAlmostEqual(supply.committed_qty_kg, 12000, places=3)
        self.assertAlmostEqual(supply.available_to_promise_kg, 5803.38, places=2)

    def test_received_raw_stock_to_repack_replaces_future_supply(self):
        from lotus_farm.stock_bridge import make_repack_entry

        supply = self.forecast()
        raw_item = self.make(
            "Item",
            item_code="RAW-" + self.tag,
            item_name="Raw Test",
            item_group="All Item Groups",
            stock_uom="Kg",
            is_stock_item=1,
            has_batch_no=1,
        ).name
        stock_account = frappe.db.get_value(
            "Account", {"company": self.company, "account_type": "Stock", "is_group": 0}, "name"
        )
        raw_account = self.make(
            "Account", account_name="Raw Inventory " + self.tag,
            company=self.company, account_type="Stock", is_group=0,
            parent_account=frappe.db.get_value("Account", stock_account, "parent_account"),
        ).name
        # Distinct inventory accounts make Repack produce meaningful GL entries;
        # equal-cost transfers within one account can legitimately net to zero GL.
        raw_warehouse = self.make(
            "Warehouse", warehouse_name="Raw " + self.tag,
            company=self.company, account=raw_account,
        ).name
        finished = self.make("Warehouse", warehouse_name="Finished " + self.tag, company=self.company).name
        batch = self.make("Batch", batch_id="RAW-" + self.tag, item=raw_item).name
        receipt = self.make(
            "Stock Entry",
            stock_entry_type="Material Receipt",
            purpose="Material Receipt",
            company=self.company,
            posting_date=nowdate(),
            items=[
                dict(
                    item_code=raw_item,
                    t_warehouse=raw_warehouse,
                    qty=22310,
                    uom="Kg",
                    stock_uom="Kg",
                    conversion_factor=1,
                    basic_rate=1,
                    batch_no=batch,
                    use_serial_batch_fields=1,
                )
            ],
        )
        receipt.submit()
        actual = self.make(
            "Harvest Actual",
            farm=self.farm,
            farm_block=self.block,
            crop_cycle=self.cycle,
            sucker_selection_batch=self.cohort,
            harvest_date=nowdate(),
            forecast=supply.name,
            harvested_bunch_qty=970,
            gross_weight_kg=24250,
            rejected_weight_kg=1940,
        )
        actual.submit()
        lot = self.make(
            "Harvest Lot",
            farm=self.farm,
            received_date=nowdate(),
            raw_item=raw_item,
            raw_warehouse=raw_warehouse,
            raw_batch=batch,
            sources=[dict(harvest_actual=actual.name, contributed_kg=22310)],
        )
        lot.submit()
        run = self.make(
            "Packout Run",
            farm=self.farm,
            company=self.company,
            packing_date=nowdate(),
            quality_standard=self.standard,
            target_warehouse=finished,
            sources=[dict(harvest_lot=lot.name, input_kg=22310)],
            outputs=[dict(item=self.item, net_kg=18740.4)],
            reject_kg=3569.6,
            other_loss_kg=0,
            qc_state="Released",
        )
        run.submit()
        draft = make_repack_entry(run.name)
        self.assertEqual(draft["docstatus"], 0)
        self.assertEqual(make_repack_entry(run.name), draft)
        entry = frappe.get_doc("Stock Entry", draft["stock_entry"])
        entry.submit()
        supply.reload()
        self.assertAlmostEqual(supply.materialized_qty_kg, 18740.4, places=2)
        self.assertEqual(supply.available_to_promise_kg, 0)
        sle = frappe.get_all(
            "Stock Ledger Entry",
            filters={
                "voucher_type": "Stock Entry",
                "voucher_no": entry.name,
                "item_code": self.item,
                "warehouse": finished,
            },
            fields=["actual_qty"],
        )
        self.assertAlmostEqual(sum(r.actual_qty for r in sle), 18740.4, places=2)
        gl = frappe.get_all(
            "GL Entry",
            filters={"voucher_type": "Stock Entry", "voucher_no": entry.name},
            fields=["debit", "credit"],
        )
        self.assertTrue(gl, "Perpetual inventory must create GL entries through ERPNext.")
        self.assertAlmostEqual(sum(float(r.debit) - float(r.credit) for r in gl), 0, places=2)
