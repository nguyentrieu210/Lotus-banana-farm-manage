"""Auditable Lotus 222 census supplements from manager-provided photo boards.

Only these 5 previously-empty Farm Blocks are eligible for update. Photo
labels are not certified field inventory; explicit provenance retained.
"""
import frappe

from lotus_farm.forecast_import_preview import _private_rows, FARM
from lotus_farm.vip126_live import VARIETY

COUNTS = {
    "A1": {"count": 6830, "source": "Ảnh biển lô A1 do người dùng gửi 18/10/2026"},
    "A2": {"count": 8568, "source": "Ảnh biển lô A2 do người dùng gửi 18/10/2026"},
    "A3": {"count": 8060, "source": "Ảnh biển lô A3 do người dùng gửi 18/10/2026"},
    "A4": {"count": 8743, "source": "Ảnh biển lô A4 do người dùng gửi 18/10/2026"},
    "A12": {"count": 10148, "source": "Người quản lý xác nhận A12 18/10/2026"},
}
TOTAL_ADDITION = sum(item["count"] for item in COUNTS.values())
EXPECTED_A_TOTAL = 105632
EXPECTED_FARM_TOTAL = 269353
PROVENANCE_WARNING = (
    "Số đọc từ biển và xác nhận người quản lý, chưa kiểm kê độc lập; "
    "không thay thế số cây trồng ban đầu hoặc số cây đủ điều kiện trổ."
)


def _records():
    rows = _private_rows()
    if rows is None or len(rows) != 64:
        frappe.throw("Chưa có bảng Excel gốc đủ 64 lô trong private site.")
    index = {r["code"]: r for r in rows}
    if len(index) != 64 or any(index[c]["tree_count"] for c in COUNTS):
        frappe.throw("Bảng gốc đã thay đổi: 5 lô bổ sung không còn trống.")
    return index


def apply():
    index = _records()
    docs = {r.block_code: r.name for r in frappe.get_all(
        "Farm Block", filters={"farm": FARM},
        fields=["name", "block_code"], limit_page_length=100)}
    if set(docs) != set(index):
        frappe.throw("Danh sách 64 lô hiện tại không khớp bảng Excel.")
    pending = []
    for code, evidence in COUNTS.items():
        doc = frappe.get_doc("Farm Block", docs[code])
        current = int(doc.get("lotus_tree_count") or 0)
        source = str(doc.get("lotus_tree_count_source") or "")
        expected_source = evidence["source"]
        if doc.variety != VARIETY:
            frappe.throw("Giống lô " + code + " đã thay đổi, không nhập.")
        if abs(float(doc.area_ha or 0) - float(index[code]["area_ha"])) > .03:
            frappe.throw("Diện tích lô " + code + " không khớp Excel.")
        if current not in (0, evidence["count"]):
            frappe.throw("Lô " + code + " đã có số khác, không được tự ghi đè.")
        if current == evidence["count"] and source != expected_source:
            frappe.throw("Lô " + code + " trùng số cây nhưng nguồn khác, kiểm tra lại.")
        if current == 0:
            pending.append((doc, evidence))
    for doc, evidence in pending:
        doc.lotus_tree_count = evidence["count"]
        doc.lotus_tree_count_source = evidence["source"]
        doc.save(ignore_permissions=True)
    frappe.db.commit()
    return verify(update_count=len(pending))


def verify(update_count=None):
    index = _records()
    all_lots = frappe.get_all("Farm Block", filters={"farm": FARM},
        fields=["block_code", "lotus_tree_count", "lotus_tree_count_source"],
        limit_page_length=100)
    by_code = {x.block_code: x for x in all_lots}
    a_count = sum(int(x.lotus_tree_count or 0)
                  for x in all_lots if x.block_code.startswith("A"))
    total = sum(int(x.lotus_tree_count or 0) for x in all_lots)
    filled = sum(int(x.lotus_tree_count or 0)>0 for x in all_lots)
    errors = []
    for code, info in COUNTS.items():
        x=by_code[code]
        if int(x.lotus_tree_count or 0) != info["count"] or x.lotus_tree_count_source != info["source"]:
            errors.append(code)
    if errors or a_count != EXPECTED_A_TOTAL or total != EXPECTED_FARM_TOTAL or filled != 35:
        frappe.throw(
            "Tổng cây khu A hoặc toàn vườn không khớp: " +
            str({"A":a_count,"all":total,"filled":filled,"issues":errors}))
    result = {"status":"verified", "farm":FARM, "variety":VARIETY,
              "A_counted_lots":13,"A_trees":a_count,
              "all_counted_lots":filled,"all_missing_lots":64-filled,
              "all_trees":total,"supplemented":COUNTS,
              "source_warning":PROVENANCE_WARNING}
    if update_count is not None:
        result["updated_lots"]=update_count
    return result
