from frappe.model.document import Document
from lotus_farm.work_allowance import validate_rate


class LotusPayRate(Document):
    def validate(self):
        validate_rate(self)

    def on_trash(self):
        import frappe
        frappe.throw("Không xoá mức đã đặt; thêm mức mới với ngày áp dụng mới.")
