import frappe
from frappe.model.document import Document


class FarmBlock(Document):
    def validate(self):
        if self.area_ha is not None and self.area_ha < 0:
            frappe.throw("Area (ha) cannot be negative.")
