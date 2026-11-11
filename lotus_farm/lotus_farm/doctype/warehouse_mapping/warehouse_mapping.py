import frappe
from frappe.model.document import Document

from lotus_farm.controls import check_farm, validate_warehouse


class WarehouseMapping(Document):
    def validate(self):
        check_farm(self)
        validate_warehouse(self.warehouse, frappe.db.get_value("Farm", self.farm, "company"))
