"""OneDrive physical-source publication acceptance for a disposable site only.

Run with bench --site <disposable-site> run-tests --app lotus_farm
--module lotus_farm.tests.test_onedrive_supply. All observations are isolated
synthetic fixtures; these tests never import or allocate actual handover counts.
"""

import json
import math
import unittest
from unittest.mock import patch

import frappe
from frappe.utils import add_days, getdate

from lotus_farm.tests import test_onedrive_takeover as takeover_fixtures


class TestOneDriveSupplyOnSite(unittest.TestCase):
    # Alias the fixtures rather than inheriting their test methods.
    setUpClass = classmethod(takeover_fixtures.TestOneDriveTakeoverOnSite.setUpClass.__func__)
    make = staticmethod(takeover_fixtures.TestOneDriveTakeoverOnSite.make)
    tearDown = takeover_fixtures.TestOneDriveTakeoverOnSite.tearDown
    scope = takeover_fixtures.TestOneDriveTakeoverOnSite.scope
    adoption_and_tag = takeover_fixtures.TestOneDriveTakeoverOnSite.adoption_and_tag

    def setUp(self):
        takeover_fixtures.TestOneDriveTakeoverOnSite.setUp(self)
        # A tag beginning around month-first minus ten days has an E+55/F+70
        # window spanning two months. Both dates stay after the opening boundary.
        first = getdate(self.today).replace(day=1)
        self.cut_date = add_days(first, -65)
        self.takeover.coverage_start_date = add_days(self.cut_date, -1)
        self.takeover.save()
        self.adoption, self.tag_name = self.adoption_and_tag(self.cut_date)
        self.source = self.make(
            "Bunch Operation", farm=self.farm, farm_block=self.block, farm_plot=self.plot,
            crop_cycle=self.takeover.name, operation_date=self.cut_date,
            operation_type="Cut Bud", bunch_qty=100, rejected_qty=0, bunch_tag=self.tag_name,
        )
        self.source.submit()
        self.mapping = [dict(item=self.item, packout_profile=self.pack_profile, share_percent=100)]

    def source_details(self):
        from lotus_farm.onedrive_supply import source_cut

        return source_cut(self.source.name)

    def slices(self):
        from lotus_farm.onedrive_supply import source_rows

        rows = source_rows(self.source_details())
        self.assertEqual(len(rows), 2, rows)
        self.assertNotEqual(rows[0]["month"], rows[1]["month"])
        return rows

    def preview(self, start=None, end=None, mapping=None):
        from lotus_farm.onedrive_supply import prepare_cut_forecasts

        balance = self.source_details()["balance"]
        return prepare_cut_forecasts(
            [self.source.name], start or balance["start"], end or balance["end"],
            mapping or self.mapping, preview=1,
        )

    def create_from_preview(self, preview, event_id, start=None, end=None, mapping=None):
        from lotus_farm.onedrive_supply import prepare_cut_forecasts

        balance = self.source_details()["balance"]
        return prepare_cut_forecasts(
            [self.source.name], start or balance["start"], end or balance["end"],
            mapping or self.mapping, client_event_id=event_id, preview=0,
            expected_source_hash=preview["source_hash"],
        )

    @staticmethod
    def release(name):
        doc = frappe.get_doc("Harvest Forecast", name)
        doc.supply_state = "Released"
        doc.save()
        return doc

    def publish_months(self):
        result = []
        for index, part in enumerate(self.slices()):
            preview = self.preview(part["slice_start"], part["slice_end"])
            created = self.create_from_preview(
                preview, "MONTH-" + self.tag + "-" + str(index), part["slice_start"], part["slice_end"],
            )
            result.append(self.release(created["documents"][0]))
        return result

    def cancellation(self, quantity, on_date=None):
        if not getattr(self, "cancel_reason", None):
            group = self.make(
                "Cancellation Reason Group", group_code="SUPPLY-" + self.tag,
                group_name="Observed source losses",
            ).name
            self.cancel_reason = self.make(
                "Cancellation Reason", reason_code="SUPPLY-" + self.tag,
                reason_name="Counted damaged bunches", reason_group=group,
            ).name
        cancellation = self.make(
            "Bunch Cancellation", **self.scope(on_date or self.cut_date),
            source_operation=self.source.name, expected_harvest_date=self.source.expected_harvest_date,
            bunch_qty=quantity, reason=self.cancel_reason,
        )
        cancellation.submit()
        return cancellation

    def alternate_mapping(self):
        item = self.make(
            "Item", item_code="SUPPLY-ALT-" + self.tag, item_group="All Item Groups",
            stock_uom="Kg", is_stock_item=1, has_batch_no=1,
        ).name
        standard = self.make(
            "Quality Standard", standard_code="SUPPLY-QS-" + self.tag, version=1, item=item,
            approval_state="Approved", valid_from=add_days(self.cut_date, -10), max_defective_percent=15,
        ).name
        profile = self.make(
            "Packout Profile", profile_name="SUPPLY-PP-" + self.tag, version=1,
            farm=self.farm, variety=self.variety, item=item, quality_standard=standard,
            approval_state="Approved", valid_from=add_days(self.cut_date, -10), yield_percent=50,
        ).name
        return [dict(item=item, packout_profile=profile, share_percent=100)]

    def test_preview_creation_retry_and_changed_source_require_repreview(self):
        from lotus_farm.onedrive_supply import prepare_cut_forecasts
        from lotus_farm.onedrive_protocol import forecast_quantities

        before = frappe.db.count("Harvest Forecast", {"crop_cycle": self.takeover.name})
        preview = self.preview()
        self.assertEqual(preview["documents"], [])
        self.assertEqual(frappe.db.count("Harvest Forecast", {"crop_cycle": self.takeover.name}), before)
        expected = forecast_quantities(100, self.source_details()["parameters"])
        self.assertAlmostEqual(preview["drafts"][0]["source_bunch_qty"], 100)
        self.assertAlmostEqual(preview["drafts"][0]["gross_forecast_kg"], expected["gross_kg"], places=3)
        self.assertAlmostEqual(preview["drafts"][0]["packed_forecast_kg"], expected["processed_kg"], places=3)

        event_id = "PREPARE-" + self.tag
        created = self.create_from_preview(preview, event_id)
        retry = self.create_from_preview(preview, event_id)
        self.assertEqual(created, retry)
        self.assertEqual(len(created["documents"]), 1)
        self.assertEqual(frappe.db.count("Harvest Forecast", {"crop_cycle": self.takeover.name}), before + 1)
        doc = frappe.get_doc("Harvest Forecast", created["documents"][0])
        self.assertFalse(doc.harvest_profile)
        self.assertEqual(doc.formula_version, "lotus-onedrive/1")
        self.assertAlmostEqual(doc.packed_forecast_kg, expected["processed_kg"], places=3)
        self.assertAlmostEqual(doc.output_plan[0].expected_packed_kg, expected["processed_kg"], places=3)
        # The approved profile's 84% is deliberately not multiplied into an
        # already processed-kg source for a second time.
        self.assertNotAlmostEqual(doc.packed_forecast_kg, expected["processed_kg"] * 0.84, places=3)
        self.assertEqual(doc.source_claims[0].source_hash, preview["drafts"][0]["source_hash"])

        balance = self.source_details()["balance"]
        with self.assertRaisesRegex(frappe.ValidationError, "Mã yêu cầu đã dùng"):
            prepare_cut_forecasts(
                [self.source.name], balance["start"], add_days(balance["end"], -1), self.mapping,
                client_event_id=event_id, preview=0, expected_source_hash=preview["source_hash"],
            )
        self.cancellation(1)
        with self.assertRaisesRegex(frappe.ValidationError, "Nguồn buồng đã đổi"):
            self.create_from_preview(preview, "STALE-" + self.tag)
        self.assertEqual(frappe.db.count("Harvest Forecast", {"crop_cycle": self.takeover.name}), before + 1)
        current = self.preview()
        self.assertNotEqual(current["source_hash"], preview["source_hash"])
        self.assertAlmostEqual(current["drafts"][0]["source_bunch_qty"], 99)

    def test_two_monthly_claims_release_once_and_reject_cross_item_overlap(self):
        docs = self.publish_months()
        self.assertAlmostEqual(sum(doc.source_bunch_qty for doc in docs), 100)
        self.assertAlmostEqual(sum(doc.source_claims[0].capacity_bunch_qty for doc in docs), 100)
        self.assertLess(getdate(docs[0].period_end_date), getdate(docs[1].period_start_date))
        self.assertEqual({doc.source_claims[0].source_cut_operation for doc in docs}, {self.source.name})
        self.assertTrue(all(doc.supply_state == "Released" for doc in docs))

        alternate = self.alternate_mapping()
        with self.assertRaisesRegex(frappe.ValidationError, "đã phát hành"):
            self.preview(docs[0].period_start_date, docs[0].period_end_date, alternate)
        with self.assertRaisesRegex(frappe.ValidationError, "đã phát hành"):
            self.preview(docs[0].period_end_date, docs[1].period_start_date)

        # Direct native document release must enforce ownership as well as the
        # preparation API, including when an entirely different Item is chosen.
        duplicate = self.make(
            "Harvest Forecast", farm=self.farm, farm_block=self.block, crop_cycle=self.takeover.name,
            process_adoption=self.adoption["name"],
            source_claims=[dict(source_cut_operation=self.source.name)],
            period_start_date=docs[0].period_start_date, period_end_date=docs[0].period_end_date,
            planning_granularity="Custom", supply_state="Draft", forecast_basis="Cut Bud Operations",
            output_plan=[dict(
                item=alternate[0]["item"], packout_profile=alternate[0]["packout_profile"],
                source_share_percent=100,
            )],
        )
        with self.assertRaisesRegex(frappe.ValidationError, "đã phát hành"):
            self.release(duplicate.name)
        duplicate.reload()
        self.assertEqual(duplicate.supply_state, "Draft")
        self.assertEqual(frappe.db.count("Harvest Forecast", {
            "crop_cycle": self.takeover.name, "supply_state": "Released",
        }), 2)

    def test_native_legacy_release_blocked_after_adoption_and_successor_stays_strict(self):
        native = self.make(
            "Harvest Forecast", farm=self.farm, farm_block=self.block, crop_cycle=self.takeover.name,
            harvest_profile=self.profile, packout_profile=self.pack_profile, item=self.item,
            forecast_basis="Cut Bud Operations", planning_granularity="Custom",
            period_start_date=self.source.expected_harvest_date,
            period_end_date=add_days(self.source.expected_harvest_date, 6), supply_state="Draft",
        )
        self.assertAlmostEqual(native.source_bunch_qty, 100)
        with self.assertRaisesRegex(frappe.ValidationError, "Vườn áp dụng OneDrive"):
            self.release(native.name)
        native.reload()
        self.assertEqual(native.supply_state, "Draft")

        successor = self.make(
            "Crop Cycle", farm=self.farm, farm_block=self.block, farm_plot=self.plot,
            cycle_no=3, origin_basis="Observed", parent_cycle=self.takeover.name,
            variety=self.variety, status="Active",
        )
        base = dict(
            farm=self.farm, farm_block=self.block, crop_cycle=successor.name,
            forecast_basis="Cut Bud Operations", planning_granularity="Custom",
            period_start_date=self.source.expected_harvest_date,
            period_end_date=add_days(self.source.expected_harvest_date, 6), supply_state="Draft",
        )
        with self.assertRaisesRegex(frappe.ValidationError, "Ratoon forecasts.*Sucker Selection Batch"):
            self.make(
                "Harvest Forecast", **base, harvest_profile=self.profile,
                packout_profile=self.pack_profile, item=self.item,
            )
        with self.assertRaisesRegex(frappe.ValidationError, "Ratoon forecasts.*Sucker Selection Batch"):
            self.make(
                "Harvest Forecast", **base, process_adoption=self.adoption["name"],
                source_claims=[dict(source_cut_operation=self.source.name)],
                output_plan=[dict(item=self.item, packout_profile=self.pack_profile, source_share_percent=100)],
            )

    def test_harvest_and_cancellation_consume_all_month_claims_without_rewriting_snapshots(self):
        from lotus_farm.cut_supply import interval_quantity
        from lotus_farm.onedrive_supply import actual_forecast_shares, remaining_fraction
        from lotus_farm.onedrive_workspace import forecast

        docs = self.publish_months()
        snapshots = {doc.name: (doc.snapshot_hash, doc.source_snapshot) for doc in docs}
        first_capacity = float(docs[0].source_bunch_qty)
        harvested = math.ceil(first_capacity) + 5
        self.assertLess(harvested + 3, 100)
        event_date = str(getdate(docs[0].period_start_date))
        actual = self.make(
            "Harvest Actual", farm=self.farm, farm_block=self.block, crop_cycle=self.takeover.name,
            harvest_date=event_date, harvested_bunch_qty=harvested, gross_weight_kg=harvested * 25,
            rejected_weight_kg=0, source_cut_operation=self.source.name,
        )
        actual.submit()
        self.assertEqual(actual.forecast, docs[0].name)
        self.cancellation(3, add_days(event_date, 1))
        details = self.source_details()
        self.assertAlmostEqual(details["balance"]["remaining"], 100 - harvested - 3)

        shares = actual_forecast_shares(actual)
        self.assertEqual({doc.name for doc, _ in shares}, {doc.name for doc in docs})
        self.assertAlmostEqual(sum(share for _, share in shares), 1)
        remaining_bunches = 0
        for index, doc in enumerate(docs):
            doc.reload()
            self.assertEqual((doc.snapshot_hash, doc.source_snapshot), snapshots[doc.name])
            remaining = interval_quantity(details["balance"], doc.period_start_date, doc.period_end_date)
            remaining_bunches += remaining
            self.assertAlmostEqual(remaining_fraction(doc), remaining / float(doc.source_bunch_qty))
            self.assertAlmostEqual(
                doc.available_to_promise_kg,
                float(doc.safe_saleable_kg) * remaining / float(doc.source_bunch_qty), places=3,
            )
            if index == 0:
                self.assertEqual(doc.available_to_promise_kg, 0)
        self.assertAlmostEqual(remaining_bunches, 100 - harvested - 3)

        board = forecast(farm=self.farm, from_date=str(getdate(docs[0].period_start_date).replace(day=1)))
        rows = [row for row in board["source_rows"] if row["source"] == self.source.name]
        self.assertAlmostEqual(sum(row["remaining_bunch_qty"] for row in rows), remaining_bunches)
        for row in rows:
            preview = self.preview_without_ownership(row)
            self.assertAlmostEqual(preview["source_bunch_qty"], row["remaining_bunch_qty"])
            self.assertAlmostEqual(preview["processed_kg"], row["processed_kg"], places=3)

        actual.cancel()
        self.assertAlmostEqual(self.source_details()["balance"]["remaining"], 97)
        for doc in docs:
            doc.reload()
            self.assertEqual((doc.snapshot_hash, doc.source_snapshot), snapshots[doc.name])

    def preview_without_ownership(self, row):
        """Read the shared calculator after release; publication itself is owned."""
        from lotus_farm.onedrive_supply import cut_slice

        return cut_slice(self.source_details(), row["slice_start"], row["slice_end"])

    def test_preview_native_snapshot_and_workspace_use_identical_source_slices(self):
        from lotus_farm.onedrive_workspace import forecast

        rows = self.slices()
        board = forecast(farm=self.farm, from_date=rows[0]["month"] + "-01")
        board_rows = {row["month"]: row for row in board["source_rows"] if row["source"] == self.source.name}
        for index, row in enumerate(rows):
            preview = self.preview(row["slice_start"], row["slice_end"])
            created = self.create_from_preview(
                preview, "PARITY-" + self.tag + "-" + str(index), row["slice_start"], row["slice_end"],
            )
            doc = frappe.get_doc("Harvest Forecast", created["documents"][0])
            evidence = json.loads(doc.source_snapshot)
            self.assertEqual(evidence["formula"], "lotus-onedrive/1")
            self.assertEqual(evidence["evidence"]["cut"], self.source.name)
            self.assertEqual(evidence["evidence"]["process_adoption"], self.adoption["name"])
            self.assertAlmostEqual(doc.source_bunch_qty, board_rows[row["month"]]["remaining_bunch_qty"])
            self.assertAlmostEqual(doc.gross_forecast_kg, board_rows[row["month"]]["gross_kg"], places=3)
            self.assertAlmostEqual(doc.packed_forecast_kg, board_rows[row["month"]]["processed_kg"], places=3)
            self.assertAlmostEqual(preview["drafts"][0]["packed_forecast_kg"], doc.packed_forecast_kg, places=3)
            self.assertAlmostEqual(evidence["slice"]["processed_kg"], doc.packed_forecast_kg, places=3)
            self.assertEqual(doc.source_claims[0].source_hash, row["source_hash"])
            self.assertEqual(getdate(doc.source_claims[0].slice_start), getdate(row["slice_start"]))
            self.assertEqual(getdate(doc.source_claims[0].slice_end), getdate(row["slice_end"]))

    def test_closing_requires_reason_and_released_reservations_then_is_idempotent(self):
        from lotus_farm.allocations import reserve, release as release_allocation
        from lotus_farm.onedrive_supply import close_forecast
        from lotus_farm.tests import test_brd as brd_fixtures

        preview = self.preview()
        created = self.create_from_preview(preview, "CLOSE-" + self.tag)
        doc = self.release(created["documents"][0])
        frozen = (doc.snapshot_hash, doc.source_snapshot)
        with self.assertRaisesRegex(frappe.ValidationError, "Ghi lý do"):
            close_forecast(doc.name, "   ")
        doc.reload()
        self.assertEqual(doc.supply_state, "Released")

        order = brd_fixtures.TestBRDOnSite.order(self, 1)
        allocation = reserve(doc.name, order.name, order.items[0].name, 1, "CLOSE-RESERVE-" + self.tag)
        with self.assertRaisesRegex(frappe.ValidationError, "Giải phóng"):
            close_forecast(doc.name, "Close reviewed residual supply")
        doc.reload()
        self.assertEqual(doc.supply_state, "Released")
        self.assertEqual((doc.snapshot_hash, doc.source_snapshot), frozen)

        release_allocation(doc.name, allocation["allocation"])
        doc.reload()
        before_modified = doc.modified
        result = close_forecast(doc.name, "Close reviewed residual supply", base_modified=before_modified)
        self.assertEqual(result, dict(forecast=doc.name, supply_state="Closed"))
        doc.reload()
        self.assertEqual(doc.supply_state, "Closed")
        self.assertEqual(doc.available_to_promise_kg, 0)
        self.assertEqual((doc.snapshot_hash, doc.source_snapshot), frozen)
        comment_filter = dict(reference_doctype="Harvest Forecast", reference_name=doc.name, comment_type="Comment")
        comment_count = frappe.db.count("Comment", comment_filter)
        self.assertGreater(comment_count, 0)
        self.assertEqual(close_forecast(doc.name, "Close reviewed residual supply", base_modified=before_modified), result)
        self.assertEqual(frappe.db.count("Comment", comment_filter), comment_count)
        with self.assertRaisesRegex(frappe.ValidationError, "truy xuất"):
            self.source.cancel()
        self.source.reload()
        self.assertEqual(self.source.docstatus, 1)

    def test_changed_cut_evidence_blocks_release_until_explicit_draft_recalculation(self):
        preview = self.preview()
        created = self.create_from_preview(preview, "DRAFT-STALE-" + self.tag)
        doc = frappe.get_doc("Harvest Forecast", created["documents"][0])
        previous_claim_hash = doc.source_claims[0].source_hash
        previous_snapshot = doc.source_snapshot
        self.assertAlmostEqual(doc.source_bunch_qty, 100)
        self.cancellation(1)
        doc.reload()
        self.assertEqual(doc.supply_state, "Draft")
        self.assertEqual(doc.source_claims[0].source_hash, previous_claim_hash)
        self.assertEqual(doc.source_snapshot, previous_snapshot)
        with self.assertRaisesRegex(frappe.ValidationError, "Nguồn buồng đã đổi"):
            self.release(doc.name)
        doc.reload()
        self.assertEqual(doc.supply_state, "Draft")
        doc.save()
        self.assertNotEqual(doc.source_claims[0].source_hash, previous_claim_hash)
        self.assertNotEqual(doc.source_snapshot, previous_snapshot)
        self.assertAlmostEqual(doc.source_bunch_qty, 99)
        released = self.release(doc.name)
        self.assertEqual(released.supply_state, "Released")
        self.assertAlmostEqual(released.source_bunch_qty, 99)
        self.assertEqual(len(json.loads(released.source_snapshot)["evidence"]["events"]), 1)


class TestOneDriveStockSnapshotGuardOnSite(unittest.TestCase):
    def test_stock_impacts_cannot_be_forged_changed_or_cleared(self):
        from lotus_farm.stock_bridge import validate_entry

        original = json.dumps({"HF-test-evidence": {"finished-item": 84}}, sort_keys=True)
        # Exercise the server guard with unsaved Stock Entry objects only. No
        # ledger transaction or database tampering is needed to test this seam.
        for before, new_value in (
            (None, original),
            (frappe._dict(lotus_forecast_impacts_json=original), "{}"),
            (frappe._dict(lotus_forecast_impacts_json=original), ""),
        ):
            with self.subTest(before=bool(before), new_value=new_value):
                doc = frappe.get_doc(dict(doctype="Stock Entry", lotus_forecast_impacts_json=new_value))
                with patch.object(doc, "get_doc_before_save", return_value=before):
                    with self.assertRaisesRegex(frappe.ValidationError, "written only by the stock bridge"):
                        validate_entry(doc)
        unchanged = frappe.get_doc(dict(doctype="Stock Entry", lotus_forecast_impacts_json=original))
        with patch.object(
            unchanged, "get_doc_before_save", return_value=frappe._dict(lotus_forecast_impacts_json=original),
        ):
            validate_entry(unchanged)
