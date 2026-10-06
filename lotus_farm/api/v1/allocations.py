import frappe
from frappe.utils import flt


@frappe.whitelist(methods=["POST"])
def reserve(forecast, sales_order, sales_order_item, reserved_qty_kg, client_event_id):
    if not client_event_id:
        frappe.throw("A client event ID is required for retry-safe reservations.")
    existing = frappe.db.get_value("Forecast Reservation", {"client_event_id": client_event_id}, "name")
    if existing:
        doc = frappe.get_doc("Forecast Reservation", existing)
        doc.check_permission("read")
        if (doc.forecast, doc.sales_order, doc.sales_order_item, flt(doc.reserved_qty_kg)) != (
            forecast, sales_order, sales_order_item, flt(reserved_qty_kg)
        ):
            frappe.throw("Client event ID was already used for a different reservation.")
        return {"name": doc.name, "docstatus": doc.docstatus}
    doc = frappe.get_doc({"doctype": "Forecast Reservation", "forecast": forecast,
                          "sales_order": sales_order, "sales_order_item": sales_order_item,
                          "reserved_qty_kg": reserved_qty_kg, "client_event_id": client_event_id})
    doc.insert()
    doc.submit()
    return {"name": doc.name, "docstatus": doc.docstatus}


@frappe.whitelist(methods=["POST"])
def release(reservation, reason):
    if not reason or not reason.strip():
        frappe.throw("A release reason is required.")
    doc = frappe.get_doc("Forecast Reservation", reservation)
    doc.check_permission("cancel")
    if doc.docstatus == 2:
        return doc.name
    if doc.docstatus != 1:
        frappe.throw("Only submitted reservations can be released.")
    doc.add_comment("Comment", text=reason)
    doc.cancel()
    return doc.name
