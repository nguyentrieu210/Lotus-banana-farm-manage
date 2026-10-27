"""Read-only preview of private Excel-derived lot counts.

This data MUST NOT populate planting_density, Bunch Operation, Crop Cycle,
Harvest Profile, sales commitments, or live forecasts.
File stored in the site private/files volume, not in public assets or Git.
"""
import csv
import os
from collections import defaultdict

import frappe

from lotus_farm.reporting import records
from lotus_farm.scoping import land_filters, land_scope

DATA_FILE = "lotus_222_import_preview_20261018.csv"
FARM = "LOTUS-222"
SOURCE = "Lo_lon_lo_nho_va_so_cay_222.xlsx"
SOURCE_SHA256 = "1e71054ce186babac7be6b19432557b7a912b29ea4043ba3fda20f70b7128435"


def _private_rows():
    path = frappe.get_site_path("private", "files", DATA_FILE)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8-sig", newline="") as handle:
        data = list(csv.DictReader(handle))
    codes = [r["code"] for r in data]
    if len(data) != 64 or len(set(codes)) != 64 or set(code[0] for code in codes) != set("ABCDE"):
        frappe.throw("Bảng mẫu Vườn 222 không đủ 64 lô lớn hoặc bị trùng mã; chưa hiển thị để tránh sai số.")
    return data


@frappe.whitelist()
def preview(farm=None, block=None):
    if not frappe.has_permission("Farm Block", "read") or not frappe.has_permission("Harvest Forecast", "read"):
        frappe.throw("Không có quyền xem dữ liệu dự thu.", frappe.PermissionError)
    if farm and farm != FARM:
        return {"available": False, "message": "Bảng mẫu chỉ thuộc Vườn 222 Thuận Phú."}
    selected = land_scope(farm=FARM, block=block)
    source = _private_rows()
    if source is None:
        return {"available": False, "message": "Bảng mẫu chưa được nạp vào bộ nhớ riêng của máy chủ."}
    permitted = records("Farm Block", land_filters(frappe.get_meta("Farm Block"), selected),
                        ["name", "farm", "block_code", "block_name", "area_ha", "lotus_tree_count", "lotus_tree_count_source"])
    permitted_by_code = {r.block_code: r for r in permitted if r.farm == FARM}
    result = []
    for item in source:
        existing = permitted_by_code.get(item["code"])
        if not existing:
            continue
        count_text = item["tree_count"].strip()
        original_count = int(count_text) if count_text else None
        count = int(existing.lotus_tree_count or 0) or original_count
        count_source = str(existing.lotus_tree_count_source or (SOURCE if original_count else ""))
        expected_area = float(item["area_ha"])
        existing_area = float(existing.area_ha or 0)
        match = abs(expected_area - existing_area) <= 0.03
        result.append({
            "block": existing.name, "code": item["code"],
            "zone": item["code"][0],
            "area_ha": expected_area,
            "system_area_ha": existing_area,
            "area_match": match,
            "tree_count": count,
            "count_status": ("Số cây gốc đợt trước đã chốt" if count is not None else "Chưa có số cây"),
            "count_source": count_source,
            "source_excel_row": int(item["source_excel_row"]),
        })
    groups = []
    for zone in "ABCDE":
        subset = [r for r in result if r["zone"] == zone]
        if subset:
            groups.append({
                "zone": zone, "lots": len(subset),
                "counted_lots": sum(r["tree_count"] is not None for r in subset),
                "area_ha": round(sum(r["area_ha"] for r in subset), 2),
                "known_trees": sum(r["tree_count"] or 0 for r in subset)
            })
    return {
        "available": True, "mode": "import_preview", "farm": FARM,
        "source": SOURCE, "source_sha256": SOURCE_SHA256,
        "source_status": "Bộ số cây kỳ trước được chốt dùng cho dự thu và kế hoạch Lotus, có nguồn theo lô",
        "notice": "Không lưu số cây vào mật độ trồng; không tạo bản ghi trổ hoa/thu hoạch thực tế hoặc cam kết bán.",
        "summary": {
            "lots": len(result),
            "counted_lots": sum(r["tree_count"] is not None for r in result),
            "missing_count_lots": sum(r["tree_count"] is None for r in result),
            "known_trees": sum(r["tree_count"] or 0 for r in result),
            "area_ha": round(sum(r["area_ha"] for r in result), 2),
            "area_mismatch_lots": [r["code"] for r in result if not r["area_match"]],
        },
        "groups": groups, "rows": result,
        "zone_a_outlook": {
            "zone": "A", "flowering_date": "2026-11-01", "as_of": "2026-10-18",
            "basis": "Ước tính người dùng: khu A còn khoảng 2 tuần sẽ trổ hoa",
            "status": "Dự kiến, chưa quan sát", "confidence": "Thấp",
            "harvest_from": "2027-01-17", "harvest_to": "2027-03-29",
            "harvest_basis": "Ba đợt trổ 20/60/20; cắt sau 17 ngày, thu 60-70 ngày sau cắt bắp",
            "reference": "https://www.fao.org/4/ad523e/ad523e05.htm",
            "scope_note": "Ước tính cấp khu A, không khẳng định mọi cây trong từng lô trổ cùng ngày.",
            "ready_for_release": False
        } if any(r["zone"] == "A" for r in result) else None,
    }