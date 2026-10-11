"""Accepted output from one submitted task becomes one auditable piece payment."""
import frappe
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime
from lotus_farm.controls import check_farm, lock, require_role
from lotus_farm.rules import RuleError, quantity
from lotus_farm.piece_pay import accepted_output, piece_amount


class WorkPieceSettlement(Document):
    def validate(self):
        check_farm(self)
        lock("Farm", self.farm)
        result = frappe.get_doc("Daily Work Result", self.work_result)
        result.check_permission("read")
        lock("Daily Work Result", result.name)
        if result.docstatus != 1 or result.farm != self.farm:
            frappe.throw("Select a submitted Work Result from this Farm.")
        plan = frappe.get_doc("Daily Work Plan", result.work_plan)
        plan.check_permission("read")
        row = next((r for r in plan.lines if r.name == result.work_plan_line), None)
        if plan.docstatus != 1 or not row or not row.work_team:
            frappe.throw("A submitted Work Plan task assigned to a Work Team is required.")
        team = frappe.get_doc("Work Team", row.work_team)
        team.check_permission("read")
        if team.farm != self.farm:
            frappe.throw("Work Team must belong to this Farm.")
        work = frappe.get_doc("Work Type", row.work_type)
        work.check_permission("read")
        if (work.get("payment_basis") or "Daywork") != "Piece":
            frappe.throw("This task is not configured for piece payment.")
        rate = frappe.get_doc("Work Piece Rate", self.piece_rate)
        rate.check_permission("read")
        if (rate.docstatus != 1 or rate.farm != self.farm or
                rate.work_type != row.work_type or rate.uom != row.uom):
            frappe.throw("Select a submitted price for the same Farm, Work Type and UOM.")
        if not getdate(rate.valid_from) <= getdate(result.posting_date) <= getdate(rate.valid_to):
            frappe.throw("The piece price is not effective on the actual work date.")
        if rate.currency != "VND":
            frappe.throw("Only VND piece settlements are supported.")
        if frappe.db.exists(self.doctype, {
            "work_result": result.name, "docstatus": 1, "name": ["!=", self.name],
        }):
            frappe.throw("This work result already has an active piece settlement.")
        if not (self.payee_name or "").strip():
            frappe.throw("Record the foreman/contractor receiving this settlement.")
        if self.get("amended_from") and not (self.amendment_reason or "").strip():
            frappe.throw("Amended settlement requires a reason.")
        try:
            accepted = accepted_output(result.completed_qty, self.accepted_qty, self.acceptance_note)
            price = quantity(rate.unit_price, "Unit price", positive=True)
        except RuleError as exc:
            frappe.throw(str(exc))
        # Always derive identity/price from submitted source documents, not client input.
        self.company = frappe.db.get_value("Farm", self.farm, "company")
        self.posting_date = result.posting_date
        self.farm_plot = row.farm_plot
        self.work_team = team.name
        self.work_type = row.work_type
        self.uom = row.uom
        self.reported_qty = result.completed_qty
        self.accepted_qty = accepted
        self.actual_workdays = result.actual_workdays or 0  # KPI only; never part of pay.
        self.currency = "VND"
        self.unit_price = float(price)
        self.amount = piece_amount(accepted, price)

    def before_submit(self):
        require_role("Lotus Farm Manager")
        self.accepted_by = frappe.session.user
        self.accepted_at = now_datetime()

    def before_cancel(self):
        require_role("Lotus Farm Manager")
