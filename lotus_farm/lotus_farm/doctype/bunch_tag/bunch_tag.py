import frappe
from frappe.utils import getdate
from lotus_farm.bunch_tag_rules import overlaps
from lotus_farm.controls import lock
from lotus_farm.promax_controls import ReferenceMaster


class BunchTag(ReferenceMaster):
    def before_insert(self):
        if self.farm and not self.get("process_adoption"):
            lock("Farm", self.farm)

    def validate(self):
        super().validate()
        if self.valid_from and self.valid_to and getdate(self.valid_to) < getdate(self.valid_from):
            frappe.throw("Ngày kết thúc kỳ màu dây không được trước ngày bắt đầu.")
        before = self.get_doc_before_save()
        protected = ("farm", "tag_code", "color_code", "color_label", "period_basis", "valid_from", "valid_to", "week_year", "week_number", "week_half", "source_kind")
        if before and any(self.get(key) != before.get(key) for key in protected):
            if frappe.db.exists("Bunch Operation", {"bunch_tag": self.name}):
                frappe.throw("Màu dây đã có phiếu công đoạn; không được sửa mã, màu hoặc ngày áp dụng. Tạo kỳ mới.")

        if self.source_kind == "Lotus Weekly":
            if not (self.farm and self.color_label and self.color_code and self.valid_from and self.valid_to and self.week_year and self.week_number and self.week_half):
                frappe.throw("Lịch màu Lotus phải có tên màu, tuần, đợt và hai ngày áp dụng.")
            start, end = getdate(self.valid_from), getdate(self.valid_to)
            if (start.isocalendar().year, start.isocalendar().week) != (int(self.week_year), int(self.week_number)):
                frappe.throw("Ngày bắt đầu không thuộc tuần màu đã chọn.")
            if self.week_half == "1":
                if start.weekday() != 0 or (end-start).days != 3:
                    frappe.throw("Đợt 1 phải từ thứ Hai đến hết thứ Năm.")
            elif self.week_half == "2":
                if start.weekday() != 4 or (end-start).days != 2:
                    frappe.throw("Đợt 2 phải từ thứ Sáu đến hết Chủ nhật.")
            else:
                frappe.throw("Chọn đợt 1 hoặc đợt 2.")
            if self.get("process_adoption"):
                frappe.throw("Lịch màu Lotus riêng không được nhận là nguồn OneDrive.")

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
