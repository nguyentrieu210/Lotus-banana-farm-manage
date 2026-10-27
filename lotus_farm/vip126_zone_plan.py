"""VIP 126 LOTUS-222 zone planting sequence, entered as explicitly ESTIMATED data.

User confirms only the *relative order*: A then B then C then D,
one calendar month apart. Absolute date for zone A is inferred from an
unverified flowering estimate. NEVER set Farm Block.planting_date.
"""
from datetime import timedelta
import frappe
from frappe.utils import add_months, getdate
from lotus_farm.vip126_live import FARM, VARIETY
from lotus_farm.forecast_import_preview import _private_rows
from lotus_farm.scoping import land_scope, land_filters
from lotus_farm.reporting import records

CONFIRMED_SEQUENCE = ("A", "B", "C", "D")
PENDING_ZONE = "E"
ZONE_A_INFERRED_PLANTING = "2026-05-01"
ZONE_A_EXPECTED_FLOWERING = "2026-11-01"
DISTRIBUTION = (20, 60, 20)
REVISION_TAG = "LOTUS-ZONE-SEQUENCE-6MONTH-20261018"
LEGACY_REVISION_TAG = "LOTUS-ZONE-SEQUENCE-20261018"
ZONE_REASON = (
    "ƯỚC TÍNH KẾ HOẠCH, KHÔNG PHẢI NGÀY TRỒNG THỰC TẾ. "
     "Khu A suy ngược từ ngày trổ đầu tiên dự kiến 01/11/2026 lùi đúng 6 tháng lịch = 01/05/2026. "
    "Người quản lý xác nhận thứ tự trồng A → B → C → D; "
    "mỗi khu sau trồng muộn hơn khu trước đúng 01 tháng lịch. "
    "Trổ dự kiến từng khu được giãn theo tháng tương ứng; "
     "Trổ đợt 1 sau trồng 6 tháng (20%), tháng 7 (60%), tháng 8 (20%). "
    "Chọn chồi kiểm tra dự kiến sau 90 ngày; cắt bắp 17 ngày sau trổ; thu sau cắt 60-70 ngày. "
    "Dự phóng chưa có số đo thực địa, chỉ phục vụ tính thử 36 tháng."
)


def planned_dates(zone):
    if zone not in CONFIRMED_SEQUENCE:
        return None
    offset = CONFIRMED_SEQUENCE.index(zone)
    return {
        "zone": zone,
        "planting_estimate": str(getdate(add_months(ZONE_A_INFERRED_PLANTING, offset))),
        "flowering_estimate": str(getdate(add_months(ZONE_A_EXPECTED_FLOWERING, offset))),
        "planting_month_offset": offset,
        "source": "Zone A baseline inferred; B–D order confirmed by manager",
        "estimate_only": True,
        "flowering_distribution": list(DISTRIBUTION),
        "sucker_selection_estimate": str(getdate(add_months(ZONE_A_INFERRED_PLANTING, offset)) + timedelta(days=90)),
    }


def _check_inventory():
    rows = _private_rows()
    if not rows or len(rows) != 64:
        frappe.throw("Bảng kiểm kê private của Vườn 222 chưa có đủ 64 lô.")
    source = {r["code"]: r for r in rows}
    if len(source) != len(rows):
        frappe.throw("Có mã lô trùng trong bảng nhập Excel.")
    observed = frappe.get_all("Farm Block", filters={"farm": FARM},
        fields=["name", "block_code", "area_ha"], limit_page_length=200)
    docs = {x.block_code: x for x in observed}
    if set(docs) != set(source):
        frappe.throw("Mã lô Excel và Lotus không khớp; dừng cập nhật.")
    if any(abs(float(docs[code].area_ha)-float(item["area_ha"])) > .03
           for code, item in source.items()):
        frappe.throw("Diện tích của một số lô không khớp, dừng cập nhật.")
    return docs


def _ensure_sucker_estimate_field():
    fieldname = "lotus_estimated_sucker_selection_date"
    if frappe.db.exists("Custom Field", "Farm Block-" + fieldname):
        return False
    frappe.get_doc({
        "doctype":"Custom Field", "dt":"Farm Block", "fieldname":fieldname,
        "fieldtype":"Date", "label":"Ngày chọn chồi dự kiến (90 ngày)",
        "insert_after":"lotus_inferred_planting_date",
        "description":"Ngày trồng suy ngược + 90 ngày; chưa phải ngày chọn chồi thực tế.",
    }).insert(ignore_permissions=True)
    frappe.clear_cache(doctype="Farm Block")
    return True


def apply_zone_estimates():
    """Retired: the shared Farm Block forecast owns all estimated dates."""
    frappe.throw("Công cụ lịch khu cũ đã ngừng. Sửa mốc trổ tại Vườn & lô; dự thu dùng chung mô hình 36 tháng.")


def status(farm=None, zone=None, block=None):
    if not frappe.has_permission("Farm Block", "read") or not frappe.has_permission(
        "Harvest Forecast", "read"
    ):
        frappe.throw("Không có quyền xem kế hoạch khu.", frappe.PermissionError)
    if farm and farm != FARM:
        return {"available": False, "message": "Kế hoạch này dành cho Vườn 222."}
    if zone and zone not in (*CONFIRMED_SEQUENCE, PENDING_ZONE):
        frappe.throw("Khu không hợp lệ.")
    selected = land_scope(farm=FARM, block=block)
    docs = records("Farm Block", land_filters(
        frappe.get_meta("Farm Block"), selected),
        ["name","farm","block_code","planting_date",
         "lotus_inferred_planting_date","lotus_estimated_flowering_date",
         "lotus_tree_count","lotus_estimation_basis",
         "lotus_estimated_sucker_selection_date"])
    docs = [d for d in docs if d.farm == FARM and
            (not zone or d.block_code.startswith(zone))]
    result = []
    for z in (*CONFIRMED_SEQUENCE, PENDING_ZONE):
        rows = [x for x in docs if x.block_code.startswith(z)]
        if not rows:
            continue
        plan = planned_dates(z)
        result.append({
            "zone":z,"lots":len(rows),"confirmed_counted_lots":
                sum(int(x.lotus_tree_count or 0)>0 for x in rows),
            "estimated_planting_date":plan["planting_estimate"] if plan else None,
            "estimated_flowering_date":plan["flowering_estimate"] if plan else None,
            "estimated_sucker_selection_date":plan["sucker_selection_estimate"] if plan else None,
            "saved_estimated_dates":sum(
                str(x.lotus_inferred_planting_date or "") ==
                (plan["planting_estimate"] if plan else "-") and
                str(x.lotus_estimated_flowering_date or "") ==
                (plan["flowering_estimate"] if plan else "-") and
                str(x.lotus_estimated_sucker_selection_date or "") ==
                (plan["sucker_selection_estimate"] if plan else "-") for x in rows),
            "actual_planting_lots":sum(bool(x.planting_date) for x in rows),
            "pending":plan is None,
            "note":("Chưa xác nhận lịch trồng của khu E; chỉ chạy giả lập."
                    if plan is None else
                    "Đã lưu ngày trồng suy ngược và ngày trổ dự kiến, chưa đo thực tế."),
        })
    return {"available":True,"status":"ESTIMATE_NOT_OBSERVED",
            "farm":FARM,"distribution":list(DISTRIBUTION),
            "zones":result,"note":ZONE_REASON}