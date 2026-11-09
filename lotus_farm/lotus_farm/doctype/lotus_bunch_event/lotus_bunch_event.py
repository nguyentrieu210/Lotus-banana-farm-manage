import frappe
from frappe.model.document import Document

# Once confirmed a line never changes: a correction voids it (with a reason) and writes a new line.
FROZEN = ("farm", "farm_block", "cycle_no", "event_type", "event_date", "qty", "area_ha", "bunch_tag", "reject_stage", "reason", "weight_kg",
          "source_type", "source_name", "source_key", "entered_by")
NEEDS_TAG = ("Cut Bud", "Harvest")


class LotusBunchEvent(Document):
    def validate(self):
        if self.cycle_no is None or int(self.cycle_no) < 1:
            frappe.throw("Vụ phải từ 1 trở lên.")
        if int(self.qty or 0) <= 0:
            frappe.throw("Số lượng phải là số nguyên lớn hơn 0.")
        if frappe.db.get_value("Farm Block", self.farm_block, "farm") != self.farm:
            frappe.throw("Lô không thuộc vườn đã chọn.")
        if self.event_type in NEEDS_TAG and not self.bunch_tag:
            frappe.throw("Việc này phải có màu dây.")
        if self.event_type == "Reject":
            if not self.reason or not self.reject_stage:
                frappe.throw("Buồng hủy phải có lý do và giai đoạn hủy.")
            if self.reject_stage == "After Cut" and not self.bunch_tag:
                frappe.throw("Buồng hủy sau cắt bắp phải có màu dây.")
        if self.event_type == "Harvest" and (self.weight_kg or 0) <= 0:
            frappe.throw("Thu hoạch phải có khối lượng.")
        if self.event_type == "Sucker Select" and (self.area_ha or 0) <= 0:
            frappe.throw("Chọn chồi phải có diện tích đã làm.")
        if self.state == "Voided" and not (self.void_reason or "").strip():
            frappe.throw("Hủy dòng phải ghi lý do.")
        if self.bunch_tag and frappe.db.get_value("Bunch Tag", self.bunch_tag, "farm") != self.farm:
            frappe.throw("Màu dây không thuộc vườn này.")
        before = self.get_doc_before_save()
        if before and before.state != "Draft":
            if before.state == "Voided" or self.state == "Draft" or any(self.get(f) != before.get(f) for f in FROZEN):
                frappe.throw("Dòng đã xác nhận không được sửa; hủy dòng có lý do rồi ghi dòng mới.")

    def on_trash(self):
        if self.state != "Draft":
            frappe.throw("Không xóa dòng sổ buồng; hủy dòng có lý do.")
