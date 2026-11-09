"""The daily bunch sheet end to end on a site that has Vườn 222 set up. Everything runs in one transaction and is rolled back.

docker exec -i ... python - < tests/integration/verify_bunch_forecast.py
"""
import json

import frappe
from frappe.utils import nowdate

SITE = "frontend"
FARM = "LOTUS-222"
EVENT = "Lotus Bunch Event"

frappe.init(site=SITE)
frappe.connect()

from lotus_farm import bunch_posting as api  # noqa: E402
from lotus_farm import field_report as field  # noqa: E402

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


def rows_of(block=None):
    filters = {"farm": FARM, "event_date": day, "state": ["!=", "Voided"]}
    if block:
        filters["farm_block"] = block
    return frappe.get_all(EVENT, filters=filters, fields=["name", "event_type", "qty", "state", "bunch_tag", "entered_by", "confirmed_by"])


day = nowdate()
crew = "9krktf6h66"
leader = frappe.db.get_value("Work Team", crew, "lotus_leader")
teams = frappe.get_all("Work Team", filters={"lotus_parent_team": crew}, pluck="name", order_by="team_name asc")
team, other_team = teams[0], teams[1]
foreman = next(u for u in frappe.get_all("User Permission", filters={"allow": "Farm", "for_value": FARM}, pluck="user")
               if u != leader and not field.is_manager(u) and frappe.db.exists("User", u))
frappe.db.set_value("Work Team", team, "lotus_leader", foreman)
for user, role in ((foreman, field.LEADER), (leader, field.SUPERVISOR)):
    if role not in frappe.get_roles(user):
        frappe.get_doc(dict(doctype="Has Role", parent=user, parenttype="User", parentfield="roles", role=role, name=frappe.generate_hash(length=10))).db_insert()
        frappe.clear_cache(user=user)
blocks = {b.block_code: b.name for b in frappe.get_all("Farm Block", filters={"farm": FARM, "farm_zone": "A"}, fields=["name", "block_code"])}
A1, A5, A6 = blocks["A1"], blocks["A5"], blocks["A6"]
reasons = {r.reason_code: r.name for r in frappe.get_all("Cancellation Reason", fields=["name", "reason_code"])}
reason = reasons["GAY-DO"]
tag = field.ribbon(FARM, day).name
frappe.db.delete(EVENT, {"farm": FARM, "event_date": day})

try:
    # ------------------------------------------------------------ tổ trưởng enters
    frappe.set_user(foreman)
    sheet = api.day_sheet(FARM, crew, day)
    check("foreman sees only their tổ", [t["name"] for t in sheet["teams"]] == [team], sheet["teams"])
    check("sheet carries the ribbon of the day", sheet["ribbon"]["name"] == tag)
    check("sheet lists the lots of the đội", any(b["code"] == "A1" for b in sheet["blocks"]))
    check("sheet lists reject reasons", len(sheet["reasons"]) == 4)
    first = [dict(block=A1, event_type="Bud Injection", qty=10), dict(block=A5, event_type="Cut Bud", qty=120, bunch_tag="ignored"),
             dict(block=A6, event_type="Reject", qty=2, reject_stage="Before Cut", reason=reason)]
    out = api.save_day(FARM, crew, day, team, first)
    check("three lines saved", out["saved"] == 3 and not out["errors"], out)
    cut = [r for r in rows_of(A5)][0]
    check("cut takes the ribbon, not what was sent", cut.bunch_tag == tag)
    check("lines start as Draft by the foreman", cut.state == "Draft" and cut.entered_by == foreman)
    out = api.save_day(FARM, crew, day, team, first)
    check("saving the same sheet changes nothing", out["saved"] == 0 and len(rows_of()) == 3, out)
    second = [dict(first[0], qty=15), first[1]]
    out = api.save_day(FARM, crew, day, team, second)
    check("saving replaces and drops removed lines", out["saved"] == 1 and out["removed"] == 1 and len(rows_of()) == 2, out)
    bad = [dict(block=A1, event_type="Bud Injection", qty=2.5), dict(block=A5, event_type="Cut Bud", qty=999)]
    out = api.save_day(FARM, crew, day, team, bad)
    check("a bad line stops the whole save", out["saved"] == 0 and len(out["errors"]) == 1, out)
    check("nothing changed after the refused save", sum(r.qty for r in rows_of(A5)) == 120)
    over = second + [dict(block=A5, event_type="Harvest", qty=121, bunch_tag=tag, weight_kg=2000)]
    out = api.save_day(FARM, crew, day, team, over)
    check("harvest above the cut of the colour is refused", out["saved"] == 0 and "vượt" in out["errors"][0]["message"], out)
    refused("foreman cannot enter for another tổ", lambda: api.save_day(FARM, crew, day, other_team, second), frappe.PermissionError)
    refused("foreman cannot confirm", lambda: api.confirm_day(FARM, crew, day), frappe.PermissionError)
    refused("no entry for a future day", lambda: api.save_day(FARM, crew, "2099-01-01", team, second))

    # ------------------------------------------------------------ đội trưởng confirms
    frappe.set_user(leader)
    sheet = api.day_sheet(FARM, crew, day)
    check("đội trưởng sees all tổ", len(sheet["teams"]) == len(teams))
    out = api.save_day(FARM, crew, day, other_team, [dict(block=A6, event_type="Bud Injection", qty=7)])
    check("đội trưởng can enter for a tổ", out["saved"] == 1, out)
    out = api.confirm_day(FARM, crew, day)
    check("two confirmed, own line refused", out["confirmed"] == 2 and len(out["errors"]) == 1, out)
    states = {r.event_type: r.state for r in rows_of(A5)}
    check("cut is confirmed", states["Cut Bud"] == "Confirmed")
    check("own line stays Draft", [r.state for r in rows_of(A6)] == ["Draft"])
    frappe.set_user("Administrator")
    out = api.confirm_day(FARM, crew, day)
    check("the manager confirms it", out["confirmed"] == 1, out)
    out = api.confirm_day(FARM, crew, day)
    check("confirming again does nothing", out["confirmed"] == 0 and not out["errors"], out)

    # ------------------------------------------------------------ after confirmation
    frappe.set_user(foreman)
    out = api.save_day(FARM, crew, day, team, second)
    check("same numbers after confirmation are accepted", out["saved"] == 0 and not out["errors"], out)
    out = api.save_day(FARM, crew, day, team, [dict(first[0], qty=99), first[1]])
    check("changed number after confirmation is refused", out["saved"] == 0 and len(out["errors"]) == 1, out)
    harvest = second + [dict(block=A5, event_type="Harvest", qty=100, bunch_tag=tag, weight_kg=1800.5),
                        dict(block=A5, event_type="Reject", qty=20, reject_stage="After Cut", reason=reason, bunch_tag=tag)]
    out = api.save_day(FARM, crew, day, team, harvest)
    check("harvest + reject up to the cut are accepted", out["saved"] == 2 and not out["errors"], out)
    frappe.set_user(leader)
    out = api.confirm_day(FARM, crew, day)
    check("harvest and reject confirmed", out["confirmed"] == 2 and not out["errors"], out)
    cuts, _ = field._bunch_counts(FARM, [tag])
    check("caps count cuts from the ledger", cuts.get((A5, tag)) == 120, cuts)

    event = frappe.get_all(EVENT, filters={"farm_block": A5, "event_date": day, "event_type": "Harvest", "state": "Confirmed"}, pluck="name")[0]
    refused("amend needs a reason", lambda: api.amend(event, {"qty": 90}, ""))
    refused("amend above the cut is refused", lambda: api.amend(event, {"qty": 101}, "đếm lại"))
    frappe.set_user(foreman)
    refused("foreman cannot amend", lambda: api.amend(event, {"qty": 90}, "đếm lại"), frappe.PermissionError)
    frappe.set_user(leader)
    out = api.amend(event, {"qty": 90, "weight_kg": 1620}, "đếm lại")
    old, new = frappe.get_doc(EVENT, out["voided"]), frappe.get_doc(EVENT, out["event"])
    check("old line voided with its reason", old.state == "Voided" and old.void_reason == "đếm lại" and old.qty == 100)
    check("new line carries the correction", new.state == "Confirmed" and new.qty == 90 and new.weight_kg == 1620 and new.confirmed_by == leader)
    refused("a voided line cannot be amended", lambda: api.amend(event, {"qty": 80}, "lại"))
    cut_name = frappe.get_all(EVENT, filters={"farm_block": A5, "event_date": day, "event_type": "Cut Bud", "state": "Confirmed"}, pluck="name")[0]
    refused("cut cannot go below what was used", lambda: api.amend(cut_name, {"qty": 50}, "đếm lại"))
    out = api.amend(new.name, {"qty": 0}, "nhập nhầm")
    check("amending to zero only voids", out["event"] is None and frappe.db.get_value(EVENT, new.name, "state") == "Voided", out)

    # ------------------------------------------------------------ the ledger protects itself
    frappe.set_user("Administrator")
    refused("a confirmed line cannot be deleted", lambda: frappe.delete_doc(EVENT, cut_name, force=True))
    doc = frappe.get_doc(EVENT, cut_name)
    doc.qty = 121
    refused("a confirmed line cannot be edited", lambda: api._store(doc))

    # ------------------------------------------------------------ chọn chồi from a phiếu
    sucker_work = frappe.db.get_value("Work Type", {"lotus_bunch_stage": "Sucker Select", "lotus_farm": FARM}) \
        or frappe.get_all("Work Type", filters={"lotus_bunch_stage": "Sucker Select"}, pluck="name")[0]
    entry = frappe.new_doc("Lotus Work Entry")
    entry.update(dict(farm=FARM, crew=crew, work_team=team, farm_block=A6, work_type=sucker_work, posting_date=day, qty=1, entered_by=foreman,
                      company=frappe.db.get_value("Farm", FARM, "company")))
    entry.flags.ignore_mandatory = entry.flags.ignore_links = True
    field._store(entry)
    trees, area = frappe.db.get_value("Farm Block", A6, ["lotus_tree_count", "area_ha"])
    frappe.set_user(leader)
    pending = api.day_sheet(FARM, crew, day)["suckers"]
    check("confirm screen lists the pending Chọn F", len(pending) == 1 and pending[0]["name"] == entry.name, pending)
    out = api.confirm_day(FARM, crew, day)
    check("Chọn F is written on confirm", out["suckers"] == 1, out)
    posted = frappe.db.get_value("Lotus Work Entry", entry.name, ["posted_event", "confirmed_by"], as_dict=True)
    line = frappe.get_doc(EVENT, posted.posted_event)
    check("entry links its ledger line", posted.confirmed_by == leader and line.source_key == "work-entry:" + entry.name)
    check("estimate = trees x ha / area", line.qty == min(trees, round(trees / area)), line.qty)
    check("lot with bud work: next vụ (FR-026)", line.cycle_no == 3, line.cycle_no)
    out = api.confirm_day(FARM, crew, day)
    check("confirming again writes no second Chọn F", out["suckers"] == 0, out)
    frappe.db.set_value("Lotus Work Entry", entry.name, "qty", 0.5)
    out = api.confirm_day(FARM, crew, day)
    posted2 = frappe.db.get_value("Lotus Work Entry", entry.name, "posted_event")
    check("a changed report replaces its line", out["suckers"] == 1 and posted2 != line.name
          and frappe.db.get_value(EVENT, line.name, "state") == "Voided", out)
    out = api.amend(posted2, {"qty": 0}, "không chọn")
    check("voided Chọn F is not written back", api.confirm_day(FARM, crew, day)["suckers"] == 0, out)

    # ------------------------------------------------------------ the opening book and the 12-week forecast
    from lotus_farm import bunch_opening_import as opening, bunch_opening_rules, block_forecast
    import base64, glob, io, unicodedata
    frappe.set_user("Administrator")
    frappe.db.delete(EVENT, {"farm": FARM})
    frappe.db.delete("Lotus Work Entry", {"name": entry.name})
    import openpyxl
    book = openpyxl.Workbook()
    sheet = book.active
    pad = [None] * 12
    sheet.append(["SỐ LIỆU CẮT BẮP NĂM 2026 FARM 222"])
    sheet.append(["Lô", "Số cây", "c", "d", "e", "ghi chú", "Tuần 43 (19-25/10)", None, "Tuần 44 (26/10-01/11)", None, "Tuần 45 (02/11-08/11)", None, "Tuần 46", None])
    sheet.append([None] * 6 + [" ĐỎ(RÚT)", " ĐỎ", "TRẮNG( RÚT)", " TRẮNG", "TÍM( RÚT)", " TÍM", " CAM", "CAM"])
    data = [("A1", 20, 22, 31, 21), ("A2", 6, 9, 17, 7), ("A3", 7, 10, 20, 6), ("A4", 3, 8, 19, None), ("A5", 13, 6, 17, None), ("A6", 21, 12, 14, None),
            ("A7", 5, 8, 9, None), ("A8", 38, 60, 57, 28), ("A9", None, 15, 22, None), ("A10", None, 16, 10, None), ("A11", None, 8, 7, None),
            ("A12", None, 5, 6, None), ("A13", None, 3, 7, None)]
    for code, a, b, c, e in data:
        sheet.append([code, 1, "#REF!", "#REF!", "#REF!", None, a, None, b, None, c, e, None, None] + pad + [sum(x or 0 for x in (a, b, c, e))])
    sheet.append(["TỔNG"] + [None] * 25 + [593])
    raw = io.BytesIO()
    book.save(raw)
    content = base64.b64encode(raw.getvalue()).decode()

    frappe.set_user(foreman)
    refused("only the manager imports", lambda: opening.preview(FARM, content), frappe.PermissionError)
    frappe.set_user("Administrator")
    before = frappe.db.count(EVENT, {"farm": FARM})
    first_look = opening.preview(FARM, content, "so.xlsx")
    check("preview reads 593 bunches with no errors", first_look["summary"]["bunches"] == 593 and not first_look["errors"], first_look["errors"][:3])
    check("preview colours match the farm's count", {c["label"]: c["bunches"] for c in first_look["summary"]["colours"]} == {"Đỏ": 113, "Trắng": 182, "Tím": 298}, first_look["summary"])
    check("preview writes nothing", frappe.db.count(EVENT, {"farm": FARM}) == before)
    done = opening.commit(FARM, first_look["token"])
    check("commit writes the book", done["bunches"] == 593 and done["skipped"] == 0, done)
    lines = frappe.get_all(EVENT, filters={"farm": FARM}, fields=["source_type", "state", "event_date", "qty", "farm_block", "source_key", "cycle_no"])
    check("lines are confirmed opening balance on vụ 2", all(l.source_type == "Opening Import" and l.state == "Confirmed" and l.cycle_no == 2 for l in lines))
    check("lần 1 is Wednesday, lần 2 Saturday", {str(l.event_date) for l in lines if l.farm_block == A1} == {"2026-10-21", "2026-10-28", "2026-11-04", "2026-11-07"})
    again = opening.preview(FARM, content, "so.xlsx")
    check("second preview finds nothing new", again["summary"]["new_bunches"] == 0 and not again["ready"], again["summary"])
    done = opening.commit(FARM, again["token"])
    check("importing again adds nothing", done["written"] == 0 and sum(l.qty for l in frappe.get_all(EVENT, filters={"farm": FARM}, fields=["qty"])) == 593, done)
    cuts, _ = field._bunch_counts(FARM, [field.ribbon(FARM, "2026-10-21").name])
    check("caps see the opening cuts", cuts.get((A1, field.ribbon(FARM, "2026-10-21").name)) == 20, cuts)

    board = block_forecast.board(FARM)["bunch"]
    expected = sum(r["bunches"] for r in board["rows"])
    check("13 weeks on the board", len(board["weeks"]) == 13)
    check("12 months on the board", len(board["months"]) == 12)
    check("pace shows the real cuts", board["pace"]["last_actual"]["actual"] == 298 and board["pace"]["last_actual"]["number"] == 45, board["pace"]["last_actual"])
    check("coverage counts lots with real numbers", board["coverage"] == {"with_data": 13, "total": 64}, board["coverage"])
    check("containers are worked out", board["totals"]["containers"] > 0 and abs(board["totals"]["containers"] * 1320 - board["totals"]["cartons"]) < 1, board["totals"]["containers"])
    check("each khu says when it starts", set(board["zone_starts"]) == {"A", "B", "C", "D", "E"}, board["zone_starts"])
    # 97% of 593 is 575.2; each lô and colour rounds on its own, so the sum sits a little above it.
    check("the cut layer applies the 97% once", 575 <= board["totals"]["layers"]["cut"] <= 580, board["totals"])
    check("rows add up to the total", expected == board["totals"]["bunches"], (expected, board["totals"]))
    zoned = block_forecast.board(FARM, zone="B")["bunch"]
    check("zone filter keeps other zones out", zoned["totals"]["layers"]["cut"] == 0 and all(r["zone"] == "B" for r in zoned["rows"]), zoned["totals"])
    single = block_forecast.board(FARM, block=A1)["bunch"]
    check("lot filter", single["rows"] and all(r["block"] == A1 for r in single["rows"]))
    row = next(r for r in single["rows"] if r["layer"] == "cut")
    info = block_forecast.trace(FARM, A1, row["week"], "cut", row["tag"], row["cycle"])
    check("trace returns ledger lines and parameters", info["lines"] and info["params"]["min_days"] == 60 and info["groups"], info)

    # A reject comes off the colour; a draft does not change the forecast until it is confirmed.
    tag43 = field.ribbon(FARM, "2026-10-21").name
    frappe.set_user(foreman)
    before_total = block_forecast.board(FARM, block=A5)["bunch"]["totals"]["bunches"]
    out = api.save_day(FARM, crew, day, team, [dict(block=A5, event_type="Reject", qty=5, reject_stage="After Cut", reason=reason, bunch_tag=tag43),
                                               dict(block=A5, event_type="Cut Bud", qty=10)])
    check("foreman records a reject against the opening cut", out["saved"] == 2 and not out["errors"], out)
    frappe.set_user("Administrator")
    check("drafts do not move the forecast", block_forecast.board(FARM, block=A5)["bunch"]["totals"]["bunches"] == before_total)
    frappe.set_user(leader)
    api.confirm_day(FARM, crew, day)
    frappe.set_user("Administrator")
    after = block_forecast.board(FARM, block=A5)["bunch"]["totals"]["bunches"]
    check("confirmed numbers move the forecast", after != before_total, (before_total, after))
    third = opening.preview(FARM, content, "so.xlsx")
    check("a book never overwrites what is in the ledger", not third["errors"] and third["summary"]["new_bunches"] == 0, third["errors"][:2])

    # ------------------------------------------------------------ the layers on real lots
    tree_row = next((r for r in block_forecast.board(FARM)["bunch"]["rows"] if r["layer"] == "tree"), None)
    if tree_row:
        info = block_forecast.trace(FARM, tree_row["block"], tree_row["week"], "tree", None, tree_row["cycle"])
        check("a tree number traces to its count", info["groups"] and info["params"], info)
    a6_before = sum(m["bunches"] for m in block_forecast.board(FARM, block=A6)["bunch"]["months"])
    frappe.set_user(foreman)
    out = api.save_day(FARM, crew, day, team, [dict(block=A6, event_type="Bud Injection", qty=200)])
    frappe.set_user(leader)
    api.confirm_day(FARM, crew, day)
    frappe.set_user("Administrator")
    board_a6 = block_forecast.board(FARM, block=A6)["bunch"]
    months_inject = sum(m["layers"]["inject"] for m in board_a6["months"])
    check("injected bunches appear in the medium layer", 190 <= months_inject <= 200, board_a6["totals"])
    check("confidence is medium", all(r["confidence"] == "medium" for r in board_a6["rows"] if r["layer"] == "inject"))
    a6_after = sum(m["bunches"] for m in board_a6["months"])
    check("the tree layer gave way: bunches moved, not added", abs(a6_after - a6_before) <= 2, (a6_before, a6_after))
    all_months = block_forecast.board(FARM)["bunch"]["months"]
    from lotus_farm import block_forecast as bf
    old, _, _, _ = bf._projection(FARM)
    window = {m["month"] for m in all_months}
    old_total = sum(int(m["bunches"]) for m in old["monthly"] if m["month"] in window)
    new_total = sum(m["bunches"] for m in all_months)
    check("the new total stays close to the tree forecast", abs(new_total - old_total) / old_total < .02, (new_total, old_total))

    # ------------------------------------------------------------ the morning list
    frappe.set_user(leader)
    status = api.day_status(FARM, crew, day)
    check("day status answers", {"pending", "not_reported", "anomalies"} <= set(status), status)
    frappe.set_user(foreman)
    refused("foreman has no morning list", lambda: api.day_status(FARM, crew, day), frappe.PermissionError)
    trees_a7 = frappe.db.get_value("Farm Block", blocks["A7"], "lotus_tree_count")
    out = api.save_day(FARM, crew, day, team, [dict(block=A6, event_type="Bud Injection", qty=200), dict(block=blocks["A7"], event_type="Bud Injection", qty=trees_a7 + 1)])
    frappe.set_user(leader)
    done = api.confirm_day(FARM, crew, day)
    check("confirming above the trees warns with lot and number", any(w["block"] == "A7" and str(trees_a7) in w["message"] for w in done["warnings"]), done)
    check("the warning is also on the morning list", any(a["block"] == "A7" and a["kind"] == "inject" for a in api.day_status(FARM, crew, day)["anomalies"]))

    # ------------------------------------------------------------ the daily reports
    from lotus_farm import bunch_report as report
    frappe.set_user("Administrator")
    stock = report.stock(FARM)
    red = next(c for c in stock["cards"] if c["colour"] == "Đỏ" and c["week"] == 43 and c["lan"] == 1)
    check("stock has a card per colour and half-week", red["cut"] == sum(x[1] or 0 for x in data), red["cut"])
    check("stock left adds up", stock["left"] == sum(c["left"] for c in stock["cards"]) and stock["left"] > 0, stock["left"])
    check("a zone with no cuts has no cards", report.stock(FARM, {"zone": ["B"]})["cards"] == [])
    in_week = report.stock(FARM, {"week": ["2026-W43"]})["cards"]
    check("a week keeps the colours cut in it", {c["week"] for c in in_week} == {43}, [c["week"] for c in in_week])
    numbers = {w["number"] for w in report.cut_weeks(FARM, {"month": ["2026-11"]})["weeks"]}
    check("a month filters cutting", 45 in numbers and 43 not in numbers and 44 not in numbers, numbers)
    check("a year is the whole book", report.stock(FARM, {"year": ["2026"]})["left"] == stock["left"])
    check("colour, lot and khu combine", {c["colour"] for c in report.stock(FARM, {"colour": ["Tím"], "zone": ["A"], "block": ["A1"]})["cards"]} == {"Tím"})
    narrowed = report.stock(FARM, {"colour": ["Đỏ"]})["options"]
    offered = {o["value"] for o in narrowed["week"]}
    check("the lists narrow by the other fields", "2026-W43" in offered and not offered & {"2026-W44", "2026-W45"}, offered)
    check("the opening book has its own tick in Tổ", "Sổ đầu kỳ" in {o["value"] for o in report.stock(FARM)["options"]["team"]})
    check("a list ignores its own filter", {"Đỏ", "Trắng", "Tím"} <= {o["value"] for o in narrowed["colour"]}, narrowed["colour"])
    check("nothing ticked shows nothing", report.stock(FARM, {"zone": []})["cards"] == [])
    teams_stock = report.stock(FARM, {"team": ["no such team"]})
    check("the book has no tổ, so a tổ filter leaves it out", all(c["week"] != 43 for c in teams_stock["cards"]), [c["week"] for c in teams_stock["cards"]])
    parts = report.sections(FARM)
    check("sections answer", {"progress", "injection", "rejects", "harvest", "dashboard", "stock", "cut_weeks", "options"} <= set(parts), list(parts))
    check("the dashboard adds up to the book", parts["dashboard"]["totals"]["cut"] == sum(w["cut"] for w in parts["dashboard"]["weeks"]) >= 593, parts["dashboard"]["totals"])
    check("the pivot rows add up to the same", sum(r["q"] for r in parts["cube"] if r["s"] == "cut") == parts["dashboard"]["totals"]["cut"])
    check("tồn in the pivot rows matches the stock", sum(r["q"] for r in parts["cube"] if r["s"] == "left") == parts["stock"]["left"])
    check("each pivot row names its khu and lô", all(r["z"] and r["b"] for r in parts["cube"]))
    check("one week filters the dashboard", {w["number"] for w in report.sections(FARM, {"week": ["2026-W45"]})["dashboard"]["weeks"]} == {45})
    check("progress starts from the cut colours", any(c["cut"] and c["colour"] == "Đỏ" for c in parts["progress"]), parts["progress"][:1])
    check("injection counts what was recorded", parts["injection"]["injected"] >= 200, parts["injection"]["injected"])
    check("rejects carry a rate", parts["rejects"]["total"] >= 5 and parts["rejects"]["rate"] is not None, parts["rejects"])
    colour_only = report.sections(FARM, {"colour": ["Đỏ"]})
    check("a colour filter keeps chích, which has no colour", colour_only["injection"]["injected"] == parts["injection"]["injected"])
    check("a colour filter narrows progress", all(c["colour"] == "Đỏ" for c in colour_only["progress"]), [c["colour"] for c in colour_only["progress"]])
    weeks = report.cut_weeks(FARM)["weeks"]
    check("cut weeks follow the book", [(w["number"], w["total"]) for w in weeks[:3]][:3] == [(43, 113), (44, 182), (45, 298)] or weeks[0]["total"] == 113, [(w["number"], w["total"]) for w in weeks])
    check("lần 1 and lần 2 are split", weeks[2]["lan1"] == 236 and weeks[2]["lan2"] == 62, weeks[2])
    daily = report.day_report(FARM, None, day, day)
    check("day report groups by tổ", daily["teams"] and all(r["date"] == day for r in daily["rows"]), daily["totals"])
    check("day report shows the opening book nowhere", not any(r["team"] is None for r in daily["rows"]))
    refused("a wrong range is refused", lambda: report.day_report(FARM, None, day, "2000-01-01"))
    report.export_cut_book(FARM)
    import openpyxl as _xl
    exported = _xl.load_workbook(io.BytesIO(frappe.local.response.filecontent), data_only=True).worksheets[0]
    back = bunch_opening_rules.parse(list(exported.iter_rows(values_only=True)))
    check("the exported book reads back", not back["errors"] and back["year"] == 2026, back["errors"][:3])
    first_three = sum(x["qty"] for x in back["lines"] if x["week"] in (43, 44, 45))
    check("the exported book has the same cuts", first_three >= 593, first_three)
    frappe.set_user(foreman)
    check("a tổ trưởng can read the reports", isinstance(report.stock(FARM)["cards"], list))
    frappe.set_user("Administrator")

    # ------------------------------------------------------------ chăm sóc vườn, BVTV, xưởng
    from lotus_farm import work_report as works
    def add_entry(group, stage=None):
        work = frappe.get_all("Work Type", filters=dict(lotus_work_group=group, lotus_farm=FARM, **({"lotus_bunch_stage": stage} if stage else {"lotus_bunch_stage": ["is", "not set"]})), pluck="name", limit=1)[0]
        doc = frappe.new_doc("Lotus Work Entry")
        doc.update(dict(farm=FARM, crew=crew, work_team=team, farm_block=A6, work_type=work, posting_date=day, qty=2, entered_by=foreman, morning_people=4, afternoon_people=2, company=frappe.db.get_value("Farm", FARM, "company")))
        doc.flags.ignore_mandatory = doc.flags.ignore_links = True
        return doc
    care_entry = add_entry("Field")
    field._store(care_entry)
    care = works.field_care(FARM, {"day": [day]})
    check("garden care report sums phiếu per việc", care["entries"] >= 1 and any(r["name"] == care_entry.name for c in care["cards"] for r in c["rows"]), care["entries"])
    check("the garden filter offers tổ and việc", care["options"]["team"] and care["options"]["work"], care["options"])
    check("garden care counts công from buổi", any(r["workdays"] == 3 for c in care["cards"] for r in c["rows"] if r["name"] == care_entry.name))
    spray = add_entry("Protection")
    item = frappe.get_all("Item", pluck="name", limit=1)[0]
    spray.append("materials", dict(item_code=item, qty=1.5, uom="Lít", dose="1/1000", phi_days=7))
    field._store(spray)
    frappe.db.set_value("Farm Block", A6, "lotus_quarantine_until", frappe.utils.add_days(day, 5))
    bvtv = works.protection(FARM, {"day": [day]})
    check("BVTV lists the spray and what it used", any(c["materials"] and c["materials"][0]["item"] == item for c in bvtv["cards"]), bvtv["cards"])
    check("BVTV lists lots under quarantine", [q["days"] for q in bvtv["quarantine"] if q["block"] == A6] == [5], bvtv["quarantine"])
    bag = add_entry("Bunch", "Bag")
    field._store(bag)
    daily2 = report.day_report(FARM, None, day, day)
    check("the bunch day report includes bao buồng from phiếu", daily2["totals"]["Bag"]["qty"] == 2, daily2["totals"]["Bag"])
    bag.db_set("bunch_tag", field.ribbon(FARM, "2026-10-21").name, update_modified=False)
    frappe.db.set_value("Lotus Work Entry", bag.name, "farm_block", A5, update_modified=False)
    tagged = next(c for c in report.sections(FARM)["progress"] if c["tag"] == field.ribbon(FARM, "2026-10-21").name)
    check("progress counts bao buồng from phiếu", tagged["bag"] == 2, tagged)
    press = works.packhouse(FARM, {"day": [day]})
    check("the packhouse report answers empty", press["days"] == [] and press["totals"]["packout"] is None, press["totals"])
    frappe.set_user(foreman)
    check("a tổ trưởng reads the garden report", isinstance(works.field_care(FARM)["cards"], list))
    frappe.set_user("Administrator")

    # ------------------------------------------------------------ frozen copies and the comparison
    from lotus_farm import forecast_snapshot as snap
    frappe.db.delete("Lotus Forecast Snapshot", {"farm": FARM})
    frappe.set_user(foreman)
    refused("only the manager freezes a forecast", lambda: snap.create(FARM), frappe.PermissionError)
    frappe.set_user("Administrator")
    made = snap.create(FARM)
    doc = frappe.get_doc("Lotus Forecast Snapshot", made["name"])
    check("a frozen copy keeps rows and totals", doc.total_bunches > 0 and len(frappe.parse_json(doc.rows_json)) > 0)
    doc.total_kg = 1
    refused("a frozen copy cannot be edited", lambda: field._store(doc))
    refused("a frozen copy cannot be deleted", lambda: frappe.delete_doc("Lotus Forecast Snapshot", made["name"], force=True))
    snap.weekly()
    snap.weekly()
    week_now = snap.bunch_forecast_engine.week_key(frappe.utils.getdate(day))
    check("the Monday job writes one copy a week", frappe.db.count("Lotus Forecast Snapshot", {"farm": FARM, "week_label": week_now, "kind": "Weekly"}) == 1)
    forecast_week = next(r["week"] for r in json.loads(doc.rows_json) if r["layer"] == "cut")
    variance = snap.variance(FARM, forecast_week, forecast_week)
    check("a future week compares against the frozen copy", variance["rows"] and variance["rows"][0]["forecast_bunches"] > 0 and variance["rows"][0]["actual_bunches"] == 0, variance)
    before_params = frappe.get_all("Lotus Block Forecast Profile", fields=["name", "modified"], order_by="name")
    advice = snap.suggest_parameters(FARM)
    check("suggestions change nothing", advice["applied"] is False and before_params == frappe.get_all("Lotus Block Forecast Profile", fields=["name", "modified"], order_by="name"), advice)
finally:
    frappe.set_user("Administrator")
    frappe.db.rollback()
    frappe.clear_cache(user=foreman)
    frappe.clear_cache(user=leader)

print("\n" + ("ALL PASSED" if not failures else f"{len(failures)} FAILED: {failures}"))
