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

        # The sổ lô, phiếu giao, ca xưởng and the books keep the lô's farm, and paper forms, the Excel round-trip and
        # the map find a lô by its code: once anything names the lô, its farm and code stay.
        moved = self.get_doc_before_save() and (self.has_value_changed("farm") or self.has_value_changed("block_code"))
        if moved and self.referenced():
            frappe.throw("Lô đã có dữ liệu thì không được đổi vườn hoặc mã lô.")

    def referenced(self):
        """Whether any record links to this lô, through any Link to Farm Block: a field of a DocType or a custom field. The
        custom ones include the lotus_farm_block accounting dimension on GL Entry and on stock, invoice and journal rows."""
        links = {(f.parent, f.fieldname) for f in frappe.get_all(
            "DocField", filters={"parenttype": "DocType", "fieldtype": "Link", "options": "Farm Block"}, fields=["parent", "fieldname"])}
        links |= {(f.dt, f.fieldname) for f in frappe.get_all(
            "Custom Field", filters={"fieldtype": "Link", "options": "Farm Block"}, fields=["dt", "fieldname"])}
        return any(frappe.db.exists(doctype, {fieldname: self.name}) for doctype, fieldname in sorted(links))
