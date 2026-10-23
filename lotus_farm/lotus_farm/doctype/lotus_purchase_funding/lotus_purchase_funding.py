from frappe.model.document import Document


class LotusPurchaseFunding(Document):
    def validate(self):
        from lotus_farm.purchase_funding import validate
        validate(self)

    def on_trash(self):
        from lotus_farm.purchase_funding import protect_delete
        protect_delete(self)
