"""Bảng màu dây và danh sách cần thu: bunches on the plants per lô and ribbon colour, from the confirmed sổ lô.

Each colour of a week (cắt bắp lần 1 or 2) is one card: cut, bagged, rejected after cutting, harvested, left on the
plants, its age in weeks and its harvest window from the parameters in force. A colour in or past its window is due;
lô under a pesticide quarantine are flagged, since thu hoạch is refused there until the interval ends.
"""
import datetime as dt

import frappe
from frappe.utils import cint, getdate, nowdate

from lotus_farm import bunch_report as report
from lotus_farm import bunch_report_rules as rules
from lotus_farm.lot_ledger import ENTRY, bunch_rows

FIELDS = ["farm_block", "event_type", "event_date", "qty", "bunch_tag", "reject_stage", "weight_kg"]


def _day(week=None):
    """The day the board is read on: today, or the Monday of a later week ("2026-W47" or any day in it)."""
    today = getdate(nowdate())
    if not week:
        return today
    text = str(week).strip()
    if "-W" in text.upper():
        year, number = text.upper().split("-W")
        monday = dt.date.fromisocalendar(cint(year), cint(number), 1)
    else:
        day = getdate(text)
        monday = day - dt.timedelta(days=day.weekday())
    return max(today, monday)


def _quarantine(blocks):
    return {b.name: b.lotus_quarantine_until for b in frappe.get_all(
        "Farm Block", filters={"name": ["in", list(blocks) or [""]]}, fields=["name", "lotus_quarantine_until"], limit_page_length=0)}


def _bags(farm, blocks):
    bags = {}
    for r in frappe.get_all(ENTRY, filters={"farm": farm, "stage": "Bag", "state": "Confirmed", "farm_block": ["in", list(blocks) or [""]]},
                            fields=["farm_block", "bunch_tag", "qty"], limit_page_length=0):
        key = (r.farm_block, r.bunch_tag)
        bags[key] = bags.get(key, 0) + cint(r.qty)
    return bags


@frappe.whitelist()
def board(farm=None, zone=None, block=None, week=None):
    """Every colour cut on the lô (the ones harvested out included), per lô, and the lô and colours to harvest in the week."""
    ctx = report._context(farm, zone)
    blocks = {name: b for name, b in ctx.blocks.items() if not block or name == block}
    day = _day(week)
    lines = bunch_rows({"farm": ctx.farm, "state": "Confirmed", "farm_block": ["in", list(blocks) or [""]],
                        "event_type": ["in", ["Cut Bud", "Reject", "Harvest"]]}, FIELDS)
    cards = rules.stock(lines, report._tags(ctx.farm), blocks, report._days_for(ctx.farm), day)["cards"]
    result = rules.ribbon(cards, _bags(ctx.farm, blocks), _quarantine(blocks), day)
    return dict(result, **report._head(ctx), due_rows=rules.due_rows(result["cards"]), day=str(day))


@frappe.whitelist()
def harvest_due(farm=None, week=None, zone=None):
    """Only the lô and colours to harvest in the week (this week by default), oldest first, lô under quarantine flagged."""
    return board(farm, zone, week=week)["due_rows"]
