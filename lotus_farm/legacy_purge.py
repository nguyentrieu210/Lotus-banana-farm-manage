"""Dọn các bảng đời cũ (spec 002, US7; danh sách và lý do ở specs/002-cham-soc-thu-hoach-du-thu/cleanup.md): 76 bảng của
mảng vườn cũ (nhóm A–D) và 3 bảng của khung ứng dụng cũ chỉ còn phục vụ các luồng đã xóa (nhóm E).

preview() only reads:
- rows in each legacy table (for a Single, its stored values) and the size of the table, for the archive;
- fields of kept documents that point at a legacy table (the "Vụ" accounting dimension, the old plan and harvest-lot
  links on stock documents, the work category…) with how many values they hold, and how many of those sit on posted
  documents;
- closed timekeeping periods whose month had Labor Allocation rows (their payroll was computed with them);
- the block list: a legacy value on a posted accounting document, such a payroll period, or opening bunches of the old
  bunch ledger not yet moved to the sổ lô stop the purge until the owner decides; the books are never edited to make room.

commit(archive_dir) writes every legacy table (and the rows elsewhere that only describe legacy documents: history,
comments, the recycle bin, permissions) to JSON files with row counts and checksums, reads them back and compares them
with the database, and only then removes, in this order: the columns of the fields that pointed at legacy tables, their
metadata and accounting dimensions, the DocTypes, the tables, and what else in the database still named them. Columns go
before their metadata, so a run cut short can be started again and still finds what is left. It stops before removing
anything when preview has a block list. Run again, it finds nothing and changes nothing.

verify() lists what in the database still names a legacy table (empty when clean).

Run with bench only (commit is not callable over HTTP):
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
    # The old desktop shell: proactive alerts and the settings page, both fed only by the flows above, and the market
    # list whose only link was the old packout output.
    "E": ["Lotus Alert", "Lotus Farm Settings", "Market"],
}
ALL = [name for group in LEGACY.values() for name in group]
REPORTS = ("Daily Operations", "Harvest Availability")  # script reports of the old chain, removed with it
# Documents whose posted rows are part of the books: a legacy value on one of them blocks the purge.
ACCOUNTING = {"GL Entry", "Journal Entry", "Journal Entry Account", "Stock Entry", "Stock Entry Detail", "Purchase Invoice", "Purchase Invoice Item",
              "Purchase Receipt", "Purchase Receipt Item", "Sales Invoice", "Sales Invoice Item", "Delivery Note", "Delivery Note Item", "Payment Entry",
              "Stock Ledger Entry", "Asset", "Asset Capitalization", "Landed Cost Voucher"}
LINKS = ["Link", "Dynamic Link", "Table", "Table MultiSelect"]
# Columns known to belong to the legacy flows, looked for even when their metadata is already gone (a run cut short, a
# kept DocType synced from its new JSON): links taken out of kept DocTypes, and fields that carried data of the old flows
# without being links (requirement line ids, the forecast notes of the old stock bridge, the OneDrive source version).
KNOWN_COLUMNS = {("Lotus Work Entry", "posted_event"): "Lotus Bunch Event", ("Packhouse Preprocessing", "harvest_lot"): "Harvest Lot",
                 ("Work Schedule Rule", "norm_profile"): "Material Norm Profile", ("Bunch Tag", "process_adoption"): "Lotus Process Adoption",
                 ("Bunch Tag", "source_version"): "Source Import Batch", ("Work Type", "category"): "Work Category",
                 ("Stock Entry", "lotus_work_plan"): "Daily Work Plan", ("Stock Entry", "lotus_harvest_lot"): "Harvest Lot",
                 ("Stock Entry", "lotus_packout_run"): "Packout Run", ("Stock Entry", "lotus_forecast_impacts_json"): "Harvest Forecast",
                 ("Stock Entry Detail", "lotus_requirement"): "Material Requirement",
                 ("Stock Entry Detail", "lotus_requirement_line"): "Material Requirement Line",
                 ("Material Request Item", "lotus_requirement"): "Material Requirement",
                 ("Material Request Item", "lotus_requirement_line"): "Material Requirement Line"}
DIMENSION_COLUMN = "lotus_crop_cycle"  # the "Vụ" accounting dimension (Crop Cycle), on every document that carries dimensions
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


def _single(doctype):
    return bool(frappe.db.exists("DocType", doctype) and frappe.db.get_value("DocType", doctype, "issingle"))


def _rows(doctype):
    """Rows of a legacy table (a Single: its stored values), or None when it no longer exists."""
    if frappe.db.table_exists(doctype):
        return frappe.db.count(doctype)
    if _single(doctype) or frappe.db.count("Singles", {"doctype": doctype}):
        return frappe.db.count("Singles", {"doctype": doctype})
    return None


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
    table, fields of the DocType itself (as the database still has it), and the known legacy columns still present
    (also those whose metadata is already gone)."""
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
    for (dt, fieldname), target in KNOWN_COLUMNS.items():
        if frappe.db.table_exists(dt) and frappe.db.has_column(dt, fieldname):
            found.setdefault((dt, fieldname), target)
    for (table,) in frappe.db.sql("""select table_name from information_schema.columns where table_schema = database() and column_name = %s""",
                                  DIMENSION_COLUMN):
        dt = table[3:] if table.startswith("tab") else table
        if dt not in ALL:
            found.setdefault((dt, DIMENSION_COLUMN), "Crop Cycle")
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
    """Confirmed rows of the old bunch ledger with no line in the sổ lô (release 1 of spec 002 moves them all), or a
    message when the site never got release 1 (the sổ lô has no source keys yet)."""
    if not frappe.db.table_exists("Lotus Bunch Event") or not frappe.db.count("Lotus Bunch Event", {"state": "Confirmed"}):
        return None
    if not frappe.db.table_exists("Lotus Work Entry") or not frappe.db.has_column("Lotus Work Entry", "source_key"):
        return ("Sổ lô chưa có ở bản này: triển khai bản phát hành 1 của spec 002 (40f8330) và chạy lot_ledger_migrate.commit của bản đó "
                "trước khi dọn bảng cũ.")
    unmoved = frappe.db.sql("""select count(*) from `tabLotus Bunch Event` e where e.state = 'Confirmed'
                               and not exists (select 1 from `tabLotus Work Entry` w where w.source_key = e.source_key)""")[0][0]
    if unmoved:
        return (f"Sổ cắt bắp đầu kỳ còn {unmoved} dòng chưa chuyển sang sổ lô: chạy lot_ledger_migrate.commit của bản phát hành 1 (40f8330) "
                "trước khi dọn bảng cũ.")
    return None


def _scan():
    tables = []
    for group, names in LEGACY.items():
        for name in names:
            rows = _rows(name)
            tables.append({"group": group, "doctype": name, "single": _single(name), "exists": rows is not None, "rows": rows or 0,
                           "bytes": _size(name) if rows is not None else 0})
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
        block.append(unmoved)
    if frappe.db.table_exists("Stock Entry") and frappe.db.has_column("Stock Entry", "lotus_issue_mode"):
        planned = frappe.db.count("Stock Entry", {"docstatus": 0, "lotus_issue_mode": "Plan"})
        if planned:  # the plan issue mode is gone: such a draft could no longer be saved or posted
            block.append(f"Còn {planned} phiếu xuất kho nháp theo kế hoạch ngày (cách xuất đã bỏ): ghi sổ, đổi sang Thủ công hoặc xóa trước khi dọn.")
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
    if not frappe.db.table_exists(doctype):  # a Single keeps its values in tabSingles
        return frappe.db.sql("select * from `tabSingles` where doctype = %s order by field", doctype, as_dict=True)
    order = "parent, parentfield, idx, name" if frappe.db.has_column(doctype, "parent") else "name"
    return frappe.db.sql(f"select * from `tab{doctype}` order by {order}", as_dict=True)


def _count(doctype):
    return frappe.db.count(doctype) if frappe.db.table_exists(doctype) else frappe.db.count("Singles", {"doctype": doctype})


def _write(folder, filename, payload):
    path = os.path.join(folder, filename)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(payload)
    return path


def _archive(folder, scan):
    """One JSON file per legacy table that exists, the rows elsewhere that only describe legacy documents, the values of
    the fields about to be removed, and a manifest. Every file is read back and compared before anything is deleted."""
    os.makedirs(folder, exist_ok=True)
    manifest = {"site": frappe.local.site, "made_at": str(now_datetime()), "made_by": frappe.session.user, "tables": [], "fields": [], "files": []}
    for t in scan["tables"]:
        if not t["exists"]:
            continue
        rows = _table_rows(t["doctype"])
        body = _dump(rows)
        name = t["doctype"].replace(" ", "_") + ".json"
        checksum = hashlib.sha256(body.encode("utf-8")).hexdigest()
        head = _dump({"doctype": t["doctype"], "single": t["single"], "rows": len(rows), "sha256": checksum})
        _write(folder, name, head[:-1] + ',"data":' + body + "}")
        manifest["tables"].append({"doctype": t["doctype"], "group": t["group"], "single": t["single"], "file": name, "rows": len(rows),
                                   "sha256": checksum})
    for f in scan["fields"]:
        values = []
        if f["values"]:
            values = frappe.db.sql(f"select name, `{f['fieldname']}` as value from `tab{f['doctype']}` where ifnull(`{f['fieldname']}`, '') != '' order by name",
                                   as_dict=True)
        manifest["fields"].append(dict(f, kept_values=values))
    if frappe.db.table_exists("File"):
        manifest["files"] = frappe.get_all("File", filters={"attached_to_doctype": ["in", ALL]},
                                           fields=["name", "file_name", "file_url", "attached_to_doctype", "attached_to_name"], limit_page_length=0)
    # The rows elsewhere that only describe the legacy documents (history, comments, the recycle bin, permissions) are
    # removed too: they are archived with the tables.
    mentions = {}
    for table, column in HISTORY:
        if frappe.db.table_exists(table) and frappe.db.has_column(table, column):
            rows = frappe.db.sql(f"select * from `tab{table}` where `{column}` in %s order by name", (tuple(ALL),), as_dict=True)
            if rows:
                mentions[f"{table}.{column}"] = rows
    if frappe.db.table_exists("Deleted Document"):
        rows = frappe.db.sql("select * from `tabDeleted Document` where deleted_doctype = 'DocType' and deleted_name in %s order by name", (tuple(ALL),),
                             as_dict=True)
        if rows:
            mentions["Deleted Document.deleted_name"] = rows
    body = _dump(mentions)
    manifest["mentions"] = {"file": "_mentions.json", "rows": {k: len(v) for k, v in mentions.items()},
                            "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest()}
    _write(folder, "_mentions.json", body)
    _write(folder, "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=1, default=str))
    with open(os.path.join(folder, "_mentions.json"), encoding="utf-8") as handle:
        if hashlib.sha256(_dump(json.load(handle)).encode("utf-8")).hexdigest() != manifest["mentions"]["sha256"]:
            frappe.throw("Tệp lưu trữ _mentions.json không khớp: dừng, chưa xóa gì.")
    for entry in manifest["tables"]:
        with open(os.path.join(folder, entry["file"]), encoding="utf-8") as handle:
            saved = json.load(handle)
        again = _dump(saved["data"])
        if saved["rows"] != entry["rows"] or len(saved["data"]) != _count(entry["doctype"]) or \
                hashlib.sha256(again.encode("utf-8")).hexdigest() != entry["sha256"]:
            frappe.throw(f"Tệp lưu trữ {entry['file']} không khớp bảng {entry['doctype']}: dừng, chưa xóa gì.")
    return manifest


# ---------------------------------------------------------------- removal

def _drop_column(dt, fieldname):
    if frappe.db.table_exists(dt) and frappe.db.has_column(dt, fieldname):
        frappe.db.sql_ddl(f"alter table `tab{dt}` drop column `{fieldname}`")
        frappe.client_cache.delete_value(f"table_columns::tab{dt}")  # as schema sync does: a rerun must see the column gone


def _remove_fields(scan):
    """Every column of a kept document that pointed at a legacy table first (DDL commits on its own), then the metadata
    that described it and the accounting dimensions built on a legacy table. A run cut short in the middle leaves
    metadata or known columns that the next run finds again."""
    for f in scan["fields"]:
        _drop_column(f["doctype"], f["fieldname"])
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
    for dt in sorted({f["doctype"] for f in scan["fields"]}):
        frappe.clear_cache(doctype=dt)


def _remove_tables(scan):
    for t in scan["tables"]:
        doctype = t["doctype"]
        if t["exists"] and t["rows"]:
            if frappe.db.table_exists(doctype):
                frappe.db.delete(doctype)
            else:
                frappe.db.delete("Singles", {"doctype": doctype})
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
    frappe.db.delete("Singles", {"doctype": ["in", ALL]})
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


def commit(archive_dir=None):
    """Archive, check the archive, then remove. Stops with nothing removed when preview has a block list. Not
    whitelisted: run it with bench execute or through the patch purge_legacy_doctypes."""
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
    singles = frappe.db.count("Singles", {"doctype": ["in", ALL]})
    if singles:
        left.append(f"{singles} giá trị Singles của bảng cũ")
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
