import frappe
from frappe.model.document import Document
from lotus_farm.controls import validate_item, validate_version


class PackoutProfile(Document):
    def validate(self):
        validate_version(self, "profile_name", ("Lotus Packing Supervisor",))
        validate_item(self.item)
        standard = frappe.get_doc("Quality Standard", self.quality_standard)
        standard.check_permission("read")
        if standard.approval_state != "Approved" or standard.item != self.item:
            frappe.throw("Select an approved quality standard matching the output Item.")
        if not 0 <= float(self.yield_percent) <= 100:
            frappe.throw("Packout yield must be between 0 and 100.")

    def on_trash(self):
        if self.approval_state == "Approved":
            frappe.throw("Approved packout versions cannot be deleted.")
