"""The sổ lô in the database: Lotus Work Entry lines (one job, one lô, one tổ, one day) and their tổ-day header.

Readers that were written for the old bunch ledger (Lotus Bunch Event) get the same row shape from `bunch_rows`:
event_type is the line's bunch stage and event_date its work day. Only Confirmed lines are official; Draft and Sent
lines are returned as "Draft" (not yet confirmed) to readers that still speak the old states.
"""
import frappe
from frappe.utils import add_days, cint, flt, getdate, nowdate

from lotus_farm import lot_ledger_rules as rules

ENTRY, REPORT, MATERIAL = "Lotus Work Entry", "Lotus Daily Report", "Lotus Work Entry Material"
EVENT_TYPES = (rules.SUCKER, rules.INJECT, rules.CUT, rules.REJECT, rules.HARVEST)
_TO_ENTRY = {"event_type": "stage", "event_date": "posting_date"}
_TO_EVENT = {v: k for k, v in _TO_ENTRY.items()}
QUARANTINE_LOOKBACK_DAYS = 180


def _entry_filters(filters):
    result = {}
    for key, value in (filters or {}).items():
        field = _TO_ENTRY.get(key, key)
        if field == "state":
            value = _entry_state(value)
        result[field] = value
    if "stage" not in result:
        result["stage"] = ["in", list(EVENT_TYPES)]
    return result


def _entry_state(value):
    """Old ledger states → sổ lô states: an unconfirmed line is Draft or Sent."""
    def widen(states):
        out = []
        for s in states:
            out += [rules.DRAFT, rules.SENT] if s == rules.DRAFT else [s]
        return out
    if isinstance(value, str):
        return ["in", widen([value])] if value == rules.DRAFT else value
    if isinstance(value, (list, tuple)) and len(value) == 2 and value[0] == "in":
        return ["in", widen(list(value[1]))]
    return value


def bunch_rows(filters=None, fields=None, order_by="posting_date asc, creation asc"):
    """Bunch-ledger lines (chọn chồi, chích, cắt, hủy, thu) of the sổ lô, in the shape of the old Lotus Bunch Event."""
    wanted = list(fields or ["name", "farm", "farm_block", "work_team", "cycle_no", "event_type", "event_date", "qty",
                             "area_ha", "bunch_tag", "reject_stage", "reason", "weight_kg", "source_type", "source_name",
                             "source_key", "state", "entered_by", "confirmed_by", "confirmed_at", "notes"])
    columns = sorted({_TO_ENTRY.get(f, f) for f in wanted} | {"stage", "state"})
    rows = frappe.get_all(ENTRY, filters=_entry_filters(filters), fields=columns, order_by=order_by, limit_page_length=0)
    result = []
    for row in rows:
        event = frappe._dict({_TO_EVENT.get(k, k): v for k, v in row.items()})
        event["event_type"] = row.stage
        if row.state == rules.SENT:
            event["state"] = rules.DRAFT
        if "qty" in event:
            event["qty"] = cint(event["qty"])
        result.append(event)
    return result


# ---------------------------------------------------------------- quarantine

def _spray_lines(block, first, last, live=False):
    """Lines of the lô carrying a product with a pre-harvest interval. live: every line not voided (a spray reported but
    not yet confirmed still holds the harvest); otherwise confirmed lines only."""
    state = ["!=", rules.VOIDED] if live else rules.CONFIRMED
    names = frappe.get_all(ENTRY, filters={"farm_block": block, "state": state, "posting_date": ["between", [first, last]]},
                           fields=["name", "posting_date"], limit_page_length=0)
    if not names:
        return []
    days = {n.name: getdate(n.posting_date) for n in names}
    materials = frappe.get_all(MATERIAL, filters={"parenttype": ENTRY, "parent": ["in", list(days)], "phi_days": [">", 0]},
                               fields=["parent", "phi_days"], limit_page_length=0)
    lines = {}
    for m in materials:
        lines.setdefault(m.parent, {"posting_date": days[m.parent], "materials": []})["materials"].append({"phi_days": cint(m.phi_days)})
    return list(lines.values())


def harvest_hold(block, day):
    """(spray day, last day) of the pre-harvest interval that forbids harvesting this lô on `day`, or None."""
    day = getdate(day)
    lines = _spray_lines(block, add_days(day, -QUARANTINE_LOOKBACK_DAYS), day, live=True)
    return rules.harvest_blocked(day, rules.quarantine_intervals(lines))


def refresh_quarantine(block):
    """Farm Block.lotus_quarantine_until = end of the latest pre-harvest interval still running, from confirmed lines."""
    today = getdate(nowdate())
    end = rules.quarantine_end(_spray_lines(block, add_days(today, -QUARANTINE_LOOKBACK_DAYS), add_days(today, 3650)))
    frappe.db.set_value("Farm Block", block, "lotus_quarantine_until", end if end and end >= today else None, update_modified=False)
    return end


# ---------------------------------------------------------------- catalogue

def works(farm):
    """The việc of a farm that can be reported, with what the rules need to know about each."""
    from lotus_farm import field_report as field
    result = {}
    for w in field._works(farm):
        result[w.name] = frappe._dict(name=w.name, code=w.work_code, label=w.work_name, uom=w.uom, stage=w.lotus_bunch_stage or "",
                                      group=w.lotus_work_group or rules.FIELD_GROUP, pay_mode=w.lotus_pay_mode,
                                      cap_basis=w.lotus_cap_basis or "None", requires_material=cint(w.lotus_requires_material),
                                      records_disease=cint(w.get("lotus_records_disease")),
                                      norm_min=flt(w.productivity_per_workday))
    return result


def work_for_stage(farm, stage):
    return next((w for w in works(farm).values() if w.stage == stage), None)
