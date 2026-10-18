"""Read-only live smoke test; draft insert is rolled back unconditionally."""
import frappe
from datetime import date

def verify():
    try:
        frappe.set_user("Administrator")
        assert frappe.db.exists("DocType","Plan Cohort"), "Plan Cohort DocType missing"
        assert frappe.db.table_exists("Plan Cohort"), "Plan Cohort table missing"
        from lotus_farm.plan_norm import board
        farm = "LOTUS-222"
        payload = board(farm=farm)
        assert payload["farm"] == farm
        assert payload["blocks"], "Expected permitted blocks"
        print("BOARD_OK", {"blocks":len(payload["blocks"]),"cohorts":len(payload["cohorts"]),
          "rules":len(payload["rules"]),"norms":len(payload["norms"]),"profiles":len(payload["profiles"]),
          "works":len(payload["works"])})
        # Verify a DRAFT can pass real validation without persisting anything.
        block = next((b for b in payload["blocks"] if b.active), None)
        assert block, "No active block for safe validation"
        marker = "PN-LIVE-UAT-" + date.today().strftime("%Y%m%d")
        sample=frappe.get_doc({
          "doctype":"Plan Cohort","farm":farm,"farm_block":block.name,
          "cohort_code":marker,"cohort_name":"Kiểm tra cấu hình (sẽ hủy)",
          "anchor":"Shooting","anchor_date":"2026-11-01",
          "quantity_basis":"Bunches","planned_qty":10,"version":1,
          "approval_state":"Draft","notes":"Smoke test rollback, không sử dụng"
        })
        sample.insert()
        assert frappe.db.exists("Plan Cohort",sample.name)
        print("DRAFT_CREATE_OK", block.name)
        frappe.db.rollback()
        assert not frappe.db.exists("Plan Cohort",sample.name), "Rollback failed"
        print("ROLLBACK_OK")
        frappe.set_user("Guest")
        denied = False
        try:
          board(farm=farm)
        except frappe.PermissionError:
          denied=True
        except Exception as error:
          denied=("permission" in str(error).lower() or "quyền" in str(error).lower())
        assert denied, "Guest bypassed Farm read permission"
        print("GUEST_DENIED_OK")
    finally:
        frappe.db.rollback()
