"""Frozen copies of the weekly forecast, and how they compare with what was harvested. Nothing here changes the parameters in force.

A weekly copy stands for 0 giờ of its Monday: the sổ lô as it was then (lines confirmed before, not voided before) and
the parameter sets approved by then. There is no scheduler on the server: the first person to open the app in a week
queues ensure_all, which builds every copy still missing (up to eight weeks back). A unique key per farm and Monday
keeps it to one copy even when two sessions start together.
"""
import json

import frappe
from frappe.utils import getdate, now_datetime, nowdate

from lotus_farm import block_forecast, bunch_forecast_engine
from lotus_farm import field_report as field
from lotus_farm.lot_ledger import ENTRY, bunch_rows
from lotus_farm import forecast_snapshot_rules as rules
from lotus_farm.forecast_parameters import DEFAULTS, validate

SNAPSHOT = "Lotus Forecast Snapshot"


LIMITS = ("Dựng lại theo sổ lô lúc 0 giờ thứ Hai. Số cây, ngày trổ ước tính và lô đang hoạt động lấy giá trị lúc dựng, "
          "không phải giá trị của ngày đó.")
WEEKS_CACHE = "lotus_forecast_weeks"
MAX_VARIANCE_WEEKS = 104


def _write(farm, kind, as_of=None):
    """A copy of the forecast now (Manual), or as of a Monday 00:00 (Weekly)."""
    day = as_of.date() if as_of else getdate(nowdate())
    summary, cohorts = block_forecast.bunch_summary(farm, as_of=as_of)
    refs = sorted({c["profile"] for c in cohorts if c["profile"]})
    monday = rules.monday_of(day)
    doc = frappe.new_doc(SNAPSHOT)
    doc.update({"farm": farm, "snapshot_date": day, "week_label": bunch_forecast_engine.week_key(day), "kind": kind,
                "week_start": monday if kind == "Weekly" else None, "as_of": as_of or now_datetime(),
                "weekly_key": f"{farm}:{monday}" if kind == "Weekly" else None, "limits": LIMITS if kind == "Weekly" else None,
                "profile_refs": json.dumps(refs), "total_bunches": summary["totals"]["bunches"], "total_kg": summary["totals"]["kg"],
                "rows_json": json.dumps(bunch_forecast_engine.snapshot_rows(summary), ensure_ascii=False)})
    field._store(doc)
    return doc


def _require(farm, manager=False):
    field.require_farm(farm)
    if manager and not field.is_manager():
        frappe.throw("Chỉ quản lý vườn chốt bản dự thu.", frappe.PermissionError)


@frappe.whitelist(methods=["POST"])
def create(farm):
    _require(farm, manager=True)
    doc = _write(farm, "Manual")
    return {"name": doc.name, "snapshot_date": str(doc.snapshot_date), "total_bunches": doc.total_bunches, "total_kg": doc.total_kg}


def _first_confirmed(farm):
    return frappe.db.sql(f"""select min(confirmed_at) from `tab{ENTRY}` where farm = %s and state in ('Confirmed', 'Voided')
                             and ifnull(stage, '') != '' and confirmed_at is not null""", farm)[0][0]


def ensure_weeks(farm):
    """Build every weekly copy of this farm still missing, oldest first. Another session building the same week wins."""
    have = frappe.get_all(SNAPSHOT, filters={"farm": farm, "kind": "Weekly", "week_start": ["is", "set"]}, pluck="week_start")
    built = []
    for monday in rules.weeks_to_build(_first_confirmed(farm), have, nowdate()):
        if frappe.db.exists(SNAPSHOT, {"weekly_key": f"{farm}:{monday}"}):
            continue
        frappe.db.savepoint("weekly_copy")
        try:
            _write(farm, "Weekly", as_of=rules.week_moment(monday))
        except (frappe.UniqueValidationError, frappe.DuplicateEntryError):
            frappe.db.rollback(save_point="weekly_copy")
            frappe.clear_messages()
            continue
        built.append(str(monday))
    return built


def ensure_all():
    """Every farm with a sổ lô. Runs in the background; remembered for the week once done. The copy is the farm's, not
    the view of whoever's login queued it, so it is built with full rights."""
    frappe.set_user("Administrator")
    monday = str(rules.monday_of(nowdate()))
    farms = sorted({r.farm for r in frappe.get_all(ENTRY, filters={"stage": ["is", "set"], "state": "Confirmed"}, fields=["farm"], distinct=True,
                                                    limit_page_length=0)})
    built = {}
    for farm in farms:
        try:
            built[farm] = ensure_weeks(farm)
            frappe.db.commit()
        except Exception:
            frappe.db.rollback()
            frappe.log_error(title=f"Bản chốt dự thu tuần {monday}: {farm}")
    if all(farm in built for farm in farms):
        frappe.cache.set_value(WEEKS_CACHE, monday, expires_in_sec=8 * 24 * 3600)
    return built


def weekly():
    """Scheduler hook, where a scheduler runs."""
    ensure_all()


def queue_missing_weeks():
    """Called when a session starts: queue ensure_all once a week. Never stops the app from opening."""
    try:
        monday = str(rules.monday_of(nowdate()))
        if frappe.cache.get_value(WEEKS_CACHE) == monday:
            return
        frappe.enqueue("lotus_farm.forecast_snapshot.ensure_all", queue="short", job_id=f"lotus-forecast-weeks-{monday}", deduplicate=True,
                       enqueue_after_commit=False)
    except Exception:
        frappe.log_error(title="Không xếp được việc dựng bản chốt dự thu")


def _snapshots(farm):
    return frappe.get_all(SNAPSHOT, filters={"farm": farm}, fields=["name", "snapshot_date", "week_label", "week_start", "kind", "total_bunches", "total_kg", "rows_json", "profile_refs"],
                          order_by="snapshot_date asc, creation asc", limit_page_length=0)


def _forecast_for(snapshots, week):
    """What we believed when the week began: that week's own weekly copy, else the latest copy frozen no later than its Monday."""
    monday = rules.week_monday(week)
    own = [s for s in snapshots if s.kind == "Weekly" and s.week_start and getdate(s.week_start) == monday]
    if own:
        return own[-1]
    chosen = None
    for s in snapshots:
        if getdate(s.snapshot_date) <= monday:
            chosen = s
    return chosen


def _actual_rows(farm, first, last):
    rows = bunch_rows({"farm": farm, "state": "Confirmed", "event_type": "Harvest", "event_date": ["between", [first, last]]},
                      ["farm_block", "bunch_tag", "event_date", "qty", "weight_kg"])
    labels = frappe._dict({t.name: t.color_label for t in frappe.get_all("Bunch Tag", filters={"farm": farm}, fields=["name", "color_label"], limit_page_length=0)})
    codes = {b.name: b.block_code for b in frappe.get_all("Farm Block", filters={"farm": farm}, fields=["name", "block_code"], limit_page_length=0)}
    return [{"week": rules.week_key(r.event_date), "block": r.farm_block, "block_code": codes.get(r.farm_block, ""), "tag": r.bunch_tag, "ribbon": labels.get(r.bunch_tag, ""), "bunches": r.qty, "kg": r.weight_kg}
            for r in rows]


@frappe.whitelist()
def variance(farm, from_week, to_week, group_by="week"):
    """Forecast against harvest, week by week. Only weeks that had a frozen copy before they began are compared."""
    _require(farm)
    snapshots = _snapshots(farm)
    first, last = rules.week_monday(from_week), rules.week_monday(to_week)
    if last < first or (last - first).days > MAX_VARIANCE_WEEKS * 7:
        frappe.throw(f"Chọn khoảng tuần hợp lệ, tối đa {MAX_VARIANCE_WEEKS} tuần.")
    forecast, used, cursor, weeks = [], {}, first, []
    while cursor <= last:
        week = rules.week_key(cursor)
        weeks.append(week)
        chosen = _forecast_for(snapshots, week)
        if chosen:
            used[week] = {"name": chosen.name, "date": str(chosen.snapshot_date)}
            forecast += [r for r in json.loads(chosen.rows_json or "[]") if r["week"] == week]
        cursor = frappe.utils.add_days(cursor, 7)
        cursor = getdate(cursor)
    actual = [r for r in _actual_rows(farm, first, frappe.utils.add_days(last, 6)) if r["week"] in used]
    return {"rows": rules.compare(forecast, actual, group_by), "weeks": weeks, "snapshots": used, "group_by": group_by, "has_snapshot": bool(snapshots),
            "packout": _packout(farm, first, frappe.utils.add_days(last, 6))}


def _packout(farm, first, last):
    """What the xưởng made of the bunches, week by week, from closed shifts: kg and cartons per bunch, pack-out rate."""
    rows = frappe.db.sql("""select p.posting_date, sum(s.bunches) as bunches, sum(s.kg) as kg from `tabPackhouse Shift Source` s
                            join `tabPackhouse Shift` p on p.name = s.parent where p.farm = %s and p.docstatus = 1
                            and p.posting_date between %s and %s group by p.name, p.posting_date""", (farm, first, last), as_dict=True)
    shifts = {r.name: r for r in frappe.get_all("Packhouse Shift", filters={"farm": farm, "docstatus": 1, "posting_date": ["between", [first, last]]},
                                                 fields=["name", "posting_date", "finished_kg", "cartons"], limit_page_length=0)}
    weeks = {}
    for r in rows:
        w = weeks.setdefault(rules.week_key(r.posting_date), {"bunches": 0, "kg": 0.0, "finished_kg": 0.0, "cartons": 0})
        w["bunches"] += int(r.bunches or 0)
        w["kg"] += float(r.kg or 0)
    for s in shifts.values():
        w = weeks.setdefault(rules.week_key(s.posting_date), {"bunches": 0, "kg": 0.0, "finished_kg": 0.0, "cartons": 0})
        w["finished_kg"] += float(s.finished_kg or 0)
        w["cartons"] += int(s.cartons or 0)
    for w in weeks.values():
        w["kg_per_bunch"] = round(w["kg"] / w["bunches"], 2) if w["bunches"] else None
        w["cartons_per_bunch"] = round(w["cartons"] / w["bunches"], 2) if w["bunches"] else None
        w["packout_percent"] = round(w["finished_kg"] / w["kg"] * 100, 1) if w["kg"] else None
    return weeks


@frappe.whitelist()
def suggest_parameters(farm, block=None):
    """Numbers measured from finished colours, next to those in force. Applied only when someone approves a new set of parameters."""
    _require(farm)
    filters = {"farm": farm, "state": "Confirmed", "event_type": ["in", ["Cut Bud", "Harvest", "Reject"]]}
    if block:
        filters["farm_block"] = block
    lines = bunch_rows(filters, ["farm_block", "bunch_tag", "event_type", "event_date", "qty", "weight_kg", "reject_stage"])
    result = rules.suggest(rules.colour_results(lines, nowdate()), validate(DEFAULTS))
    return dict(result, applied=False)
