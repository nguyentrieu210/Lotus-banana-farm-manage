import frappe
from frappe.model.document import Document
from lotus_farm.supply import lock_document


class HarvestLot(Document):
    def validate(self):
        actual = frappe.get_doc("Harvest Actual", self.harvest_actual)
        actual.check_permission("read")
        if actual.docstatus != 1:
            frappe.throw("Harvest Lot requires a submitted Harvest Actual.")
        for field in ("farm", "farm_block", "crop_cycle", "sucker_selection_batch", "forecast"):
            self.set(field, actual.get(field))
        self.raw_weight_kg = actual.saleable_weight_kg

    def before_submit(self):
        lock_document("Harvest Actual", self.harvest_actual)
        self.validate()
        if frappe.db.sql("SELECT name FROM `tabHarvest Lot` WHERE harvest_actual=%s AND docstatus=1 AND name!=%s FOR UPDATE",
                         (self.harvest_actual, self.name)):
            frappe.throw("This Harvest Actual already has a submitted lot.")

    def before_cancel(self):
        if frappe.db.exists("Packout Run Source", {"harvest_lot": self.name, "docstatus": 1}):
            frappe.throw("Cancel downstream packout runs before cancelling this lot.")
