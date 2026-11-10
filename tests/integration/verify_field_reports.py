"""Báo cáo Sáng nay, Tuần, Tháng on a site that has Vườn 222 set up, over a small week of confirmed sổ lô lines and one
packhouse shift. Everything runs in one transaction and is rolled back.

docker exec -i lotus-vps-test-backend-1 bash -lc 'cd /home/frappe/frappe-bench/sites && ../env/bin/python -' < tests/integration/verify_field_reports.py
"""
import json
import os

import frappe
from frappe.utils import add_days, flt, getdate, nowdate

SITE = os.environ.get("SITE", "frontend")
FARM = "LOTUS-222"
ENTRY = "Lotus Work Entry"

frappe.init(site=SITE)
frappe.connect()

from lotus_farm import field_report as field  # noqa: E402
from lotus_farm import field_reports as reports  # noqa: E402
from lotus_farm import lot_ledger  # noqa: E402
from lotus_farm import lot_ledger_rules as rules  # noqa: E402
from lotus_farm import shift as shift_api  # noqa: E402

failures = []


def check(label, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + label + (f" -> {detail}" if not ok and detail != "" else ""))
    if not ok:
        failures.append(label)


def store(doc):
    token = field._writing.set(True)
    frappe.flags.lotus_ledger_migrating = True
    try:
        doc.save(ignore_permissions=True)
    finally:
        frappe.flags.lotus_ledger_migrating = False
        field._writing.reset(token)
    return doc


today = getdate(nowdate())
monday = today - __import__("datetime").timedelta(days=today.weekday())
company = frappe.db.get_value("Farm", FARM, "company")
works = lot_ledger.works(FARM)
by_stage = {w["stage"]: w for w in works.values() if w["stage"]}
spray = next(w for w in works.values() if w["requires_material"] and not w["stage"])
blocks = {b.block_code: b.name for b in frappe.get_all("Farm Block", filters={"farm": FARM, "farm_zone": "A", "active": 1}, fields=["name", "block_code"])}
A5, A6 = blocks["A5"], blocks["A6"]
tag = frappe.get_all("Bunch Tag", filters={"farm": FARM}, pluck="name", order_by="creation asc", limit=1)[0]
crew = frappe.get_all("Work Team", filters={"farm": FARM, "lotus_team_level": "Crew"}, pluck="name", order_by="creation asc")[0]
leader = frappe.db.get_value("Work Team", crew, "lotus_leader")
if field.SUPERVISOR not in frappe.get_roles(leader):
    frappe.get_doc(dict(doctype="Has Role", parent=leader, parenttype="User", parentfield="roles", role=field.SUPERVISOR, name=frappe.generate_hash(length=10))).db_insert()
    frappe.clear_cache(user=leader)
item = frappe.get_all("Item", filters={"is_stock_item": 1, "disabled": 0}, pluck="name", limit=1)[0]


def line(block, work, qty, on, **values):
    doc = frappe.new_doc(ENTRY)
    materials = values.pop("materials", [])
    doc.update(dict({"farm": FARM, "company": company, "farm_block": block, "work_type": work["name"], "stage": work["stage"] or None,
                     "pay_mode": work["pay_mode"], "posting_date": on, "qty": qty, "uom": work["uom"], "state": rules.CONFIRMED,
                     "source_type": rules.MANUAL, "source_key": "report:" + frappe.generate_hash(length=12), "entered_by": "Administrator",
                     "confirmed_by": "Administrator", "confirmed_at": frappe.utils.now_datetime(), "cycle_no": 2}, **values))
    for m in materials:
        doc.append("materials", m)
    return store(doc)


try:
    frappe.set_user("Administrator")
    for block in (A5, A6):
        line(block, by_stage[rules.CUT], 150, add_days(today, -70), bunch_tag=tag)
    line(A5, by_stage[rules.HARVEST], 100, monday, bunch_tag=tag, weight_kg=2000)
    line(A6, by_stage[rules.HARVEST], 40, monday, bunch_tag=tag, weight_kg=1000)
    line(A5, spray, 1, monday, materials=[{"item_code": item, "qty": 3, "dose": "50 ml / bình"}])
    harvest_lines = {r.farm_block: r.name for r in frappe.get_all(ENTRY, filters={"farm": FARM, "stage": "Harvest", "posting_date": monday,
                                                                                  "source_key": ["like", "report:%"]}, fields=["name", "farm_block"])}
    shift = shift_api.save_shift(FARM, json.dumps({"shift_code": "RPT-1", "posting_date": str(monday), "started_at": f"{monday} 07:00:00",
                                                    "ended_at": f"{monday} 16:00:00", "finished_kg": 2400, "secondary_kg": 300, "cartons": 180,
                                                    "sources": [{"farm_block": A5, "bunch_tag": tag, "bunches": 100, "kg": 2000, "harvest_entry": harvest_lines[A5]},
                                                                {"farm_block": A6, "bunch_tag": tag, "bunches": 40, "kg": 1000, "harvest_entry": harvest_lines[A6]}]}))
    shift_api.close_shift(shift["doc"]["name"])

    # ------------------------------------------------------------ Sáng nay
    frappe.set_user(leader)
    morning = {c["key"]: c for c in reports.morning(FARM)["cards"]}
    check("sáng nay has the six questions", set(morning) == {"not_sent", "waiting", "anomalies", "overdue", "quarantine", "harvest_due"}, list(morning))
    check("every tổ of the đội is either not sent, waiting or done",
          morning["not_sent"]["value"] + morning["waiting"]["value"] <= len(frappe.get_all("Work Team", filters={"lotus_parent_team": crew})) and all(
              "team_name" in r for r in morning["not_sent"]["rows"]))
    check("each card says how to read its rows", all(c["columns"] and all({"field", "label"} <= set(col) for col in c["columns"]) for c in morning.values()))

    # ------------------------------------------------------------ Tuần
    week = reports.week(FARM)
    cards = {c["key"]: c for c in week["cards"]}
    check("the week counts what was harvested", cards["harvest"]["value"] >= 140 and any(r["code"] == "A5" and r["bunches"] == 100 for r in cards["harvest"]["rows"]),
          cards["harvest"]["value"])
    check("the week shows the xưởng", cards["packhouse"]["value"] >= 180 and any(r["shift_code"] == "RPT-1" for r in cards["packhouse"]["rows"]))
    check("work by lô includes the spraying", any(r["code"] == "A5" and r["work_name"] == spray["label"] for r in cards["work"]["rows"]), cards["work"]["rows"][:3])
    status = {r["code"]: r["status"] for r in week["lots"]}
    check("the map knows the lô harvested this week", status.get("A5") in ("harvest", "late", "held") and status.get("A6") in ("harvest", "late", "held"), status)
    check("the forecast card says whether a frozen copy existed", "forecast" in cards and cards["forecast"]["note"])

    # ------------------------------------------------------------ Tháng
    month = {c["key"]: c for c in reports.month(FARM, str(monday)[:7])["cards"]}
    a5 = next(r for r in month["harvest"]["rows"] if r["code"] == "A5")
    check("the month has kg and cartons per bunch per lô", a5["kg_per_bunch"] == 20.0 and abs(flt(a5["cartons_per_bunch"]) - 1.2) < 0.02, a5)
    check("kg per bunch of the farm", month["kg_per_bunch"]["value"] is not None)
    used = [r for r in month["materials"]["rows"] if r["code"] == "A5"]
    check("materials reported used are set against what was issued", used and used[0]["used"] == 3 and used[0]["gap"] == used[0]["issued"] - 3, used)
    check("money and công per lô", "pay" in month and all({"workdays", "count_pay", "lot_pay", "total"} <= set(r) for r in month["pay"]["rows"]))
finally:
    frappe.set_user("Administrator")
    frappe.db.rollback()

print("\nALL PASSED" if not failures else f"\n{len(failures)} FAILED: " + "; ".join(failures))
