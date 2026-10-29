"""Integration check for giao việc theo lô and the đội daily report on a disposable site (kho.test), after
field_report_seed ran.
bench --site kho.test execute tests.integration.verify_field_report.run   (copy to apps/lotus_farm/... first)
Everything is rolled back at the end."""
import json

import frappe
from frappe.utils import add_days, nowdate

FARM = "LOTUS-222"
LEADER = "fr.leader@example.com"
SUPERVISOR = "haitrongvan1987@gmail.com"
TASK = "Lotus Work Assignment"


def expect(error, fn, text=None):
    try:
        fn()
    except error as e:
        if text and text not in str(e):
            raise AssertionError(f"expected '{text}' in '{e}'")
        frappe.clear_messages()
        return
    raise AssertionError(f"expected {error.__name__}")


def keep(report, **changes):
    """The saved lines of a report as the editor sends them back, with optional changes per line_id."""
    from lotus_farm.field_report import LINE_KEYS
    rows = [{k: v for k, v in l.items() if k in LINE_KEYS} for l in report["lines"] if l["editable"]]
    for row in rows:
        row.update(changes.get(row["line_id"], {}))
    return rows


def run():
    from lotus_farm import field_report as fr
    from lotus_farm.hr_period import payroll_sheet
    frappe.set_user("Administrator")
    try:
        crew = frappe.db.get_value("Work Team", {"farm": FARM, "lotus_team_level": "Crew"})
        teams = frappe.get_all("Work Team", filters={"farm": FARM, "lotus_team_level": "Team"}, order_by="team_name", pluck="name")
        mine, other = teams[0], teams[1]
        if not frappe.db.exists("User", LEADER):
            frappe.get_doc({"doctype": "User", "email": LEADER, "first_name": "Tổ trưởng thử", "send_welcome_email": 0,
                            "roles": [{"role": "Lotus Team Leader"}]}).insert(ignore_permissions=True)
        frappe.get_doc({"doctype": "User Permission", "user": LEADER, "allow": "Farm", "for_value": FARM}).insert(ignore_permissions=True)
        frappe.set_user(SUPERVISOR)
        fr.save_team(FARM, mine, crew, LEADER)
        fr.save_team(FARM, other, crew, None)
        works = {w.work_code: w.name for w in frappe.get_all("Work Type", filters={"lotus_farm": FARM}, fields=["name", "work_code"])}
        blocks = {b.block_code: b for b in frappe.get_all("Farm Block", filters={"farm": FARM}, fields=["name", "block_code", "area_ha", "lotus_tree_count"])}
        leaf = works["F222-07"]
        d1, d2 = add_days(nowdate(), -2), add_days(nowdate(), -1)

        # 1. Đội trưởng giao Cắt lá on A5–A8 to the tổ: one phiếu per lô; a second phiếu on an open lô is refused.
        frappe.set_user(LEADER)
        expect(frappe.PermissionError, lambda: fr.assign(FARM, crew, leaf, mine, [blocks["A5"].name]))
        frappe.set_user(SUPERVISOR)
        lots = [blocks[c].name for c in ("A5", "A6", "A7", "A8")]
        made = fr.assign(FARM, crew, leaf, mine, json.dumps(lots), due_date=nowdate(), assigned_on=d1)["created"]
        assert len(made) == 4, made
        expect(frappe.ValidationError, lambda: fr.assign(FARM, crew, leaf, other, [lots[0]]), "đang giao")
        expect(frappe.ValidationError, lambda: fr.assign(FARM, crew, works["F222-02"], mine, [lots[0]]), "Chăm sóc buồng")
        expect(frappe.ValidationError, lambda: fr.assign(FARM, crew, leaf, mine, [blocks["C1"].name]), "khu")
        task = {frappe.db.get_value(TASK, n, "farm_block"): n for n in made}
        a8, a5, a6 = task[blocks["A8"].name], task[blocks["A5"].name], task[blocks["A6"].name]

        # 2. Tổ trưởng reports progress on A8: việc, lô and tổ come from the phiếu, nothing is paid before Xong.
        frappe.set_user(LEADER)
        got = fr.get(FARM, crew, d1)
        assert set(made) <= {a["name"] for a in got["assignments"]}, got["assignments"]
        before = add_days(d1, -1)
        assert a8 not in {a["name"] for a in fr.get(FARM, crew, before)["assignments"]}, "a phiếu shows from its day on"
        expect(frappe.ValidationError, lambda: fr.save(FARM, crew, before, [{"line_id": "fa000000000009", "assignment": a8,
                                                                           "pay_kind": "Piece", "workdays_am": 1}]), "phiếu giao từ ngày")
        line = {"line_id": "fa000000000001", "assignment": a8, "pay_kind": "Piece", "workdays_am": 1, "qty": 1.2,
                "work_type": works["F222-05"], "farm_block": blocks["C1"].name}
        r = fr.save(FARM, crew, d1, [line])
        saved = r["lines"][0]
        assert saved["work_type"] == leaf and saved["farm_block"] == blocks["A8"].name and saved["work_team"] == mine, saved
        assert saved["amount"] == 0 and saved["paid_qty"] == 0, saved
        assert {x["name"]: x for x in fr.assignments(FARM, crew)}[a8]["display"] == "Working"
        stray = {"line_id": "fa000000000002", "work_type": leaf, "pay_kind": "Piece", "farm_block": blocks["A9"].name, "workdays_am": 1}
        expect(frappe.ValidationError, lambda: fr.save(FARM, crew, d1, keep(r) + [stray], expected_modified=r["modified"]), "phiếu giao")
        free = {"line_id": "fa000000000003", "work_type": leaf, "pay_kind": "Daywork", "location": "Zone", "zone": "A", "workdays_am": 2}
        r = fr.save(FARM, crew, d1, keep(r) + [free], expected_modified=r["modified"])
        assert len(r["lines"]) == 2
        expect(frappe.PermissionError, lambda: fr.confirm(r["name"], r["modified"]))

        # 3. Next day the tổ ticks Xong: the whole lot is paid, the phiếu waits for the đội trưởng.
        r2 = fr.save(FARM, crew, d2, [{"line_id": "fa000000000004", "assignment": a8, "pay_kind": "Piece", "workdays_am": 3,
                                       "qty": 3.28, "done": 1}])
        expected = round(blocks["A8"].area_ha * 300000)
        assert r2["lines"][0]["amount"] == expected and abs(r2["lines"][0]["paid_qty"] - blocks["A8"].area_ha) < 1e-6, r2["lines"][0]
        assert {x["name"]: x for x in fr.assignments(FARM, crew)}[a8]["display"] == "Reported"
        frappe.set_user(SUPERVISOR)
        r = fr.get(FARM, crew, d1)
        expect(frappe.ValidationError, lambda: fr.save(FARM, crew, d1, keep(r, fa000000000001={"done": 1}), expected_modified=r["modified"]), "đã báo Xong")
        expect(frappe.ValidationError, lambda: fr.reassign(a8, other, "đổi"), "báo Xong")
        c = fr.confirm(r2["name"], r2["modified"])
        assert frappe.db.get_value(TASK, a8, ["state", "done_report"]) == ("Done", c["name"])
        pay = fr.payable(FARM, d2[:7])
        assert any(p["work_team"] == mine and p["amount"] == expected and abs(p["qty"] - blocks["A8"].area_ha) < 1e-6 for p in pay), pay
        made2 = fr.assign(FARM, crew, leaf, mine, [blocks["A8"].name])["created"]
        assert len(made2) == 1, "a done lô can be given the next round"
        c = fr.reopen(c["name"], "Sửa số công", c["modified"])
        assert frappe.db.get_value(TASK, a8, "state") == "Open"
        c = fr.confirm(c["name"], c["modified"])
        assert frappe.db.get_value(TASK, a8, "state") == "Done"

        # 4. Đổi tổ and huỷ need a reason; the board shows every phiếu of the month.
        expect(frappe.ValidationError, lambda: fr.reassign(a5, other, ""), "lý do")
        fr.reassign(a5, other, "Tổ 1 làm lô khác")
        assert frappe.db.get_value(TASK, a5, "work_team") == other
        fr.cancel_assignment(a6, "Lô ngập nước")
        assert frappe.db.get_value(TASK, a6, "state") == "Cancelled"
        board = fr.board(FARM, crew, d2[:7])
        cells = {(x["farm_block"], x["display"]) for x in board["cells"]}
        assert (blocks["A8"].name, "Done") in cells and not any(b == blocks["A6"].name for b, _ in cells), cells

        # 5. Chăm buồng: lots held by the tổ; bao buồng carries a colour and is flagged over the cắt bắp count.
        fr.bunch_assign(FARM, crew, json.dumps([blocks[c].name for c in ("A1", "A2", "A3")]), team=mine, from_date=d1)
        expect(frappe.ValidationError, lambda: fr.bunch_assign(FARM, crew, [blocks["A1"].name], team=other, from_date=d2), "lý do")
        tag = fr.ribbon(FARM, d1).name
        frappe.set_user(LEADER)
        r = fr.get(FARM, crew, d1)
        assert r["bunch_lots"].get(blocks["A1"].name) == mine, r["bunch_lots"]
        cut = {"line_id": "fb000000000001", "work_type": works["F222-06"], "pay_kind": "Daywork", "farm_block": blocks["A1"].name,
               "workdays_am": 2, "qty": 40}
        bag = {"line_id": "fb000000000002", "work_type": works["F222-02"], "pay_kind": "Piece", "farm_block": blocks["A1"].name,
               "workdays_am": 0.25, "qty": 30, "bunch_tag": tag}
        expect(frappe.ValidationError, lambda: fr.save(FARM, crew, d1, keep(r) + [cut, dict(bag, bunch_tag=None)], expected_modified=r["modified"]), "màu dây")
        r = fr.save(FARM, crew, d1, keep(r) + [cut, bag], expected_modified=r["modified"])
        lines = {l["line_id"]: l for l in r["lines"]}
        assert lines["fb000000000001"]["bunch_tag"] == tag and lines["fb000000000002"]["amount"] == 120000, lines
        assert not lines["fb000000000002"]["over_cut"]
        r = fr.save(FARM, crew, d1, keep(r, fb000000000002={"qty": 45}), expected_modified=r["modified"])
        assert {l["line_id"]: l for l in r["lines"]}["fb000000000002"]["over_cut"] == 1, "45 bao > 40 cắt bắp: flagged before 01/12"
        frappe.set_user(SUPERVISOR)
        r = fr.get(FARM, crew, d1)
        expect(frappe.ValidationError, lambda: fr.save(FARM, crew, d1, keep(r) + [dict(bag, line_id="fb000000000003", work_team=other, qty=1)],
                                                     expected_modified=r["modified"]), "chăm buồng")
        fr.bunch_assign(FARM, crew, [blocks["A1"].name], team=other, from_date=d2, reason="Tổ 1 thiếu người")
        assert fr._bunch_lots(FARM, d1)[blocks["A1"].name].work_team == mine
        assert fr._bunch_lots(FARM, d2)[blocks["A1"].name].work_team == other
        r = fr.confirm(r["name"], r["modified"])
        assert r["state"] == "Confirmed"

        frappe.set_user("Administrator")
        company = frappe.db.get_value("Farm", FARM, "company")
        crews = payroll_sheet(company, d2[:7]).get("crews") or []
        assert any(x.get("work_team") == mine and round(x.get("amount")) >= expected for x in crews), crews
        print("OK giao việc theo lô:", len(made), "phiếu, Xong", expected, "đ, ribbon", tag)
    finally:
        frappe.set_user("Administrator")
        frappe.db.rollback()
