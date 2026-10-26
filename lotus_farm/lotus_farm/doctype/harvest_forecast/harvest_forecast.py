import frappe
from frappe.model.document import Document
from frappe.utils import add_days, cint, flt, getdate, get_datetime, now_datetime
from lotus_farm.controls import command, command_allowed, lock, require_role, validate_item
from lotus_farm.rules import canonical_hash

from lotus_farm.forecasting import ForecastInputError, calculate_availability


class HarvestForecast(Document):
    def validate(self):
        before = self.get_doc_before_save()
        if self.is_new() and not self.planning_granularity:self.planning_granularity="Week"
        if before and before.supply_state != "Draft":
            self._validate_frozen(before)
            self._hydrate_allocations()
            self._calculate_remaining()
            return
        self._validate_period()
        self._validate_scope()
        onedrive = bool(self.get('process_adoption') or self.get('source_claims'))
        if onedrive:
            from lotus_farm.onedrive_supply import hydrate_draft
            hydrate_draft(self)
            self._prepare_output_plan()
        else:
            self._apply_profile_defaults()
            self._apply_settings_fallback()
            self._prepare_output_plan()
            self._pull_source_qty()
            from lotus_farm.daily_operations import cancellation_adjustment
            cancellation_adjustment(self)
        self._hydrate_allocations()
        self._calculate()
        self.formula_version = "lotus-onedrive/1" if onedrive else "lotus-forecast/5"
        self.calculated_at = now_datetime()
        self.source_cutoff = self.calculated_at
        self.snapshot_hash = canonical_hash(self._snapshot())
        if self.supply_state == "Released":
            self._release()
        elif self.supply_state != "Draft":
            frappe.throw("Chỉ phát hành được dự thu ở trạng thái nháp.")

    def _snapshot(self):
        values = {
            name: self.get(name)
            for name in (
                "farm",
                "farm_block",
                "farm_plot",
                "crop_cycle",
                "sucker_selection_batch",
                "item",
                "period_start_date",
                "period_end_date",
                "forecast_basis",
                "source_bunch_qty",
                "cancellation_bunch_qty",
                "net_source_bunch_qty",
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
                "process_adoption",
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
                    "source_share_percent",
                )
            }
            for row in self.output_plan or []
        ]
        from lotus_farm.onedrive_supply import CLAIM_FIELDS
        values['source_claims'] = [{key: (str(row.get(key)) if row.get(key) is not None and key in ('window_start','window_end','slice_start','slice_end') else row.get(key))
                                   for key in CLAIM_FIELDS} for row in self.get('source_claims') or []]
        return values

    def _validate_frozen(self, before):
        if (self.planning_granularity or "Custom") != (before.planning_granularity or "Custom"):
            frappe.throw("Mức chi tiết kế hoạch của dự thu đã phát hành không được sửa.")
        if (
            self.snapshot_hash != before.snapshot_hash
            or self.released_by != before.released_by
            or get_datetime(self.released_at) != get_datetime(before.released_at)
        ):
            frappe.throw("Không được sửa các trường kiểm toán phát hành.")
        if self._snapshot() != before._snapshot():
            frappe.throw("Không được sửa ảnh chụp dự thu đã phát hành. Hãy tạo bản điều chỉnh mới.")
        if self.supply_state != before.supply_state and not command_allowed(self, "supply"):
            frappe.throw("Dùng lệnh cung ứng Lotus để đóng hoặc thay thế dự thu.")
        if self.materialized_qty_kg != before.materialized_qty_kg and not command_allowed(self, "supply"):
            frappe.throw("Số lượng đã hiện thực chỉ thay đổi qua đối soát kho.")

        def output_materialized(doc):
            return [
                (row.item, flt(row.materialized_qty_kg, 3))
                for row in doc.output_plan or []
            ]

        if output_materialized(self) != output_materialized(before) and not command_allowed(self, "supply"):
            frappe.throw("Số lượng đã hiện thực theo vật tư chỉ thay đổi qua đối soát kho.")

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
                        "materialized_from",
                        "restored_to",
                        "allocated_by",
                        "allocated_at",
                    )
                }
                for r in doc.allocations or []
            ]

        if allocations(self) != allocations(before) and not command_allowed(self, "allocation"):
            frappe.throw("Dùng chức năng phân bổ để đổi hàng giữ trên dự thu đã phát hành.")

    def _release(self):
        require_role("Lotus Farm Manager")
        from lotus_farm.onedrive_supply import adopted, assert_source_ownership, blank_filter
        onedrive = bool(self.get('process_adoption'))
        if adopted(self.farm) and not onedrive:
            frappe.throw('Vườn áp dụng OneDrive chỉ phát hành nguồn cung từ đợt cắt bắp có truy xuất. Dùng Xem trước / Tạo nháp trong Dự thu OneDrive.')
        if self.allocations:
            frappe.throw("Phát hành dự thu chưa phân bổ trước; giữ hàng bằng lệnh phân bổ.")
        if not self.harvest_profile and not onedrive:
            frappe.throw("Phát hành cần hệ số dự thu đã duyệt.")
        if self.output_plan:
            if self.item or self.packout_profile:
                frappe.throw("Chỉ dùng hoặc danh sách thành phẩm dự kiến, hoặc các trường vật tư/hệ số kiểu cũ, không dùng cả hai.")
        else:
            if not self.item or not self.packout_profile:
                frappe.throw("Phát hành cần vật tư và hệ số đóng gói đã duyệt.")
            validate_item(self.item)
        if not self.source_bunch_qty:
            frappe.throw("Không phát hành được dự thu không có nguồn cung.")
        # Serialize publication for this biological cycle across all Items and bases.
        lock("Crop Cycle", self.crop_cycle)
        for actual in ([] if onedrive else frappe.get_all('Harvest Actual', filters={'crop_cycle': self.crop_cycle, 'sucker_selection_batch': blank_filter(self.sucker_selection_batch), 'docstatus': 1, 'harvest_date': ['between', [self.period_start_date, self.period_end_date]]}, fields=['name', 'forecast'])):
            if not actual.forecast:
                frappe.throw('Có thu hoạch thực tế chưa liên kết trong kỳ này. Đối soát nguồn cung đã thu hoạch trước khi phát hành dự thu mới.')
        table = frappe.qb.DocType('Harvest Forecast')
        others = (frappe.qb.from_(table).select(table.name, table.sucker_selection_batch, table.process_adoption)
                  .where((table.crop_cycle == self.crop_cycle) & (table.supply_state == 'Released') & (table.name != self.name)
                         & (table.period_start_date <= self.period_end_date) & (table.period_end_date >= self.period_start_date))
                  .for_update().run(as_dict=True))
        for other in others:
            if (other.sucker_selection_batch or '') == (self.sucker_selection_batch or '') and other.name != self.supersedes and not (onedrive and other.process_adoption):
                frappe.throw("Nguồn cung đã phát hành bị chồng chéo sẽ tính cùng một đợt cây hai lần.")
        if onedrive:
            assert_source_ownership(self)
        if self.supersedes:
            previous = frappe.get_doc("Harvest Forecast", self.supersedes, for_update=True)
            previous.check_permission("write")
            lock("Harvest Forecast", previous.name)
            if previous.materialized_qty_kg or (not onedrive and frappe.db.exists(
                "Harvest Actual", {"forecast": previous.name, "docstatus": 1}
            )):
                frappe.throw(
                    "Nguồn cung đã thu hoạch không được phát hành lại như một dự thu đầy đủ. Đối soát phần còn lại trước."
                )
            if previous.supply_state != "Released" or any(
                r.allocation_state in ("Reserved", "Materialized") for r in previous.allocations or []
            ):
                frappe.throw("Giải phóng hoặc đối soát các hàng giữ trước đó trước khi thay thế dự thu.")
            scope_fields = (
                "farm",
                "crop_cycle",
                "sucker_selection_batch",
            )
            if any((self.get(f) or '') != (previous.get(f) or '') for f in scope_fields) or (not onedrive and any(
                getdate(self.get(f)) != getdate(previous.get(f))
                for f in ("period_start_date", "period_end_date")
            )):
                frappe.throw("Bản điều chỉnh phải giữ nguyên phạm vi nguồn cung và kỳ.")
            if onedrive and (not previous.process_adoption or {r.source_cut_operation for r in self.source_claims} != {r.source_cut_operation for r in previous.source_claims}):
                frappe.throw('Bản thay thế phải giữ cùng nguồn cắt bắp; kỳ mới chỉ nhận phần buồng còn lại.')
            if not self.revision_reason:
                frappe.throw("Phải nhập lý do điều chỉnh.")
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
        from lotus_farm.daily_operations import live_loss_fraction
        inactive = self.supply_state in ('Closed', 'Superseded')
        loss_fraction = 0 if inactive else live_loss_fraction(self)
        harvested = sum(flt(v) for v in frappe.get_all('Harvest Actual', filters={'forecast':self.name,'docstatus':1}, pluck='harvested_bunch_qty')) if not self.is_new() else 0
        harvest_fraction = min(harvested / flt(self.expected_harvest_bunch_qty), 1) if self.expected_harvest_bunch_qty else 0
        if self.get('source_claims') and not inactive:
            from lotus_farm.onedrive_supply import remaining_fraction
            loss_fraction = 0
            harvest_fraction = 1-remaining_fraction(self)
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
                    min(flt(output.safe_commit_kg) * max(1-loss_fraction-harvest_fraction,0),
                        flt(output.safe_commit_kg) * (1-loss_fraction) - flt(output.materialized_qty_kg)),
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

        remaining = max(min(flt(self.safe_saleable_kg) * max(1-loss_fraction-harvest_fraction,0), flt(self.safe_saleable_kg) * (1-loss_fraction) - flt(self.materialized_qty_kg)), 0)
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
            frappe.throw("Không được xóa nguồn cung đã phát hành.")

    def _validate_period(self):
        if (
            self.period_start_date
            and self.period_end_date
            and getdate(self.period_end_date) < getdate(self.period_start_date)
        ):
            frappe.throw("Ngày kết thúc thu hoạch không được trước ngày bắt đầu thu hoạch.")

    def _validate_scope(self):
        from lotus_farm.inheritance import INHERITED_CYCLE_FIELDS, is_inherited_opening
        block = frappe.db.get_value("Farm Block", self.farm_block, ["farm", "variety"], as_dict=True)
        if not block:
            frappe.throw("Lô không tồn tại.")
        if block.farm != self.farm:
            frappe.throw("Lô phải thuộc vườn đã chọn.")

        cycle = frappe.db.get_value(
            "Crop Cycle",
            self.crop_cycle,
            ["farm", "farm_block", *INHERITED_CYCLE_FIELDS],
            as_dict=True,
        )
        if not cycle:
            frappe.throw("Vụ không tồn tại.")
        if cycle.farm != self.farm or cycle.farm_block != self.farm_block:
            frappe.throw("Vụ phải thuộc vườn và lô đã chọn.")
        inherited_physical = is_inherited_opening(cycle) and self.forecast_basis in ('Cut Bud Operations','Shooting Operations')
        if cycle.cycle_type == "Ratoon" and not self.sucker_selection_batch and not inherited_physical:
            frappe.throw("Dự thu vụ chồi (lưu gốc) phải chọn đợt chọn chồi.")

        if self.sucker_selection_batch:
            batch = frappe.db.get_value(
                "Sucker Selection Batch",
                self.sucker_selection_batch,
                ["farm", "farm_block", "crop_cycle"],
                as_dict=True,
            )
            if not batch:
                frappe.throw("Đợt chọn chồi không tồn tại.")
            if (
                batch.farm != self.farm
                or batch.farm_block != self.farm_block
                or batch.crop_cycle != self.crop_cycle
            ):
                frappe.throw("Đợt chọn chồi phải thuộc vụ đã chọn.")

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
            frappe.throw("Hệ số dự thu không tồn tại.")
        if profile.approval_state != "Approved":
            frappe.throw("Hệ số dự thu phải được duyệt.")
        cycle = frappe.get_doc("Crop Cycle", self.crop_cycle)
        if profile.cycle_type and profile.cycle_type != cycle.cycle_type:
            frappe.throw("Hệ số dự thu không áp dụng cho loại vụ này.")
        self.profile_version = profile.version
        if not profile.active:
            frappe.throw("Hệ số dự thu đang ngừng dùng.")
        if profile.farm and profile.farm != self.farm:
            frappe.throw("Hệ số dự thu không áp dụng cho vườn đã chọn.")
        if profile.farm_block and profile.farm_block != self.farm_block:
            frappe.throw("Hệ số dự thu không áp dụng cho lô đã chọn.")

        block_variety = cycle.variety
        if profile.variety and block_variety and profile.variety != block_variety:
            frappe.throw("Hệ số dự thu không áp dụng cho giống của lô.")

        on_date = getdate(self.period_start_date)
        if profile.valid_from and on_date < getdate(profile.valid_from):
            frappe.throw("Hệ số dự thu chưa có hiệu lực trong kỳ dự thu này.")
        if profile.valid_to and getdate(self.period_end_date) > getdate(profile.valid_to):
            frappe.throw("Hệ số dự thu đã hết hiệu lực trong kỳ dự thu này.")

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
                frappe.throw("Hệ số đóng gói phải được duyệt cho vật tư của dự thu.")
            if profile.farm and profile.farm != self.farm:
                frappe.throw("Hệ số đóng gói thuộc vườn khác.")
            cycle_variety = frappe.db.get_value("Crop Cycle", self.crop_cycle, "variety")
            if profile.variety and profile.variety != cycle_variety:
                frappe.throw("Hệ số đóng gói thuộc giống khác.")
            if getdate(self.period_start_date) < getdate(profile.valid_from) or (
                profile.valid_to and getdate(self.period_end_date) > getdate(profile.valid_to)
            ):
                frappe.throw("Hệ số đóng gói không có hiệu lực trong toàn bộ kỳ dự thu.")
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
            frappe.throw("Không dùng chung danh sách thành phẩm dự kiến với các trường vật tư/hệ số đóng gói kiểu cũ.")

        cycle_variety = frappe.db.get_value("Crop Cycle", self.crop_cycle, "variety")
        seen_items = set()
        total_yield = 0
        total_source_share = 0
        for row in self.output_plan:
            if row.item in seen_items:
                frappe.throw("Mỗi vật tư đầu ra của dự thu chỉ được xuất hiện một lần.")
            seen_items.add(row.item)
            validate_item(row.item)
            profile = frappe.get_doc("Packout Profile", row.packout_profile)
            profile.check_permission("read")
            if profile.approval_state != "Approved" or profile.item != row.item:
                frappe.throw("Mỗi đầu ra của dự thu cần hệ số đóng gói đã duyệt khớp vật tư.")
            if profile.farm and profile.farm != self.farm:
                frappe.throw("Hệ số đóng gói của đầu ra thuộc vườn khác.")
            if profile.variety and profile.variety != cycle_variety:
                frappe.throw("Hệ số đóng gói của đầu ra thuộc giống khác.")
            if getdate(self.period_start_date) < getdate(profile.valid_from) or (
                profile.valid_to and getdate(self.period_end_date) > getdate(profile.valid_to)
            ):
                frappe.throw("Hệ số đóng gói của đầu ra không có hiệu lực trong toàn bộ kỳ.")
            if flt(profile.yield_percent) <= 0:
                frappe.throw("Tỷ lệ thành phẩm của đầu ra phải lớn hơn 0.")
            row.profile_version = profile.version
            row.quality_standard = profile.quality_standard
            row.yield_percent = flt(profile.yield_percent, 6)
            if self.get('process_adoption'):
                if not 0 < flt(row.source_share_percent) <= 100:
                    frappe.throw('Mỗi Item cần tỷ phần kg sơ chế OneDrive lớn hơn 0 và không vượt 100%.')
                total_source_share += flt(row.source_share_percent)
            if self._is_blank(row.materialized_qty_kg):
                row.materialized_qty_kg = 0
            total_yield += row.yield_percent

        if self.get('process_adoption') and total_source_share > 100.000001:
            frappe.throw('Tổng tỷ phần thành phẩm không vượt 100% kg sơ chế OneDrive.')
        if not self.get('process_adoption') and total_yield > 100.000001:
            frappe.throw("Tổng tỷ lệ thành phẩm của dự thu không được vượt 100%.")
        self.packout_rate_percent = flt(total_yield, 6)
        self.packout_profile_version = 0

    def _profile_days(self, fieldname, label):
        if not self.harvest_profile:
            frappe.throw(f"Dự thu {label} cần hệ số dự thu đã duyệt.")
        days = frappe.db.get_value("Harvest Profile", self.harvest_profile, fieldname)
        if days in (None, "") or cint(days) <= 0:
            frappe.throw(f"Hệ số dự thu phải khai báo số ngày lệch {label} lớn hơn 0.")
        return cint(days)

    def _pull_source_qty(self):
        import json
        from lotus_farm.onedrive_supply import blank_filter

        if self.forecast_basis == "Manual":
            self.source_snapshot = json.dumps(
                {"basis": "Manual", "reason": self.notes, "qty": self.source_bunch_qty},
                default=str,
                sort_keys=True,
            )
            if self.supply_state == "Released" and not self.notes:
                frappe.throw("Nguồn cung nhập tay phải có giải thích nguồn/đối soát.")
            return

        if self.forecast_basis == "Sucker Selection":
            if not self.sucker_selection_batch:
                frappe.throw("Dự thu theo chọn chồi cần đợt chọn chồi.")
            days = self._profile_days("sucker_to_harvest_days", "từ chọn chồi đến thu hoạch")
            batch = frappe.db.get_value(
                "Sucker Selection Batch",
                self.sucker_selection_batch,
                ["name", "selection_date", "selected_sucker_qty", "expected_productive_qty", "modified"],
                as_dict=True,
            )
            if not batch:
                frappe.throw("Đợt chọn chồi không tồn tại.")
            expected_date = getdate(add_days(batch.selection_date, days))
            if not getdate(self.period_start_date) <= expected_date <= getdate(self.period_end_date):
                frappe.throw("Đợt chọn chồi không cho trái trong kỳ dự thu này.")
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
            days = self._profile_days("shooting_to_harvest_days", "từ trổ đến thu hoạch")
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
                    "sucker_selection_batch": blank_filter(self.sucker_selection_batch),
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
            filters["sucker_selection_batch"] = blank_filter(self.sucker_selection_batch)
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

        frappe.throw("Cơ sở dự thu không được hỗ trợ.")

    def _hydrate_allocations(self):
        if self.allocations and self.supply_state == "Draft":
            frappe.throw(
                "Phát hành dự thu trước khi phân bổ. Gắn các dòng cũ qua chức năng phân bổ."
            )

        output_by_item = {row.item: row for row in self.output_plan or []}
        allowed_items = set(output_by_item) if output_by_item else ({self.item} if self.item else set())
        seen_rows = set()
        for row in self.allocations or []:
            if flt(row.reserved_qty_kg) <= 0 or not row.sales_order_item:
                frappe.throw("Phân bổ cần số lượng lớn hơn 0 và đúng một dòng đơn bán hàng.")
            key = (row.sales_order_item, row.allocation_state)
            if row.allocation_state == "Reserved" and key in seen_rows:
                frappe.throw("Dòng đơn bán hàng/trạng thái bị trùng trong dự thu này.")
            seen_rows.add(key)
            so = frappe.get_doc("Sales Order", row.sales_order)
            # Preserve released/materialized history after SO cancellation.
            if row.allocation_state == "Reserved" and (
                so.docstatus != 1 or so.status in ("Closed", "Cancelled")
            ):
                frappe.throw("Phân bổ đang hiệu lực cần đơn bán hàng đang mở và đã duyệt.")
            line = next((x for x in so.items if x.name == row.sales_order_item), None)
            if not line or line.item_code not in allowed_items:
                frappe.throw("Dòng đơn bán hàng phải khớp một trong các thành phẩm của dự thu.")
            row.customer, row.item = so.customer, line.item_code
            row.forecast_output = output_by_item[line.item_code].name if output_by_item else None
            row.delivery_date = line.delivery_date or so.delivery_date
            if row.allocation_state == "Reserved" and getdate(row.delivery_date) < getdate(
                self.period_start_date
            ):
                frappe.throw("Ngày giao sớm hơn ngày dự thu có hàng.")

    def _calculate(self):
        if self.get('process_adoption'):
            from lotus_farm.onedrive_supply import calculate
            calculate(self)
            self._calculate_remaining()
            return
        committed_qty_kg = sum(
            flt(row.reserved_qty_kg)
            for row in (self.allocations or [])
            if row.allocation_state == "Reserved"
        )
        try:
            values = calculate_availability(
                source_bunch_qty=self.net_source_bunch_qty,
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
