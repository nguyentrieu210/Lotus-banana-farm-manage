"""Plan & norms workspace. Planning cohorts are estimates, NEVER observed operations.

Only permission-filtered reads. This module never creates Daily Work Plans,
Material Requirements, Purchase Orders, Harvest Forecasts or stock documents.
"""
import frappe
from frappe.model.document import Document
from frappe.utils import flt, cint
from lotus_farm.scoping import land_scope, land_filters
from lotus_farm.controls import check_farm


class PlanCohort(Document):
    def validate(self):
        check_farm(self)
        block = frappe.get_doc("Farm Block", self.farm_block)
        block.check_permission("read")
        if block.farm != self.farm or not block.active:
            frappe.throw("Đợt cây phải thuộc lô đang hoạt động của đúng vườn.")
        if self.crop_cycle:
            cycle = frappe.get_doc("Crop Cycle", self.crop_cycle)
            cycle.check_permission("read")
            if cycle.farm != self.farm or cycle.farm_block != self.farm_block:
                frappe.throw("Vụ cây không thuộc lô đã chọn.")
        if flt(self.planned_qty) <= 0:
            frappe.throw("Số lượng dự kiến phải lớn hơn 0.")
        if cint(self.version) < 1:
            frappe.throw("Phiên bản phải từ 1 trở lên.")
        if not (self.cohort_code or "").strip():
            frappe.throw("Phải nhập mã đợt cây.")
        previous = self.get_doc_before_save()
        if previous and previous.approval_state == "Approved":
            frappe.throw("Đợt đã duyệt không được sửa. Hãy tạo phiên bản mới.")
        if frappe.db.exists("Plan Cohort", {
            "farm": self.farm, "farm_block": self.farm_block,
            "cohort_code": self.cohort_code, "version": self.version,
            "name": ["!=", self.name],
        }):
            frappe.throw("Mã đợt và phiên bản đã tồn tại trong lô.")
        if self.supersedes:
            earlier = frappe.get_doc("Plan Cohort", self.supersedes)
            earlier.check_permission("read")
            if (earlier.farm != self.farm or earlier.farm_block != self.farm_block
                    or earlier.cohort_code != self.cohort_code
                    or cint(earlier.version) >= cint(self.version)):
                frappe.throw("Bản thay thế phải cùng đợt/lô và có phiên bản lớn hơn.")
            if self.approval_state == "Approved" and earlier.approval_state != "Approved":
                frappe.throw("Chỉ thay thế bản đã duyệt.")
        if self.approval_state == "Approved":
            existing = frappe.get_all("Plan Cohort", filters={
                "farm": self.farm, "farm_block": self.farm_block,
                "cohort_code": self.cohort_code, "approval_state": "Approved",
                "name": ["!=", self.name],
            }, fields=["name", "version"], limit_page_length=100)
            for row in existing:
                if cint(row.version) >= cint(self.version):
                    frappe.throw("Phiên bản mới phải lớn hơn bản đã duyệt.")
            if existing and not self.supersedes:
                frappe.throw("Đợt đã có bản duyệt: phải chỉ định bản được thay thế.")

    def on_trash(self):
        if self.approval_state == "Approved":
            frappe.throw("Không được xóa đợt cây đã duyệt.")


def _list(doctype, fields, filters=None, limit=2000):
    if not frappe.has_permission(doctype, "read"):
        return []
    return frappe.get_list(
        doctype, fields=fields, filters=filters or {}, order_by="modified desc",
        limit_page_length=limit,
    )


@frappe.whitelist()
def board(farm=None, block=None):
    """Settings and 36-month simulator inputs; no write side effects."""
    if not farm:
        frappe.throw("Chọn một vườn trước khi xem cấu hình.")
    scope = land_scope(farm=farm, block=block)
    if not frappe.has_permission("Farm", "read") or not frappe.has_permission("Farm Block", "read"):
        frappe.throw("Không có quyền xem vườn hoặc lô.", frappe.PermissionError)
    # All Farm-linked queries are bounded by this permission-checked Farm.
    blocks = _list("Farm Block", ["name", "farm", "block_name", "block_code",
        "area_ha", "planting_density", "variety", "active"],
        land_filters(frappe.get_meta("Farm Block"), scope))
    permitted = {b.name for b in blocks}
    farm_scope = {"farm": farm}
    cycles = _list("Crop Cycle", ["name","farm_block","cycle_no","cycle_type",
        "planting_date","status","variety"], farm_scope)
    cycles = [c for c in cycles if c.farm_block in permitted]
    cohorts = _list("Plan Cohort", ["name","farm","farm_block","cohort_code",
        "cohort_name","crop_cycle","anchor","anchor_date","quantity_basis",
        "planned_qty","version","approval_state","supersedes","modified","notes"],
        farm_scope) if frappe.db.exists("DocType","Plan Cohort") else []
    cohorts = [c for c in cohorts if c.farm_block in permitted]
    rules = _list("Work Schedule Rule", ["name","farm","rule_name","work_type",
        "anchor","offset_days","repeat_days","quantity_basis","norm_profile",
        "valid_from","valid_to","version","approval_state","modified"], farm_scope)
    norms = _list("Material Norm Profile", ["name","farm","profile_name",
        "work_type","valid_from","valid_to","version","approval_state","modified"], farm_scope)
    # Material quantities only come from approved norm versions, by Work Type.
    norm_lines = {}
    for profile in norms:
        if profile.approval_state == "Approved":
            doc = frappe.get_doc("Material Norm Profile", profile.name)
            doc.check_permission("read")
            norm_lines[profile.name] = [
                {"item": r.item, "uom": r.uom, "norm_qty": r.norm_qty,
                 "basis_qty": r.basis_qty, "frequency": r.frequency,
                 "conversion_factor": r.conversion_factor}
                for r in doc.lines
            ]
    profiles = _list("Harvest Profile", [
        "name","profile_name","farm","farm_block","variety","cycle_type",
        "valid_from","valid_to","approval_state","active","version",
        "planting_to_harvest_days","sucker_to_harvest_days",
        "shooting_to_harvest_days","cut_bud_to_harvest_days",
        "ratoon_interval_days","avg_bunch_weight_kg",
        "bunch_survival_rate_percent","quality_pass_rate_percent",
        "packout_rate_percent","modified"
    ], {"farm": ["in", [farm, ""]]}, limit=1000)
    profiles = [p for p in profiles if not p.farm_block or p.farm_block in permitted]
    return {
        "farm": farm, "blocks": blocks, "cycles": cycles, "cohorts": cohorts,
        "rules": rules, "norms": norms, "norm_lines": norm_lines,
        "profiles": profiles,
        "works": _list("Work Type", ["name","work_name","uom",
            "productivity_per_workday","piecework_rate","allow_piecework",
            "allow_daywork","active"], {"active": 1}, limit=1000),
        "permissions": {dt: {
            "read": frappe.has_permission(dt,"read"),
            "create": frappe.has_permission(dt,"create"),
            "write": frappe.has_permission(dt,"write"),
        } for dt in ["Plan Cohort","Work Schedule Rule",
            "Material Norm Profile","Harvest Profile","Work Type"]},
        "rule": "Mô phỏng chỉ đọc. Số đợt dự kiến không phải sản lượng thật hay hàng có thể bán.",
    }
