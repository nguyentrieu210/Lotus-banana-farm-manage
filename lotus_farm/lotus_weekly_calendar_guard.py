"""Retire the superseded 5-day reference calendar for LOTUS-222.

Only the user-confirmed weekly calendar (2026 ISO weeks 43-50) remains active.
Future weeks are left unassigned until real Lotus colors are provided.
All historical reference tags remain readable in archive mode.
"""
import frappe
from frappe.utils import getdate
from lotus_farm.controls import lock
from lotus_farm.lotus_weekly_ribbon_2026 import FARM, _referenced


def preview():
    first = frappe.db.get_value(
        "Bunch Tag",
        {"farm": FARM, "source_kind": "Lotus Weekly", "enabled": 1},
        "valid_from", order_by="valid_from asc",
    )
    if not first:
        frappe.throw("Chưa có lịch màu dây Lotus theo tuần.")
    old = frappe.get_all(
        "Bunch Tag",
        filters={"farm": FARM, "enabled": 1, "process_adoption": ["is", "set"]},
        fields=["name", "tag_code", "valid_from", "valid_to"],
        limit_page_length=5000,
    )
    old = [row for row in old if not row.valid_to or getdate(row.valid_to) >= getdate(first)]
    conflicts = [row.tag_code for row in old if _referenced(row.name)]
    return {"farm": FARM, "weekly_start": str(first), "retire_count": len(old),
            "conflicts": conflicts}


def apply():
    frappe.only_for("System Manager")
    lock("Farm", FARM)
    state = preview()
    if state["conflicts"]:
        frappe.throw("Các kỳ 5 ngày đã có chứng từ, không thể ngừng: " + ", ".join(state["conflicts"]))
    for row in frappe.get_all(
        "Bunch Tag",
        filters={"farm": FARM, "enabled": 1, "process_adoption": ["is", "set"]},
        fields=["name", "valid_to"],
        limit_page_length=5000,
    ):
        if row.valid_to and getdate(row.valid_to) < getdate(state["weekly_start"]):
            continue
        doc = frappe.get_doc("Bunch Tag", row.name)
        doc.enabled = 0
        doc.save()
    frappe.db.commit()
    result = {"farm": FARM, "retired_reference_periods": state["retire_count"],
              "active_weekly_periods": frappe.db.count("Bunch Tag",
                  {"farm": FARM, "source_kind": "Lotus Weekly", "enabled": 1}),
              "weekly_start": state["weekly_start"]}
    print("Retired five-day reference schedule:", result)
    return result
