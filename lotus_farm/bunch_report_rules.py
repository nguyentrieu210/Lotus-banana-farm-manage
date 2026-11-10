"""The bunch ledger by ribbon colour: what is on the plants (bảng màu dây) and cutting by week (sổ cắt bắp). Pure: no Frappe, no database."""
import datetime as dt

SUCKER, INJECT, CUT, REJECT, HARVEST, AFTER_CUT = "Sucker Select", "Bud Injection", "Cut Bud", "Reject", "Harvest", "After Cut"
BAG, CARE, PROP = "Bag", "Care", "Prop"
EVENTS = (SUCKER, INJECT, CUT, BAG, CARE, PROP, REJECT, HARVEST)
WAITING, DUE, OVERDUE, DONE = "waiting", "due", "overdue", "done"


def _day(value):
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])


def _natural(code):
    return (len(str(code)), str(code))


def _week_key(day):
    iso = day.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def stock(lines, tags, blocks, days_for, today):
    """On the trees per colour of a week: cut - hủy after cut - harvested. Recorded numbers only, no expected loss.

    days_for(block, first cut) -> (earliest, latest) days from cut to harvest."""
    today = _day(today)
    week_end = today + dt.timedelta(days=6 - today.weekday())
    colours = {}
    for line in lines:
        tag = line.get("bunch_tag")
        if not tag or line["farm_block"] not in blocks:
            continue
        lot = colours.setdefault(tag, {}).setdefault(line["farm_block"], {"cut": 0, "rejected": 0, "harvested": 0, "kg": 0.0, "first": None, "last": None})
        qty, day = int(line["qty"]), _day(line["event_date"])
        if line["event_type"] == CUT:
            lot["cut"] += qty
            lot["first"] = min(lot["first"] or day, day)
            lot["last"] = max(lot["last"] or day, day)
        elif line["event_type"] == HARVEST:
            lot["harvested"] += qty
            lot["kg"] += float(line.get("weight_kg") or 0)
        elif line["event_type"] == REJECT and line.get("reject_stage") == AFTER_CUT:
            lot["rejected"] += qty
    cards = []
    for tag, lots in colours.items():
        cut_lots = {block: lot for block, lot in lots.items() if lot["cut"]}
        if not cut_lots:
            continue
        info = tags.get(tag) or {}
        first_block, first = min(((b, l["first"]) for b, l in cut_lots.items()), key=lambda x: x[1])
        last = max(l["last"] for l in cut_lots.values())
        earliest, latest = days_for(first_block, first)
        start, end = first + dt.timedelta(days=earliest), last + dt.timedelta(days=latest)
        rows = sorted(({"block": b, "code": blocks[b]["code"], "zone": blocks[b]["zone"], "cut": l["cut"], "rejected": l["rejected"], "harvested": l["harvested"], "kg": round(l["kg"], 3),
                        "left": max(0, l["cut"] - l["rejected"] - l["harvested"])} for b, l in cut_lots.items()), key=lambda r: _natural(r["code"]))
        left = sum(r["left"] for r in rows)
        status = DONE if not left else OVERDUE if end < today else DUE if start <= week_end else WAITING
        cards.append({"tag": tag, "colour": info.get("label") or "", "code": info.get("code") or "", "week": info.get("week"), "year": info.get("year"), "lan": info.get("half"), "first_cut": str(first), "start": str(start), "end": str(end),
                      "status": status, "cut": sum(r["cut"] for r in rows), "rejected": sum(r["rejected"] for r in rows), "harvested": sum(r["harvested"] for r in rows), "left": left, "lots": rows})
    cards.sort(key=lambda c: (c["first_cut"], c["lan"] or 0))
    return {"cards": cards, "left": sum(c["left"] for c in cards), "due": sum(c["left"] for c in cards if c["status"] == DUE), "overdue": sum(c["left"] for c in cards if c["status"] == OVERDUE)}


def ribbon(cards, bags, quarantine, today):
    """The bảng màu dây: the stock cards with what was bagged per lô and colour, what is still to bag, the age of the
    colour in weeks and the lô under quarantine. bags: {(lô, màu): bao buồng}; quarantine: {lô: last day held}."""
    today = _day(today)
    for card in cards:
        card["age_weeks"] = (today - _day(card["first_cut"])).days // 7
        for lot in card["lots"]:
            lot["bag"] = int(bags.get((lot["block"], card["tag"]), 0))
            lot["bag_left"] = max(lot["cut"] - lot["bag"], 0)
            until = quarantine.get(lot["block"])
            lot["quarantine_until"] = str(until) if until and _day(until) >= today else None
        card["bag"] = sum(lot["bag"] for lot in card["lots"])
    return {"cards": cards, "left": sum(c["left"] for c in cards), "due": sum(c["left"] for c in cards if c["status"] == DUE),
            "overdue": sum(c["left"] for c in cards if c["status"] == OVERDUE)}


def due_rows(cards):
    """Lô and colours to harvest now: colours in or past their harvest window, lô with bunches left, oldest first."""
    rows = [dict(lot, tag=c["tag"], colour=c["colour"], code_colour=c["code"], week=c["week"], lan=c["lan"], start=c["start"], end=c["end"],
                 status=c["status"]) for c in cards if c["status"] in (DUE, OVERDUE) for lot in c["lots"] if lot["left"] > 0]
    return sorted(rows, key=lambda r: (r["start"], _natural(r["code"])))


def cut_weeks(lines, tags, blocks):
    """Cutting by week and lần, from the first week with a cut to the last, weeks without a cut included. A lần comes from the colour's half-week."""
    found = {}
    for line in lines:
        if line["event_type"] != CUT or line["farm_block"] not in blocks:
            continue
        day, info = _day(line["event_date"]), tags.get(line.get("bunch_tag")) or {}
        monday = day - dt.timedelta(days=day.weekday())
        week = found.setdefault(monday, {"lan1": 0, "lan2": 0, "colour": "", "lots": {}})
        lan = "lan2" if str(info.get("half")) == "2" else "lan1"
        week[lan] += int(line["qty"])
        week["colour"] = info.get("label") or week["colour"]
        lot = week["lots"].setdefault(line["farm_block"], {"lan1": 0, "lan2": 0})
        lot[lan] += int(line["qty"])
    if not found:
        return []
    result, monday, last = [], min(found), max(found)
    while monday <= last:
        week = found.get(monday) or {"lan1": 0, "lan2": 0, "colour": "", "lots": {}}
        lots = sorted(({"block": b, "code": blocks[b]["code"], "lan1": v["lan1"], "lan2": v["lan2"], "total": v["lan1"] + v["lan2"]} for b, v in week["lots"].items()), key=lambda r: _natural(r["code"]))
        result.append({"week": _week_key(monday), "number": monday.isocalendar()[1], "start": str(monday), "end": str(monday + dt.timedelta(days=6)), "colour": week["colour"],
                       "lan1": week["lan1"], "lan2": week["lan2"], "total": week["lan1"] + week["lan2"], "lots": lots})
        monday += dt.timedelta(weeks=1)
    return result
