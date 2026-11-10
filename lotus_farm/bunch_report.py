"""Báo cáo ngày, phần vườn: read-only views of the bunch ledger for anyone working with the field report."""
import datetime as dt
from io import BytesIO

import frappe
from frappe.utils import cint, date_diff, getdate, nowdate

from lotus_farm import block_forecast, bunch_flow_rules
from lotus_farm import bunch_report_rules as rules
from lotus_farm import field_report as field
from lotus_farm import report_filter_rules as report_filters
from lotus_farm.lot_ledger import ENTRY, bunch_rows

MAX_DAYS = 366
WEEKS_PER_SHEET = 10
FIELDS = ["name", "farm_block", "work_team", "event_type", "event_date", "qty", "area_ha", "bunch_tag", "reject_stage", "reason", "weight_kg", "state", "source_type"]


def _context(farm=None, zone=None):
    names = field.farm_names()
    if not names:
        frappe.throw("Bạn không có quyền với vườn nào.", frappe.PermissionError)
    if not farm:
        with_ledger = {r.farm for r in frappe.get_all(ENTRY, filters={"farm": ["in", names], "stage": ["is", "set"]}, fields=["farm"], distinct=True, limit_page_length=0)}
        farm = next((n for n in names if n in with_ledger), names[0])
    field.require_farm(farm)
    all_blocks = frappe.get_all("Farm Block", filters={"farm": farm, "active": 1}, fields=["name", "block_code", "farm_zone", "lotus_tree_count"], limit_page_length=0)
    blocks = {b.name: {"code": b.block_code, "zone": b.farm_zone or "", "trees": cint(b.lotus_tree_count)} for b in all_blocks if not zone or b.farm_zone == zone}
    farms = frappe.get_all("Farm", filters={"name": ["in", names]}, fields=["name", "farm_name"], limit_page_length=0)
    return frappe._dict(farm=farm, zone=zone or "", blocks=blocks, farms=farms, zones=sorted({b.farm_zone for b in all_blocks if b.farm_zone}))


def _head(ctx):
    return {"farm": ctx.farm, "zone": ctx.zone, "farms": ctx.farms, "zones": ctx.zones}


def _lines(ctx, states=("Confirmed",), **filters):
    return bunch_rows(dict(filters, farm=ctx.farm, state=["in", list(states)]), FIELDS)


def _tags(farm):
    return {t.name: {"label": t.color_label or t.name, "code": t.color_code or "", "week": t.week_number, "year": t.week_year, "half": cint(t.week_half)}
            for t in frappe.get_all("Bunch Tag", filters={"farm": farm}, fields=["name", "color_label", "color_code", "week_number", "week_year", "week_half"], limit_page_length=0)}


def _days_for(farm):
    params = block_forecast._bunch_params(block_forecast._profiles(farm))

    def days_for(block, first_cut):
        config = params(block, first_cut)[1]
        return config["cut_to_harvest_min_days"], config["cut_to_harvest_max_days"]
    return days_for


NO_TEAM = "Sổ đầu kỳ"  # the opening book names no tổ; like (blank) in a pivot, it needs its own tick
BUNCH_FIELDS = ("year", "month", "week", "zone", "block", "team", "colour", "lan")


def _ledger_facts(ctx, tags):
    """Every confirmed line with what the pivot-style filter can choose from. Chích and hủy before cutting have no colour, so a colour filter passes them by."""
    teams = {t.name: t.team_name.strip() for t in field._teams(ctx.farm)}
    facts = []
    for line in _lines(ctx):
        block = ctx.blocks.get(line.farm_block)
        if not block:
            continue
        fact = dict(report_filters.date_facts(line.event_date), zone=block["zone"], block=block["code"], team=teams.get(line.work_team) or NO_TEAM)
        tag = tags.get(line.bunch_tag)
        if tag:
            fact.update(colour=tag.get("label") or "", lan=str(tag.get("half") or ""))
        facts.append((line, fact))
    return facts


def _cut_facts(ctx, tags):
    return [(line, fact) for line, fact in _ledger_facts(ctx, tags) if line.event_type == "Cut Bud"]


def _chosen(raw):
    return report_filters.clean(frappe.parse_json(raw) if raw else {})


@frappe.whitelist()
def stock(farm=None, filters=None):
    ctx, wanted = _context(farm), _chosen(filters)
    tags = _tags(ctx.farm)
    facts = _ledger_facts(ctx, tags)
    pairs = _chosen_colours(facts, wanted)
    lines = [l for l, _ in facts if (l.farm_block, l.bunch_tag) in pairs]
    return dict(_head(ctx), options=report_filters.options([f for _, f in facts], wanted, BUNCH_FIELDS), **rules.stock(lines, tags, ctx.blocks, _days_for(ctx.farm), nowdate()))


def _entry_facts(ctx, tags):
    """Bao, tỉa and chống đổ from the phiếu, with the same fields to filter on."""
    teams = {t.name: t.team_name.strip() for t in field._teams(ctx.farm)}
    facts = []
    for entry in _phieu_lines(ctx):
        block = ctx.blocks.get(entry["farm_block"])
        if not block:
            continue
        fact = dict(report_filters.date_facts(entry["event_date"]), zone=block["zone"], block=block["code"], team=teams.get(entry["work_team"]) or NO_TEAM)
        tag = tags.get(entry["bunch_tag"])
        if tag:
            fact.update(colour=tag.get("label") or "", lan=str(tag.get("half") or ""))
        facts.append((entry, fact))
    return facts


def _chosen_colours(facts, wanted):
    """(lô, màu) whose cutting matches the filter; everything that later happened to those bunches then belongs to them."""
    return {(line.farm_block, line.bunch_tag) for line, fact in facts if line.event_type == "Cut Bud" and report_filters.keep(fact, wanted)}


@frappe.whitelist()
def sections(farm=None, filters=None):
    """Tiến độ, chích bắp, hủy buồng and thu hoạch of the report page."""
    ctx, wanted = _context(farm), _chosen(filters)
    tags = _tags(ctx.farm)
    facts = _ledger_facts(ctx, tags)
    pairs = _chosen_colours(facts, wanted)
    every = [l for l, _ in facts]
    kept = [l for l, f in facts if report_filters.keep(f, wanted)]
    phieu = _entry_facts(ctx, tags)
    entries = [e for e, _ in phieu if (e["farm_block"], e["bunch_tag"]) in pairs]
    entries_kept = [e for e, f in phieu if report_filters.keep(f, wanted)]
    waiting_ok = {l.name for l in kept if l.event_type == "Bud Injection"}
    waiting = [w for w in bunch_flow_rules.waiting_injections(every, block_forecast._bunch_params(block_forecast._profiles(ctx.farm)), nowdate()) if w["event"] in waiting_ok]
    reasons = {r.name: r.reason_name for r in frappe.get_all("Cancellation Reason", fields=["name", "reason_name"], limit_page_length=0)}
    first_cuts = {}
    for line in every:
        if line.event_type == "Cut Bud":
            key = (line.farm_block, line.bunch_tag)
            first_cuts[key] = min(first_cuts.get(key, line.event_date), line.event_date)
    cut_total = sum(int(l.qty) for l in kept if l.event_type == "Cut Bud")
    paired = [l for l in every if (l.farm_block, l.bunch_tag) in pairs]
    stock_now = rules.stock(paired, tags, ctx.blocks, _days_for(ctx.farm), nowdate())
    records = [(rules.STAGE_KEYS[l.event_type], dict(f, reason=reasons.get(l.reason, "")), int(l.qty), float(l.weight_kg or 0)) for l, f in facts if l.event_type in rules.STAGE_KEYS and report_filters.keep(f, wanted)]
    records += [(rules.STAGE_KEYS[e["event_type"]], f, int(round(float(e["qty"]))), 0.0) for e, f in phieu if report_filters.keep(f, wanted)]
    for card in stock_now["cards"]:
        when = report_filters.date_facts(card["first_cut"])
        records += [("left", dict(when, zone=lot["zone"], block=lot["code"], colour=card["colour"], lan=str(card["lan"] or "")), lot["left"], 0.0) for lot in card["lots"] if lot["left"]]
    return dict(_head(ctx), cube=rules.cube(records), options=report_filters.options([f for _, f in facts] + [f for _, f in phieu], wanted, BUNCH_FIELDS),
                dashboard=rules.dashboard(kept, entries_kept, ctx.blocks), stock=stock_now,
                cut_weeks=rules.cut_weeks([l for l in kept if l.event_type == "Cut Bud"], tags, ctx.blocks),
                progress=rules.progress(paired, entries, tags, ctx.blocks), injection=rules.injection(kept, waiting, ctx.blocks),
                rejects=rules.rejects(kept, cut_total, ctx.blocks, tags, reasons), harvest=rules.harvest(kept, first_cuts, tags, ctx.blocks))


@frappe.whitelist()
def cut_weeks(farm=None, filters=None):
    ctx, wanted = _context(farm), _chosen(filters)
    tags = _tags(ctx.farm)
    lines = [line for line, fact in _cut_facts(ctx, tags) if report_filters.keep(fact, wanted)]
    return dict(_head(ctx), weeks=rules.cut_weeks(lines, tags, ctx.blocks))


@frappe.whitelist()
def day_report(farm=None, zone=None, from_date=None, to_date=None):
    first, last = getdate(from_date or nowdate()), getdate(to_date or from_date or nowdate())
    if last < first or date_diff(last, first) > MAX_DAYS:
        frappe.throw(f"Khoảng ngày phải đúng thứ tự và không quá {MAX_DAYS} ngày.")
    ctx = _context(farm, zone)
    labels = {name: tag["label"] for name, tag in _tags(ctx.farm).items()}
    reasons = {r.name: r.reason_name for r in frappe.get_all("Cancellation Reason", fields=["name", "reason_name"], limit_page_length=0)}
    teams = {t.name: t.team_name.strip() for t in field._teams(ctx.farm)}
    lines = _lines(ctx, ("Draft", "Confirmed"), event_date=["between", [first, last]]) + _phieu_lines(ctx, first, last, ("Draft", "Sent", "Confirmed"))
    return dict(_head(ctx), from_date=str(first), to_date=str(last), **rules.day_report(lines, ctx.blocks, teams, labels, reasons))


def _phieu_lines(ctx, first=None, last=None, states=("Confirmed",)):
    """Bao buồng, tỉa and chống đổ lines of the sổ lô: the colour caps and the report need them next to the ledger stages."""
    filters = {"farm": ctx.farm, "stage": ["in", list(field.rules.CARE_STAGES)], "state": ["in", list(states)]}
    if first:
        filters["posting_date"] = ["between", [first, last]]
    rows = frappe.get_all(ENTRY, filters=filters, fields=["name", "farm_block", "work_team", "stage", "posting_date", "qty", "bunch_tag", "state"],
                          limit_page_length=0)
    return [{"name": r.name, "farm_block": r.farm_block, "work_team": r.work_team, "event_type": r.stage, "event_date": r.posting_date, "qty": r.qty,
             "bunch_tag": r.bunch_tag, "state": "Draft" if r.state == "Sent" else r.state} for r in rows]



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
        sheet.append([blocks[name]["code"], total_trees, all_cut, max(0, total_trees - all_cut), round(all_cut / total_trees * 100, 2) if total_trees else None, None] + cells + [row_total])
        grand += row_total
    sheet.append(["TỔNG", None, None, None, None, None] + column_totals + [grand])
    sheet.freeze_panes = "G4"


@frappe.whitelist()
def export_cut_book(farm=None, filters=None):
    """The ledger in the layout of the farm's Excel book, ten weeks to a sheet."""
    from openpyxl import Workbook
    ctx, wanted = _context(farm), _chosen(filters)
    tags = _tags(ctx.farm)
    weeks = rules.cut_weeks([line for line, fact in _cut_facts(ctx, tags) if report_filters.keep(fact, wanted)], tags, ctx.blocks)
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
    count, index = max(1, (len(weeks) + WEEKS_PER_SHEET - 1) // WEEKS_PER_SHEET), 0
    for index in range(count):
        mondays = [first + dt.timedelta(weeks=WEEKS_PER_SHEET * index + i) for i in range(WEEKS_PER_SHEET)]
        sheet = book.create_sheet(f"Tuần {mondays[0].isocalendar()[1]}-{mondays[-1].isocalendar()[1]}")
        _write_sheet(sheet, mondays[0].isocalendar()[0], mondays, by_week, ctx.blocks, cut, trees)
    out = BytesIO()
    book.save(out)
    frappe.local.response.filename = f"so-cat-bap-{ctx.farm}.xlsx"
    frappe.local.response.filecontent = out.getvalue()
    frappe.local.response.type = "download"
