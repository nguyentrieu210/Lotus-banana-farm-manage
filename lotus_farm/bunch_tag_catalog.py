"""Date-aware ribbon-color catalogue for field cut-bud tagging.

Manual periods are separate Bunch Tag records. Historical referenced tags are
never rewritten when the next rotation starts.
"""
import frappe
from datetime import timedelta
from frappe.utils import getdate, cint
from lotus_farm.bunch_tag_rules import overlaps, manual_tag_code
from lotus_farm.controls import lock, require_role
from lotus_farm.ribbon_cycle import COLORS


def _farm_access(farm):
    if not farm:
        frappe.throw("Chọn vườn trước khi xem lịch màu dây.")
    doc = frappe.get_doc("Farm", farm)
    doc.check_permission("read")
    return doc


@frappe.whitelist()
def catalog(farm, include_disabled=0):
    _farm_access(farm)
    if not frappe.has_permission("Bunch Tag", "read"):
        frappe.throw("Không có quyền xem danh mục màu dây.", frappe.PermissionError)
    weekly_mode = bool(frappe.db.exists("Bunch Tag", {
        "farm": farm, "source_kind": "Lotus Weekly", "enabled": 1
    }))
    filters = {"farm": farm}
    if not cint(include_disabled):
        filters["enabled"] = 1
        if weekly_mode:
            filters["source_kind"] = "Lotus Weekly"
    rows = frappe.get_list(
        "Bunch Tag",
        filters=filters,
        fields=["name", "tag_code", "display_name", "color_code", "valid_from",
                "valid_to", "enabled", "period_basis", "source_kind",
                "color_label", "week_year", "week_number", "week_half"],
        order_by="valid_from desc, name desc",
        limit_page_length=3000,
    )
    for row in rows:
        if row.source_kind == "Lotus Weekly" and row.valid_from:
            monday = getdate(row.valid_from) - timedelta(days=getdate(row.valid_from).weekday())
            row["week_from"] = str(monday)
            row["week_to"] = str(monday + timedelta(days=6))
    # The twelve colours of the Lotus cycle, and any other colour the listed periods carry.
    palette = {**COLORS, **{r.color_code: r.color_label for r in rows if r.color_code and r.color_label}}
    return {
        "rows": rows,
        "colors": [{"code": code, "label": label} for code, label in sorted(palette.items())],
        "can_create": bool(frappe.has_permission("Bunch Tag", "create")) and not weekly_mode,
        "weekly_mode": weekly_mode,
        "notice": ("Lịch Lotus áp dụng theo tuần 7 ngày (thứ Hai đến Chủ nhật); "
                   "đợt 1 và 2 để ghi nhận đầu và cuối tuần. "
                   "Lịch tham chiếu 5 ngày đã ngừng áp dụng tại vườn này."
                   if weekly_mode else
                   "Vườn chưa có lịch màu Lotus theo tuần; đang hiển thị các kỳ màu lập thủ công."),
    }


@frappe.whitelist(methods=["POST"])
def add_manual_period(farm, color_code, valid_from, valid_to):
    """Create a new dated tag, not an in-place edit of an earlier tagged cohort."""
    require_role("Lotus Farm Manager", "System Manager")
    _farm_access(farm)
    if not frappe.has_permission("Bunch Tag", "create"):
        frappe.throw("Không có quyền thêm kỳ màu dây.", frappe.PermissionError)
    if color_code not in COLORS:
        frappe.throw("Chọn màu có trong bảng màu dây.")
    if not valid_from or not valid_to:
        frappe.throw("Nhập đủ ngày bắt đầu và ngày kết thúc.")
    try:
        start, end = getdate(valid_from), getdate(valid_to)
    except (ValueError, TypeError):
        frappe.throw("Ngày bắt đầu và kết thúc phải hợp lệ.")
    if end < start:
        frappe.throw("Ngày kết thúc không được trước ngày bắt đầu.")
    lock("Farm", farm)
    active = frappe.get_all(
        "Bunch Tag",
        filters={"farm": farm, "enabled": 1, "period_basis": "Cut Bud",
                 "valid_from": ["<=", end]},
        fields=["name", "valid_from", "valid_to"],
    )
    if any(overlaps(start, end, row.valid_from, row.valid_to) for row in active):
        frappe.throw("Khoảng ngày đã có màu dây đang sử dụng. Không thể xếp chồng hai màu.")
    doc = frappe.get_doc({
        "doctype": "Bunch Tag",
        "tag_code": manual_tag_code(farm, start, color_code),
        "display_name": COLORS[color_code] + " (" + str(start) + " – " + str(end) + ")",
        "farm": farm, "color_code": color_code, "period_basis": "Cut Bud",
        "valid_from": str(start), "valid_to": str(end), "enabled": 1,
    })
    doc.insert()
    return {"name": doc.name, "tag_code": doc.tag_code}
