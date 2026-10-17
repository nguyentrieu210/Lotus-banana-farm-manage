"""Install editable VIP 126 reference parameters as a REAL Frappe Draft record.

Not Approved/active: scenario assumptions from Lotus management's requested
trial, not calibrated measurements.
"""
import frappe

NAME = "VIP 126 | Lotus 222 | Bộ hệ số khởi tạo (chờ đo thực tế)"
NOTES = (
 "CHƯA HIỆU CHUẨN; không được xem là đã duyệt hoặc dùng cam kết bán. "
 "Giống VIP 126 theo xác nhận của người quản lý 18/10/2026. "
 "Số ngày trồng đến thu 339 = 255 ngày trồng->trổ (giả định 8,5 tháng)"
 " + 84 ngày trổ->thu (12 tuần trong khoảng FAO 10-14 tuần). "
 "Từ chọn chồi đến thu 245 ngày và vụ chồi cách 270 ngày là giả định kế hoạch. "
 "Kg/buồng 20, tỷ lệ sống 90%, QC đạt 85%, đóng gói 75%, "
 "dự phòng 10% là GIẢ ĐỊNH thử tính, chưa cân mẫu VIP 126 tại Lotus. "
 "Nguồn FAO (10-14 tuần): https://www.fao.org/4/ad523e/ad523e05.htm . "
 "Phải đo ngày trổ, số buồng, cân kg, QC, packout rồi mới trình duyệt."
)


def seed():
    previous = frappe.db.get_value("Harvest Profile", {"profile_name": NAME}, "name")
    if previous:
        return {"status": "already_exists", "name": previous}
    record = frappe.get_doc({
        "doctype": "Harvest Profile", "profile_name": NAME,
        "farm": "LOTUS-222", "farm_block": None, "variety": "VIP 126",
        "valid_from": "2026-10-18", "version": 1,
        "active": 0, "approval_state": "Draft",
        "planting_to_harvest_days": 339, "shooting_to_harvest_days": 84,
        "sucker_to_harvest_days": 245, "ratoon_interval_days": 270,
        "avg_bunch_weight_kg": 20,
        "bunch_survival_rate_percent": 90,
        "quality_pass_rate_percent": 85,
        "packout_rate_percent": 75,
        "safety_buffer_percent": 10,
        "notes": NOTES,
    })
    record.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "created_draft", "name": record.name,
            "approval_state": record.approval_state, "active": record.active,
            "note": "Persisted for operator editing. Approval and stock release stay blocked."}
