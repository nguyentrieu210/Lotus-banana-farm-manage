"""Vòng chăm sóc end to end on a site that has Vườn 222 set up: the quản lý vườn sets cycles, the đội trưởng gives the
lô due to a tổ (several at once, đổi tổ and huỷ with a reason), the tổ reports a lô done and the lô moves to its next
round; khoán cả lô waits for the nghiệm thu. Everything runs in one transaction and is rolled back.

docker exec -i lotus-vps-test-backend-1 bash -lc 'cd /home/frappe/frappe-bench/sites && ../env/bin/python -' < tests/integration/verify_care_cycle.py
"""
import json
import os

import frappe
from frappe.utils import add_days, flt, nowdate

SITE = os.environ.get("SITE", "frontend")
FARM = "LOTUS-222"
ENTRY, ASSIGNMENT = "Lotus Work Entry", "Lotus Work Assignment"

frappe.init(site=SITE)
frappe.connect()

from lotus_farm import care_cycle as cc  # noqa: E402
from lotus_farm import field_report as field  # noqa: E402
from lotus_farm import lot_ledger  # noqa: E402
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
yesterday = str(add_days(day, -1))
start = str(add_days(day, -30))
company = frappe.db.get_value("Farm", FARM, "company")
crew = frappe.get_all("Work Team", filters={"farm": FARM, "lotus_team_level": "Crew"}, pluck="name", order_by="creation asc")[0]
leader = frappe.db.get_value("Work Team", crew, "lotus_leader")
teams = frappe.get_all("Work Team", filters={"lotus_parent_team": crew, "lotus_team_level": "Team"}, pluck="name", order_by="team_name asc")
team, other_team = teams[0], teams[1]
foreman = next(u for u in frappe.get_all("User Permission", filters={"allow": "Farm", "for_value": FARM}, pluck="user")
               if u != leader and not field.is_manager(u) and frappe.db.exists("User", u))
frappe.db.set_value("Work Team", team, "lotus_leader", foreman)
for user, role in ((foreman, field.LEADER), (leader, field.SUPERVISOR)):
    if role not in frappe.get_roles(user):
        frappe.get_doc(dict(doctype="Has Role", parent=user, parenttype="User", parentfield="roles", role=role, name=frappe.generate_hash(length=10))).db_insert()
        frappe.clear_cache(user=user)
blocks = {b.block_code: b.name for b in frappe.get_all("Farm Block", filters={"farm": FARM, "farm_zone": "A", "active": 1}, fields=["name", "block_code"])}
A1, A5, A6 = blocks["A1"], blocks["A5"], blocks["A6"]
works = lot_ledger.works(FARM)
cut_leaf = next(w for w in works.values() if not w["stage"] and w["pay_mode"] == "Lot" and w["uom"] == "Ha")
pipes = next(w for w in works.values() if not w["stage"] and w["pay_mode"] == "Daywork" and not w["requires_material"] and w["group"] == "Field")
frappe.db.delete(ENTRY, {"farm": FARM, "posting_date": ["in", [yesterday, day]], "source_type": ["!=", "Opening Import"]})
frappe.db.delete(lr.REPORT, {"farm": FARM, "report_date": ["in", [yesterday, day]]})
frappe.db.delete("Work Schedule Rule", {"farm": FARM})
frappe.db.sql(f"update `tab{ASSIGNMENT}` set state = 'Cancelled' where farm = %s and kind = 'Round' and state in ('Open', 'Reported', 'Approved', 'Failed')", FARM)
workers = frappe.get_all("Employee", filters={"company": company, "status": "Active"}, pluck="name", limit=2)
e1 = workers[0]
for e in workers:
    frappe.db.set_value("Employee", e, "lotus_work_team", team)
    for on in (yesterday, day):
        for hour in ("06:30:00", "17:30:00"):
            frappe.get_doc({"doctype": "Employee Checkin", "employee": e, "time": f"{on} {hour}", "log_type": "IN"}).insert(ignore_permissions=True)


def cells(work):
    return {r["code"]: r for r in cc.due(FARM, crew)["rows"] if r["work_type"] == work["name"]}


try:
    # ------------------------------------------------------------ the quản lý vườn sets the cycles
    frappe.set_user("Administrator")
    rule = cc.save_rule(FARM, pipes["name"], 14, start)
    check("a new cycle is version 1 and waits for approval", rule["approval_state"] == "Draft" and rule["version"] == 1, rule)
    frappe.set_user(leader)
    check("a cycle waiting for approval makes nothing due", not cells(pipes))
    refused("only the quản lý vườn sets cycles", lambda: cc.save_rule(FARM, pipes["name"], 7, day), frappe.PermissionError)
    frappe.set_user("Administrator")
    cc.approve_rule(rule["name"])
    leaf_rule = cc.save_rule(FARM, cut_leaf["name"], 21, start, farm_zone="a")
    cc.approve_rule(leaf_rule["name"])
    check("a khu cycle is named after the việc and the khu", leaf_rule["rule_name"].endswith("khu A") and leaf_rule["farm_zone"] == "A", leaf_rule)
    v2 = cc.save_rule(FARM, pipes["name"], 10, day, rule_name=rule["rule_name"])
    check("a change is a new version of the same cycle", v2["version"] == 2 and v2["approval_state"] == "Draft", v2)
    refused("one version waiting at a time", lambda: cc.save_rule(FARM, pipes["name"], 12, day, rule_name=rule["rule_name"]))
    cc.delete_rule(v2["name"])
    refused("an approved version is kept", lambda: cc.delete_rule(rule["name"]))
    refused("a cycle needs at least one day", lambda: cc.save_rule(FARM, cut_leaf["name"], 0, day))

    # ------------------------------------------------------------ Danh mục and Desk save the rule itself: the same rules hold
    def direct(**values):
        return frappe.get_doc(dict({"doctype": "Work Schedule Rule", "farm": FARM, "rule_name": rule["rule_name"], "work_type": pipes["name"],
                                    "repeat_days": 7, "valid_from": day, "version": 2, "approval_state": "Draft"}, **values)).insert()
    refused("a new version saved directly cannot start approved", lambda: direct(approval_state="Approved"))
    refused("a cycle name stays with its việc", lambda: direct(work_type=cut_leaf["name"]))
    other_draft = direct()
    refused("one version waiting at a time, however it is saved", lambda: direct(version=3))
    cc.delete_rule(other_draft.name)
    listed = cc.rule_list(FARM)
    check("the list shows the cycles in force", {r["name"] for r in listed["rules"] if r["in_force"]} == {rule["name"], leaf_rule["name"]}, listed["rules"])

    # ------------------------------------------------------------ what is due
    frappe.set_user(leader)
    rows = cells(pipes)
    check("every lô of the đội is due under the farm cycle", {"A1", "A5", "A6"} <= set(rows), sorted(rows))
    check("a lô never done is late from the day the cycle starts",
          rows["A1"]["status"] == "overdue" and rows["A1"]["overdue_days"] == 30 and rows["A1"]["last_done"] is None, rows.get("A1"))
    check("a khu cycle covers only its khu", cells(cut_leaf) and all(r["zone"] == "A" for r in cells(cut_leaf).values()))
    before = next(s for s in cc.due(FARM, crew)["summary"] if s["work_type"] == pipes["name"])

    # ------------------------------------------------------------ giao, đổi tổ, huỷ
    out = cc.assign(FARM, pipes["name"], json.dumps([A1, A5]), team)
    check("two lô given at once make two phiếu", len(out["created"]) == 2, out)
    given = {frappe.db.get_value(ASSIGNMENT, n, "farm_block"): n for n in out["created"]}
    check("each phiếu keeps the cycle it was given under", all(frappe.db.get_value(ASSIGNMENT, n, "cycle_rule") == rule["name"] for n in out["created"]))
    rows = cells(pipes)
    check("the due list says which tổ has the lô", rows["A1"]["work_team"] == team and rows["A6"]["assignment"] is None, (rows["A1"], rows["A6"]))
    after = next(s for s in cc.due(FARM, crew)["summary"] if s["work_type"] == pipes["name"])
    check("two lô fewer left to give", after["to_give"] == before["to_give"] - 2 and after["given"] == before["given"] + 2, (before, after))
    refused("a lô with an open phiếu for the việc is not given twice", lambda: cc.assign(FARM, pipes["name"], json.dumps([A1, A6]), other_team))
    frappe.set_user(foreman)
    refused("a tổ trưởng does not give work", lambda: cc.assign(FARM, pipes["name"], json.dumps([A6]), team), frappe.PermissionError)
    frappe.set_user(leader)
    refused("đổi tổ needs a reason", lambda: cc.reassign(given[A5], other_team, " "))
    cc.reassign(given[A5], other_team, "Tổ 1 thiếu người")
    check("đổi tổ", frappe.db.get_value(ASSIGNMENT, given[A5], "work_team") == other_team)
    refused("huỷ needs a reason", lambda: cc.cancel(given[A5], ""))
    cc.cancel(given[A5], "Lô đang tưới")
    check("a cancelled phiếu puts the lô back on the list to give",
          frappe.db.get_value(ASSIGNMENT, given[A5], "state") == "Cancelled" and cells(pipes)["A5"]["assignment"] is None)

    # ------------------------------------------------------------ the tổ reports A1 done; the lô moves to its next round
    frappe.set_user(foreman)
    first = lr.open_report(FARM, team, yesterday)["name"]
    out = lr.save_lot(first, A1, [{"work_type": pipes["name"], "qty": 0.5, "people": [{"employee": e1, "morning": 1}]}])
    check("a day of work that does not finish the lô", out["saved"] == 1 and not out["errors"], out)
    lr.send(first)
    frappe.set_user(leader)
    lr.confirm(first)
    check("work not reported done leaves the lô late", cells(pipes)["A1"]["status"] == "overdue" and cells(pipes)["A1"]["last_done"] is None)
    check("and the phiếu open", frappe.db.get_value(ASSIGNMENT, given[A1], "state") == "Open")
    frappe.set_user(foreman)
    report = lr.open_report(FARM, team, day)["name"]
    lot_a1 = next(l for l in lr.today(FARM, team, day)["lots"] if l["block"] == A1)
    check("the phiếu shows on the tổ's day", any(a["name"] == given[A1] for a in lot_a1["assignments"]), lot_a1["assignments"])
    out = lr.save_lot(report, A1, [{"work_type": pipes["name"], "qty": 0.5, "done": 1, "people": [{"employee": e1, "afternoon": 1}]}])
    check("the tổ reports A1 done", out["saved"] == 1 and not out["errors"], out)
    line = frappe.get_all(ENTRY, filters={"daily_report": report, "farm_block": A1, "done": 1}, fields=["name", "assignment"])[0]
    check("the line is on the phiếu", line.assignment == given[A1], line)
    lr.send(report)
    frappe.set_user(leader)
    lr.confirm(report)
    task = frappe.get_doc(ASSIGNMENT, given[A1])
    check("công nhật: confirming the day closes the phiếu with its report",
          task.state == "Locked" and task.done_report == report and task.done_line == line.name and str(task.done_date) == day,
          (task.state, task.done_report, task.done_line, task.done_date))
    a1 = cells(pipes)["A1"]
    check("A1 moves to the next round: due 14 days after the day it was done",
          a1["last_done"] == day and a1["due_date"] == str(add_days(day, 14)) and a1["overdue_days"] == 0 and a1["assignment"] is None, a1)

    # ------------------------------------------------------------ khoán cả lô waits for the nghiệm thu
    out = cc.assign(FARM, cut_leaf["name"], json.dumps([A6]), team)
    leaf_task = out["created"][0]
    lr.reopen(report, "cắt lá A6")
    frappe.set_user(foreman)
    area = flt(frappe.db.get_value("Farm Block", A6, "area_ha"))
    out = lr.save_lot(report, A6, [{"work_type": cut_leaf["name"], "qty": area, "done": 1, "people": [{"employee": e1, "morning": 1}]}])
    check("the tổ reports cắt lá A6 done", out["saved"] == 1 and not out["errors"], out)
    lr.send(report)
    frappe.set_user(leader)
    lr.confirm(report)
    check("khoán cả lô waits for the nghiệm thu after the day is confirmed", frappe.db.get_value(ASSIGNMENT, leaf_task, "state") == "Approved")
    check("the lô is done with cắt lá all the same", cells(cut_leaf)["A6"]["last_done"] == day)
    refused("the đội trưởng does not inspect his own đội", lambda: field.inspect(leaf_task, 10, 10), frappe.PermissionError)
    frappe.set_user("Administrator")
    field.inspect(leaf_task, 10, 10)
    task = frappe.get_doc(ASSIGNMENT, leaf_task)
    check("passing the nghiệm thu locks the lô and pays it", task.state == "Locked" and flt(task.amount) > 0, (task.state, task.amount))
finally:
    frappe.set_user("Administrator")
    frappe.db.rollback()

print("\nALL PASSED" if not failures else f"\n{len(failures)} FAILED: " + "; ".join(failures))
