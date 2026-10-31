"""Framework-free rules for công việc ngoài vườn: phiếu giao việc theo lô, how each việc is paid, the caps a report
may not exceed, the ticket states, inspection results, the split of khoán money by buổi and the minimum-wage top-up.

A việc's pay mode comes from the catalogue (Work Type), never from the person giving the work:
  Count   = khoán số lượng (buồng, cây, bao), checked against an independent count (the cap);
  Lot     = khoán lô: the whole lô is paid once, only after an inspection by someone outside the đội passes;
  Daywork = công nhật, paid from the time clock; the ticket only records what was done.
"""
from datetime import date, datetime, timedelta

AREA, TREES, COUNT = "Area", "Trees", "Count"
# Work groups decide which fields a report shows.
BUNCH_GROUP, FIELD_GROUP, PROTECTION = "Bunch", "Field", "Protection"
GROUPS = (BUNCH_GROUP, FIELD_GROUP, PROTECTION)
# Pay modes.
PAY_COUNT, PAY_LOT, PAY_DAYWORK = "Count", "Lot", "Daywork"
PAY_MODES = (PAY_COUNT, PAY_LOT, PAY_DAYWORK)
KHOAN = (PAY_COUNT, PAY_LOT)
# What a report on a ticket is capped by.
CAP_CUT_BUD, CAP_TREES, CAP_AREA, CAP_NONE = "CutBud", "LotTrees", "LotArea", "None"
# Ticket (phiếu giao) states.
OPEN, REPORTED, APPROVED, PASSED, FAILED, LOCKED, CANCELLED = "Open", "Reported", "Approved", "Passed", "Failed", "Locked", "Cancelled"
ROUND = "Round"
# Bunch stages after cắt bắp that carry the ribbon colour and cannot exceed the cắt bắp count of that colour.
COLOUR_STAGES = ("Bag", "Care", "Prop")
CUT_BUD = "Cut Bud"
# Before this day an excess over cắt bắp only warns (bunches cut before the system were never counted).
BUNCH_CAP_FROM = date(2026, 12, 1)
# Default pass marks of an inspection, by work group (bunch care is held tighter).
PASS_MARK = {BUNCH_GROUP: 95, FIELD_GROUP: 90, PROTECTION: 90}
SESSIONS = ("Morning", "Afternoon")
SESSION_HOURS = 4


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


def pay_amount(pay_mode, qty, whole, rate, passed=True):
    """Money of a ticket: counted work is paid for what was reported, a khoán lô once for the whole lô and only when
    its inspection passed; công nhật carries no money here."""
    if pay_mode == PAY_COUNT:
        return round(float(qty or 0) * float(rate or 0))
    if pay_mode == PAY_LOT:
        return round(float(whole or 0) * float(rate or 0)) if passed else 0
    return 0


def split_by_sessions(amount, sessions):
    """Split a ticket's money over the people who worked on it, by buổi. sessions: {employee: count}. Rounded to the
    đồng; the remainder goes to the person with the most buổi so the shares add up to the amount."""
    total = sum(n for n in sessions.values() if n > 0)
    if not total or not amount:
        return {e: 0 for e in sessions}
    shares = {e: int(amount * n // total) if n > 0 else 0 for e, n in sessions.items()}
    rest = int(round(amount)) - sum(shares.values())
    if rest:
        top = max((e for e, n in sessions.items() if n > 0), key=lambda e: (sessions[e], str(e)))
        shares[top] += rest
    return shares


# action -> (states it applies from, state it leads to)
_FLOW = {
    "report": ((OPEN, FAILED), REPORTED),
    "approve": ((REPORTED,), APPROVED),
    "return": ((REPORTED, APPROVED), OPEN),
    "pass": ((APPROVED,), PASSED),
    "fail": ((APPROVED,), FAILED),
    "lock": ((PASSED,), LOCKED),
    "cancel": ((OPEN, REPORTED, FAILED), CANCELLED),
}


def next_state(state, action, pay_mode=None):
    """The state a ticket moves to, or a ValueError. Counted and công nhật tickets need no inspection: approving them
    moves straight to Passed."""
    if action not in _FLOW:
        raise ValueError("Thao tác không hợp lệ.")
    sources, target = _FLOW[action]
    if state not in sources:
        raise ValueError("Phiếu đang ở trạng thái " + str(state) + ", không làm được thao tác này.")
    if action == "approve" and pay_mode != PAY_LOT:
        return PASSED
    return target


def can_report(state):
    return state in (OPEN, FAILED)


def inspection_result(sample_size, passed_count, pass_mark):
    """Score in % of the sample and Pass/Fail against the pass mark."""
    sample = int(sample_size or 0)
    passed = int(passed_count or 0)
    if sample <= 0:
        raise ValueError("Số cây mẫu phải lớn hơn 0.")
    if passed < 0 or passed > sample:
        raise ValueError("Số cây đạt phải từ 0 đến số cây mẫu.")
    score = round(passed * 100.0 / sample, 1)
    return score, ("Pass" if score >= float(pass_mark) else "Fail")


def cap_left(cap_basis, used, lot_area=0, lot_trees=0, cut=0):
    """How much more may be reported on a ticket: the lot's area or trees, or the bunches cut of that colour, minus
    what is already reported. None means no cap."""
    if cap_basis == CAP_AREA:
        whole = float(lot_area or 0)
    elif cap_basis == CAP_TREES:
        whole = float(lot_trees or 0)
    elif cap_basis == CAP_CUT_BUD:
        whole = float(cut or 0)
    else:
        return None
    return round(max(whole - float(used or 0), 0.0), 4)


def cap_blocks(report_day):
    return day(report_day) >= BUNCH_CAP_FROM


def bunch_over_cut(cut, done, rows):
    """Bunch lines after cắt bắp may not add up to more bunches than were cut of that colour in that lô.
    cut: {(block, tag): n}; done: {(block, tag, stage): n} from the other reports;
    rows: this report's lines as dicts with farm_block, bunch_tag, stage, qty. Returns the exceeded keys with totals."""
    totals = dict(done)
    for row in rows:
        if row.get("stage") not in COLOUR_STAGES or not row.get("bunch_tag"):
            continue
        key = (row["farm_block"], row["bunch_tag"], row["stage"])
        totals[key] = totals.get(key, 0) + float(row.get("qty") or 0)
    touched = {(r["farm_block"], r["bunch_tag"], r["stage"]) for r in rows if r.get("stage") in COLOUR_STAGES and r.get("bunch_tag")}
    return {key: (totals[key], float(cut.get(key[:2], 0))) for key in touched if totals[key] > float(cut.get(key[:2], 0))}


def under_norm(qty, workdays, norm_min):
    """True when the recorded output per workday is below the low end of the norm (no output recorded: not judged)."""
    return bool(workdays and norm_min and qty and float(qty) / float(workdays) < float(norm_min))


def minimum_topup(piece_amount, piece_sessions, hourly_minimum):
    """Khoán pay converted to an hourly figure for normal hours may not fall below the regional minimum
    (Nghị định 293/2025 Điều 4): the shortfall over the buổi worked on khoán tickets."""
    floor = int(piece_sessions or 0) * SESSION_HOURS * float(hourly_minimum or 0)
    return round(max(floor - float(piece_amount or 0), 0))


def quarantine_until(posting_date, phi_days):
    """Last day of the pre-harvest interval (thời gian cách ly) after a spray; None when the product has none."""
    days = int(phi_days or 0)
    return day(posting_date) + timedelta(days=days) if days > 0 else None


def display_state(state, due_date, today, reported=False):
    """What the đội sees: the stored state, or Late / Working for an open ticket."""
    if state != OPEN:
        return state
    if due_date and day(due_date) < day(today):
        return "Late"
    return "Working" if reported else "Assigned"


def crew_zones(text):
    return [z.strip().upper() for z in str(text or "").replace(";", ",").replace("+", ",").split(",") if z.strip()]
