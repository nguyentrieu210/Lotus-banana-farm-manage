"""The forecast by week, month, lô and khu, from the cohorts of bunch_flow_rules. Pure: no Frappe, no database."""
import datetime as dt

from lotus_farm.block_forecast_engine import date as to_date
from lotus_farm.block_forecast_engine import months_after, weight_kg

LAYERS = ("cut", "inject", "sucker", "tree")
CONFIDENCE = {"cut": "high", "inject": "medium", "sucker": "low", "tree": "low"}
WEEKS, MONTHS = 13, 12


def monday(day):
    return day - dt.timedelta(days=day.weekday())


def week_key(day):
    iso = day.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def _blank():
    return {"bunches": 0, "kg": 0.0, "cartons": 0.0, "containers": 0.0, "layers": {name: 0 for name in LAYERS},
            "layer_kg": {name: 0.0 for name in LAYERS}, "layer_cartons": {name: 0.0 for name in LAYERS}, "layer_containers": {name: 0.0 for name in LAYERS}}


def _add(slot, layer, bunches, kg, cartons, containers):
    slot["bunches"] += bunches
    slot["kg"] += kg
    slot["cartons"] += cartons
    slot["containers"] += containers
    slot["layers"][layer] += bunches
    slot["layer_kg"][layer] += kg
    slot["layer_cartons"][layer] += cartons
    slot["layer_containers"][layer] += containers


def _rounded(slot):
    def each(values, digits):
        return {k: round(v, digits) for k, v in values.items()}
    return dict(slot, kg=round(slot["kg"], 3), cartons=round(slot["cartons"], 3), containers=round(slot["containers"], 3), layer_kg=each(slot["layer_kg"], 3),
                layer_cartons=each(slot["layer_cartons"], 3), layer_containers=each(slot["layer_containers"], 3))


def _spread_warnings(cohorts, blocks, labels):
    warnings = []
    late = {"inject": {}, "sucker": {}, "tree": {}}
    for c in cohorts:
        if not c["overdue"]:
            continue
        code = (blocks.get(c["block"]) or {"code": c["block"]})["code"]
        if c["layer"] == "cut":
            warnings.append(f"{code} màu {labels.get(c['tag'], c['tag'])}: {c['bunches']} buồng đã qua {c['config']['cut_to_harvest_max_days']} ngày mà chưa ghi thu hoạch.")
        else:
            late[c["layer"]][code] = late[c["layer"]].get(code, 0) + c["bunches"]
    for layer, text in (("inject", "đã chích quá số ngày đến cắt bắp mà chưa ghi cắt"), ("sucker", "đã qua thời điểm thu theo ngày chọn chồi"),
                        ("tree", "theo số cây đã qua thời điểm dự kiến mà chưa có số thực tế, đã chuyển sang các tuần tới")):
        if late[layer]:
            warnings.append(f"{len(late[layer])} lô ({', '.join(sorted(late[layer]))}): {sum(late[layer].values())} buồng {text}.")
    return warnings


def summarize(cohorts, blocks, labels, today, horizon=WEEKS, months=MONTHS):
    """blocks: {name: {code, zone}}; labels: {tag: colour}. Weeks and months with nothing still appear, so the calendar has no holes.
    Weeks, lô and khu cover the weeks shown; months run further, for the long view."""
    today = to_date(today)
    first = monday(today)
    last = first + dt.timedelta(weeks=horizon) - dt.timedelta(days=1)
    month_end = months_after(today.replace(day=1), months) - dt.timedelta(days=1)
    weeks = {}
    for i in range(horizon):
        start = first + dt.timedelta(weeks=i)
        weeks[week_key(start)] = dict(_blank(), week=week_key(start), number=start.isocalendar()[1], start=str(start), end=str(start + dt.timedelta(days=6)))
    by_month = {str(months_after(today.replace(day=1), i))[:7]: dict(_blank(), month=str(months_after(today.replace(day=1), i))[:7]) for i in range(months)}
    rows, by_block, by_zone, total = {}, {}, {}, _blank()
    zone_starts, block_starts = {}, {}
    later = 0
    for c in cohorts:
        info = blocks.get(c["block"]) or {"code": c["block"], "zone": ""}
        config, layer = c["config"], c["layer"]
        if c["days"]:
            first_day = str(c["days"][0][0])
            zone_starts[info["zone"]] = min(zone_starts.get(info["zone"], first_day), first_day)
            lot = block_starts.setdefault(c["block"], {"code": info["code"], "zone": info["zone"], "first": first_day})
            lot["first"] = min(lot["first"], first_day)
        for day, bunches in c["days"]:
            kg = bunches * weight_kg(c["cycle"], config) * config["pack_rate"]
            cartons = kg / config["kg_per_carton"]
            amounts = (bunches, kg, cartons, cartons / config["cartons_per_container"])
            if day <= month_end:
                _add(by_month[str(day)[:7]], layer, *amounts)
            if day > last:
                if layer in ("cut", "inject"):
                    later += bunches
                continue
            key = week_key(day)
            _add(weeks[key], layer, *amounts)
            _add(total, layer, *amounts)
            _add(by_block.setdefault(c["block"], dict(_blank(), block=c["block"], code=info["code"], zone=info["zone"])), layer, *amounts)
            _add(by_zone.setdefault(info["zone"], dict(_blank(), zone=info["zone"])), layer, *amounts)
            row = rows.setdefault((key, c["block"], c["tag"], c["cycle"], layer), dict(
                _blank(), week=key, block=c["block"], block_code=info["code"], zone=info["zone"], tag=c["tag"], ribbon=labels.get(c["tag"], ""),
                cycle=c["cycle"], layer=layer, confidence=CONFIDENCE[layer], overdue=False))
            row["overdue"] = row["overdue"] or c["overdue"]
            _add(row, layer, *amounts)
    warnings = _spread_warnings(cohorts, blocks, labels)
    if later:
        warnings.append(f"{later} buồng đã cắt hoặc đã chích sẽ thu sau {horizon} tuần tới, chưa tính trong các thẻ tuần.")
    order = {name: i for i, name in enumerate(LAYERS)}
    return {"weeks": [_rounded(w) for w in weeks.values()],
            "rows": sorted((_rounded(r) for r in rows.values()), key=lambda r: (r["week"], r["zone"], len(str(r["block_code"])), str(r["block_code"]), order[r["layer"]], r["ribbon"])),
            "months": [_rounded(by_month[k]) for k in sorted(by_month)], "blocks": [_rounded(b) for b in by_block.values()],
            "zones": [_rounded(by_zone[k]) for k in sorted(by_zone)], "totals": _rounded(total), "warnings": warnings, "later": later, "horizon": horizon,
            "zone_starts": zone_starts, "block_starts": block_starts}


PACE_ALERT = 2


def cut_pace(cohorts, lines, today, back=4, ahead=9):
    """Bunches really cut each week against those the estimates need, cut_to_harvest_days before each is due to come in.
    Cutting comes about nine weeks before harvest, so this shows an estimate is off long before the harvest does."""
    today = to_date(today)
    current = monday(today)
    weeks = {}
    for i in range(-back, ahead + 1):
        start = current + dt.timedelta(weeks=i)
        weeks[week_key(start)] = {"week": week_key(start), "number": start.isocalendar()[1], "start": str(start), "actual": 0, "needed": None if i < 0 else 0.0, "future": i >= 0}
    for line in lines:
        if line.get("event_type") == "Cut Bud":
            slot = weeks.get(week_key(to_date(line["event_date"])))
            if slot:
                slot["actual"] += int(line["qty"])
    for c in cohorts:
        if c["layer"] == "cut":
            continue
        config = c["config"]
        for day, bunches in c["days"]:
            cut_day = day - dt.timedelta(days=config["cut_to_harvest_days"])
            slot = weeks.get(week_key(cut_day))
            if slot and slot["future"]:
                slot["needed"] += bunches / config["harvest_rate"]
    rows = list(weeks.values())
    for slot in rows:
        if slot["needed"] is not None:
            slot["needed"] = int(slot["needed"] + .5)
    done = [s for s in rows if s["actual"]]
    last_actual = done[-1] if done else None
    # A wave often begins on the last days of a week; that first thin week says nothing about the pace needed.
    ahead_rows = [s for s in rows if s["future"]]
    next_need = next((s for s, after in zip(ahead_rows, ahead_rows[1:] + [None]) if s["needed"] and (after is None or s["needed"] * 2 >= after["needed"])), None)
    best = max((s["actual"] for s in done), default=0)
    alert = bool(best and next_need and next_need["needed"] > PACE_ALERT * best)
    return {"weeks": rows, "last_actual": last_actual, "next_need": next_need, "alert": alert, "times": round(next_need["needed"] / best) if alert else None}


def snapshot_rows(summary):
    """What a frozen forecast keeps: per week, lô, colour and layer."""
    return [{k: r[k] for k in ("week", "block", "block_code", "tag", "ribbon", "cycle", "layer", "bunches", "kg")} for r in summary["rows"]]
