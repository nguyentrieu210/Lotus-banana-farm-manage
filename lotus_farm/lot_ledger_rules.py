"""Rules of the sổ lô and of the tổ's daily report. Pure: no Frappe, no database.

Every job done on a lô is one line of the sổ lô (Lotus Work Entry): việc vườn, phun bón, kiểm tra sâu bệnh, every bunch
stage and thu hoạch. A tổ sends one report a day; the đội trưởng confirms it. Confirmed lines are never edited: a
correction voids the line with a reason and writes a new one. Bunch caps:
  - bao buồng of a colour never exceeds the cắt bắp of that colour in that lô;
  - thu hoạch + hủy sau cắt of a colour never exceed the cắt bắp of that colour in that lô;
  - chích bắp, tỉa, chống đổ in the vụ never exceed the trees of the lô.
A lô sprayed with a product that has a pre-harvest interval cannot be harvested until the day after it ends.
"""
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

SUCKER, INJECT, CUT, BAG, CARE, PROP, REJECT, HARVEST = (
    "Sucker Select", "Bud Injection", "Cut Bud", "Bag", "Care", "Prop", "Reject", "Harvest")
STAGES = (SUCKER, INJECT, CUT, BAG, CARE, PROP, REJECT, HARVEST)
BUNCH_STAGES = (INJECT, CUT, BAG, CARE, PROP, REJECT, HARVEST)  # counted in whole bunches
TREE_CAPPED = (INJECT, CARE, PROP)
BEFORE_CUT, AFTER_CUT = "Before Cut", "After Cut"
BUNCH_GROUP, FIELD_GROUP, PROTECTION = "Bunch", "Field", "Protection"
PAY_COUNT, PAY_LOT, PAY_DAYWORK = "Count", "Lot", "Daywork"
DRAFT, SENT, CONFIRMED, VOIDED, REOPENED = "Draft", "Sent", "Confirmed", "Voided", "Reopened"
DAILY, PHOTO, OPENING, MANUAL = "Daily", "Photo", "Opening Import", "Manual"
MORNING, AFTERNOON = "Morning", "Afternoon"
SEVERITIES = ("Nhẹ", "Vừa", "Nặng")
LABELS = {SUCKER: "Chọn chồi", INJECT: "Chích bắp", CUT: "Cắt bắp", BAG: "Bao buồng", CARE: "Tỉa", PROP: "Chống đổ",
          REJECT: "Hủy buồng", HARVEST: "Thu hoạch"}
MAX_MATERIALS = 6


class LineError(Exception):
    """One line cannot be stored; the message is shown next to it."""


# ---------------------------------------------------------------- numbers

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


def plain_number(value):
    """Zero or more, from what was typed; '' is 0. Raises LineError on anything else."""
    if value in (None, ""):
        return 0.0
    try:
        number = float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        raise LineError("Khối lượng phải là số.")
    if number < 0 or number == float("inf"):
        raise LineError("Khối lượng không được âm.")
    return number


# ---------------------------------------------------------------- one line

def line_key(report, block, work_type, tag=None, reason=None):
    return ":".join(("day", str(report), str(block), str(work_type), str(tag or ""), str(reason or "")))


def clean_materials(raw):
    items = [m for m in (raw or []) if isinstance(m, dict) and m.get("item_code")]
    if len(items) > MAX_MATERIALS:
        raise LineError(f"Tối đa {MAX_MATERIALS} vật tư mỗi dòng.")
    result = []
    for m in items:
        qty = positive_number(m.get("qty"))
        if qty is None:
            raise LineError("Nhập số lượng vật tư lớn hơn 0.")
        result.append({"item_code": str(m["item_code"]), "qty": qty, "dose": str(m.get("dose") or "").strip()[:140],
                       "stock_entry": m.get("stock_entry") or None})
    return result


def clean_people(raw):
    """{employee: {morning, afternoon}} from what the screen sent; people with no buổi are dropped."""
    result = {}
    for p in raw or []:
        if not isinstance(p, dict) or not p.get("employee"):
            continue
        morning, afternoon = 1 if p.get("morning") else 0, 1 if p.get("afternoon") else 0
        if morning or afternoon:
            row = result.setdefault(str(p["employee"]), {"morning": 0, "afternoon": 0})
            row["morning"] |= morning
            row["afternoon"] |= afternoon
    return result


def clean_line(raw, work, ribbon_tag=None):
    """The values to store for one line of a lô. `work` is the catalogue row: stage, group, pay_mode,
    requires_material, records_disease. Cắt bắp always takes the ribbon of the work day, never a typed colour."""
    stage = work.get("stage") or ""
    clean = {"work_type": work.get("name"), "stage": stage, "qty": 0, "area_ha": 0.0, "bunch_tag": None, "reason": None,
             "reject_stage": None, "weight_kg": 0.0, "disease": None, "severity": None, "done": 1 if raw.get("done") else 0,
             "notes": str(raw.get("notes") or "").strip()[:1000], "materials": clean_materials(raw.get("materials"))}
    tag = raw.get("bunch_tag") or None
    if work.get("records_disease"):
        qty = whole_number(raw.get("qty"))
        if not raw.get("disease"):
            raise LineError("Chọn bệnh đã gặp.")
        if raw.get("severity") not in SEVERITIES:
            raise LineError("Chọn mức độ: nhẹ, vừa hay nặng.")
        if qty is None:
            raise LineError("Số cây bị phải là số nguyên lớn hơn 0.")
        clean.update(qty=qty, disease=raw["disease"], severity=raw["severity"])
    elif stage == SUCKER:
        area = positive_number(raw.get("area_ha"))
        if area is None:
            raise LineError("Chọn chồi báo theo số ha đã làm, lớn hơn 0.")
        clean["area_ha"] = area
    elif stage in BUNCH_STAGES:
        qty = whole_number(raw.get("qty"))
        if qty is None:
            raise LineError("Số buồng phải là số nguyên lớn hơn 0.")
        clean["qty"] = qty
        if stage == CUT:
            if not ribbon_tag:
                raise LineError("Ngày này chưa có màu dây cắt bắp trong lịch màu dây.")
            clean["bunch_tag"] = ribbon_tag
        elif stage == BAG:
            if not tag:
                raise LineError("Bao buồng phải chọn màu dây.")
            clean["bunch_tag"] = tag
        elif stage == HARVEST:
            weight = positive_number(raw.get("weight_kg"))
            if not tag:
                raise LineError("Thu hoạch phải chọn màu dây.")
            if weight is None:
                raise LineError("Thu hoạch phải có khối lượng (kg).")
            clean.update(bunch_tag=tag, weight_kg=weight)
        elif stage == REJECT:
            reject_stage, reason = raw.get("reject_stage"), raw.get("reason")
            if reject_stage not in (BEFORE_CUT, AFTER_CUT):
                raise LineError("Chọn hủy trước hay sau cắt bắp.")
            if not reason:
                raise LineError("Buồng hủy phải có lý do.")
            if reject_stage == AFTER_CUT and not tag:
                raise LineError("Buồng hủy sau cắt bắp phải có màu dây.")
            clean.update(reject_stage=reject_stage, reason=reason, bunch_tag=tag if reject_stage == AFTER_CUT else None)
    else:
        qty = plain_number(raw.get("qty"))
        if work.get("pay_mode") == PAY_COUNT and qty <= 0:
            raise LineError("Việc khoán số lượng phải nhập khối lượng lớn hơn 0.")
        if qty <= 0 and not clean["done"]:
            raise LineError("Nhập khối lượng, hoặc đánh dấu đã làm xong cả lô.")
        clean["qty"] = qty
    if work.get("requires_material"):
        if not clean["materials"]:
            raise LineError("Việc này phải ghi vật tư đã dùng: tên, số lượng, liều.")
        if any(not m["dose"] for m in clean["materials"]):
            raise LineError("Ghi liều dùng cho từng vật tư.")
    return clean


# ---------------------------------------------------------------- caps

def _after_cut(row):
    return row.get("stage") == HARVEST or (row.get("stage") == REJECT and row.get("reject_stage") == AFTER_CUT)


def colour_balance(rows):
    """{(lô, màu): {cut, bag, used, left}} over ledger lines. used = thu hoạch + hủy sau cắt; left = still on the plants."""
    balance = {}
    for row in rows:
        tag = row.get("bunch_tag")
        if not tag:
            continue
        stage = row.get("stage")
        if stage not in (CUT, BAG) and not _after_cut(row):
            continue
        slot = balance.setdefault((row.get("farm_block"), tag), {"cut": 0, "bag": 0, "used": 0, "harvested": 0, "rejected": 0})
        qty = int(row.get("qty") or 0)
        if stage == CUT:
            slot["cut"] += qty
        elif stage == BAG:
            slot["bag"] += qty
        else:
            slot["used"] += qty
            slot["harvested" if stage == HARVEST else "rejected"] += qty
    for slot in balance.values():
        slot["left"] = slot["cut"] - slot["used"]
    return balance


def over_cut(rows):
    """The (lô, màu) where bao, or thu hoạch + hủy sau cắt, exceed cắt bắp: {key: balance}."""
    return {key: b for key, b in colour_balance(rows).items() if b["bag"] > b["cut"] or b["used"] > b["cut"]}


def cap_message(block_code, colour, balance):
    if balance["bag"] > balance["cut"]:
        return f"{block_code} màu {colour}: bao buồng {balance['bag']} vượt số đã cắt bắp {balance['cut']}."
    return f"{block_code} màu {colour}: thu hoạch và hủy sau cắt là {balance['used']}, vượt số đã cắt bắp {balance['cut']}."


def overage(balance):
    """How far a colour is beyond its cắt bắp (0 when within)."""
    return max(balance["bag"] - balance["cut"], 0) + max(balance["used"] - balance["cut"], 0)


def line_cap(pay_mode, cap_basis, stage, qty, trees):
    """A khoán-số-lượng line counted per tree (bón phân, phun, hạ cây…) cannot exceed the trees of the lô. Bunch stages
    have their own cumulative caps. Returns the message, or None."""
    if pay_mode != PAY_COUNT or stage or cap_basis != "LotTrees" or not int(trees or 0):
        return None
    if float(qty or 0) > int(trees):
        return f"Số lượng {qty:g} vượt số cây {int(trees)} của lô."
    return None


def over_trees(rows, trees, cycles):
    """{(lô, công đoạn): (total, trees)} where chích bắp, tỉa or chống đổ of the lô's current vụ exceed its trees."""
    totals = {}
    for row in rows:
        block, stage = row.get("farm_block"), row.get("stage")
        if stage not in TREE_CAPPED or int(row.get("cycle_no") or 0) != int(cycles.get(block) or 0):
            continue
        totals[(block, stage)] = totals.get((block, stage), 0) + int(row.get("qty") or 0)
    return {key: (total, int(trees.get(key[0]) or 0)) for key, total in totals.items()
            if int(trees.get(key[0]) or 0) and total > int(trees.get(key[0]) or 0)}


# ---------------------------------------------------------------- quarantine

def quarantine_intervals(lines):
    """[(spray day, last day of the pre-harvest interval)] over confirmed spraying lines:
    [{posting_date, materials: [{phi_days}]}]. A material without an interval holds nothing."""
    result = []
    for line in lines:
        days = max([int(m.get("phi_days") or 0) for m in line.get("materials") or []] or [0])
        if days > 0:
            result.append((line["posting_date"], line["posting_date"] + timedelta(days=days)))
    return result


def quarantine_end(lines):
    """Last day of the pre-harvest interval over confirmed spraying lines, or None."""
    ends = [end for _, end in quarantine_intervals(lines)]
    return max(ends) if ends else None


def harvest_blocked(day, intervals):
    """The (spray day, end) that forbids harvesting on `day`, or None. A harvest is blocked from the spray day to
    the end of its interval, so a spray after the harvest day never blocks a harvest entered late."""
    for start, end in sorted(intervals or [], key=lambda i: i[1], reverse=True):
        if start <= day <= end:
            return (start, end)
    return None


# ---------------------------------------------------------------- buổi công

def _split(total, parts):
    """total split over {key: share}; equal when every share is 0. Exact: the last key takes the rounding rest."""
    keys = list(parts)
    weight = sum(max(float(v or 0), 0.0) for v in parts.values())
    result, used = {}, Decimal(0)
    for i, key in enumerate(keys):
        if i == len(keys) - 1:
            result[key] = float(Decimal(str(total)) - used)
            break
        share = (max(float(parts[key] or 0), 0.0) / weight) if weight else 1 / len(keys)
        value = (Decimal(str(total)) * Decimal(str(share))).quantize(Decimal("0.000001"), ROUND_HALF_UP)
        result[key] = float(value)
        used += value
    return result


def session_weights(lines):
    """{(line key, employee, buổi): weight}. One buổi of one person counts once: shared evenly between the việc they
    had that buổi, and within one việc by the quantity of each lô (evenly when any of them has no quantity: a lô ticked
    "xong" without a number still took part of the buổi)."""
    slots = {}
    for line in lines:
        for employee, flags in (line.get("people") or {}).items():
            for flag, session in (("morning", MORNING), ("afternoon", AFTERNOON)):
                if flags.get(flag):
                    slots.setdefault((employee, session), []).append(line)
    weights = {}
    for (employee, session), held in slots.items():
        works = {}
        for line in held:
            works.setdefault(line.get("work_type"), []).append(line)
        per_work = _split(1, {w: 0 for w in works})
        for work, group in works.items():
            shares = {line["key"]: float(line.get("qty") or 0) for line in group}
            if any(v <= 0 for v in shares.values()):
                shares = {key: 0 for key in shares}
            for key, value in _split(per_work[work], shares).items():
                weights[(key, employee, session)] = value
    return weights


# ---------------------------------------------------------------- report flow and money

_FLOW = {"send": ((DRAFT, REOPENED), SENT), "confirm": ((SENT,), CONFIRMED), "reopen": ((SENT, CONFIRMED), REOPENED)}


def next_report_state(state, action):
    sources, target = _FLOW[action]
    if state not in sources:
        raise ValueError(f"Báo cáo đang ở trạng thái {state}, không {action} được.")
    return target


def can_edit(state):
    return state in (DRAFT, REOPENED)


def can_confirm(entered_by, user):
    return bool(entered_by) and entered_by != user


def line_amount(pay_mode, qty, rate):
    """Khoán số lượng is paid for every confirmed line; khoán lô once per lô after inspection; công nhật not here."""
    return round(float(qty or 0) * float(rate or 0)) if pay_mode == PAY_COUNT else 0


# ---------------------------------------------------------------- chọn chồi, checks

def sucker_estimate(trees, area_done, lot_area):
    """Suckers selected, from the hectares done: there is no count in the field. Never more than the trees of the lô."""
    trees, area_done, lot_area = int(trees or 0), float(area_done or 0), float(lot_area or 0)
    if trees <= 0 or area_done <= 0 or lot_area <= 0:
        return 0
    estimate = int((Decimal(trees) * Decimal(str(area_done)) / Decimal(str(lot_area))).quantize(Decimal(1), ROUND_HALF_UP))
    return min(estimate, trees)


def sucker_cycle(current_cycle, bud_work_in_cycle):
    """Chọn chồi before any chích/cắt of the vụ belongs to it; after that, it is for the next vụ."""
    return int(current_cycle) + 1 if bud_work_in_cycle else int(current_cycle)


LATE_FLOWER_DAYS = 14


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
