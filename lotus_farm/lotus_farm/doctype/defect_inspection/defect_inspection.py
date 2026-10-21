import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate
import json
from lotus_farm.inheritance import INHERITED_CYCLE_FIELDS, is_inherited_opening, validate_coverage_date


class DefectInspection(Document):
    def validate(self):
        self._validate_scope()
        self._validate_standard()
        inspected_qty = cint(self.inspected_qty)
        defect_qty = cint(self.defect_qty)

        if inspected_qty <= 0 or defect_qty < 0:
            frappe.throw("Inspection quantities cannot be negative.")
        if defect_qty > inspected_qty:
            frappe.throw("Defect Qty cannot exceed Inspected Qty.")

        self.defect_rate_percent = flt(defect_qty / inspected_qty * 100, 2) if inspected_qty else 0

    def _validate_scope(self):
        block_farm = frappe.db.get_value("Farm Block", self.farm_block, "farm")
        if block_farm and block_farm != self.farm:
            frappe.throw("Farm Block must belong to the selected Farm.")

        cycle = frappe.db.get_value(
            "Crop Cycle",
            self.crop_cycle,
            ["farm", "farm_block", *INHERITED_CYCLE_FIELDS],
            as_dict=True,
        )
        if not cycle:
            frappe.throw("Crop Cycle does not exist.")
        if cycle.farm != self.farm or cycle.farm_block != self.farm_block:
            frappe.throw("Crop Cycle must belong to the selected Farm and Farm Block.")
        validate_coverage_date(cycle, self.inspection_date)
        if cycle.cycle_type == "Ratoon" and not self.sucker_selection_batch and not is_inherited_opening(cycle):
            frappe.throw("Ratoon inspections must select a Sucker Selection Batch.")

        if self.sucker_selection_batch:
            batch_cycle = frappe.db.get_value(
                "Sucker Selection Batch", self.sucker_selection_batch, "crop_cycle"
            )
            if batch_cycle != self.crop_cycle:
                frappe.throw("Sucker Selection Batch must belong to the selected Crop Cycle.")

    def _validate_standard(self):
        if not self.quality_standard:
            if self.docstatus == 1:
                frappe.throw("Submitted inspections require a Quality Standard.")
            return
        standard = frappe.get_doc("Quality Standard", self.quality_standard)
        standard.check_permission("read")
        if standard.approval_state != "Approved":
            frappe.throw("Quality Standard must be approved.")
        if getdate(self.inspection_date) < getdate(standard.valid_from) or (
            standard.valid_to and getdate(self.inspection_date) > getdate(standard.valid_to)
        ):
            frappe.throw("Standard is not valid on the inspection date.")
        self.standard_version = standard.version
        self.standard_snapshot = json.dumps(standard.as_dict(), default=str, sort_keys=True)
        seen = set()
        for row in self.defects or []:
            if (
                row.defect_reason in seen
                or cint(row.affected_units) < 0
                or cint(row.affected_units) > cint(self.defect_qty)
                or cint(row.occurrences) < cint(row.affected_units)
            ):
                frappe.throw(
                    "Defect lines must be unique; affected units cannot exceed defective units; occurrences must cover affected units."
                )
            seen.add(row.defect_reason)
        measurements = {r.parameter: r for r in self.measurements or []}
        if len(measurements) != len(self.measurements or []):
            frappe.throw("Duplicate quality measurements.")
        passed = cint(self.inspected_qty) > 0 and cint(self.defect_qty) / cint(
            self.inspected_qty
        ) * 100 <= float(standard.max_defective_percent)
        if set(measurements) != {r.parameter for r in standard.parameters or []}:
            frappe.throw("Supply exactly the measurements required by the standard.")
        for parameter in standard.parameters or []:
            observed = measurements[parameter.parameter]
            if observed.uom != parameter.uom:
                frappe.throw("Quality measurement UOM must match the standard.")
            if not float(parameter.minimum) <= float(observed.value) <= float(parameter.maximum):
                passed = False
        self.quality_result = "Pass" if passed else "Fail"
