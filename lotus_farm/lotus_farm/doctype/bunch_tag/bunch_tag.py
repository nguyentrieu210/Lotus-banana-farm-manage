import frappe
from frappe.utils import getdate
from lotus_farm.bunch_tag_rules import overlaps
from lotus_farm.promax_controls import ReferenceMaster


class BunchTag(ReferenceMaster):
    def validate(self):
        super().validate()
        if self.valid_from and self.valid_to and getdate(self.valid_to) < getdate(self.valid_from):
            frappe.throw("Ngày kết thúc kỳ màu dây không được trước ngày bắt đầu.")
        before = self.get_doc_before_save()
        protected = ("farm", "tag_code", "color_code", "period_basis", "valid_from", "valid_to")
        if before and any(self.get(key) != before.get(key) for key in protected):
            if frappe.db.exists("Bunch Operation", {"bunch_tag": self.name}):
                frappe.throw("Màu dây đã có phiếu công đoạn; không được sửa mã, màu hoặc ngày áp dụng. Tạo kỳ mới.")

        # Old unversioned records can still be read. New cut-bud periods must
        # have a farm and both dates so they cannot apply indefinitely by mistake.
        if not self.get("process_adoption") and self.is_new() and self.period_basis == "Cut Bud":
            if not (self.farm and self.valid_from and self.valid_to):
                frappe.throw("Kỳ màu dây mới phải chọn vườn, ngày bắt đầu và ngày kết thúc.")

        if not self.get("process_adoption") and self.enabled and self.farm and self.period_basis == "Cut Bud" and self.valid_from and self.valid_to:
            others = frappe.get_all(
                "Bunch Tag",
                filters={"farm": self.farm, "period_basis": "Cut Bud", "enabled": 1,
                         "valid_from": ["<=", self.valid_to], "name": ["!=", self.name]},
                fields=["name", "valid_from", "valid_to"],
            )
            if any(overlaps(self.valid_from, self.valid_to, row.valid_from, row.valid_to) for row in others):
                frappe.throw("Vườn đã có kỳ màu dây trùng ngày. Tạo kỳ mới không chồng lịch.")

    def on_trash(self):
        if frappe.db.exists("Bunch Operation", {"bunch_tag": self.name}):
            frappe.throw("Màu dây đã dùng trong phiếu công đoạn; không được xóa lịch sử.")
