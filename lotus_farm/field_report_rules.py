"""Framework-free rules for the đội daily report (báo cáo ngày): prices by date, whole-lot quantities, money,
the "chưa đạt ngày công" flag, the confirmation deadline, phiếu giao việc states and the ribbon (màu dây) cap."""
from datetime import date, datetime, time, timedelta

PIECE, DAYWORK = "Piece", "Daywork"
BLOCK, BLOCKS, ZONE = "Block", "Blocks", "Zone"
AREA, TREES, COUNT = "Area", "Trees", "Count"
# The đội trưởng confirms a day's report before this hour of the next day.
CONFIRM_HOUR = 10
# Phiếu giao: Round = one round of việc vườn on one lô; Bunch = a standing chăm buồng assignment of a lô to a tổ.
ROUND, BUNCH = "Round", "Bunch"
OPEN, DONE, CANCELLED, ENDED = "Open", "Done", "Cancelled", "Ended"
# Bunch stages after cắt bắp that carry the ribbon colour and cannot exceed the cắt bắp count of that colour.
COLOUR_STAGES = ("Bag", "Care", "Prop")
CUT_BUD = "Cut Bud"
# Before this day an excess over cắt bắp only warns (old bunches were never counted); from it the save is refused.
BUNCH_CAP_FROM = date(2026, 12, 1)


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


def round_amount(basis, done, qty, whole, rate):
    """Money of one report line of a phiếu giao. Work priced per ha or per tree is paid once, for the whole lot, on the
    day it is ticked Xong; the days before only record progress. Counted work (bao, bao phân…) is paid as reported."""
    if basis in (AREA, TREES):
        return round(float(whole or 0) * float(rate or 0)) if done else 0
    return round(float(qty or 0) * float(rate or 0))


def paid_qty(basis, done, qty, whole):
    if basis in (AREA, TREES):
        return float(whole or 0) if done else 0.0
    return float(qty or 0)


def display_state(state, due_date, today, reported=False, reported_done=False):
    """What the đội sees for a phiếu: Assigned, Working, Reported (tổ báo xong, chờ xác nhận), Late, Done, Cancelled, Ended."""
    if state in (DONE, CANCELLED, ENDED):
        return state
    if reported_done:
        return "Reported"
    if due_date and day(due_date) < day(today):
        return "Late"
    return "Working" if reported else "Assigned"


def bunch_over_cut(cut, done, rows):
    """Bunch lines after cắt bắp may not add up to more bunches than were cut of that colour in that lô.
    cut: {(block, tag): n} from every report; done: {(block, tag, stage): n} from the other reports;
    rows: this report's lines as dicts with farm_block, bunch_tag, stage, qty. Returns the exceeded keys with totals."""
    totals = dict(done)
    for row in rows:
        if row.get("stage") not in COLOUR_STAGES or not row.get("bunch_tag"):
            continue
        key = (row["farm_block"], row["bunch_tag"], row["stage"])
        totals[key] = totals.get(key, 0) + float(row.get("qty") or 0)
    touched = {(r["farm_block"], r["bunch_tag"], r["stage"]) for r in rows if r.get("stage") in COLOUR_STAGES and r.get("bunch_tag")}
    return {key: (totals[key], float(cut.get(key[:2], 0))) for key in touched if totals[key] > float(cut.get(key[:2], 0))}


def cap_blocks(report_day):
    return day(report_day) >= BUNCH_CAP_FROM


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


def crew_zones(text):
    return [z.strip().upper() for z in str(text or "").replace(";", ",").replace("+", ",").split(",") if z.strip()]
