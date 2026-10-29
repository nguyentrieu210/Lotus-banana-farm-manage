"""Framework-free rules for the đội daily report (báo cáo ngày): prices by date, whole-lot quantities, money,
the "chưa đạt ngày công" flag and the confirmation deadline."""
from datetime import date, datetime, time, timedelta

PIECE, DAYWORK = "Piece", "Daywork"
BLOCK, BLOCKS, ZONE = "Block", "Blocks", "Zone"
AREA, TREES, COUNT = "Area", "Trees", "Count"
# The đội trưởng confirms a day's report before this hour of the next day.
CONFIRM_HOUR = 10


def day(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def number(value, label, maximum=1_000_000_000):
    if value is None or value == "":
        return 0.0
    if isinstance(value, bool):
        raise ValueError(label + ": cần nhập số.")
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError(label + ": cần nhập số.")
    if result != result or result < 0 or result > maximum:
        raise ValueError(f"{label}: số không âm, tối đa {maximum:,.0f}.".replace(",", "."))
    return result


def rate_for(rates, work_type, on):
    """The price row in force for a work type on a day (latest valid_from wins), or None."""
    on = day(on)
    found = None
    for row in rates:
        if row.get("work_type") != work_type or day(row["valid_from"]) > on:
            continue
        if row.get("valid_to") and day(row["valid_to"]) < on:
            continue
        if not found or day(row["valid_from"]) > day(found["valid_from"]):
            found = row
    return found


def whole_lot_qty(basis, area_ha, trees):
    """Quantity of a whole lot for work priced per ha or per tree; counted work has no default."""
    if basis == AREA:
        return round(float(area_ha or 0), 4)
    if basis == TREES:
        return float(int(trees or 0))
    return None


def amount(pay_kind, qty, rate):
    return round(float(qty or 0) * float(rate or 0)) if pay_kind == PIECE else 0


def under_norm(qty, workdays, norm_min):
    """True when the recorded output per workday is below the low end of the norm (no output recorded: not judged)."""
    return bool(workdays and norm_min and qty and float(qty) / float(workdays) < float(norm_min))


def deadline(report_day):
    return datetime.combine(day(report_day) + timedelta(days=1), time(CONFIRM_HOUR))


def overdue(report_day, now, state):
    return state != "Confirmed" and now > deadline(report_day)


def check_line(line, prefix=""):
    """Shape rules that do not need the database. Returns the cleaned numbers."""
    pay = line.get("pay_kind")
    if pay not in (PIECE, DAYWORK):
        raise ValueError(prefix + "Chọn công nhật (CN) hoặc công khoán (CK).")
    location = line.get("location") or BLOCK
    if location not in (BLOCK, BLOCKS, ZONE):
        raise ValueError(prefix + "Vị trí không hợp lệ.")
    if pay == PIECE and location != BLOCK:
        raise ValueError(prefix + "Công khoán ghi từng lô, mỗi lô một dòng.")
    if location == BLOCK and not line.get("farm_block"):
        raise ValueError(prefix + "Chọn lô.")
    if location == BLOCKS and len([b for b in str(line.get("blocks") or "").split(",") if b.strip()]) < 2:
        raise ValueError(prefix + "Chọn ít nhất hai lô, hoặc ghi một lô.")
    if location == ZONE and not line.get("zone"):
        raise ValueError(prefix + "Chọn khu.")
    am = number(line.get("workdays_am"), prefix + "Công sáng", 1000)
    pm = number(line.get("workdays_pm"), prefix + "Công chiều", 1000)
    qty = number(line.get("qty"), prefix + "Khối lượng")
    if not am and not pm and not qty:
        raise ValueError(prefix + "Nhập số công hoặc khối lượng.")
    return dict(workdays_am=am, workdays_pm=pm, workdays=round(am + pm, 4), qty=qty, location=location)


def over_whole_lot(lines):
    """Piece lines priced per ha or per tree: in one day the same work on the same lot cannot add up to more than the
    whole lot (two tổ may split it). Returns (work_type, farm_block, total, whole) for the first excess, else None."""
    totals = {}
    for line in lines:
        if line.get("pay_kind") != PIECE or line.get("basis") not in (AREA, TREES) or not line.get("farm_block"):
            continue
        key = (line["work_type"], line["farm_block"])
        whole = line["lot_area_ha"] if line["basis"] == AREA else line["lot_trees"]
        total, _ = totals.get(key, (0.0, whole))
        totals[key] = (total + float(line.get("qty") or 0), whole)
    for (work, block), (total, whole) in totals.items():
        if whole and total > float(whole) * 1.0001:
            return work, block, round(total, 4), whole
    return None


def crew_zones(text):
    return [z.strip().upper() for z in str(text or "").replace(";", ",").replace("+", ",").split(",") if z.strip()]
