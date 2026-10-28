"""Date-aware ribbon-color catalogue for field cut-bud tagging.

Manual periods are separate Bunch Tag records. Historical referenced tags are
never rewritten when the next rotation starts. Approved OneDrive programs
continue to use their existing versioned generate_tags workflow.
"""
import frappe
from frappe.utils import getdate
from lotus_farm.bunch_tag_rules import overlaps, manual_tag_code
from lotus_farm.controls import lock, require_role
from lotus_farm.onedrive_workspace import library


def _farm_access(farm):
    if not farm:
        frappe.throw("Chọn vườn trước khi xem lịch màu dây.")
    doc = frappe.get_doc("Farm", farm)
    doc.check_permission("read")
    return doc


@frappe.whitelist()
def catalog(farm):
    _farm_access(farm)
    if not frappe.has_permission("Bunch Tag", "read"):
        frappe.throw("Không có quyền xem danh mục màu dây.", frappe.PermissionError)
    source, _ = library()
    rows = frappe.get_list(
        "Bunch Tag",
        filters={"farm": farm},
        fields=["name", "tag_code", "display_name", "color_code", "valid_from",
                "valid_to", "enabled", "period_basis", "process_adoption", "source_kind"],
        order_by="valid_from desc, name desc",
        limit_page_length=3000,
    )
    programs = []
    if frappe.has_permission("Lotus Process Adoption", "read"):
        programs = frappe.get_list(
            "Lotus Process Adoption",
            filters={"farm": farm, "approval_state": "Approved"},
            fields=["name", "version", "valid_from", "valid_to", "color_anchor",
                    "color_anchor_code", "color_period_days"],
            order_by="valid_from desc",
            limit_page_length=100,
        )
    return {
        "rows": rows,
        "colors": [{"code": c["code"], "label": c["label"]} for c in source["colors"]],
        "programs": programs,
        "can_create": bool(frappe.has_permission("Bunch Tag", "create")),
        "notice": "Thư viện tham chiếu hiện có " + str(len(source["colors"])) +
                  " màu; không tự giả định 12 màu hay số ngày áp dụng của Lotus.",
    }


@frappe.whitelist(methods=["POST"])
def add_manual_period(farm, color_code, valid_from, valid_to):
    """Create a new dated tag, not an in-place edit of an earlier tagged cohort."""
    require_role("Lotus Farm Manager", "System Manager")
    _farm_access(farm)
    if not frappe.has_permission("Bunch Tag", "create"):
        frappe.throw("Không có quyền thêm kỳ màu dây.", frappe.PermissionError)
    source, _ = library()
    palette = {str(c["code"]): c["label"] for c in source["colors"]}
    if color_code not in palette:
        frappe.throw("Chọn mã màu có trong danh mục tham chiếu.")
    try:
        start, end = getdate(valid_from), getdate(valid_to)
    except (ValueError, TypeError):
        frappe.throw("Ngày bắt đầu và kết thúc phải hợp lệ.")
    if end < start or (end - start).days > 30:
        frappe.throw("Ngày kết thúc phải từ ngày bắt đầu đến tối đa 30 ngày sau.")
    lock("Farm", farm)
    programs = frappe.get_all(
        "Lotus Process Adoption",
        filters={"farm": farm, "approval_state": "Approved", "valid_from": ["<=", end]},
        fields=["valid_from", "valid_to"],
    )
    if any(overlaps(start, end, p.valid_from, p.valid_to) for p in programs):
        frappe.throw("Vườn đã có lịch màu theo quy trình được duyệt. Hãy tạo kỳ màu từ chương trình đó, không lập thêm lịch thủ công trùng ngày.")
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
        "display_name": palette[color_code] + " (" + str(start) + " – " + str(end) + ")",
        "farm": farm, "color_code": color_code, "period_basis": "Cut Bud",
        "valid_from": str(start), "valid_to": str(end), "enabled": 1,
    })
    doc.insert()
    return {"name": doc.name, "tag_code": doc.tag_code}
