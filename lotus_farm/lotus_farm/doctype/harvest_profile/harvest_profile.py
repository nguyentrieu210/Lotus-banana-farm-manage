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
                frappe.throw('Calibration evidence hash does not match the proposal.')

    def _validate_scope(self):
        if self.farm_block:
            block = frappe.db.get_value("Farm Block", self.farm_block, ["farm", "variety"], as_dict=True)
            if not block:
                frappe.throw("Farm Block does not exist.")
            if self.farm and block.farm != self.farm:
                frappe.throw("Harvest Profile Farm Block must belong to the selected Farm.")
            if not self.farm:
                self.farm = block.farm
            if not self.variety:
                self.variety = block.variety

    def _validate_dates(self):
        if self.valid_from and self.valid_to and getdate(self.valid_to) < getdate(self.valid_from):
            frappe.throw("Valid To cannot be before Valid From.")

    def _validate_values(self):
        try:
            quantity(self.avg_bunch_weight_kg, "Average bunch weight", positive=True)
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
                frappe.throw("Harvest Profile day offsets cannot be negative.")

        for fieldname, label in (
            ("bunch_survival_rate_percent", "Bunch Survival Rate"),
            ("quality_pass_rate_percent", "Quality Pass Rate"),
            ("packout_rate_percent", "Packout Rate"),
            ("safety_buffer_percent", "Safety Buffer"),
        ):
            value = flt(self.get(fieldname))
            if not 0 <= value <= 100:
                frappe.throw(f"{label} must be between 0 and 100.")

    def on_trash(self):
        if self.approval_state == "Approved":
            frappe.throw("Approved profiles cannot be deleted.")
