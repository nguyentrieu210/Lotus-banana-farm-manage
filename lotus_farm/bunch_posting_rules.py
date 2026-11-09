"""Rules of the daily bunch sheet and its confirmation. Pure: no Frappe, no database."""
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

SUCKER, INJECT, CUT, REJECT, HARVEST = "Sucker Select", "Bud Injection", "Cut Bud", "Reject", "Harvest"
SHEET_TYPES = (INJECT, CUT, REJECT, HARVEST)
BEFORE_CUT, AFTER_CUT = "Before Cut", "After Cut"
# The only stage on a phiếu that writes the ledger; bao, tỉa, chống đổ stay on the phiếu and are capped by it.
STAGE_EVENTS = {SUCKER: SUCKER}
LABELS = {INJECT: "Chích bắp", CUT: "Cắt bắp", REJECT: "Hủy buồng", HARVEST: "Thu hoạch", SUCKER: "Chọn chồi"}


class RowError(Exception):
    """One line of the sheet cannot be stored; the message is shown next to it."""


def event_for_stage(stage):
    return STAGE_EVENTS.get(stage)


def whole_number(value):
    """A positive whole number from what was typed, or None. 12.0 is 12; 12,5 and 12.5 are not bunches."""
    try:
        number = Decimal(str(value).strip().replace(",", "."))
    except (InvalidOperation, ValueError):
        return None
    if not number.is_finite() or number != number.to_integral_value() or number <= 0:
        return None
    return int(number)


def positive_number(value):
    try:
        number = float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None
    return number if 0 < number < float("inf") else None


def row_key(block, day, event_type, tag, reason, team):
    return ":".join(("daily", str(block), str(day), str(event_type), str(tag or ""), str(reason or ""), str(team or "")))


def clean_row(row, ribbon_tag=None):
    """The values to store for one sheet line. Cắt bắp always takes the ribbon of the day, never a typed colour."""
    event_type = row.get("event_type")
    if event_type not in SHEET_TYPES:
        raise RowError("Việc không thuộc bảng nhập nhanh.")
    qty = whole_number(row.get("qty"))
    if qty is None:
        raise RowError("Số buồng phải là số nguyên lớn hơn 0.")
    clean = {"event_type": event_type, "qty": qty, "bunch_tag": None, "reason": None, "reject_stage": None, "weight_kg": 0}
    tag = row.get("bunch_tag") or None
    if event_type == CUT:
        if not ribbon_tag:
            raise RowError("Ngày này chưa có màu dây cắt bắp trong lịch màu dây.")
        clean["bunch_tag"] = ribbon_tag
    elif event_type == REJECT:
        stage, reason = row.get("reject_stage"), row.get("reason")
        if stage not in (BEFORE_CUT, AFTER_CUT):
            raise RowError("Chọn hủy trước hay sau cắt bắp.")
        if not reason:
            raise RowError("Buồng hủy phải có lý do.")
        if stage == AFTER_CUT and not tag:
            raise RowError("Buồng hủy sau cắt bắp phải có màu dây.")
        clean.update(reject_stage=stage, reason=reason, bunch_tag=tag if stage == AFTER_CUT else None)
    elif event_type == HARVEST:
        weight = positive_number(row.get("weight_kg"))
        if not tag:
            raise RowError("Thu hoạch phải có màu dây.")
        if weight is None:
            raise RowError("Thu hoạch phải có khối lượng (kg).")
        clean.update(bunch_tag=tag, weight_kg=weight)
    return clean


def uses_cut(row):
    """Does this ledger line take bunches out of what was cut (thu hoạch, loại sau cắt)?"""
    return row.get("event_type") == HARVEST or (row.get("event_type") == REJECT and row.get("reject_stage") == AFTER_CUT)


def cut_balance(rows):
    """{(lô, màu): (cut, used)} over ledger lines. Lines without a colour do not count."""
    balance = {}
    for r in rows:
        tag = r.get("bunch_tag")
        if not tag or not (r.get("event_type") == CUT or uses_cut(r)):
            continue
        key = (r.get("farm_block"), tag)
        cut, used = balance.get(key, (0, 0))
        balance[key] = (cut + int(r.get("qty") or 0), used) if r.get("event_type") == CUT else (cut, used + int(r.get("qty") or 0))
    return balance


def over_cut(rows):
    """The (lô, màu) where thu hoạch + loại sau cắt exceed cắt bắp: {key: (cut, used)}."""
    return {key: value for key, value in cut_balance(rows).items() if value[1] > value[0]}


def sucker_estimate(trees, area_done, lot_area):
    """Suckers selected, from the hectares done: there is no count in the field. Never more than the trees of the lô."""
    trees, area_done, lot_area = int(trees or 0), float(area_done or 0), float(lot_area or 0)
    if trees <= 0 or area_done <= 0 or lot_area <= 0:
        return 0
    estimate = int((Decimal(trees) * Decimal(str(area_done)) / Decimal(str(lot_area))).quantize(Decimal(1), ROUND_HALF_UP))
    return min(estimate, trees)


def sucker_cycle(current_cycle, bud_work_in_cycle):
    """FR-026: chọn chồi before any chích/cắt of the vụ belongs to it; after that, it is for the next vụ."""
    return int(current_cycle) + 1 if bud_work_in_cycle else int(current_cycle)


def can_confirm(entered_by, user):
    return bool(entered_by) and entered_by != user


LATE_FLOWER_DAYS = 14


def not_reported(assigned, reported):
    """Lô with a phiếu open on the day and no number at all that day: {lô: tổ}. A lô reported by any tổ counts as reported."""
    return {block: team for block, team in assigned if block not in set(reported)}


def anomalies(lots, today):
    """lots: code, trees, flower_date, inject, cut, used. Numbers that cannot be right, and lô old enough to flower with no number."""
    found = []
    for lot in lots:
        trees = int(lot.get("trees") or 0)
        if trees and int(lot.get("inject") or 0) > trees:
            found.append({"block": lot["code"], "kind": "inject", "message": f"Chích bắp lũy kế {lot['inject']} vượt số cây {trees}."})
        if trees and int(lot.get("cut") or 0) > trees:
            found.append({"block": lot["code"], "kind": "cut", "message": f"Cắt bắp lũy kế {lot['cut']} vượt số cây {trees}."})
        if int(lot.get("used") or 0) > int(lot.get("cut") or 0):
            found.append({"block": lot["code"], "kind": "used", "message": f"Thu hoạch và hủy sau cắt {lot['used']} vượt số đã cắt bắp {lot.get('cut') or 0}."})
        flower = lot.get("flower_date")
        if flower and (today - flower).days >= LATE_FLOWER_DAYS and not lot.get("inject") and not lot.get("cut"):
            found.append({"block": lot["code"], "kind": "silent", "message": f"Đã đến tuổi trổ từ {flower.strftime('%d/%m')} mà chưa có số chích hay cắt bắp."})
    return found
