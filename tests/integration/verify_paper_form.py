"""Phiếu giấy và đọc ảnh phiếu end to end on a site that has Vườn 222 set up. The model call is replaced by fixed cells,
so no AI key is used. Everything runs in one transaction and is rolled back.

docker exec -i lotus-vps-test-backend-1 bash -lc 'cd /home/frappe/frappe-bench/sites && ../env/bin/python -' < tests/integration/verify_paper_form.py
"""
import os

import frappe
from frappe.utils import nowdate

SITE = os.environ.get("SITE", "frontend")
FARM = "LOTUS-222"
ENTRY = "Lotus Work Entry"

frappe.init(site=SITE)
frappe.connect()

from lotus_farm import document_ai  # noqa: E402
from lotus_farm import field_report as field  # noqa: E402
from lotus_farm import lot_paper_form as paper  # noqa: E402
from lotus_farm import lot_report as lr  # noqa: E402

failures = []


def check(label, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + label + (f" -> {detail}" if not ok and detail != "" else ""))
    if not ok:
        failures.append(label)


def refused(label, fn, kind=frappe.ValidationError):
    try:
        fn()
    except kind:
        frappe.clear_messages()
        check(label, True)
    except Exception as e:
        check(label, False, repr(e))
    else:
        check(label, False, "no error")


day = nowdate()
company = frappe.db.get_value("Farm", FARM, "company")
crew = frappe.get_all("Work Team", filters={"farm": FARM, "lotus_team_level": "Crew"}, pluck="name", order_by="creation asc")[0]
leader = frappe.db.get_value("Work Team", crew, "lotus_leader")
team = frappe.get_all("Work Team", filters={"lotus_parent_team": crew, "lotus_team_level": "Team"}, pluck="name", order_by="team_name asc")[0]
foreman = next(u for u in frappe.get_all("User Permission", filters={"allow": "Farm", "for_value": FARM}, pluck="user")
               if u != leader and not field.is_manager(u) and frappe.db.exists("User", u))
frappe.db.set_value("Work Team", team, "lotus_leader", foreman)
for user, role in ((foreman, field.LEADER), (leader, field.SUPERVISOR)):
    if role not in frappe.get_roles(user):
        frappe.get_doc(dict(doctype="Has Role", parent=user, parenttype="User", parentfield="roles", role=role, name=frappe.generate_hash(length=10))).db_insert()
        frappe.clear_cache(user=user)
frappe.db.delete(ENTRY, {"farm": FARM, "posting_date": day, "source_type": ["!=", "Opening Import"]})
frappe.db.delete(lr.REPORT, {"farm": FARM, "report_date": day})
workers = frappe.get_all("Employee", filters={"company": company, "status": "Active"}, pluck="name", limit=2)
for e in workers:
    frappe.db.set_value("Employee", e, "lotus_work_team", team)
    for hour in ("06:30:00", "17:30:00"):
        frappe.get_doc({"doctype": "Employee Checkin", "employee": e, "time": f"{day} {hour}", "log_type": "IN"}).insert(ignore_permissions=True)
blocks = {b.block_code: b.name for b in frappe.get_all("Farm Block", filters={"farm": FARM, "farm_zone": "A", "active": 1}, fields=["name", "block_code"])}
leaf = frappe.db.get_value("Work Type", {"work_name": "Cắt lá"}, "name")

try:
    # The tổ is given cắt lá on A1 and A2, so the form has rows for them and a cắt lá column.
    frappe.set_user(leader)
    field.assign(FARM, crew, leaf, team, frappe.as_json([blocks["A1"], blocks["A2"]]))
    frappe.set_user(foreman)
    printed = paper.form_url(FARM, team, day)
    report = printed["report"]["name"]
    form = frappe.parse_json(frappe.db.get_value(lr.REPORT, report, "machine_draft"))["form"]
    codes = {c["work_type"]: c["code"] for c in form["columns"]}
    check("the form fixes its columns: bunch stages first, then the việc given", leaf in codes and codes[leaf] == form["columns"][-1]["code"], form["columns"])
    check("the form lists the lô given to the tổ", {"A1", "A2"} <= {r["code"] for r in form["rows"]}, form["rows"])
    check("the print page has the report code to read the photo back", printed["url"].endswith(report))
    frappe.form_dict.report = report
    from lotus_farm.www import lotus_daily_form
    page = frappe._dict()
    lotus_daily_form.get_context(page)
    check("the print page shows the code, the lô and the column codes",
          report in str(page.html) and ">A1<" in str(page.html) and codes[leaf] in str(page.html))
    cut = next(c["code"] for c in form["columns"] if c["stage"] == "Cut Bud")

    # A lô entered by hand before the photo keeps its numbers.
    works = {w["stage"]: w["name"] for w in lr.today(FARM, team, day)["works"] if w["stage"]}
    lr.save_lot(report, blocks["A2"], [{"work_type": works["Cut Bud"], "qty": 7, "people": [{"employee": workers[0], "morning": 1}]}])

    cells = [{"lot": "A1", "col": cut, "qty": 12}, {"lot": "A1", "col": codes[leaf], "qty": 1.2, "done": True},
             {"lot": "A2", "col": cut, "qty": 9}, {"lot": "Z9", "col": cut, "qty": 3}]
    original = document_ai.read_photo
    document_ai.read_photo = lambda file_url, prompt, max_tokens=3000: {"report": report, "cells": cells}
    try:
        read = paper.read_photo(report, "/private/files/phieu-test.jpg")
    finally:
        document_ai.read_photo = original
    check("the photo gives draft lines for the lô without hand-entered numbers", read["lots"] == ["A1"] and read["lines"] == 2, read)
    check("a lô on the photo but not on the form, and a lô already entered, are notes",
          any("Z9" in n for n in read["notes"]) and any("A2 đã có số nhập tay" in n for n in read["notes"]), read["notes"])
    machine = frappe.get_all(ENTRY, filters={"daily_report": report, "farm_block": blocks["A1"]}, fields=["name", "qty", "done", "machine_read", "review_flags", "source_type", "bunch_tag"])
    check("machine lines are marked and wait for a check", len(machine) == 2 and all(m.machine_read and m.review_flags and m.source_type == "Photo" for m in machine), machine)
    check("cắt bắp takes the ribbon of the day; cắt lá keeps 'xong cả lô'",
          any(m.qty == 12 and m.bunch_tag for m in machine) and any(m.qty == 1.2 and m.done for m in machine), machine)
    check("the people present are on the machine lines",
          frappe.db.count("Lotus Work Entry Person", {"parent": ["in", [m.name for m in machine]]}) == 2 * len(workers))
    refused("a report with machine lines not checked cannot be sent", lambda: lr.send(report))
    # The tổ trưởng opens A1, checks the numbers and saves: the flags go.
    lot = next(l for l in lr.today(FARM, team, day)["lots"] if l["block"] == blocks["A1"])
    payload = [{"work_type": l.work_type, "qty": l.qty, "done": l.done, "bunch_tag": l.bunch_tag, "machine_read": 1,
                "people": [{"employee": p["employee"], "morning": p["morning"], "afternoon": p["afternoon"]} for p in l.people]} for l in lot["lines"]]
    saved = lr.save_lot(report, blocks["A1"], payload)
    check("saving the checked lô clears the flags", not saved["errors"] and not frappe.db.exists(ENTRY, {"daily_report": report, "review_flags": ["is", "set"]}), saved)
    sent = lr.send(report)
    check("then the report can be sent", sent["state"] == "Sent", sent)
    refused("a sent report is not read again", lambda: paper.read_photo(report, "/private/files/phieu-test.jpg"))
finally:
    frappe.set_user("Administrator")
    frappe.db.rollback()

print("\nALL PASSED" if not failures else f"\n{len(failures)} FAILED: " + "; ".join(failures))
