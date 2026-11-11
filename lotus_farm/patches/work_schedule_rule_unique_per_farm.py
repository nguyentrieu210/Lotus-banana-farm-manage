"""Care cycles (Work Schedule Rule) are numbered per farm: the unique key becomes (farm, rule_name, version).
Frappe adds the new key in after_migrate (install.setup) but never drops the old one, so it is dropped here."""
import frappe


def execute():
    if frappe.db.table_exists("Work Schedule Rule") and frappe.db.has_index("tabWork Schedule Rule", "unique_rule_name_version"):
        frappe.db.sql_ddl("alter table `tabWork Schedule Rule` drop index `unique_rule_name_version`")
