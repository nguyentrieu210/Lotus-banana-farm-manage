from lotus_farm.daily_operations import WorkResult
import frappe


class DailyWorkResult(WorkResult):
    def before_cancel(self):
        # A settled result must be reversed deliberately before the production
        # evidence changes, otherwise the payout would refer to stale output.
        if frappe.db.exists("Work Piece Settlement", {"work_result": self.name, "docstatus": 1}):
            frappe.throw("Cancel the piece settlement before cancelling this work result.")
        super().before_cancel()
