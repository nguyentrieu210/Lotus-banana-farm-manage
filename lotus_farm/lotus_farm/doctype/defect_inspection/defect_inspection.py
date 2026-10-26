import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate
import json
from lotus_farm.inheritance import INHERITED_CYCLE_FIELDS, is_inherited_opening, validate_coverage_date


class DefectInspection(Document):
    def validate(self):
        self._validate_scope()
        self._validate_standard()
        inspected_qty = cint(self.inspected_qty)
        defect_qty = cint(self.defect_qty)

        if inspected_qty <= 0 or defect_qty < 0:
            frappe.throw("Số lượng kiểm tra không được âm.")
        if defect_qty > inspected_qty:
            frappe.throw("Số lượng lỗi không được vượt số lượng kiểm tra.")

        self.defect_rate_percent = flt(defect_qty / inspected_qty * 100, 2) if inspected_qty else 0

    def _validate_scope(self):
        block_farm = frappe.db.get_value("Farm Block", self.farm_block, "farm")
        if block_farm and block_farm != self.farm:
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
        validate_coverage_date(cycle, self.inspection_date)
        if cycle.cycle_type == "Ratoon" and not self.sucker_selection_batch and not is_inherited_opening(cycle):
            frappe.throw("Kiểm tra trên vụ chồi (lưu gốc) phải chọn đợt chọn chồi.")

        if self.sucker_selection_batch:
            batch_cycle = frappe.db.get_value(
                "Sucker Selection Batch", self.sucker_selection_batch, "crop_cycle"
            )
            if batch_cycle != self.crop_cycle:
                frappe.throw("Đợt chọn chồi phải thuộc vụ đã chọn.")

    def _validate_standard(self):
        if not self.quality_standard:
            if self.docstatus == 1:
                frappe.throw("Phiếu kiểm tra đã duyệt phải có tiêu chuẩn chất lượng.")
            return
        standard = frappe.get_doc("Quality Standard", self.quality_standard)
        standard.check_permission("read")
        if standard.approval_state != "Approved":
            frappe.throw("Tiêu chuẩn chất lượng phải được duyệt.")
        if getdate(self.inspection_date) < getdate(standard.valid_from) or (
            standard.valid_to and getdate(self.inspection_date) > getdate(standard.valid_to)
        ):
            frappe.throw("Tiêu chuẩn chưa/hết hiệu lực vào ngày kiểm tra.")
        self.standard_version = standard.version
        self.standard_snapshot = json.dumps(standard.as_dict(), default=str, sort_keys=True)
        seen = set()
        for row in self.defects or []:
            if (
                row.defect_reason in seen
                or cint(row.affected_units) < 0
                or cint(row.affected_units) > cint(self.defect_qty)
                or cint(row.occurrences) < cint(row.affected_units)
            ):
                frappe.throw(
                    "Dòng lỗi không được trùng; số đơn vị bị ảnh hưởng không vượt số đơn vị lỗi; số lần xuất hiện phải bao gồm đủ số đơn vị bị ảnh hưởng."
                )
            seen.add(row.defect_reason)
        measurements = {r.parameter: r for r in self.measurements or []}
        if len(measurements) != len(self.measurements or []):
            frappe.throw("Chỉ tiêu chất lượng bị trùng.")
        passed = cint(self.inspected_qty) > 0 and cint(self.defect_qty) / cint(
            self.inspected_qty
        ) * 100 <= float(standard.max_defective_percent)
        if set(measurements) != {r.parameter for r in standard.parameters or []}:
            frappe.throw("Nhập đúng và đủ các chỉ tiêu tiêu chuẩn yêu cầu.")
        for parameter in standard.parameters or []:
            observed = measurements[parameter.parameter]
            if observed.uom != parameter.uom:
                frappe.throw("Đơn vị đo chỉ tiêu chất lượng phải khớp tiêu chuẩn.")
            if not float(parameter.minimum) <= float(observed.value) <= float(parameter.maximum):
                passed = False
        self.quality_result = "Pass" if passed else "Fail"
