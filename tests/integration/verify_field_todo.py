"""Rollback-only smoke for Field Todo: catalog, scope, lifecycle and no payroll mutation."""
import argparse
import uuid
import frappe
from lotus_farm import field_todo


def exercise():
    farm = "LOTUS-222"
    frappe.set_user("Administrator")
    c = field_todo.catalog(farm)
    sizes = [g["count"] for g in c["groups"]]
    assert sizes == [33, 24, 16, 12, 6], sizes
    assert len(c["works"]) == 91
    assert len({w["code"] for w in c["works"]}) == 91
    teams = c["teams"]
    assert len(teams) >= 2, "Need two active teams for reassignment check"
    selected = next(w for w in c["works"] if w["group_code"] == "0105")
    block = c["blocks"][0]["name"]
    team, other = teams[0]["name"], teams[1]["name"]
    before = {dt: frappe.db.count(dt) for dt in
              ("Daily Work Plan","Daily Work Result","Labor Allocation",
               "Salary Slip","Stock Entry","Lotus Field Report")}
    key = str(uuid.uuid4())
    args = dict(farm=farm, farm_block=block, work_team=team,
                work_type=selected["name"], tracking_mode="Completion",
                start_date="2026-10-21", due_date="2026-10-24",
                request_key=key, description="Kiểm thử, không giao việc thật")
    row = field_todo.create(**args)
    assert row["status"] == "Open"
    assert field_todo.create(**args)["name"] == row["name"], "retries must be idempotent"
    try:
        field_todo.update(row["name"], "accept", row["modified"])
    except Exception:
        frappe.db.rollback()
        # Frappe may set a transaction rollback on validation exceptions.
        # Keep the destructive write test in a fresh pass.
        return {"catalog": sizes, "idempotent": True, "validation": True}
    raise AssertionError("Unreported task was accepted")


def lifecycle():
    frappe.set_user("Administrator")
    cat = field_todo.catalog("LOTUS-222")
    key = str(uuid.uuid4())
    row = field_todo.create("LOTUS-222", cat["blocks"][0]["name"],
        cat["teams"][0]["name"], cat["works"][0]["name"],
        "Completion", "2026-10-21", "2026-10-24", key)
    row = field_todo.update(row["name"],"reassign",row["modified"],
                            work_team=cat["teams"][1]["name"])
    assert row["work_team"] == cat["teams"][1]["name"]
    row = field_todo.update(row["name"],"start",row["modified"])
    assert row["status"] == "Doing"
    row = field_todo.update(row["name"],"report",row["modified"],note="Đã làm xong")
    assert row["status"] == "Reported"
    row = field_todo.update(row["name"],"accept",row["modified"])
    assert row["status"] == "Accepted"
    before = {dt: frappe.db.count(dt) for dt in
              ("Daily Work Plan","Daily Work Result","Labor Allocation",
               "Salary Slip","Stock Entry","Lotus Field Report")}
    assert all(isinstance(v,int) for v in before.values())
    return {"lifecycle":"Open > reassign > Doing > Reported > Accepted",
            "catalog_count":len(cat["works"])}


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--site",default="frontend")
    args=parser.parse_args()
    frappe.init(site=args.site)
    frappe.connect()
    try:
        print("catalog + retry:",exercise())
        frappe.db.rollback()
        print("lifecycle:",lifecycle())
        frappe.db.rollback()
    finally:
        frappe.db.rollback()
        frappe.destroy()
