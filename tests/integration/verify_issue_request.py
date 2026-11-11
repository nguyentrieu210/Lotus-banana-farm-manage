"""Spec 005, yêu cầu cấp vật tư end to end on a copy of the live site (Vườn 222): the đội trưởng enters and approves,
Kho issues against it, the 621 cost carries the lô and việc of the request, close / reopen / cancel and their guards.
Temporary users, item and stock; everything runs in one transaction and is rolled back. Never on production.

    python /tmp/lt/tests/integration/run_from_tmp.py verify_issue_request
"""
import json
import os
import sys

import frappe
from frappe.utils import add_days, flt, nowdate

if "__file__" in globals():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SITE = os.environ.get("SITE", "frontend")
FARM = os.environ.get("FARM", "LOTUS-222")

frappe.init(site=SITE, sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

import issue_request_fixture as fx  # noqa: E402
from lotus_farm import field_report as field  # noqa: E402
from lotus_farm import issue_request as api  # noqa: E402
from lotus_farm import issue_request_rules as rules  # noqa: E402
from lotus_farm import push_notifications, warehouse  # noqa: E402

failures = []


def check(label, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + label + (f" -> {detail}" if not ok and detail != "" else ""))
    if not ok:
        failures.append(label)


def refused(label, fn, kind=(frappe.ValidationError, frappe.PermissionError)):
    frappe.db.savepoint("issue_refused")
    try:
        fn()
    except kind:
        frappe.db.rollback(save_point="issue_refused")
        frappe.clear_messages()
        check(label, True)
    except Exception as e:
        frappe.db.rollback(save_point="issue_refused")
        check(label, False, repr(e))
    else:
        frappe.db.rollback(save_point="issue_refused")
        check(label, False, "no error")


def alerts(name, title_part):
    return frappe.get_all("Lotus Mobile Alert", filters={"document_name": name, "title": ["like", f"%{title_part}%"]}, fields=["user", "title", "app"])


def post(result):
    doc = frappe.get_doc("Stock Entry", result["name"])
    return warehouse.submit_document("Stock Entry", doc.name, modified=str(doc.modified))


try:
    farm_doc = frappe.get_doc("Farm", FARM)
    company, today = farm_doc.company, nowdate()
    crew, members, lots = fx.crew_with_teams(FARM)
    team = members[0]
    who = fx.people(FARM, crew.name, team)
    store = frappe.db.get_value("Warehouse", {"company": company, "is_group": 0, "disabled": 0}, "name")
    employee = frappe.db.get_value("Employee", {"company": company, "status": "Active"}, "name")
    works = field._works(FARM)
    work = next((w for w in works if w.lotus_requires_material), works[0])
    group = frappe.db.get_value("Item Group", {"is_group": 0}, "name")
    tag = frappe.generate_hash(length=6).upper()
    items = []
    for n, uom in ((1, frappe.db.get_value("Item", {"is_stock_item": 1, "has_batch_no": 0}, "stock_uom") or "Nos"), (2, "Nos")):
        code = f"UAT-ISSUE-{tag}-{n}"
        frappe.get_doc(dict(doctype="Item", item_code=code, item_name=f"Vật tư thử cấp {n}", item_group=group, stock_uom=uom,
                            is_stock_item=1)).insert(ignore_permissions=True)
        items.append(code)
    received = warehouse.create_draft(company=company, kind="receipt", posting_date=today, target=store, receipt_reason="Surplus",
                                      notes="Spec 005 test stock", lines=[dict(item=i, qty=100, rate=1000) for i in items])
    post(received)
    A, B = lots[0], lots[1]
    codes = {b: frappe.db.get_value("Farm Block", b, "block_code") for b in (A, B)}
    values = dict(team=team, work_type=work.name, needed=today, warehouse=store, receiver=employee, note="Phun đợt thử",
                  lines=[dict(item_code=i, farm_block=b, qty=3, notes="0,5 lít/ha") for i in items for b in (A, B)])

    # ------------------------------------------------------------ 1. the đội trưởng enters and sends
    data = fx.as_user(who.leader, api.form_data, FARM, crew.name)
    check("form: tổ of the đội, lô of its khu, việc and kho", team in [t["name"] for t in data["teams"]] and
          {A, B} <= {b["name"] for b in data["blocks"]} and store in [w["name"] for w in data["warehouses"]] and data["can_approve"], data.get("approver_label"))
    event = "itest-" + tag
    sent = fx.request(FARM, crew.name, values, who.leader, send=1, event=event)
    name = sent["name"]
    doc = frappe.get_doc("Material Request", name)
    check("a Material Issue with 4 lines waiting for approval", doc.material_request_type == "Material Issue" and doc.docstatus == 0
          and len(doc.items) == 4 and sent["state"] == rules.SENT, (doc.docstatus, len(doc.items), sent["state"]))
    row = doc.items[0]
    check("each line carries lô, vườn, việc, mã lô and kho", row.lotus_farm_block in (A, B) and row.lotus_farm == FARM and row.lotus_work_type == work.name
          and row.lotus_usage_area == codes[row.lotus_farm_block] and row.warehouse == store, row.as_dict())
    check("expected approver is the đội trưởng", doc.lotus_issue_approver == who.leader, doc.lotus_issue_approver)

    # ------------------------------------------------------------ 2. retries
    again = fx.request(FARM, crew.name, values, who.leader, send=1, event=event)
    check("the same client_event_id returns the same request", again["name"] == name)
    refused("the same client_event_id with other content is refused",
            lambda: fx.request(FARM, crew.name, dict(values, note="khác"), who.leader, send=1, event=event))

    # ------------------------------------------------------------ 3. who may not
    refused("a tổ trưởng does not make requests", lambda: fx.request(FARM, crew.name, values, who.team_leader))
    refused("a tổ trưởng does not approve", lambda: fx.as_user(who.team_leader, api.approve, name, str(doc.modified), "t-" + tag))
    refused("doc.submit() outside Lotus is refused (even Administrator)", lambda: frappe.get_doc("Material Request", name).submit())
    refused("frappe.client.submit is refused", lambda: frappe.get_attr("frappe.client.submit")(frappe.get_doc("Material Request", name).as_dict()))
    refused("Desk save of a Lotus request is refused", lambda: frappe.get_doc("Material Request", name).save())
    refused("a lô outside the khu is refused", lambda: fx.request(FARM, crew.name, dict(values, lines=[dict(item_code=items[0], farm_block="NOT-A-LOT", qty=1)]), who.leader))
    refused("a past ngày cần is refused", lambda: fx.request(FARM, crew.name, dict(values, needed=add_days(today, -1)), who.leader))
    refused("two lines of the same vật tư × lô are refused",
            lambda: fx.request(FARM, crew.name, dict(values, lines=[dict(item_code=items[0], farm_block=A, qty=1)] * 2), who.leader))

    # ------------------------------------------------------------ 4. lower and approve
    doc.reload()
    # every line is sent: a line left out of the dict is dropped (rules.lowered); only the first is lowered to 1
    lowered = {r.name: (1 if i == 0 else flt(r.qty)) for i, r in enumerate(doc.items)}
    refused("lowering needs a reason", lambda: fx.as_user(who.leader, api.approve, name, str(doc.modified), "a0-" + tag, json.dumps(lowered)))
    refused("raising is refused", lambda: fx.as_user(who.leader, api.approve, name, str(doc.modified), "a1-" + tag,
                                                    json.dumps({doc.items[0].name: 9}), "nhiều hơn"))
    approved = fx.as_user(who.leader, api.approve, name, str(doc.modified), "a2-" + tag, json.dumps(lowered), "đủ cho A")
    doc.reload()
    check("the đội trưởng approves their own request (chủ vườn 11/11/2026)", doc.docstatus == 1 and doc.status == "Pending"
          and doc.lotus_issue_approved_by == who.leader and approved["state"] == rules.WAITING, (doc.docstatus, doc.status))
    check("the lowered line keeps the new quantity", flt(next(r.qty for r in doc.items if r.name == list(lowered)[0])) == 1)
    check("an APPROVE event by the đội trưởng", frappe.db.exists("Lotus Signature Event", {"document_type": "Material Request", "document_name": name,
                                                                                         "action": "APPROVE", "actor": who.leader}))
    check("history says what was lowered", any("Giảm số" in h["text"] for h in approved["history"]), approved["history"])
    check("no 'Có đề xuất mua mới' for an issue request", not alerts(name, "đề xuất mua") and push_notifications._recipients(doc, "submitted") == [])
    refused("ERPNext stop outside Lotus is refused",
            lambda: frappe.get_attr("erpnext.stock.doctype.material_request.material_request.update_status")(name, "Stopped"))

    # quản lý vườn approves a request sent by the đội trưởng; a request of another đội is not the đội trưởng's to approve
    second = fx.request(FARM, crew.name, dict(values, lines=values["lines"][:1]), who.leader, send=1)
    approved2 = fx.as_user(who.manager, api.approve, second["name"], second["doc"]["modified"], "m-" + tag)
    check("the quản lý vườn approves", approved2["docstatus"] == 1 and approved2["approved_by"] == who.manager)

    # ------------------------------------------------------------ 5. Kho issues part of it
    queue = warehouse.issue_queue(company)
    card = next((r for r in queue["rows"] if r["name"] == name), None)
    check("the request is in Kho's queue", card and card["crew"] == crew.name and card["needed"] == today, card)
    lines = warehouse.issue_lines(company, "Request", name)
    check("issue lines carry the header (kho, người nhận, việc, người duyệt)", lines["header"]["warehouse"] == store and lines["header"]["receiver"] == employee
          and lines["header"]["work_type"] == work.name and lines["header"]["approved_by"] == who.leader, lines["header"])
    first = lines["rows"][0]
    draft = warehouse.create_draft(company=company, kind="issue", posting_date=today, source=store, receiver_employee=employee, issue_mode="Request",
                                   notes="Cấp theo yêu cầu", lines=[dict(item=first["item"], qty=first["remaining_qty"] / 2 if first["remaining_qty"] > 1 else 1,
                                                                        uom=first["stock_uom"], area=first["area"], material_request=name,
                                                                        material_request_item=first["material_request_item"])])
    seen = fx.as_user(who.leader, api.detail, name)
    check("requester sees 'Kho đang lập phiếu' and what it holds", seen["state"] == rules.PICKING and any(l["draft"] > 0 for l in seen["items"]), seen["state"])
    se = frappe.get_doc("Stock Entry", draft["name"])
    other = next(b for b in lots if b not in (A, B)) if len(lots) > 2 else B
    se.items[0].lotus_farm_block = other
    se.items[0].lotus_work_type = None
    se.save()
    se.reload()
    source = frappe.get_doc("Material Request Item", first["material_request_item"])
    check("the issue line takes the lô and việc of the request line, not the client's", se.items[0].lotus_farm_block == source.lotus_farm_block
          and se.items[0].lotus_work_type == work.name, (se.items[0].lotus_farm_block, se.items[0].lotus_work_type))
    post(draft)
    gl = frappe.get_all("GL Entry", filters={"voucher_no": draft["name"], "is_cancelled": 0, "debit": [">", 0]},
                        fields=["account", "lotus_farm_block", "lotus_work_type"])
    if gl:
        check("GL debit carries lô and việc", all(g.lotus_farm_block == source.lotus_farm_block and g.lotus_work_type == work.name for g in gl), gl)
    else:
        print("skip GL check: no ledger posting on this site")
    doc.reload()
    check("request is partly issued", doc.status == "Partially Ordered", doc.status)
    check("requester is told 'Kho đã cấp'", any(a.user == who.leader for a in alerts(name, "Kho đã cấp")))

    # ------------------------------------------------------------ 6. over-issue, then the rest
    left = warehouse.issue_lines(company, "Request", name)["rows"]
    # the first line was lowered to 1 and may be issued in full already: try the over-issue on any line still open
    check("lines still open after a partial issue", bool(left), left)
    row0 = left[0]
    refused("issuing more than is left is refused", lambda: warehouse.create_draft(
        company=company, kind="issue", posting_date=today, source=store, receiver_employee=employee, issue_mode="Request", notes="vượt",
        lines=[dict(item=row0["item"], qty=row0["remaining_qty"] + 1, uom=row0["stock_uom"], area=row0["area"], material_request=name,
                    material_request_item=row0["material_request_item"])]))
    rest = warehouse.create_draft(company=company, kind="issue", posting_date=today, source=store, receiver_employee=employee, issue_mode="Request",
                                  notes="Cấp nốt", lines=[dict(item=r["item"], qty=r["remaining_qty"], uom=r["stock_uom"], area=r["area"],
                                                               material_request=name, material_request_item=r["material_request_item"]) for r in left])
    post(rest)
    doc.reload()
    check("issued in full", doc.status == "Issued" and fx.as_user(who.leader, api.detail, name)["state"] == rules.DONE, doc.status)
    check("a request issued in full is no longer offered", name not in [r["name"] for r in warehouse.issue_sources(company, "Request")["rows"]]
          and name not in [r["name"] for r in warehouse.issue_queue(company)["rows"]])

    # ------------------------------------------------------------ 9. Kho cancels a posted issue
    posted = frappe.get_doc("Stock Entry", rest["name"])
    warehouse.cancel_document("Stock Entry", posted.name, str(posted.modified), "Cấp nhầm, thử hủy")
    doc.reload()
    check("cancelling an issue gives the quantity back", doc.status == "Partially Ordered" and name in [r["name"] for r in warehouse.issue_queue(company)["rows"]], doc.status)
    check("requester is told of the cancelled issue", any(a.user == who.leader for a in alerts(name, "Kho hủy phiếu")))

    # ------------------------------------------------------------ 7. close, reopen, cancel
    third = fx.request(FARM, crew.name, dict(values, lines=values["lines"][:2]), who.leader, approve=1)
    check("Lưu và duyệt in one go", third["docstatus"] == 1 and third["state"] == rules.WAITING, third["state"])
    t = frappe.get_doc("Material Request", third["name"])
    l3 = warehouse.issue_lines(company, "Request", t.name)["rows"][0]
    held = warehouse.create_draft(company=company, kind="issue", posting_date=today, source=store, receiver_employee=employee, issue_mode="Request",
                                  notes="giữ", lines=[dict(item=l3["item"], qty=1, uom=l3["stock_uom"], area=l3["area"], material_request=t.name,
                                                           material_request_item=l3["material_request_item"])])
    refused("closing is refused while Kho holds a draft", lambda: fx.as_user(who.leader, api.close, t.name, str(t.modified), "hết hàng", "c0-" + tag))
    refused("cancelling is refused while an issue exists", lambda: fx.as_user(who.leader, api.cancel, t.name, str(t.modified), "nhầm", "x0-" + tag))
    refused("closing needs a reason", lambda: fx.as_user(who.leader, api.close, t.name, str(t.modified), "", "c1-" + tag))
    frappe.delete_doc("Stock Entry", held["name"], ignore_permissions=True)
    t.reload()
    closed = fx.as_user(who.leader, api.close, t.name, str(t.modified), "Kho hết hàng", "c2-" + tag)
    check("closed", closed["state"] == rules.CLOSED, closed["state"])
    check("Kho cannot pick a closed request", t.name not in [r["name"] for r in warehouse.issue_sources(company, "Request")["rows"]])
    refused("Kho cannot issue against a closed request", lambda: warehouse.issue_lines(company, "Request", t.name))
    t.reload()
    refused("a tổ trưởng cannot reopen", lambda: fx.as_user(who.team_leader, api.reopen, t.name, str(t.modified), "x", "r0-" + tag))
    reopened = fx.as_user(who.leader, api.reopen, t.name, str(t.modified), "Có hàng lại", "r1-" + tag)
    check("reopened", reopened["state"] == rules.WAITING, reopened["state"])
    t.reload()
    cancelled = fx.as_user(who.leader, api.cancel, t.name, str(t.modified), "Không phun nữa", "x1-" + tag)
    check("a request with no issue is cancelled", cancelled["docstatus"] == 2 and cancelled["state"] == rules.CANCELLED)
    doc.reload()
    refused("a request with posted issues cannot be cancelled", lambda: fx.as_user(who.leader, api.cancel, name, str(doc.modified), "x", "x2-" + tag))
    refused("cancel outside Lotus is refused", lambda: frappe.get_doc("Material Request", second["name"]).cancel())

    # draft, withdraw, return, delete
    d = fx.request(FARM, crew.name, dict(values, lines=values["lines"][:1]), who.leader, send=1)
    returned = fx.as_user(who.manager, api.return_request, d["name"], d["doc"]["modified"], "Ghi rõ liều", "rt-" + tag)
    check("the quản lý vườn returns with a reason", returned["state"] == rules.RETURNED and returned["return_reason"] == "Ghi rõ liều")
    refused("Desk delete of a Lotus draft is refused", lambda: frappe.delete_doc("Material Request", d["name"]))
    gone = fx.as_user(who.leader, api.delete_draft, d["name"], returned["doc"]["modified"], "dl-" + tag)
    check("the requester deletes the draft", gone == {"deleted": d["name"]} and not frappe.db.exists("Material Request", d["name"]))

    # ------------------------------------------------------------ US4: phiếu giao việc, vòng chăm sóc, lần trước
    made = fx.as_user(who.leader, field.assign, FARM, crew.name, work.name, team, json.dumps([A]))
    ticket = made["created"][0]
    linked = fx.request(FARM, crew.name, dict(values, lines=[dict(item_code=items[0], farm_block=A, qty=1, assignment=ticket)]), who.leader)
    check("a line can carry its phiếu giao việc", frappe.db.get_value("Material Request Item", {"parent": linked["name"]}, "lotus_work_assignment") == ticket)
    refused("a phiếu of another lô is refused", lambda: fx.request(FARM, crew.name, dict(values, lines=[dict(item_code=items[0], farm_block=B, qty=1, assignment=ticket)]), who.leader))
    by_ticket = fx.as_user(who.leader, api.requests, FARM, crew.name, None, "all", ticket)
    check("requests filtered by phiếu", [r["name"] for r in by_ticket["rows"]] == [linked["name"]], by_ticket["rows"])
    data = fx.as_user(who.leader, api.form_data, FARM, crew.name)
    check("form offers the open phiếu", ticket in [t["name"] for t in data["open_assignments"]])
    check("'lần trước' names its request", any(l["work_type"] == work.name and l["request"] for l in data["last"]), data["last"])
    try:
        from lotus_farm import care_cycle
        due = {(r["farm_block"], r["work_type"]) for r in fx.as_user(who.leader, care_cycle.due, FARM, crew.name)["rows"] if r["status"] != "later"}
        check("lô due by the vòng chăm sóc match care_cycle.due", due == {(r["farm_block"], r["work_type"]) for r in data["due_blocks"]})
    except frappe.ValidationError as e:
        print("skip care cycle check:", e)

    # ------------------------------------------------------------ lists
    listed = fx.as_user(who.leader, api.requests, FARM, crew.name)
    check("the đội trưởng's list has the request and counts", name in [r["name"] for r in listed["rows"]] and listed["counts"]["partial"] >= 1, listed["counts"])
    refused("a user without đội cannot read a request", lambda: fx.as_user(fx.user(FARM, "none", ["Lotus Team Leader"]), api.detail, name))

    # ------------------------------------------------------------ 10-12. planning, month card, print
    from lotus_farm import warehouse_planning, field_reports
    plan = warehouse_planning.snapshot(company, warehouse=store, from_date=today, to_date=today)
    check("planning reads the approved lines with their kho", any(r.get("item") in items for r in plan["rows"]), plan.get("warnings"))
    month = field_reports.month(FARM, today[:7])
    card = next(c for c in month["cards"] if c["key"] == "materials")
    check("the month card counts the issue on the lô", any(r["code"] == codes[A] and r["issued"] > 0 for r in card["rows"]), card["rows"][:5])
    from lotus_farm.www import lotus_material_proposal_print as printing
    printed = printing.build(name)
    check("the request prints for a stock user", bool(printed))
finally:
    frappe.set_user("Administrator")
    frappe.db.rollback()
    frappe.destroy()

print("\nALL PASSED" if not failures else f"\n{len(failures)} FAILED: " + "; ".join(failures))
