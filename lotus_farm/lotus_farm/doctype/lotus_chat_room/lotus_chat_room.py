import frappe
from frappe.model.document import Document


class LotusChatRoom(Document):
    def validate(self):
        if not self.flags.get('chat_write'):
            frappe.throw('Chỉ tạo hoặc sửa hội thoại qua Lotus Chat.', frappe.PermissionError)

    def on_trash(self):
        frappe.throw('Không xóa lịch sử hội thoại qua màn hình quản trị.', frappe.PermissionError)
