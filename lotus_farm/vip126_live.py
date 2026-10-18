"""Verified Lotus 222 VIP 126 census import, and controlled removal of legacy cycle.

Actual values: 64 lot IDs, area and 30 counted tree quantities from Excel.
Inferences: planting date and flowering/harvest window derived from user forecast.
No guessed values are written into observed planting_date or harvest receipts.
"""
import csv
import json
import os
from datetime import timedelta

import frappe
from frappe.utils import getdate, nowdate
from lotus_farm.forecast_import_preview import _private_rows, FARM, SOURCE, SOURCE_SHA256

VARIETY = "VIP 126"
OLD_CYCLE = "CYCLE-00001"
OLD_BLOCK_CODE = "A13"
OLD_BLOCK_ID = "cihuaei26t"
FLOWER_DATE = "2026-11-01"
AS_OF = "2026-10-18"
PLANT_TO_FLOWER_DAYS = 184  # legacy, do not use for new calendar-month inference
FLOWER_TO_HARVEST_DAYS = 84  # 12 weeks planning median; range 10-14 weeks
RATOON_INTERVAL_DAYS = 270  # uncalibrated planning scenario
SOURCE_NOTICE = "Nguồn số cây: " + SOURCE + " | SHA256 " + SOURCE_SHA256
ESTIMATE_NOTICE = (
    "VIP 126 do người quản lý xác nhận 18/10/2026. "
    "Trổ hoa khu A 01/11/2026 là DỰ KIẾN, chưa quan sát từng lô. "
    "Ngày trồng suy ngược 6 tháng lịch từ trổ là ƯỚC TÍNH, không phải ngày trồng thật. "
    "Thời gian trổ-đến-thu tham khảo 10–14 tuần, chưa có hiệu chuẩn thực địa. "
    "Các lô A có nhiều thế hệ cây thì không gộp lượng cây để cam kết."
)


def _backup(doc, name):
    """Create a private, local audit snapshot before a destructive mutation."""
    path = frappe.get_site_path("private", "backups", name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.isfile(path):
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(doc.as_dict(), handle, default=str, ensure_ascii=False, indent=2)
        os.chmod(path, 0o600)
    return path


def cycle_dependencies():
    """Check every direct Link field to Crop Cycle before deletion."""
    refs = []
    for field in frappe.get_all(
        "DocField",
        filters={"fieldtype": "Link", "options": "Crop Cycle"},
        fields=["parent", "fieldname"], limit_page_length=500
    ):
        if field.parent == "Crop Cycle":
            continue
        if not frappe.db.exists("DocType", field.parent):
            continue
        try:
            hits = frappe.get_all(
                field.parent, filters={field.fieldname: OLD_CYCLE},
                fields=["name"], limit_page_length=15
            )
        except Exception as exc:
            refs.append({"doctype": field.parent, "field": field.fieldname, "error": str(exc)})
            continue
        if hits:
            refs.append({"doctype": field.parent, "field": field.fieldname,
                         "documents": [x.name for x in hits]})
    return refs


def old_cycle_status():
    if not frappe.db.exists("Crop Cycle", OLD_CYCLE):
        return {"exists": False, "name": OLD_CYCLE, "dependencies": []}
    doc = frappe.get_doc("Crop Cycle", OLD_CYCLE)
    return {
        "exists": True, "name": doc.name, "farm": doc.farm,
        "farm_block": doc.farm_block, "cycle_no": doc.cycle_no,
        "variety": doc.variety, "planting_date": str(doc.planting_date or ""),
        "dependencies": cycle_dependencies()
    }


def remove_old_cycle():
    """Delete the ONE specifically named legacy cycle only if unreferenced."""
    current = old_cycle_status()
    if not current["exists"]:
        return {"status": "already_removed", "name": OLD_CYCLE}
    if (current["farm"] != FARM or current["farm_block"] != OLD_BLOCK_ID
            or int(current["cycle_no"]) != 1 or current["variety"] != "Nammy"):
        frappe.throw("Hồ sơ vụ cũ không còn khớp A13/Nammy; dừng để tránh xóa nhầm.")
    if current["dependencies"]:
        return {"status": "blocked_by_dependencies", **current}
    doc = frappe.get_doc("Crop Cycle", OLD_CYCLE)
    backup_path = _backup(doc, "lotus_cycle_CYCLE-00001_before_delete_20261018.json")
    frappe.delete_doc("Crop Cycle", OLD_CYCLE, ignore_permissions=True)
    frappe.db.commit()
    return {"status": "removed", "name": OLD_CYCLE,
            "backup_file": backup_path, "after_exists": bool(frappe.db.exists("Crop Cycle", OLD_CYCLE))}


def _field(label, field, kind, insert_after, description):
    name = "Farm Block-" + field
    if frappe.db.exists("Custom Field", name):
        return False
    frappe.get_doc(dict(doctype="Custom Field", dt="Farm Block",
        fieldname=field, label=label, fieldtype=kind, insert_after=insert_after,
        description=description)).insert(ignore_permissions=True)
    return True


def _install_fields():
    fields = [
        ("Số cây kiểm kê Excel", "lotus_tree_count", "Int", "notes",
         "Từ bảng Excel, không phải số buồng đang trổ hoặc mật độ trồng ban đầu."),
        ("Nguồn số cây", "lotus_tree_count_source", "Data", "lotus_tree_count",
         "Nguồn và thời gian nhập số cây."),
        ("Ngày trổ dự kiến", "lotus_estimated_flowering_date", "Date", "lotus_tree_count_source",
         "Ước tính, chưa quan sát thực địa."),
        ("Ngày trồng suy ngược", "lotus_inferred_planting_date", "Date",
         "lotus_estimated_flowering_date", "Không phải ngày trồng thực tế."),
        ("Căn cứ tính ước lượng", "lotus_estimation_basis", "Small Text",
         "lotus_inferred_planting_date", "Phương pháp, độ tin cậy, ngày xác nhận."),
    ]
    count = sum(int(_field(*f)) for f in fields)
    if count:
        frappe.clear_cache(doctype="Farm Block")
    return count


def import_census():
    """Idempotent production import: persist real counts, cultivar & inferred dates separately."""
    rows = _private_rows()
    if rows is None or len(rows) != 64:
        frappe.throw("Thiếu bảng kiểm kê 64 lô trong private site. Không nhập.")
    existing = {d.block_code: d.name for d in frappe.get_all("Farm Block",
        filters={"farm": FARM}, fields=["name", "block_code"], limit_page_length=500)}
    if set(existing) != {r["code"] for r in rows}:
        frappe.throw("64 mã lô trong Excel không khớp hoàn toàn với Lotus.")
    for row in rows:
        block = frappe.get_doc("Farm Block", existing[row["code"]])
        if abs(float(block.area_ha or 0)-float(row["area_ha"])) > .03:
            frappe.throw("Lệch diện tích lô "+row["code"]+", dừng toàn bộ.")
    if not frappe.db.exists("Banana Variety", VARIETY):
        frappe.get_doc(dict(doctype="Banana Variety",
            variety_code=VARIETY, variety_name="VIP 126", active=1,
            notes="Giống do người quản lý xác nhận 18/10/2026.")).insert(ignore_permissions=True)
    new_fields = _install_fields()
    changed = 0
    counted = 0
    for row in rows:
        code = row["code"]
        doc = frappe.get_doc("Farm Block", existing[code])
        census_from_excel = int(row["tree_count"]) if row["tree_count"] else None
        if census_from_excel is not None:
            counted += 1
        updates = {"variety": VARIETY}
        # Never overwrite newer photo/manager census, or revisioned zone dates.
        # The original 64-lot private CSV remains an immutable import source.
        if census_from_excel is not None and int(doc.get("lotus_tree_count") or 0) == 0:
            updates["lotus_tree_count"] = census_from_excel
            updates["lotus_tree_count_source"] = SOURCE_NOTICE
        for field, value in updates.items():
            if str(doc.get(field) or "") != str(value or ""):
                doc.set(field, value)
                changed += 1
        if any(doc.has_value_changed(x) for x in updates):
            doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "imported", "farm": FARM, "variety": VARIETY,
        "lots": len(rows), "counted_lots": counted, "known_trees": sum(int(r["tree_count"]) for r in rows if r["tree_count"]),
        "missing_lots":len(rows)-counted,
        "zone_a_flowering_estimate": FLOWER_DATE, "inferred_planting_date":str(inferred),
        "new_fields":new_fields,"changed_field_values":changed,
        "note":"Không sửa ngày trồng thực tế; không tạo vụ đã trổ hoặc hàng bán."}