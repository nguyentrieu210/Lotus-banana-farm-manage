import frappe
from frappe.model.document import Document

from lotus_farm.care_cycle_rules import APPROVED, check_rule, version_error, zone_of
from lotus_farm.controls import check_farm, lock, validate_version


class WorkScheduleRule(Document):
    """Vòng chăm sóc: one việc every N days, for the farm or one khu. Approved versions are kept.

    A cycle is a farm and a name: all its versions are for the same việc, a new version starts as a draft waiting for
    approval, a version not approved yet is numbered above every other one, and only one version waits at a time. These
    hold however the rule is saved: Công việc ngoài vườn (care_cycle.save_rule), Danh mục or Desk."""

    def before_insert(self):
        # One new version at a time per farm: two people cannot both add the version waiting for approval.
        if self.farm:
            lock("Farm", self.farm)

    def validate(self):
        check_farm(self)
        self.farm_zone = zone_of(self.farm_zone) or None
        validate_version(self, "rule_name", ("Lotus Farm Manager",))
        errors = check_rule(self.as_dict())
        if self.farm_zone and not frappe.db.exists("Farm Block", {"farm": self.farm, "farm_zone": self.farm_zone, "active": 1}):
            errors.append(f"Vườn không có lô nào ở khu {self.farm_zone}.")
        if errors:
            frappe.throw("<br>".join(errors))
        self.keep_cycle()

    def keep_cycle(self):
        before = self.get_doc_before_save()
        if before and before.approval_state == APPROVED:
            return  # validate_version keeps an approved version exactly as it was
        others = frappe.get_all("Work Schedule Rule", filters={"farm": self.farm, "rule_name": self.rule_name, "name": ["!=", self.name]},
                                fields=["work_type", "version", "approval_state"])
        error = version_error(self.as_dict(), others, self.is_new())
        if error:
            frappe.throw(error)

    def on_trash(self):
        if self.approval_state == "Approved":
            frappe.throw("Không được xóa vòng chăm sóc đã duyệt; tạo phiên bản mới hoặc đặt ngày hết áp dụng.")
