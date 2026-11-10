"""Move the bunch ledger of spec 001 into the sổ lô, and close the demo records of the old phiếu flow.

- Confirmed Lotus Bunch Event lines (the 593-bunch opening book and anything confirmed since) become confirmed sổ lô
  lines with the same source key, so running this again writes nothing twice.
- Draft and voided bunch lines are demo data and are not moved.
- Old Lotus Work Entry rows (phiếu reports of the demo, no source key) are voided with reason "Bản thử trước sổ lô",
  open Round phiếu are cancelled with the same reason. Standing bunch-care assignments stay.

Run: bench --site <site> execute lotus_farm.lot_ledger_migrate.preview
     bench --site <site> execute lotus_farm.lot_ledger_migrate.commit
"""
import frappe
from frappe.utils import cint, now_datetime

from lotus_farm import field_report as field
from lotus_farm import lot_ledger
from lotus_farm import lot_ledger_rules as rules

EVENT = "Lotus Bunch Event"
DEMO_REASON = "Bản thử trước sổ lô"
SOURCE = {"Opening Import": rules.OPENING, "Manual": rules.DAILY, "Work Entry": rules.DAILY}


def _events():
    if not frappe.db.table_exists(EVENT):
        return []
    return frappe.get_all(EVENT, fields=["name", "farm", "farm_block", "work_team", "cycle_no", "event_type", "event_date", "qty", "area_ha",
                                         "bunch_tag", "reject_stage", "reason", "weight_kg", "source_type", "source_name", "source_key",
                                         "state", "entered_by", "confirmed_by", "confirmed_at", "notes"],
                          order_by="event_date asc, creation asc", limit_page_length=0)


def _plan():
    events = _events()
    existing = set(frappe.get_all(lot_ledger.ENTRY, filters={"source_key": ["in", [e.source_key for e in events] or [""]]}, pluck="source_key"))
    works = {}
    create, errors = [], []
    for e in events:
        if e.state != rules.CONFIRMED or e.source_key in existing:
            continue
        if e.farm not in works:
            works[e.farm] = {w.stage: w for w in lot_ledger.works(e.farm).values() if w.stage}
        work = works[e.farm].get(e.event_type)
        if not work:
            errors.append(f"Vườn {e.farm} chưa có việc cho công đoạn {e.event_type}: chạy field_report_seed.apply_ledger_works trước.")
            continue
        create.append((e, work))
    old_entries = frappe.get_all(lot_ledger.ENTRY, filters={"source_key": ["is", "not set"]}, pluck="name")
    rounds = frappe.get_all(field.ASSIGNMENT, filters={"kind": field.rules.ROUND, "state": ["in", list(field.OPEN_STATES)]}, pluck="name")
    colours = {}
    for e, _ in create:
        if e.source_type == "Opening Import":
            label = frappe.db.get_value("Bunch Tag", e.bunch_tag, "color_label") or e.bunch_tag
            colours[label] = colours.get(label, 0) + cint(e.qty)
    return dict(events=events, existing=existing, create=create, errors=sorted(set(errors)), old_entries=old_entries, rounds=rounds,
                colours=colours)


def _summary(plan):
    events = plan["events"]
    return {"bunch_lines": len(events),
            "confirmed": sum(1 for e in events if e.state == rules.CONFIRMED),
            "already_moved": sum(1 for e in events if e.state == rules.CONFIRMED and e.source_key in plan["existing"]),
            "to_move": len(plan["create"]),
            "opening_bunches_by_colour": plan["colours"],
            "drafts_not_moved": sum(1 for e in events if e.state == rules.DRAFT),
            "voided_not_moved": sum(1 for e in events if e.state == rules.VOIDED),
            "old_entries_to_void": len(plan["old_entries"]),
            "rounds_to_cancel": len(plan["rounds"]),
            "errors": plan["errors"]}


def preview():
    frappe.only_for("System Manager")
    summary = _summary(_plan())
    print(frappe.as_json(summary, indent=1))
    return summary


def _crew(team):
    return frappe.db.get_value("Work Team", team, "lotus_parent_team") if team else None


def commit():
    frappe.only_for("System Manager")
    plan = _plan()
    summary = _summary(plan)
    if plan["errors"]:
        print(frappe.as_json(summary, indent=1))
        frappe.throw("Còn lỗi, chưa chuyển: " + "; ".join(plan["errors"]))
    companies = {}
    token = field._writing.set(True)
    frappe.flags.lotus_ledger_migrating = True
    try:
        for e, work in plan["create"]:
            company = companies.setdefault(e.farm, frappe.db.get_value("Farm", e.farm, "company"))
            doc = frappe.new_doc(lot_ledger.ENTRY)
            doc.update({"farm": e.farm, "company": company, "crew": _crew(e.work_team), "work_team": e.work_team, "farm_block": e.farm_block,
                        "work_type": work.name, "stage": e.event_type, "pay_mode": work.pay_mode, "cycle_no": e.cycle_no,
                        "posting_date": e.event_date, "qty": e.qty, "uom": work.uom, "area_ha": e.area_ha, "bunch_tag": e.bunch_tag,
                        "reject_stage": e.reject_stage, "reason": e.reason, "weight_kg": e.weight_kg, "state": rules.CONFIRMED,
                        "source_type": SOURCE.get(e.source_type, rules.DAILY), "source_name": e.source_name or e.name,
                        "source_key": e.source_key, "entered_by": e.entered_by, "confirmed_by": e.confirmed_by,
                        "confirmed_at": e.confirmed_at, "notes": e.notes})
            doc.insert(ignore_permissions=True)
        now = now_datetime()
        for name in plan["old_entries"]:
            frappe.db.set_value(lot_ledger.ENTRY, name, {"state": rules.VOIDED, "void_reason": DEMO_REASON, "voided_at": now,
                                                         "source_type": rules.MANUAL, "source_key": "legacy:" + name},
                                update_modified=False)
        for name in plan["rounds"]:
            frappe.db.set_value(field.ASSIGNMENT, name, {"state": field.rules.CANCELLED, "cancel_reason": DEMO_REASON}, update_modified=False)
    finally:
        frappe.flags.lotus_ledger_migrating = False
        field._writing.reset(token)
    blocks = {e.farm_block for e, _ in plan["create"]}
    for block in blocks:
        lot_ledger.refresh_quarantine(block)
    frappe.db.commit()
    print(frappe.as_json(summary, indent=1))
    return summary
