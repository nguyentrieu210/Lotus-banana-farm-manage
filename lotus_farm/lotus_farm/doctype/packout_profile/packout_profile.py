import frappe
from frappe.model.document import Document
from lotus_farm.controls import validate_item, validate_version, validate_calibration_evidence


class PackoutProfile(Document):
    def validate(self):
        validate_calibration_evidence(self)
        validate_version(self, "profile_name", ("Lotus Packing Supervisor",))
        validate_item(self.item)
        if self.calibration_json:
            import json
            from lotus_farm.rules import canonical_hash
            if canonical_hash(json.loads(self.calibration_json))!=self.calibration_hash:
                frappe.throw('Packout calibration evidence hash is invalid.')
        standard = frappe.get_doc("Quality Standard", self.quality_standard)
        standard.check_permission("read")
        if standard.approval_state != "Approved" or standard.item != self.item:
            frappe.throw("Select an approved quality standard matching the output Item.")
        if not 0 <= float(self.yield_percent) <= 100:
            frappe.throw("Packout yield must be between 0 and 100.")

    def on_trash(self):
        if self.approval_state == "Approved":
            frappe.throw("Approved packout versions cannot be deleted.")
