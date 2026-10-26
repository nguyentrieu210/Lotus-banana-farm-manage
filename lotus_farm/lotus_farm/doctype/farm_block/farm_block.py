import frappe
from frappe.model.document import Document


class FarmBlock(Document):
    def validate(self):
        if self.area_ha is not None and self.area_ha <= 0:
            frappe.throw("Diện tích (ha) phải lớn hơn 0.")
        if self.planting_density is not None and self.planting_density < 0:
            frappe.throw("Mật độ trồng không được âm.")

        existing = frappe.db.get_value(
            "Farm Block",
            {"farm": self.farm, "block_code": self.block_code},
            "name",
        )
        if existing and existing != self.name:
            frappe.throw(f"Mã lô {self.block_code} đã tồn tại ở vườn {self.farm}.")
