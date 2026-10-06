import frappe
from frappe.model.document import Document


class ForecastMaterialization(Document):
    def validate(self):
        if not self.flags.get('from_stock_hook'):
            frappe.throw('Materialization is managed only by ERPNext Stock Entry lifecycle.')

    def before_cancel(self):
        if not self.flags.get('from_stock_hook'):
            frappe.throw('Cancel the linked ERPNext Stock Entry to reverse materialization.')
