import frappe

ROLES = (
    "Lotus Farm Manager",
    "Lotus Sales Planner",
    "Lotus QC Manager",
    "Lotus Packing Supervisor",
    "Lotus Integration User",
    "Lotus Auditor",
    "Lotus Stock Reviewer",
    "Lotus Price Approver",
)


def create_roles():
    for name in ROLES:
        if not frappe.db.exists("Role", name):
            frappe.get_doc(dict(doctype="Role", role_name=name, desk_access=1)).insert(
                ignore_permissions=True
            )


def setup():
    create_roles()
    from lotus_farm.warehouse_issue import install_fields
    install_fields()
    from lotus_farm.warehouse_masters import install_fields as install_minimum_fields
    install_minimum_fields()
    from lotus_farm.warehouse_planning import install_fields as install_planning_fields
    install_planning_fields()
    from lotus_farm.timekeeping import install_fields as install_timekeeping_fields
    install_timekeeping_fields()
    from lotus_farm.hr_workspace import install_fields as install_hr_fields
    install_hr_fields()
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
    upgrade_cycle_unique_index()
    for doctype, fields in (
        ("Farm Block", ["farm", "block_code"]),
        ("Crop Cycle", ["farm_block", "farm_plot", "cycle_no"]),
        ("Farm Plot", ["farm_block", "plot_code"]),
        ("Work Team", ["farm", "team_code"]),
        ("Plot Geometry", ["farm_plot", "version"]),
        ("Work Schedule Rule", ["rule_name", "version"]),
        ("Source Import Mapping", ["mapping_name", "version"]),
        ("Warehouse Mapping", ["farm", "warehouse", "warehouse_role"]),
        ("Pack Specification", ["spec_code", "version"]),
        ("Material Norm Profile", ["profile_name", "version"]),
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


def upgrade_cycle_unique_index():
    # The old block/cycle unique key prevented independent cycles on different plots.
    # No data reassignment: blank legacy plot remains blank until explicitly mapped.
    indexes = frappe.db.sql("SHOW INDEX FROM `tabCrop Cycle`", as_dict=True)
    grouped = {}
    for row in indexes:
        if not row.Non_unique and row.Key_name != "PRIMARY":
            grouped.setdefault(row.Key_name, []).append((row.Seq_in_index, row.Column_name))
    for name, columns in grouped.items():
        if [c for _, c in sorted(columns)] == ["farm_block", "cycle_no"]:
            if not name.replace("_", "").isalnum():
                frappe.throw("Unexpected Crop Cycle index name.")
            frappe.db.sql("ALTER TABLE `tabCrop Cycle` DROP INDEX `" + name + "`")
