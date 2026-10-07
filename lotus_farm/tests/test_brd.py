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
        self.plot = self.make("Farm Plot", farm=self.farm, farm_block=self.block,
                               plot_code="A12.1", plot_name="A12.1", area_ha=1).name
        self.parent = self.make(
            "Crop Cycle",
            farm=self.farm,
            farm_block=self.block,
            farm_plot=self.plot,
            cycle_no=1,
            planting_date=add_days(nowdate(), -500),
            variety=self.variety,
        ).name
        self.cycle = self.make(
            "Crop Cycle",
            farm=self.farm,
            farm_block=self.block,
            farm_plot=self.plot,
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
            sucker_to_harvest_days=130,
            shooting_to_harvest_days=90,
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
        revised = frappe.copy_doc(supply)
        revised.allocations = []
        revised.supersedes = supply.name
        revised.revision_reason = "Reviewed planning revision"
        revised.period_start_date = str(revised.period_start_date)
        revised.period_end_date = str(revised.period_end_date)
        revised.insert()
        supply.reload()
        self.assertEqual(supply.supply_state, "Superseded")
        self.assertEqual(supply.available_to_promise_kg, 0)
        self.assertEqual(supply.snapshot_hash, original_hash)
        self.assertEqual(revised.revision_no, 2)

    def test_forecast_evidence_ladder_sucker_to_shooting_to_cut_bud(self):
        import json

        sucker = self.make(
            "Harvest Forecast",
            farm=self.farm,
            farm_block=self.block,
            crop_cycle=self.cycle,
            sucker_selection_batch=self.cohort,
            harvest_profile=self.profile,
            packout_profile=self.pack_profile,
            item=self.item,
            forecast_basis="Sucker Selection",
            period_start_date=self.start,
            period_end_date=add_days(self.start, 6),
            supply_state="Released",
        )
        self.assertEqual(sucker.source_bunch_qty, 1000)
        self.assertEqual(json.loads(sucker.source_snapshot)["basis"], "Sucker Selection")

        create_operation(
            "shoot-" + self.tag,
            self.farm,
            self.block,
            self.cycle,
            add_days(nowdate(), -60),
            "Shooting",
            950,
            sucker_selection_batch=self.cohort,
            harvest_profile=self.profile,
        )
        shooting = frappe.copy_doc(sucker)
        shooting.supersedes = sucker.name
        shooting.revision_reason = "Replace early sucker estimate with observed shooting"
        shooting.forecast_basis = "Shooting Operations"
        shooting.insert()
        sucker.reload()
        self.assertEqual(sucker.supply_state, "Superseded")
        self.assertEqual(shooting.source_bunch_qty, 950)
        shooting_source = json.loads(shooting.source_snapshot)
        self.assertEqual(shooting_source["basis"], "Shooting Operations")
        self.assertEqual(shooting_source["rows"][0]["expected_harvest_date"], str(self.start))

        create_operation(
            "cut-" + self.tag,
            self.farm,
            self.block,
            self.cycle,
            nowdate(),
            "Cut Bud",
            900,
            sucker_selection_batch=self.cohort,
            harvest_profile=self.profile,
        )
        cut = frappe.copy_doc(shooting)
        cut.supersedes = shooting.name
        cut.revision_reason = "Replace shooting estimate with cut-bud evidence"
        cut.forecast_basis = "Cut Bud Operations"
        cut.insert()
        shooting.reload()
        self.assertEqual(shooting.supply_state, "Superseded")
        self.assertEqual(cut.source_bunch_qty, 900)
        self.assertEqual(json.loads(cut.source_snapshot)["basis"], "Cut Bud Operations")
        self.assertEqual(cut.formula_version, "lotus-forecast/5")

    def test_multi_item_forecast_reserves_and_materializes_each_finished_item(self):
        from lotus_farm.api import availability
        from lotus_farm.stock_bridge import make_repack_entry, set_output_valuation

        item_b = self.make(
            "Item",
            item_code="B-" + self.tag,
            item_name="Grade B",
            item_group="All Item Groups",
            stock_uom="Kg",
            is_stock_item=1,
            has_batch_no=1,
        ).name
        standard_b = self.make(
            "Quality Standard",
            standard_code="QS-B-" + self.tag,
            version=1,
            item=item_b,
            approval_state="Approved",
            valid_from=add_days(nowdate(), -500),
            max_defective_percent=20,
        ).name
        profile_b = self.make(
            "Packout Profile",
            profile_name="PP-B-" + self.tag,
            version=1,
            farm=self.farm,
            variety=self.variety,
            item=item_b,
            quality_standard=standard_b,
            approval_state="Approved",
            valid_from=add_days(nowdate(), -500),
            yield_percent=15,
        ).name

        create_operation(
            "multi-cut-" + self.tag,
            self.farm,
            self.block,
            self.cycle,
            nowdate(),
            "Cut Bud",
            1000,
            sucker_selection_batch=self.cohort,
            harvest_profile=self.profile,
        )
        supply = self.make(
            "Harvest Forecast",
            farm=self.farm,
            farm_block=self.block,
            crop_cycle=self.cycle,
            sucker_selection_batch=self.cohort,
            harvest_profile=self.profile,
            forecast_basis="Cut Bud Operations",
            period_start_date=self.start,
            period_end_date=add_days(self.start, 6),
            output_plan=[
                dict(item=self.item, packout_profile=self.pack_profile),
                dict(item=item_b, packout_profile=profile_b),
            ],
            supply_state="Released",
        )
        outputs = {row.item: row for row in supply.output_plan}
        self.assertAlmostEqual(outputs[self.item].safe_commit_kg, 17803.38, places=2)
        self.assertAlmostEqual(outputs[item_b].safe_commit_kg, 3179.175, places=2)
        self.assertAlmostEqual(supply.safe_saleable_kg, 20982.555, places=2)

        rows = [row for row in availability(self.start, add_days(self.start, 6), farm=self.farm) if row["name"] == supply.name]
        self.assertEqual({row["item"] for row in rows}, {self.item, item_b})
        filtered = availability(self.start, add_days(self.start, 6), farm=self.farm, item=item_b)
        self.assertEqual([row["item"] for row in filtered if row["name"] == supply.name], [item_b])

        from lotus_farm.lotus_farm.report.harvest_availability.harvest_availability import execute as availability_report

        _, report_rows, _, _, _ = availability_report(
            {"farm": self.farm, "item": item_b, "from_date": self.start, "to_date": add_days(self.start, 6)}
        )
        self.assertEqual([row.item for row in report_rows if row.name == supply.name], [item_b])

        finished = self.make("Warehouse", warehouse_name="Multi Finished " + self.tag, company=self.company).name
        order = self.make(
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
                    qty=16000,
                    uom="Kg",
                    conversion_factor=1,
                    rate=1,
                    delivery_date=self.start,
                    warehouse=finished,
                ),
                dict(
                    item_code=item_b,
                    qty=4000,
                    uom="Kg",
                    conversion_factor=1,
                    rate=1,
                    delivery_date=self.start,
                    warehouse=finished,
                ),
            ],
        )
        order.submit()
        reserve(supply.name, order.name, order.items[0].name, 15000, "multi-a-" + self.tag)
        reserve(supply.name, order.name, order.items[1].name, 3000, "multi-b-" + self.tag)
        with self.assertRaises(frappe.ValidationError):
            reserve(supply.name, order.name, order.items[1].name, 500, "multi-b-over-" + self.tag)
        supply.reload()
        outputs = {row.item: row for row in supply.output_plan}
        self.assertAlmostEqual(outputs[self.item].available_to_promise_kg, 2803.38, places=2)
        self.assertAlmostEqual(outputs[item_b].available_to_promise_kg, 179.175, places=2)

        raw_item = self.make(
            "Item",
            item_code="RAW-M-" + self.tag,
            item_name="Raw Multi",
            item_group="All Item Groups",
            stock_uom="Kg",
            is_stock_item=1,
            has_batch_no=1,
        ).name
        raw_warehouse = self.make("Warehouse", warehouse_name="Multi Raw " + self.tag, company=self.company).name
        raw_batch = self.make("Batch", batch_id="RAW-M-" + self.tag, item=raw_item).name
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
                    batch_no=raw_batch,
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
            raw_batch=raw_batch,
            sources=[dict(harvest_actual=actual.name, contributed_kg=22310)],
        )
        lot.submit()
        self.make("Incoming Quality Inspection", farm=self.farm, posting_date=nowdate(),
                  harvest_lot=lot.name, accepted_kg=lot.released_raw_kg).submit()
        run = self.make(
            "Packout Run",
            farm=self.farm,
            company=self.company,
            packing_date=nowdate(),
            quality_standard=self.standard,
            target_warehouse=finished,
            sources=[dict(harvest_lot=lot.name, input_kg=22310)],
            outputs=[
                dict(item=self.item, net_kg=18000),
                dict(item=item_b, net_kg=3000, quality_standard=standard_b),
            ],
            reject_kg=1310,
            other_loss_kg=0,
            qc_state="Released",
        )
        loss_reason = self.make("Defect Reason", defect_code="LOSS-"+self.tag, defect_name="Process reject", category="Other").name
        run.loss_details = []
        if run.reject_kg:
            run.append("loss_details",dict(loss_type="Reject",weight_kg=run.reject_kg,reason=loss_reason))
        if run.other_loss_kg:
            run.append("loss_details",dict(loss_type="Process Loss",weight_kg=run.other_loss_kg,reason=loss_reason))
        run.save()
        run.submit()
        with self.assertRaises(frappe.ValidationError):
            make_repack_entry(run.name)

        set_output_valuation(
            run.name,
            {
                self.item: 1,
                item_b: 4310 / 3000,
            },
        )
        run.reload()
        valued = {row.item: row for row in run.outputs}
        self.assertEqual(valued[self.item].valuation_set_by, "Administrator")
        self.assertAlmostEqual(valued[self.item].valuation_rate, 1, places=6)
        self.assertAlmostEqual(valued[item_b].valuation_rate, 4310 / 3000, places=6)

        run.outputs[0].valuation_rate = 99
        with self.assertRaises(frappe.ValidationError):
            run.save()
        run.reload()

        draft = make_repack_entry(run.name)
        entry = frappe.get_doc("Stock Entry", draft["stock_entry"])
        finished_rows = {row.item_code: row for row in entry.items if row.t_warehouse}
        self.assertTrue(all(row.set_basic_rate_manually for row in finished_rows.values()))
        self.assertAlmostEqual(finished_rows[self.item].basic_rate, 1, places=6)
        self.assertAlmostEqual(finished_rows[item_b].basic_rate, 4310 / 3000, places=6)

        finished_rows[item_b].basic_rate = 99
        with self.assertRaises(frappe.ValidationError):
            entry.save()
        entry.reload()

        entry.submit()

        supply.reload()
        outputs = {row.item: row for row in supply.output_plan}
        self.assertAlmostEqual(outputs[self.item].materialized_qty_kg, 18000, places=2)
        self.assertAlmostEqual(outputs[item_b].materialized_qty_kg, 3000, places=2)
        self.assertAlmostEqual(supply.materialized_qty_kg, 21000, places=2)
        self.assertLess(outputs[self.item].available_to_promise_kg, 0)
        self.assertLess(outputs[item_b].available_to_promise_kg, 0)

    def test_idempotent_operations_and_scales(self):
        args = ("event-" + self.tag, self.farm, self.block, self.cycle, nowdate(), "Cut Bud", 1000)
        first = create_operation(*args, sucker_selection_batch=self.cohort, harvest_profile=self.profile)
        again = create_operation(*args, sucker_selection_batch=self.cohort, harvest_profile=self.profile)
        self.assertEqual(first["document"], again["document"])
        with self.assertRaises(frappe.ValidationError):
            create_operation(
                *args[:-1], 999, sucker_selection_batch=self.cohort, harvest_profile=self.profile
            )
        self.make('Scale Device',farm=self.farm,device_id='scale',integration_user='Administrator',
                  calibrated_on=add_days(nowdate(),-10),calibration_due=add_days(nowdate(),10),unit='Kg')
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
        self.make("Incoming Quality Inspection", farm=self.farm, posting_date=nowdate(),
                  harvest_lot=lot.name, accepted_kg=lot.released_raw_kg).submit()
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
        loss_reason = self.make("Defect Reason", defect_code="LOSS-"+self.tag, defect_name="Process reject", category="Other").name
        run.loss_details = []
        if run.reject_kg:
            run.append("loss_details",dict(loss_type="Reject",weight_kg=run.reject_kg,reason=loss_reason))
        if run.other_loss_kg:
            run.append("loss_details",dict(loss_type="Process Loss",weight_kg=run.other_loss_kg,reason=loss_reason))
        run.save()
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
                # A real request retries a deadlocked transaction with the same event ID.
                # Roll back the entire isolated worker transaction before retrying.
                for attempt in range(3):
                    try:
                        result = reserve(forecast_name, order_name, line_name, 12000, "race-" + self.tag + str(index))
                        frappe.db.commit()
                        return ("accepted", result)
                    except frappe.QueryDeadlockError:
                        frappe.db.rollback()
                        if attempt == 2:
                            raise
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
        from lotus_farm.stock_bridge import link_stock_reservation, make_repack_entry

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
        order = self.make(
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
                    qty=2000,
                    uom="Kg",
                    conversion_factor=1,
                    rate=1,
                    delivery_date=self.start,
                    warehouse=finished,
                )
            ],
        )
        order.submit()
        allocation = reserve(
            supply.name,
            order.name,
            order.items[0].name,
            1000,
            "physical-" + self.tag,
        )
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
        self.make("Incoming Quality Inspection", farm=self.farm, posting_date=nowdate(),
                  harvest_lot=lot.name, accepted_kg=lot.released_raw_kg).submit()
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
        loss_reason = self.make("Defect Reason", defect_code="LOSS-"+self.tag, defect_name="Process reject", category="Other").name
        run.loss_details = []
        if run.reject_kg:
            run.append("loss_details",dict(loss_type="Reject",weight_kg=run.reject_kg,reason=loss_reason))
        if run.other_loss_kg:
            run.append("loss_details",dict(loss_type="Process Loss",weight_kg=run.other_loss_kg,reason=loss_reason))
        run.save()
        run.submit()
        draft = make_repack_entry(run.name)
        self.assertEqual(draft["docstatus"], 0)
        self.assertEqual(make_repack_entry(run.name), draft)
        entry = frappe.get_doc("Stock Entry", draft["stock_entry"])
        entry.submit()
        supply.reload()
        self.assertAlmostEqual(supply.materialized_qty_kg, 18740.4, places=2)
        # Until the physical SRE is linked, the old future commitment must remain visible as shortage.
        self.assertEqual(supply.available_to_promise_kg, -1000)
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

        from lotus_farm.learning import propose_complete_profile,create_calibrated_profile,create_calibrated_packout
        from lotus_farm.reporting import trace_item,forecast_vintages
        frappe.db.set_single_value('Lotus Farm Settings','minimum_calibration_samples',1)
        measured=propose_complete_profile(self.farm,self.cycle,nowdate(),nowdate())
        self.assertAlmostEqual(measured['avg_bunch_weight_kg'],25)
        self.assertAlmostEqual(measured['quality_pass_rate_percent'],92)
        self.assertAlmostEqual(measured['packout_rate_percent'],84)
        proposal=create_calibrated_profile(self.profile,self.cycle,nowdate(),nowdate(),self.start,add_days(self.start,30))
        self.assertEqual(proposal['approval_state'],'Draft')
        packed_proposal=create_calibrated_packout(self.pack_profile,self.cycle,nowdate(),nowdate(),self.start,add_days(self.start,30))
        self.assertAlmostEqual(packed_proposal['yield_percent'],84)
        calibrated=frappe.get_doc('Harvest Profile',proposal['profile'])
        calibrated.calibration_json='{}'
        with self.assertRaises(frappe.ValidationError):
            calibrated.save()
        forged=frappe.copy_doc(frappe.get_doc('Packout Profile',packed_proposal['profile']))
        forged.version+=1
        with self.assertRaises(frappe.ValidationError):
            forged.insert()
        self.assertEqual(trace_item(self.item)[0]['sources'][0]['farm_plot'],self.plot)
        self.assertEqual(forecast_vintages(nowdate(),add_days(nowdate(),60),self.farm)['rows'],[])

        reservation = self.make(
            "Stock Reservation Entry",
            voucher_type="Sales Order",
            voucher_no=order.name,
            voucher_detail_no=order.items[0].name,
            voucher_qty=2000,
            available_qty=18740.4,
            reserved_qty=1000,
            item_code=self.item,
            warehouse=finished,
            stock_uom="Kg",
            company=self.company,
            has_batch_no=1,
            reservation_based_on="Qty",
        )
        reservation.submit()
        partial=link_stock_reservation(supply.name, allocation["allocation"], reservation.name,qty_kg=600)
        self.assertEqual(partial['remaining_future_kg'],400)
        self.assertEqual(link_stock_reservation(supply.name,allocation['allocation'],reservation.name,qty_kg=600)['allocation'],partial['allocation'])
        with self.assertRaises(frappe.ValidationError):
            link_stock_reservation(supply.name,allocation['allocation'],reservation.name,qty_kg=601)
        supply.reload()
        linked = next(row for row in supply.allocations if row.name == partial['allocation'])
        self.assertEqual(linked.allocation_state, "Materialized")
        self.assertEqual(supply.available_to_promise_kg, -400)

        with self.assertRaises(frappe.ValidationError):
            reservation.cancel()
        reservation.reload()
        self.assertEqual(reservation.docstatus, 1)

        # Stock reversal is not reviewable while physical commitments still point at the output.
        blocked = self.make(
            "Supply Reconciliation",
            farm=self.farm,
            reconciliation_type="Stock Entry Reversal",
            stock_entry=entry.name,
            reason="Must cancel the physical reservation first",
        )
        with self.assertRaises(frappe.ValidationError):
            blocked.submit()

        from lotus_farm.reconciliation import execute

        reservation_request = self.make(
            "Supply Reconciliation",
            farm=self.farm,
            reconciliation_type="Stock Reservation Cancellation",
            stock_reservation=reservation.name,
            reservation_disposition="Restore Future Reservation",
            reason="Correct stock documents without dropping the customer commitment",
        )
        reservation_request.submit()
        execute(reservation_request.name)
        reservation.reload()
        supply.reload()
        linked = next(row for row in supply.allocations if row.name == allocation["allocation"])
        self.assertEqual(reservation.docstatus, 2)
        self.assertEqual(linked.allocation_state, "Reserved")

        # Lotus-linked stock cannot be cancelled directly: the forecast impact must be reviewed first.
        with self.assertRaises(frappe.ValidationError):
            entry.cancel()
        entry.reload()
        self.assertEqual(entry.docstatus, 1)

        request = self.make(
            "Supply Reconciliation",
            farm=self.farm,
            reconciliation_type="Stock Entry Reversal",
            stock_entry=entry.name,
            reason="Test reviewed reversal",
        )
        request.submit()
        self.assertEqual(request.state, "Approved")
        result = execute(request.name)
        self.assertEqual(result["state"], "Applied")
        entry.reload()
        supply.reload()
        request.reload()
        self.assertEqual(entry.docstatus, 2)
        self.assertEqual(request.state, "Applied")
        self.assertAlmostEqual(supply.materialized_qty_kg, 0, places=2)
        self.assertAlmostEqual(supply.committed_qty_kg, 1000, places=2)
        self.assertAlmostEqual(supply.available_to_promise_kg, 16803.38, places=2)

        # A cancelled bridge entry remains audit history but must not prevent a corrected draft.
        replacement_entry = make_repack_entry(run.name)
        self.assertNotEqual(replacement_entry["stock_entry"], entry.name)
        self.assertEqual(replacement_entry["docstatus"], 0)

    def daily_scope(self):
        return dict(farm=self.farm,farm_block=self.block,farm_plot=self.plot,
                    crop_cycle=self.cycle,sucker_selection_batch=self.cohort,posting_date=nowdate())

    def daily_plan(self, material=True):
        for uom in ('Bunch','Sheet'):
            if not frappe.db.exists('UOM',uom):
                self.make('UOM',uom_name=uom)
        category=self.make('Work Category',category_code='CSB-'+self.tag,category_name='Bunch care').name
        work=self.make('Work Type',work_code='BAG-'+self.tag,work_name='Bag bunches',category=category,
                       uom='Bunch',productivity_per_workday=40).name
        norm=None; material_item=None
        if material:
            basis=self.make('Norm Basis',basis_code='BUNCH-'+self.tag,basis_name='Per bunch',uom='Bunch').name
            material_item=self.make('Item',item_code='SHEET-'+self.tag,item_group='All Item Groups',
                                    stock_uom='Sheet',is_stock_item=1).name
            norm=self.make('Material Norm Profile',farm=self.farm,profile_name='NORM-'+self.tag,
                           version=1,work_type=work,valid_from=add_days(nowdate(),-1),valid_to=add_days(nowdate(),30),
                           approval_state='Approved',lines=[dict(item=material_item,uom='Sheet',norm_qty=4,
                           norm_basis=basis,basis_qty=1,frequency=1,conversion_factor=1)])
        plan=self.make('Daily Work Plan',farm=self.farm,posting_date=nowdate(),
                       lines=[dict(**{k:v for k,v in self.daily_scope().items() if k!='posting_date'},
                                   work_type=work,planned_qty=1250,norm_profile=norm.name if norm else None)])
        plan.submit()
        return plan,norm,material_item

    def test_promax_norm_plan_materials_and_daily_close(self):
        plan,norm,item=self.daily_plan()
        self.assertAlmostEqual(plan.lines[0].required_workdays,31.25)
        with self.assertRaises(frappe.ValidationError):
            norm.lines[0].norm_qty=9
            norm.save()
        req=self.make('Material Requirement',**self.daily_scope(),work_plan=plan.name,work_plan_line=plan.lines[0].name)
        req.submit()
        self.assertEqual(req.lines[0].required_qty,5000)
        from lotus_farm.daily_api import material_availability, create_material_request
        shortage_warehouse=self.make('Warehouse',warehouse_name='Requirement '+self.tag,company=self.company).name
        check=material_availability(req.name,shortage_warehouse)
        self.assertEqual(check['rows'][0]['shortage_qty'],5000)
        purchase=create_material_request(req.name,shortage_warehouse,nowdate())
        retry=create_material_request(req.name,shortage_warehouse,nowdate())
        self.assertEqual(purchase['material_request'],retry['material_request'])
        self.assertEqual(purchase['docstatus'],0)
        req.reload();req.save() if req.docstatus==0 else None
        team=self.make('Work Team',farm=self.farm,team_code='T-'+self.tag,team_name='Team').name
        allocation=self.make('Labor Allocation',**self.daily_scope(),work_plan=plan.name,
                             work_plan_line=plan.lines[0].name,work_team=team,allocated_workdays=32,allocation_note='32 people for one day')
        allocation.submit()
        result=self.make('Daily Work Result',**self.daily_scope(),work_plan=plan.name,
                         work_plan_line=plan.lines[0].name,completed_qty=1110,actual_workdays=30)
        with self.assertRaises(frappe.ValidationError):result.submit()
        result.reload();result.unfinished_reason='Shortage of people';result.save();result.submit()
        close=self.make('Daily Production Close',farm=self.farm,posting_date=nowdate())
        with self.assertRaises(frappe.ValidationError):close.submit()
        close.reload()
        self.assertTrue(any(r.check_code=='consumption' and r.status=='Block' for r in close.checks))
        warehouse=self.make('Warehouse',warehouse_name='Materials '+self.tag,company=self.company).name
        receipt=self.make('Stock Entry',company=self.company,purpose='Material Receipt',stock_entry_type='Material Receipt',
                          posting_date=nowdate(),items=[dict(item_code=item,qty=5000,t_warehouse=warehouse,basic_rate=1)])
        receipt.submit()
        issue=self.make('Stock Entry',company=self.company,purpose='Material Issue',stock_entry_type='Material Issue',
                        posting_date=nowdate(),items=[dict(item_code=item,qty=5000,s_warehouse=warehouse)])
        issue.submit()
        use=self.make('Material Consumption',**self.daily_scope(),work_result=result.name,
                      material_requirement=req.name,item=item,warehouse=warehouse,
                      stock_entry=issue.name,stock_entry_detail=issue.items[0].name,consumed_qty=4440)
        use.submit()
        self.assertEqual(use.remaining_qty,560)
        recovery_receipt=self.make('Stock Entry',company=self.company,purpose='Material Receipt',stock_entry_type='Material Receipt',
                                    posting_date=nowdate(),items=[dict(item_code=item,qty=560,t_warehouse=warehouse,basic_rate=1)])
        recovery_receipt.submit()
        recovered=self.make('Material Recovery',**self.daily_scope(),consumption=use.name,
                            stock_entry=recovery_receipt.name,stock_entry_detail=recovery_receipt.items[0].name,recovered_qty=560)
        recovered.submit()
        close.reload();close.save();close.submit()
        self.assertTrue(close.snapshot_hash)
        with self.assertRaises(frappe.ValidationError):result.cancel()
        issue.reload()
        with self.assertRaisesRegex(frappe.ValidationError,'Cancel submitted Lotus material contexts'):
            issue.cancel()
        with self.assertRaises(frappe.ValidationError):close.cancel()
        close.reload();close.reopen_reason='Correction requested';close.save();close.cancel()
        recovered.cancel();use.cancel();issue.reload();issue.cancel()

    def test_promax_cancellation_changes_atp_without_rewriting_snapshot(self):
        supply=self.forecast();old_hash=supply.snapshot_hash;old_atp=supply.available_to_promise_kg
        group=self.make('Cancellation Reason Group',group_code='WEATHER-'+self.tag,group_name='Weather').name
        reason=self.make('Cancellation Reason',reason_code='WIND-'+self.tag,reason_name='Wind',reason_group=group).name
        cancel=self.make('Bunch Cancellation',**self.daily_scope(),expected_harvest_date=self.start,bunch_qty=50,reason=reason)
        cancel.submit();supply.reload()
        self.assertEqual(supply.snapshot_hash,old_hash)
        self.assertAlmostEqual(supply.available_to_promise_kg,old_atp*0.95,places=2)
        order=self.order(20000)
        with self.assertRaises(frappe.ValidationError):
            reserve(supply.name,order.name,order.items[0].name,old_atp,'after-loss-'+self.tag)
        cancel.cancel();supply.reload()
        self.assertAlmostEqual(supply.available_to_promise_kg,old_atp,places=2)
        # Manual draft saves must not subtract cancellations twice.
        cancel=self.make('Bunch Cancellation',**self.daily_scope(),expected_harvest_date=self.start,bunch_qty=50,reason=reason)
        cancel.submit()
        draft=self.make('Harvest Forecast',farm=self.farm,farm_block=self.block,crop_cycle=self.cycle,
                        sucker_selection_batch=self.cohort,forecast_basis='Manual',source_bunch_qty=1000,
                        harvest_profile=self.profile,packout_profile=self.pack_profile,item=self.item,
                        period_start_date=self.start,period_end_date=add_days(self.start,6))
        self.assertEqual(draft.net_source_bunch_qty,950)
        draft.save();draft.reload();self.assertEqual(draft.source_bunch_qty,1000)
        self.assertEqual(draft.net_source_bunch_qty,950)

    def test_promax_plot_cycles_and_labor_summary(self):
        block=frappe.get_doc('Farm Block',self.block);block.area_ha=2;block.save()
        plot=self.make('Farm Plot',farm=self.farm,farm_block=self.block,plot_code='A12.2',plot_name='Second',area_ha=1).name
        other=self.make('Crop Cycle',farm=self.farm,farm_block=self.block,farm_plot=plot,cycle_no=1,
                        planting_date=nowdate(),variety=self.variety)
        self.assertNotEqual(other.name,self.parent)
        with self.assertRaises(frappe.ValidationError):
            self.make('Crop Cycle',farm=self.farm,farm_block=self.block,cycle_no=3,
                      parent_cycle=self.cycle,variety=self.variety)
        category=self.make('Work Category',category_code='LAB-'+self.tag,category_name='Labor').name
        summary=self.make('Daily Labor Summary',farm=self.farm,posting_date=nowdate(),work_category=category,
                          work_area='Field',headcount=40,present=32,staffing_target=35,area_ha=5,actual_workdays=31.25)
        summary.submit();self.assertEqual(summary.staffing_gap,-3)
        self.assertAlmostEqual(summary.workdays_per_ha,6.25)
        with self.assertRaises(frappe.ValidationError):
            self.make('Daily Labor Summary',farm=self.farm,posting_date=nowdate(),work_category=category,
                      work_area='Field',headcount=10,present=11,staffing_target=10)

    def test_promax_cycle_close_requires_daily_close_and_reopen_reason(self):
        plan,_,_=self.daily_plan(material=False)
        team=self.make('Work Team',farm=self.farm,team_code='C-'+self.tag,team_name='Closing team').name
        self.make('Labor Allocation',**self.daily_scope(),work_plan=plan.name,work_plan_line=plan.lines[0].name,
                  work_team=team,allocated_workdays=32,allocation_note='Full shift').submit()
        self.make('Daily Work Result',**self.daily_scope(),work_plan=plan.name,work_plan_line=plan.lines[0].name,
                  completed_qty=1250,actual_workdays=32).submit()
        scope={k:v for k,v in self.daily_scope().items() if k!='sucker_selection_batch'}
        closing=self.make('Cycle Closing Report',**scope)
        with self.assertRaises(frappe.ValidationError):closing.submit()
        closing.reload()
        self.make('Daily Production Close',farm=self.farm,posting_date=nowdate()).submit()
        closing.submit()
        self.assertEqual(frappe.db.get_value('Crop Cycle',self.cycle,'status'),'Closed')
        self.assertEqual(closing.actual_workdays,32)
        with self.assertRaises(frappe.ValidationError):closing.cancel()
        closing.reload();closing.reopen_reason='Continue harvesting';closing.save();closing.cancel()
        self.assertEqual(frappe.db.get_value('Crop Cycle',self.cycle,'status'),'Harvesting')

    def test_promax_source_registry_mapping_and_duplicate_row_rejection(self):
        from lotus_farm.source_data import staged_row
        source=self.make('Source File Registry',source_key='SRC-'+self.tag,source_path='/AnhDung/test.xlsx',
                         source_filename='test.xlsx',sha256='a'*64,business_period='2026-10',migration_tier='A',source_status='Active')
        self.make('Legacy Organization Map',legacy_key='ORG-'+self.tag,legacy_source_unit='XNC-BP1',legacy_farm='BP1.1.1',
                  farm=self.farm,company=self.company,approval_state='Approved')
        row=staged_row(source.source_key,'DATALO',2,{'plot':'A12.1'},'ORG-'+self.tag)
        row.update(row_status='Imported',target_doctype='Farm Plot',target_name=self.plot)
        batch=self.make('Source Import Batch',source_file=source.name,farm=self.farm,batch_key='BATCH-'+self.tag,rows=[row])
        batch.submit();self.assertEqual(batch.resolved_percent,100)
        with self.assertRaises(frappe.ValidationError):
            self.make('Source Import Batch',source_file=source.name,farm=self.farm,batch_key='RETRY-'+self.tag,rows=[row])
        source.sha256='b'*64
        with self.assertRaises(frappe.ValidationError):source.save()
        rejected=staged_row(source.source_key,'DATALO',3,{'plot':'unknown'},'ORG-'+self.tag)
        rejected.update(row_status='Rejected',reject_reason='Missing plot mapping',reject_owner='Administrator')
        batch=self.make('Source Import Batch',source_file=source.name,farm=self.farm,batch_key='REJECT-'+self.tag,rows=[rejected])
        batch.submit()

    def test_360_field_capture_replay_evidence_and_dashboard(self):
        import json
        from lotus_farm.field import capture, map_data, bootstrap
        from lotus_farm.reporting import dashboard,plot_history
        plan,_,_=self.daily_plan(material=False)
        self.make('Plot Geometry',farm=self.farm,farm_plot=self.plot,version=1,approval_state='Approved',reason='Survey checked',
                  geojson=json.dumps(dict(type='Polygon',coordinates=[[[106,10],[107,10],[107,11],[106,11],[106,10]]])))
        values=dict(**self.daily_scope(),work_plan=plan.name,work_plan_line=plan.lines[0].name,
                    completed_qty=1000,actual_workdays=25,unfinished_reason='Rain')
        values.pop('farm')
        args=dict(client_event_id='capture-'+self.tag,farm=self.farm,target_doctype='Daily Work Result',values=values,
                  captured_at=nowdate()+' 00:00:00',latitude=10.5,longitude=106.5,gps_accuracy_m=4)
        first=capture(**args);again=capture(**args)
        self.assertEqual(first['document'],again['document']);self.assertTrue(again['replayed'])
        evidence=frappe.get_doc('Field Capture',first['capture'])
        self.assertEqual(evidence.target_name,first['document'])
        self.assertEqual(frappe.get_doc('Daily Work Result',first['document']).field_capture,evidence.name)
        evidence.latitude=11
        with self.assertRaises(frappe.ValidationError):evidence.save()
        args['values']['completed_qty']=1001
        with self.assertRaises(frappe.ValidationError):capture(**args)
        summary=dashboard(nowdate(),nowdate(),farm=self.farm)
        self.assertEqual(summary['farms'][0]['work_completion_percent'],80)
        self.assertEqual(len(map_data(self.farm)['features']),1)
        self.assertTrue(any(e['name']==first['document'] for e in plot_history(self.plot)['events']))
        self.assertEqual(bootstrap(self.farm,nowdate())['user'],'Administrator')

    def test_360_excel_staging_dry_run_import_and_tamper(self):
        import hashlib,json
        from io import BytesIO
        from openpyxl import Workbook
        from frappe.utils.file_manager import save_file
        from lotus_farm.importing import stage_workbook,preview_import,import_rows
        book=Workbook();sheet=book.active;sheet.title='Planting'
        header=['Org','Block','Plot','Cycle','Cohort','Date','Type','Plants','Area'];sheet.append(header)
        org='ORG360-'+self.tag
        sheet.append([org,self.block,self.plot,self.cycle,self.cohort,nowdate(),'Replanting','1.250','0,5'])
        buffer=BytesIO();book.save(buffer);data=buffer.getvalue()
        file=save_file('planting-'+self.tag+'.xlsx',data,None,None,is_private=1)
        source=self.make('Source File Registry',source_key='XLSX360-'+self.tag,source_path='/test/planting.xlsx',source_filename='planting.xlsx',
                         sha256=hashlib.sha256(data).hexdigest(),business_period=nowdate()[:7],migration_tier='A',source_status='Active')
        self.make('Legacy Organization Map',legacy_key=org,legacy_source_unit='Old company',legacy_farm='Farm old',farm=self.farm,company=self.company,approval_state='Approved')
        names=['farm_block','farm_plot','crop_cycle','sucker_selection_batch','posting_date','event_type','plant_qty','area_ha']
        types=['Text','Text','Text','Text','Date','Text','Integer','Number']
        mapping=self.make('Source Import Mapping',mapping_name='PLANTING-'+self.tag,target_doctype='Planting Event',sheet_name='Planting',header_row=1,first_data_row=2,
                          decimal_mark=',',grouping_mark='.',legacy_org_column='Org',version=1,approval_state='Approved',
                          fields=[dict(source_column=c,target_field=n,value_type=t,required=1) for c,n,t in zip(header[1:],names,types)])
        staged=stage_workbook(source.name,mapping.name,self.farm,file.file_url)
        self.assertEqual(stage_workbook(source.name,mapping.name,self.farm,file.file_url)['batch'],staged['batch'])
        self.assertEqual(preview_import(staged['batch'])[0]['status'],'Ready')
        self.assertFalse(frappe.db.exists('Planting Event',{'source_import_batch':staged['batch']}))
        batch=frappe.get_doc('Source Import Batch',staged['batch']);original=batch.rows[0].normalized_json
        altered=json.loads(original);altered['plant_qty']=9000;batch.rows[0].normalized_json=json.dumps(altered);batch.save()
        with self.assertRaises(frappe.ValidationError):import_rows(batch.name)
        batch.reload();batch.rows[0].normalized_json=original;batch.save()
        result=import_rows(batch.name);self.assertEqual(len(result['created_drafts']),1)
        target=frappe.get_doc('Planting Event',result['created_drafts'][0]);self.assertEqual(target.plant_qty,1250);self.assertEqual(target.docstatus,0)
        self.assertEqual(import_rows(batch.name)['created_drafts'],[])
        batch.reload();batch.submit();self.assertEqual(batch.resolved_percent,100)

    def test_360_scale_binding_and_schedule_due_tasks(self):
        from lotus_farm.field import suggest_work,make_suggested_plan
        frappe.db.set_single_value('Lotus Farm Settings','require_registered_scale',1)
        with self.assertRaises(frappe.ValidationError):ingest_scale(self.farm,'unregistered',self.tag,nowdate()+' 00:00:00',100,5)
        self.make('Scale Device',farm=self.farm,device_id='360-'+self.tag,integration_user='Administrator',calibrated_on=add_days(nowdate(),-1),calibration_due=add_days(nowdate(),1),unit='Kg')
        result=ingest_scale(self.farm,'360-'+self.tag,self.tag,nowdate()+' 00:00:00',100,5);self.assertEqual(result['net_kg'],95)
        with self.assertRaises(frappe.ValidationError):ingest_scale(self.farm,'360-'+self.tag,'old',add_days(nowdate(),-2)+' 00:00:00',100,5)
        plan,_,_=self.daily_plan(material=False)
        self.make('Work Schedule Rule',farm=self.farm,rule_name='BAG-SCHEDULE-'+self.tag,work_type=plan.lines[0].work_type,
                  anchor='Selection',offset_days=100,repeat_days=7,quantity_basis='Selected Suckers',valid_from=add_days(nowdate(),-1),valid_to=add_days(nowdate(),30),version=1,approval_state='Approved')
        cycle=frappe.get_doc('Crop Cycle',self.cycle);cycle.status='Active';cycle.save()
        suggested=suggest_work(self.farm,nowdate());self.assertEqual(len(suggested),1);self.assertEqual(suggested[0]['planned_qty'],1000)
        created=make_suggested_plan(self.farm,nowdate());self.assertEqual(created['docstatus'],0)
        self.assertEqual(suggest_work(self.farm,nowdate()),[])

    def test_360_integration_retry_and_closed_day_blocker(self):
        import hashlib
        from io import BytesIO
        from openpyxl import Workbook
        from frappe.utils.file_manager import save_file
        from lotus_farm.importing import run_task
        from lotus_farm.daily_operations import close_checks
        book=Workbook();sheet=book.active;sheet.title='Wrong';sheet.append(['Org','Plants']);sheet.append(['old',2]);buffer=BytesIO();book.save(buffer);data=buffer.getvalue()
        file=save_file('bad-'+self.tag+'.xlsx',data,None,None,is_private=1)
        source=self.make('Source File Registry',source_key='BAD360-'+self.tag,source_path='/test/bad.xlsx',source_filename='bad.xlsx',sha256=hashlib.sha256(data).hexdigest(),business_period=nowdate()[:7],migration_tier='A',source_status='Active')
        mapping=self.make('Source Import Mapping',mapping_name='BAD-'+self.tag,target_doctype='Planting Event',sheet_name='Expected',header_row=1,first_data_row=2,decimal_mark=',',grouping_mark='.',legacy_org_column='Org',version=1,approval_state='Approved',fields=[dict(source_column='Plants',target_field='plant_qty',value_type='Integer')])
        task=self.make('Integration Task',farm=self.farm,external_id='external-'+self.tag,source_system='test',source_hash=source.sha256,source_file=source.name,mapping=mapping.name,file=file.file_url,posting_date=nowdate())
        self.assertEqual(run_task(task.name)['status'],'Failed');self.assertEqual(run_task(task.name)['status'],'Failed')
        task.reload();self.assertEqual(task.retry_count,2)
        self.assertTrue(any(c['check_code']=='integration_task' and c['status']=='Block' for c in close_checks(self.farm,nowdate())))
        task.status='Completed'
        with self.assertRaises(frappe.ValidationError):task.save()

    def test_360_quick_incoming_qc_and_qr(self):
        from lotus_farm.packhouse import receive_quality
        from lotus_farm.field import lot_qr
        from lotus_farm.reporting import trace_lot,packhouse_day
        actual=self.make('Harvest Actual',farm=self.farm,farm_block=self.block,crop_cycle=self.cycle,sucker_selection_batch=self.cohort,
                         harvest_date=nowdate(),harvested_bunch_qty=4,gross_weight_kg=100,rejected_weight_kg=0)
        actual.submit()
        lot=self.make('Harvest Lot',farm=self.farm,received_date=nowdate(),sources=[dict(harvest_actual=actual.name,contributed_kg=100)])
        lot.submit()
        reason=self.make('Defect Reason',defect_code='QC360-'+self.tag,defect_name='Bruised',category='Mechanical')
        result=receive_quality('qc-'+self.tag,self.farm,nowdate(),lot.name,90,reason.name)
        again=receive_quality('qc-'+self.tag,self.farm,nowdate(),lot.name,90,reason.name)
        self.assertEqual(result['document'],again['document']);self.assertEqual(result['rejected_kg'],10)
        with self.assertRaises(frappe.ValidationError):
            receive_quality('qc-'+self.tag,self.farm,nowdate(),lot.name,89,reason.name)
        self.assertTrue(lot_qr(lot.name)['image'].startswith('data:image/svg+xml;base64,'))
        self.assertEqual(trace_lot(lot.name)['sources'][0]['farm_plot'],self.plot)
        self.assertEqual(packhouse_day(self.farm,nowdate())['lots'][0].remaining_to_pack_kg,90)
