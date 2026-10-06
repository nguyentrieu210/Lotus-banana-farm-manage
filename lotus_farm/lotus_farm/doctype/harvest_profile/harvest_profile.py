import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate


class HarvestProfile(Document):
    def validate(self):
        old = self.get_doc_before_save()
        if old and old.docstatus == 1:
            return
        self._validate_scope()
        self._validate_dates()
        self._validate_values()
        if cint(self.profile_version) < 1:
            frappe.throw("Profile Version must be positive.")

    def before_submit(self):
        if frappe.db.exists("Harvest Profile", {"profile_name": self.profile_name,
                                              "profile_version": self.profile_version,
                                              "name": ["!=", self.name]}):
            frappe.throw("This profile name/version already exists. Create a new version.")

    def _validate_scope(self):
        if self.farm_block:
            block = frappe.db.get_value(
                "Farm Block", self.farm_block, ["farm", "variety"], as_dict=True
            )
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
        if flt(self.avg_bunch_weight_kg) < 0 or cint(self.cut_bud_to_harvest_days) < 0:
            frappe.throw("Harvest Profile quantities cannot be negative.")

        for fieldname, label in (
            ("bunch_survival_rate_percent", "Bunch Survival Rate"),
            ("quality_pass_rate_percent", "Quality Pass Rate"),
            ("packout_rate_percent", "Packout Rate"),
            ("safety_buffer_percent", "Safety Buffer"),
        ):
            value = flt(self.get(fieldname))
            if not 0 <= value <= 100:
                frappe.throw(f"{label} must be between 0 and 100.")
