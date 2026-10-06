import frappe
from frappe.model.document import Document
from frappe.utils import add_days, cint, flt, getdate, get_datetime, now_datetime
from lotus_farm.controls import command, command_allowed, lock, require_role, validate_item
from lotus_farm.rules import canonical_hash

from lotus_farm.forecasting import ForecastInputError, calculate_availability


class HarvestForecast(Document):
    def validate(self):
        before = self.get_doc_before_save()
        if before and before.supply_state != "Draft":
            self._validate_frozen(before)
            self._hydrate_allocations()
            self._calculate_remaining()
            return
        self._validate_period()
        self._validate_scope()
        self._apply_profile_defaults()
        self._apply_settings_fallback()
        self._prepare_output_plan()
        self._pull_source_qty()
        self._hydrate_allocations()
        self._calculate()
        self.formula_version = "lotus-forecast/3"
        self.calculated_at = now_datetime()
        self.source_cutoff = self.calculated_at
        self.snapshot_hash = canonical_hash(self._snapshot())
        if self.supply_state == "Released":
            self._release()
        elif self.supply_state != "Draft":
            frappe.throw("Only Draft forecasts can be released.")

    def _snapshot(self):
        values = {
            name: self.get(name)
            for name in (
                "farm",
                "farm_block",
                "crop_cycle",
                "sucker_selection_batch",
                "item",
                "period_start_date",
                "period_end_date",
                "forecast_basis",
                "source_bunch_qty",
                "source_snapshot",
                "harvest_profile",
                "profile_version",
                "packout_profile",
                "packout_profile_version",
                "avg_bunch_weight_kg",
                "bunch_survival_rate_percent",
                "quality_pass_rate_percent",
                "packout_rate_percent",
                "safety_buffer_percent",
                "formula_version",
                "source_cutoff",
                "calculated_at",
                "supersedes",
                "revision_no",
                "gross_forecast_kg",
                "saleable_forecast_kg",
                "packed_forecast_kg",
                "safe_saleable_kg",
                "expected_harvest_bunch_qty",
                "revision_reason",
            )
        }
        for name in ("period_start_date", "period_end_date"):
            if values[name]:
                values[name] = str(getdate(values[name]))
        for name in ("calculated_at", "source_cutoff"):
            if values[name]:
                values[name] = str(get_datetime(values[name]))
        values["output_plan"] = [
            {
                key: row.get(key)
                for key in (
                    "idx",
                    "item",
                    "packout_profile",
                    "quality_standard",
                    "profile_version",
                    "yield_percent",
                    "expected_packed_kg",
                    "safe_commit_kg",
                )
            }
            for row in self.output_plan or []
        ]
        return values

    def _validate_frozen(self, before):
        if (
            self.snapshot_hash != before.snapshot_hash
            or self.released_by != before.released_by
            or get_datetime(self.released_at) != get_datetime(before.released_at)
        ):
            frappe.throw("Release audit fields cannot be edited.")
        if self._snapshot() != before._snapshot():
            frappe.throw("Released forecast snapshots cannot be edited. Create a new revision.")
        if self.supply_state != before.supply_state and not command_allowed(self, "supply"):
            frappe.throw("Use the Lotus supply command to close or supersede forecasts.")
        if self.materialized_qty_kg != before.materialized_qty_kg and not command_allowed(self, "supply"):
            frappe.throw("Materialized quantity can only change through stock reconciliation.")

        def output_materialized(doc):
            return [
                (row.item, flt(row.materialized_qty_kg, 3))
                for row in doc.output_plan or []
            ]

        if output_materialized(self) != output_materialized(before) and not command_allowed(self, "supply"):
            frappe.throw("Per-Item materialized quantity can only change through stock reconciliation.")

        def allocations(doc):
            return [
                {
                    k: r.get(k)
                    for k in (
                        "name",
                        "sales_order",
                        "sales_order_item",
                        "forecast_output",
                        "reserved_qty_kg",
                        "allocation_state",
                        "stock_reservation",
                        "allocated_by",
                        "allocated_at",
                    )
                }
                for r in doc.allocations or []
            ]

        if allocations(self) != allocations(before) and not command_allowed(self, "allocation"):
            frappe.throw("Use the allocation API to change reservations on a released forecast.")

    def _release(self):
        require_role("Lotus Farm Manager")
        if self.allocations:
            frappe.throw("Release an unallocated forecast first; reserve through the allocation command.")
        if not self.harvest_profile:
            frappe.throw("Release requires an approved Harvest Profile.")
        if self.output_plan:
            if self.item or self.packout_profile:
                frappe.throw("Use either Expected Finished Items or the legacy single Item/Profile fields, not both.")
        else:
            if not self.item or not self.packout_profile:
                frappe.throw("Release requires an Item and approved Packout Profile.")
            validate_item(self.item)
        if not self.source_bunch_qty:
            frappe.throw("A forecast with no source supply cannot be released.")
        # Serialize publication for this biological cycle across all Items and bases.
        lock("Crop Cycle", self.crop_cycle)
        others = frappe.get_all(
            "Harvest Forecast",
            filters={
                "crop_cycle": self.crop_cycle,
                "supply_state": "Released",
                "name": ["!=", self.name],
                "period_start_date": ["<=", self.period_end_date],
                "period_end_date": [">=", self.period_start_date],
            },
            fields=["name", "sucker_selection_batch"],
        )
        for other in others:
            if other.sucker_selection_batch == self.sucker_selection_batch and other.name != self.supersedes:
                frappe.throw("Overlapping released supply would count the same cohort twice.")
        if self.supersedes:
            previous = frappe.get_doc("Harvest Forecast", self.supersedes)
            previous.check_permission("write")
            lock("Harvest Forecast", previous.name)
            if previous.materialized_qty_kg or frappe.db.exists(
                "Harvest Actual", {"forecast": previous.name, "docstatus": 1}
            ):
                frappe.throw(
                    "Already harvested supply cannot be re-released as a full forecast. Reconcile residual supply first."
                )
            if previous.supply_state != "Released" or any(
                r.allocation_state in ("Reserved", "Materialized") for r in previous.allocations or []
            ):
                frappe.throw("Release or reconcile previous reservations before superseding the forecast.")
            scope_fields = (
                "farm",
                "crop_cycle",
                "sucker_selection_batch",
            )
            if any(self.get(f) != previous.get(f) for f in scope_fields) or any(
                getdate(self.get(f)) != getdate(previous.get(f))
                for f in ("period_start_date", "period_end_date")
            ):
                frappe.throw("Revision must retain the same supply scope and period.")
            if not self.revision_reason:
                frappe.throw("Revision reason is required.")
            self.revision_no = int(previous.revision_no or 1) + 1
            previous.supply_state = "Superseded"
            with command(previous, "supply"):
                previous.save()
        self.released_by = frappe.session.user
        self.released_at = now_datetime()
        self.snapshot_hash = canonical_hash(self._snapshot())
        self._calculate_remaining()

    @staticmethod
    def _availability_status(remaining, atp, shortage):
        if shortage:
            return "Overcommitted"
        if remaining and atp / remaining <= 0.1:
            return "Tight"
        return "Available"

    def _calculate_remaining(self):
        reserved = [
            row for row in self.allocations or [] if row.allocation_state == "Reserved"
        ]
        self.committed_qty_kg = flt(sum(flt(row.reserved_qty_kg) for row in reserved), 3)

        if self.output_plan:
            total_atp = 0
            total_shortage = 0
            total_materialized = 0
            statuses = []
            for output in self.output_plan:
                output.committed_qty_kg = flt(
                    sum(flt(row.reserved_qty_kg) for row in reserved if row.item == output.item),
                    3,
                )
                total_materialized += flt(output.materialized_qty_kg)
                remaining = max(
                    flt(output.safe_commit_kg) - flt(output.materialized_qty_kg),
                    0,
                )
                if self.supply_state in ("Closed", "Superseded"):
                    remaining = 0
                output.available_to_promise_kg = flt(
                    remaining - flt(output.committed_qty_kg),
                    3,
                )
                output.shortage_kg = flt(max(-output.available_to_promise_kg, 0), 3)
                output.availability_status = self._availability_status(
                    remaining,
                    output.available_to_promise_kg,
                    output.shortage_kg,
                )
                total_atp += output.available_to_promise_kg
                total_shortage += output.shortage_kg
                statuses.append(output.availability_status)

            self.materialized_qty_kg = flt(total_materialized, 3)
            self.available_to_promise_kg = flt(total_atp, 3)
            self.shortage_kg = flt(total_shortage, 3)
            self.availability_status = (
                "Overcommitted"
                if "Overcommitted" in statuses
                else ("Tight" if "Tight" in statuses else "Available")
            )
            return

        remaining = max(flt(self.safe_saleable_kg) - flt(self.materialized_qty_kg), 0)
        if self.supply_state in ("Closed", "Superseded"):
            remaining = 0
        self.available_to_promise_kg = flt(remaining - self.committed_qty_kg, 3)
        self.shortage_kg = flt(max(-self.available_to_promise_kg, 0), 3)
        self.availability_status = self._availability_status(
            remaining,
            self.available_to_promise_kg,
            self.shortage_kg,
        )

    def on_trash(self):
        if self.supply_state != "Draft":
            frappe.throw("Released supply cannot be deleted.")

    def _validate_period(self):
        if (
            self.period_start_date
            and self.period_end_date
            and getdate(self.period_end_date) < getdate(self.period_start_date)
        ):
            frappe.throw("Harvest Period End cannot be before Harvest Period Start.")

    def _validate_scope(self):
        block = frappe.db.get_value("Farm Block", self.farm_block, ["farm", "variety"], as_dict=True)
        if not block:
            frappe.throw("Farm Block does not exist.")
        if block.farm != self.farm:
            frappe.throw("Farm Block must belong to the selected Farm.")

        cycle = frappe.db.get_value(
            "Crop Cycle",
            self.crop_cycle,
            ["farm", "farm_block", "cycle_type"],
            as_dict=True,
        )
        if not cycle:
            frappe.throw("Crop Cycle does not exist.")
        if cycle.farm != self.farm or cycle.farm_block != self.farm_block:
            frappe.throw("Crop Cycle must belong to the selected Farm and Farm Block.")
        if cycle.cycle_type == "Ratoon" and not self.sucker_selection_batch:
            frappe.throw("Ratoon forecasts must select a Sucker Selection Batch.")

        if self.sucker_selection_batch:
            batch = frappe.db.get_value(
                "Sucker Selection Batch",
                self.sucker_selection_batch,
                ["farm", "farm_block", "crop_cycle"],
                as_dict=True,
            )
            if not batch:
                frappe.throw("Sucker Selection Batch does not exist.")
            if (
                batch.farm != self.farm
                or batch.farm_block != self.farm_block
                or batch.crop_cycle != self.crop_cycle
            ):
                frappe.throw("Sucker Selection Batch must belong to the selected Crop Cycle.")

    @staticmethod
    def _is_blank(value):
        return value is None or value == ""

    def _apply_profile_defaults(self):
        if not self.harvest_profile:
            return

        profile = frappe.db.get_value(
            "Harvest Profile",
            self.harvest_profile,
            [
                "active",
                "approval_state",
                "version",
                "cycle_type",
                "farm",
                "farm_block",
                "variety",
                "valid_from",
                "valid_to",
                "avg_bunch_weight_kg",
                "bunch_survival_rate_percent",
                "quality_pass_rate_percent",
                "packout_rate_percent",
                "safety_buffer_percent",
            ],
            as_dict=True,
        )
        if not profile:
            frappe.throw("Harvest Profile does not exist.")
        if profile.approval_state != "Approved":
            frappe.throw("Harvest Profile must be approved.")
        cycle = frappe.get_doc("Crop Cycle", self.crop_cycle)
        if profile.cycle_type and profile.cycle_type != cycle.cycle_type:
            frappe.throw("Harvest Profile does not apply to this cycle type.")
        self.profile_version = profile.version
        if not profile.active:
            frappe.throw("Harvest Profile is inactive.")
        if profile.farm and profile.farm != self.farm:
            frappe.throw("Harvest Profile does not apply to the selected Farm.")
        if profile.farm_block and profile.farm_block != self.farm_block:
            frappe.throw("Harvest Profile does not apply to the selected Farm Block.")

        block_variety = cycle.variety
        if profile.variety and block_variety and profile.variety != block_variety:
            frappe.throw("Harvest Profile does not apply to the Farm Block variety.")

        on_date = getdate(self.period_start_date)
        if profile.valid_from and on_date < getdate(profile.valid_from):
            frappe.throw("Harvest Profile is not valid yet for this forecast period.")
        if profile.valid_to and getdate(self.period_end_date) > getdate(profile.valid_to):
            frappe.throw("Harvest Profile has expired for this forecast period.")

        for fieldname in (
            "avg_bunch_weight_kg",
            "bunch_survival_rate_percent",
            "quality_pass_rate_percent",
            "packout_rate_percent",
            "safety_buffer_percent",
        ):
            self.set(fieldname, profile.get(fieldname))

    def _apply_settings_fallback(self):
        if self.packout_profile:
            profile = frappe.get_doc("Packout Profile", self.packout_profile)
            profile.check_permission("read")
            if profile.approval_state != "Approved" or profile.item != self.item:
                frappe.throw("Packout Profile must be approved for the forecast Item.")
            if profile.farm and profile.farm != self.farm:
                frappe.throw("Packout Profile belongs to another Farm.")
            cycle_variety = frappe.db.get_value("Crop Cycle", self.crop_cycle, "variety")
            if profile.variety and profile.variety != cycle_variety:
                frappe.throw("Packout Profile belongs to another variety.")
            if getdate(self.period_start_date) < getdate(profile.valid_from) or (
                profile.valid_to and getdate(self.period_end_date) > getdate(profile.valid_to)
            ):
                frappe.throw("Packout Profile is not valid for the full forecast period.")
            self.packout_rate_percent = profile.yield_percent
            self.packout_profile_version = profile.version
        settings = frappe.get_single("Lotus Farm Settings")

        if self._is_blank(self.avg_bunch_weight_kg):
            self.avg_bunch_weight_kg = settings.default_avg_bunch_weight_kg or 0

        if self._is_blank(self.bunch_survival_rate_percent):
            self.bunch_survival_rate_percent = 100

        if self._is_blank(self.quality_pass_rate_percent):
            defect_rate = flt(settings.default_defect_rate_percent or 0)
            self.quality_pass_rate_percent = 100 - defect_rate

        if self._is_blank(self.packout_rate_percent):
            self.packout_rate_percent = 100

        if self._is_blank(self.safety_buffer_percent):
            self.safety_buffer_percent = settings.safety_buffer_percent or 0

    def _prepare_output_plan(self):
        if not self.output_plan:
            return
        if self.item or self.packout_profile:
            frappe.throw("Expected Finished Items cannot be combined with legacy Item/Packout Profile fields.")

        cycle_variety = frappe.db.get_value("Crop Cycle", self.crop_cycle, "variety")
        seen_items = set()
        total_yield = 0
        for row in self.output_plan:
            if row.item in seen_items:
                frappe.throw("Each forecast output Item can appear only once.")
            seen_items.add(row.item)
            validate_item(row.item)
            profile = frappe.get_doc("Packout Profile", row.packout_profile)
            profile.check_permission("read")
            if profile.approval_state != "Approved" or profile.item != row.item:
                frappe.throw("Each forecast output needs an approved Packout Profile matching its Item.")
            if profile.farm and profile.farm != self.farm:
                frappe.throw("Forecast output Packout Profile belongs to another Farm.")
            if profile.variety and profile.variety != cycle_variety:
                frappe.throw("Forecast output Packout Profile belongs to another variety.")
            if getdate(self.period_start_date) < getdate(profile.valid_from) or (
                profile.valid_to and getdate(self.period_end_date) > getdate(profile.valid_to)
            ):
                frappe.throw("Forecast output Packout Profile is not valid for the full period.")
            if flt(profile.yield_percent) <= 0:
                frappe.throw("Forecast output yield must be positive.")
            row.profile_version = profile.version
            row.quality_standard = profile.quality_standard
            row.yield_percent = flt(profile.yield_percent, 6)
            if self._is_blank(row.materialized_qty_kg):
                row.materialized_qty_kg = 0
            total_yield += row.yield_percent

        if total_yield > 100.000001:
            frappe.throw("Combined forecast output yield cannot exceed 100%.")
        self.packout_rate_percent = flt(total_yield, 6)
        self.packout_profile_version = 0

    def _profile_days(self, fieldname, label):
        if not self.harvest_profile:
            frappe.throw(f"{label} forecast requires an approved Harvest Profile.")
        days = frappe.db.get_value("Harvest Profile", self.harvest_profile, fieldname)
        if days in (None, "") or cint(days) <= 0:
            frappe.throw(f"Harvest Profile must define a positive {label} day offset.")
        return cint(days)

    def _pull_source_qty(self):
        import json

        if self.forecast_basis == "Manual":
            self.source_snapshot = json.dumps(
                {"basis": "Manual", "reason": self.notes, "qty": self.source_bunch_qty},
                default=str,
                sort_keys=True,
            )
            if self.supply_state == "Released" and not self.notes:
                frappe.throw("Manual supply requires a source/reconciliation explanation.")
            return

        if self.forecast_basis == "Sucker Selection":
            if not self.sucker_selection_batch:
                frappe.throw("Sucker Selection forecast requires a Sucker Selection Batch.")
            days = self._profile_days("sucker_to_harvest_days", "Sucker-to-Harvest")
            batch = frappe.db.get_value(
                "Sucker Selection Batch",
                self.sucker_selection_batch,
                ["name", "selection_date", "selected_sucker_qty", "expected_productive_qty", "modified"],
                as_dict=True,
            )
            if not batch:
                frappe.throw("Sucker Selection Batch does not exist.")
            expected_date = getdate(add_days(batch.selection_date, days))
            if not getdate(self.period_start_date) <= expected_date <= getdate(self.period_end_date):
                frappe.throw("Sucker Selection cohort does not mature inside this forecast period.")
            self.source_bunch_qty = flt(batch.selected_sucker_qty)
            self.source_snapshot = json.dumps(
                {
                    "basis": self.forecast_basis,
                    "profile_days": days,
                    "rows": [
                        {
                            "name": batch.name,
                            "modified": batch.modified,
                            "selection_date": batch.selection_date,
                            "selected_sucker_qty": batch.selected_sucker_qty,
                            "expected_productive_qty": batch.expected_productive_qty,
                            "expected_harvest_date": expected_date,
                        }
                    ],
                },
                default=str,
                sort_keys=True,
            )
            return

        if self.forecast_basis == "Shooting Operations":
            days = self._profile_days("shooting_to_harvest_days", "Shooting-to-Harvest")
            rows = frappe.get_all(
                "Bunch Operation",
                filters={
                    "farm": self.farm,
                    "farm_block": self.farm_block,
                    "crop_cycle": self.crop_cycle,
                    "operation_type": "Shooting",
                    "docstatus": 1,
                    "operation_date": [
                        "between",
                        [
                            add_days(self.period_start_date, -days),
                            add_days(self.period_end_date, -days),
                        ],
                    ],
                    **(
                        {"sucker_selection_batch": self.sucker_selection_batch}
                        if self.sucker_selection_batch
                        else {}
                    ),
                },
                fields=["name", "modified", "operation_date", "net_bunch_qty"],
                order_by="name",
            )
            snapshot_rows = []
            for row in rows:
                expected_date = getdate(add_days(row.operation_date, days))
                if getdate(self.period_start_date) <= expected_date <= getdate(self.period_end_date):
                    snapshot_rows.append(
                        {
                            "name": row.name,
                            "modified": row.modified,
                            "operation_date": row.operation_date,
                            "net_bunch_qty": row.net_bunch_qty,
                            "expected_harvest_date": expected_date,
                        }
                    )
            self.source_bunch_qty = sum(flt(row["net_bunch_qty"]) for row in snapshot_rows)
            self.source_snapshot = json.dumps(
                {"basis": self.forecast_basis, "profile_days": days, "rows": snapshot_rows},
                default=str,
                sort_keys=True,
            )
            return

        if self.forecast_basis == "Cut Bud Operations":
            filters = {
                "farm": self.farm,
                "farm_block": self.farm_block,
                "crop_cycle": self.crop_cycle,
                "operation_type": "Cut Bud",
                "docstatus": 1,
                "expected_harvest_date": ["between", [self.period_start_date, self.period_end_date]],
            }
            if self.sucker_selection_batch:
                filters["sucker_selection_batch"] = self.sucker_selection_batch
            rows = frappe.get_all(
                "Bunch Operation",
                filters=filters,
                fields=["name", "modified", "net_bunch_qty", "expected_harvest_date"],
                order_by="name",
            )
            self.source_bunch_qty = sum(flt(row.net_bunch_qty) for row in rows)
            self.source_snapshot = json.dumps(
                {"basis": self.forecast_basis, "rows": rows},
                default=str,
                sort_keys=True,
            )
            return

        frappe.throw("Unsupported Forecast Basis.")

    def _hydrate_allocations(self):
        if self.allocations and self.supply_state == "Draft":
            frappe.throw(
                "Release the forecast before allocating. Map legacy rows through the allocation API."
            )

        output_by_item = {row.item: row for row in self.output_plan or []}
        allowed_items = set(output_by_item) if output_by_item else ({self.item} if self.item else set())
        seen_rows = set()
        for row in self.allocations or []:
            if flt(row.reserved_qty_kg) <= 0 or not row.sales_order_item:
                frappe.throw("Allocation requires a positive quantity and an exact Sales Order Item row.")
            key = (row.sales_order_item, row.allocation_state)
            if row.allocation_state == "Reserved" and key in seen_rows:
                frappe.throw("Duplicate Sales Order Item/state in this forecast.")
            seen_rows.add(key)
            so = frappe.get_doc("Sales Order", row.sales_order)
            # Preserve released/materialized history after SO cancellation.
            if row.allocation_state == "Reserved" and (
                so.docstatus != 1 or so.status in ("Closed", "Cancelled")
            ):
                frappe.throw("Active allocations require an open submitted Sales Order.")
            line = next((x for x in so.items if x.name == row.sales_order_item), None)
            if not line or line.item_code not in allowed_items:
                frappe.throw("Sales Order Item must match one of the forecast finished Items.")
            row.customer, row.item = so.customer, line.item_code
            row.forecast_output = output_by_item[line.item_code].name if output_by_item else None
            row.delivery_date = line.delivery_date or so.delivery_date
            if row.allocation_state == "Reserved" and getdate(row.delivery_date) < getdate(
                self.period_start_date
            ):
                frappe.throw("Delivery date is earlier than forecast availability.")

    def _calculate(self):
        committed_qty_kg = sum(
            flt(row.reserved_qty_kg)
            for row in (self.allocations or [])
            if row.allocation_state == "Reserved"
        )
        try:
            values = calculate_availability(
                source_bunch_qty=self.source_bunch_qty,
                avg_bunch_weight_kg=self.avg_bunch_weight_kg,
                bunch_survival_rate_percent=self.bunch_survival_rate_percent,
                quality_pass_rate_percent=self.quality_pass_rate_percent,
                packout_rate_percent=self.packout_rate_percent,
                safety_buffer_percent=self.safety_buffer_percent,
                committed_qty_kg=committed_qty_kg,
            )
        except ForecastInputError as exc:
            frappe.throw(str(exc))

        for fieldname, value in values.items():
            setattr(self, fieldname, value)

        if self.output_plan:
            for output in self.output_plan:
                output.expected_packed_kg = flt(
                    self.saleable_forecast_kg * flt(output.yield_percent) / 100,
                    3,
                )
                output.safe_commit_kg = flt(
                    output.expected_packed_kg * (1 - flt(self.safety_buffer_percent) / 100),
                    3,
                )
            self.packed_forecast_kg = flt(
                sum(flt(row.expected_packed_kg) for row in self.output_plan),
                3,
            )
            self.safe_saleable_kg = flt(
                sum(flt(row.safe_commit_kg) for row in self.output_plan),
                3,
            )

        self._calculate_remaining()
