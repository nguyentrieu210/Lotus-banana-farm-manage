"""Takeover acceptance tests for a disposable ERPNext site only.

All quantities below are synthetic test fixtures in a newly created Farm. They
are not imported AnhDung actuals and never allocate the zone handover journal.
Run with bench --site <disposable-site> run-tests --app lotus_farm
--module lotus_farm.tests.test_onedrive_takeover.
"""

import json
import unittest

import frappe
from frappe.utils import add_days, getdate, nowdate

from lotus_farm.tests import test_brd as brd_fixtures


class TestOneDriveTakeoverOnSite(unittest.TestCase):
    # Reuse fixture setup, not TestBRDOnSite inheritance: selecting this module
    # must run only these takeover cases, rather than the entire BRD suite.
    setUpClass = classmethod(brd_fixtures.TestBRDOnSite.setUpClass.__func__)
    make = staticmethod(brd_fixtures.TestBRDOnSite.make)
    tearDown = brd_fixtures.TestBRDOnSite.tearDown

    def setUp(self):
        brd_fixtures.TestBRDOnSite.setUp(self)
        self.today = nowdate()
        self.cut_date = add_days(self.today, -60)
        self.block = self.make(
            "Farm Block", farm=self.farm, block_code="HANDOVER-" + self.tag,
            block_name="Synthetic takeover block", farm_zone="A", area_ha=1,
            variety=self.variety,
        ).name
        self.plot = self.make(
            "Farm Plot", farm=self.farm, farm_block=self.block,
            plot_code="TAKEOVER-1", plot_name="Observed takeover plot", area_ha=1,
        ).name
        self.takeover = self.make(
            "Crop Cycle", farm=self.farm, farm_block=self.block, farm_plot=self.plot,
            cycle_no=2, origin_basis="Handover", status="Active", variety=self.variety,
            inheritance_note="Test fixture: previous crop and planting history unavailable.",
            coverage_start_date=add_days(self.cut_date, -1),
        )

    def scope(self, day=None, cycle=None):
        return dict(
            farm=self.farm, farm_block=self.block, farm_plot=self.plot,
            crop_cycle=cycle or self.takeover.name, posting_date=day or self.today,
        )

    def adoption_and_tag(self, day):
        from lotus_farm.onedrive_workspace import create_adoption, generate_tags, library

        data, _ = library()
        adoption = create_adoption(
            self.farm, data["defaults"][0]["key"], valid_from=add_days(self.cut_date, -20),
            approve=True,
        )
        generate_tags(adoption["name"], add_days(day, -5), add_days(day, 5))
        name = frappe.db.get_value("Bunch Tag", {
            "farm": self.farm, "process_adoption": adoption["name"],
            "valid_from": ["<=", day], "valid_to": [">=", day],
        }, "name")
        self.assertTrue(name)
        return adoption, name

    def cut(self, tag, cycle=None, cohort=None):
        doc = self.make(
            "Bunch Operation", farm=self.farm, farm_block=self.block, farm_plot=self.plot,
            crop_cycle=cycle or self.takeover.name, sucker_selection_batch=cohort,
            operation_date=self.cut_date, operation_type="Cut Bud", bunch_qty=5,
            bunch_tag=tag, rejected_qty=0,
        )
        doc.submit()
        return doc

    def work_evidence(self, day, completed_qty):
        """Enter genuine task/result/allocation fixtures for each operational day."""
        if not frappe.db.exists("UOM", "Bunch"):
            self.make("UOM", uom_name="Bunch")
        if not getattr(self, "work_type", None):
            category = self.make(
                "Work Category", category_code="TAKE-" + self.tag,
                category_name="Takeover test tasks",
            ).name
            self.work_type = self.make(
                "Work Type", work_code="TAKE-" + self.tag, work_name="Observed bunch task",
                category=category, uom="Bunch", allow_daywork=1,
                productivity_per_workday=20,
            ).name
            self.team = self.make(
                "Work Team", farm=self.farm, team_code="TAKE-" + self.tag,
                team_name="Takeover test field team",
            ).name
        line_scope = {k: v for k, v in self.scope(day).items() if k != "posting_date"}
        plan = self.make(
            "Daily Work Plan", farm=self.farm, posting_date=day,
            lines=[dict(**line_scope, work_type=self.work_type, planned_qty=completed_qty)],
        )
        plan.submit()
        self.make(
            "Labor Allocation", **self.scope(day), work_plan=plan.name,
            work_plan_line=plan.lines[0].name, work_team=self.team,
            allocated_workdays=0.5, allocation_note="Synthetic fixture: observed half-day team allocation.",
        ).submit()
        self.make(
            "Daily Work Result", **self.scope(day), work_plan=plan.name,
            work_plan_line=plan.lines[0].name, completed_qty=completed_qty, actual_workdays=0.5,
        ).submit()
        return plan

    def test_inherited_cut_to_stock_and_reviewed_closes_without_invented_cohort(self):
        from lotus_farm.api import ingest_scale
        from lotus_farm.daily_operations import close_checks
        from lotus_farm.onedrive_supply import close_forecast, prepare_cut_forecasts, source_cut
        from lotus_farm.stock_bridge import make_repack_entry

        _, tag = self.adoption_and_tag(self.cut_date)
        cut = self.cut(tag)
        balance = source_cut(cut.name)["balance"]
        mapping = [dict(item=self.item, packout_profile=self.pack_profile, share_percent=100)]
        preview = prepare_cut_forecasts(
            [cut.name], balance["start"], balance["end"], mapping, preview=1,
        )
        prepared = prepare_cut_forecasts(
            [cut.name], balance["start"], balance["end"], mapping, preview=0,
            client_event_id="TAKEOVER-SUPPLY-" + self.tag,
            expected_source_hash=preview["source_hash"],
        )
        supply = frappe.get_doc("Harvest Forecast", prepared["documents"][0])
        supply.supply_state = "Released"
        supply.save()
        frozen_supply = (supply.snapshot_hash, supply.source_snapshot)
        self.work_evidence(self.cut_date, 5)
        self.work_evidence(self.today, 4)

        with self.assertRaisesRegex(frappe.ValidationError, "cắt bắp gốc"):
            self.make(
                "Harvest Actual", farm=self.farm, farm_block=self.block, crop_cycle=self.takeover.name,
                harvest_date=self.today, harvested_bunch_qty=1, gross_weight_kg=25,
                rejected_weight_kg=0,
            )

        if not frappe.db.exists("UOM", "Centimeter"):
            self.make("UOM", uom_name="Centimeter")
        measurement = self.make(
            "Fruit Measurement", **self.scope(), row_code="Lane 1", uom="Centimeter",
            source_cut_operation=cut.name,
            samples=[
                dict(lane="Lane 1", sample_no="1", dimension="Length", value=18, uom="Centimeter"),
                dict(lane="Lane 1", sample_no="2", dimension="Length", value=22, uom="Centimeter"),
            ],
        )
        measurement.submit()
        self.assertEqual(measurement.sample_count, 2)
        self.assertEqual(measurement.average_length, 20)
        self.assertEqual(measurement.ribbon_color, tag)

        group = self.make(
            "Cancellation Reason Group", group_code="TAKE-" + self.tag,
            group_name="Observed field losses",
        ).name
        cancellation_reason = self.make(
            "Cancellation Reason", reason_code="TAKE-" + self.tag,
            reason_name="Observed damaged bunch", reason_group=group,
        ).name
        cancellation = self.make(
            "Bunch Cancellation", **self.scope(), source_operation=cut.name,
            expected_harvest_date=cut.expected_harvest_date, bunch_qty=1,
            reason=cancellation_reason,
        )
        cancellation.submit()

        self.make(
            "Scale Device", farm=self.farm, device_id="TAKE-" + self.tag,
            integration_user="Administrator", calibrated_on=add_days(self.today, -1),
            calibration_due=add_days(self.today, 30), unit="Kg",
        )
        reading = ingest_scale(
            self.farm, "TAKE-" + self.tag, "RECEIPT-1",
            add_days(self.today, -1) + " 12:00:00", 105, 5,
        )["document"]
        actual = self.make(
            "Harvest Actual", farm=self.farm, farm_block=self.block, crop_cycle=self.takeover.name,
            harvest_date=self.today, harvested_bunch_qty=4, gross_weight_kg=100,
            rejected_weight_kg=0, source_cut_operation=cut.name, scale_reading=reading,
        )
        actual.submit()
        self.assertFalse(actual.sucker_selection_batch)
        self.assertEqual(actual.ribbon_color, tag)
        self.assertEqual(actual.forecast, supply.name)
        supply.reload()
        self.assertEqual((supply.snapshot_hash, supply.source_snapshot), frozen_supply)

        with self.assertRaises(frappe.ValidationError):
            self.make(
                "Harvest Actual", farm=self.farm, farm_block=self.block, crop_cycle=self.takeover.name,
                harvest_date=self.today, harvested_bunch_qty=1, gross_weight_kg=25,
                rejected_weight_kg=0, source_cut_operation=cut.name,
            )
        with self.assertRaises(frappe.ValidationError):
            cut.cancel()

        raw = self.make(
            "Item", item_code="TAKE-RAW-" + self.tag, item_group="All Item Groups",
            stock_uom="Kg", is_stock_item=1, has_batch_no=1,
        ).name
        raw_warehouse = self.make(
            "Warehouse", warehouse_name="Takeover Raw " + self.tag, company=self.company,
        ).name
        finished_warehouse = self.make(
            "Warehouse", warehouse_name="Takeover Finished " + self.tag, company=self.company,
        ).name
        batch = self.make("Batch", batch_id="TAKE-RAW-" + self.tag, item=raw).name
        raw_receipt = self.make(
            "Stock Entry", stock_entry_type="Material Receipt", purpose="Material Receipt",
            company=self.company, posting_date=self.today,
            items=[dict(
                item_code=raw, t_warehouse=raw_warehouse, qty=100, uom="Kg", stock_uom="Kg",
                conversion_factor=1, basic_rate=1, batch_no=batch, use_serial_batch_fields=1,
            )],
        )
        raw_receipt.submit()
        lot = self.make(
            "Harvest Lot", farm=self.farm, received_date=self.today, raw_item=raw,
            raw_warehouse=raw_warehouse, raw_batch=batch, scale_reading=reading,
            sources=[dict(harvest_actual=actual.name, contributed_kg=100)],
        )
        lot.submit()
        self.assertTrue(any(r["check_code"] == "incoming_qc" and r["status"] == "Block"
                            for r in close_checks(self.farm, self.today)))
        self.make(
            "Incoming Quality Inspection", farm=self.farm, posting_date=self.today,
            harvest_lot=lot.name, accepted_kg=100,
        ).submit()

        if not frappe.db.exists("Gender", "Male"):
            self.make("Gender", gender="Male")
        employee = self.make(
            "Employee", first_name="Takeover " + self.tag, gender="Male",
            date_of_birth=add_days(self.today, -10000), date_of_joining=add_days(self.today, -100),
            company=self.company, status="Active",
        ).name
        shift = self.make(
            "Packhouse Shift", farm=self.farm, posting_date=self.today, shift_code="DAY",
            started_at=self.today + " 07:00:00", ended_at=self.today + " 15:00:00",
            supervisor="Administrator", labor=[dict(employee=employee, workdays=0.5)],
            preprocessing=[dict(harvest_lot=lot.name, processed_bunches=4, processed_kg=100)],
        )
        loss_reason = self.make(
            "Defect Reason", defect_code="TAKE-LOSS-" + self.tag,
            defect_name="Measured processing loss", category="Other",
        ).name
        run = self.make(
            "Packout Run", farm=self.farm, company=self.company, packing_date=self.today,
            packhouse_shift=shift.name, quality_standard=self.standard,
            target_warehouse=finished_warehouse, sources=[dict(harvest_lot=lot.name, input_kg=100)],
            outputs=[dict(item=self.item, net_kg=84)], reject_kg=0, other_loss_kg=16,
            loss_details=[dict(loss_type="Process Loss", weight_kg=16, reason=loss_reason)],
            qc_state="Released",
        )
        run.submit()
        self.assertTrue(any(r["check_code"] == "stock_posted" and r["status"] == "Block"
                            for r in close_checks(self.farm, self.today)))
        entry = frappe.get_doc("Stock Entry", make_repack_entry(run.name)["stock_entry"])
        entry.submit()
        from erpnext.stock.utils import get_stock_balance

        self.assertEqual(entry.docstatus, 1)
        self.assertAlmostEqual(get_stock_balance(self.item, finished_warehouse), 84)
        self.assertAlmostEqual(get_stock_balance(raw, raw_warehouse), 0)
        entry.reload()
        impacts = json.loads(entry.lotus_forecast_impacts_json)
        self.assertAlmostEqual(impacts[supply.name][self.item], 84)
        supply.reload()
        self.assertAlmostEqual(supply.materialized_qty_kg, 84)
        self.assertAlmostEqual(supply.output_plan[0].materialized_qty_kg, 84)
        self.assertEqual((supply.snapshot_hash, supply.source_snapshot), frozen_supply)
        shift.reload()
        shift.submit()
        close_forecast(supply.name, "All source bunches received and finished stock posted")
        supply.reload()
        self.assertEqual(supply.supply_state, "Closed")
        self.assertEqual((supply.snapshot_hash, supply.source_snapshot), frozen_supply)

        closing = self.make("Cycle Closing Report", **self.scope())
        with self.assertRaises(frappe.ValidationError):
            closing.submit()
        closing.reload()
        for day in (self.cut_date, self.today):
            checks = close_checks(self.farm, day)
            self.assertFalse([r for r in checks if r["status"] == "Block"], checks)
            self.make("Daily Production Close", farm=self.farm, posting_date=day).submit()
        closing.submit()
        self.assertEqual(frappe.db.get_value("Crop Cycle", self.takeover.name, "status"), "Closed")
        self.assertEqual(closing.planted_qty, 0)
        self.assertEqual(closing.cancelled_bunch_qty, 1)
        self.assertEqual(closing.harvested_bunch_qty, 4)
        self.assertEqual(closing.gross_harvest_kg, 100)
        self.assertEqual(closing.finished_kg, 84)
        self.assertEqual(closing.process_loss_kg, 16)
        self.assertEqual(closing.actual_workdays, 1)
        self.assertAlmostEqual(closing.tons_per_ha, 0.1)
        self.assertEqual(closing.origin_basis, "Handover")
        self.assertEqual(getdate(closing.coverage_start_date), getdate(add_days(self.cut_date, -1)))
        self.assertFalse(closing.planting_date_known)
        self.assertFalse(frappe.db.exists("Sucker Selection Batch", {"crop_cycle": self.takeover.name}))
        self.assertFalse(frappe.db.exists("Planting Event", {"crop_cycle": self.takeover.name}))
        self.takeover.reload()
        self.assertFalse(self.takeover.parent_cycle)
        self.assertFalse(self.takeover.planting_date)
        snapshot = json.loads(closing.snapshot_json)
        self.assertEqual(len(snapshot["actuals"]), 1)
        self.assertTrue(snapshot["cycle_origin"]["inherited_opening"])
        self.assertFalse(snapshot["cycle_origin"]["planting_date_known"])
        self.assertIsNone(snapshot["cycle_origin"]["planting_date"])
        self.assertIsNone(snapshot["cycle_origin"]["parent_cycle"])

    def test_successor_requires_parent_and_real_selected_cohort(self):
        _, tag = self.adoption_and_tag(self.cut_date)
        with self.assertRaises(frappe.ValidationError):
            self.make(
                "Crop Cycle", farm=self.farm, farm_block=self.block, farm_plot=self.plot,
                cycle_no=3, origin_basis="Observed", variety=self.variety,
            )
        successor = self.make(
            "Crop Cycle", farm=self.farm, farm_block=self.block, farm_plot=self.plot,
            cycle_no=3, origin_basis="Observed", parent_cycle=self.takeover.name,
            variety=self.variety, status="Active",
        )
        with self.assertRaisesRegex(frappe.ValidationError, "Ratoon operations.*Sucker Selection Batch"):
            self.cut(tag, cycle=successor.name)
        with self.assertRaisesRegex(frappe.ValidationError, "Ratoon harvests.*Sucker Selection Batch"):
            self.make(
                "Harvest Actual", farm=self.farm, farm_block=self.block, crop_cycle=successor.name,
                harvest_date=self.today, harvested_bunch_qty=4, gross_weight_kg=100,
                rejected_weight_kg=0,
            )
        cohort = self.make(
            "Sucker Selection Batch", farm=self.farm, farm_block=self.block,
            crop_cycle=successor.name, selection_date=add_days(self.cut_date, -5), selected_sucker_qty=5,
            notes="Synthetic fixture: five individually counted selected suckers.",
        )
        cut = self.cut(tag, cycle=successor.name, cohort=cohort.name)
        self.assertEqual(cut.sucker_selection_batch, cohort.name)
        self.assertEqual(successor.parent_cycle, self.takeover.name)
        self.assertEqual(successor.origin_basis, "Observed")
        self.assertEqual(getdate(cohort.selection_date), getdate(add_days(self.cut_date, -5)))
