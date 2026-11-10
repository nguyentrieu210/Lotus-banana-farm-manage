"""Vòng chăm sóc: when each việc vườn is due on each lô. Pure: no Frappe, no database.

A rule says: việc X every N days, on the whole farm or on one khu, from a day (to a day). The rule in force on a lô is
the approved one valid that day, the khu's own before the farm's, then the newest version. A lô is done with a việc on
the day a confirmed line says the whole lô is done; the days before are work in progress. A lô never done is due from
the day the rule starts. A việc without a rule is never due.
"""
import datetime as dt

OVERDUE, DUE, LATER = "overdue", "due", "later"
APPROVED = "Approved"


def _day(value):
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])


def _natural(code):
    return (len(str(code or "")), str(code or ""))


def zone_of(value):
    return str(value or "").strip().upper()


def in_force(rules, day):
    """Per rule name, the approved version that applies on a day: the highest version already started. A newer version
    ends the older ones; one past its last day ends the rule (an older version does not come back)."""
    day = _day(day)
    latest = {}
    for r in rules:
        if (r.get("approval_state") or APPROVED) != APPROVED or _day(r["valid_from"]) > day:
            continue
        key = r.get("rule_name") or r["name"]
        if key not in latest or int(r.get("version") or 0) > int(latest[key].get("version") or 0):
            latest[key] = r
    return [r for r in latest.values() if int(r.get("repeat_days") or 0) > 0 and (not r.get("valid_to") or day <= _day(r["valid_to"]))]


def rule_for(rules, zone, work_type, day):
    """The rule in force for a việc on a lô of this khu on a day, or None: the khu's own before the farm's, then the one
    started last (a season rule over the year-round one)."""
    zone = zone_of(zone)
    fits = [r for r in in_force(rules, day)
            if r["work_type"] == work_type and (not zone_of(r.get("farm_zone")) or zone_of(r.get("farm_zone")) == zone)]
    if not fits:
        return None
    return max(fits, key=lambda r: (bool(zone_of(r.get("farm_zone"))), str(r["valid_from"]), int(r.get("version") or 0)))


def last_done(lines):
    """{(lô, việc): the latest day a line said the whole lô was done}. The caller passes confirmed lines only."""
    done = {}
    for line in lines:
        if not line.get("done"):
            continue
        key, day = (line["farm_block"], line["work_type"]), _day(line["posting_date"])
        if key not in done or day > done[key]:
            done[key] = day
    return done


def cell(rule, done_on, today, until):
    """One lô × việc: the day it is due, the days it is late, and whether it falls due by `until` (end of the period
    looked at). Due on the day itself; late from the day after."""
    today, until = _day(today), _day(until)
    due = done_on + dt.timedelta(days=int(rule["repeat_days"])) if done_on else _day(rule["valid_from"])
    late = (today - due).days
    status = OVERDUE if late > 0 else DUE if due <= until else LATER
    return {"last_done": str(done_on) if done_on else None, "due_date": str(due), "overdue_days": max(late, 0), "status": status,
            "rule": rule["name"], "repeat_days": int(rule["repeat_days"])}


def due_cells(blocks, work_types, rules, done, open_rounds, today, until):
    """Every lô × việc with a rule in force today, earliest due first.

    blocks: {lô: {"code", "zone"}}; done: from last_done; open_rounds: {(lô, việc): {"name", "work_team", ...}}."""
    rows = []
    for block, b in blocks.items():
        for work in work_types:
            rule = rule_for(rules, b.get("zone"), work, today)
            if not rule:
                continue
            row = dict(cell(rule, done.get((block, work)), today, until), farm_block=block, code=b["code"], zone=zone_of(b.get("zone")),
                       work_type=work)
            given = open_rounds.get((block, work))
            row["assignment"] = given.get("name") if given else None
            row["work_team"] = given.get("work_team") if given else None
            rows.append(row)
    rows.sort(key=lambda r: (r["due_date"], r["zone"], _natural(r["code"]), r["work_type"]))
    return rows


def summary(rows):
    """Per việc: how many lô are late, due in the period, already given to a tổ."""
    out = {}
    for r in rows:
        s = out.setdefault(r["work_type"], {"work_type": r["work_type"], "overdue": 0, "due": 0, "later": 0, "given": 0, "to_give": 0})
        s[r["status"]] += 1
        if r["assignment"]:
            s["given"] += 1
        elif r["status"] != LATER:
            s["to_give"] += 1
    return sorted(out.values(), key=lambda s: (-s["overdue"], -s["to_give"], s["work_type"]))


def check_rule(rule):
    """Errors of a rule as typed by the quản lý vườn, in Vietnamese; empty when it can be saved."""
    errors = []
    if not str(rule.get("work_type") or "").strip():
        errors.append("Chọn việc.")
    days = rule.get("repeat_days")
    try:
        days = int(days)
    except (TypeError, ValueError):
        days = 0
    if not 1 <= days <= 366:
        errors.append("Vòng phải từ 1 đến 366 ngày.")
    if not rule.get("valid_from"):
        errors.append("Chọn ngày bắt đầu áp dụng.")
    elif rule.get("valid_to") and _day(rule["valid_to"]) < _day(rule["valid_from"]):
        errors.append("Ngày hết áp dụng không được trước ngày bắt đầu.")
    return errors
