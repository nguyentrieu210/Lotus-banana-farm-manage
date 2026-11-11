"""Spec 002, US7: the 76 legacy DocTypes of the field area are removed for good (list and reasons in
specs/002-cham-soc-thu-hoach-du-thu/cleanup.md). Their rows are written to a JSON archive under the site's private
files first; a legacy value on a posted accounting document stops the migration (nothing is removed) until the owner
decides. On the production site the deploy runs lotus_farm.legacy_purge.commit before migrating, so this finds nothing
left to do there."""
import frappe


def execute():
    from lotus_farm import legacy_purge
    result = legacy_purge.commit()
    if result["left"]:
        frappe.throw("Còn sót tên bảng cũ trong cơ sở dữ liệu: " + "; ".join(result["left"][:20]))
