"""Đợt cây kế hoạch (estimates, never observed operations). Kept until the legacy purge of spec 002 removes the DocType."""
import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt

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
