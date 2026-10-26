"""Explicit DEMO seed for a disposable Lotus ERPNext site only.

Never run automatically on migration/install or production.
Usage: bench --site lotus.test execute lotus_farm.mobile_demo_seed.seed
Requires allow_tests enabled; no real Lotus records or prices are inferred.
"""
import frappe
from frappe.utils import add_days, nowdate


FARM_CODE = "LOTUS-DEMO-222"
TEAM_NAMES = ["Tổ bao buồng 01", "Tổ chăm sóc 02", "Tổ trồng 03", "Tổ tổng hợp 04"]
# Demo productivity is illustrative and MUST be replaced with Lotus-approved norms.
WORKS = [
    ("BAG", "Bao buồng", "Bunch", 100, "Chăm sóc buồng"),
    ("PROP", "Chống buồng", "Tree", 80, "Chăm sóc buồng"),
    ("BUD", "Cắt bắp", "Bunch", 90, "Chăm sóc buồng"),
    ("LEAF", "Cắt lá", "Ha", 0.5, "Chăm sóc cây"),
    ("SICK", "Cắt lá bệnh", "Ha", 0.3, "Chăm sóc cây"),
    ("WEED", "Phát cỏ", "Ha", 0.8, "Chăm sóc cây"),
    ("REPLANT", "Trồng dặm", "Tree", 65, "Trồng và chăm sóc"),
    ("FERT", "Bón phân", "Tree", 120, "Trồng và chăm sóc"),
]


def seed(company=None):
    if not frappe.conf.get("allow_tests"):
        frappe.throw("Dữ liệu mẫu chỉ chạy trên site cho phép kiểm thử (allow_tests); không chạy trên hệ thống thật.")
    if frappe.session.user != "Administrator":
        frappe.throw("Chạy dữ liệu mẫu bằng tài khoản Administrator.")
    if frappe.db.exists("Farm", FARM_CODE):
        return dict(farm=FARM_CODE, already_seeded=True,
                    note="Demo farm already exists. No existing data was changed.")

    companies = frappe.get_all("Company", pluck="name", limit_page_length=1000)
    if company:
        if company not in companies:
            frappe.throw("Chọn một công ty có sẵn hợp lệ trên site THỬ này.")
    elif len(companies) == 1:
        company = companies[0]
    else:
        frappe.throw("Chỉ rõ company=... cho một công ty thử có sẵn (không tìm thấy hoặc có nhiều công ty).")

    for unit in ("Bunch", "Tree", "Ha"):
        if not frappe.db.exists("UOM", unit):
            frappe.get_doc(dict(doctype="UOM", uom_name=unit)).insert()

    variety = frappe.db.get_value("Banana Variety", {"variety_code": "LOTUS-DEMO"}) or frappe.get_doc(dict(
        doctype="Banana Variety", variety_code="LOTUS-DEMO",
        variety_name="Chuối Cavendish (dữ liệu mẫu)")).insert().name

    farm = frappe.get_doc(dict(doctype="Farm", company=company, farm_code=FARM_CODE,
        farm_name="Lotus 222 ha — DỮ LIỆU MẪU", area_ha=222, active=1,
        notes="TEST ONLY / KHÔNG DÙNG ĐỂ BÁO CÁO HAY THANH TOÁN")).insert()

    def farm_doc(doctype, **values):
        values["farm"] = farm.name
        if frappe.get_meta(doctype).has_field("company"):
            values["company"] = company
        return frappe.get_doc(dict(doctype=doctype, **values))

    blocks, plots, cycles = {}, {}, {}
    for code, area in (("A01", 80), ("A02", 72), ("A03", 70)):
        b = farm_doc("Farm Block", block_code=code,
            block_name="Lô "+code+" (mẫu)", area_ha=area, variety=variety, active=1).insert()
        blocks[code] = b.name
        for index in range(1, 5):
            pcode = f"{code}-{index:02d}"
            p = farm_doc("Farm Plot",
                farm_block=b.name, plot_code=pcode, plot_name="Thửa "+pcode,
                area_ha=area / 4, active=1).insert()
            plots[pcode] = p.name
            c = farm_doc("Crop Cycle",
                farm_block=b.name, farm_plot=p.name, cycle_no=1,
                planting_date=add_days(nowdate(), -240), variety=variety,
                status="Active").insert()
            cycles[pcode] = c.name

    teams = {}
    for idx, name in enumerate(TEAM_NAMES, 1):
        values = dict(team_code=f"DEMO-T{idx:02d}", team_name=name, active=1)
        if frappe.get_meta("Work Team").has_field("foreman_name"):
            values["foreman_name"] = f"Tổ trưởng mẫu {idx:02d}"
        teams[idx] = farm_doc("Work Team", **values).insert().name

    categories = {}
    for c in ("Chăm sóc buồng", "Chăm sóc cây", "Trồng và chăm sóc"):
        categories[c] = frappe.get_doc(dict(doctype="Work Category",
            category_code="DEMO-"+str(len(categories)+1),
            category_name=c, active=1)).insert().name

    work_ids = {}
    for code, name, uom, norm, group in WORKS:
        values = dict(doctype="Work Type", work_code="DEMO-"+code,
            work_name=name, uom=uom, category=categories[group],
            productivity_per_workday=norm, allow_daywork=1, allow_piecework=0, active=1)
        # Demo capacity is daywork only. No approved piecework price exists in
        # this fixture; leave payroll rates unset instead of inventing a rate.
        work_ids[code] = frappe.get_doc(values).insert().name

    def make_plan(on_date, work_team, work_rows, completed=None):
        line_data = []
        for pcode, work, qty in work_rows:
            p = frappe.get_doc("Farm Plot", plots[pcode])
            line_data.append(dict(farm=farm.name, farm_block=p.farm_block, farm_plot=p.name,
                crop_cycle=cycles[pcode], work_type=work_ids[work], planned_qty=qty,
                work_team=teams[work_team]))
        plan = farm_doc("Daily Work Plan", posting_date=on_date, lines=line_data).insert()
        plan.submit()
        if completed is not None:
            for row, done in zip(plan.lines, completed):
                farm_doc("Daily Work Result",
                    farm_block=row.farm_block, farm_plot=row.farm_plot,
                    crop_cycle=row.crop_cycle, posting_date=on_date,
                    work_plan=plan.name, work_plan_line=row.name,
                    completed_qty=done, actual_workdays=0,
                    unfinished_reason="Mưa hoặc thiếu vật tư (mẫu)" if done < row.planned_qty else "").insert().submit()
        return plan.name

    yesterday = add_days(nowdate(), -1)
    make_plan(yesterday, 1, [("A01-01", "BAG", 800), ("A01-02", "PROP", 200)], [750, 200])
    make_plan(nowdate(), 2, [("A02-01", "BUD", 500), ("A02-02", "WEED", 1.5)])
    make_plan(nowdate(), 3, [("A03-01", "REPLANT", 250), ("A03-02", "FERT", 600)])

    # Labor totals are one separate daily report, not tied to piecework rows.
    farm_doc("Daily Labor Summary",
        posting_date=yesterday, work_category=categories["Chăm sóc buồng"],
        work_area="Field", headcount=12, present=10,
        staffing_target=12, actual_workdays=10, area_ha=80).insert().submit()

    return dict(farm=farm.name, company=company, blocks=len(blocks), plots=len(plots),
                cycles=len(cycles), teams=len(teams), work_types=len(work_ids),
                note="Demo seeded on test site ONLY. Visit /lotus/giao-viec?farm="+farm.name)
