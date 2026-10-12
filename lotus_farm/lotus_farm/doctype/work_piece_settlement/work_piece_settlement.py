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
        if row.get("payment_basis") != "Piece" or not row.get("piece_rate"):
            frappe.throw("Việc chưa chốt giá khoán khi giao. Hủy và lập lại kế hoạch trước.")
        if row.price_approval_state not in ("Not Required", "Approved"):
            frappe.throw("Giá giao việc chưa được duyệt.")
        self.piece_rate = row.piece_rate
        self.acceptance_criteria = row.acceptance_criteria
        if frappe.db.exists(self.doctype, {
            "work_result": result.name, "docstatus": 1, "name": ["!=", self.name],
        }):
            frappe.throw("This work result already has an active piece settlement.")
        if team.get("foreman_name"):
            if (self.payee_name or "").strip() and self.payee_name.strip() != team.foreman_name.strip():
                frappe.throw("Payee must match the foreman configured on Work Team.")
            self.payee_name = team.foreman_name.strip()
        if not (self.payee_name or "").strip():
            frappe.throw("Record the foreman/contractor receiving this settlement.")
        if self.get("amended_from") and not (self.amendment_reason or "").strip():
            frappe.throw("Amended settlement requires a reason.")
        try:
            accepted = accepted_output(result.completed_qty, self.accepted_qty, self.acceptance_note)
            price = quantity(row.agreed_unit_price, "Unit price", positive=True)
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

