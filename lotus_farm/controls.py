from contextlib import contextmanager
from contextvars import ContextVar
from zoneinfo import ZoneInfo
import frappe
from frappe.utils import getdate, get_datetime, get_system_timezone

from lotus_farm.rules import RuleError, quantity, integer_quantity


def require_role(*roles):
    if frappe.session.user == "Administrator":
        return
    if not set(roles).intersection(frappe.get_roles()):
        frappe.throw("This action requires: " + ", ".join(roles), frappe.PermissionError)


def lock(doctype, name):
    table = frappe.qb.DocType(doctype)
    rows = frappe.qb.from_(table).select(table.name).where(table.name == name).for_update().run()
    if not rows:
        frappe.throw(f"{doctype} {name} does not exist.")


def positive(value, label):
    try:
        return float(quantity(value, label, positive=True))
    except RuleError as exc:
        frappe.throw(str(exc))


def validate_version(doc, key, roles):
    before = doc.get_doc_before_save()
    if before and before.approval_state == "Approved":
        # Approved assumptions are append-only. Retire via new version/effective range, not edits.
        ignored = {"modified", "modified_by", "__last_sync_on"}
        for field in doc.meta.fields:
            if (
                field.fieldtype not in ("Section Break", "Column Break", "Tab Break")
                and field.fieldname not in ignored
            ):
                if doc.as_dict().get(field.fieldname) != before.as_dict().get(field.fieldname):
                    frappe.throw("Approved versions are immutable. Create a new version.")
    if int(doc.version or 0) < 1:
        frappe.throw("Version must be positive.")
    if doc.approval_state == "Approved" and (not before or before.approval_state != "Approved"):
        require_role(*roles)
    if doc.get("valid_to") and getdate(doc.valid_to) < getdate(doc.valid_from):
        frappe.throw("Valid To cannot precede Valid From.")
    duplicate = frappe.db.exists(
        doc.doctype, {key: doc.get(key), "version": doc.version, "name": ["!=", doc.name]}
    )
    if duplicate:
        frappe.throw("This key/version already exists.")


def validate_item(item, *, batched=False):
    record = frappe.get_doc("Item", item)
    record.check_permission("read")
    if record.disabled or not record.is_stock_item or record.stock_uom != "Kg":
        frappe.throw("Lotus inventory Items must be active stock Items with stock UOM Kg.")
    if batched and (not record.has_batch_no or record.has_serial_no):
        frappe.throw("Lotus stock bridge requires batched, non-serialized Items.")
    return record


def validate_warehouse(name, company):
    warehouse = frappe.get_doc("Warehouse", name)
    warehouse.check_permission("read")
    if warehouse.company != company or warehouse.is_group or warehouse.disabled:
        frappe.throw("Warehouse must be an active leaf of the same Company.")


def check_farm(doc, method=None):
    if doc.doctype=='Farm' and doc.is_new() and command_allowed(doc,'create_attendance_farm'):return
    farm = doc.name if doc.doctype == "Farm" else doc.get("farm")
    if farm and not farm_allowed(farm):
        frappe.throw("You do not have access to this Farm.", frappe.PermissionError)


def farm_allowed(farm, user=None):
    user = user or frappe.session.user
    if user == "Administrator":
        return True
    allowed = frappe.get_all("User Permission", filters={"user": user, "allow": "Farm"}, pluck="for_value")
    # Business roles fail closed: a farm grant is mandatory even for System Manager.
    return farm in allowed


def farm_permission(doc, user=None, permission_type=None):
    farm = doc.name if doc.doctype == "Farm" else doc.get("farm")
    if not farm:
        return True
    if not farm_allowed(farm, user):
        return False
    # Frappe v16 treats any falsy hook result as denial; role/User Permissions
    # are independently evaluated after this controller restriction.
    return True


def query_condition(doctype, user=None):
    user = user or frappe.session.user
    if user == "Administrator":
        return ""
    allowed = frappe.get_all("User Permission", filters={"user": user, "allow": "Farm"}, pluck="for_value")
    if not allowed:
        return "1=0"
    column = "name" if doctype == "Farm" else "farm"
    values = ",".join(frappe.db.escape(value) for value in allowed)
    return f"`tab{doctype}`.`{column}` in ({values})"


def preserve_lineage(doc, method=None):
    before = doc.get_doc_before_save()
    if not before:
        return
    dependencies = {
        "Crop Cycle": (
            "crop_cycle",
            [
                "Sucker Selection Batch",
                "Bunch Operation",
                "Harvest Forecast",
                "Harvest Actual",
                "Defect Inspection",
            ],
            ["farm", "farm_block", "farm_plot", "cycle_no", "parent_cycle", "variety", "planting_date"],
        ),
        "Sucker Selection Batch": (
            "sucker_selection_batch",
            ["Bunch Operation", "Harvest Forecast", "Harvest Actual", "Defect Inspection"],
            ["farm", "farm_block", "crop_cycle", "selection_date", "selected_sucker_qty"],
        ),
        "Farm Block": ("farm_block", ["Crop Cycle", "Farm Plot"], ["farm", "block_code"]),
        "Farm": ("farm", ["Farm Block"], ["company"]),
    }
    field, targets, immutable = dependencies[doc.doctype]
    if any(doc.get(f) != before.get(f) for f in immutable) and any(
        frappe.db.exists(target, {field: doc.name}) for target in targets
    ):
        frappe.throw("Used production identities cannot be edited. Create a new cycle/cohort instead.")


def validate_operation_date(doc, method=None):
    date_field = {
        "Bunch Operation": "operation_date",
        "Harvest Actual": "harvest_date",
        "Defect Inspection": "inspection_date",
    }[doc.doctype]
    on_date = getdate(doc.get(date_field))
    cycle = frappe.get_doc("Crop Cycle", doc.crop_cycle)
    if cycle.planting_date and on_date < getdate(cycle.planting_date):
        frappe.throw("Transaction date precedes planting.")
    if doc.sucker_selection_batch:
        selection = frappe.db.get_value(
            "Sucker Selection Batch", doc.sucker_selection_batch, "selection_date"
        )
        if on_date < getdate(selection):
            frappe.throw("Transaction date precedes sucker selection.")
    if (
        doc.doctype == "Bunch Operation"
        and doc.expected_harvest_date
        and getdate(doc.expected_harvest_date) < on_date
    ):
        frappe.throw("Expected harvest cannot precede the operation.")


_authorized_commands = ContextVar("lotus_authorized_commands", default=frozenset())


def command_allowed(doc, action):
    return (doc.doctype, id(doc), action) in _authorized_commands.get()


def validate_calibration_evidence(doc):
    previous = doc.get_doc_before_save()
    fields = ('calibration_json', 'calibration_hash')
    changed = any((doc.get(f) or None) != (previous.get(f) or None if previous else None) for f in fields)
    if changed and not command_allowed(doc, 'calibrated_profile'):
        frappe.throw('Calibration evidence can only be created by the measured proposal command.')


@contextmanager
def command(doc, action):
    token = _authorized_commands.set(_authorized_commands.get() | {(doc.doctype, id(doc), action)})
    try:
        yield
    finally:
        _authorized_commands.reset(token)


def local_timestamp(value):
    timestamp = get_datetime(value)
    if timestamp.tzinfo:
        timestamp = timestamp.astimezone(ZoneInfo(get_system_timezone())).replace(tzinfo=None)
    return timestamp


def whole_count(value, label):
    try:
        return integer_quantity(value, label)
    except RuleError as exc:
        frappe.throw(str(exc))
