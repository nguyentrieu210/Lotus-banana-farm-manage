import frappe
from frappe.utils import getdate
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

    def on_trash(self):
        if frappe.db.exists("Bunch Operation", {"bunch_tag": self.name}):
            frappe.throw("Màu dây đã dùng trong phiếu công đoạn; không được xóa lịch sử.")
