import frappe

from lotus_farm.supply import availability


@frappe.whitelist(methods=["GET"])
def get(forecast):
    doc = frappe.get_doc("Harvest Forecast", forecast)
    doc.check_permission("read")
    if doc.docstatus != 1:
        frappe.throw("Availability is published only for submitted forecasts.")
    return {"forecast": doc.name, "item_code": doc.item_code, **availability(doc)}
