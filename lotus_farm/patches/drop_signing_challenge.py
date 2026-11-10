"""Phiên QR ký chứng từ (Lotus Signing Challenge) was removed by spec 003: a signature is the confirmation of the
person who is logged in. Its rows were short-lived tokens, never business records; the signature events stay."""
import frappe


def execute():
    doctype = "Lotus Signing Challenge"
    if frappe.db.exists("DocType", doctype):
        frappe.delete_doc("DocType", doctype, force=True, ignore_permissions=True, ignore_missing=True)
    frappe.db.sql_ddl(f"drop table if exists `tab{doctype}`")
