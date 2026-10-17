"""Idempotent, scoped setup of Lotus Farm names (2026-10-16).

Changes only Farm LOTUS-222 display name and creates LOTUS-180 if absent.
Never renames document IDs, blocks, plots or linked transactions.
"""
import json
import frappe

SITE = "frontend"
SITE_PATH = "/home/frappe/frappe-bench/sites"

def main():
    frappe.init(site=SITE, sites_path=SITE_PATH)
    frappe.connect()
    frappe.set_user("Administrator")
    try:
        existing = frappe.get_doc("Farm", "LOTUS-222")
        assert existing.farm_code == "LOTUS-222", "Unexpected existing garden code"
        assert existing.company == "Lotus Agritech", "Unexpected company: must review"
        if existing.farm_name != "Vườn 222 Thuận Phú":
            existing.farm_name = "Vườn 222 Thuận Phú"
            existing.save()
        if frappe.db.exists("Farm", "LOTUS-180"):
            new = frappe.get_doc("Farm", "LOTUS-180")
            assert new.company == existing.company, "LOTUS-180 is in another company"
            if new.farm_name != "Vườn 180 Thuận Phú":
                new.farm_name = "Vườn 180 Thuận Phú"
                new.save()
            action = "existing"
        else:
            new = frappe.get_doc({
                "doctype": "Farm",
                "farm_code": "LOTUS-180",
                "farm_name": "Vườn 180 Thuận Phú",
                "company": existing.company,
                "location": "Thuận Phú",
                "area_ha": 180,
                "active": 1,
            })
            new.insert()
            action = "created"
        frappe.db.commit()
        rows = frappe.get_all("Farm",
            filters={"name": ["in", ["LOTUS-222", "LOTUS-180"]]},
            fields=["name", "farm_code", "farm_name", "company", "area_ha", "active"],
            order_by="name asc", limit_page_length=3)
        print(json.dumps({"action_180": action, "farms": rows}, ensure_ascii=True))
    except Exception:
        frappe.db.rollback()
        raise
    finally:
        frappe.destroy()

if __name__ == "__main__":
    main()
