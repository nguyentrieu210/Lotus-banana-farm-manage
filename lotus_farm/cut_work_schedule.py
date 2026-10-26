"""Book2 cut-forecast -> proposed care operations (pure, no DB/write).

One source cut row splits into four forecast waves. Only explicitly linked large
blocks are eligible for a work-plan proposal. Operations based on the injection
date and the measurement window remain ESTIMATES until on-site confirmation.
"""
from __future__ import annotations

import datetime as dt
import hashlib
from collections import defaultdict

from lotus_farm import cut_forecast_rules as rules

# (work code, days from injection, quantity source, note)
INJECTION_STEPS = (
    ("CV020", 0, "shoot_qty", "Chích bắp – cần xác nhận bắp thực tế"),
    ("CV021", 5, "shoot_qty", "Chống đổ: cửa sổ chích +3 đến +10"),
    ("CV022", 7, "shoot_qty", "Vén lá, tỉa trái"),
    ("CV023", 7, "shoot_qty", "Lặt hoa lần 1"),
    ("CV024", 7, "shoot_qty", "Phun buồng lần 1 – theo phác đồ đã duyệt"),
    ("CV025", 10, "shoot_qty", "Lặt hoa lần 2"),
    ("CV026", 10, "shoot_qty", "Phun buồng lần 2 – theo phác đồ đã duyệt"),
    ("CV027", 13, "shoot_qty", "Lặt hoa lần 3"),
    ("CV028", 13, "shoot_qty", "Phun buồng lần 3 – theo phác đồ đã duyệt"),
    ("CV029", 16, "budcut_qty", "Cắt bắp: phải xác nhận ngày kỹ thuật"),
    ("CV030", 16, "budcut_qty", "Cột dây màu"),
    ("CV031", 16, "budcut_qty", "Phun buồng lần 4 – theo phác đồ đã duyệt"),
    ("CV032", 16, "budcut_qty", "Lót nải, chèn xốp"),
    ("CV033", 16, "budcut_qty", "Bao buồng sau phun lần 4"),
)
HARVEST_STEPS = (
    ("CV034", -10, "harvest_qty", "Đo trái: cửa sổ thu -10 đến -7 ngày"),
    ("CV035", 0, "harvest_qty", "Cắt/vác buồng: phải dựa thực tế đo trái"),
    ("CV036", 0, "harvest_qty", "Vận chuyển buồng về xưởng"),
)
# The Book2 stage offsets are 16 days after injection. If the approved
# cut profile differs, NEVER schedule care around a mismatched cut-bud date.
EXPECTED_INJECTION_TO_BUDCUT = 16


def work_calendar(entries, profile, *, from_date=None, to_date=None, farm_block=None):
    """Returns (dated proposals, warnings, number of unmapped cut rows).

    Dates are inclusive. Group identical (date, block, code) into ONE draft line,
    so different flowering waves cannot generate duplicate Work Plan lines.
    """
    start = rules.as_date(from_date) if from_date else None
    end = rules.as_date(to_date) if to_date else None
    if start and end and end < start:
        raise ValueError("Ngày kết thúc phải từ ngày bắt đầu trở đi.")
    grouped = {}
    warnings = set()
    unmapped = 0
    if int(profile["inject_to_budcut_days"]) != EXPECTED_INJECTION_TO_BUDCUT:
        warnings.add("Bộ thông số đã duyệt chưa dùng chích→cắt bắp +16 ngày Book2; chưa sinh lịch chăm sóc để tránh lệch mốc.")
        return [], sorted(warnings), sum(not e.get("farm_block") for e in entries)
    for entry in entries:
        block = entry.get("farm_block")
        if not block:
            unmapped += 1
            continue
        if farm_block and block != farm_block:
            continue
        for wave in rules.expand([entry], profile):
            parts = [(code, wave["inject_date"] + dt.timedelta(days=days), basis, note)
                     for code, days, basis, note in INJECTION_STEPS]
            parts += [(code, wave["harvest_date"] + dt.timedelta(days=days), basis, note)
                      for code, days, basis, note in HARVEST_STEPS]
            for code, when, basis, note in parts:
                if (start and when < start) or (end and when > end):
                    continue
                qty = int(wave[basis])
                if qty <= 0:
                    continue
                key = (block, str(when), code)
                if key not in grouped:
                    grouped[key] = dict(farm_block=block, crop_cycle=entry.get("crop_cycle"),
                                        plan_cohort=entry.get("plan_cohort"),
                                        work_code=code, date=str(when), planned_qty=0,
                                        uom="Buồng" if code != "CV021" else "Cây",
                                        note=note, sources=[], forecast_only=True,
                                        window_end=str(when + dt.timedelta(days=3))
                                           if code == "CV034" else None)
                target = grouped[key]
                if target["crop_cycle"] != entry.get("crop_cycle"):
                    target["crop_cycle"] = None  # Different cycles cannot share a single link.
                if target["plan_cohort"] != entry.get("plan_cohort"):
                    target["plan_cohort"] = None
                target["planned_qty"] += qty
                target["sources"].append(dict(entry=entry.get("name"), wave=wave["wave"],
                                              source_ref=entry.get("source_ref")))
    proposals = []
    for (_block, _when, _code), item in sorted(grouped.items(), key=lambda v: (v[0][1], v[0][0], v[0][2])):
        item["sources"].sort(key=lambda r:(str(r["entry"]), r["wave"], str(r["source_ref"])))
        signature = "|".join([item["farm_block"], item["date"], item["work_code"]]
                             + ["%s:%s" % (s["entry"] or s["source_ref"], s["wave"]) for s in item["sources"]])
        item["schedule_key"] = "BOOK2-" + hashlib.sha256(signature.encode()).hexdigest()[:34]
        proposals.append(item)
    if unmapped:
        warnings.add("%d dòng chặt mẹ chưa được gắn lô; không đưa vào lịch công việc." % unmapped)
    if proposals:
        warnings.add("Các ngày chích, phun, cắt bắp, đo trái và thu là DỰ KIẾN; phải xác nhận tại lô trước khi giao việc.")
    return proposals, sorted(warnings), unmapped
