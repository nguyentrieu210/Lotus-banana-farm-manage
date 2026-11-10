"""Bảng màu dây và danh sách cần thu: bunches on the plants per lô and ribbon colour, from the confirmed sổ lô.

Each colour of a week (cắt bắp lần 1 or 2) is one card: cut, bagged, rejected after cutting, harvested, left on the
plants, its age in weeks and its harvest window from the parameters in force. A colour in or past its window is due;
lô under a pesticide quarantine are flagged, since thu hoạch is refused there until the interval ends.
"""
import datetime as dt
from io import BytesIO

import frappe
from frappe.utils import cint, getdate, nowdate

from lotus_farm import block_forecast
from lotus_farm import bunch_report_rules as rules
from lotus_farm import field_report as field
from lotus_farm.lot_ledger import ENTRY, bunch_rows

WEEKS_PER_SHEET = 10


def _context(farm=None, zone=None):
    names = field.farm_names()
    if not names:
        frappe.throw("Bạn không có quyền với vườn nào.", frappe.PermissionError)
    if not farm:
        with_ledger = {r.farm for r in frappe.get_all(ENTRY, filters={"farm": ["in", names], "stage": ["is", "set"]}, fields=["farm"], distinct=True,
                                                      limit_page_length=0)}
        farm = next((n for n in names if n in with_ledger), names[0])
    field.require_farm(farm)
    all_blocks = frappe.get_all("Farm Block", filters={"farm": farm, "active": 1}, fields=["name", "block_code", "farm_zone", "lotus_tree_count"],
                                limit_page_length=0)
    blocks = {b.name: {"code": b.block_code, "zone": b.farm_zone or "", "trees": cint(b.lotus_tree_count)} for b in all_blocks if not zone or b.farm_zone == zone}
    farms = frappe.get_all("Farm", filters={"name": ["in", names]}, fields=["name", "farm_name"], limit_page_length=0)
    return frappe._dict(farm=farm, zone=zone or "", blocks=blocks, farms=farms, zones=sorted({b.farm_zone for b in all_blocks if b.farm_zone}))


def _head(ctx):
    return {"farm": ctx.farm, "zone": ctx.zone, "farms": ctx.farms, "zones": ctx.zones}


def _tags(farm):
    return {t.name: {"label": t.color_label or t.name, "code": t.color_code or "", "week": t.week_number, "year": t.week_year, "half": cint(t.week_half)}
            for t in frappe.get_all("Bunch Tag", filters={"farm": farm}, fields=["name", "color_label", "color_code", "week_number", "week_year", "week_half"],
                                    limit_page_length=0)}


def _days_for(farm):
    params = block_forecast._bunch_params(block_forecast._profiles(farm))

    def days_for(block, first_cut):
        config = params(block, first_cut)[1]
        return config["cut_to_harvest_min_days"], config["cut_to_harvest_max_days"]
    return days_for


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
    ctx = _context(farm, zone)
    blocks = {name: b for name, b in ctx.blocks.items() if not block or name == block}
    day = _day(week)
    lines = bunch_rows({"farm": ctx.farm, "state": "Confirmed", "farm_block": ["in", list(blocks) or [""]],
                        "event_type": ["in", ["Cut Bud", "Reject", "Harvest"]]}, FIELDS)
    cards = rules.stock(lines, _tags(ctx.farm), blocks, _days_for(ctx.farm), day)["cards"]
    result = rules.ribbon(cards, _bags(ctx.farm, blocks), _quarantine(blocks), day)
    return dict(result, **_head(ctx), due_rows=rules.due_rows(result["cards"]), day=str(day))


@frappe.whitelist()
def harvest_due(farm=None, week=None, zone=None):
    """Only the lô and colours to harvest in the week (this week by default), oldest first, lô under quarantine flagged."""
    return board(farm, zone, week=week)["due_rows"]


def _write_sheet(sheet, year, mondays, tags_by_week, blocks, cut, trees):
    """The farm's own book layout: columns G to Z hold ten weeks, two columns each, so the file can be read back."""
    pad = [None] * 26
    sheet.append([f"SỐ LIỆU CẮT BẮP NĂM {year} FARM 222"] + pad)
    heads = ["Lô", "Số cây", "Số cây cắt búp (cây)", "Số cây còn lại (cây)", "Tỉ lệ cắt búp (%)", "GHI CHÚ"]
    colours = [None] * 6
    for monday in mondays:
        sunday = monday + dt.timedelta(days=6)
        heads += [f"Tuần {monday.isocalendar()[1]} ({monday.strftime('%d/%m')}-{sunday.strftime('%d/%m')})", None]
        colour = tags_by_week.get((monday.isocalendar()[0], monday.isocalendar()[1]), "").upper()
        colours += [f"{colour}(RÚT)" if colour else None, colour or None]
    sheet.append(heads + ["Tổng"])
    sheet.append(colours + [None])
    column_totals, grand = [0] * (len(mondays) * 2), 0
    for name in sorted(cut, key=lambda b: (len(blocks[b]["code"]), blocks[b]["code"])):
        cells, row_total = [], 0
        for index, monday in enumerate(mondays):
            lan1, lan2 = cut[name].get((monday, 1), 0), cut[name].get((monday, 2), 0)
            cells += [lan1 or None, lan2 or None]
            row_total += lan1 + lan2
            column_totals[index * 2] += lan1
            column_totals[index * 2 + 1] += lan2
        all_cut = trees[name]["all_cut"]
        total_trees = trees[name]["trees"]
        sheet.append([blocks[name]["code"], total_trees, all_cut, max(0, total_trees - all_cut), round(all_cut / total_trees * 100, 2) if total_trees else None, None]
                     + cells + [row_total])
        grand += row_total
    sheet.append(["TỔNG", None, None, None, None, None] + column_totals + [grand])
    sheet.freeze_panes = "G4"


@frappe.whitelist()
def export_cut_book(farm=None, zone=None):
    """Sổ cắt bắp: the confirmed cắt bắp of the sổ lô in the layout of the farm's Excel book, ten weeks to a sheet."""
    from openpyxl import Workbook
    ctx = _context(farm, zone)
    tags = _tags(ctx.farm)
    lines = bunch_rows({"farm": ctx.farm, "state": "Confirmed", "event_type": "Cut Bud", "farm_block": ["in", list(ctx.blocks) or [""]]}, FIELDS)
    weeks = rules.cut_weeks(lines, tags, ctx.blocks)
    if not weeks:
        frappe.throw("Chưa có số cắt bắp để xuất.")
    by_week = {(t["year"], t["week"]): t["label"] for t in tags.values()}
    cut, trees = {}, {}
    for week in weeks:
        monday = getdate(week["start"])
        for lot in week["lots"]:
            slot = cut.setdefault(lot["block"], {})
            slot[(monday, 1)], slot[(monday, 2)] = lot["lan1"], lot["lan2"]
            info = trees.setdefault(lot["block"], {"trees": ctx.blocks[lot["block"]]["trees"], "all_cut": 0})
            info["all_cut"] += lot["total"]
    book = Workbook()
    book.remove(book.active)
    first = getdate(weeks[0]["start"])
    for index in range(max(1, (len(weeks) + WEEKS_PER_SHEET - 1) // WEEKS_PER_SHEET)):
        mondays = [first + dt.timedelta(weeks=WEEKS_PER_SHEET * index + i) for i in range(WEEKS_PER_SHEET)]
        sheet = book.create_sheet(f"Tuần {mondays[0].isocalendar()[1]}-{mondays[-1].isocalendar()[1]}")
        _write_sheet(sheet, mondays[0].isocalendar()[0], mondays, by_week, ctx.blocks, cut, trees)
    out = BytesIO()
    book.save(out)
    frappe.local.response.filename = f"so-cat-bap-{ctx.farm}.xlsx"
    frappe.local.response.filecontent = out.getvalue()
    frappe.local.response.type = "download"
