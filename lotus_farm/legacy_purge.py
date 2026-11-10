"""Dọn 76 bảng đời cũ của mảng vườn (spec 002, US7; danh sách và lý do ở specs/002-cham-soc-thu-hoach-du-thu/cleanup.md).

preview() only reads, so it can run on the live site long before anything is removed:
- rows in each legacy table (and the size of the table, for the archive);
- custom fields of kept documents that point at a legacy table (the "Vụ" accounting dimension lotus_crop_cycle,
  lotus_work_plan, lotus_harvest_lot, the Material Requirement link…) with how many values they hold, and how many of
  those sit on posted documents;
- closed timekeeping periods whose month had Labor Allocation rows (their payroll was computed with them);
- the block list: a legacy value on a posted accounting document stops the purge until the owner decides, the books
  are never edited to make room.
commit() (archive to JSON with counts and checksums, then data, custom fields and dimensions, then DocTypes) comes
with the second deployment of spec 002.

bench --site frontend execute lotus_farm.legacy_purge.preview
"""
import frappe

LEGACY = {
    "A": ["Bunch Operation", "Bunch Cancellation", "Sucker Selection Batch", "Planting Event", "Crop Cycle", "Cycle Closing Report", "Field Capture",
          "Field Todo", "Daily Work Plan", "Daily Work Plan Line", "Daily Work Result", "Work Actual Labor", "Labor Allocation", "Daily Labor Summary",
          "Daily Production Close", "Daily Close Check", "Disease Observation", "Farm Plot", "Plot Geometry", "Legacy Cycle Plot Mapping", "Work Category",
          "Lotus Bunch Event"],
    "B": ["Harvest Actual", "Harvest Lot", "Harvest Lot Source", "Harvest Profile", "Incoming Quality Inspection", "Defect Inspection",
          "Defect Inspection Line", "Defect Reason", "Quality Defect Group", "Quality Standard", "Quality Standard Parameter", "Quality Measurement",
          "Production Loss Detail", "Fruit Measurement", "Fruit Measurement Sample", "Product Grade", "Pack Specification", "Packout Run",
          "Packout Run Source", "Packout Output", "Packout Profile", "Secondary Product Type", "Secondary Product Movement", "Scale Device",
          "Scale Reading"],
    "C": ["Harvest Forecast", "Forecast Allocation", "Forecast Output Plan", "Forecast Source Claim", "Supply Reconciliation",
          "Lotus Cut Forecast Profile", "Lotus Cut Journal Entry", "Lotus Cut Journal Import", "Plan Cohort", "Lotus Handover Cohort",
          "Material Norm Profile", "Material Norm Line", "Norm Basis", "Material Requirement", "Material Requirement Line", "Material Consumption",
          "Material Recovery"],
    "D": ["OneDrive Feed", "Source File Registry", "Source Import Batch", "Source Import Mapping", "Source Import Row", "Source Inventory Item",
          "Source Mapping Field", "Integration Event", "Integration Task", "Lotus Process Adoption", "Legacy Organization Map",
          "Cancellation Reason Alias"],
}
ALL = [name for group in LEGACY.values() for name in group]
# Documents whose posted rows are part of the books: a legacy value on one of them blocks the purge.
ACCOUNTING = {"GL Entry", "Journal Entry", "Journal Entry Account", "Stock Entry", "Stock Entry Detail", "Purchase Invoice", "Purchase Invoice Item",
              "Purchase Receipt", "Purchase Receipt Item", "Sales Invoice", "Sales Invoice Item", "Delivery Note", "Delivery Note Item", "Payment Entry",
              "Stock Ledger Entry", "Asset", "Asset Capitalization", "Landed Cost Voucher"}


def _rows(doctype):
    if not frappe.db.table_exists(doctype):
        return None
    return frappe.db.count(doctype)


def _size(doctype):
    row = frappe.db.sql("""select coalesce(data_length, 0) + coalesce(index_length, 0) from information_schema.tables
                           where table_schema = database() and table_name = %s""", f"tab{doctype}")
    return int(row[0][0]) if row else 0


def _legacy_fields():
    """Custom fields of kept DocTypes that link to a legacy table, plus the accounting dimensions built on one."""
    found = {}
    for f in frappe.get_all("Custom Field", filters={"fieldtype": ["in", ["Link", "Dynamic Link", "Table", "Table MultiSelect"]], "options": ["in", ALL]},
                            fields=["dt", "fieldname", "options"], limit_page_length=0):
        if f.dt not in ALL:
            found[(f.dt, f.fieldname)] = f.options
    if frappe.db.exists("DocType", "Accounting Dimension"):
        for d in frappe.get_all("Accounting Dimension", filters={"document_type": ["in", ALL]}, fields=["fieldname", "document_type"]):
            for f in frappe.get_all("Custom Field", filters={"fieldname": d.fieldname}, fields=["dt"], limit_page_length=0):
                found[(f.dt, d.fieldname)] = d.document_type
    return found


def _values(dt, fieldname):
    if not frappe.db.table_exists(dt) or not frappe.db.has_column(dt, fieldname):
        return 0, 0
    table = f"`tab{dt}`"
    total = frappe.db.sql(f"select count(*) from {table} where ifnull(`{fieldname}`, '') != ''")[0][0]
    if dt == "GL Entry" or dt == "Stock Ledger Entry":
        posted = frappe.db.sql(f"select count(*) from {table} where ifnull(`{fieldname}`, '') != '' and is_cancelled = 0")[0][0]
    elif frappe.db.has_column(dt, "docstatus"):
        posted = frappe.db.sql(f"select count(*) from {table} where ifnull(`{fieldname}`, '') != '' and docstatus = 1")[0][0]
    else:
        posted = 0
    return int(total), int(posted)


def _payroll_months():
    """Closed timekeeping periods whose month had submitted Labor Allocation rows."""
    if not frappe.db.table_exists("Labor Allocation") or not frappe.db.table_exists("Lotus Timekeeping Period"):
        return []
    months = {r[0] for r in frappe.db.sql("select distinct date_format(posting_date, '%%Y-%%m') from `tabLabor Allocation` where docstatus = 1")}
    return [dict(p) for p in frappe.get_all("Lotus Timekeeping Period", filters={"status": "Closed"}, fields=["name", "company", "month"],
                                             limit_page_length=0) if p.month in months]


@frappe.whitelist()
def preview():
    """Counts and checks only; writes nothing."""
    frappe.only_for("System Manager")
    tables = []
    for group, names in LEGACY.items():
        for name in names:
            rows = _rows(name)
            tables.append({"group": group, "doctype": name, "exists": rows is not None, "rows": rows or 0, "bytes": _size(name) if rows is not None else 0})
    fields, block = [], []
    for (dt, fieldname), target in sorted(_legacy_fields().items()):
        total, posted = _values(dt, fieldname)
        fields.append({"doctype": dt, "fieldname": fieldname, "points_to": target, "values": total, "on_posted": posted})
        if posted and dt in ACCOUNTING:
            block.append(f"{dt}.{fieldname} ({target}) có giá trị trên {posted} chứng từ đã ghi sổ: chủ vườn quyết định trước khi gỡ.")
    payroll = _payroll_months()
    for p in payroll:
        block.append(f"Kỳ công {p['month']} của {p['company']} đã khóa và có dùng Labor Allocation: giữ số đã tính, xem lại trước khi xóa bảng.")
    result = {"tables": tables, "table_count": len(tables), "rows": sum(t["rows"] for t in tables), "bytes": sum(t["bytes"] for t in tables),
              "with_data": [t["doctype"] for t in tables if t["rows"]], "fields": fields, "payroll_periods": payroll, "block": block}
    print(frappe.as_json({k: v for k, v in result.items() if k != "tables"}, indent=1))
    return result
