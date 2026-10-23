import frappe
from frappe.model.document import Document


class LotusPurchaseImport(Document):
    def validate(self):
        if not self.is_new() or not self.flags.get('procurement_write'):
            frappe.throw('Lịch sử nhập mua hàng chỉ được tạo bằng bước xác nhận xem trước.')

    def on_trash(self):
        frappe.throw('Giữ lịch sử và file gốc để đối chiếu các chứng từ đã nhập.')
