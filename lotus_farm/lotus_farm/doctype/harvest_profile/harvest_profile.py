import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate
from lotus_farm.controls import validate_version, validate_calibration_evidence
from lotus_farm.rules import quantity, RuleError


class HarvestProfile(Document):
    def validate(self):
        validate_calibration_evidence(self)
        validate_version(self, "profile_name", ("Lotus Farm Manager",))
        self._validate_scope()
        self._validate_dates()
        self._validate_values()
        if self.calibration_json:
            import json
            from lotus_farm.rules import canonical_hash
            result=json.loads(self.calibration_json);expected=result.pop('source_hash',None)
            if canonical_hash(result)!=expected or self.calibration_hash!=expected:
                frappe.throw('Mã băm bằng chứng hiệu chỉnh không khớp đề xuất.')

    def _validate_scope(self):
        if self.farm_block:
            block = frappe.db.get_value("Farm Block", self.farm_block, ["farm", "variety"], as_dict=True)
            if not block:
                frappe.throw("Lô không tồn tại.")
            if self.farm and block.farm != self.farm:
                frappe.throw("Lô của hệ số dự thu phải thuộc vườn đã chọn.")
            if not self.farm:
                self.farm = block.farm
            if not self.variety:
                self.variety = block.variety

    def _validate_dates(self):
        if self.valid_from and self.valid_to and getdate(self.valid_to) < getdate(self.valid_from):
            frappe.throw("Hiệu lực đến không được trước hiệu lực từ.")

    def _validate_values(self):
        try:
            quantity(self.avg_bunch_weight_kg, "Trọng lượng buồng bình quân", positive=True)
        except RuleError as exc:
            frappe.throw(str(exc))
        for fieldname in (
            "sucker_to_harvest_days",
            "planting_to_harvest_days",
            "ratoon_interval_days",
            "shooting_to_harvest_days",
            "cut_bud_to_harvest_days",
        ):
            value = self.get(fieldname)
            if value not in (None, "") and cint(value) < 0:
                frappe.throw("Số ngày lệch của hệ số dự thu không được âm.")

        for fieldname, label in (
            ("bunch_survival_rate_percent", "Tỷ lệ buồng sống"),
            ("quality_pass_rate_percent", "Tỷ lệ đạt chất lượng"),
            ("packout_rate_percent", "Tỷ lệ đóng gói"),
            ("safety_buffer_percent", "Hệ số an toàn"),
        ):
            value = flt(self.get(fieldname))
            if not 0 <= value <= 100:
                frappe.throw(f"{label} phải từ 0 đến 100.")

    def on_trash(self):
        if self.approval_state == "Approved":
            frappe.throw("Không được xóa hệ số đã duyệt.")
