import frappe
from frappe.model.document import Document

from lotus_farm import cut_forecast_rules as rules


class LotusCutForecastProfile(Document):
    """An approved profile is frozen: changing a parameter creates the next version (lotus_farm.cut_forecast.save_profile)."""

    def validate(self):
        before = None if self.is_new() else self.get_doc_before_save()
        if before and before.approval_state == 'Approved':
            frappe.throw('Bộ thông số đã duyệt không sửa được. Hãy lưu thành phiên bản mới.')
        clean, errors = rules.validate_profile({f: self.get(f) for f, _, _, _ in rules.PARAMS})
        if errors:
            frappe.throw('<br>'.join(errors))
        self.update(clean)

    def on_trash(self):
        if self.approval_state == 'Approved':
            frappe.throw('Không xóa bộ thông số đã duyệt.')
