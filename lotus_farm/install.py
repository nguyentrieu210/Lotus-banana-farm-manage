import frappe

ROLES = (
    "Lotus Work Journal Clerk",
    "Lotus Farm Manager",
    "Lotus Sales Planner",
    "Lotus QC Manager",
    "Lotus Packing Supervisor",
    "Lotus Integration User",
    "Lotus Auditor",
    "Lotus Stock Reviewer",
    "Lotus Price Approver",
    "Lotus Team Leader",
    "Lotus Field Supervisor",
    "Lotus Field Inspector",
)


def create_roles():
    for name in ROLES:
        if not frappe.db.exists("Role", name):
            frappe.get_doc(dict(doctype="Role", role_name=name, desk_access=1)).insert(
                ignore_permissions=True
            )


def set_brand():
    """Show the Lotus logo on /login and the Desk navbar. Frappe uses the first app_logo_url hook (Frappe's own)
    when several apps are installed, so set Navbar Settings once; an administrator's own logo is kept."""
    if not frappe.db.get_single_value("Navbar Settings", "app_logo"):
        frappe.db.set_single_value("Navbar Settings", "app_logo", "/assets/lotus_farm/images/lotus-agritech.jpg")


def setup():
    from lotus_farm.field_report import install_fields as install_field_report_fields
    install_field_report_fields()
    from lotus_farm.localization import install_translations
    install_translations()
    create_roles()
    from lotus_farm.forecast_profiles import install_units
    install_units()
    set_brand()
    from frappe.permissions import add_permission, update_permission_property
    for _dt in ("Farm", "Farm Block", "Work Team", "Work Type"):
        for _role in ("Lotus Team Leader", "Lotus Field Supervisor"):
            add_permission(_dt, _role)
            update_permission_property(_dt, _role, 0, "read", 1)
    from lotus_farm.warehouse_issue import install_fields
    install_fields()
    from lotus_farm.warehouse_masters import install_fields as install_minimum_fields
    install_minimum_fields()
    from lotus_farm.warehouse_planning import install_fields as install_planning_fields
    install_planning_fields()
    from lotus_farm.warehouse_buying_lite import install_fields as install_buying_fields
    install_buying_fields()
    from lotus_farm.warehouse_access import install_roles as install_warehouse_roles
    install_warehouse_roles()
    from lotus_farm.timekeeping import install_fields as install_timekeeping_fields
    install_timekeeping_fields()
    from lotus_farm.work_allowance import install_fields as install_allowance_fields
    install_allowance_fields()
    from lotus_farm.work_allowance import seed_rates
    seed_rates()
    from lotus_farm.hr_workspace import install_fields as install_hr_fields
    install_hr_fields()
    from lotus_farm.hr_setup import install_fields as install_org_fields
    install_org_fields()
    from lotus_farm.digital_signature import install_fields as install_signature_fields
    install_signature_fields()
    from lotus_farm.purchase_proposal import install_fields as install_proposal_fields
    install_proposal_fields()
    from lotus_farm.hr_payroll import install_fields as install_payroll_fields
    install_payroll_fields()
    from lotus_farm.shift_admin import install_fields as install_shift_fields
    install_shift_fields()
    from lotus_farm.farm_land import install as install_land
    install_land()
    from lotus_farm.finance.setup import install as install_finance
    install_finance()
    from lotus_farm.finance.asset_setup import install as install_assets
    install_assets()
    from lotus_farm.procurement_setup import install as install_procurement
    install_procurement()
    from lotus_farm.issue_request import install_fields as install_issue_request_fields
    install_issue_request_fields()
    for doctype, fields in (
        ("Farm Block", ["farm", "block_code"]),
        ("Work Team", ["farm", "team_code"]),
        ("Work Schedule Rule", ["farm", "rule_name", "version"]),
        ("Warehouse Mapping", ["farm", "warehouse", "warehouse_role"]),
    ):
        frappe.db.add_unique(doctype, fields)
    # ERPNext standard grants remain untouched. Lotus-specific roles only extend farm masters.
    for doctype in (
        "Farm",
        "Farm Block",
        "Banana Variety",
        "Bunch Tag",
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
                frappe.throw("Trung tâm chi phí phải thuộc công ty của vườn.")
