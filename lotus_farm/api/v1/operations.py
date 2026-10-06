import json

import frappe


@frappe.whitelist(methods=["POST"])
def create(payload):
    payload = frappe.parse_json(payload) if isinstance(payload, str) else payload
    allowed = {"client_event_id", "farm", "farm_block", "crop_cycle", "sucker_selection_batch",
               "operation_type", "operation_date", "bunch_qty", "rejected_qty", "harvest_profile",
               "expected_harvest_date", "device_timestamp"}
    if not isinstance(payload, dict) or set(payload) - allowed or not payload.get("client_event_id"):
        frappe.throw("Supply the operation fields and a client event ID; unsupported fields are rejected.")
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    existing = frappe.db.get_value("Bunch Operation", {"client_event_id": payload["client_event_id"]}, "name")
    if existing:
        doc = frappe.get_doc("Bunch Operation", existing)
        doc.check_permission("read")
        if doc.request_payload_snapshot != canonical:
            frappe.throw("Client event ID was already used with a different payload.")
        return {"name": doc.name, "docstatus": doc.docstatus, "net_bunch_qty": doc.net_bunch_qty}
    doc = frappe.get_doc({"doctype": "Bunch Operation", **payload, "request_payload_snapshot": canonical})
    doc.insert()
    doc.submit()
    return {"name": doc.name, "docstatus": doc.docstatus, "net_bunch_qty": doc.net_bunch_qty}
