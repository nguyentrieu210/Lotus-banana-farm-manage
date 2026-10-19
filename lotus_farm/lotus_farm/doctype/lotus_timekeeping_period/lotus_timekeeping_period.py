import frappe
from frappe.model.document import Document


class LotusTimekeepingPeriod(Document):
    def validate(self):
        from lotus_farm.timekeeping_rules import month_range
        try:
            month_range(self.month)
        except ValueError as exc:
            frappe.throw(str(exc))
        before = self.get_doc_before_save()
        # Status only moves through close_period / reopen_period, which check blockers and keep the snapshot.
        if (self.status or 'Open') != ((before.status if before else None) or 'Open') and not self.flags.get('lotus_period_action'):
            frappe.throw('Khóa hoặc mở kỳ công từ màn Cấu hình lương Lotus.')

    def on_trash(self):
        if self.status == 'Closed':
            frappe.throw('Không xóa kỳ công đã khóa.')
