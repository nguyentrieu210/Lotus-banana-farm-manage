"""Dọn 76 bảng đời cũ của mảng vườn (spec 002, US7; danh sách và lý do ở specs/002-cham-soc-thu-hoach-du-thu/cleanup.md).

preview() only reads:
- rows in each legacy table (and the size of the table, for the archive);
- fields of kept documents that point at a legacy table (the "Vụ" accounting dimension, the old plan and harvest-lot
  links on stock documents…) with how many values they hold, and how many of those sit on posted documents;
- closed timekeeping periods whose month had Labor Allocation rows (their payroll was computed with them);
- the block list: a legacy value on a posted accounting document stops the purge until the owner decides; the books
  are never edited to make room.

commit(archive_dir) writes every legacy table to a JSON file with its row count and checksum, checks the files against
the tables, and only then removes, in this order: the rows, the fields and accounting dimensions that pointed at the
tables, the DocTypes, the tables, and what else in the database still named them (menus, reports, history rows). It
stops before removing anything when preview has a block list. Run again, it finds nothing and changes nothing. (If a
run is cut short after the archive, the folder of that first run is the archive; a later run writes its own folder of
what was still there.)

verify() lists what in the database still names a legacy table (empty when clean).

bench --site frontend execute lotus_farm.legacy_purge.preview
bench --site frontend execute lotus_farm.legacy_purge.commit
"""
import hashlib
import json
import os

import frappe
from frappe.utils import now_datetime

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
REPORTS = ("Daily Operations", "Harvest Availability")  # script reports of the old chain, removed with it
# Documents whose posted rows are part of the books: a legacy value on one of them blocks the purge.
ACCOUNTING = {"GL Entry", "Journal Entry", "Journal Entry Account", "Stock Entry", "Stock Entry Detail", "Purchase Invoice", "Purchase Invoice Item",
              "Purchase Receipt", "Purchase Receipt Item", "Sales Invoice", "Sales Invoice Item", "Delivery Note", "Delivery Note Item", "Payment Entry",
              "Stock Ledger Entry", "Asset", "Asset Capitalization", "Landed Cost Voucher"}
LINKS = ["Link", "Dynamic Link", "Table", "Table MultiSelect"]
# Links to a legacy table already taken out of a kept DocType by the first deployment: the column stayed behind.
STALE_COLUMNS = {("Lotus Work Entry", "posted_event"): "Lotus Bunch Event", ("Packhouse Preprocessing", "harvest_lot"): "Harvest Lot",
                 ("Work Schedule Rule", "norm_profile"): "Material Norm Profile"}
# Fields that carried data of the old flows without being links (ids of requirement lines, forecast notes of the old
# stock bridge): removed with the tables they described.
FLOW_FIELDS = {("Stock Entry", "lotus_forecast_impacts_json"): "Harvest Forecast", ("Stock Entry Detail", "lotus_requirement_line"): "Material Requirement Line",
               ("Material Request Item", "lotus_requirement_line"): "Material Requirement Line"}
# Rows elsewhere that only describe a document by its DocType name: (table, column holding the DocType name).
HISTORY = (("Version", "ref_doctype"), ("Comment", "reference_doctype"), ("Activity Log", "reference_doctype"), ("DocShare", "share_doctype"),
           ("ToDo", "reference_type"), ("View Log", "reference_doctype"), ("Communication", "reference_doctype"),
           ("Deleted Document", "deleted_doctype"), ("Notification Log", "document_type"), ("Document Follow", "ref_doctype"),
           ("Energy Point Log", "reference_doctype"), ("Tag Link", "document_type"), ("Custom DocPerm", "parent"),
           ("Property Setter", "doc_type"), ("Custom Field", "dt"), ("Client Script", "dt"), ("Print Format", "doc_type"), ("Notification", "document_type"),
           ("Workflow", "document_type"), ("Web Form", "doc_type"), ("Report", "ref_doctype"), ("Dashboard Chart", "document_type"),
           ("Number Card", "document_type"), ("Kanban Board", "reference_doctype"), ("List View Settings", "name"),
           ("Workspace Link", "link_to"), ("Workspace Shortcut", "link_to"), ("Workspace Quick List", "document_type"),
           ("User Permission", "allow"), ("Data Import", "reference_doctype"), ("DocType Link", "link_doctype"))


def _rows(doctype):
    if not frappe.db.table_exists(doctype):
        return None
    return frappe.db.count(doctype)


def _size(doctype):
    row = frappe.db.sql("""select coalesce(data_length, 0) + coalesce(index_length, 0) from information_schema.tables
                           where table_schema = database() and table_name = %s""", f"tab{doctype}")
    return int(row[0][0]) if row else 0


def _dimensions():
    if not frappe.db.exists("DocType", "Accounting Dimension"):
        return []
    return frappe.get_all("Accounting Dimension", filters={"document_type": ["in", ALL]}, fields=["name", "fieldname", "document_type"])


def _legacy_fields():
    """{(DocType, field): legacy table} over kept DocTypes: custom fields, the accounting dimensions built on a legacy
    table, fields of the DocType itself (as the database still has it) and columns left by the first deployment."""
    found = {}
    for f in frappe.get_all("Custom Field", filters={"fieldtype": ["in", LINKS], "options": ["in", ALL]}, fields=["dt", "fieldname", "options"],
                            limit_page_length=0):
        if f.dt not in ALL:
            found[(f.dt, f.fieldname)] = f.options
    for d in _dimensions():
        for f in frappe.get_all("Custom Field", filters={"fieldname": d.fieldname}, fields=["dt"], limit_page_length=0):
            if f.dt not in ALL:
                found[(f.dt, d.fieldname)] = d.document_type
    for f in frappe.get_all("DocField", filters={"fieldtype": ["in", LINKS], "options": ["in", ALL], "parenttype": "DocType"},
                            fields=["parent", "fieldname", "options"], limit_page_length=0):
        if f.parent not in ALL:
            found[(f.parent, f.fieldname)] = f.options
    for (dt, fieldname), target in {**STALE_COLUMNS, **FLOW_FIELDS}.items():
        if frappe.db.table_exists(dt) and frappe.db.has_column(dt, fieldname):
            found.setdefault((dt, fieldname), target)
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


def _unmoved_bunch_events():
    """Confirmed rows of the old bunch ledger with no line in the sổ lô (the first deployment moves them all)."""
    if not frappe.db.table_exists("Lotus Bunch Event") or not frappe.db.has_column("Lotus Bunch Event", "source_key"):
        return 0
    return frappe.db.sql("""select count(*) from `tabLotus Bunch Event` e where e.state = 'Confirmed'
                            and not exists (select 1 from `tabLotus Work Entry` w where w.source_key = e.source_key)""")[0][0]


def _scan():
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
    unmoved = _unmoved_bunch_events()
    if unmoved:
        block.append(f"Sổ cắt bắp đầu kỳ còn {unmoved} dòng chưa chuyển sang sổ lô: chạy bước chuyển dữ liệu của lần triển khai 1 trước.")
    return {"tables": tables, "table_count": len(tables), "rows": sum(t["rows"] for t in tables), "bytes": sum(t["bytes"] for t in tables),
            "with_data": [t["doctype"] for t in tables if t["rows"]], "fields": fields, "payroll_periods": payroll, "block": block}


@frappe.whitelist()
def preview():
    """Counts and checks only; writes nothing."""
    frappe.only_for("System Manager")
    result = _scan()
    print(frappe.as_json({k: v for k, v in result.items() if k != "tables"}, indent=1))
    return result


# ---------------------------------------------------------------- archive

def _dump(rows):
    return json.dumps(rows, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))


def _table_rows(doctype):
    order = "parent, parentfield, idx, name" if frappe.db.has_column(doctype, "parent") else "name"
    return frappe.db.sql(f"select * from `tab{doctype}` order by {order}", as_dict=True)


def _write(folder, filename, payload):
    path = os.path.join(folder, filename)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(payload)
    return path


def _archive(folder, scan):
    """One JSON file per legacy table that exists, the values of the fields about to be removed, and a manifest.
    Every file is read back and compared with the table before anything is deleted."""
    os.makedirs(folder, exist_ok=True)
    manifest = {"site": frappe.local.site, "made_at": str(now_datetime()), "made_by": frappe.session.user, "tables": [], "fields": [], "files": []}
    for t in scan["tables"]:
        if not t["exists"]:
            continue
        rows = _table_rows(t["doctype"])
        body = _dump(rows)
        name = t["doctype"].replace(" ", "_") + ".json"
        checksum = hashlib.sha256(body.encode("utf-8")).hexdigest()
        head = _dump({"doctype": t["doctype"], "rows": len(rows), "sha256": checksum})
        _write(folder, name, head[:-1] + ',"data":' + body + "}")
        manifest["tables"].append({"doctype": t["doctype"], "group": t["group"], "file": name, "rows": len(rows), "sha256": checksum})
    for f in scan["fields"]:
        values = []
        if f["values"]:
            values = frappe.db.sql(f"select name, `{f['fieldname']}` as value from `tab{f['doctype']}` where ifnull(`{f['fieldname']}`, '') != '' order by name",
                                   as_dict=True)
        manifest["fields"].append(dict(f, kept_values=values))
    if frappe.db.table_exists("File"):
        manifest["files"] = frappe.get_all("File", filters={"attached_to_doctype": ["in", ALL]},
                                           fields=["name", "file_name", "file_url", "attached_to_doctype", "attached_to_name"], limit_page_length=0)
    _write(folder, "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=1, default=str))
    for entry in manifest["tables"]:
        with open(os.path.join(folder, entry["file"]), encoding="utf-8") as handle:
            saved = json.load(handle)
        again = _dump(saved["data"])
        if saved["rows"] != entry["rows"] or len(saved["data"]) != frappe.db.count(entry["doctype"]) or \
                hashlib.sha256(again.encode("utf-8")).hexdigest() != entry["sha256"]:
            frappe.throw(f"Tệp lưu trữ {entry['file']} không khớp bảng {entry['doctype']}: dừng, chưa xóa gì.")
    return manifest


# ---------------------------------------------------------------- removal

def _drop_column(dt, fieldname):
    if frappe.db.table_exists(dt) and frappe.db.has_column(dt, fieldname):
        frappe.db.sql_ddl(f"alter table `tab{dt}` drop column `{fieldname}`")


def _remove_fields(scan):
    """The accounting dimensions built on a legacy table, then every field of a kept document that pointed at one."""
    for d in _dimensions():
        doc = frappe.get_doc("Accounting Dimension", d.name)
        try:
            from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import delete_accounting_dimension
            delete_accounting_dimension(doc)
        except frappe.DoesNotExistError:
            frappe.clear_messages()  # no budget property to tidy on this site
        frappe.db.delete("Accounting Dimension Detail", {"parent": d.name})
        frappe.db.delete("Accounting Dimension", {"name": d.name})
    for f in scan["fields"]:
        dt, fieldname = f["doctype"], f["fieldname"]
        frappe.db.delete("Custom Field", {"dt": dt, "fieldname": fieldname})
        frappe.db.delete("Property Setter", {"doc_type": dt, "field_name": fieldname})
        frappe.db.delete("DocField", {"parent": dt, "parenttype": "DocType", "fieldname": fieldname})
    frappe.db.commit()
    for f in scan["fields"]:
        _drop_column(f["doctype"], f["fieldname"])
        frappe.clear_cache(doctype=f["doctype"])


def _remove_tables(scan):
    for t in scan["tables"]:
        doctype = t["doctype"]
        if t["exists"] and t["rows"]:
            frappe.db.delete(doctype)
        if frappe.db.exists("DocType", doctype):
            frappe.delete_doc("DocType", doctype, force=True, ignore_permissions=True, ignore_missing=True, delete_permanently=True)
    frappe.db.commit()
    for t in scan["tables"]:
        frappe.db.sql_ddl(f"drop table if exists `tab{t['doctype']}`")


def _remove_mentions():
    """What else names a legacy table: history rows, permissions, menus, the two old script reports, attachments."""
    for name in REPORTS:
        if frappe.db.exists("Report", name):
            frappe.delete_doc("Report", name, force=True, ignore_permissions=True, delete_permanently=True)
    for table, column in HISTORY:
        if frappe.db.table_exists(table) and frappe.db.has_column(table, column):
            frappe.db.delete(table, {column: ["in", ALL]})
    if frappe.db.table_exists("Deleted Document"):
        frappe.db.delete("Deleted Document", {"deleted_doctype": "DocType", "deleted_name": ["in", ALL]})
    if frappe.db.table_exists("File"):  # the files stay (they are the farm's papers); only the pointer to the removed document goes
        frappe.db.sql("update `tabFile` set attached_to_doctype = null, attached_to_name = null, attached_to_field = null where attached_to_doctype in %s",
                      (tuple(ALL),))
    frappe.db.commit()
    frappe.clear_cache()


def _as_migration(fn):
    """Standard DocTypes and reports are only removable the way a migration removes them (and their controller files,
    which belong to the code, are then left alone)."""
    before, frappe.flags.in_migrate = frappe.flags.in_migrate, True
    try:
        return fn()
    finally:
        frappe.flags.in_migrate = before


@frappe.whitelist()
def commit(archive_dir=None):
    """Archive, check the archive, then remove. Stops with nothing removed when preview has a block list."""
    frappe.only_for("System Manager")
    scan = _scan()
    if scan["block"]:
        frappe.throw("Chưa dọn được bảng cũ:<br>" + "<br>".join(scan["block"]))
    remaining = [t for t in scan["tables"] if t["exists"]]
    if not remaining and not scan["fields"]:
        _as_migration(_remove_mentions)
        result = {"archive": None, "tables": 0, "rows": 0, "fields": 0, "left": verify()}
        print(frappe.as_json(result, indent=1))
        return result
    folder = archive_dir or frappe.get_site_path("private", "files", "legacy_purge_" + now_datetime().strftime("%Y%m%d_%H%M%S"))
    manifest = _archive(folder, scan)
    _as_migration(lambda: (_remove_fields(scan), _remove_tables(scan), _remove_mentions()))
    result = {"archive": os.path.abspath(folder), "tables": len(manifest["tables"]), "rows": sum(t["rows"] for t in manifest["tables"]),
              "fields": len(scan["fields"]), "left": verify()}
    print(frappe.as_json(result, indent=1))
    return result


@frappe.whitelist()
def verify():
    """What in the database still names a legacy table. An empty list means clean."""
    frappe.only_for("System Manager")
    left = []
    for name in ALL:
        if frappe.db.table_exists(name):
            left.append(f"bảng tab{name}")
        if frappe.db.exists("DocType", name):
            left.append(f"DocType {name}")
    for (dt, fieldname), target in sorted(_legacy_fields().items()):
        left.append(f"trường {dt}.{fieldname} → {target}")
    for d in _dimensions():
        left.append(f"chiều kế toán {d.name} → {d.document_type}")
    for f in frappe.get_all("Custom Field", filters={"dt": ["in", ALL]}, fields=["dt", "fieldname"], limit_page_length=0):
        left.append(f"trường tùy chỉnh {f.dt}.{f.fieldname}")
    for name in REPORTS:
        if frappe.db.exists("Report", name):
            left.append(f"báo cáo {name}")
    for table, column in HISTORY:
        if frappe.db.table_exists(table) and frappe.db.has_column(table, column):
            count = frappe.db.count(table, {column: ["in", ALL]})
            if count:
                left.append(f"{count} dòng {table}.{column}")
    if frappe.db.table_exists("File"):
        count = frappe.db.count("File", {"attached_to_doctype": ["in", ALL]})
        if count:
            left.append(f"{count} tệp còn gắn vào chứng từ cũ")
    return left
