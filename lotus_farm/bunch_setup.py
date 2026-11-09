"""One-off preparation for the bunch ledger on Vườn 222 (agreed with the owner on 09/11/2026).

- Every lô with trees is on vụ 2 (vụ 1 was the new planting, already harvested).
- Khu A tree counts are the field census.
- The list of reasons a bunch is rejected.

Run: bench --site <site> execute lotus_farm.bunch_setup.apply  (dry run; --kwargs "{'commit': 1}" to write).
Running it again changes nothing: a lô that already has a vụ keeps it.
"""
import frappe

FARM = "LOTUS-222"
CURRENT_CYCLE = 2
CENSUS_ZONES = ("A",)
GROUP = ("BUONG", "Hao hụt buồng")
REASONS = (("GAY-DO", "Gãy đổ"), ("SAU-BENH", "Sâu bệnh"), ("BUONG-XAU", "Buồng xấu"), ("KHAC", "Khác"))


def plan():
    blocks = frappe.get_all("Farm Block", filters={"farm": FARM, "lotus_tree_count": [">", 0]},
                            fields=["name", "farm_zone", "forecast_count_source", "lotus_current_cycle_no"], limit_page_length=0)
    return dict(
        blocks=len(blocks),
        set_cycle=[b.name for b in blocks if not b.lotus_current_cycle_no],
        set_census=[b.name for b in blocks if b.farm_zone in CENSUS_ZONES and b.forecast_count_source != "Census Confirmed"],
        group=frappe.db.get_value("Cancellation Reason Group", {"group_code": GROUP[0]}),
        reasons=[r for r in REASONS if not frappe.db.exists("Cancellation Reason", {"reason_code": r[0]})],
    )


def apply(commit=0):
    frappe.only_for("System Manager")
    state = plan()
    print("Lô:", state["blocks"], "| đặt vụ:", len(state["set_cycle"]), "| đánh dấu kiểm kê:", len(state["set_census"]),
          "| lý do mới:", len(state["reasons"]))
    if not int(commit):
        frappe.db.rollback()
        print("Dry run only. Run with commit=1 to write.")
        return state
    for name in state["set_cycle"]:
        frappe.db.set_value("Farm Block", name, "lotus_current_cycle_no", CURRENT_CYCLE)
    for name in state["set_census"]:
        frappe.db.set_value("Farm Block", name, "forecast_count_source", "Census Confirmed")
    group = state["group"] or frappe.get_doc({"doctype": "Cancellation Reason Group", "group_code": GROUP[0], "group_name": GROUP[1],
                                              "active": 1}).insert(ignore_permissions=True).name
    for code, label in state["reasons"]:
        frappe.get_doc({"doctype": "Cancellation Reason", "reason_code": code, "reason_name": label, "reason_group": group,
                        "active": 1}).insert(ignore_permissions=True)
    frappe.db.commit()
    print("Done.")
    return plan()
