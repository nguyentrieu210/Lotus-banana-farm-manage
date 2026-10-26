import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, getdate
from lotus_farm.controls import local_timestamp
from lotus_farm.rules import canonical_hash, scale_net, RuleError


class ScaleReading(Document):
    def validate(self):
        if not self.is_new():
            frappe.throw("Dữ liệu cân gốc không được sửa. Ghi điều chỉnh riêng.")
        self.captured_at = local_timestamp(self.captured_at)
        if frappe.db.get_single_value('Lotus Farm Settings','require_registered_scale'):
            device_name=frappe.db.get_value('Scale Device',{'device_id':self.device_id},'name')
            if not device_name:frappe.throw('Đăng ký và gắn cân này trước khi nhận dữ liệu cân.')
            device=frappe.get_doc('Scale Device',device_name);device.check_permission('read')
            if not device.enabled or device.farm!=self.farm or device.integration_user!=frappe.session.user:
                frappe.throw('Cân đang tắt hoặc chưa gắn với vườn và người dùng API này.',frappe.PermissionError)
            if not getdate(device.calibrated_on)<=getdate(self.captured_at)<=getdate(device.calibration_due):
                frappe.throw('Lần cân nằm ngoài kỳ hiệu chuẩn đã đăng ký.')
        if self.captured_at > now_datetime():
            frappe.throw("Thời điểm cân không được ở tương lai.")
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
        frappe.throw("Không được xóa dữ liệu cân gốc.")
