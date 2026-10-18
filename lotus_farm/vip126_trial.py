"""Isolated, read-only VIP 126 trial on the running Lotus site.

Historical OneDrive *planning* is used to illustrate ratios, not as measurements
of Lotus Farm. Missing counts and stage dates are generated in memory, never
written to Farm Block, Crop Cycle, Harvest Profile, stock or sales.
"""
from datetime import date, timedelta
import frappe
from frappe.utils import add_months, flt, getdate, nowdate
from lotus_farm.reporting import records
from lotus_farm.scoping import land_scope, land_filters
from lotus_farm.vip126_live import FARM, VARIETY
from lotus_farm.vip126_zone_plan import planned_dates
from lotus_farm.vip126_timeline import (
    SCENARIOS, _event_candidates, _pick_anchor, _year_rows,
    _month_end, _monthbins,
)

# From OneDrive: planned 17 kg / preprocessed bunch, 98% preprocessed/harvest.
# Distinct cut->harvest is chosen for trial; NOT validated by Lotus.
# Lower/upper variants are EXPLICIT what-if assumptions, not empirical limits.
TRIAL = {
    "low": {"name": "Thấp", "density": 2269, "flower_share": .40,
            "cut_rate": .85, "harvest_rate": .96,
            "preprocess_rate": .95, "packed_kg_per_processed_bunch": 15.,
            "raw_kg_per_cut_bunch": 18.},
    "base": {"name": "Cơ sở", "density": 2600, "flower_share": .60,
             "cut_rate": .90, "harvest_rate": .98,
             "preprocess_rate": .98, "packed_kg_per_processed_bunch": 17.,
             "raw_kg_per_cut_bunch": 20.},
    "high": {"name": "Cao", "density": 2600, "flower_share": .80,
             "cut_rate": .95, "harvest_rate": .995,
             "preprocess_rate": .99, "packed_kg_per_processed_bunch": 19.,
             "raw_kg_per_cut_bunch": 23.},
}

# Every projected flowering cohort follows 20% / 60% / 20% across three months.
# User-selected trial rule; NOT an observed distribution at Lotus.
FLOWERING_DISTRIBUTION = (20, 60, 20)

# A–D flowering estimates stored on Farm Block follow A's planting sequence.
# E remains unconfirmed; E's date is mocked in trial only.
TRIAL_FLOWERING = {"A": "2026-11-01", "B": "2026-12-01",
                   "C": "2027-01-01", "D": "2027-02-01",
                   "E": "2027-03-01"}
SOURCE_LINKS = {
    "packing_plan": (
        "https://onedrive.live.com/personal/f0460d3126520905/_layouts/15/"
        "doc.aspx?resid=a567ed0a-32dc-4bf6-9b46-33c1aa62b472&"
        "cid=f0460d3126520905&web=1"
    ),
    "planting_records": (
        "https://onedrive.live.com/personal/f0460d3126520905/_layouts/15/"
        "doc.aspx?resid=1ba59cab-afa5-4cd8-aa28-825aa06df0f6&"
        "cid=f0460d3126520905&web=1"
    ),
    "sucker_schedule": (
        "https://onedrive.live.com/personal/af58eed931a9a3a8/_layouts/15/"
        "doc.aspx?resid=f9cdde84-d94d-4d74-a04d-dbd1ec9bf15d&"
        "cid=af58eed931a9a3a8&web=1"
    ),
    "crop_close": (
        "https://onedrive.live.com/personal/af58eed931a9a3a8/_layouts/15/"
        "doc.aspx?resid=000f4a1b-1bda-42e4-8762-034706c7a4f6&"
        "cid=af58eed931a9a3a8&web=1"
    ),
}
DESCRIPTION = (
    "THỬ NGHIỆM: 17 kg/buồng SƠ CHẾ và khoảng 98% số buồng thu đi sơ chế "
    "được lấy từ dòng kế hoạch VIP 126 cũ trong OneDrive, không phải cân/đếm "
    "thực tế tại Lotus. Dữ liệu cũ có mật độ 2.269 / 2.600 cây/ha. "
    "Khoảng cách chọn chồi trong lịch cũ khoảng 6 tháng; KHÔNG đồng nhất "
    "với khoảng cách giữa hai lần thu hoạch. "
     "Tỷ lệ phát buồng, sống tới cắt, thu/cắt, kg thô, ngày trổ E và các dải "
    "thấp/cao chỉ phục vụ thử nghiệm công thức. Mọi số tấn đều chưa duyệt. "
    "Phân bố trổ hoa THỬ NGHIỆM 20% tháng đầu, 60% tháng sau, 20% tháng cuối. "
    "Người quản lý xác nhận trổ tới cắt bắp 17 ngày, cắt bắp tới thu 60–70 ngày. "
    "Hệ thống lấy 65 ngày làm cơ sở, tổng trổ tới thu 82 ngày; chưa hiệu chuẩn thực địa."
)
TEST_STAGES = {
    "plant": ("Thử ngày trồng", 1),
    "sucker": ("Thử ngày chọn chồi", 2),
    "shoot": ("Thử ngày trổ", 3),
    "cut": ("Thử ngày cắt bắp", 4),
    "harvest_actual": ("Thử ngày thu hoạch", 5),
}


def _is_positive(value):
    return value is not None and flt(value) > 0


def _synthetic_anchor(block, count, scenario):
    """Use stored inferred planting for A-D; keep E mock-only."""
    zone = (block.block_code or "")[:1]
    inferred_planting = block.get("lotus_inferred_planting_date")
    flower = block.get("lotus_estimated_flowering_date")
    inferred = bool(inferred_planting and flower and planned_dates(zone))
    estimate = str(flower or TRIAL_FLOWERING[zone])
    return {
        "priority": 1,
        "source": ("inferred_plant" if inferred else
                   ("estimated_flower" if flower else "trial_flower")),
        "source_name": ("Trồng suy ngược → trổ dự kiến khu " + zone if inferred
                        else ("Trổ dự kiến khu " + zone if flower else
                              "Trổ GIẢ LẬP khu " + zone)),
        "source_date": str(inferred_planting) if inferred else estimate,
        "planting_estimate": str(inferred_planting) if inferred else None,
        "harvest_date": getdate(estimate) + timedelta(
            days=SCENARIOS[scenario]["flower_to_harvest"]),
        "bunches": count * TRIAL[scenario]["flower_share"],
        "observed": False, "batch": None, "cycle": None,
    }


def _trial_event_anchor(stage, day, qty, scenario):
    config = SCENARIOS[scenario]
    days = {
        "plant": config["plant_to_flower"] + config["flower_to_harvest"],
        "sucker": config["sucker_to_harvest"],
        "shoot": config["flower_to_harvest"],
        "cut": config["cut_to_harvest"],
        "harvest_actual": 0,
    }[stage]
    return {
        "priority": TEST_STAGES[stage][1], "source": stage,
        "source_name": TEST_STAGES[stage][0],
        "source_date": str(day),
        "harvest_date": getdate(day) + timedelta(days=days),
        "bunches": qty,
        "observed": False, "trial_event": True, "batch": None, "cycle": None,
    }


def _counts(anchor, cycle_no, trial):
    """Keep measurement stages and their denominators distinct.

    17 kg per PREPROCESSED bunch is the terminal mass in the historical
    plan. Never multiply quality and packout on it again.
    """
    source = anchor["source"] if cycle_no == 1 else "future"
    basis = max(0, flt(anchor["bunches"]))
    if source == "cut":
        cut = round(basis)
        harvested = round(cut * trial["harvest_rate"])
        preprocessed = round(harvested * trial["preprocess_rate"])
    elif source == "harvest_actual":
        # The current harvest was already posted; only future ratoons use
        # this reference bunch count. No repeated harvest in forecast rows.
        harvested = round(basis)
        cut = round(harvested / trial["harvest_rate"]) if trial["harvest_rate"] else 0
        preprocessed = round(harvested * trial["preprocess_rate"])
    else:
        cut = round(basis * trial["cut_rate"])
        harvested = round(cut * trial["harvest_rate"])
        preprocessed = round(harvested * trial["preprocess_rate"])
    return {
        "cut_bunches": cut, "harvest_bunches": harvested,
        "preprocessed_bunches": preprocessed,
        "gross_kg": round(cut * trial["raw_kg_per_cut_bunch"], 2),
        "packed_kg": round(
            preprocessed * trial["packed_kg_per_processed_bunch"], 2),
        "bunches": harvested,
    }


def _split_flowering_quantity(total):
    """Integer allocations sum to exact projected flowering bunches."""
    total = max(0, round(flt(total)))
    first = round(total * FLOWERING_DISTRIBUTION[0] / 100)
    second = round(total * FLOWERING_DISTRIBUTION[1] / 100)
    return (first, second, total - first - second)


def _flowering_rows(block, anchor, config, trial, start, end):
    """Project independent 20/60/20 flowering cohorts within each 36m cycle.

    Each cohort goes through cut -> harvest -> preprocessing -> kg separately.
    Observed shooting, cut and actual-harvest first events stay on their
    reported date and quantity; only future ratoons are modeled in waves.
    """
    expanded_start = getdate(add_months(start, -2))
    core_rows = _year_rows(block, anchor, config, expanded_start, end)
    base_flower_date = getdate(anchor["harvest_date"]) - timedelta(
        days=config["flower_to_harvest"])
    portions = _split_flowering_quantity(anchor["bunches"])
    result = []
    for base in core_rows:
        is_first = base["cycle_no"] == 1
        split = (not is_first or anchor["source"] in
                 ("estimated_flower", "trial_flower", "inferred_plant", "plant", "sucker") or
                 (anchor["source"] == "shoot" and not anchor.get("observed")))
        for wave in (range(3) if split else range(1)):
            if split and portions[wave] <= 0:
                continue
            base_flower_month = getdate(add_months(base_flower_date, wave))
            offset_days = (base_flower_month - base_flower_date).days
            predicted_date = getdate(base["expected_date"]) + timedelta(
                days=offset_days if split else 0)
            if not start <= predicted_date <= end:
                continue
            flowering_date = (getdate(base["expected_date"]) -
                              timedelta(days=config["flower_to_harvest"]) +
                              timedelta(days=offset_days))
            if split:
                cut_date = flowering_date + timedelta(days=config["flower_to_cut"])
                cut_observed = False
            elif is_first and anchor["source"] == "cut":
                # Real recorded cutting is the authority; never add 17 again.
                cut_date = getdate(anchor["source_date"])
                cut_observed = bool(anchor.get("observed"))
            elif is_first and anchor["source"] == "shoot":
                cut_date = getdate(anchor["source_date"]) + timedelta(
                    days=config["flower_to_cut"])
                cut_observed = False
            else:
                cut_date = None
                cut_observed = False
            harvested_earliest = cut_date + timedelta(days=60) if cut_date else None
            harvested_latest = cut_date + timedelta(days=70) if cut_date else None
            counted_anchor = dict(anchor)
            if split:
                counted_anchor["bunches"] = portions[wave]
            row = dict(base)
            row.update(_counts(counted_anchor, base["cycle_no"], trial))
            row.update({
                "expected_date": str(predicted_date),
                "month": str(predicted_date)[:7],
                "flowering_date": str(flowering_date) if split else (
                    str(anchor["source_date"]) if is_first and anchor["source"] == "shoot" else None),
                "flowering_month": str(flowering_date)[:7] if split else None,
                "cut_date": str(cut_date) if cut_date else None,
                "cut_observed": cut_observed,
                "harvest_earliest_date": str(harvested_earliest) if harvested_earliest else None,
                "harvest_latest_date": str(harvested_latest) if harvested_latest else None,
                "flowering_share_percent": FLOWERING_DISTRIBUTION[wave]
                    if split else None,
                "flowering_bunches": portions[wave] if split else None,
                "flowering_wave": wave + 1 if split else None,
                "flowering_wave_count": 3 if split else None,
            })
            result.append(row)
    return result


@frappe.whitelist()
def calendar(farm=None, zone=None, block=None, scenario="base",
             from_date=None, trial_block=None, trial_stage=None,
             trial_date=None, trial_qty=None):
    if not frappe.has_permission("Harvest Forecast", "read") or not frappe.has_permission(
        "Farm Block", "read"
    ):
        frappe.throw("Không có quyền xem dự thu thử nghiệm.", frappe.PermissionError)
    if scenario not in TRIAL:
        frappe.throw("Kịch bản không hợp lệ.")
    if zone and zone not in TRIAL_FLOWERING:
        frappe.throw("Khu chỉ có A, B, C, D hoặc E.")
    if farm and farm != FARM:
        return {"available": False, "note": "Chỉ dành cho Vườn 222."}
    test_enabled = bool(trial_block or trial_stage or trial_date or trial_qty)
    if test_enabled and not (trial_block and trial_stage and trial_date):
        frappe.throw("Thử mốc cần đủ Lô, công đoạn và ngày.")
    if trial_stage and trial_stage not in TEST_STAGES:
        frappe.throw("Công đoạn thử không hợp lệ.")
    if trial_date:
        event_date = getdate(trial_date)
        if not date(2020, 1, 1) <= event_date <= date(2040, 12, 31):
            frappe.throw("Ngày thử nằm ngoài phạm vi hỗ trợ.")
    else:
        event_date = None

    selected = land_scope(farm=FARM, block=block)
    fields = ["name", "farm", "block_code", "block_name", "variety", "area_ha",
              "planting_date", "lotus_tree_count", "lotus_estimated_flowering_date",
              "lotus_inferred_planting_date"]
    blocks = records("Farm Block",
                     land_filters(frappe.get_meta("Farm Block"), selected),
                     fields)
    blocks = [b for b in blocks if b.farm == FARM and b.variety == VARIETY and
              (not zone or (b.block_code or "").startswith(zone))]
    allowed_codes = {b.block_code for b in blocks}
    if trial_block and trial_block not in allowed_codes:
        frappe.throw("Không thể thử mốc tại lô nằm ngoài phạm vi đã chọn.",
                     frappe.PermissionError)

    config = SCENARIOS[scenario]
    trial = TRIAL[scenario]
    start = getdate(from_date or nowdate()).replace(day=1)
    end = _month_end(start)
    observation = _event_candidates(blocks, config, start, end)
    months = _monthbins(start)
    rows = []
    issues = []
    synthetic_count_lots = 0
    synthetic_anchor_lots = 0
    tested_lots = 0
    source_lots = 0
    for b in blocks:
        real_count = int(b.get("lotus_tree_count") or 0)
        synthetic_count = real_count <= 0
        if synthetic_count:
            synthetic_count_lots += 1
        count = (round(flt(b.area_ha) * trial["density"]) if synthetic_count
                 else real_count)
        if count <= 0:
            issues.append({"block_code": b.block_code,
                           "reason": "Không có diện tích/số cây để chạy thử."})
            continue
        events = observation.get(b.name, [])
        active = _pick_anchor(b, events, config)
        if active and active.get("observed") and _is_positive(active.get("bunches")):
            source_lots += 1
        else:
            active = _synthetic_anchor(b, count, scenario)
            if active["source"] == "trial_flower":
                synthetic_anchor_lots += 1
        if trial_block == b.block_code:
            qty = flt(trial_qty) if trial_qty is not None and str(
                trial_qty).strip() else round(count * trial["flower_share"])
            if qty <= 0 or qty > max(1000, count * 2):
                frappe.throw("Số lượng thử phải dương và không quá gấp đôi cây lô.")
            active = _trial_event_anchor(trial_stage, event_date, qty, scenario)
            tested_lots += 1
        if len([x for x in events if _is_positive(x.get("bunches"))]) > 1:
            issues.append({"block_code": b.block_code,
                           "reason": "Nhiều đợt cùng lô; cần liên kết đợt chồi để không cộng trùng."})
        predicted = _flowering_rows(b, active, config, trial, start, end)
        for r in predicted:
            r.update({
                "synthetic_count": synthetic_count,
                "estimated_stage": not active["observed"],
                "trial_event": bool(active.get("trial_event")),
                "synthetic_stage": active["source"] == "trial_flower",
                "inferred_planting": active.get("planting_estimate"),
                "trial_mode": True,
                "confidence": "THỬ NGHIỆM",
                "approved": False, "commit_ready": False,
                "source_label": (active["source_name"] if r["cycle_no"] == 1 else
                                 "Vụ chồi dự phóng từ mốc thử"),
                "tree_count_used": count,
                "tree_count_source": ("Giả lập từ ha × mật độ" if synthetic_count
                                      else "Số cây từ Excel"),
            })
            if r["month"] not in months:
                raise ValueError("Forecast fell outside the monthly 36-month window")
            for key in ("bunches", "gross_kg", "packed_kg"):
                months[r["month"]][key] += r[key]
            rows.append(r)

    rows.sort(key=lambda r: (r["expected_date"], r["block_code"], r["cycle_no"]))
    return {
        "available": True, "farm": FARM, "zone": zone or "ALL",
        "status": "LIVE_SIMULATION_ONLY", "simulation": True,
        "scenario": scenario, "scenario_name": trial["name"],
        "from_date": str(start), "to_date": str(end),
        "flowering_distribution_percent": list(FLOWERING_DISTRIBUTION),
        "rows": rows, "months": list(months.values()), "issues": issues,
        "config": {**trial,
                   "flower_to_harvest": config["flower_to_harvest"],
                   "plant_to_flower": config["plant_to_flower"],
                   "sucker_to_harvest": config["sucker_to_harvest"],
                   "cut_to_harvest": config["cut_to_harvest"],
                   "flower_to_cut": config["flower_to_cut"],
                   "cut_to_harvest_min": 60,
                   "cut_to_harvest_max": 70,
                   "ratoon_days": config["ratoon_days"],
                   "sucker_selection_interval_days": 183,
                   "flowering_distribution_percent": list(FLOWERING_DISTRIBUTION)},
        "trial_event": {
            "block": trial_block, "stage": trial_stage,
            "date": str(event_date) if event_date else None,
            "qty": flt(trial_qty) if trial_qty else None,
        } if tested_lots else None,
        "summary": {
            "total_lots": len(blocks), "projected_lots": len(
                {x["block"] for x in rows}),
            "known_count_lots": len(blocks) - synthetic_count_lots,
            "synthetic_count_lots": synthetic_count_lots,
            "synthetic_anchor_lots": synthetic_anchor_lots,
            "estimated_planting_lots": len({r["block"] for r in rows if r["inferred_planting"]}),
            "tested_lots": tested_lots,
            "gross_kg": round(sum(r["gross_kg"] for r in rows), 2),
            "packed_kg": round(sum(r["packed_kg"] for r in rows), 2),
            "bunches": sum(r["bunches"] for r in rows),
            "releasable_kg": 0,
        },
        "source_notice": DESCRIPTION,
        "source_links": SOURCE_LINKS,
        "safe_note": ("Không ghi giả lập vào DB, lịch sử, kho hoặc bán hàng. "
                      "Lịch chọn chồi 183 ngày là nhịp kế hoạch, không phải "
                      "khoảng cách giữa hai kỳ thu."),
    }