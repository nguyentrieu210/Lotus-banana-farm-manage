"""Permission-checked forecast profile editing and explicit approval."""
import json
import frappe
from lotus_farm.controls import lock, require_role
from lotus_farm.forecast_parameters import DEFAULTS

DOCTYPE = "Lotus Block Forecast Profile"
EDITABLE = (*DEFAULTS, "profile_name", "farm_block", "valid_from", "valid_to", "source_reference", "notes")


def install_units():
    """Count units used by Book2 care jobs; preserve all existing UOM records."""
    for unit in ("Buồng", "Cây"):
        if not frappe.db.exists("UOM", unit):
            frappe.get_doc(dict(doctype="UOM", uom_name=unit, must_be_whole_number=1)).insert(ignore_permissions=True)


def _farm(name):
    frappe.get_doc("Farm", name).check_permission("read")


def _current(doc, modified):
    if not modified or str(doc.modified) != str(modified):
        frappe.throw("Bộ thông số vừa thay đổi. Tải lại trước khi lưu.")


@frappe.whitelist()
def list_profiles(farm):
    _farm(farm)
    rows = frappe.get_list(DOCTYPE, filters={"farm": farm}, fields=["name"], order_by="version desc", limit_page_length=1000)
    documents = []
    for row in rows:
        doc = frappe.get_doc(DOCTYPE, row.name)
        doc.check_permission("read")
        doc.apply_fieldlevel_read_permissions()
        documents.append(doc.as_dict())
    return dict(rows=documents, defaults=DEFAULTS,
                can_create=frappe.has_permission(DOCTYPE, "create"),
                can_write=frappe.has_permission(DOCTYPE, "write"),
                can_approve=frappe.has_permission(DOCTYPE, "write") and
                    (frappe.session.user == "Administrator" or bool(set(frappe.get_roles()) & {"System Manager", "Lotus Farm Manager"})))


@frappe.whitelist(methods=["POST"])
def save_draft(farm, values, name=None, modified=None):
    _farm(farm)
    lock("Farm", farm)
    values = json.loads(values) if isinstance(values, str) else values
    if not isinstance(values, dict):
        frappe.throw("Thông số không hợp lệ.")
    if name:
        doc = frappe.get_doc(DOCTYPE, name)
        doc.check_permission("write")
        if doc.farm != farm:
            frappe.throw("Bộ thông số thuộc vườn khác.")
        _current(doc, modified)
        if doc.approval_state != "Draft":
            frappe.throw("Bộ thông số đã duyệt được khóa. Tạo phiên bản mới.")
    else:
        if not frappe.has_permission(DOCTYPE, "create"):
            frappe.throw("Không có quyền tạo bộ thông số.", frappe.PermissionError)
        block = values.get("farm_block") or ""
        versions = frappe.get_all(DOCTYPE, filters={"farm": farm, "farm_block": block}, fields=["version"], limit_page_length=0)
        doc = frappe.new_doc(DOCTYPE)
        doc.update(dict(farm=farm, version=max([int(v.version or 0) for v in versions] or [0]) + 1))
    for field in EDITABLE:
        if field in values:
            doc.set(field, (values[field] or None) if field == "farm_block" else values[field])
    doc.approval_state = "Draft"
    doc.save()
    return dict(name=doc.name, version=doc.version, modified=doc.modified)


@frappe.whitelist(methods=["POST"])
def approve(name, modified):
    require_role("System Manager", "Lotus Farm Manager")
    doc = frappe.get_doc(DOCTYPE, name)
    doc.check_permission("write")
    _farm(doc.farm)
    lock("Farm", doc.farm)
    doc.reload()
    _current(doc, modified)
    if doc.approval_state != "Draft":
        frappe.throw("Bộ thông số đã được duyệt.")
    doc.approval_state = "Approved"
    doc.save()
    return dict(name=doc.name, version=doc.version, approval_state=doc.approval_state)
