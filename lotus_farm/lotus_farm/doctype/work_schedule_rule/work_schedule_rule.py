import frappe
from frappe.model.document import Document

from lotus_farm.care_cycle_rules import check_rule, zone_of
from lotus_farm.controls import check_farm, validate_version


class WorkScheduleRule(Document):
    """Vòng chăm sóc: one việc every N days, for the farm or one khu. Approved versions are kept."""

    def validate(self):
        check_farm(self)
        self.farm_zone = zone_of(self.farm_zone) or None
        validate_version(self, "rule_name", ("Lotus Farm Manager",))
        errors = check_rule(self.as_dict())
        if self.farm_zone and not frappe.db.exists("Farm Block", {"farm": self.farm, "farm_zone": self.farm_zone, "active": 1}):
            errors.append(f"Vườn không có lô nào ở khu {self.farm_zone}.")
        if errors:
            frappe.throw("<br>".join(errors))

    def on_trash(self):
        if self.approval_state == "Approved":
            frappe.throw("Không được xóa vòng chăm sóc đã duyệt; tạo phiên bản mới hoặc đặt ngày hết áp dụng.")
