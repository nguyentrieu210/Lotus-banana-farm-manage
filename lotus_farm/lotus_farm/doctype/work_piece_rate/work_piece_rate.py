"""Effective-dated, approved price per completed work unit."""
import frappe
from frappe.model.document import Document
from frappe.utils import getdate
from lotus_farm.controls import check_farm, lock, require_role
from lotus_farm.rules import RuleError, quantity


class WorkPieceRate(Document):
    def validate(self):
        check_farm(self)
        lock("Farm", self.farm)
        work = frappe.get_doc("Work Type", self.work_type)
        work.check_permission("read")
        if (work.get("payment_basis") or "Daywork") != "Piece":
            frappe.throw("Work Type must use Piece payment basis.")
        if self.uom != work.uom:
            frappe.throw("Piece price UOM must match the Work Type UOM.")
        if self.currency != "VND":
            frappe.throw("Piece prices currently support VND only; no currency conversion is performed.")
        try:
            quantity(self.unit_price, "Unit price", positive=True)
        except RuleError as exc:
            frappe.throw(str(exc))
        if getdate(self.valid_to) < getdate(self.valid_from):
            frappe.throw("Valid To must not precede Valid From.")
        if self.docstatus == 1:
            require_role("Lotus Farm Manager")
            for row in frappe.get_all(self.doctype, filters={
                "farm": self.farm, "work_type": self.work_type,
                "docstatus": 1, "name": ["!=", self.name],
            }, fields=["valid_from", "valid_to"]):
                if getdate(row.valid_from) <= getdate(self.valid_to) and getdate(self.valid_from) <= getdate(row.valid_to):
                    frappe.throw("Overlapping submitted piece prices for this Farm/Work Type.")

    def before_cancel(self):
        require_role("Lotus Farm Manager")
        if frappe.db.exists("Work Piece Settlement", {"piece_rate": self.name, "docstatus": 1}):
            frappe.throw("Cancel linked piece settlements before cancelling this price.")
