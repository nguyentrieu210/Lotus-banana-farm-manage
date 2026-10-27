"""Farm-scoped, immutable-on-approval forecast assumptions."""
import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

from lotus_farm.forecast_parameters import validate
from lotus_farm.controls import lock, require_role


class LotusBlockForecastProfile(Document):
    def validate(self):
        frappe.get_doc("Farm", self.farm).check_permission("read")
        lock("Farm", self.farm)
        old = None if self.is_new() else self.get_doc_before_save()
        if old and old.approval_state == "Approved":
            frappe.throw("Bộ dự thu đã duyệt không chỉnh sửa được. Tạo phiên bản mới.")
        if self.farm_block:
            block=frappe.get_doc("Farm Block",self.farm_block)
            block.check_permission("read")
            if block.farm != self.farm:
                frappe.throw("Bộ thông số phải dùng lô thuộc đúng vườn.")
        if int(self.version or 0)<1:
            frappe.throw("Phiên bản phải từ 1 trở lên.")
        if self.valid_to and str(self.valid_to)<str(self.valid_from):
            frappe.throw("Ngày hiệu lực kết thúc phải sau ngày bắt đầu.")
        duplicate=frappe.db.exists(self.doctype, {
            "farm":self.farm,
            "farm_block":self.farm_block or "",
            "version":self.version,
            "name":["!=",self.name],
        })
        if duplicate:
            frappe.throw("Vườn/lô đã có phiên bản thông số cùng số phiên bản.")
        try:
            clean=validate(self.as_dict())
        except ValueError as err:
            frappe.throw(str(err))
        for key,val in clean.items():
            self.set(key,val)
        if self.approval_state=="Approved":
            require_role("System Manager", "Lotus Farm Manager")
            if not self.valid_to:
                frappe.throw("Bộ thông số đã duyệt phải có ngày hết hiệu lực để quản lý phiên bản về sau.")
            if not (self.source_reference or "").strip() or not (self.notes or "").strip():
                frappe.throw("Trước khi duyệt cần ghi nguồn và biên bản/căn cứ xác nhận kỹ thuật.")
            others=frappe.get_all(self.doctype,filters={
                "farm":self.farm,"approval_state":"Approved","name":["!=",self.name]},
                fields=["name","farm_block","valid_from","valid_to"])
            for other in others:
                if (other.farm_block or "")!=(self.farm_block or ""):
                    continue
                if str(other.valid_from)<=str(self.valid_to) and str(self.valid_from)<=str(other.valid_to or "9999-12-31"):
                    frappe.throw("Hai phiên bản dự thu đã duyệt cùng vườn/lô không được chồng ngày hiệu lực.")
            self.approved_by=frappe.session.user
            self.approved_at=now_datetime()
        else:
            self.approved_by=None
            self.approved_at=None

    def on_trash(self):
        if self.approval_state=="Approved":
            frappe.throw("Không xóa bộ hệ số đã duyệt. Tạo phiên bản thay thế.")
