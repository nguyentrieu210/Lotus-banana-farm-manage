"""Integration check for công việc ngoài vườn (phiếu giao việc theo lô) on a disposable site (kho.test), after
field_report_seed ran. Copy into lotus_farm/ and run with bench --site kho.test execute <module>.run. Everything is
rolled back at the end."""
import json
import uuid

import frappe
from frappe.utils import add_days, flt, nowdate

FARM = "LOTUS-222"
SUPERVISOR = "haitrongvan1987@gmail.com"
LEADER = "fw.leader@example.com"
INSPECTOR = "fw.inspector@example.com"


def expect(error, fn, text=None):
    try:
        fn()
    except error as e:
        if text and text not in str(e):
            raise AssertionError(f"expected '{text}' in '{e}'")
        frappe.clear_messages()
        return
    raise AssertionError(f"expected {error.__name__}")


def user(email, role):
    if not frappe.db.exists("User", email):
        frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0,
                        "roles": [{"role": role}]}).insert(ignore_permissions=True)
    frappe.get_doc({"doctype": "User Permission", "user": email, "allow": "Farm", "for_value": FARM}).insert(ignore_permissions=True)


def run():
    from lotus_farm import field_report as fr, field_report_seed as seed, hr_period as hp, timekeeping as t
    frappe.set_user("Administrator")
    try:
        company = frappe.db.get_value("Farm", FARM, "company")
        tag = uuid.uuid4().hex[:6]
        for code, (group, pay, cap, material) in seed.MODES.items():
            name = frappe.db.get_value("Work Type", {"work_code": code})
            if name:
                frappe.db.set_value("Work Type", name, {"lotus_work_group": group, "lotus_pay_mode": pay, "lotus_cap_basis": cap,
                                                        "lotus_requires_material": material})
        works = {w.work_code: w.name for w in frappe.get_all("Work Type", filters={"lotus_farm": FARM}, fields=["name", "work_code"])}
        blocks = {b.block_code: b for b in frappe.get_all("Farm Block", filters={"farm": FARM}, fields=["name", "block_code", "area_ha", "lotus_tree_count"])}
        crew = frappe.db.get_value("Work Team", {"farm": FARM, "lotus_team_level": "Crew"})
        teams = frappe.get_all("Work Team", filters={"farm": FARM, "lotus_team_level": "Team"}, order_by="team_name", pluck="name")
        mine, other = teams[0], teams[1]
        user(LEADER, "Lotus Team Leader")
        user(INSPECTOR, "Lotus Field Inspector")
        frappe.db.set_value("Work Team", mine, {"lotus_parent_team": crew, "lotus_leader": LEADER})
        frappe.db.set_value("Work Team", other, {"lotus_parent_team": crew, "lotus_leader": None})
        d1, d2 = add_days(nowdate(), -2), add_days(nowdate(), -1)

        def employee(label, team, punches):
            name = t.create_employee(company, dict(employee_name="FW " + label + " " + tag, gender="Male", date_of_birth="1990-01-01",
                                                   date_of_joining=d1[:8] + "01"))["name"]
            frappe.db.set_value("Employee", name, dict(status="Active", lotus_onboarding_state="Ready", lotus_payment_basis="Daywork",
                                                       lotus_daily_rate=290000, lotus_work_team=team))
            for day in (d1, d2):
                for clock in punches:
                    frappe.get_doc(dict(doctype="Employee Checkin", employee=name, time=day + " " + clock, log_type="IN")).insert()
            return name

        e1 = employee("both", mine, ("06:30:00", "17:30:00"))
        e2 = employee("morning", mine, ("06:40:00",))
        e3 = employee("other", other, ("06:35:00", "17:20:00"))
        here = fr.presence(company, d1)
        assert here[e1]["morning"] and here[e1]["afternoon"] and here[e2]["morning"] and not here[e2]["afternoon"], here.get(e2)

        # Giao: cách trả, giá và trần đi theo việc, chụp lại trên phiếu.
        frappe.set_user(SUPERVISOR)
        bag = fr.assign(FARM, crew, works["F222-02"], mine, [blocks["A1"].name], assigned_on=d1)["created"][0]
        cut = fr.assign(FARM, crew, works["F222-06"], other, [blocks["A1"].name], assigned_on=d1)["created"][0]
        fert = fr.assign(FARM, crew, works["F222-12"], mine, [blocks["A2"].name], assigned_on=d1)["created"][0]
        leaf = fr.assign(FARM, crew, works["F222-07"], mine, [blocks["A5"].name], assigned_on=d1)["created"][0]
        doc = frappe.get_doc(fr.ASSIGNMENT, bag)
        assert (doc.pay_mode, doc.cap_basis, doc.work_group, doc.rate) == ("Count", "CutBud", "Bunch", 4000), doc.as_dict()
        expect(frappe.ValidationError, lambda: fr.assign(FARM, crew, works["F222-02"], other, [blocks["A1"].name]), "đang giao")

        # Cắt bắp (công nhật) gives the colour count; the clock decides who can be put on a buổi.
        frappe.set_user(SUPERVISOR)
        r = fr.save_entry(cut, d1, json.dumps([{"employee": e3, "morning": 1}]), qty=40)
        ribbon = r["entries"][0]["bunch_tag"]
        assert ribbon, r["entries"]
        frappe.set_user(LEADER)
        expect(frappe.ValidationError, lambda: fr.save_entry(bag, d1, json.dumps([{"employee": e2, "afternoon": 1}]), qty=5, bunch_tag=ribbon),
               "không có lượt buổi chiều")
        expect(frappe.ValidationError, lambda: fr.save_entry(bag, d1, json.dumps([{"employee": e1, "morning": 1}]), qty=5), "màu dây")
        expect(frappe.PermissionError, lambda: fr.save_entry(cut, d1, json.dumps([{"employee": e1, "morning": 1}]), qty=1))
        r = fr.save_entry(bag, d1, json.dumps([{"employee": e1, "morning": 1, "afternoon": 1}, {"employee": e2, "morning": 1}]),
                          qty=30, bunch_tag=ribbon)
        assert r["state"] == "Open" and r["progress"]["sessions"] == 3, r["progress"]
        # One buổi of one person belongs to one phiếu.
        expect(frappe.ValidationError, lambda: fr.save_entry(fert, d1, json.dumps([{"employee": e1, "morning": 1}]), qty=10,
                                                             materials=json.dumps([])), "đã ghi ở phiếu")
        # Over the cắt bắp count of that colour: flagged before 01/12/2026, refused from then on.
        r = fr.save_entry(bag, d1, json.dumps([{"employee": e1, "morning": 1, "afternoon": 1}, {"employee": e2, "morning": 1}]),
                          qty=45, bunch_tag=ribbon, expected_modified=r["entries"][0]["modified"])
        assert r["entries"][0]["over_cut"] == (0 if fr.rules.cap_blocks(d1) else 1), r["entries"][0]
        r = fr.save_entry(bag, d1, json.dumps([{"employee": e1, "morning": 1, "afternoon": 1}, {"employee": e2, "morning": 1}]),
                          qty=30, bunch_tag=ribbon, done=1, expected_modified=r["entries"][0]["modified"])
        assert r["state"] == "Reported", r["state"]

        # BVTV / phân bón: materials required, the lô's trees are the cap, a pre-harvest interval holds the lô.
        item = frappe.get_all("Item", filters={"is_stock_item": 1, "disabled": 0}, pluck="name", limit=1)[0]
        frappe.db.set_value("Item", item, "lotus_phi_days", 7)
        expect(frappe.ValidationError, lambda: fr.save_entry(fert, d2, json.dumps([{"employee": e2, "morning": 1}]), qty=10), "phải ghi vật tư")
        trees = int(blocks["A2"].lotus_tree_count or 0)
        expect(frappe.ValidationError, lambda: fr.save_entry(fert, d2, json.dumps([{"employee": e2, "morning": 1}]), qty=trees + 1,
                                                             materials=json.dumps([{"item_code": item, "qty": 5}])), "số cây của lô")
        fr.save_entry(fert, d2, json.dumps([{"employee": e2, "morning": 1}]), qty=500, materials=json.dumps([{"item_code": item, "qty": 5, "dose": "120 g/gốc"}]))
        until = frappe.db.get_value("Farm Block", blocks["A2"].name, "lotus_quarantine_until")
        assert str(until) == add_days(d2, 7), until
        expect(frappe.ValidationError, lambda: fr.harvest_guard(frappe._dict(farm_block=blocks["A2"].name, harvest_date=d2)), "cách ly")

        # Đội trưởng duyệt: counted work is locked and split by buổi.
        frappe.set_user(LEADER)
        expect(frappe.PermissionError, lambda: fr.approve(bag))
        frappe.set_user(SUPERVISOR)
        r = fr.approve(bag)
        assert r["state"] == "Locked" and r["amount"] == 120000, (r["state"], r["amount"])
        shares = {s["employee"]: s["amount"] for s in r["shares"]}
        assert shares == {e1: 80000, e2: 40000}, shares

        # Khoán lô: báo xong → duyệt → nghiệm thu by a Kỹ thuật vườn; fail sends it back, pass pays the whole lô.
        frappe.set_user(LEADER)
        r = fr.save_entry(leaf, d2, json.dumps([{"employee": e1, "morning": 1, "afternoon": 1}]), qty=1.0, done=1)
        frappe.set_user(SUPERVISOR)
        r = fr.approve(leaf)
        assert r["state"] == "Approved" and r["actions"]["inspect"] is False, "the đội trưởng does not inspect"
        expect(frappe.PermissionError, lambda: fr.inspect(leaf, 20, 19))
        frappe.set_user(INSPECTOR)
        r = fr.inspect(leaf, 20, 17)
        assert r["state"] == "Failed" and r["inspection_doc"]["result"] == "Fail", r["state"]
        frappe.set_user(LEADER)
        r = fr.report_done(leaf)
        frappe.set_user(SUPERVISOR)
        fr.approve(leaf)
        frappe.set_user(INSPECTOR)
        r = fr.inspect(leaf, 20, 19)
        expected = round(flt(blocks["A5"].area_ha) * 300000)
        assert r["state"] == "Locked" and r["amount"] == expected, (r["state"], r["amount"], expected)

        # Payroll: khoán buổi are not paid as công nhật; khoán shares are paid; finance places the buổi on lô.
        frappe.set_user("Administrator")
        month = d1[:7]
        begin, end = hp._month(month)
        pieces = fr.month_piece(company, begin, end)
        assert pieces[e1]["khoan_sessions"] == 4 and round(pieces[e1]["piece"]) == 80000 + expected, pieces[e1]
        assert pieces[e2]["khoan_sessions"] == 2, pieces[e2]  # bao buồng sáng d1 + bón phân sáng d2
        rows = fr.work_rows(company, begin, end)
        assert any(r["employee"] == e1 and r["lotus_farm_block"] == blocks["A5"].name and r["workdays"] == 1 for r in rows), rows
        print("OK công việc ngoài vườn:", "bao buồng", 120000, "cắt lá", expected, "buổi khoán E1", pieces[e1]["khoan_sessions"])
    finally:
        frappe.set_user("Administrator")
        frappe.db.rollback()
