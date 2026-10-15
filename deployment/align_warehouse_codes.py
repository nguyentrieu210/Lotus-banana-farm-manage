"""One-off Lotus warehouse code reconciliation for site frontend.

Run inside Docker container: env/bin/python /tmp/align_warehouse_codes.py
Explicit targets prevent renaming unrelated warehouses and make re-runs harmless.
Always take a Frappe site backup before executing this script.
"""
import json
import os
import frappe

os.chdir("/home/frappe/frappe-bench/sites")
frappe.init(site="frontend")
frappe.connect()
frappe.set_user("Administrator")

TARGETS = {
    "KHO FARM 1 - LT": ("KHO 1", "KHO 1 - LT"),
    "KHO A - LT": ("KHO 2", "KHO 2 - LT"),
    "Kho 180 - LT": ("Kho 4", "Kho 4 - LT"),
}
TABLES = {
    "Stock Ledger Entry": ["warehouse"],
    "Bin": ["warehouse"],
    "Stock Entry Detail": ["s_warehouse", "t_warehouse"],
    "Item Default": ["default_warehouse"],
    "Purchase Order Item": ["warehouse"],
    "Purchase Receipt Item": ["warehouse"],
    "Material Request Item": ["warehouse"],
}
from lotus_farm.warehouse_masters import warehouse_code


def counts(name):
    return {
        doctype + "." + field: frappe.db.count(doctype, {field: name})
        for doctype, fields in TABLES.items()
        for field in fields
    }


try:
    pending = []
    for old, (label, new) in TARGETS.items():
        if frappe.db.exists("Warehouse", new):
            if frappe.db.exists("Warehouse", old):
                raise RuntimeError("Collision: both warehouse codes exist: " + old + " / " + new)
            target = frappe.get_doc("Warehouse", new)
            if target.warehouse_name != label or target.company != "Lotus Agritech":
                raise RuntimeError("Existing target has unexpected data: " + new)
            print("ALREADY ALIGNED", new)
            continue
        if not frappe.db.exists("Warehouse", old):
            raise RuntimeError("Original warehouse missing: " + old)
        warehouse = frappe.get_doc("Warehouse", old)
        if (warehouse.is_group or warehouse.company != "Lotus Agritech"
                or warehouse.warehouse_name != label
                or warehouse_code(label, warehouse.company) != new):
            raise RuntimeError("Unexpected warehouse data: " + old)
        pending.append((old, new, counts(old)))
    print("PREFLIGHT", len(pending), "warehouse(s) needing correction")
    for old, new, before in pending:
        # Frappe performs all regular Link field and nested-set reference updates.
        frappe.rename_doc("Warehouse", old, new, merge=False, force=True)
        # Item minimum levels are stored as a JSON dict, not as Link fields.
        # Keep those keys in sync even if they are configured in the future.
        items = frappe.get_all("Item", fields=["name", "lotus_minimum_stock"], limit_page_length=0)
        for item in items:
            try:
                levels = json.loads(item.lotus_minimum_stock or "{}")
            except (TypeError, ValueError):
                continue
            if not isinstance(levels, dict) or old not in levels:
                continue
            if new in levels:
                raise RuntimeError("Conflicting minimum-stock keys for Item " + item.name)
            levels[new] = levels.pop(old)
            frappe.db.set_value("Item", item.name, "lotus_minimum_stock",
                                json.dumps(levels, ensure_ascii=False), update_modified=False)
        if frappe.db.exists("Warehouse", old) or not frappe.db.exists("Warehouse", new):
            raise RuntimeError("Warehouse rename did not complete: " + old)
        after = counts(new)
        if after != before or any(counts(old).values()):
            raise RuntimeError("References did not transfer completely: " + old + " -> " + new +
                               " BEFORE=" + repr(before) + " AFTER=" + repr(after))
        print("RENAMED", old, "=>", new, "| linked records:", sum(after.values()))
    frappe.db.commit()
    frappe.clear_cache()
    print("SUCCESS", len(pending), "renamed; records and quantities preserved")
except Exception:
    frappe.db.rollback()
    raise
finally:
    frappe.destroy()
