import frappe
from frappe.model.document import Document


class CancellationReason(Document):
    def validate(self):
        before = self.get_doc_before_save()
        if before and frappe.db.exists("Lotus Work Entry", {"reason": self.name}):
            if any(self.get(f) != before.get(f) for f in ("reason_code", "reason_name", "reason_group")):
                frappe.throw("Phân loại hủy đã dùng thì không được gán lại. Hãy tạo lý do mới và ngừng dùng lý do cũ.")
