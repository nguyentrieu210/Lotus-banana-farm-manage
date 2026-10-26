import frappe
from frappe.model.document import Document


class LotusChatMessage(Document):
    def validate(self):
        if not self.is_new() or not self.flags.get('chat_write'):
            frappe.throw('Tin nhắn chỉ được gửi qua Lotus Chat.', frappe.PermissionError)

    def on_trash(self):
        frappe.throw('Không xóa tin nhắn qua màn hình quản trị.', frappe.PermissionError)
