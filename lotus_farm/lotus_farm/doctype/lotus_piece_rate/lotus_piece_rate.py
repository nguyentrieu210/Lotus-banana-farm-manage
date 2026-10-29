from frappe.model.document import Document
from lotus_farm.field_report import validate_rate


class LotusPieceRate(Document):
    def validate(self):
        validate_rate(self)
