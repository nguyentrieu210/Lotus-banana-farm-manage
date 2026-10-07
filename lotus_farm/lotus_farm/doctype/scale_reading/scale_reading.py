import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, getdate
from lotus_farm.controls import local_timestamp
from lotus_farm.rules import canonical_hash, scale_net, RuleError


class ScaleReading(Document):
    def validate(self):
        if not self.is_new():
            frappe.throw("Raw Scale Readings are immutable. Record corrections separately.")
        self.captured_at = local_timestamp(self.captured_at)
        if frappe.db.get_single_value('Lotus Farm Settings','require_registered_scale'):
            device_name=frappe.db.get_value('Scale Device',{'device_id':self.device_id},'name')
            if not device_name:frappe.throw('Register and bind this Scale Device before receiving readings.')
            device=frappe.get_doc('Scale Device',device_name);device.check_permission('read')
            if not device.enabled or device.farm!=self.farm or device.integration_user!=frappe.session.user:
                frappe.throw('Scale is disabled or not bound to this Farm and API user.',frappe.PermissionError)
            if not getdate(device.calibrated_on)<=getdate(self.captured_at)<=getdate(device.calibration_due):
                frappe.throw('Reading is outside the registered calibration period.')
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
