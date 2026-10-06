import frappe
from frappe.model.document import Document
from lotus_farm.controls import validate_item, validate_version
from lotus_farm.rules import quantity, RuleError


class QualityStandard(Document):
    def validate(self):
        validate_version(self, "standard_code", ("Lotus QC Manager",))
        validate_item(self.item)
        if not 0 <= float(self.max_defective_percent) <= 100:
            frappe.throw("Maximum defective percent must be between 0 and 100.")
        seen = set()
        for row in self.parameters or []:
            if row.parameter in seen or float(row.minimum) > float(row.maximum):
                frappe.throw("Parameters must be unique and minimum cannot exceed maximum.")
            try:
                quantity(row.minimum)
                quantity(row.maximum)
            except RuleError as exc:
                frappe.throw(str(exc))
            seen.add(row.parameter)

    def on_trash(self):
        if self.approval_state == "Approved":
            frappe.throw("Approved quality versions cannot be deleted.")
