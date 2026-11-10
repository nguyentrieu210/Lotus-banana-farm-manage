import hashlib

import frappe
from frappe.model.document import Document


def copy_name(document_type, document_name, round_):
    """One copy per document and signing round: the name itself refuses a second archive."""
    return hashlib.sha1(('%s|%s|%s' % (document_type, document_name, int(round_ or 0))).encode()).hexdigest()


class LotusSignedCopy(Document):
    def autoname(self):
        self.name = copy_name(self.document_type, self.document_name, self.round)

    def validate(self):
        if not self.is_new():
            frappe.throw('Bản PDF đã ký không được sửa.')


def on_doctype_update():
    frappe.db.add_index('Lotus Signed Copy', ['document_type', 'document_name'])
