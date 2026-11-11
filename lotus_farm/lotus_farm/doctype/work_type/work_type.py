import frappe
from frappe.model.document import Document

from lotus_farm.labor_pricing import labor_settings
from lotus_farm.rules import RuleError, quantity


class WorkType(Document):
    def validate(self):
        try:
            quantity(self.productivity_per_workday or 0, 'Productivity')
        except RuleError as exc:
            frappe.throw(str(exc))
        if self.allow_piecework or self.allow_daywork:
            try:
                labor_settings(self.allow_daywork, self.allow_piecework,
                               self.productivity_per_workday, self.piecework_rate)
            except ValueError as exc:
                frappe.throw(str(exc))
        self.payment_basis = ('Both' if self.allow_piecework and self.allow_daywork else
            'Piece' if self.allow_piecework else 'Daywork' if self.allow_daywork else '')
