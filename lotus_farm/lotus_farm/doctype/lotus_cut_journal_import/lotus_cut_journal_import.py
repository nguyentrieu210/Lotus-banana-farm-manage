from frappe.model.document import Document


class LotusCutJournalImport(Document):
    """Evidence of one journal upload; written only by lotus_farm.cut_forecast.commit_import."""
