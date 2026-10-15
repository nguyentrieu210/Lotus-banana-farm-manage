from lotus_farm.daily_operations import WorkTypeMaster
from lotus_farm.labor_pricing import labor_settings


class WorkType(WorkTypeMaster):
    def validate(self):
        super().validate()
        if self.allow_piecework or self.allow_daywork:
            try:
                labor_settings(self.allow_daywork, self.allow_piecework,
                               self.productivity_per_workday, self.piecework_rate)
            except ValueError as exc:
                import frappe
                frappe.throw(str(exc))
        self.payment_basis = ('Both' if self.allow_piecework and self.allow_daywork else
            'Piece' if self.allow_piecework else 'Daywork' if self.allow_daywork else '')