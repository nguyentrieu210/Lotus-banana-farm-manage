"""Install editable VIP 126 reference parameters as a REAL Frappe Draft record.

Not Approved/active: scenario assumptions from Lotus management's requested
trial, not calibrated measurements.
"""
import frappe

NAME = "VIP 126 | Lotus 222 | Bộ hệ số khởi tạo (chờ đo thực tế)"
NOTES = (
 "CHƯA HIỆU CHUẨN; không được xem là đã duyệt hoặc dùng cam kết bán. "
 "Giống VIP 126 theo xác nhận của người quản lý 18/10/2026. "
  "Trồng đến trổ đầu tiên 6 tháng LỊCH, các đợt trổ tháng 6/7/8 với tỷ lệ 20/60/20. "
 "Ngày trồng tới thu cơ sở của đợt đầu khu A 266 ngày (01/05/2026 đến 22/01/2027). "
 "Chọn chồi kiểm tra sau 90 ngày, từ chọn chồi dự báo trổ sau 6 tháng lịch - hệ số thử nghiệm. "
 "Trổ đến cắt bắp 17 ngày, cắt bắp đến thu 60-70 ngày, lấy giữa 65 ngày, "
 "nên trổ đến thu cơ sở 82 ngày theo người quản lý. "
  "Vụ chồi cách 270 ngày là giả định kế hoạch (chưa hiệu chuẩn, dễ chồng thế hệ). "
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
        "planting_to_harvest_days": 266, "shooting_to_harvest_days": 82, "cut_bud_to_harvest_days": 65,
        "sucker_to_harvest_days": 266, "ratoon_interval_days": 270,
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
            "note": "Đã lưu để người vận hành chỉnh sửa. Việc duyệt và phát hành hàng vẫn bị khóa."}

def sync_cutbud_draft():
    """Controlled, idempotent update of the existing unapproved VIP126 setup.

    Does not modify any approved/active profile or a manually edited value.
    Only this known startup draft gets the 17+65 day rule.
    """
    name = frappe.db.get_value("Harvest Profile", {"profile_name": NAME}, "name")
    if not name:
        return {"status": "missing_profile"}
    doc = frappe.get_doc("Harvest Profile", name)
    if doc.name != "HP-00002" or doc.approval_state != "Draft" or int(doc.active or 0) != 0:
        return {"status": "blocked_protected_profile", "name": doc.name}
    current = (int(doc.shooting_to_harvest_days or 0), int(doc.cut_bud_to_harvest_days or 0))
    if current == (82, 65):
        return {"status": "already_applied", "name": doc.name, "days": current}
    if current != (84, 0):
        return {"status": "blocked_manually_changed", "name": doc.name, "days": current}
    doc.shooting_to_harvest_days = 82
    doc.cut_bud_to_harvest_days = 65
    doc.notes = (doc.notes or "") + (
        "\\n[18/10/2026 - Mốc bổ sung người quản lý] Trổ hoa đến cắt bắp 17 ngày. "
        "Cắt bắp đến thu 60–70 ngày (mốc cơ sở 65). "
        "Tổng trổ đến thu cơ sở 82, sớm 77, muộn 87 ngày. "
        "Không tự động sửa ngày trồng, tỷ lệ sống hay duyệt hệ số."
    )
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "updated_draft", "name": doc.name,
            "flower_to_cut_days": 17,
            "cut_to_harvest_min_days": 60,
            "cut_to_harvest_base_days": 65,
            "cut_to_harvest_max_days": 70,
            "shooting_to_harvest_days": int(doc.shooting_to_harvest_days),
            "cut_bud_to_harvest_days": int(doc.cut_bud_to_harvest_days),
            "approval_state": doc.approval_state,
            "active": doc.active}

def sync_six_month_trial_draft():
    """Update ONLY guarded unapproved HP-00002; no active profile altered."""
    name=frappe.db.get_value("Harvest Profile",{"profile_name":NAME},"name")
    if not name:
        return {"status":"missing"}
    doc=frappe.get_doc("Harvest Profile",name)
    if doc.name!="HP-00002" or doc.approval_state!="Draft" or int(doc.active or 0):
        return {"status":"blocked_approved_or_active","name":doc.name}
    old=(int(doc.planting_to_harvest_days or 0),int(doc.sucker_to_harvest_days or 0))
    if old == (266,266):
        return {"status":"already_applied","name":doc.name}
    if old != (339,245):
        return {"status":"blocked_manual_edit","current":old,"name":doc.name}
    doc.planting_to_harvest_days=266
    doc.sucker_to_harvest_days=266
    doc.notes=(doc.notes or "")+(
      "\\n[18/10/2026 - Quy tắc mới] Trồng đến trổ đợt đầu sau 6 tháng lịch. "
      "Trổ theo 20/60/20 ở tháng +6/+7/+8; chọn chồi dự kiến 90 ngày sau trồng; "
      "từ ngày chọn chồi tính lại như ngày trồng mới trong chế độ thử, "
      "trổ+cắt 17 ngày, cắt->thu 60-70 ngày. "
      "Đợt đầu A: 01/05/2026 trồng suy ngược; 01/11 trổ; 22/01/2027 thu cơ sở. "
      "Các mốc là kế hoạch/chưa đo thực tế. "
      "Giá trị ngày tính theo tháng lịch ưu tiên hơn hệ số ngày cố định."
    )
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"status":"updated_draft","name":doc.name,"planting_to_harvest_days":266,
            "sucker_to_harvest_days":266,"approval_state":doc.approval_state,"active":doc.active}
