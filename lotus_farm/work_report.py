"""Báo cáo công việc: chăm sóc vườn, BVTV and the packhouse. Read-only; the phiếu and the shifts remain the source. Chăm sóc buồng is in bunch_report."""
import frappe
from frappe.utils import nowdate

from lotus_farm import field_report as field
from lotus_farm import report_filter_rules as report_filters
from lotus_farm import work_report_rules as rules
from lotus_farm.bunch_report import _chosen, _context, _head
from lotus_farm.field_report_rules import FIELD_GROUP, PROTECTION

ENTRY = "Lotus Work Entry"
MATERIAL = "Lotus Work Entry Material"


WORK_FIELDS = ("year", "month", "week", "day", "zone", "block", "team", "work")
TIME_ONLY = ("year", "month", "week", "day")


def _work_summary(ctx, group, wanted):
    works = {w.name: {"name": w.work_name, "uom": w.uom} for w in frappe.get_all("Work Type", filters={"lotus_work_group": group}, fields=["name", "work_name", "uom"], limit_page_length=0)}
    all_entries = frappe.get_all(ENTRY, filters={"farm": ctx.farm, "work_type": ["in", list(works) or [""]]},
                                 fields=["name", "farm_block", "work_team", "work_type", "posting_date", "qty", "morning_people", "afternoon_people", "done", "notes"], order_by="posting_date asc", limit_page_length=0)
    teams = {t.name: t.team_name.strip() for t in field._teams(ctx.farm)}
    facts, entries = [], []
    for e in all_entries:
        block = ctx.blocks.get(e.farm_block)
        if not block:
            continue
        fact = dict(report_filters.date_facts(e.posting_date), zone=block["zone"], block=block["code"], team=teams.get(e.work_team, ""), work=works[e.work_type]["name"])
        facts.append(fact)
        if report_filters.keep(fact, wanted):
            entries.append(e)
    materials = {}
    if entries:
        for m in frappe.get_all(MATERIAL, filters={"parent": ["in", [e.name for e in entries]]}, fields=["parent", "item_code", "qty", "uom", "dose", "phi_days"], limit_page_length=0):
            materials.setdefault(m.parent, []).append(m)
    codes = {m.item_code for rows in materials.values() for m in rows}
    items = {i.name: i.item_name for i in frappe.get_all("Item", filters={"name": ["in", list(codes) or [""]]}, fields=["name", "item_name"], limit_page_length=0)}
    return rules.by_work(entries, materials, works, ctx.blocks, teams, items), facts


@frappe.whitelist()
def field_care(farm=None, filters=None):
    ctx, wanted = _context(farm), _chosen(filters)
    summary, facts = _work_summary(ctx, FIELD_GROUP, wanted)
    return dict(_head(ctx), options=report_filters.options(facts, wanted, WORK_FIELDS), **summary)


@frappe.whitelist()
def protection(farm=None, filters=None):
    """Spraying and fertiliser from the phiếu, sâu bệnh observed in the field, and the lô still under quarantine."""
    ctx, wanted = _context(farm), _chosen(filters)
    summary, facts = _work_summary(ctx, PROTECTION, wanted)
    seen, kept = frappe.get_all("Disease Observation", filters={"farm": ctx.farm, "docstatus": 1}, fields=["name", "farm_block", "disease", "posting_date", "affected_plants", "severity", "action_taken"],
                                order_by="posting_date asc", limit_page_length=0), []
    for row in seen:
        block = ctx.blocks.get(row.farm_block)
        if block:
            fact = dict(report_filters.date_facts(row.posting_date), zone=block["zone"], block=block["code"])
            facts.append(fact)
            if report_filters.keep(fact, wanted):
                kept.append(row)
    held = [r for r in frappe.get_all("Farm Block", filters={"name": ["in", list(ctx.blocks) or [""]], "lotus_quarantine_until": [">=", nowdate()]}, fields=["name", "lotus_quarantine_until"], limit_page_length=0)
            if report_filters.keep({"zone": ctx.blocks[r.name]["zone"], "block": ctx.blocks[r.name]["code"]}, wanted)]
    return dict(_head(ctx), options=report_filters.options(facts, wanted, WORK_FIELDS), **summary, quarantine=rules.quarantine([(r.name, r.lotus_quarantine_until) for r in held], ctx.blocks, nowdate()), diseases=rules.disease_summary(kept, ctx.blocks))


@frappe.whitelist()
def packhouse(farm=None, filters=None):
    """Ca đóng gói đã ghi. Packhouse staff read this without being part of the field teams, so the shift's own permission decides."""
    if not frappe.has_permission("Packhouse Shift", "read"):
        frappe.throw("Bạn không có quyền xem ca đóng gói.", frappe.PermissionError)
    wanted = _chosen(filters)
    conditions = {"docstatus": 1}
    if farm:
        conditions["farm"] = farm
    shifts = frappe.get_list("Packhouse Shift", filters=conditions, fields=["name", "shift_code", "posting_date", "labor", "input_kg", "finished_kg", "secondary_kg", "loss_kg", "cartons"], order_by="posting_date desc", limit_page_length=0)
    facts = [report_filters.date_facts(s.posting_date) for s in shifts]
    kept = [s for s, fact in zip(shifts, facts) if report_filters.keep(fact, wanted)]
    return dict(farm=farm or "", options=report_filters.options(facts, wanted, TIME_ONLY), **rules.packhouse(kept))
