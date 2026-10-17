"""Idempotent initialization of requested Lotus garden master records.

This is executed in an existing bench site context (bench --site frontend execute).
Never rename the farm IDs or touch plot geometry/history.
"""
import frappe


def apply():
    frappe.set_user("Administrator")
    farm = frappe.get_doc("Farm", "LOTUS-222")
    if farm.company != "Lotus Agritech":
        frappe.throw("LOTUS-222 thuộc công ty khác, cần kiểm tra trước khi sửa.")
    if farm.farm_name != "Vườn 222 Thuận Phú":
        farm.farm_name = "Vườn 222 Thuận Phú"
        farm.save()
    if frappe.db.exists("Farm", "LOTUS-180"):
        second = frappe.get_doc("Farm", "LOTUS-180")
        if second.company != farm.company:
            frappe.throw("Vườn 180 thuộc công ty khác.")
        if second.farm_name != "Vườn 180 Thuận Phú":
            second.farm_name = "Vườn 180 Thuận Phú"
            second.save()
    else:
        frappe.get_doc({
            "doctype": "Farm",
            "farm_code": "LOTUS-180",
            "farm_name": "Vườn 180 Thuận Phú",
            "company": farm.company,
            "location": "Thuận Phú",
            "area_ha": 180,
            "active": 1
        }).insert()
    frappe.db.commit()
    return frappe.get_list("Farm", filters={"name": ["in", ["LOTUS-222", "LOTUS-180"]]},
                           fields=["name", "farm_name", "farm_code", "area_ha", "active"],
                           order_by="name asc")
