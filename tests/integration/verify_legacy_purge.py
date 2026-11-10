"""lotus_farm.legacy_purge on a DISPOSABLE copy of a site that still has the legacy tables (spec 002, US7, quickstart 20-23).

It drops tables and columns, which no rollback brings back: it refuses any site whose name does not end in ".test".

    cd sites && SITE=copy.test ../env/bin/python ../apps/lotus_farm/tests/integration/verify_legacy_purge.py

Checks: preview writes nothing; a legacy value on a posted accounting document stops commit with nothing removed;
commit writes one JSON file per table with the row count and checksum of preview, removes rows, fields, dimensions,
DocTypes and tables, leaves the books untouched, and can be run again; verify() then finds nothing.
"""
import hashlib
import json
import os
import shutil
import tempfile

import frappe

SITE = os.environ.get("SITE", "")
if not SITE.endswith(".test"):
    raise SystemExit("verify_legacy_purge.py removes tables: run it only on a disposable copy (site name ending in .test).")

frappe.init(site=SITE)
frappe.connect()
frappe.set_user("Administrator")

from lotus_farm import legacy_purge  # noqa: E402

failures = []
BOOKS = ("GL Entry", "Stock Ledger Entry", "Journal Entry", "Stock Entry", "Stock Entry Detail", "Purchase Invoice", "Payment Entry", "Attendance",
         "Employee", "Employee Checkin", "Lotus Work Entry", "Farm Block", "Work Type", "Bunch Tag", "Item", "Warehouse")


def check(label, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + label + (f" -> {detail}" if not ok and detail != "" else ""))
    if not ok:
        failures.append(label)


def quiet(fn, *args, **kwargs):
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args, **kwargs)


def counts():
    return {r[0]: r[1] for r in ((t, frappe.db.count(t)) for t in BOOKS if frappe.db.table_exists(t))}


def book_hash(doctype, fields):
    rows = frappe.db.sql(f"select {', '.join('`' + f + '`' for f in fields)} from `tab{doctype}` order by name")
    return hashlib.sha256(json.dumps(rows, default=str).encode()).hexdigest()


folder = tempfile.mkdtemp(prefix="legacy_purge_test_")
try:
    before = counts()
    gl = book_hash("GL Entry", ["name", "account", "debit", "credit", "posting_date", "voucher_no", "is_cancelled"])
    sle = book_hash("Stock Ledger Entry", ["name", "item_code", "warehouse", "actual_qty", "stock_value_difference", "voucher_no", "is_cancelled"])
    first = quiet(legacy_purge.preview)
    check("preview lists the 76 tables", first["table_count"] == 76, first["table_count"])
    check("preview writes nothing", counts() == before and quiet(legacy_purge.preview)["rows"] == first["rows"])
    existing = [t for t in first["tables"] if t["exists"]]
    print(f"     tables present: {len(existing)}, rows: {first['rows']}, fields pointing at them: {len(first['fields'])}, block: {first['block']}")

    if existing and not first["block"]:
        # A legacy value on a posted accounting document must stop everything.
        target = next((f for f in first["fields"] if f["doctype"] == "GL Entry"), None)
        entry = frappe.db.get_value("GL Entry", {"is_cancelled": 0}, "name")
        if target and entry:
            frappe.db.sql(f"update `tabGL Entry` set `{target['fieldname']}` = 'THU-CHAN' where name = %s", entry)
            try:
                quiet(legacy_purge.commit, folder)
                check("a legacy value on a posted entry stops commit", False, "no error")
            except frappe.ValidationError:
                frappe.clear_messages()
                check("a legacy value on a posted entry stops commit", True)
            check("…with nothing archived or removed", not os.listdir(folder) and all(frappe.db.table_exists(t["doctype"]) for t in existing))
            frappe.db.sql(f"update `tabGL Entry` set `{target['fieldname']}` = null where name = %s", entry)
            frappe.db.commit()
        else:
            print("     skip block check: no legacy field on GL Entry on this site")

    scan = quiet(legacy_purge.preview)
    result = quiet(legacy_purge.commit, folder)
    if existing:
        manifest = json.load(open(os.path.join(folder, "manifest.json"), encoding="utf-8"))
        by_name = {t["doctype"]: t for t in manifest["tables"]}
        check("one JSON file per table that existed", set(by_name) == {t["doctype"] for t in scan["tables"] if t["exists"]}, sorted(by_name)[:5])
        check("row counts match preview", all(by_name[t["doctype"]]["rows"] == t["rows"] for t in scan["tables"] if t["exists"]))
        bad = []
        for entry in manifest["tables"]:
            saved = json.load(open(os.path.join(folder, entry["file"]), encoding="utf-8"))
            body = json.dumps(saved["data"], ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))
            if len(saved["data"]) != entry["rows"] or hashlib.sha256(body.encode("utf-8")).hexdigest() != entry["sha256"]:
                bad.append(entry["doctype"])
        check("every file holds its rows and checksum", not bad, bad)
        check("fields with values are kept in the manifest", all(len(f["kept_values"]) == f["values"] for f in manifest["fields"]))
        check("commit reports what it removed", result["tables"] == len(manifest["tables"]) and result["rows"] == scan["rows"], result)
    check("no legacy table, DocType, field or dimension is left", result["left"] == [] and legacy_purge.verify() == [], result["left"][:10])
    check("no table of the 76 exists", not any(frappe.db.table_exists(name) for name in legacy_purge.ALL))
    after = counts()
    check("kept tables keep their rows", after == before, {k: (before[k], after.get(k)) for k in before if before[k] != after.get(k)})
    check("the general ledger is untouched", gl == book_hash("GL Entry", ["name", "account", "debit", "credit", "posting_date", "voucher_no", "is_cancelled"]))
    check("the stock ledger is untouched",
          sle == book_hash("Stock Ledger Entry", ["name", "item_code", "warehouse", "actual_qty", "stock_value_difference", "voucher_no", "is_cancelled"]))
    again = quiet(legacy_purge.commit, folder)
    check("commit can be run again", again["tables"] == 0 and again["rows"] == 0 and again["left"] == [], again)
    leftover = quiet(legacy_purge.preview)
    check("preview afterwards finds nothing", leftover["rows"] == 0 and not leftover["fields"] and not any(t["exists"] for t in leftover["tables"]))
finally:
    shutil.rmtree(folder, ignore_errors=True)
    frappe.db.rollback()
    print("\n" + ("ALL PASSED" if not failures else f"{len(failures)} FAILED: " + "; ".join(failures)))
    frappe.destroy()
