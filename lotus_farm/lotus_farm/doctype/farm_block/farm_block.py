import frappe
from frappe.model.document import Document


class FarmBlock(Document):
    def validate(self):
        if self.area_ha is not None and self.area_ha <= 0:
            frappe.throw("Area (ha) must be positive.")
        if self.planting_density is not None and self.planting_density < 0:
            frappe.throw("Planting Density cannot be negative.")

        existing = frappe.db.get_value(
            "Farm Block",
            {"farm": self.farm, "block_code": self.block_code},
            "name",
        )
        if existing and existing != self.name:
            frappe.throw(f"Block Code {self.block_code} already exists in Farm {self.farm}.")
