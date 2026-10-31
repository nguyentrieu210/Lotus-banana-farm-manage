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
# code, name, category, uom, basis, rate, norm_min, norm_max, bunch stage, note
WORKS = [
    ("F222-01", "Vặt râu, vén lá cọ buồng, vắt lá đài, tặt trái nách, vệ sinh buồng", "Chăm sóc buồng / Vén lá, tỉa trái, lặt hoa", "Buồng", "Count", 3500, 85, 120, "Care", "Vặt toàn bộ buồng"),
    ("F222-02", "Bao buồng, chèn nải 2 lớp, bìa lô thêm bao cám", "Chăm sóc buồng / Bao Buồng", "Buồng", "Count", 4000, 120, 200, "Bag", ""),
    ("F222-03", "Chống đổ 3 dây", "Chăm sóc buồng / Chống đổ ngã", "Cây", "Count", 3000, 150, 200, "Prop", "1.000 đ/dây"),
    ("F222-04", "Chống đổ 2 dây", "Chăm sóc buồng / Chống đổ ngã", "Cây", "Count", 2000, 150, 200, "Prop", "1.000 đ/dây"),
    ("F222-05", "Chích bắp", "Chăm sóc buồng / Chích búp", "Buồng", None, 0, 0, 0, "Bud Injection", "Công nhật, phụ cấp chăm buồng 20.000 đ/người/ngày"),
    ("F222-06", "Cắt bắp, buộc dây màu", "Chăm sóc buồng / Cắt bắp, buộc dây màu", "Buồng", None, 0, 0, 0, "Cut Bud", "Công nhật; màu dây theo lịch tuần"),
    ("F222-07", "Cắt lá", "Chăm sóc vườn / Vệ sinh vườn", "Ha", "Area", 300000, 1, 1.5, "", "115 đ/cây; 1 tháng 3 lần"),
    ("F222-08", "Dọn cỏ gốc, bẹ lá khô", "Chăm sóc vườn / Quản lý cỏ dại", "Ha", "Area", 300000, 1, 1.5, "", "115 đ/cây"),
    ("F222-09", "Dọn lá cọ buồng", "Chăm sóc vườn / Vệ sinh vườn", "Ha", "Area", 400000, 0, 0, "", "400.000 đ/ha/tháng, 10 ha/người, làm xuyên suốt"),
    ("F222-10", "Cào lá gốc", "Chăm sóc vườn / Vệ sinh vườn", "Ha", "Area", 750000, 0.4, 0.4, "", "2,5 người/ha; 1 vụ làm 1 lần"),
    ("F222-11", "Bốc vận chuyển ra lô", "Chăm sóc vườn / Bón phân", "Bao", "Count", 1000, 0, 0, "", "1.000 đ/bao"),
    ("F222-12", "Bón phân hữu cơ (5 kg/gốc)", "Chăm sóc vườn / Bón phân", "Cây", "Trees", 600, 450, 600, "", "Định lượng 1 người"),
    ("F222-13", "Bón lân (200–300 g/gốc)", "Chăm sóc vườn / Bón phân", "Cây", "Trees", 150, 2000, 2500, "", ""),
    ("F222-14", "Bón phân hóa học (120–150 g/gốc)", "Chăm sóc vườn / Bón phân", "Cây", "Trees", 120, 2500, 3000, "", ""),
    ("F222-15", "Rải tro 3 kg/gốc", "Chăm sóc vườn / Bón phân", "Cây", "Trees", 400, 0, 0, "", ""),
    ("F222-16", "Rải tro 5 kg/gốc", "Chăm sóc vườn / Bón phân", "Cây", "Trees", 600, 0, 0, "", ""),
    ("F222-17", "Chọn F (chọn chồi)", "Chăm sóc vườn / Quản lý mật độ", "Ha", "Area", 290000, 0.8, 1, "", ""),
    ("F222-18", "Hạ cây, dọn cây thu hoạch", "Thu hoạch / Thu hoạch phụ phẩm", "Cây", "Count", 700, 0, 0, "", "Hạ lá, hạ thân để gọn hàng 3 m"),
    ("F222-19", "Xịt cỏ, xịt bệnh gốc", "Chăm sóc vườn / Quản lý cỏ dại", "Ha", "Area", 300000, 1, 1.2, "", ""),
    ("F222-20", "Xắn chồi lần 1", "Chăm sóc vườn / Quản lý mật độ", "Cây", "Trees", 600, 600, 600, "", "4 người/ha"),
    ("F222-21", "Xắn chồi đã chọn chồi (khu D, E)", "Chăm sóc vườn / Quản lý mật độ", "Cây", "Trees", 700, 600, 600, "", "4 người/ha"),
    ("F222-22", "Xắn chồi lần 2", "Chăm sóc vườn / Quản lý mật độ", "Cây", "Trees", 450, 800, 800, "", "3 người/ha"),
    ("F222-23", "Cắt F hủy lấy đỉnh", "Chăm sóc vườn / Quản lý mật độ", "Cây", "Count", 400, 0, 0, "", "3,5 người/ha"),
    ("F222-24", "Cắt chồi", "Chăm sóc vườn / Quản lý mật độ", "Ha", "Area", 400000, 1, 1.4, "", ""),
    ("F222-25", "Kiểm tra, sửa béc tưới", "Chăm sóc vườn / Tưới nước", "Ha", "Area", 75000, 0, 0, "", "3 lần/tháng, trước kế hoạch tưới phân 2 ngày"),
    ("F222-26", "Sửa ống nước", "Chăm sóc vườn / Tưới nước", "Ha", None, 0, 0, 0, "", "Công nhật"),
]

# How each việc is paid, agreed 31/10/2026: (nhóm, cách trả, trần, bắt buộc vật tư). Khoán only what an independent
# count can check (Count), or a whole lô an inspector accepts (Lot); the rest is công nhật. Cắt bắp stays công nhật:
# its count is the base every bunch cap is checked against.
MODES = {
    "F222-01": ("Bunch", "Count", "CutBud", 0), "F222-02": ("Bunch", "Count", "CutBud", 0),
    "F222-03": ("Bunch", "Count", "CutBud", 0), "F222-04": ("Bunch", "Count", "CutBud", 0),
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


def _category(name):
    found = frappe.db.get_value("Work Category", {"category_name": name})
    if not found:
        frappe.throw(f"Không có nhóm công đoạn {name}.")
    return found


def plan():
    rows = []
    for code, name, category, uom, basis, rate, low, high, stage, note in WORKS:
        existing = frappe.db.get_value("Work Type", {"work_code": code})
        rows.append(dict(code=code, name=name, category=_category(category), uom=uom, basis=basis, rate=rate, low=low,
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
        doc.update({"work_code": w["code"], "work_name": w["name"], "category": w["category"], "uom": w["uom"], "active": 1,
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
