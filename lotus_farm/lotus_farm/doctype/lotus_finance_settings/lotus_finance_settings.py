import frappe
from frappe.model.document import Document


class LotusFinanceSettings(Document):
    """Accounts are checked by lotus_farm.finance.setup.validate_settings when saved."""

    def validate(self):
        from lotus_farm.finance.setup import validate_settings
        validate_settings(self)
