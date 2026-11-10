"""The daily reports of the bunch ledger: what is on the trees by ribbon colour, cutting by week, and the work of a day. Pure: no Frappe, no database."""
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


def _blank_totals():
    return {event: {"qty": 0, "kg": 0.0, "area": 0.0} for event in EVENTS}


def day_report(lines, blocks, team_names, labels, reason_names):
    """The work reported in a period, per tổ. Only work of a tổ: the opening book has no day's work behind it."""
    teams, totals, rows = {}, _blank_totals(), []
    draft = 0
    for line in lines:
        team = line.get("work_team")
        if not team or line["farm_block"] not in blocks or line["event_type"] not in EVENTS:
            continue
        qty, kg, area = int(round(float(line["qty"]))), float(line.get("weight_kg") or 0), float(line.get("area_ha") or 0)
        slot = teams.setdefault(team, {"team": team, "name": team_names.get(team, team), "totals": _blank_totals(), "draft": 0, "rows": []})
        for bucket in (totals, slot["totals"]):
            bucket[line["event_type"]]["qty"] += qty
            bucket[line["event_type"]]["kg"] += kg
            bucket[line["event_type"]]["area"] += area
        is_draft = line.get("state") == "Draft"
        draft += is_draft
        slot["draft"] += is_draft
        row = {"name": line.get("name"), "date": str(line["event_date"]), "team": team, "team_name": slot["name"], "block": line["farm_block"], "block_code": blocks[line["farm_block"]]["code"], "zone": blocks[line["farm_block"]]["zone"],
               "event_type": line["event_type"], "qty": qty, "kg": kg, "area": area, "ribbon": labels.get(line.get("bunch_tag"), ""), "reason": reason_names.get(line.get("reason"), ""), "state": line.get("state")}
        slot["rows"].append(row)
        rows.append(row)
    order = lambda r: (r["date"], _natural(r["block_code"]), EVENTS.index(r["event_type"]))
    rows.sort(key=order)
    for slot in teams.values():
        slot["rows"].sort(key=order)
    return {"totals": totals, "teams": sorted(teams.values(), key=lambda t: t["name"]), "rows": rows, "draft": draft}


def _monday(day):
    return day - dt.timedelta(days=day.weekday())


def _tag_fields(tag, info):
    return {"tag": tag, "colour": info.get("label") or "", "week": info.get("week"), "year": info.get("year"), "lan": info.get("half")}


def progress(lines, entries, tags, blocks):
    """How far the care of each cut colour has come. lines: ledger of the colours chosen; entries: bao, tỉa, chống đổ from the phiếu."""
    colours = {}

    def lot(tag, block):
        return colours.setdefault(tag, {}).setdefault(block, {"cut": 0, "Bag": 0, "Care": 0, "Prop": 0, "rejected": 0, "harvested": 0, "first": None})

    for line in lines:
        tag, block = line.get("bunch_tag"), line["farm_block"]
        if not tag or block not in blocks:
            continue
        slot, qty = lot(tag, block), int(line["qty"])
        if line["event_type"] == CUT:
            slot["cut"] += qty
            day = _day(line["event_date"])
            slot["first"] = min(slot["first"] or day, day)
        elif line["event_type"] == HARVEST:
            slot["harvested"] += qty
        elif line["event_type"] == REJECT and line.get("reject_stage") == AFTER_CUT:
            slot["rejected"] += qty
    for entry in entries:
        tag, block = entry.get("bunch_tag"), entry["farm_block"]
        if tag in colours and block in colours[tag]:
            colours[tag][block][entry["event_type"]] += int(round(float(entry["qty"])))
    cards = []
    for tag, lots in colours.items():
        rows = sorted(({"block": b, "code": blocks[b]["code"], "cut": l["cut"], "bag": l["Bag"], "care": l["Care"], "prop": l["Prop"], "rejected": l["rejected"], "harvested": l["harvested"],
                        "left": max(0, l["cut"] - l["rejected"] - l["harvested"])} for b, l in lots.items() if l["cut"]), key=lambda r: _natural(r["code"]))
        if not rows:
            continue
        first = min(lots[r["block"]]["first"] for r in rows)
        cards.append(dict(_tag_fields(tag, tags.get(tag) or {}), first_cut=str(first), lots=rows, **{name: sum(r[name] for r in rows) for name in ("cut", "bag", "care", "prop", "rejected", "harvested", "left")}))
    cards.sort(key=lambda c: (c["first_cut"], c["lan"] or 0))
    return cards


def injection(lines, waiting, blocks):
    """Chích bắp by week, and what still waits to be cut. Past its cutting day, a batch is late."""
    weeks, total = {}, 0
    for line in lines:
        if line["event_type"] != INJECT or line["farm_block"] not in blocks:
            continue
        monday, qty = _monday(_day(line["event_date"])), int(line["qty"])
        slot = weeks.setdefault(monday, {"injected": 0, "lots": {}})
        slot["injected"] += qty
        slot["lots"][line["farm_block"]] = slot["lots"].get(line["farm_block"], 0) + qty
        total += qty
    rows = []
    if weeks:
        monday, last = min(weeks), max(weeks)
        while monday <= last:
            slot = weeks.get(monday) or {"injected": 0, "lots": {}}
            rows.append({"week": _week_key(monday), "number": monday.isocalendar()[1], "start": str(monday), "end": str(monday + dt.timedelta(days=6)), "injected": slot["injected"],
                         "lots": sorted(({"block": b, "code": blocks[b]["code"], "qty": q} for b, q in slot["lots"].items()), key=lambda r: _natural(r["code"]))})
            monday += dt.timedelta(weeks=1)
    late = sorted(({"block": w["block"], "code": blocks[w["block"]]["code"], "date": w["date"], "qty": w["left"], "late_days": w["late_days"]} for w in waiting if w["late_days"] and w["block"] in blocks), key=lambda r: -r["late_days"])
    return {"weeks": rows, "injected": total, "waiting": sum(w["left"] for w in waiting if w["block"] in blocks), "late": late, "late_total": sum(r["qty"] for r in late)}


def rejects(lines, cut_total, blocks, tags, reason_names):
    """Hủy buồng by reason, worst first. The rate compares hủy after cutting with what was cut."""
    reasons, total, before, after = {}, 0, 0, 0
    for line in lines:
        if line["event_type"] != REJECT or line["farm_block"] not in blocks:
            continue
        qty = int(line["qty"])
        total += qty
        is_after = line.get("reject_stage") == AFTER_CUT
        after += qty if is_after else 0
        before += 0 if is_after else qty
        slot = reasons.setdefault(line.get("reason"), {"reason": reason_names.get(line.get("reason"), line.get("reason") or ""), "qty": 0, "lots": {}, "rows": []})
        slot["qty"] += qty
        slot["lots"][line["farm_block"]] = slot["lots"].get(line["farm_block"], 0) + qty
        slot["rows"].append({"name": line.get("name"), "date": str(line["event_date"]), "code": blocks[line["farm_block"]]["code"], "qty": qty, "after": is_after, "colour": (tags.get(line.get("bunch_tag")) or {}).get("label") or ""})
    cards = []
    for slot in reasons.values():
        slot["rows"].sort(key=lambda r: (r["date"], _natural(r["code"])))
        worst = sorted(slot["lots"].items(), key=lambda kv: -kv[1])
        cards.append(dict(slot, lots=len(worst), worst=[{"code": blocks[b]["code"], "qty": q} for b, q in worst[:3]]))
    cards.sort(key=lambda c: -c["qty"])
    return {"total": total, "before": before, "after": after, "rate": round(after / cut_total * 100, 1) if cut_total else None, "cards": cards}


def harvest(lines, first_cuts, tags, blocks):
    """Thu hoạch per colour: bunches, kilograms, and how many days really passed since cắt bắp. first_cuts: {(lô, màu): first cut day}."""
    colours = {}
    for line in lines:
        tag, block = line.get("bunch_tag"), line["farm_block"]
        if line["event_type"] != HARVEST or block not in blocks or not tag:
            continue
        lot = colours.setdefault(tag, {}).setdefault(block, {"qty": 0, "kg": 0.0, "days": []})
        qty = int(line["qty"])
        lot["qty"] += qty
        lot["kg"] += float(line.get("weight_kg") or 0)
        first = first_cuts.get((block, tag))
        if first:
            lot["days"].append(((_day(line["event_date"]) - _day(first)).days, qty))
    cards, total_qty, total_kg = [], 0, 0.0
    for tag, lots in colours.items():
        days = [pair for lot in lots.values() for pair in lot["days"]]
        qty, kg = sum(l["qty"] for l in lots.values()), sum(l["kg"] for l in lots.values())
        total_qty += qty
        total_kg += kg
        rows = sorted(({"block": b, "code": blocks[b]["code"], "qty": l["qty"], "kg": round(l["kg"], 3), "kg_per": round(l["kg"] / l["qty"], 2) if l["qty"] else None} for b, l in lots.items()), key=lambda r: _natural(r["code"]))
        cards.append(dict(_tag_fields(tag, tags.get(tag) or {}), qty=qty, kg=round(kg, 3), kg_per=round(kg / qty, 2) if qty else None, days=round(sum(d * q for d, q in days) / sum(q for _, q in days), 1) if days else None,
                          min_days=min((d for d, _ in days), default=None), max_days=max((d for d, _ in days), default=None), lots=rows))
    cards.sort(key=lambda c: ((c["year"] or 0), (c["week"] or 0), (c["lan"] or 0)))
    return {"qty": total_qty, "kg": round(total_kg, 3), "kg_per": round(total_kg / total_qty, 2) if total_qty else None, "cards": cards}


STAGE_KEYS = {INJECT: "inject", CUT: "cut", BAG: "bag", CARE: "care", PROP: "prop", REJECT: "reject", HARVEST: "harvest"}


def dashboard(lines, entries, blocks):
    """Every stage by week and by lô, for the charts. Weeks with nothing stay on the calendar."""
    blank = lambda: dict({key: 0 for key in STAGE_KEYS.values()}, kg=0.0)
    weeks, totals = {}, blank()
    for row in list(lines) + list(entries):
        key, block = STAGE_KEYS.get(row["event_type"]), row["farm_block"]
        if not key or block not in blocks:
            continue
        qty, kg = int(round(float(row["qty"]))), float(row.get("weight_kg") or 0)
        for slot in (weeks.setdefault(_monday(_day(row["event_date"])), blank()), totals):
            slot[key] += qty
            slot["kg"] += kg
    rows = []
    if weeks:
        monday, last = min(weeks), max(weeks)
        while monday <= last:
            rows.append(dict(weeks.get(monday) or blank(), week=_week_key(monday), number=monday.isocalendar()[1], start=str(monday)))
            monday += dt.timedelta(weeks=1)
    return {"weeks": rows, "totals": totals}


def cube(records):
    """Flat rows for the screen to pivot: records are (stage, fact, qty, kg) and rows that differ only in day or line are added together."""
    slots = {}
    for stage, fact, qty, kg in records:
        key = (fact.get("week", ""), fact.get("month", ""), fact.get("zone", ""), fact.get("block", ""), fact.get("team", ""), fact.get("colour", ""), fact.get("lan", ""), fact.get("reason", ""), stage)
        slot = slots.setdefault(key, [0, 0.0])
        slot[0] += qty
        slot[1] += kg
    return [dict(zip(("w", "m", "z", "b", "t", "c", "l", "r", "s"), key), q=value[0], k=round(value[1], 3)) for key, value in slots.items()]
