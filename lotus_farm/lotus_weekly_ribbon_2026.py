"""Import the Lotus-222 twelve-colour weekly ribbon cycle (ISO 2026 W43 to the end of 2027).

Source: the farm's colour table sent by the user on 29/10/2026. One colour per ISO week, in a fixed
12-week cycle starting W43/2026 = Đỏ. In the field the first and second ties of a week are marked
"2 dây" / "1 dây", but they are the same colour and the same cohort; the two halves (Mon–Thu, Fri–Sun)
are kept only because Bunch Tag validates Lotus Weekly periods per half week.
Run once as administrator from bench execute; repeat runs create nothing new.
"""
import frappe
from lotus_farm.controls import lock
from lotus_farm.ribbon_cycle import FARM, periods  # FARM is re-exported for lotus_weekly_calendar_guard


def _referenced(tag_name):
    for dt, field in (("Bunch Operation", "bunch_tag"),
                      ("Fruit Measurement", "ribbon_color"),
                      ("Harvest Actual", "ribbon_color")):
        if frappe.db.exists(dt, {field: tag_name}):
            return True
    return False


def preview():
    rows = list(periods())
    codes = {r["tag_code"] for r in rows}
    current = frappe.get_all("Bunch Tag", filters={"farm": FARM, "source_kind": "Lotus Weekly"},
                             fields=["name", "tag_code", "enabled"], limit_page_length=5000)
    stale = [x for x in current if x.tag_code not in codes]
    return dict(farm=FARM, start=rows[0]["valid_from"], end=rows[-1]["valid_to"], periods=rows,
                existing=len(current) - len(stale), stale=[x.tag_code for x in stale],
                conflicts=[x.tag_code for x in stale if _referenced(x.name)])


def apply():
    frappe.only_for("System Manager")
    lock("Farm", FARM)
    plan = preview()
    if plan["conflicts"]:
        frappe.throw("Màu dây cũ đã gắn chứng từ, không được thay: " + ", ".join(plan["conflicts"]))
    existing = {x.tag_code: x for x in frappe.get_all("Bunch Tag", filters={"farm": FARM, "source_kind": "Lotus Weekly"},
        fields=["name", "tag_code", "color_code", "valid_from", "valid_to", "enabled"], limit_page_length=5000)}
    # The superseded weekly schedule (W43–W50 sent 28/10) was never used, so it is removed, not kept disabled.
    for code in plan["stale"]:
        frappe.delete_doc("Bunch Tag", existing[code].name, force=True, ignore_permissions=True)
    created = 0
    for row in plan["periods"]:
        if row["tag_code"] in existing:
            continue
        frappe.get_doc({"doctype": "Bunch Tag", "farm": FARM, "period_basis": "Cut Bud",
                        "source_kind": "Lotus Weekly", "enabled": 1, **row}).insert()
        created += 1
    frappe.db.commit()
    result = dict(created=created, removed=len(plan["stale"]), periods=len(plan["periods"]),
                  start=plan["start"], end=plan["end"])
    print("Imported Lotus 12-colour weekly ribbon cycle", result)
    return result
