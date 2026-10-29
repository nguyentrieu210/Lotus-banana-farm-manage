"""Nhật ký công việc (chép Zalo) was replaced by the đội daily report (Lotus Field Report) on 29/10/2026.
It never held data on production; drop its DocTypes and tables."""
import frappe


def execute():
    for doctype in ("Work Journal Request", "Work Daily Journal", "Work Daily Journal Line"):
        if frappe.db.exists("DocType", doctype):
            if frappe.db.table_exists(doctype) and frappe.db.count(doctype):
                frappe.throw(f"{doctype} vẫn còn dữ liệu, không xóa.")
            frappe.delete_doc("DocType", doctype, force=True, ignore_permissions=True, ignore_missing=True)
        frappe.db.sql_ddl(f"drop table if exists `tab{doctype}`")
