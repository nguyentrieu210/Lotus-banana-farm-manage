import frappe
from frappe.model.document import Document


class LotusSignatureEvent(Document):
    pass


def on_doctype_update():
    # The history of one document is read by (type, name) on every print and verification.
    frappe.db.add_index('Lotus Signature Event', ['document_type', 'document_name'])
