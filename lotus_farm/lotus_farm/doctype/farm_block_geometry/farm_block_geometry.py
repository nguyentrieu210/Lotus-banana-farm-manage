"""Versioned, review-only care block geometry."""
import json
import frappe
from frappe.model.document import Document

from lotus_farm.controls import check_farm, validate_version
from lotus_farm.promax_rules import geometry
from lotus_farm.rules import RuleError


class FarmBlockGeometry(Document):
    def validate(self):
        check_farm(self)
        block = frappe.get_doc("Farm Block", self.farm_block)
        block.check_permission("read")
        if block.farm != self.farm:
            frappe.throw("Hình học lô chăm sóc phải thuộc cùng vườn.")
        validate_version(self, "farm_block", ("Lotus Farm Manager",))
        try:
            self.geojson = json.dumps(geometry(self.geojson), separators=(",", ":"))
        except (ValueError, KeyError, TypeError, RuleError) as exc:
            frappe.throw(str(exc))

    def on_trash(self):
        if self.approval_state == "Approved":
            frappe.throw("Hình học lô chăm sóc đã duyệt được giữ lại để kiểm toán.")
