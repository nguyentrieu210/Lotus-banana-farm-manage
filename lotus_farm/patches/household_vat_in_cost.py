import frappe


def execute():
    """Lotus is a household business (hộ kinh doanh): input VAT is not deductible and goes into the cost of goods bought.
    Turn the setting on once for sites created before it existed; the chief accountant can turn it off in Tài chính."""
    frappe.db.set_single_value('Lotus Finance Settings', 'vat_in_cost', 1)
