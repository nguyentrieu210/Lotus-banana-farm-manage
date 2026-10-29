"""Integration check for the đội daily report on a disposable site (kho.test), after field_report_seed ran.
bench --site kho.test execute tests.integration.verify_field_report.run   (copy to apps/lotus_farm/... first)
Everything is rolled back at the end."""
import frappe
from frappe.utils import add_days, nowdate

FARM = "LOTUS-222"
LEADER = "fr.leader@example.com"
SUPERVISOR = "haitrongvan1987@gmail.com"


def expect(error, fn, text=None):
    try:
        fn()
    except error as e:
        if text and text not in str(e):
            raise AssertionError(f"expected '{text}' in '{e}'")
        frappe.clear_messages()
        return
    raise AssertionError(f"expected {error.__name__}")


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
        day = add_days(nowdate(), -1)

        frappe.set_user(LEADER)
        setup = fr.setup(FARM)
        assert crew in setup["my_crews"] and mine in setup["my_teams"], setup["my_teams"]
        cut_leaf = {"line_id": "lineleader0001", "work_type": works["F222-07"], "pay_kind": "Piece", "farm_block": blocks["A8"].name,
                    "workdays_am": 2, "workdays_pm": 2, "materials": [], "work_team": mine}
        bunch = {"line_id": "lineleader0002", "work_type": works["F222-06"], "pay_kind": "Daywork", "farm_block": blocks["A1"].name,
                 "workdays_am": 2, "qty": 40, "work_team": mine}
        expect(frappe.ValidationError, lambda: fr.save(FARM, crew, day, [dict(cut_leaf, workdays_am=6)]), "chưa đạt")
        expect(frappe.ValidationError, lambda: fr.save(FARM, crew, day, [cut_leaf, dict(cut_leaf, line_id="lineleader0009")]), "vượt cả lô")
        r = fr.save(FARM, crew, day, [cut_leaf, bunch])
        line = r["lines"][0]
        assert abs(line["qty"] - blocks["A8"].area_ha) < 1e-6 and line["whole_lot"] == 1, line
        assert line["amount"] == round(blocks["A8"].area_ha * 300000), line["amount"]
        assert r["lines"][1]["section"] == "Bunch" and r["lines"][1]["ribbon"], r["lines"][1]
        expect(frappe.PermissionError, lambda: fr.save(FARM, crew, day, [dict(cut_leaf, line_id="lineleader0003", work_team=other)], expected_modified=r["modified"]))
        expect(frappe.ValidationError, lambda: fr.save(FARM, crew, day, [dict(cut_leaf, farm_block=blocks["C1"].name)], expected_modified=r["modified"]), "khu")
        expect(frappe.PermissionError, lambda: fr.confirm(r["name"], r["modified"]))

        frappe.set_user(SUPERVISOR)
        got = fr.get(FARM, crew, day)
        zone_line = {"line_id": "linesuper00001", "work_type": works["F222-05"], "pay_kind": "Daywork", "location": "Zone", "zone": "A",
                     "workdays_am": 3.5, "qty": 32, "materials": [{"item_code": frappe.get_all("Item", filters={"is_stock_item": 1, "disabled": 0}, pluck="name", limit=1)[0], "qty": 1}]}
        keep = [{k: v for k, v in l.items() if k in fr.LINE_KEYS} for l in got["lines"]]
        r = fr.save(FARM, crew, day, keep + [zone_line], weather="Sáng nắng, chiều mưa", expected_modified=got["modified"])
        assert len(r["lines"]) == 3 and r["weather"] == "Sáng nắng, chiều mưa"
        expect(frappe.TimestampMismatchError, lambda: fr.save(FARM, crew, day, keep, expected_modified="2000-01-01"))
        r = fr.confirm(r["name"], r["modified"])
        assert r["state"] == "Confirmed"
        expect(frappe.ValidationError, lambda: fr.save(FARM, crew, day, keep, expected_modified=r["modified"]), "đã xác nhận")
        month = day[:7]
        pay = fr.payable(FARM, month)
        assert any(p["work_team"] == mine and p["amount"] == line["amount"] for p in pay), pay
        expect(frappe.ValidationError, lambda: fr.reopen(r["name"], "", r["modified"]), "lý do")
        r = fr.reopen(r["name"], "Sửa số công", r["modified"])
        assert r["state"] == "Draft"
        r = fr.confirm(r["name"], r["modified"])

        frappe.set_user("Administrator")
        company = frappe.db.get_value("Farm", FARM, "company")
        sheet = payroll_sheet(company, month)
        crews = sheet.get("crews") or []
        assert any(c.get("work_team") == mine and round(c.get("amount")) == line["amount"] for c in crews), crews
        print("OK field report:", r["name"], "lines", len(r["lines"]), "piece", line["amount"], "ribbon", r["lines"][1]["ribbon"])
    finally:
        frappe.set_user("Administrator")
        frappe.db.rollback()
