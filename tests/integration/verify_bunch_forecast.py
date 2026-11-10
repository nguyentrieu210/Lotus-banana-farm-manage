"""The daily report of a tổ, the sổ lô behind it and the bunch forecast, end to end on a site that has Vườn 222 set up.
Everything runs in one transaction and is rolled back.

docker exec -i lotus-vps-test-backend-1 bash -lc 'cd /home/frappe/frappe-bench/sites && ../env/bin/python -' < tests/integration/verify_bunch_forecast.py
"""
import json
import os

import frappe
from frappe.utils import nowdate

SITE = os.environ.get("SITE", "frontend")
FARM = "LOTUS-222"
ENTRY = "Lotus Work Entry"

frappe.init(site=SITE)
frappe.connect()

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
blocks = {b.block_code: b.name for b in frappe.get_all("Farm Block", filters={"farm": FARM, "farm_zone": "A"}, fields=["name", "block_code"])}
A1, A5, A6 = blocks["A1"], blocks["A5"], blocks["A6"]
reasons = {r.reason_code: r.name for r in frappe.get_all("Cancellation Reason", fields=["name", "reason_code"])}
reason = reasons["GAY-DO"]
tag = field.ribbon(FARM, day).name
works = {w.stage: w for w in lot_ledger.works(FARM).values() if w.stage}
frappe.db.delete(ENTRY, {"farm": FARM, "posting_date": day})
frappe.db.delete(lr.REPORT, {"farm": FARM, "report_date": day})


def as_line(row):
    line = {k: v for k, v in row.items() if k not in ("block", "event_type")}
    line["work_type"] = works[row["event_type"]].name
    return line


def report_name(of_team, user):
    frappe.set_user(user)
    return lr.open_report(FARM, of_team, day)["name"]


def put(of_team, user, rows, on_day=None):
    """Save rows (block + event_type) on the tổ's report of the day, lô by lô; lô of the report left out are emptied."""
    frappe.set_user(user)
    report = lr.open_report(FARM, of_team, on_day or day)["name"]
    by_block = {}
    for row in rows:
        by_block.setdefault(row["block"], []).append(as_line(row))
    for block in {l.farm_block for l in frappe.get_all(ENTRY, filters={"daily_report": report, "state": "Draft"}, fields=["farm_block"])}:
        by_block.setdefault(block, [])
    out = {"saved": 0, "removed": 0, "errors": []}
    for block, lines in by_block.items():
        result = lr.save_lot(report, block, lines)
        for k in ("saved", "removed"):
            out[k] += result[k]
        out["errors"] += result["errors"]
    return out


def confirm(of_team, sender, confirmer):
    report = report_name(of_team, sender)
    if frappe.db.get_value(lr.REPORT, report, "state") in ("Draft", "Reopened"):
        lr.send(report)
    frappe.set_user(confirmer)
    return lr.confirm(report)


def reopen(of_team, why="bổ sung"):
    report = frappe.db.get_value(lr.REPORT, {"farm": FARM, "work_team": of_team, "report_date": day})
    if frappe.db.get_value(lr.REPORT, report, "state") in ("Sent", "Confirmed"):
        frappe.set_user(leader)
        lr.reopen(report, why)


def rows_of(block=None):
    filters = {"farm": FARM, "posting_date": day, "state": ["!=", "Voided"]}
    if block:
        filters["farm_block"] = block
    return frappe.get_all(ENTRY, filters=filters, fields=["name", "stage", "qty", "state", "bunch_tag", "entered_by", "confirmed_by"])


try:
    # ------------------------------------------------------------ tổ trưởng enters
    frappe.set_user(foreman)
    sheet = lr.today(FARM, team, day)
    check("foreman may enter for their tổ", sheet["rights"]["write"] and not sheet["rights"]["confirm"], sheet["rights"])
    check("today carries the ribbon of the day", sheet["ribbon"]["name"] == tag)
    check("today lists the lots of the đội", any(b["code"] == "A1" for b in sheet["blocks"]))
    check("today lists reject reasons", len(sheet["reasons"]) == 4)
    first = [dict(block=A1, event_type="Bud Injection", qty=10), dict(block=A5, event_type="Cut Bud", qty=120, bunch_tag="ignored"),
             dict(block=A6, event_type="Reject", qty=2, reject_stage="Before Cut", reason=reason)]
    out = put(team, foreman, first)
    check("three lines saved", out["saved"] == 3 and not out["errors"], out)
    cut = rows_of(A5)[0]
    check("cut takes the ribbon, not what was sent", cut.bunch_tag == tag)
    check("lines start as Draft by the foreman", cut.state == "Draft" and cut.entered_by == foreman)
    put(team, foreman, first)
    check("saving the same lines again makes no copies", len(rows_of()) == 3)
    second = [dict(first[0], qty=15), first[1]]
    out = put(team, foreman, second)
    check("saving replaces and drops removed lines", out["removed"] == 1 and len(rows_of()) == 2, out)
    report = report_name(team, foreman)
    out = lr.save_lot(report, A1, [as_line(dict(block=A1, event_type="Bud Injection", qty=2.5))])
    check("a bad line stops the save of its lô", out["saved"] == 0 and len(out["errors"]) == 1, out)
    check("nothing changed after the refused save", sum(r.qty for r in rows_of(A1)) == 15)
    out = lr.save_lot(report, A5, [as_line(second[1]), as_line(dict(block=A5, event_type="Harvest", qty=121, bunch_tag=tag, weight_kg=2000))])
    check("harvest above the cut of the colour is refused", out["saved"] == 0 and "vượt" in out["errors"][0]["message"], out)
    refused("the foreman cannot read another tổ's day", lambda: lr.today(FARM, other_team, day), frappe.PermissionError)
    refused("the foreman cannot open another tổ's report", lambda: lr.open_report(FARM, other_team, day), frappe.PermissionError)
    check("reading a day writes nothing", frappe.db.count(lr.REPORT, {"farm": FARM, "work_team": other_team, "report_date": day}) == 0)
    refused("foreman cannot confirm", lambda: lr.confirm(report), frappe.PermissionError)
    check("no report for a future day", lr.today(FARM, team, "2099-01-01")["report"] is None and not lr.today(FARM, team, "2099-01-01")["rights"]["write"])
    refused("a future day cannot be opened", lambda: lr.open_report(FARM, team, "2099-01-01"))

    # ------------------------------------------------------------ đội trưởng confirms
    frappe.set_user(leader)
    out = put(other_team, leader, [dict(block=A6, event_type="Bud Injection", qty=7)])
    check("đội trưởng can enter for a tổ", out["saved"] == 1, out)
    other = report_name(other_team, leader)
    check("entering for a tổ marks the report as nhập hộ", frappe.db.get_value(lr.REPORT, other, "on_behalf") == 1)
    lr.send(other)
    refused("đội trưởng cannot confirm what they entered", lambda: lr.confirm(other))
    frappe.set_user("Administrator")
    lr.confirm(other)
    check("the manager confirms it", [r.state for r in rows_of(A6)] == ["Confirmed"])
    frappe.set_user(foreman)
    lr.send(report)
    refused("a sent report cannot be edited", lambda: lr.save_lot(report, A1, [as_line(first[0])]))
    frappe.set_user(leader)
    lr.confirm(report)
    states = {r.stage: r.state for r in rows_of(A5)}
    check("cut is confirmed", states["Cut Bud"] == "Confirmed")
    refused("confirming again is refused", lambda: lr.confirm(report))

    # ------------------------------------------------------------ after confirmation
    reopen(team, "thêm thu hoạch")
    frappe.set_user(foreman)
    out = lr.save_lot(report, A5, [as_line(dict(block=A5, event_type="Cut Bud", qty=99))])
    check("a confirmed line cannot be changed from the report", out["saved"] == 0 and len(out["errors"]) == 1, out)
    harvest = [dict(block=A5, event_type="Harvest", qty=100, bunch_tag=tag, weight_kg=1800.5),
               dict(block=A5, event_type="Reject", qty=20, reject_stage="After Cut", reason=reason, bunch_tag=tag)]
    out = lr.save_lot(report, A5, [as_line(h) for h in harvest])
    check("harvest + reject up to the cut are accepted", out["saved"] == 2 and not out["errors"], out)
    confirm(team, foreman, leader)
    cuts, _ = field._bunch_counts(FARM, [tag])
    check("caps count cuts from the sổ lô", cuts.get((A5, tag)) == 120, cuts)

    line = frappe.get_all(ENTRY, filters={"farm_block": A5, "posting_date": day, "stage": "Harvest", "state": "Confirmed"}, pluck="name")[0]
    frappe.set_user(leader)
    refused("amend needs a reason", lambda: lr.amend(line, {"qty": 90}, ""))
    refused("amend above the cut is refused", lambda: lr.amend(line, {"qty": 101}, "đếm lại"))
    frappe.set_user(foreman)
    refused("foreman cannot amend", lambda: lr.amend(line, {"qty": 90}, "đếm lại"), frappe.PermissionError)
    frappe.set_user(leader)
    out = lr.amend(line, {"qty": 90, "weight_kg": 1620}, "đếm lại")
    old, new = frappe.get_doc(ENTRY, out["voided"]), frappe.get_doc(ENTRY, out["entry"])
    check("old line voided with its reason", old.state == "Voided" and old.void_reason == "đếm lại" and old.qty == 100)
    check("new line carries the correction", new.state == "Confirmed" and new.qty == 90 and new.weight_kg == 1620 and new.confirmed_by == leader
          and new.replaces == old.name)
    refused("a voided line cannot be amended", lambda: lr.amend(line, {"qty": 80}, "lại"))
    cut_name = frappe.get_all(ENTRY, filters={"farm_block": A5, "posting_date": day, "stage": "Cut Bud", "state": "Confirmed"}, pluck="name")[0]
    refused("cut cannot go below what was used", lambda: lr.amend(cut_name, {"qty": 50}, "đếm lại"))
    out = lr.amend(new.name, {"qty": 0}, "nhập nhầm")
    check("amending to zero only voids", out["entry"] is None and frappe.db.get_value(ENTRY, new.name, "state") == "Voided", out)

    # ------------------------------------------------------------ the sổ lô protects itself
    frappe.set_user("Administrator")
    refused("a confirmed line cannot be deleted", lambda: frappe.delete_doc(ENTRY, cut_name, force=True))
    doc = frappe.get_doc(ENTRY, cut_name)
    doc.qty = 121
    refused("a confirmed line cannot be edited", lambda: lr._store(doc))

    # ------------------------------------------------------------ chọn chồi in hectares
    reopen(team, "chọn chồi")
    trees, area = frappe.db.get_value("Farm Block", A6, ["lotus_tree_count", "area_ha"])
    frappe.set_user(foreman)
    out = lr.save_lot(report, A6, [{"work_type": works["Sucker Select"].name, "area_ha": 1}])
    check("chọn chồi is saved from hectares", out["saved"] == 1 and not out["errors"], out)
    sucker = frappe.get_all(ENTRY, filters={"daily_report": report, "stage": "Sucker Select"}, fields=["qty", "cycle_no", "area_ha"])[0]
    check("estimate = trees x ha / area", sucker.qty == min(trees, round(trees / area)), sucker.qty)
    check("lot with bud work: next vụ (FR-026)", sucker.cycle_no == 3, sucker.cycle_no)
    confirm(team, foreman, leader)

    # ------------------------------------------------------------ the opening book and the 13-week forecast
    from lotus_farm import bunch_opening_import as opening, bunch_opening_rules, block_forecast
    import base64, io
    frappe.set_user("Administrator")
    frappe.db.delete(ENTRY, {"farm": FARM})
    frappe.db.delete(lr.REPORT, {"farm": FARM})
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
    before = frappe.db.count(ENTRY, {"farm": FARM})
    first_look = opening.preview(FARM, content, "so.xlsx")
    check("preview reads 593 bunches with no errors", first_look["summary"]["bunches"] == 593 and not first_look["errors"], first_look["errors"][:3])
    check("preview colours match the farm's count", {c["label"]: c["bunches"] for c in first_look["summary"]["colours"]} == {"Đỏ": 113, "Trắng": 182, "Tím": 298}, first_look["summary"])
    check("preview writes nothing", frappe.db.count(ENTRY, {"farm": FARM}) == before)
    done = opening.commit(FARM, first_look["token"])
    check("commit writes the book", done["bunches"] == 593 and done["skipped"] == 0, done)
    lines = frappe.get_all(ENTRY, filters={"farm": FARM}, fields=["source_type", "state", "posting_date", "qty", "farm_block", "source_key", "cycle_no", "stage"])
    check("lines are confirmed opening cắt bắp on vụ 2", all(l.source_type == "Opening Import" and l.state == "Confirmed" and l.cycle_no == 2 and l.stage == "Cut Bud" for l in lines))
    check("lần 1 is Wednesday, lần 2 Saturday", {str(l.posting_date) for l in lines if l.farm_block == A1} == {"2026-10-21", "2026-10-28", "2026-11-04", "2026-11-07"})
    again = opening.preview(FARM, content, "so.xlsx")
    check("second preview finds nothing new", again["summary"]["new_bunches"] == 0 and not again["ready"], again["summary"])
    done = opening.commit(FARM, again["token"])
    check("importing again adds nothing", done["written"] == 0 and sum(l.qty for l in frappe.get_all(ENTRY, filters={"farm": FARM}, fields=["qty"])) == 593, done)
    cuts, _ = field._bunch_counts(FARM, [field.ribbon(FARM, "2026-10-21").name])
    check("caps see the opening cuts", cuts.get((A1, field.ribbon(FARM, "2026-10-21").name)) == 20, cuts)

    board = block_forecast.board(FARM)["bunch"]
    expected = sum(r["bunches"] for r in board["rows"])
    check("13 weeks on the board", len(board["weeks"]) == 13)
    check("12 months on the board", len(board["months"]) == 12)
    check("pace shows the real cuts", board["pace"]["last_actual"]["actual"] == 298 and board["pace"]["last_actual"]["number"] == 45, board["pace"]["last_actual"])
    check("coverage counts lots with real numbers", board["coverage"] == {"with_data": 13, "total": 64}, board["coverage"])
    check("containers are worked out", board["totals"]["containers"] > 0 and abs(board["totals"]["containers"] * 1320 - board["totals"]["cartons"]) < 1, board["totals"]["containers"])
    check("the cut layer applies the 97% once", 575 <= board["totals"]["layers"]["cut"] <= 580, board["totals"])
    check("rows add up to the total", expected == board["totals"]["bunches"], (expected, board["totals"]))
    zoned = block_forecast.board(FARM, zone="B")["bunch"]
    check("zone filter keeps other zones out", zoned["totals"]["layers"]["cut"] == 0 and all(r["zone"] == "B" for r in zoned["rows"]), zoned["totals"])
    single = block_forecast.board(FARM, block=A1)["bunch"]
    check("lot filter", single["rows"] and all(r["block"] == A1 for r in single["rows"]))
    row = next(r for r in single["rows"] if r["layer"] == "cut")
    info = block_forecast.trace(FARM, A1, row["week"], "cut", row["tag"], row["cycle"])
    check("trace returns sổ lô lines and parameters", info["lines"] and info["params"]["min_days"] == 60 and info["groups"], info)

    # A reject comes off the colour; an unconfirmed line does not change the forecast until it is confirmed.
    tag43 = field.ribbon(FARM, "2026-10-21").name
    before_total = block_forecast.board(FARM, block=A5)["bunch"]["totals"]["bunches"]
    out = put(team, foreman, [dict(block=A5, event_type="Reject", qty=5, reject_stage="After Cut", reason=reason, bunch_tag=tag43),
                              dict(block=A5, event_type="Cut Bud", qty=10)])
    check("foreman records a reject against the opening cut", out["saved"] == 2 and not out["errors"], out)
    frappe.set_user("Administrator")
    check("drafts do not move the forecast", block_forecast.board(FARM, block=A5)["bunch"]["totals"]["bunches"] == before_total)
    confirm(team, foreman, leader)
    frappe.set_user("Administrator")
    after = block_forecast.board(FARM, block=A5)["bunch"]["totals"]["bunches"]
    check("confirmed numbers move the forecast", after != before_total, (before_total, after))
    third = opening.preview(FARM, content, "so.xlsx")
    check("a book never overwrites what is in the sổ lô", not third["errors"] and third["summary"]["new_bunches"] == 0, third["errors"][:2])

    # ------------------------------------------------------------ the layers on real lots
    tree_row = next((r for r in block_forecast.board(FARM)["bunch"]["rows"] if r["layer"] == "tree"), None)
    if tree_row:
        info = block_forecast.trace(FARM, tree_row["block"], tree_row["week"], "tree", None, tree_row["cycle"])
        check("a tree number traces to its count", info["groups"] and info["params"], info)
    a6_before = sum(m["bunches"] for m in block_forecast.board(FARM, block=A6)["bunch"]["months"])
    reopen(team, "chích thêm")
    out = put(team, foreman, [dict(block=A6, event_type="Bud Injection", qty=200)])
    confirm(team, foreman, leader)
    frappe.set_user("Administrator")
    board_a6 = block_forecast.board(FARM, block=A6)["bunch"]
    months_inject = sum(m["layers"]["inject"] for m in board_a6["months"])
    check("injected bunches appear in the medium layer", 190 <= months_inject <= 200, board_a6["totals"])
    check("confidence is medium", all(r["confidence"] == "medium" for r in board_a6["rows"] if r["layer"] == "inject"))
    a6_after = sum(m["bunches"] for m in board_a6["months"])
    check("the tree layer gave way: bunches moved, not added", abs(a6_after - a6_before) <= 2, (a6_before, a6_after))
    all_months = block_forecast.board(FARM)["bunch"]["months"]
    old, _, _, _ = block_forecast._projection(FARM)
    window = {m["month"] for m in all_months}
    old_total = sum(int(m["bunches"]) for m in old["monthly"] if m["month"] in window)
    new_total = sum(m["bunches"] for m in all_months)
    check("the new total stays close to the tree forecast", abs(new_total - old_total) / old_total < .02, (new_total, old_total))

    # ------------------------------------------------------------ the morning list and the tree cap
    frappe.set_user(leader)
    status = lr.status(FARM, crew, day)
    check("status answers per tổ", {"teams", "anomalies", "overdue"} <= set(status) and any(t["team"] == team and t["state"] == "Confirmed" for t in status["teams"]), status)
    frappe.set_user(foreman)
    refused("foreman has no morning list", lambda: lr.status(FARM, crew, day), frappe.PermissionError)
    reopen(team, "chích A7")
    trees_a7 = frappe.db.get_value("Farm Block", blocks["A7"], "lotus_tree_count")
    frappe.set_user(foreman)
    out = lr.save_lot(report_name(team, foreman), blocks["A7"], [as_line(dict(block=blocks["A7"], event_type="Bud Injection", qty=trees_a7 + 1))])
    check("chích bắp above the trees of the lô is refused with lot and number", out["saved"] == 0 and str(trees_a7) in out["errors"][0]["message"], out)

    # ------------------------------------------------------------ the daily reports
    frappe.set_user("Administrator")
    from lotus_farm import ribbon_board
    board = ribbon_board.board(FARM)
    red = next(c for c in board["cards"] if c["colour"] == "Đỏ" and c["week"] == 43 and c["lan"] == 1)
    check("the ribbon board has a card per colour and half-week", red["cut"] == sum(x[1] or 0 for x in data), red["cut"])
    check("the ribbon board left adds up", board["left"] == sum(c["left"] for c in board["cards"]) and board["left"] > 0, board["left"])
    check("each lô of a colour has cut, bag, rejected, harvested, left and its age",
          all({"cut", "bag", "bag_left", "rejected", "harvested", "left", "quarantine_until"} <= set(lot) for lot in red["lots"]) and red["age_weeks"] >= 0, red["lots"][:1])
    check("a lô adds up: left = cut - rejected after cut - harvested",
          all(lot["left"] == max(0, lot["cut"] - lot["rejected"] - lot["harvested"]) for c in board["cards"] for lot in c["lots"]))
    check("a zone with no cuts has no cards", ribbon_board.board(FARM, "B")["cards"] == [])
    due = ribbon_board.harvest_due(FARM)
    check("the due list holds only colours in or past their window, lô with bunches left",
          all(r["status"] in ("due", "overdue") and r["left"] > 0 for r in due), due[:2])
    later = ribbon_board.harvest_due(FARM, str(frappe.utils.add_days(nowdate(), 70)))
    check("a later week has at least what is due now", len(later) >= len(due), (len(later), len(due)))
    from lotus_farm import bunch_report_rules as report_rules
    weeks = report_rules.cut_weeks(lot_ledger.bunch_rows({"farm": FARM, "state": "Confirmed", "event_type": "Cut Bud"}, ribbon_board.FIELDS),
                                   ribbon_board._tags(FARM), ribbon_board._context(FARM).blocks)
    check("lần 1 and lần 2 are split", weeks[2]["lan1"] == 236 and weeks[2]["lan2"] == 62, weeks[2])
    ribbon_board.export_cut_book(FARM)
    exported = openpyxl.load_workbook(io.BytesIO(frappe.local.response.filecontent), data_only=True).worksheets[0]
    back = bunch_opening_rules.parse(list(exported.iter_rows(values_only=True)))
    check("the exported book reads back", not back["errors"] and back["year"] == 2026, back["errors"][:3])

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
    forecast_week = next(r["week"] for r in json.loads(doc.rows_json) if r["layer"] == "cut")
    variance = snap.variance(FARM, forecast_week, forecast_week)
    check("a future week compares against the frozen copy", variance["rows"] and variance["rows"][0]["forecast_bunches"] > 0 and variance["rows"][0]["actual_bunches"] == 0, variance)
    before_params = frappe.get_all("Lotus Block Forecast Profile", fields=["name", "modified"], order_by="name")
    advice = snap.suggest_parameters(FARM)
    check("suggestions change nothing", advice["applied"] is False and before_params == frappe.get_all("Lotus Block Forecast Profile", fields=["name", "modified"], order_by="name"), advice)

    # ------------------------------------------------------------ weekly copies as of 0 giờ Monday, built when someone opens the app
    from lotus_farm import block_forecast as bf
    from lotus_farm import forecast_snapshot_rules as snap_rules
    monday = snap_rules.monday_of(day)
    moment = snap_rules.week_moment(monday)
    # The opening book stands as confirmed ten days before this Monday; what this test confirmed today stays today.
    frappe.db.sql("""update `tabLotus Work Entry` set confirmed_at = %s where farm = %s and state in ('Confirmed', 'Voided')
                     and (source_type = 'Opening Import' or confirmed_at < %s)""", (f"{frappe.utils.add_days(monday, -10)} 08:00:00", FARM, f"{day} 00:00:00"))
    frappe.db.delete("Lotus Forecast Snapshot", {"farm": FARM, "kind": "Weekly"})
    built = snap.ensure_weeks(FARM)
    check("nobody opened the app for weeks: opening it builds the missing Mondays, this one included",
          built == [str(frappe.utils.add_days(monday, -7)), str(monday)], built)
    week_copy = frappe.get_doc("Lotus Forecast Snapshot", {"farm": FARM, "kind": "Weekly", "week_start": monday})
    check("the copy stands for 0 giờ Monday and says what it could not rebuild",
          str(week_copy.as_of) == str(moment) and week_copy.weekly_key == f"{FARM}:{monday}" and "Số cây" in (week_copy.limits or ""),
          (week_copy.as_of, week_copy.weekly_key))
    check("it leaves out what was confirmed after the Monday", 0 < len(bf._bunch_lines(FARM, None, moment)) < len(bf._bunch_lines(FARM)))
    as_then, _ = bf.bunch_summary(FARM, as_of=moment)
    check("its total is the forecast as the sổ lô stood on Monday", week_copy.total_bunches == as_then["totals"]["bunches"],
          (week_copy.total_bunches, as_then["totals"]["bunches"]))
    check("opening the app again builds nothing", snap.ensure_weeks(FARM) == [])
    refused("two sessions at once still keep one copy a week", lambda: snap._write(FARM, "Weekly", as_of=moment), frappe.UniqueValidationError)
    check("a week compares against its own Monday copy", snap._forecast_for(snap._snapshots(FARM), snap_rules.week_key(monday)).name == week_copy.name)
finally:
    frappe.set_user("Administrator")
    frappe.db.rollback()
    frappe.clear_cache(user=foreman)
    frappe.clear_cache(user=leader)

print("\n" + ("ALL PASSED" if not failures else f"{len(failures)} FAILED: {failures}"))
