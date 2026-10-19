"""Read-only 36-month banana harvest outlook, prioritized by observed phenology.

This is a planning view, not Released Harvest Forecast supply. No synthetic
numbers become saleable/committable stock without an approved document.
"""
from collections import defaultdict
from datetime import timedelta

import frappe
from frappe.utils import add_days, add_months, cint, flt, getdate, nowdate

from lotus_farm.reporting import records
from lotus_farm.scoping import land_scope, land_filters


SOURCES = {
    "cut": ("Đã cắt bắp", "Cao", 4),
    "shoot": ("Đã trổ buồng", "Khá", 3),
    "sucker": ("Đã chọn chồi", "Trung bình", 2),
    "plant": ("Ngày trồng", "Thấp", 1),
    "future": ("Vụ chồi dự phóng", "Dự phóng", 0),
}


def _day_offset(profile, key):
    return max(cint(profile.get(key)), 0) if profile else 0


def _date(value):
    return str(getdate(value)) if value else None


def _pick_profile(profiles, block, cycle, predicted_date):
    """Block > farm > variety > general; match cycle type and validity."""
    candidates = []
    for p in profiles:
        if p.farm and p.farm != block.farm:
            continue
        if p.farm_block and p.farm_block != block.name:
            continue
        if p.variety and p.variety != (cycle.variety or block.variety):
            continue
        if p.cycle_type and p.cycle_type != cycle.cycle_type:
            continue
        if p.valid_from and getdate(p.valid_from) > predicted_date:
            continue
        if p.valid_to and getdate(p.valid_to) < predicted_date:
            continue
        specificity = (4 if p.farm_block else 0) + (2 if p.farm else 0) + (1 if p.variety else 0)
        candidates.append((specificity, getdate(p.valid_from) if p.valid_from else getdate("1900-01-01"), cint(p.version), p.name, p))
    return max(candidates, key=lambda entry: entry[:4])[-1] if candidates else None


def _quantities(bunches, profile):
    if not profile or flt(profile.avg_bunch_weight_kg) <= 0:
        return 0, 0
    surviving = max(flt(bunches), 0) * flt(profile.bunch_survival_rate_percent) / 100
    gross = surviving * flt(profile.avg_bunch_weight_kg)
    packed = gross * flt(profile.quality_pass_rate_percent) / 100 * flt(profile.packout_rate_percent) / 100
    return round(gross, 2), round(packed, 2)


def _confidence(source):
    return SOURCES[source][1]


@frappe.whitelist()
def calendar(company=None, farm=None, block=None, cycle=None, from_date=None,zone=None):
    """A rolling, permission-scoped 36-month draft outlook. Never commits stock."""
    if not frappe.has_permission("Harvest Forecast", "read"):
        frappe.throw("Không có quyền xem dự thu.", frappe.PermissionError)
    start = getdate(from_date or nowdate()).replace(day=1)
    end = getdate(add_months(start, 36)) - timedelta(days=1)
    selected = land_scope(company=company, farm=farm, block=block, cycle=cycle, zone=zone)
    blocks = records("Farm Block", land_filters(frappe.get_meta("Farm Block"), selected),
                     ["name", "farm", "block_name", "area_ha", "planting_density", "planting_date", "variety"])
    block_index = {b.name: b for b in blocks}
    cycles = records("Crop Cycle", land_filters(frappe.get_meta("Crop Cycle"), selected),
                     ["name", "farm", "farm_block", "cycle_no", "cycle_type", "parent_cycle",
                      "planting_date", "status", "variety"])
    cycles = [c for c in cycles if c.farm_block in block_index]
    issue_map = {}
    def warn(block_name, message):
        issue_map[(block_name, message)] = {"farm_block": block_name, "block_name": block_index.get(block_name).block_name if block_name in block_index else block_name, "message": message}

    cycle_blocks = {c.farm_block for c in cycles}
    for block_row in blocks:
        if block_row.name not in cycle_blocks:
            if block_row.planting_date:
                cycles.append(frappe._dict(
                    name="Ngày trồng tại lô", farm=block_row.farm,
                    farm_block=block_row.name, cycle_no=1,
                    cycle_type="Plant Crop", parent_cycle=None,
                    planting_date=block_row.planting_date,
                    status="Planned", variety=block_row.variety,
                ))
                warn(block_row.name, "Đang tính từ ngày trồng trên lô, chưa có hồ sơ vụ; cần xác nhận nếu trồng nhiều đợt.")
            else:
                warn(block_row.name, "Chưa có ngày trồng; bổ sung ngay trong thông tin lô.")

    profile_fields = ["name", "farm", "farm_block", "variety", "valid_from", "valid_to",
                      "cycle_type", "version", "avg_bunch_weight_kg",
                      "bunch_survival_rate_percent", "quality_pass_rate_percent",
                      "packout_rate_percent", "planting_to_harvest_days",
                      "sucker_to_harvest_days", "shooting_to_harvest_days",
                      "cut_bud_to_harvest_days", "ratoon_interval_days"]
    if frappe.has_permission("Harvest Profile", "read"):
        profiles = records("Harvest Profile", {"approval_state": "Approved", "active": 1}, profile_fields)
    else:
        profiles = []
        for b in blocks:
            warn(b.name, "Không có quyền đọc bộ hệ số dự thu; chưa thể tính dự phóng.")

    def scoped(doctype):
        return land_filters(frappe.get_meta(doctype), selected)

    lookback = str(start - timedelta(days=1100))
    batches = records("Sucker Selection Batch", scoped("Sucker Selection Batch"),
                      ["name", "farm", "farm_block", "crop_cycle", "selection_date",
                       "selected_sucker_qty", "expected_productive_qty"]) if frappe.has_permission("Sucker Selection Batch", "read") else []
    ops = records("Bunch Operation", {
        **scoped("Bunch Operation"), "docstatus": 1,
        "operation_type": ["in", ["Shooting", "Cut Bud"]],
        "operation_date": ["between", [lookback, str(end)]],
    }, ["name", "farm", "farm_block", "crop_cycle", "sucker_selection_batch",
        "operation_date", "operation_type", "expected_harvest_date", "net_bunch_qty"]) if frappe.has_permission("Bunch Operation", "read") else []

    actual_readable = frappe.has_permission("Harvest Actual", "read")
    actuals = records("Harvest Actual", {
        **scoped("Harvest Actual"), "docstatus": 1,
        "harvest_date": ["between", [lookback, str(end)]],
    }, ["name", "farm_block", "crop_cycle", "sucker_selection_batch", "harvest_date",
        "harvested_bunch_qty", "gross_weight_kg"]) if actual_readable else []

    by_cycle = defaultdict(lambda: defaultdict(list))
    for b in batches:
        by_cycle[b.crop_cycle][b.name].append(("sucker", b))
    for o in ops:
        key = o.sucker_selection_batch or "__unknown__"
        by_cycle[o.crop_cycle][key].append(("cut" if o.operation_type == "Cut Bud" else "shoot", o))
    actual_by_cohort = defaultdict(float)
    actual_months = defaultdict(float)
    for a in actuals:
        actual_by_cohort[(a.crop_cycle, a.sucker_selection_batch or "__unknown__")] += flt(a.harvested_bunch_qty)
        if start <= getdate(a.harvest_date) <= end:
            actual_months[_date(a.harvest_date)[:7]] += flt(a.gross_weight_kg)

    output = []
    def add_entry(c, b, profile, source, when, bunches, source_count=1, batch=None):
        if not when or bunches <= 0 or not (start <= when <= end):
            return
        gross, packed = _quantities(bunches, profile)
        if not gross:
            warn(b.name, "Bộ hệ số thiếu trọng lượng hoặc tỷ lệ tính sản lượng.")
            return
        output.append(dict(
            farm=b.farm, farm_block=b.name, block_name=b.block_name or b.name,
            cycle=c.name, cycle_no=c.cycle_no, batch=batch,
            source=source, source_label=SOURCES[source][0], confidence=_confidence(source),
            expected_date=_date(when), month=_date(when)[:7],
            bunches=round(bunches, 2), gross_kg=gross, packed_kg=packed,
            source_count=source_count, projected=source in ("plant", "future"),
            commit_ready=False, profile=profile.name,
        ))

    for c in cycles:
        b = block_index[c.farm_block]
        cohort_groups = by_cycle.get(c.name, {})
        has_batches = any(key != "__unknown__" for key in cohort_groups)
        if "__unknown__" in cohort_groups and has_batches:
            warn(b.name, f"Vụ {c.cycle_no}: có số liệu chưa gắn đợt chồi, cần đối chiếu để tránh cộng trùng.")
        if not cohort_groups and not c.planting_date and cint(c.cycle_no) <= 1:
            warn(b.name, f"Vụ {c.cycle_no} chưa có ngày trồng hoặc dữ liệu ngoài vườn.")
        if cohort_groups:
            for batch_key, sources in cohort_groups.items():
                if batch_key == "__unknown__" and has_batches:
                    continue  # Unlinked events might duplicate linked batches.
                priority = max(SOURCES[k][2] for k, _ in sources)
                chosen = [(k, r) for k, r in sources if SOURCES[k][2] == priority]
                if len(set(k for k, _ in sources)) > 1:
                    warn(b.name, f"Vụ {c.cycle_no}: nhiều công đoạn cùng đợt, chỉ lấy nguồn ưu tiên cao nhất; cần tách đợt nếu mới làm một phần.")
                source = chosen[0][0]
                # Make one dated row per observed event; do not distribute quantity evenly.
                for _, event in chosen:
                    reference = getdate(event.operation_date if source != "sucker" else event.selection_date)
                    rough_profile = _pick_profile(profiles, b, c, max(reference, start))  # For choosing offset.
                    if not rough_profile:
                        warn(b.name, "Thiếu bộ hệ số đã duyệt cho vườn/lô/vụ.")
                        continue
                    days = {
                        "cut": _day_offset(rough_profile, "cut_bud_to_harvest_days"),
                        "shoot": _day_offset(rough_profile, "shooting_to_harvest_days"),
                        "sucker": _day_offset(rough_profile, "sucker_to_harvest_days"),
                    }[source]
                    if source == "cut" and event.expected_harvest_date:
                        expected = getdate(event.expected_harvest_date)
                    elif days > 0:
                        expected = reference + timedelta(days=days)
                    else:
                        warn(b.name, f"Chưa thiết lập số ngày từ {SOURCES[source][0].lower()} đến thu.")
                        continue
                    profile = _pick_profile(profiles, b, c, expected)
                    if not profile:
                        warn(b.name, "Không có bộ hệ số còn hiệu lực tại ngày dự kiến thu.")
                        continue
                    count = flt(event.selected_sucker_qty) if source == "sucker" else flt(event.net_bunch_qty)
                    if len(chosen) == 1:
                        count = max(0, count - actual_by_cohort[(c.name, batch_key)])
                    elif actual_by_cohort[(c.name, batch_key)]:
                        warn(b.name, "Đã có thu hoạch trong đợt có nhiều phiếu; chưa tự trừ để tránh trừ lặp.")
                    add_entry(c, b, profile, source, expected, count, batch=None if batch_key=="__unknown__" else batch_key)
            continue

        # Weak planting estimate is only allowed for original crop (Cycle 1).
        if cint(c.cycle_no) == 1 and c.planting_date:
            reference = getdate(c.planting_date)
            profile = _pick_profile(profiles, b, c, max(reference, start))
            days = _day_offset(profile, "planting_to_harvest_days")
            if not days:
                warn(b.name, "Thiếu thiết lập số ngày từ trồng đến thu trong bộ hệ số.")
                continue
            expected = reference + timedelta(days=days)
            profile = _pick_profile(profiles, b, c, expected)
            if not profile:
                warn(b.name, "Bộ hệ số dự thu chưa có hiệu lực ở kỳ thu dự kiến.")
                continue
            count = flt(b.area_ha) * flt(b.planting_density)
            if not count:
                warn(b.name, "Thiếu diện tích hoặc mật độ cây của lô; chưa thể tính số buồng.")
                continue
            count = max(0, count - actual_by_cohort[(c.name, "__unknown__")])
            add_entry(c, b, profile, "plant", expected, count)
        elif cint(c.cycle_no) > 1:
            warn(b.name, f"Vụ chồi {c.cycle_no} chưa có ngày chọn chồi, chưa có nguồn để dự thu.")

    # Read-only virtual ratoons: not real Crop Cycles, never created as saleable supply.
    existing = defaultdict(set)
    for c in cycles:
        existing[c.farm_block].add(cint(c.cycle_no))
    for c in cycles:
        if cint(c.cycle_no) != 1 or not c.planting_date:
            continue
        b = block_index[c.farm_block]
        base_profile = _pick_profile(profiles, b, c, max(getdate(c.planting_date), start))
        plant_days = _day_offset(base_profile, "planting_to_harvest_days")
        ratoon_interval = _day_offset(base_profile, "ratoon_interval_days")
        if not plant_days or not ratoon_interval:
            if plant_days:
                warn(b.name, "Thiếu khoảng cách giữa các vụ chồi; chưa thể dự phóng 3 năm.")
            continue
        count = flt(b.area_ha) * flt(b.planting_density)
        if count <= 0:
            continue
        first = getdate(c.planting_date) + timedelta(days=plant_days)
        for n in range(2, 9):
            if n in existing[b.name]:
                continue
            date = first + timedelta(days=ratoon_interval * (n - 1))
            if date > end:
                break
            if date < start:
                continue
            virtual_cycle = frappe._dict(name=f"Dự phóng vụ {n}", cycle_no=n, cycle_type="Ratoon", variety=c.variety)
            profile = _pick_profile(profiles, b, virtual_cycle, date)
            if not profile:
                warn(b.name, "Chưa có bộ hệ số được duyệt cho vụ chồi tương lai.")
                continue
            add_entry(virtual_cycle, b, profile, "future", date, count)

    # Rows and totals are grouped by month; draft projections are never part of Released supply.
    aggregate = {}
    for r in output:
        key = (r["farm_block"], r["cycle"], r["month"], r["source"], r.get("batch") or "")
        if key not in aggregate:
            aggregate[key] = dict(r)
        else:
            target = aggregate[key]
            for col in ("bunches", "gross_kg", "packed_kg", "source_count"):
                target[col] += r[col]
            if r["expected_date"] < target["expected_date"]:
                target["expected_date"] = r["expected_date"]
    rows = sorted(aggregate.values(), key=lambda r: (r["month"], r["farm_block"], str(r["cycle"])))
    month_bins = {}
    cursor = getdate(f"{start.year}-{start.month:02d}-01")
    while cursor <= end:
        key = _date(cursor)[:7]
        month_bins[key] = dict(month=key, bunches=0, gross_kg=0, packed_kg=0,
                               actual_gross_kg=round(actual_months[key], 2))
        cursor = getdate(add_months(cursor, 1))
    for r in rows:
        m = month_bins[r["month"]]
        for name in ("bunches", "gross_kg", "packed_kg"):
            m[name] += r[name]
    summary = dict(bunches=round(sum(r["bunches"] for r in rows), 2),
                   gross_kg=round(sum(r["gross_kg"] for r in rows), 2),
                   packed_kg=round(sum(r["packed_kg"] for r in rows), 2),
                   blocks=len(blocks),
                   ready_blocks=len({r["farm_block"] for r in rows}),
                   missing_blocks=len({x[0] for x in issue_map}),
                   projected_kg=round(sum(r["gross_kg"] for r in rows if r["projected"]), 2))
    return dict(from_date=_date(start), to_date=_date(end),
                rows=rows, months=list(month_bins.values()), summary=summary,
                issues=sorted(issue_map.values(), key=lambda x:(x["farm_block"],x["message"])),
                actual_readable=actual_readable,
                note="Dự thu tự động là ước tính để lập kế hoạch, không phải sản lượng đã phát hành hoặc được phép cam kết bán.")
