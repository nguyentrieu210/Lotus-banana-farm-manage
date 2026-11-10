"""Ca đóng gói theo nguồn buồng end to end on a site that has Vườn 222 set up: a shift takes bunches harvested on two
lô, its cartons and finished goods are split by kg, it traces back to the harvest and the spraying, and the accountant
gets a draft finished-goods receipt valued from each lô's cost. Everything runs in one transaction and is rolled back.

docker exec -i lotus-vps-test-backend-1 bash -lc 'cd /home/frappe/frappe-bench/sites && ../env/bin/python -' < tests/integration/verify_packout_sources.py
"""
import json
import os

import frappe
from frappe.utils import add_days, flt, nowdate

SITE = os.environ.get("SITE", "frontend")
FARM = "LOTUS-222"
ENTRY, SHIFT = "Lotus Work Entry", "Packhouse Shift"

frappe.init(site=SITE)
frappe.connect()

from lotus_farm import field_report as field  # noqa: E402
from lotus_farm import lot_ledger  # noqa: E402
from lotus_farm import lot_ledger_rules as rules  # noqa: E402
from lotus_farm import shift as shift_api  # noqa: E402

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
    frappe.flags.lotus_ledger_migrating = True
    try:
        doc.save(ignore_permissions=True)
    finally:
        frappe.flags.lotus_ledger_migrating = False
        field._writing.reset(token)
    return doc


day = nowdate()
works = {w["stage"]: w for w in lot_ledger.works(FARM).values() if w["stage"]}
blocks = {b.block_code: b.name for b in frappe.get_all("Farm Block", filters={"farm": FARM, "farm_zone": "A", "active": 1}, fields=["name", "block_code"])}
A5, A6 = blocks["A5"], blocks["A6"]
tag = (field.ribbon(FARM, add_days(day, -70)) or frappe._dict(name=frappe.get_all("Bunch Tag", filters={"farm": FARM}, pluck="name", order_by="creation asc", limit=1)[0])).name


def line(block, stage, qty, on, work=None, materials=(), **values):
    work = work or works[stage]
    doc = frappe.new_doc(ENTRY)
    doc.update(dict({"farm": FARM, "company": frappe.db.get_value("Farm", FARM, "company"), "farm_block": block, "work_type": work["name"],
                     "stage": stage, "pay_mode": work["pay_mode"], "posting_date": on, "qty": qty, "bunch_tag": tag, "state": rules.CONFIRMED,
                     "source_type": rules.MANUAL, "source_key": "packout:" + frappe.generate_hash(length=12), "entered_by": "Administrator",
                     "confirmed_by": "Administrator", "confirmed_at": frappe.utils.now_datetime(), "cycle_no": 2}, **values))
    for m in materials:
        doc.append("materials", m)
    return store(doc)


try:
    frappe.set_user("Administrator")
    for block in (A5, A6):
        line(block, rules.CUT, 150, add_days(day, -70))
    h5 = line(A5, rules.HARVEST, 100, day, weight_kg=2000)
    h6 = line(A6, rules.HARVEST, 40, day, weight_kg=1000)
    spray = next(w for w in lot_ledger.works(FARM).values() if w["requires_material"] and not w["stage"])
    item = frappe.get_all("Item", filters={"lotus_phi_days": [">", 0]}, pluck="name", limit=1) or frappe.get_all("Item", filters={"is_stock_item": 1}, pluck="name", limit=1)
    sprayed = line(A5, None, 1, add_days(day, -10), work=spray, materials=[{"item_code": item[0], "qty": 2, "dose": "40 ml / bình"}], bunch_tag=None)

    # ------------------------------------------------------------ the harvest the xưởng can take
    left = {(r["farm_block"], r["harvest_entry"]): r for r in shift_api.harvest_sources(FARM, day)}
    check("today's harvest lines are offered to the xưởng", (A5, h5.name) in left and left[(A5, h5.name)]["left"] == 100 and left[(A6, h6.name)]["kg"] == 1000,
          list(left.values())[:3])

    # ------------------------------------------------------------ a shift takes bunches from two lô
    values = {"shift_code": "PKT-1", "posting_date": day, "started_at": f"{day} 07:00:00", "ended_at": f"{day} 16:00:00",
              "finished_kg": 2400, "secondary_kg": 300, "cartons": 181,
              "sources": [{"farm_block": A5, "bunch_tag": tag, "bunches": 100, "kg": 2000, "harvest_entry": h5.name},
                          {"farm_block": A6, "bunch_tag": tag, "bunches": 40, "kg": 1000, "harvest_entry": h6.name}]}
    refused("a shift cannot take more bunches than were harvested",
            lambda: shift_api.save_shift(FARM, json.dumps(dict(values, shift_code="PKT-X", sources=[dict(values["sources"][0], bunches=101)]))))
    refused("a shift cannot pack more than it took in", lambda: shift_api.save_shift(FARM, json.dumps(dict(values, shift_code="PKT-Y", finished_kg=2900))))
    saved = shift_api.save_shift(FARM, json.dumps(values))
    doc = saved["doc"]
    check("the kg taken in are the kg of the sources", flt(doc["input_kg"]) == 3000 and flt(doc["loss_kg"]) == 300 and flt(doc["packout_percent"]) == 80,
          (doc["input_kg"], doc["loss_kg"], doc["packout_percent"]))
    a5, a6 = sorted(saved["split"], key=lambda r: r["kg"], reverse=True)
    check("cartons and finished kg are split by kg", (a5["cartons"], a6["cartons"]) == (121, 60) and (a5["finished_kg"], a6["finished_kg"]) == (1600.0, 800.0),
          (a5, a6))
    check("kg and cartons per bunch per lô", (a5["kg_per_bunch"], a6["kg_per_bunch"]) == (20.0, 25.0) and a6["cartons_per_bunch"] == 1.5, (a5, a6))
    refused("the same bunches cannot go to a second shift", lambda: shift_api.save_shift(FARM, json.dumps(dict(values, shift_code="PKT-2"))))
    check("bunches in a shift are no longer offered", not [r for r in shift_api.harvest_sources(FARM, day) if r["harvest_entry"] in (h5.name, h6.name)])
    closed = shift_api.close_shift(doc["name"])
    check("the shift closes", closed["doc"]["docstatus"] == 1)

    # ------------------------------------------------------------ trace back to the field
    traced = {t["farm_block"]: t for t in shift_api.trace(doc["name"])["sources"]}
    check("a source traces to its harvest line", [h["name"] for h in traced[A5]["harvests"]] == [h5.name], traced[A5]["harvests"])
    check("and to the spraying on that lô before the harvest", any(s["name"] == sprayed.name and s["dose"] == "40 ml / bình" for s in traced[A5]["sprays"]),
          traced[A5]["sprays"][:2])

    # ------------------------------------------------------------ the finished-goods receipt
    from lotus_farm.finance import costing, setup
    from lotus_farm import lot_report

    def lr_amend(entry):
        if not frappe.db.get_value("Lotus Work Entry", entry, "daily_report"):
            raise frappe.ValidationError("line outside a daily report: amend does not apply")
        return lot_report.amend(entry, {"qty": 1}, "kiểm lại")
    cfg = setup.settings()
    can_receive = cfg.finance_enabled and not setup.mapping_errors(cfg)
    if not can_receive:
        print("skip receipt checks: finance posting is off on this site")
    else:
        old = {k: cfg.get(k) for k in ("packed_item", "secondary_item", "packed_warehouse", "harvest_standard_cost")}
        stock_items = frappe.get_all("Item", filters={"is_stock_item": 1, "disabled": 0, "has_batch_no": 0, "has_serial_no": 0, "stock_uom": ["in", ["Kg", "kg"]]},
                                     pluck="name", limit=2)
        other_unit = frappe.get_all("Item", filters={"is_stock_item": 1, "disabled": 0, "stock_uom": ["not in", ["Kg", "kg"]]}, pluck="name", limit=1)
        warehouse = frappe.get_doc({"doctype": "Warehouse", "warehouse_name": "Thành phẩm thử " + frappe.generate_hash(length=5), "company": doc["company"]}).insert(ignore_permissions=True).name
        frappe.db.set_single_value("Lotus Finance Settings", {"packed_item": stock_items[0], "secondary_item": stock_items[-1], "packed_warehouse": warehouse,
                                                               "harvest_standard_cost": 5000})
        if other_unit:
            frappe.db.set_single_value("Lotus Finance Settings", "packed_item", other_unit[0])
            refused("a finished item not stocked in kg is refused", lambda: costing.receive_shift(doc["name"]))
            frappe.db.set_single_value("Lotus Finance Settings", "packed_item", stock_items[0])
        receipt = costing.receive_shift(doc["name"])
        se = frappe.get_doc("Stock Entry", receipt["stock_entry"])
        check("a draft Material Receipt for the accountant", se.docstatus == 0 and se.purpose == "Material Receipt" and se.lotus_packhouse_shift == doc["name"],
              (se.docstatus, se.purpose))
        by_lot = {}
        for row in se.items:
            by_lot[row.lotus_farm_block] = by_lot.get(row.lotus_farm_block, 0) + flt(row.qty) * flt(row.basic_rate)
        check("each lô hands over kg brought in × its cost per kg", abs(by_lot.get(A5, 0) - 2000 * 5000) < 1 and abs(by_lot.get(A6, 0) - 1000 * 5000) < 1, by_lot)
        check("finished and secondary kg go in", abs(sum(flt(r.qty) for r in se.items) - 2700) < 0.01)
        refused("one receipt per shift", lambda: costing.receive_shift(doc["name"]))
        frappe.delete_doc("Stock Entry", receipt["stock_entry"], ignore_permissions=True)
        check("deleting a wrong draft receipt frees the shift", not frappe.db.get_value("Packhouse Shift", doc["name"], "stock_entry"))
        again = costing.receive_shift(doc["name"])
        check("…and the shift can be received again", frappe.db.get_value("Stock Entry", again["stock_entry"], "docstatus") == 0 and
              frappe.db.get_value("Packhouse Shift", doc["name"], "stock_entry") == again["stock_entry"], again)
        refused("a harvest line cannot drop below the buồng its shift took",
                lambda: lr_amend(h5.name))
        frappe.set_user(frappe.get_all("Has Role", filters={"role": "Lotus Packing Supervisor", "parenttype": "User"}, pluck="parent", limit=1)[0]
                        if frappe.get_all("Has Role", filters={"role": "Lotus Packing Supervisor", "parenttype": "User"}, limit=1) else "Guest")
        refused("only the accountant makes the receipt", lambda: costing.receive_shift(doc["name"]), (frappe.PermissionError, frappe.ValidationError))
        frappe.set_user("Administrator")
finally:
    frappe.set_user("Administrator")
    frappe.db.rollback()

print("\nALL PASSED" if not failures else f"\n{len(failures)} FAILED: " + "; ".join(failures))
