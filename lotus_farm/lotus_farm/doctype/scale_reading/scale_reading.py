import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
from lotus_farm.controls import local_timestamp
from lotus_farm.rules import canonical_hash, scale_net, RuleError


class ScaleReading(Document):
    def validate(self):
        if not self.is_new():
            frappe.throw("Raw Scale Readings are immutable. Record corrections separately.")
        self.captured_at = local_timestamp(self.captured_at)
        if self.captured_at > now_datetime():
            frappe.throw("Scale capture time cannot be in the future.")
        self.event_key = canonical_hash([self.farm, self.device_id, self.reading_id])
        try:
            self.net_kg = scale_net(self.gross_kg, self.tare_kg)
        except RuleError as exc:
            frappe.throw(str(exc))
        self.server_received_at = now_datetime()
        self.payload_hash = canonical_hash(
            {
                k: self.get(k)
                for k in ("farm", "device_id", "reading_id", "captured_at", "gross_kg", "tare_kg")
            }
        )

    def on_trash(self):
        frappe.throw("Raw Scale Readings cannot be deleted.")
