"""The sổ lô end to end on a site that has Vườn 222 set up. Everything runs in one transaction and is rolled back.

docker exec -i lotus-vps-test-backend-1 bash -lc 'cd /home/frappe/frappe-bench/sites && ../env/bin/python -' < tests/integration/verify_lot_ledger.py
"""
import os

import frappe
from frappe.utils import add_days, getdate, nowdate

SITE = os.environ.get("SITE", "frontend")
FARM = "LOTUS-222"

frappe.init(site=SITE)
frappe.connect()
frappe.set_user("Administrator")

from lotus_farm import field_report as field  # noqa: E402
from lotus_farm import lot_ledger, lot_ledger_migrate  # noqa: E402
from lotus_farm import lot_ledger_rules as rules  # noqa: E402

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


def store(doc):
    token = field._writing.set(True)
    try:
        doc.save(ignore_permissions=True)
    finally:
        field._writing.reset(token)
    return doc


def line(block, work, day, **values):
    doc = frappe.new_doc(lot_ledger.ENTRY)
    doc.update(dict({"farm": FARM, "farm_block": block, "work_type": work.name, "stage": work.stage or None, "pay_mode": work.pay_mode,
                     "posting_date": day, "qty": 10, "state": rules.DRAFT, "source_type": rules.MANUAL,
                     "source_key": "itest:" + frappe.generate_hash(length=12), "entered_by": "Administrator", "cycle_no": 2}, **values))
    return doc


try:
    # ---------------------------------------------------------------- migration of the bunch ledger
    summary = lot_ledger_migrate._summary(lot_ledger_migrate._plan())
    check("migration already done: nothing left to move", summary["to_move"] == 0, summary)
    opening = frappe.get_all(lot_ledger.ENTRY, filters={"farm": FARM, "source_type": rules.OPENING, "state": rules.CONFIRMED},
                             fields=["qty", "bunch_tag", "stage"])
    colours = {}
    for o in opening:
        label = frappe.db.get_value("Bunch Tag", o.bunch_tag, "color_label")
        colours[label] = colours.get(label, 0) + int(o.qty)
    check("opening book in the sổ lô: Đỏ 113, Trắng 182, Tím 298", colours == {"Đỏ": 113, "Trắng": 182, "Tím": 298}, colours)
    check("opening lines are cắt bắp", {o.stage for o in opening} == {rules.CUT}, {o.stage for o in opening})

    # ---------------------------------------------------------------- old-ledger readers
    rows = lot_ledger.bunch_rows({"farm": FARM, "state": "Confirmed", "event_type": "Cut Bud"}, ["farm_block", "event_type", "event_date", "qty"])
    check("bunch_rows speaks the old shape", rows and {"farm_block", "event_type", "event_date", "qty"} <= set(rows[0]), rows[:1])
    check("bunch_rows sums the opening book", sum(r.qty for r in rows) >= 593, sum(r.qty for r in rows))

    # ---------------------------------------------------------------- works the ledger needs
    works = lot_ledger.works(FARM)
    by_stage = {w.stage: w for w in works.values() if w.stage}
    for stage in (rules.CUT, rules.HARVEST, rules.REJECT, rules.INJECT, rules.BAG):
        check(f"a việc exists for stage {stage}", stage in by_stage)
    disease = next((w for w in works.values() if w.records_disease), None)
    check("a việc records sâu bệnh", bool(disease))
    spray = next((w for w in works.values() if w.group == rules.PROTECTION and not w.records_disease), None)
    check("a spraying việc exists", bool(spray))

    # ---------------------------------------------------------------- quarantine
    block = frappe.get_all("Farm Block", filters={"farm": FARM, "farm_zone": "A", "active": 1}, pluck="name", limit=1)[0]
    item = frappe.get_all("Item", filters={"disabled": 0, "is_stock_item": 1}, pluck="name", limit=1)[0]
    today = getdate(nowdate())
    sprayed = line(block, spray, add_days(today, -40), qty=1)
    sprayed.append("materials", {"item_code": item, "qty": 2, "dose": "50 ml/bình", "phi_days": 14})
    store(sprayed)
    harvest = by_stage[rules.HARVEST]
    check("a draft spray holds nothing", lot_ledger.harvest_hold(block, add_days(today, -35)) is None)
    sprayed.state, sprayed.confirmed_by = rules.CONFIRMED, "Administrator"
    store(sprayed)
    check("a confirmed spray holds the lô from the spray day", lot_ledger.harvest_hold(block, add_days(today, -40)) is not None)
    check("…to the end of the interval", lot_ledger.harvest_hold(block, add_days(today, -26)) is not None)
    check("…and not the day after", lot_ledger.harvest_hold(block, add_days(today, -25)) is None)
    refused("harvest inside the interval is refused",
            lambda: store(line(block, harvest, add_days(today, -30), stage=rules.HARVEST, qty=5, weight_kg=95, bunch_tag=None)))
    check("a harvest entered late for a day before the spray is not held", lot_ledger.harvest_hold(block, add_days(today, -41)) is None)

    # ---------------------------------------------------------------- a confirmed line never changes
    cut = by_stage[rules.CUT]
    done = store(line(block, cut, add_days(today, -1), stage=rules.CUT, state=rules.CONFIRMED, confirmed_by="Administrator"))
    done.qty = 99
    refused("a confirmed line cannot be edited", lambda: store(done))
    done.reload()
    done.state = rules.VOIDED
    refused("voiding needs a reason", lambda: store(done))
    done.reload()
    done.state, done.void_reason = rules.VOIDED, "Nhập nhầm lô"
    store(done)
    check("voided with a reason", frappe.db.get_value(lot_ledger.ENTRY, done.name, "state") == rules.VOIDED)
    draft = store(line(block, cut, add_days(today, -1), stage=rules.CUT))
    refused("a sent line cannot be deleted", lambda: (frappe.db.set_value(lot_ledger.ENTRY, draft.name, "state", rules.SENT),
                                                      frappe.delete_doc(lot_ledger.ENTRY, draft.name, ignore_permissions=True)))

    # ---------------------------------------------------------------- one buổi shared by lines, once per line
    employee = frappe.get_all("Employee", filters={"status": "Active"}, pluck="name", limit=1)[0]
    a = store(line(block, cut, today, stage=rules.CUT))
    b = store(line(block, cut, today, stage=rules.CUT))

    def session(entry, weight):
        token = field._writing.set(True)
        try:
            return frappe.get_doc({"doctype": field.SESSION, "employee": employee, "posting_date": today, "session": "Morning",
                                   "entry": entry, "weight": weight, "farm": FARM, "farm_block": block}).insert(ignore_permissions=True)
        finally:
            field._writing.reset(token)
    session(a.name, 0.5)
    session(b.name, 0.5)
    check("one buổi split over two lines", frappe.db.count(field.SESSION, {"employee": employee, "posting_date": today}) == 2)
    refused("the same buổi twice on one line is refused", lambda: session(a.name, 0.5), frappe.UniqueValidationError)
    for doc in (a, b):
        frappe.db.delete(field.SESSION, {"entry": doc.name})
        frappe.delete_doc(lot_ledger.ENTRY, doc.name, ignore_permissions=True, force=True)

    # ---------------------------------------------------------------- the daily report: people, money, sâu bệnh
    from lotus_farm import lot_report as lr
    crew = frappe.get_all("Work Team", filters={"farm": FARM, "lotus_team_level": "Crew"}, pluck="name", order_by="creation asc")[0]
    leader = frappe.db.get_value("Work Team", crew, "lotus_leader")
    team = frappe.get_all("Work Team", filters={"lotus_parent_team": crew, "lotus_team_level": "Team"}, pluck="name", order_by="team_name asc")[0]
    company = frappe.db.get_value("Farm", FARM, "company")
    frappe.db.delete(lot_ledger.ENTRY, {"farm": FARM, "posting_date": today, "source_type": ["!=", rules.OPENING]})
    frappe.db.delete(lr.REPORT, {"farm": FARM, "report_date": today})
    workers = frappe.get_all("Employee", filters={"company": company, "status": "Active"}, pluck="name", limit=2)
    e1, e2 = workers
    for e in workers:
        frappe.db.set_value("Employee", e, "lotus_work_team", team)
        for hour in ("06:30:00", "17:30:00"):
            frappe.get_doc({"doctype": "Employee Checkin", "employee": e, "time": f"{today} {hour}", "log_type": "IN"}).insert(ignore_permissions=True)
    here = field.presence(company, today)
    check("the clock shows both workers present morning and afternoon", all(here.get(e, {}).get("morning") and here.get(e, {}).get("afternoon") for e in workers), here)
    t = lr.today(FARM, team, today)
    report = lr.open_report(FARM, team, today)["name"]
    check("today lists the tổ's present people first", [p["employee"] for p in t["present"] if p["own"]][:2] and all(p["own"] for p in t["present"][:2]))
    bag = by_stage[rules.BAG]
    field_work = next(w for w in works.values() if w.group == rules.FIELD_GROUP and w.pay_mode == "Lot" and not w.stage)
    cut_out = lr.save_lot(report, block, [{"work_type": cut.name, "qty": 60}])
    check("a cut for the colour of the day", not cut_out["errors"], cut_out)
    ribbon = field.ribbon(FARM, today).name
    out = lr.save_lot(report, block, [{"work_type": cut.name, "qty": 60},
                                      {"work_type": bag.name, "qty": 50, "bunch_tag": ribbon,
                                       "people": [{"employee": e1, "morning": 1}, {"employee": e2, "morning": 1, "afternoon": 1}]}])
    check("bao buồng with its people", out["saved"] == 2 and not out["errors"], out)
    other_block = frappe.get_all("Farm Block", filters={"farm": FARM, "farm_zone": "A", "active": 1, "name": ["!=", block]}, pluck="name", limit=1)[0]
    out = lr.save_lot(report, other_block, [{"work_type": field_work.name, "qty": 1.5, "people": [{"employee": e1, "morning": 1}]}])
    check("cắt lá on another lô, same morning", not out["errors"], out)
    sessions = {(s.entry, s.employee, s.session): s.weight for s in frappe.get_all(field.SESSION, filters={"posting_date": today, "employee": ["in", workers]},
                                                                                  fields=["entry", "employee", "session", "weight"])}
    e1_morning = sorted(w for (en, emp, se), w in sessions.items() if emp == e1 and se == "Morning")
    check("one morning split between two việc: 0,5 + 0,5", e1_morning == [0.5, 0.5], sessions)
    refused("a person the clock does not show is refused", lambda: (_ for _ in ()).throw(frappe.ValidationError) if
            lr.save_lot(report, other_block, [{"work_type": field_work.name, "qty": 1, "people": [{"employee": "NOT-A-PERSON", "morning": 1}]}])["errors"] else None)
    spray_out = lr.save_lot(report, other_block, [{"work_type": field_work.name, "qty": 1.5, "people": [{"employee": e1, "morning": 1}]},
                                                  {"work_type": spray.name, "qty": 2}])
    check("spraying without materials is refused", spray_out["saved"] == 0 and spray_out["errors"], spray_out)
    sick = lr.save_lot(report, other_block, [{"work_type": field_work.name, "qty": 1.5, "people": [{"employee": e1, "morning": 1}]},
                                             {"work_type": disease.name, "qty": 12}])
    check("sâu bệnh without a disease is refused", sick["saved"] == 0 and sick["errors"], sick)
    disease_name = frappe.get_all("Disease", filters={"active": 1}, pluck="name", limit=1)
    if disease_name:
        sick = lr.save_lot(report, other_block, [{"work_type": field_work.name, "qty": 1.5, "people": [{"employee": e1, "morning": 1}]},
                                                 {"work_type": disease.name, "qty": 12, "disease": disease_name[0], "severity": "Vừa"}])
        check("sâu bệnh with disease, trees and severity", not sick["errors"], sick)
    lr.send(report)
    frappe.set_user(leader)
    lr.confirm(report)
    frappe.set_user("Administrator")
    line = frappe.get_all(lot_ledger.ENTRY, filters={"daily_report": report, "stage": rules.BAG}, fields=["name", "rate", "amount"])[0]
    rate = field.rules.rate_for(field._rates(FARM), bag.name, today)
    check("the khoán price is taken at confirmation", rate and line.rate == rate.rate and line.amount == round(50 * rate.rate), (line, rate))
    piece = field.month_piece(company, frappe.utils.get_first_day(today), frappe.utils.get_last_day(today))
    share1, share2 = piece.get(e1, {}).get("piece", 0), piece.get(e2, {}).get("piece", 0)
    check("khoán money split by buổi weight (0,5 against 2)", round(share1) == round(line.amount * 0.5 / 2.5) and round(share1 + share2) == round(line.amount),
          (share1, share2, line.amount))
    check("khoán buổi counted once per buổi", abs(piece[e1]["khoan_sessions"] - 1.0) < 1e-6 and abs(piece[e2]["khoan_sessions"] - 2.0) < 1e-6, piece)
    rows = field.work_rows(company, today, today)
    check("workdays by lô from weights", abs(sum(r["workdays"] for r in rows if r["employee"] == e1) - 0.5) < 1e-6, rows)
    frappe.set_user(leader)
    mine = lr.my_pay(FARM, str(today)[:7])
    team_row = next(t for t in mine["teams"] if t["team"] == team)
    check("the tổ sees its khoán so far this month", team_row["total"] >= round(line.amount) - 1, team_row)
    frappe.set_user("Administrator")
finally:
    frappe.db.rollback()
    print("\n" + ("ALL OK" if not failures else f"{len(failures)} FAILED: " + "; ".join(failures)))
    frappe.destroy()
