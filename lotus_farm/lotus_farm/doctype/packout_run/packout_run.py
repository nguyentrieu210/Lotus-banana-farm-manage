import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate, get_datetime, now_datetime
from lotus_farm.controls import command_allowed, lock, positive, require_role, validate_item, validate_warehouse
from lotus_farm.rules import reconcile_mass, RuleError


class PackoutRun(Document):
    def validate(self):
        if not self.sources or not self.outputs:
            frappe.throw("Đóng gói cần nguồn đầu vào và thành phẩm đầu ra.")
        if frappe.db.get_value("Farm", self.farm, "company") != self.company:
            frappe.throw("Vườn phải thuộc công ty đã chọn.")
        validate_warehouse(self.target_warehouse, self.company)
        before = self.get_doc_before_save()
        if before and before.qc_state == "Released":
            names = (
                "reject_kg",
                "other_loss_kg",
                "farm",
                "company",
                "quality_standard",
                "target_warehouse",
            )
            for name in names:
                if before.get(name) != self.get(name):
                    frappe.throw("Đợt đóng gói đã phát hành QC không được sửa. Hủy rồi lập bản sửa để điều chỉnh khối lượng.")
            source_fields = ("name", "idx", "harvest_lot", "input_kg")
            output_fields = ("name", "idx", "item", "net_kg", "cartons", "batch", "quality_standard", "standard_version", "output_type", "grade", "market", "pack_specification", "secondary_type")
            def rows(doc, table, fields):
                numeric = {"idx", "input_kg", "net_kg", "cartons", "standard_version"}
                return [tuple(flt(row.get(f), 3) if f in numeric else (row.get(f) or "") for f in fields) for row in doc.get(table)]
            old_values = dict(
                packing_date=getdate(before.packing_date),
                sources=rows(before, "sources", source_fields),
                outputs=rows(before, "outputs", output_fields),
                qc_released_by=before.qc_released_by,
                qc_released_at=get_datetime(before.qc_released_at),
                stock_entry=before.stock_entry or "",
            )
            new_values = dict(
                packing_date=getdate(self.packing_date),
                sources=rows(self, "sources", source_fields),
                outputs=rows(self, "outputs", output_fields),
                qc_released_by=self.qc_released_by,
                qc_released_at=get_datetime(self.qc_released_at),
                stock_entry=self.stock_entry or "",
            )
            changed = [key for key in old_values if old_values[key] != new_values[key]]
            if changed:
                frappe.throw("Đợt đóng gói đã phát hành QC không được sửa: " + ", ".join(changed))

            def valuation_rows(doc):
                return [
                    (
                        row.name,
                        flt(row.valuation_rate, 6),
                        row.valuation_set_by or "",
                        get_datetime(row.valuation_set_at) if row.valuation_set_at else None,
                    )
                    for row in doc.outputs
                ]

            if valuation_rows(self) != valuation_rows(before) and not command_allowed(self, "valuation"):
                frappe.throw("Dùng lệnh định giá đóng gói đã kiểm tra để đổi đơn giá thành phẩm.")
        if self.qc_state == "Released" and (not before or before.qc_state != "Released"):
            require_role("Lotus QC Manager")
            self.qc_released_by = frappe.session.user
            self.qc_released_at = now_datetime()
        if before and self.qc_state != before.qc_state and before.qc_state == "Released":
            frappe.throw("Không được đặt lại QC đã phát hành.")
        seen = set()
        for row in sorted(self.sources, key=lambda r: r.harvest_lot):
            if row.harvest_lot in seen:
                frappe.throw("Lô thu hoạch bị trùng trong đợt đóng gói.")
            seen.add(row.harvest_lot)
            lock("Harvest Lot", row.harvest_lot)
            lot = frappe.get_doc("Harvest Lot", row.harvest_lot)
            lot.check_permission("read")
            if lot.docstatus != 1 or lot.farm != self.farm or lot.company != self.company:
                frappe.throw("Lô đầu vào phải đã duyệt và thuộc vườn/công ty này.")
            if getdate(self.packing_date) < getdate(lot.received_date):
                frappe.throw("Ngày đóng gói không được trước ngày nhận lô.")
            source = frappe.qb.DocType("Packout Run Source")
            run = frappe.qb.DocType("Packout Run")
            used = (
                frappe.qb.from_(source)
                .join(run)
                .on(source.parent == run.name)
                .select(source.input_kg)
                .where(
                    (source.harvest_lot == row.harvest_lot) & (run.docstatus == 1) & (run.name != self.name)
                )
                .run()
            )
            if (
                sum(float(r[0]) for r in used) + positive(row.input_kg, "Input kg")
                > float(lot.released_raw_kg) + 0.0005
            ):
                frappe.throw("Đầu vào vượt số lượng còn lại của lô thu hoạch.")
        seen_items = set()
        for row in self.outputs:
            validate_item(row.item, batched=True)
            if row.item in seen_items:
                frappe.throw("Gộp các vật tư đầu ra bị trùng thành một dòng.")
            seen_items.add(row.item)
            standard = frappe.get_doc("Quality Standard", row.quality_standard or self.quality_standard)
            standard.check_permission("read")
            if standard.approval_state != "Approved" or standard.item != row.item:
                frappe.throw("Đầu ra cần tiêu chuẩn chất lượng đã duyệt khớp vật tư.")
            if getdate(self.packing_date) < getdate(standard.valid_from) or (
                standard.valid_to and getdate(self.packing_date) > getdate(standard.valid_to)
            ):
                frappe.throw("Tiêu chuẩn chất lượng của đầu ra không có hiệu lực vào ngày đóng gói.")
            row.quality_standard = standard.name
            row.standard_version = standard.version
            if int(row.cartons or 0) < 0:
                frappe.throw("Số thùng không được âm.")
        tolerance = frappe.db.get_single_value("Lotus Farm Settings", "mass_balance_tolerance_kg") or 0
        try:
            values = reconcile_mass(
                [r.input_kg for r in self.sources],
                [r.net_kg for r in self.outputs],
                self.reject_kg,
                self.other_loss_kg,
                tolerance,
            )
        except RuleError as exc:
            frappe.throw(str(exc))
        for name, value in values.items():
            self.set(name, value)

    def before_submit(self):
        from lotus_farm.daily_operations import packout_losses
        packout_losses(self)
        if self.qc_state != "Released" or not self.qc_released_by:
            frappe.throw("Quản lý QC phải phát hành đợt đóng gói trước khi duyệt.")

    def before_cancel(self):
        if self.stock_entry and frappe.db.get_value("Stock Entry", self.stock_entry, "docstatus") != 2:
            frappe.throw("Hủy/xóa phiếu kho ERPNext đã liên kết trước khi hủy đợt đóng gói.")

    def before_update_after_submit(self):
        self.validate()
