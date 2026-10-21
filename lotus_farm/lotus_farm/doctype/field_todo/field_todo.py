"""Field To-do writes are restricted to the dedicated, scope-checked API."""
import frappe
from frappe.model.document import Document


class FieldTodo(Document):
    def validate(self):
        from lotus_farm.field_todo import _writing
        if not _writing.get():
            frappe.throw("Hãy thao tác bằng bảng giao việc ngoài vườn.", frappe.PermissionError)
