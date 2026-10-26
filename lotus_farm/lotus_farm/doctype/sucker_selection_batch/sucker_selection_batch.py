import frappe
from frappe.model.document import Document
from frappe.utils import cint, getdate, nowdate


class SuckerSelectionBatch(Document):
    def validate(self):
        self._validate_scope()
        if getdate(self.selection_date) > getdate(nowdate()):
            frappe.throw("Đợt chọn chồi thực tế không được ở tương lai; dùng Đợt cây kế hoạch cho ngày dự kiến.")
        selected = cint(self.selected_sucker_qty)
        expected = cint(self.expected_productive_qty)

        if selected <= 0 or expected < 0:
            frappe.throw("Số chồi không được âm.")
        if expected and expected > selected:
            frappe.throw("Số cây cho trái dự kiến không được vượt số chồi đã chọn.")

    def _validate_scope(self):
        cycle = frappe.db.get_value(
            "Crop Cycle",
            self.crop_cycle,
            ["farm", "farm_block", "cycle_type"],
            as_dict=True,
        )
        if not cycle:
            frappe.throw("Vụ không tồn tại.")
        if cycle.farm != self.farm or cycle.farm_block != self.farm_block:
            frappe.throw("Vụ phải thuộc vườn và lô đã chọn.")
        if cycle.cycle_type != "Ratoon":
            frappe.throw("Đợt chọn chồi dùng cho vụ chồi (lưu gốc), từ vụ 2 trở đi.")
