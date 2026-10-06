import frappe

ROLES = (
    "Lotus Farm Manager",
    "Lotus Sales Planner",
    "Lotus QC Manager",
    "Lotus Packing Supervisor",
    "Lotus Integration User",
    "Lotus Auditor",\n    "Lotus Stock Reviewer",
)


def create_roles():
    for name in ROLES:
        if not frappe.db.exists("Role", name):
            frappe.get_doc(dict(doctype="Role", role_name=name, desk_access=1)).insert(
                ignore_permissions=True
            )


def setup():
    create_roles()
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    create_custom_fields(
        {
            "Stock Entry": [
                dict(
                    fieldname="lotus_packout_run",
                    label="Lotus Packout Run",
                    fieldtype="Link",
                    options="Packout Run",
                    no_copy=1,
                    insert_after="purpose",
                )
            ]
        }
    )
    for doctype, fields in (
        ("Farm Block", ["farm", "block_code"]),
        ("Crop Cycle", ["farm_block", "cycle_no"]),
        ("Harvest Profile", ["profile_name", "version"]),
        ("Quality Standard", ["standard_code", "version"]),
        ("Packout Profile", ["profile_name", "version"]),
    ):
        frappe.db.add_unique(doctype, fields)
    # ERPNext standard grants remain untouched. Lotus-specific roles only extend farm masters.
    from frappe.permissions import add_permission, update_permission_property

    for doctype in (
        "Farm",
        "Farm Block",
        "Crop Cycle",
        "Sucker Selection Batch",
        "Banana Variety",
        "Defect Reason",
    ):
        for role in ROLES:
            add_permission(doctype, role)
            update_permission_property(doctype, role, 0, "read", 1)
            if role == "Lotus Farm Manager":
                for action in ("create", "write"):
                    update_permission_property(doctype, role, 0, action, 1)


def validate_reference_company(doc, method=None):
    if doc.doctype != "Farm":
        return
    from lotus_farm.controls import validate_warehouse

    for field in doc.meta.fields:
        value = doc.get(field.fieldname)
        if field.options == "Warehouse" and value:
            validate_warehouse(value, doc.company)
        if field.options == "Cost Center" and value:
            if frappe.db.get_value("Cost Center", value, "company") != doc.company:
                frappe.throw("Cost Center must belong to the Farm Company.")
