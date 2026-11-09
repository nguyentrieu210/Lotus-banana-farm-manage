"""The flow of bunches through a lô, from the ledger. Pure: no Frappe, no database.

Every bunch is counted once, at the stage nearest to harvest (FR-009, FR-010):
 cut     bunches already cut, by lô and colour
 inject  injected and not cut yet, oldest first (FR-025)
 sucker  selected suckers not yet injected, dated by the real selection day
 tree    what the tree count still promises after all of the above (FR-028)
Recorded rejects count toward the expected loss, never on top of it (FR-027).
"""
import datetime as dt

from lotus_farm.block_forecast_engine import date as to_date
from lotus_farm.block_forecast_engine import distribute_daily, months_after, portions, round_excel

SUCKER, INJECT, CUT, REJECT, HARVEST, AFTER_CUT, BEFORE_CUT = "Sucker Select", "Bud Injection", "Cut Bud", "Reject", "Harvest", "After Cut", "Before Cut"


def expected_left(cut, rejected, harvested, harvest_rate):
    """Bunches still to come from what was cut. The larger of the recorded and the expected loss applies, once."""
    loss = max(int(rejected), int(cut) - round_excel(int(cut) * float(harvest_rate)))
    return max(0, int(cut) - loss - int(harvested))


def _spread(bunches, first, last):
    count = (last - first).days + 1
    return [(first + dt.timedelta(days=i), n) for i, n in enumerate(distribute_daily(bunches, count)) if n]


def _qty(line):
    return int(line["qty"])


def _ordered(lines):
    return sorted(lines, key=lambda c: (str(c["event_date"]), str(c.get("name") or "")))


def _groups(lines):
    groups = {}
    for line in lines:
        tag = line.get("bunch_tag")
        if not tag:
            continue
        g = groups.setdefault((line["farm_block"], tag), {"cuts": [], "rejected": 0, "harvested": 0})
        if line["event_type"] == CUT:
            g["cuts"].append(line)
        elif line["event_type"] == HARVEST:
            g["harvested"] += _qty(line)
        elif line["event_type"] == REJECT and line.get("reject_stage") == AFTER_CUT:
            g["rejected"] += _qty(line)
    return groups


def cut_cohorts(lines, params_for, today):
    """One cohort per cut line: what is left of it and the days it should be harvested on, the total preserved.

    params_for(block, day) -> (profile name or None, parameters). A window already past lands on today and is flagged overdue;
    days already past inside a running window are not used.
    """
    today = to_date(today)
    cohorts = []
    for (block, tag), g in _groups(lines).items():
        if not g["cuts"]:
            continue
        cuts = _ordered(g["cuts"])
        total = sum(_qty(c) for c in cuts)
        profile, config = params_for(block, to_date(cuts[0]["event_date"]))
        left = expected_left(total, g["rejected"], g["harvested"], config["harvest_rate"])
        group = {"cut": total, "rejected": g["rejected"], "harvested": g["harvested"], "left": left}
        for cut, bunches in zip(cuts, portions(left, [_qty(c) / total for c in cuts])):
            if not bunches:
                continue
            day = to_date(cut["event_date"])
            start = day + dt.timedelta(days=config["cut_to_harvest_min_days"])
            end = day + dt.timedelta(days=config["cut_to_harvest_max_days"])
            overdue = end < today
            days = [(today, bunches)] if overdue else _spread(bunches, max(start, today), end)
            cohorts.append({"layer": "cut", "block": block, "tag": tag, "cycle": int(cut.get("cycle_no") or 1), "event": cut.get("name"), "cut_date": day, "bunches": bunches,
                            "window_start": start, "window_end": end, "overdue": overdue, "profile": profile, "config": config, "group": group, "days": days})
    return cohorts


def _per_cycle(lines):
    cycles = {}
    for line in lines:
        key = (line["farm_block"], int(line.get("cycle_no") or 1))
        c = cycles.setdefault(key, {"injected": [], "cuts": [], "before": 0, "suckers": []})
        if line["event_type"] == INJECT:
            c["injected"].append(line)
        elif line["event_type"] == CUT:
            c["cuts"].append(line)
        elif line["event_type"] == SUCKER:
            c["suckers"].append(line)
        elif line["event_type"] == REJECT and line.get("reject_stage") == BEFORE_CUT:
            c["before"] += _qty(line)
    return cycles


def _consume(batches, amount):
    """Take `amount` off batches, oldest first: [(batch, what is left of it)]."""
    left = []
    for batch in _ordered(batches):
        take = min(amount, _qty(batch))
        amount -= take
        if _qty(batch) > take:
            left.append((batch, _qty(batch) - take))
    return left


def inject_cohorts(lines, params_for, today):
    """Injected, not cut yet. Returns (cohorts, {(lô, vụ): bunches already seen in the field}).

    Cuts in the first days after a lô's first recorded injection belong to bunches injected before recording began (FR-025), so
    they do not use up those injections; they still count as bunches seen, so the tree layer does not promise them again.
    """
    today = to_date(today)
    cohorts, observed = [], {}
    for (block, cycle), c in _per_cycle(lines).items():
        all_cut = sum(_qty(x) for x in c["cuts"])
        if not c["injected"]:
            if all_cut:
                observed[(block, cycle)] = all_cut
            continue
        batches = _ordered(c["injected"])
        first = to_date(batches[0]["event_date"])
        profile, config = params_for(block, first)
        grace_end = first + dt.timedelta(days=config["inject_to_cut_days"])
        counted = sum(_qty(x) for x in c["cuts"] if to_date(x["event_date"]) >= grace_end)
        remaining = _consume(batches, counted)
        uncut = sum(n for _, n in remaining)
        observed[(block, cycle)] = all_cut + uncut
        if not uncut:
            continue
        rate = config["cut_rate_per_flowered_bunch"] * config["harvest_rate"]
        left = expected_left(uncut, c["before"], 0, rate)
        group = {"injected": sum(_qty(b) for b in batches), "cut": counted, "uncut": uncut, "rejected": c["before"], "left": left}
        for (batch, _), bunches in zip(remaining, portions(left, [n / uncut for _, n in remaining])):
            if not bunches:
                continue
            due = to_date(batch["event_date"]) + dt.timedelta(days=config["inject_to_cut_days"])
            cut_day = max(due, today)
            start = cut_day + dt.timedelta(days=config["cut_to_harvest_min_days"])
            end = cut_day + dt.timedelta(days=config["cut_to_harvest_max_days"])
            cohorts.append({"layer": "inject", "block": block, "tag": None, "cycle": cycle, "event": batch.get("name"), "bunches": bunches, "window_start": start, "window_end": end,
                            "overdue": due < today, "profile": profile, "config": config, "group": group, "days": _spread(bunches, start, end)})
    return cohorts, observed


def waiting_injections(lines, params_for, today):
    """Each injection still waiting to be cut, oldest first per lô, by the same reckoning as the forecast."""
    today = to_date(today)
    waiting = []
    for (block, cycle), c in _per_cycle(lines).items():
        if not c["injected"]:
            continue
        batches = _ordered(c["injected"])
        days = params_for(block, to_date(batches[0]["event_date"]))[1]["inject_to_cut_days"]
        grace_end = to_date(batches[0]["event_date"]) + dt.timedelta(days=days)
        counted = sum(_qty(x) for x in c["cuts"] if to_date(x["event_date"]) >= grace_end)
        for batch, left in _consume(batches, counted):
            due = to_date(batch["event_date"]) + dt.timedelta(days=days)
            waiting.append({"event": batch.get("name"), "block": block, "cycle": cycle, "date": str(batch["event_date"]), "left": left, "due": str(due), "late_days": max(0, (today - due).days)})
    return waiting


def sucker_cohorts(lines, observed, params_for, today):
    """Selected suckers not yet seen as bunches. Returns (cohorts, {(lô, vụ): bunches they should reach cắt bắp with}). Dates come from the real selection day."""
    today = to_date(today)
    cohorts, claimed = [], {}
    for (block, cycle), c in _per_cycle(lines).items():
        if not c["suckers"]:
            continue
        remaining = _consume(c["suckers"], observed.get((block, cycle), 0))
        for batch, suckers in remaining:
            day = to_date(batch["event_date"])
            profile, config = params_for(block, day)
            shoots = round_excel(suckers * config["flowering_rate"])
            cut = min(shoots, round_excel(suckers * config["cut_rate_per_tree"]))
            claimed[(block, cycle)] = claimed.get((block, cycle), 0) + cut
            bunches = round_excel(cut * config["harvest_rate"])
            if not bunches:
                continue
            bloom = months_after(day, config["sucker_to_flower_months"])
            start = bloom + dt.timedelta(days=config["shoot_to_inject_days"] + config["inject_to_cut_days"] + config["cut_to_harvest_days"])
            end = start + dt.timedelta(days=config["wave_window_days"] - 1)
            late = end < today
            first, last = (today, today + dt.timedelta(days=config["wave_window_days"] - 1)) if late else (max(start, today), end)
            cohorts.append({"layer": "sucker", "block": block, "tag": None, "cycle": cycle, "event": batch.get("name"), "bunches": bunches, "window_start": start, "window_end": end,
                            "overdue": late, "profile": profile, "config": config, "group": {"suckers": suckers, "selected": day, "left": bunches}, "days": _spread(bunches, first, last)})
    return cohorts, claimed


def tree_cohorts(waves, observed, claimed, current_cycle, today):
    """What the tree-count forecast still promises. Bunches already seen come off the earliest waves of their vụ, counted at cắt bắp: a wave
    of 1.000 trees expects 900 cut, so 900 seen means that wave is finished and the farm total stays what the trees allow.

    The old engine numbers crops from 1. Here generation 0 is the lô's current vụ, unless the wave comes from an approved cohort with its own vụ.
    A wave whose time has passed with nothing recorded moves into the coming weeks (FR-028).
    """
    today = to_date(today)
    def wave_cycle(wave):
        if wave.get("source_cohort"):
            return int(wave["cycle_no"])
        return int(current_cycle.get(wave["farm_block"]) or wave["cycle_no"]) + int(wave.get("generation") or 0) if current_cycle.get(wave["farm_block"]) else int(wave["cycle_no"])

    seen = {}
    for source in (observed, claimed):
        for key, value in source.items():
            seen[key] = seen.get(key, 0) + value
    cohorts = []
    for wave in sorted(waves, key=lambda w: (w["farm_block"], str(w["harvest_date"]), int(w.get("wave") or 0))):
        block, cycle = wave["farm_block"], wave_cycle(wave)
        expected, harvest = int(wave["bunches_cut"]), int(wave["bunches_harvest"])
        if expected <= 0 or harvest <= 0:
            continue
        take = min(seen.get((block, cycle), 0), expected)
        if take:
            seen[(block, cycle)] -= take
        bunches = round_excel(harvest * (expected - take) / expected)
        if not bunches:
            continue
        start, end = to_date(wave["harvest_date"]), to_date(wave["harvest_window_end"])
        window = int(wave.get("window_days") or (end - start).days + 1)
        moved = end < today
        first, last = (today, today + dt.timedelta(days=window - 1)) if moved else (max(start, today), end)
        cohorts.append({"layer": "tree", "block": block, "tag": None, "cycle": cycle, "event": None, "bunches": bunches, "window_start": start, "window_end": end, "overdue": moved,
                        "profile": wave.get("profile"), "config": wave["timing"],
                        "group": {"trees": int(wave.get("tree_qty") or 0), "wave": wave.get("wave"), "flower": str(wave.get("flower_window_start") or ""), "seen": take, "left": bunches,
                                  "source": wave.get("source") or "", "status": wave.get("count_status") or ""},
                        "days": _spread(bunches, first, last)})
    return cohorts
