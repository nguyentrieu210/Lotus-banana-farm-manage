from frappe.model.document import Document


class LotusAssetDepreciationRun(Document):
    def validate(self):
        from lotus_farm.finance.assets import validate_business_document
        validate_business_document(self)
