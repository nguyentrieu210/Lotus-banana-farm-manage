"""Báo cáo công việc: garden care, plant protection and the packhouse, summed up for reading. Pure: no Frappe, no database."""
import datetime as dt


def _day(value):
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])


def _natural(code):
    return (len(str(code)), str(code))


def workdays(morning, afternoon):
    """Two buổi make one công."""
    return (int(morning or 0) + int(afternoon or 0)) / 2


def by_work(entries, materials, works, blocks, teams, items):
    """One card per việc over a period, with its lines. entries: Lotus Work Entry rows; materials: {entry: [rows]}; works: {name: {name, uom}}."""
    cards, lots, days, used = {}, set(), 0.0, {}
    count = 0
    for e in entries:
        block = blocks.get(e["farm_block"])
        info = works.get(e["work_type"])
        if not block or not info:
            continue
        count += 1
        lots.add(e["farm_block"])
        card = cards.setdefault(e["work_type"], {"work": e["work_type"], "name": info["name"], "uom": info.get("uom") or "", "qty": 0.0, "workdays": 0.0, "lots": set(), "materials": {}, "rows": []})
        qty, labour = float(e.get("qty") or 0), workdays(e.get("morning_people"), e.get("afternoon_people"))
        card["qty"] += qty
        card["workdays"] += labour
        card["lots"].add(e["farm_block"])
        days += labour
        lines = []
        for m in materials.get(e["name"], []):
            name = items.get(m["item_code"], m["item_code"])
            amount = float(m.get("qty") or 0)
            slot = card["materials"].setdefault(m["item_code"], {"item": m["item_code"], "name": name, "qty": 0.0, "uom": m.get("uom") or ""})
            slot["qty"] += amount
            total = used.setdefault(m["item_code"], {"item": m["item_code"], "name": name, "qty": 0.0, "uom": m.get("uom") or ""})
            total["qty"] += amount
            lines.append({"name": name, "qty": amount, "uom": m.get("uom") or "", "dose": m.get("dose") or "", "phi_days": int(m.get("phi_days") or 0)})
        card["rows"].append({"name": e["name"], "date": str(e["posting_date"]), "block": e["farm_block"], "block_code": block["code"], "zone": block["zone"], "team_name": teams.get(e.get("work_team"), e.get("work_team") or ""),
                             "work_name": info["name"], "uom": info.get("uom") or "", "qty": qty, "workdays": labour, "done": bool(e.get("done")), "notes": e.get("notes") or "", "materials": lines})
    result = []
    for card in cards.values():
        card["rows"].sort(key=lambda r: (r["date"], _natural(r["block_code"])))
        result.append(dict(card, lots=len(card["lots"]), materials=sorted(card["materials"].values(), key=lambda m: m["name"])))
    result.sort(key=lambda c: c["name"])
    return {"cards": result, "entries": count, "lots": len(lots), "workdays": days, "materials": sorted(used.values(), key=lambda m: m["name"])}


def quarantine(rows, blocks, today):
    """Lô that cannot be harvested yet because of a spray. Latest release first is no use: soonest to reopen comes last."""
    today = _day(today)
    held = []
    for name, until in rows:
        if name in blocks and until and _day(until) >= today:
            held.append({"block": name, "code": blocks[name]["code"], "zone": blocks[name]["zone"], "until": str(_day(until)), "days": (_day(until) - today).days})
    return sorted(held, key=lambda r: (-r["days"], _natural(r["code"])))


def disease_summary(rows, blocks):
    """Sâu bệnh per bệnh over a period, each with its lines."""
    found = {}
    for r in rows:
        block = blocks.get(r["farm_block"])
        if not block:
            continue
        slot = found.setdefault(r["disease"], {"disease": r["disease"], "plants": 0, "lots": set(), "rows": []})
        slot["plants"] += int(r.get("affected_plants") or 0)
        slot["lots"].add(r["farm_block"])
        slot["rows"].append({"name": r["name"], "date": str(r["posting_date"]), "block_code": block["code"], "plants": int(r.get("affected_plants") or 0), "severity": r.get("severity") or "", "action": r.get("action_taken") or ""})
    result = []
    for slot in found.values():
        slot["rows"].sort(key=lambda x: (x["date"], _natural(x["block_code"])))
        result.append(dict(slot, lots=len(slot["lots"])))
    return sorted(result, key=lambda s: -s["plants"])


FIGURES = ("input_kg", "finished_kg", "secondary_kg", "loss_kg", "cartons")


def packhouse(shifts):
    """Ca đóng gói per day. Packout is worked out from the kilograms, not averaged from the shifts."""
    days, total = {}, {name: 0.0 for name in FIGURES}
    for s in shifts:
        day = str(s["posting_date"])
        slot = days.setdefault(day, dict({name: 0.0 for name in FIGURES}, date=day, shifts=[]))
        for name in FIGURES:
            amount = float(s.get(name) or 0)
            slot[name] += amount
            total[name] += amount
        slot["shifts"].append({"name": s["name"], "code": s.get("shift_code") or "", "labor": float(s.get("labor") or 0), **{name: float(s.get(name) or 0) for name in FIGURES}})
    percent = lambda r: round(r["finished_kg"] / r["input_kg"] * 100, 2) if r["input_kg"] else None
    return {"days": [dict(days[k], packout=percent(days[k])) for k in sorted(days, reverse=True)], "totals": dict(total, packout=percent(total), shifts=len(shifts))}
