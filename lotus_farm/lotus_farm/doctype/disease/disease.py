from frappe.model.document import Document

from lotus_farm.controls import keep_codes


class Disease(Document):
    def validate(self):
        keep_codes(self)
