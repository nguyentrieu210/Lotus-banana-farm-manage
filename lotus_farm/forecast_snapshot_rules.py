"""Comparing a frozen forecast with what was harvested, and what the harvests say about the parameters. Pure: no Frappe, no database."""
import datetime as dt
import statistics

MIN_SAMPLES = 3
CUT, HARVEST, REJECT, AFTER_CUT = "Cut Bud", "Harvest", "Reject", "After Cut"


def _day(value):
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])


def week_key(value):
    iso = _day(value).isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def week_monday(key):
    year, week = key.split("-W")
    return dt.date.fromisocalendar(int(year), int(week), 1)


def _pct(diff, base):
    return round(diff / base * 100, 1) if base else None


def colour_results(lines, today):
    """Per (lô, màu): what was cut, what came in, and how. `closed`: the colour is finished, its rate can be trusted."""
    groups = {}
    for line in lines:
        tag = line.get("bunch_tag")
        if not tag:
            continue
        g = groups.setdefault((line["farm_block"], tag), {"block": line["farm_block"], "tag": tag, "cut": 0, "rejected": 0, "harvested": 0, "kg": 0.0, "first_cut": None, "last_cut": None, "harvests": []})
        day, qty = _day(line["event_date"]), int(line["qty"])
        if line["event_type"] == CUT:
            g["cut"] += qty
            g["first_cut"] = min(g["first_cut"] or day, day)
            g["last_cut"] = max(g["last_cut"] or day, day)
        elif line["event_type"] == HARVEST:
            g["harvested"] += qty
            g["kg"] += float(line.get("weight_kg") or 0)
            g["harvests"].append((day, qty))
        elif line["event_type"] == REJECT and line.get("reject_stage") == AFTER_CUT:
            g["rejected"] += qty
    results = []
    today = _day(today)
    for g in groups.values():
        if not g["cut"] or not g["harvested"]:
            continue
        days = [((day - g["first_cut"]).days, qty) for day, qty in g["harvests"]]
        results.append(dict({k: g[k] for k in ("block", "tag", "cut", "rejected", "harvested")}, kg=round(g["kg"], 3),
                            rate=round(g["harvested"] / g["cut"], 4), kg_per_bunch=round(g["kg"] / g["harvested"], 3),
                            days=round(sum(d * q for d, q in days) / sum(q for _, q in days), 1), min_days=min(d for d, _ in days), max_days=max(d for d, _ in days),
                            closed=g["harvested"] + g["rejected"] >= g["cut"] or (today - g["last_cut"]).days > 90))
    return results


def compare(forecast, actual, group_by="week"):
    """forecast/actual: rows with week, block, tag, bunches, kg. group_by: week | block | colour | detail (lô and colour)."""
    def key(row):
        if group_by == "block":
            return row["block"]
        if group_by == "colour":
            return row.get("tag") or ""
        if group_by == "detail":
            return (row["block"], row.get("tag") or "")
        return row["week"]

    slots = {}
    for source, name in ((forecast, "forecast"), (actual, "actual")):
        for row in source:
            slot = slots.setdefault(key(row), {"key": key(row), "week": row["week"], "block": row["block"], "block_code": row.get("block_code") or "", "tag": row.get("tag"), "ribbon": row.get("ribbon") or "",
                                               "forecast_bunches": 0, "forecast_kg": 0.0, "actual_bunches": 0, "actual_kg": 0.0})
            slot[name + "_bunches"] += int(row["bunches"])
            slot[name + "_kg"] += float(row["kg"])
            if row.get("block_code"):
                slot["block_code"] = row["block_code"]
            if row.get("ribbon"):
                slot["ribbon"] = row["ribbon"]
    result = []
    for slot in slots.values():
        diff = slot["actual_bunches"] - slot["forecast_bunches"]
        kg_diff = slot["actual_kg"] - slot["forecast_kg"]
        result.append(dict(slot, forecast_kg=round(slot["forecast_kg"], 3), actual_kg=round(slot["actual_kg"], 3), diff_bunches=diff, diff_pct=_pct(diff, slot["forecast_bunches"]),
                           diff_kg=round(kg_diff, 3), diff_kg_pct=_pct(kg_diff, slot["forecast_kg"])))
    return sorted(result, key=lambda r: str(r["key"]))


def suggest(results, current):
    """What the finished colours say. A suggestion only: nothing is applied here. Needs MIN_SAMPLES finished colours."""
    done = [r for r in results if r["closed"]]
    enough = len(done) >= MIN_SAMPLES
    def line(name, label, value, unit=""):
        return {"field": name, "label": label, "current": current.get(name), "suggested": value if enough else None, "unit": unit}

    if not done:
        return {"samples": 0, "needed": MIN_SAMPLES, "enough": False, "lines": []}
    bunches = sum(r["harvested"] for r in done)
    cycle_kg = sum(r["kg"] for r in done) / bunches
    return {"samples": len(done), "needed": MIN_SAMPLES, "enough": enough, "lines": [
        line("cut_to_harvest_days", "Cắt bắp đến thu, trung bình", round(statistics.fmean(r["days"] for r in done)), "ngày"),
        line("cut_to_harvest_min_days", "Cắt bắp đến thu, sớm nhất", min(r["min_days"] for r in done), "ngày"),
        line("cut_to_harvest_max_days", "Cắt bắp đến thu, muộn nhất", max(r["max_days"] for r in done), "ngày"),
        line("harvest_rate", "Tỷ lệ thu trên số đã cắt", round(sum(r["harvested"] for r in done) / sum(r["cut"] for r in done), 4)),
        line("kg_cycle_2", "Kg mỗi buồng", round(cycle_kg, 2), "kg")]}
