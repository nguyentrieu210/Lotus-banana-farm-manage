"""Import the confirmed Lotus-222 two-part weekly ribbon calendar (ISO 2026 W43-W50).

This is an explicit farm-specific operating schedule, NOT the 17-color,
5-day OneDrive reference. Both schedules are preserved in the database; old
unreferenced overlapping entries are disabled rather than deleted.
Run once as administrator from bench execute, with automatic idempotency.
"""
from datetime import date, timedelta
import frappe
from frappe.utils import getdate
from lotus_farm.controls import lock


FARM = "LOTUS-222"
START = date(2026, 10, 19)  # ISO Monday of week 43
# (period 1 color, period 2 color), actual order in each week
WEEKS = [
    ("CAM", "CAM"),
    ("DEN", "DEN"),
    ("XANH_DUONG", "XANH_DUONG"),
    ("DO_XANH_LA", "DO_XANH_LA"),
    ("TRANG_XANH_LA", "TRANG_XANH_LA"),
    ("TIM_XANH_LA", "TIM_XANH_LA"),
    ("CAM_XANH_LA", "CAM_XANH_LA"),
    ("XANH_LA_XANH_DUONG", "DEN_XANH_LA"),
]
COLORS = {
    "CAM": "Cam",
    "DEN": "Đen",
    "XANH_DUONG": "Xanh dương",
    "DO_XANH_LA": "Đỏ - Xanh lá",
    "TRANG_XANH_LA": "Trắng - Xanh lá",
    "TIM_XANH_LA": "Tím - Xanh lá",
    "CAM_XANH_LA": "Cam - Xanh lá",
    "DEN_XANH_LA": "Đen - Xanh lá",
    "XANH_LA_XANH_DUONG": "Xanh lá - Xanh dương",
}


def periods():
    for i, (first, second) in enumerate(WEEKS):
        monday = START + timedelta(days=7*i)
        week = monday.isocalendar().week
        for half, code, a, b in (
            (1, first, 0, 3),  # Monday to Thursday inclusive
            (2, second, 4, 6),  # Friday to Sunday inclusive
        ):
            yield {
                "week_year": 2026, "week_number": week, "week_half": str(half),
                "color_code": code, "color_label": COLORS[code],
                "valid_from": str(monday + timedelta(days=a)),
                "valid_to": str(monday + timedelta(days=b)),
                "tag_code": f"LOTUS-222:W2026-{week:02d}-P{half}:{code}",
                "display_name": f"{COLORS[code]} · Đợt {half} · Tuần {week}/2026",
            }


def _referenced(tag_name):
    for dt, field in (("Bunch Operation", "bunch_tag"),
                      ("Fruit Measurement", "ribbon_color"),
                      ("Harvest Actual", "ribbon_color")):
        if frappe.db.exists(dt, {field: tag_name}):
            return True
    return False


def preview():
    rows = list(periods())
    low, high = rows[0]["valid_from"], rows[-1]["valid_to"]
    overlapping = frappe.get_all(
        "Bunch Tag", filters={"farm": FARM, "enabled": 1,
                              "valid_from": ["<=", high]},
        fields=["name", "tag_code", "source_kind", "valid_from", "valid_to"],
        limit_page_length=5000)
    overlapping = [x for x in overlapping if x.valid_to and str(x.valid_to) >= low]
    old = [x for x in overlapping if x.source_kind != "Lotus Weekly"]
    conflict = [x.tag_code for x in old if _referenced(x.name)]
    return dict(farm=FARM, start=low, end=high, periods=rows,
                replacing_unused=len(old), conflicts=conflict,
                existing_weekly=len(overlapping)-len(old))


def apply():
    frappe.only_for("System Manager")
    lock("Farm", FARM)
    plan = preview()
    if plan["conflicts"]:
        frappe.throw("Có màu dây cũ đã gắn chứng từ, không được thay: " + ", ".join(plan["conflicts"]))
    existing = {x.tag_code: x for x in frappe.get_all("Bunch Tag", filters={"farm": FARM, "source_kind": "Lotus Weekly"},
        fields=["name","tag_code","color_code","color_label","valid_from","valid_to","week_year","week_number","week_half","enabled"],
        limit_page_length=5000)}
    # Verify before mutating old schedule: repeat runs cannot silently change a dated tag.
    for row in plan["periods"]:
        old = existing.get(row["tag_code"])
        if old and any(str(old.get(k) or "") != str(row[k]) for k in
                       ("color_code","color_label","valid_from","valid_to","week_year","week_number","week_half")):
            frappe.throw("Kỳ màu dây đã lưu khác dữ liệu import: " + row["tag_code"])
    for rec in frappe.get_all("Bunch Tag", filters={"farm": FARM, "enabled": 1,
            "valid_from":["<=",plan["end"]]}, fields=["name","valid_to","source_kind"], limit_page_length=5000):
        if rec.source_kind == "Lotus Weekly" or not rec.valid_to or str(rec.valid_to)<plan["start"]:
            continue
        if _referenced(rec.name):
            frappe.throw("Kỳ màu dây cũ đã có phiếu, không thể ngừng sử dụng.")
        doc=frappe.get_doc("Bunch Tag",rec.name)
        doc.enabled=0
        doc.save()
    created=0
    for row in plan["periods"]:
        if row["tag_code"] in existing:
            if not existing[row["tag_code"]].enabled:
                frappe.throw("Kỳ màu dây mới bị vô hiệu hóa: "+row["tag_code"])
            continue
        doc=frappe.get_doc({"doctype":"Bunch Tag","farm":FARM,
            "period_basis":"Cut Bud","source_kind":"Lotus Weekly",
            "enabled":1,**row})
        doc.insert()
        created+=1
    frappe.db.commit()
    print("Imported Lotus weekly ribbon schedule",dict(farm=FARM,created=created,
          existing=len(plan["periods"])-created,disabled_old=plan["replacing_unused"],
          start=plan["start"],end=plan["end"]))
    return dict(created=created,disabled_old=plan["replacing_unused"],periods=len(plan["periods"]))
