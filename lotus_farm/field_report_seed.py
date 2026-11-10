"""One-off setup of công việc ngoài vườn for Vườn 222 (LOTUS-222), agreed with the user on 29 and 31/10/2026.

- Work types + giá khoán from "HẠNG MỤC KHOÁN VÀ GIÁ KHOÁN TẠI VƯỜN CHUỐI 222" (21/10/2026). Chuối ép uses the
  chuối F price; items with two levels (chống đổ 2/3 dây, rải tro 3/5 kg) are two work types. Công nhật column →
  năng suất tối thiểu/tối đa per công. Chích bắp / cắt bắp / sửa ống nước are công nhật only (no price).
- Đội khu A + B (khu A, B), đội trưởng Trương Văn Hải; he gets the Lotus Field Supervisor role.
- Tổ 01–09 become tổ (level Team); the đội trưởng puts them into the đội on the Đội, tổ & lô screen.
Run: bench --site <site> execute lotus_farm.field_report_seed.apply  (dry run; commit=1 to write).
"""
import frappe

FARM = "LOTUS-222"
VALID_FROM = "2026-10-21"
CREW_NAME, CREW_ZONES = "Đội khu A + B", "A, B"
CREW_LEADER = "haitrongvan1987@gmail.com"
# code, name, uom, basis, rate, norm_min, norm_max, bunch stage, note
WORKS = [
    ("F222-01", "Vặt râu, vén lá cọ buồng, vắt lá đài, tặt trái nách, vệ sinh buồng", "Buồng", "Count", 3500, 85, 120, "Care", "Vặt toàn bộ buồng"),
    ("F222-02", "Bao buồng, chèn nải 2 lớp, bìa lô thêm bao cám", "Buồng", "Count", 4000, 120, 200, "Bag", ""),
    ("F222-03", "Chống đổ 3 dây", "Cây", "Count", 3000, 150, 200, "Prop", "1.000 đ/dây"),
    ("F222-04", "Chống đổ 2 dây", "Cây", "Count", 2000, 150, 200, "Prop", "1.000 đ/dây"),
    ("F222-05", "Chích bắp", "Buồng", None, 0, 0, 0, "Bud Injection", "Công nhật, phụ cấp chăm buồng 20.000 đ/người/ngày"),
    ("F222-06", "Cắt bắp, buộc dây màu", "Buồng", None, 0, 0, 0, "Cut Bud", "Công nhật; màu dây theo lịch tuần"),
    ("F222-07", "Cắt lá", "Ha", "Area", 300000, 1, 1.5, "", "115 đ/cây; 1 tháng 3 lần"),
    ("F222-08", "Dọn cỏ gốc, bẹ lá khô", "Ha", "Area", 300000, 1, 1.5, "", "115 đ/cây"),
    ("F222-09", "Dọn lá cọ buồng", "Ha", "Area", 400000, 0, 0, "", "400.000 đ/ha/tháng, 10 ha/người, làm xuyên suốt"),
    ("F222-10", "Cào lá gốc", "Ha", "Area", 750000, 0.4, 0.4, "", "2,5 người/ha; 1 vụ làm 1 lần"),
    ("F222-11", "Bốc vận chuyển ra lô", "Bao", "Count", 1000, 0, 0, "", "1.000 đ/bao"),
    ("F222-12", "Bón phân hữu cơ (5 kg/gốc)", "Cây", "Trees", 600, 450, 600, "", "Định lượng 1 người"),
    ("F222-13", "Bón lân (200–300 g/gốc)", "Cây", "Trees", 150, 2000, 2500, "", ""),
    ("F222-14", "Bón phân hóa học (120–150 g/gốc)", "Cây", "Trees", 120, 2500, 3000, "", ""),
    ("F222-15", "Rải tro 3 kg/gốc", "Cây", "Trees", 400, 0, 0, "", ""),
    ("F222-16", "Rải tro 5 kg/gốc", "Cây", "Trees", 600, 0, 0, "", ""),
    ("F222-17", "Chọn F (chọn chồi)", "Ha", "Area", 290000, 0.8, 1, "Sucker Select", ""),
    ("F222-18", "Hạ cây, dọn cây thu hoạch", "Cây", "Count", 700, 0, 0, "", "Hạ lá, hạ thân để gọn hàng 3 m"),
    ("F222-19", "Xịt cỏ, xịt bệnh gốc", "Ha", "Area", 300000, 1, 1.2, "", ""),
    ("F222-20", "Xắn chồi lần 1", "Cây", "Trees", 600, 600, 600, "", "4 người/ha"),
    ("F222-21", "Xắn chồi đã chọn chồi (khu D, E)", "Cây", "Trees", 700, 600, 600, "", "4 người/ha"),
    ("F222-22", "Xắn chồi lần 2", "Cây", "Trees", 450, 800, 800, "", "3 người/ha"),
    ("F222-23", "Cắt F hủy lấy đỉnh", "Cây", "Count", 400, 0, 0, "", "3,5 người/ha"),
    ("F222-24", "Cắt chồi", "Ha", "Area", 400000, 1, 1.4, "", ""),
    ("F222-25", "Kiểm tra, sửa béc tưới", "Ha", "Area", 75000, 0, 0, "", "3 lần/tháng, trước kế hoạch tưới phân 2 ngày"),
    ("F222-26", "Sửa ống nước", "Ha", None, 0, 0, 0, "", "Công nhật"),
]

# How each việc is paid, agreed 31/10/2026: (nhóm, cách trả, trần, bắt buộc vật tư). Khoán only what an independent
# count can check (Count), or a whole lô an inspector accepts (Lot); the rest is công nhật. Cắt bắp stays công nhật:
# its count is the base every bunch cap is checked against.
MODES = {
    "F222-01": ("Bunch", "Count", "LotTrees", 0), "F222-02": ("Bunch", "Count", "CutBud", 0),
    "F222-03": ("Bunch", "Count", "LotTrees", 0), "F222-04": ("Bunch", "Count", "LotTrees", 0),
    "F222-05": ("Bunch", "Daywork", "None", 0), "F222-06": ("Bunch", "Daywork", "None", 0),
    "F222-07": ("Field", "Lot", "LotArea", 0), "F222-08": ("Field", "Lot", "LotArea", 0),
    "F222-09": ("Field", "Lot", "LotArea", 0), "F222-10": ("Field", "Lot", "LotArea", 0),
    "F222-11": ("Field", "Count", "None", 0),
    "F222-12": ("Protection", "Count", "LotTrees", 1), "F222-13": ("Protection", "Count", "LotTrees", 1),
    "F222-14": ("Protection", "Count", "LotTrees", 1), "F222-15": ("Protection", "Count", "LotTrees", 1),
    "F222-16": ("Protection", "Count", "LotTrees", 1),
    "F222-17": ("Field", "Lot", "LotArea", 0), "F222-18": ("Field", "Count", "LotTrees", 0),
    "F222-19": ("Protection", "Daywork", "None", 1),
    "F222-20": ("Field", "Lot", "LotTrees", 0), "F222-21": ("Field", "Lot", "LotTrees", 0), "F222-22": ("Field", "Lot", "LotTrees", 0),
    "F222-23": ("Field", "Count", "LotTrees", 0), "F222-24": ("Field", "Lot", "LotArea", 0),
    "F222-25": ("Field", "Daywork", "None", 0), "F222-26": ("Field", "Daywork", "None", 0),
}


def _modes(code):
    group, pay, cap, material = MODES[code]
    return {"lotus_work_group": group, "lotus_pay_mode": pay, "lotus_cap_basis": cap, "lotus_requires_material": material}


BEFORE_CUT_CODES = ("F222-01", "F222-03", "F222-04")  # tỉa, chống đổ 3 dây, chống đổ 2 dây


def apply_bunch_stages(commit=0):
    """Mark "Chọn F" as the sucker-selection stage, and cap tỉa and chống đổ by the trees of the lô, on the catalogue and on the phiếu already open.
    Every other field of the work types stays as the farm has it."""
    from lotus_farm.field_report_rules import APPROVED, CAP_CUT_BUD, CAP_TREES, FAILED, OPEN, REPORTED
    frappe.only_for("System Manager")
    name = frappe.db.get_value("Work Type", {"work_code": "F222-17"})
    if not name:
        frappe.throw("Không có việc F222-17.")
    print("F222-17 stage:", frappe.db.get_value("Work Type", name, "lotus_bunch_stage"), "-> Sucker Select")
    works = [w for w in (frappe.db.get_value("Work Type", {"work_code": code}) for code in BEFORE_CUT_CODES) if w]
    tickets = frappe.get_all("Lotus Work Assignment", filters={"work_type": ["in", works or [""]], "cap_basis": CAP_CUT_BUD, "state": ["in", [OPEN, REPORTED, APPROVED, FAILED]]}, pluck="name")
    print("Tỉa, chống đổ -> trần số cây:", len(works), "việc,", len(tickets), "phiếu đang mở")
    if int(commit):
        frappe.db.set_value("Work Type", name, "lotus_bunch_stage", "Sucker Select")
        for work in works:
            frappe.db.set_value("Work Type", work, "lotus_cap_basis", CAP_TREES)
        for ticket in tickets:
            frappe.db.set_value("Lotus Work Assignment", ticket, "cap_basis", CAP_TREES, update_modified=False)
        frappe.db.commit()
    else:
        print("Dry run only. Run with commit=1 to write.")


def apply_modes(commit=0):
    """Give the F222 work types their group and pay mode (after the 31/10/2026 redesign). Dry run unless commit=1."""
    frappe.only_for("System Manager")
    changed = []
    for code in MODES:
        name = frappe.db.get_value("Work Type", {"work_code": code})
        if not name:
            continue
        doc = frappe.get_doc("Work Type", name)
        doc.update(_modes(code))
        if doc.has_value_changed("lotus_pay_mode") or doc.has_value_changed("lotus_work_group") or doc.is_new():
            changed.append(code)
        doc.save(ignore_permissions=True)
    print("Work types with a pay mode:", len(MODES), "| changed:", len(changed))
    if int(commit):
        frappe.db.commit()
    else:
        frappe.db.rollback()
        print("Dry run only. Run with commit=1 to write.")
    return changed


# Việc the sổ lô needs that are not in the khoán list (spec 002): code, name, uom, stage, group, flags.
LEDGER_WORKS = [
    ("F222-27", "Hủy buồng", "Buồng", "Reject", "Bunch", {}),
    ("F222-28", "Thu hoạch buồng", "Buồng", "Harvest", "Bunch", {}),
    ("F222-29", "Kiểm tra sâu bệnh", "Cây", "", "Protection", {"lotus_records_disease": 1}),
]


def apply_ledger_works(commit=0):
    """Add hủy buồng, thu hoạch and kiểm tra sâu bệnh as việc of LOTUS-222 (công nhật: no money on the line).
    A stage that already has a việc keeps it. Dry run unless commit=1."""
    frappe.only_for("System Manager")
    created = []
    for code, name, uom, stage, group, flags in LEDGER_WORKS:
        if stage and frappe.db.exists("Work Type", {"lotus_bunch_stage": stage, "lotus_farm": FARM, "active": 1}):
            continue
        if not stage and frappe.db.exists("Work Type", {"lotus_records_disease": 1, "lotus_farm": FARM, "active": 1}):
            continue
        if frappe.db.exists("Work Type", {"work_code": code}):
            doc = frappe.get_doc("Work Type", frappe.db.get_value("Work Type", {"work_code": code}))
        else:
            doc = frappe.new_doc("Work Type")
        if not frappe.db.exists("UOM", uom):
            frappe.get_doc({"doctype": "UOM", "uom_name": uom}).insert(ignore_permissions=True)
        doc.update({"work_code": code, "work_name": name, "uom": uom, "active": 1, "allow_daywork": 1, "allow_piecework": 0,
                    "piecework_rate": 0, "productivity_per_workday": 1, "lotus_farm": FARM, "lotus_bunch_stage": stage or None,
                    "lotus_work_group": group, "lotus_pay_mode": "Daywork", "lotus_cap_basis": "None", "lotus_requires_material": 0,
                    **flags})
        doc.save(ignore_permissions=True)
        created.append(code)
    print("Việc thêm cho sổ lô:", created or "không có")
    if int(commit):
        frappe.db.commit()
    else:
        frappe.db.rollback()
        print("Dry run only. Run with commit=1 to write.")
    return created


def plan():
    rows = []
    for code, name, uom, basis, rate, low, high, stage, note in WORKS:
        existing = frappe.db.get_value("Work Type", {"work_code": code})
        rows.append(dict(code=code, name=name, uom=uom, basis=basis, rate=rate, low=low,
                         high=high, stage=stage, note=note, existing=existing,
                         priced=bool(existing and frappe.db.exists("Lotus Piece Rate", {"farm": FARM, "work_type": existing}))))
    crew = frappe.db.get_value("Work Team", {"farm": FARM, "lotus_team_level": "Crew", "team_name": CREW_NAME})
    teams = [t.name for t in frappe.get_all("Work Team", filters={"farm": FARM}, fields=["name", "lotus_team_level"])
             if not t.lotus_team_level]
    return dict(works=rows, crew=crew, teams=sorted(teams),
                leader_ok=bool(frappe.db.get_value("User", {"name": CREW_LEADER, "enabled": 1})))


def apply(commit=0):
    frappe.only_for("System Manager")
    state = plan()
    print("Work types new:", sum(1 for w in state["works"] if not w["existing"]), "/", len(state["works"]),
          "| prices new:", sum(1 for w in state["works"] if w["basis"] and not w["priced"]),
          "| crew exists:", bool(state["crew"]), "| tổ to mark:", len(state["teams"]), "| leader ok:", state["leader_ok"])
    if not int(commit):
        frappe.db.rollback()
        print("Dry run only. Run with commit=1 to write.")
        return state
    for w in state["works"]:
        doc = frappe.get_doc("Work Type", w["existing"]) if w["existing"] else frappe.new_doc("Work Type")
        doc.update({"work_code": w["code"], "work_name": w["name"], "uom": w["uom"], "active": 1,
                    "allow_daywork": 1, "allow_piecework": 1 if w["rate"] else 0, "piecework_rate": w["rate"] or 0,
                    "productivity_per_workday": w["low"] or w["high"] or 1, "lotus_farm": FARM, "lotus_bunch_stage": w["stage"] or None,
                    **_modes(w["code"])})
        doc.save(ignore_permissions=True)
        if w["basis"] and not w["priced"]:
            frappe.get_doc({"doctype": "Lotus Piece Rate", "farm": FARM, "work_type": doc.name, "basis": w["basis"],
                            "rate": w["rate"], "uom": w["uom"], "norm_min": w["low"], "norm_max": w["high"],
                            "valid_from": VALID_FROM, "notes": w["note"]}).insert(ignore_permissions=True)
    for name in state["teams"]:
        frappe.db.set_value("Work Team", name, "lotus_team_level", "Team")
    if not state["crew"]:
        crew = frappe.get_doc({"doctype": "Work Team", "farm": FARM, "team_code": "DOI-AB", "team_name": CREW_NAME, "active": 1,
                               "lotus_team_level": "Crew", "lotus_zones": CREW_ZONES,
                               "lotus_leader": CREW_LEADER if state["leader_ok"] else None})
        crew.insert(ignore_permissions=True)
    if state["leader_ok"]:
        user = frappe.get_doc("User", CREW_LEADER)
        if "Lotus Field Supervisor" not in frappe.get_roles(CREW_LEADER):
            user.add_roles("Lotus Field Supervisor")
    frappe.db.commit()
    print("Done.")
    return plan()
