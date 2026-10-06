import frappe
from frappe.model.document import Document
from frappe.utils import flt

from lotus_farm.domain import SupplyError, mass_balance, quantity
from lotus_farm.supply import lock_document


class PackoutRun(Document):
    def validate(self):
        if not self.sources or not self.outputs:
            frappe.throw("Packout needs source lots and measured outputs.")
        company = frappe.db.get_value("Farm", self.farm, "company")
        if company != self.company:
            frappe.throw("Packout Company must match Farm Company.")
        wh = frappe.db.get_value("Warehouse", self.target_warehouse, ["company", "is_group", "disabled"], as_dict=True)
        if not wh or wh.company != company or wh.is_group or wh.disabled:
            frappe.throw("Choose an enabled leaf Warehouse in the same Company.")
        seen = set()
        for row in self.sources:
            if row.harvest_lot in seen:
                frappe.throw("A source lot can appear only once in a run.")
            seen.add(row.harvest_lot)
            lot = frappe.get_doc("Harvest Lot", row.harvest_lot)
            lot.check_permission("read")
            if lot.docstatus != 1 or lot.farm != self.farm or lot.qc_status != "Released":
                frappe.throw("Source lot must be submitted, QC released and in the selected Farm.")
            try:
                quantity(row.source_kg, "Source kg", positive=True)
            except SupplyError as exc:
                frappe.throw(str(exc))
        for row in self.outputs:
            if row.output_type != "Waste":
                item = frappe.db.get_value("Item", row.item_code, ["disabled", "is_stock_item", "stock_uom"], as_dict=True)
                if not item or item.disabled or not item.is_stock_item or item.stock_uom != "Kg":
                    frappe.throw("Pilot stock outputs require an enabled stock Item with stock UOM Kg.")
            elif row.item_code:
                frappe.throw("Waste is recorded as kg only, without a stock Item.")
        # Site-owned tolerance, never supplied by the operator on a run.
        tolerance = frappe.db.get_single_value("Lotus Farm Settings", "mass_balance_tolerance_kg") or 0
        try:
            incoming = sum(quantity(r.source_kg, "Source kg", positive=True) for r in self.sources)
            outgoing = sum(quantity(r.net_kg, "Output kg") for r in self.outputs)
            self.input_kg = float(incoming)
            self.output_kg = float(outgoing)
            self.mass_variance_kg = mass_balance(incoming, [r.net_kg for r in self.outputs],
                                                self.recorded_loss_kg, tolerance)
        except SupplyError as exc:
            frappe.throw(str(exc))

    def before_submit(self):
        for name in sorted(r.harvest_lot for r in self.sources):
            lock_document("Harvest Lot", name)
        self.validate()
        for row in self.sources:
            lot = frappe.get_doc("Harvest Lot", row.harvest_lot)
            used = frappe.db.sql("""SELECT s.source_kg
                FROM `tabPackout Run Source` s JOIN `tabPackout Run` p ON p.name=s.parent
                WHERE s.harvest_lot=%s AND p.docstatus=1 AND p.name!=%s FOR UPDATE""", (lot.name, self.name))
            if sum(flt(r[0]) for r in used) + flt(row.source_kg) > flt(lot.raw_weight_kg):
                frappe.throw("Packout consumes more kg than are available in the source lot.")

    def before_cancel(self):
        for name in sorted(r.harvest_lot for r in self.sources):
            lock_document("Harvest Lot", name)
        lock_document("Packout Run", self.name)
        if self.stock_entry and frappe.db.get_value("Stock Entry", self.stock_entry, "docstatus") != 2:
            frappe.throw("Cancel or delete the linked Stock Entry before cancelling this run.")
