"""The daily bunch sheet: tổ trưởng enter chích, cắt, loại and thu on many lô at once (Draft lines in the bunch ledger);
the đội trưởng confirms the day. Lines are per lô, day, việc, màu, lý do and tổ, and saving the sheet again replaces them.
A confirmed line is never edited: `amend` voids it with a reason and writes a new one."""
import frappe
from frappe.utils import cint, flt, getdate, now_datetime, nowdate

from lotus_farm import bunch_posting_rules as rules
from lotus_farm import field_report as field
from lotus_farm.controls import lock

EVENT = "Lotus Bunch Event"
ENTRY = "Lotus Work Entry"
REASON_GROUP = "BUONG"
DRAFT, CONFIRMED, VOIDED = "Draft", "Confirmed", "Voided"
FIELDS = ["name", "farm_block", "work_team", "cycle_no", "event_type", "event_date", "qty", "area_ha", "bunch_tag", "reject_stage",
          "reason", "weight_kg", "source_type", "source_name", "source_key", "state", "entered_by", "confirmed_by", "confirmed_at",
          "notes"]


def _store(doc):
    token = field._writing.set(True)
    try:
        doc.save(ignore_permissions=True)
    finally:
        field._writing.reset(token)


def _rights(farm, crew):
    field.require_farm(farm)
    rights = field.access(farm, crew)
    if not rights.read:
        frappe.throw("Bạn không thuộc đội này.", frappe.PermissionError)
    return rights


def _crew_blocks(farm, rights):
    return {name: b for name, b in field._block_map(farm).items() if b["zone"] in rights.zones}


def _reasons():
    group = frappe.db.get_value("Cancellation Reason Group", {"group_code": REASON_GROUP})
    return frappe.get_all("Cancellation Reason", filters={"reason_group": group or "", "active": 1},
                          fields=["name", "reason_name"], order_by="reason_name asc", limit_page_length=0)


def _key_of(row):
    return rules.row_key(row["farm_block"], row["event_date"], row["event_type"], row.get("bunch_tag"), row.get("reason"), row["work_team"])


def _day_rows(farm, day, teams):
    """The live sheet lines of a day for some tổ."""
    if not teams:
        return []
    rows = frappe.get_all(EVENT, filters={"farm": farm, "event_date": day, "state": ["!=", VOIDED], "work_team": ["in", list(teams)]},
                          fields=FIELDS, order_by="creation asc", limit_page_length=0)
    for r in rows:
        r["event_date"] = str(r["event_date"])
    return rows


def _ledger(farm, tags, states=(DRAFT, CONFIRMED)):
    tags = [t for t in set(tags) if t]
    if not tags:
        return []
    return frappe.get_all(EVENT, filters={"farm": farm, "bunch_tag": ["in", tags], "state": ["in", list(states)]},
                          fields=["name", "farm_block", "bunch_tag", "event_type", "reject_stage", "qty"], limit_page_length=0)


def _tag_label(farm):
    return {t.name: t.color_label or t.name for t in frappe.get_all("Bunch Tag", filters={"farm": farm}, fields=["name", "color_label"],
                                                                     limit_page_length=0)}


def _cap_message(blocks, labels, key, value):
    block = blocks.get(key[0], {}).get("block_code", key[0])
    return f"{block} màu {labels.get(key[1], key[1])}: thu hoạch và hủy sau cắt là {value[1]}, vượt số đã cắt bắp {value[0]}."


def _team_names(farm):
    return {t.name: t.team_name for t in field._teams(farm)}


def _user_names(users):
    return field._user_names([u for u in set(users) if u])


@frappe.whitelist()
def day_sheet(farm, crew, date=None):
    """Everything a tổ trưởng (their tổ) or đội trưởng (all tổ) needs to enter or confirm one day."""
    day = str(getdate(date or nowdate()))
    rights = _rights(farm, crew)
    blocks = _crew_blocks(farm, rights)
    cycles = dict(frappe.get_all("Farm Block", filters={"name": ["in", list(blocks) or [""]]},
                                 fields=["name", "lotus_current_cycle_no"], as_list=True))
    names = _team_names(farm)
    teams = sorted(rights.teams, key=lambda t: names.get(t, t))
    today_tag = field.ribbon(farm, day)
    tags = field._ribbon_tags(farm, day)
    balance = rules.cut_balance(_ledger(farm, [t.name for t in tags]))
    rows = _day_rows(farm, day, rights.teams)
    people = _user_names([r.entered_by for r in rows])
    labels = _tag_label(farm)
    reasons = _reasons()
    reason_names = {r.name: r.reason_name for r in reasons}
    for r in rows:
        block = blocks.get(r.farm_block) or {}
        r.update(block_code=block.get("block_code", r.farm_block), team_name=names.get(r.work_team, r.work_team),
                 entered_name=people.get(r.entered_by, r.entered_by or ""), ribbon=labels.get(r.bunch_tag, ""),
                 reason_name=reason_names.get(r.reason, ""))
    return {"date": day, "farm": farm, "crew": crew, "user": frappe.session.user,
            "blocks": [{"name": b["name"], "code": b["block_code"], "zone": b["zone"], "trees": b["trees"],
                        "cycle": cint(cycles.get(b["name"]))} for b in blocks.values()],
            "ribbon": today_tag and {"name": today_tag.name, "label": today_tag.color_label or today_tag.display_name,
                                     "code": today_tag.color_code, "week": today_tag.week_number},
            "tags": [{"name": t.name, "label": t.color_label or t.display_name, "code": t.color_code, "week": t.week_number} for t in tags],
            "reasons": reasons, "teams": [{"name": t, "label": names.get(t, t)} for t in teams], "rows": rows,
            "suckers": _pending_suckers(farm, crew, day, blocks) if rights.supervisor else [],
            "cut_left": {f"{b}|{t}": cut - used for (b, t), (cut, used) in balance.items()},
            "rights": {"supervisor": rights.supervisor, "manager": rights.manager}}


@frappe.whitelist(methods=["POST"])
def save_day(farm, crew, date, team, rows=None):
    """Replace a tổ's unconfirmed lines of one day. All or nothing: any bad line stops the save and is reported."""
    day = str(getdate(date))
    if getdate(day) > getdate(nowdate()):
        frappe.throw("Không nhập cho ngày tương lai.")
    rights = _rights(farm, crew)
    if team not in rights.teams:
        frappe.throw("Bạn chỉ nhập cho tổ của mình.", frappe.PermissionError)
    lock("Farm", farm)
    blocks = _crew_blocks(farm, rights)
    today_tag = field.ribbon(farm, day)
    allowed_tags = set(frappe.get_all("Bunch Tag", filters={"farm": farm}, pluck="name"))
    allowed_reasons = {r.name for r in _reasons()}
    live = {_key_of(r): r for r in _day_rows(farm, day, [team]) if r.source_type == "Manual"}
    wanted, errors = {}, []

    for index, row in enumerate(frappe.parse_json(rows) or []):
        block = blocks.get(row.get("block"))
        label = block["block_code"] if block else str(row.get("block") or "")
        try:
            if not block:
                raise rules.RowError("Lô không thuộc đội này.")
            clean = rules.clean_row(row, today_tag.name if today_tag else None)
            if clean["bunch_tag"] and clean["bunch_tag"] not in allowed_tags:
                raise rules.RowError("Màu dây không thuộc vườn này.")
            if clean["reason"] and clean["reason"] not in allowed_reasons:
                raise rules.RowError("Lý do không có trong danh mục.")
            clean.update(farm_block=block["name"], event_date=day, work_team=team)
            key = _key_of(clean)
            if key in wanted:
                raise rules.RowError("Trùng dòng trong bảng; gộp số vào một dòng.")
            existing = live.get(key)
            if existing and existing.state == CONFIRMED and not _same(existing, clean):
                raise rules.RowError("Dòng này đã xác nhận; nhờ đội trưởng sửa có lý do.")
            wanted[key] = clean
        except rules.RowError as e:
            errors.append({"index": index, "block": label, "message": str(e)})

    errors += _save_cap_errors(farm, blocks, live, wanted)
    if errors:
        return {"saved": 0, "removed": 0, "errors": errors}

    saved = removed = 0
    for key, clean in wanted.items():
        existing = live.get(key)
        if existing and (existing.state == CONFIRMED or _same(existing, clean)):
            continue
        if existing:
            doc = frappe.get_doc(EVENT, existing.name, for_update=True)
        else:
            doc = frappe.new_doc(EVENT)
            doc.update(dict(clean, farm=farm, source_type="Manual", source_key=_free_key(key), state=DRAFT,
                            cycle_no=_cycle(clean["farm_block"])))
        doc.update({"qty": clean["qty"], "weight_kg": clean["weight_kg"], "entered_by": frappe.session.user})
        _store(doc)
        saved += 1
    for key, existing in live.items():
        if existing.state == DRAFT and key not in wanted:
            frappe.delete_doc(EVENT, existing.name, ignore_permissions=True, force=True)
            removed += 1
    return {"saved": saved, "removed": removed, "errors": []}


def _same(existing, clean):
    return cint(existing.qty) == clean["qty"] and flt(existing.weight_kg) == flt(clean["weight_kg"])


def _free_key(key):
    """A voided line keeps its key, so a new line for the same lô and colour needs its own."""
    candidate, n = key, 1
    while frappe.db.exists(EVENT, {"source_key": candidate}):
        n += 1
        candidate = f"{key}:{n}"
    return candidate


def _cycle(block):
    cycle = cint(frappe.db.get_value("Farm Block", block, "lotus_current_cycle_no"))
    if cycle < 1:
        code = frappe.db.get_value("Farm Block", block, "block_code")
        frappe.throw(f"Lô {code} chưa có vụ hiện tại trong danh mục lô.")
    return cycle


def _save_cap_errors(farm, blocks, live, wanted):
    """Would the sheet, once saved, leave thu hoạch + loại above cắt bắp? Drafts count: they are the tổ's own numbers."""
    tags = {c["bunch_tag"] for c in wanted.values() if rules.uses_cut(c)}
    if not tags:
        return []
    replaced = {r.name for r in live.values() if r.state == DRAFT}
    confirmed = {key for key, r in live.items() if r.state == CONFIRMED}
    rows = [r for r in _ledger(farm, tags) if r.name not in replaced]
    rows += [c for key, c in wanted.items() if key not in confirmed]
    labels = _tag_label(farm)
    touched = {(c["farm_block"], c["bunch_tag"]) for c in wanted.values() if rules.uses_cut(c)}
    return [{"index": None, "block": blocks.get(key[0], {}).get("block_code", key[0]), "message": _cap_message(blocks, labels, key, value)}
            for key, value in rules.over_cut(rows).items() if key in touched]


def _pending_suckers(farm, crew, day, blocks):
    """Chọn F reported on phiếu this day, still to be written to the ledger (new, or changed since it was confirmed)."""
    stages = field._stages(farm)
    works = [w for w, stage in stages.items() if rules.event_for_stage(stage) == rules.SUCKER]
    if not works:
        return []
    entries = frappe.get_all(ENTRY, filters={"farm": farm, "crew": crew, "posting_date": day, "work_type": ["in", works]},
                             fields=["name", "farm_block", "work_team", "qty", "entered_by", "posted_event"], limit_page_length=0)
    posted = {e.posted_event for e in entries if e.posted_event}
    # A line voided on purpose keeps its area, so the same report is not written back.
    areas = dict(frappe.get_all(EVENT, filters={"name": ["in", list(posted) or [""]]}, fields=["name", "area_ha"], as_list=True))
    pending = [e for e in entries if flt(e.qty) > 0 and flt(areas.get(e.posted_event), 6) != flt(e.qty, 6)]
    names = _team_names(farm)
    people = _user_names([e.entered_by for e in pending])
    for e in pending:
        block = blocks.get(e.farm_block) or {}
        e.update(block_code=block.get("block_code", e.farm_block), team_name=names.get(e.work_team, e.work_team),
                 entered_name=people.get(e.entered_by, e.entered_by or ""),
                 estimate=rules.sucker_estimate(block.get("trees"), e.qty, block.get("area_ha")))
    return pending


@frappe.whitelist(methods=["POST"])
def confirm_day(farm, crew, date):
    """Đội trưởng confirms the tổ's lines of a day. A line the confirmer entered, or that breaks the cut cap, stays Draft and is reported."""
    day = str(getdate(date))
    rights = _rights(farm, crew)
    if not rights.supervisor:
        frappe.throw("Chỉ đội trưởng của đội (hoặc quản lý vườn) xác nhận.", frappe.PermissionError)
    lock("Farm", farm)
    user = frappe.session.user
    blocks = _crew_blocks(farm, rights)
    labels = _tag_label(farm)
    errors, batch = [], []
    for row in _day_rows(farm, day, rights.members):
        if row.state != DRAFT:
            continue
        if rules.can_confirm(row.entered_by, user):
            batch.append(row)
        else:
            errors.append({"block": blocks.get(row.farm_block, {}).get("block_code", row.farm_block),
                           "message": f"{rules.LABELS[row.event_type]}: bạn đã tự nhập dòng này, cần người khác xác nhận."})

    tags = {r.bunch_tag for r in batch if r.bunch_tag}
    beyond = rules.over_cut(_ledger(farm, tags, (CONFIRMED,)) + batch)
    for key, value in beyond.items():
        errors.append({"block": blocks.get(key[0], {}).get("block_code", key[0]), "message": _cap_message(blocks, labels, key, value)})
    now = now_datetime()
    confirmed = 0
    for row in batch:
        if rules.uses_cut(row) and (row.farm_block, row.bunch_tag) in beyond:
            continue
        doc = frappe.get_doc(EVENT, row.name, for_update=True)
        doc.update({"state": CONFIRMED, "confirmed_by": user, "confirmed_at": now})
        _store(doc)
        confirmed += 1
    suckers, sucker_errors = _post_suckers(farm, crew, day, blocks, user, now)
    touched = {r.farm_block for r in batch if r.event_type in (rules.INJECT, rules.CUT)}
    warnings = [a for a in _anomalies(farm, blocks, day) if a["kind"] in ("inject", "cut") and a["lot"] in touched]
    return {"confirmed": confirmed, "suckers": suckers, "errors": errors + sucker_errors, "warnings": warnings}


def _anomalies(farm, blocks, day):
    flowers = dict(frappe.get_all("Farm Block", filters={"name": ["in", list(blocks) or [""]]}, fields=["name", "lotus_estimated_flowering_date"], as_list=True))
    cycles = dict(frappe.get_all("Farm Block", filters={"name": ["in", list(blocks) or [""]]}, fields=["name", "lotus_current_cycle_no"], as_list=True))
    totals = {}
    for r in frappe.get_all(EVENT, filters={"farm": farm, "farm_block": ["in", list(blocks) or [""]], "state": ["!=", VOIDED], "event_type": ["in", [rules.INJECT, rules.CUT, rules.REJECT, rules.HARVEST]]},
                            fields=["farm_block", "cycle_no", "event_type", "reject_stage", "qty"], limit_page_length=0):
        if r.cycle_no != cycles.get(r.farm_block):
            continue
        slot = totals.setdefault(r.farm_block, {"inject": 0, "cut": 0, "used": 0})
        if r.event_type == rules.INJECT:
            slot["inject"] += r.qty
        elif r.event_type == rules.CUT:
            slot["cut"] += r.qty
        elif rules.uses_cut(r):
            slot["used"] += r.qty
    by_code = {b["block_code"]: name for name, b in blocks.items()}
    found = rules.anomalies([dict(totals.get(name, {}), code=b["block_code"], trees=b["trees"], flower_date=getdate(flowers[name]) if flowers.get(name) else None) for name, b in blocks.items()], getdate(day))
    return [dict(a, lot=by_code[a["block"]]) for a in found]


@frappe.whitelist()
def day_status(farm, crew, date=None):
    """The morning list for the đội trưởng and quản lý vườn: lines still to confirm, lô with no number that day, numbers that look wrong."""
    day = str(getdate(date or nowdate()))
    rights = _rights(farm, crew)
    if not rights.supervisor:
        frappe.throw("Chỉ đội trưởng của đội (hoặc quản lý vườn) xem danh sách này.", frappe.PermissionError)
    blocks = _crew_blocks(farm, rights)
    pending = len([r for r in _day_rows(farm, day, rights.members) if r.state == DRAFT]) + len(_pending_suckers(farm, crew, day, blocks))
    tickets = frappe.get_all(field.ASSIGNMENT, filters={"farm": farm, "crew": crew, "kind": field.rules.ROUND, "state": ["in", list(field.OPEN_STATES)], "assigned_on": ["<=", day]},
                             fields=["farm_block", "work_team"], limit_page_length=0)
    reported = {e.farm_block for e in frappe.get_all(ENTRY, filters={"farm": farm, "crew": crew, "posting_date": day}, fields=["farm_block"], limit_page_length=0)}
    reported |= {r.farm_block for r in _day_rows(farm, day, rights.members)}
    names = _team_names(farm)
    silent = rules.not_reported([(t.farm_block, t.work_team) for t in tickets if t.farm_block in blocks], reported)
    missing = sorted(({"block": blocks[b]["block_code"], "team": names.get(team, team or "")} for b, team in silent.items()), key=lambda r: (len(r["block"]), r["block"]))
    return {"date": day, "pending": pending, "not_reported": missing, "anomalies": [{k: a[k] for k in ("block", "kind", "message")} for a in _anomalies(farm, blocks, day)]}


def _post_suckers(farm, crew, day, blocks, user, now):
    """Write each pending Chọn F to the ledger. A report changed after confirmation replaces its old line."""
    posted, errors = 0, []
    for entry in _pending_suckers(farm, crew, day, blocks):
        block = blocks.get(entry.farm_block) or {}
        code = block.get("block_code", entry.farm_block)
        if not rules.can_confirm(entry.entered_by, user):
            errors.append({"block": code, "message": "Chọn chồi: bạn đã tự báo phiếu này, cần người khác xác nhận."})
            continue
        if not entry.estimate:
            errors.append({"block": code, "message": "Chọn chồi: lô chưa có số cây hoặc diện tích."})
            continue
        if entry.posted_event:
            old = frappe.get_doc(EVENT, entry.posted_event, for_update=True)
            if old.state == CONFIRMED:
                old.update({"state": VOIDED, "void_reason": "Báo cáo ngày đã sửa diện tích."})
                _store(old)
        current = _cycle(entry.farm_block)
        bud_work = frappe.db.exists(EVENT, {"farm_block": entry.farm_block, "cycle_no": current, "state": ["!=", VOIDED],
                                            "event_type": ["in", [rules.INJECT, rules.CUT]]})
        doc = frappe.new_doc(EVENT)
        doc.update({"farm": farm, "farm_block": entry.farm_block, "work_team": entry.work_team, "cycle_no": rules.sucker_cycle(current, bool(bud_work)),
                    "event_type": rules.SUCKER, "event_date": day, "qty": entry.estimate, "area_ha": flt(entry.qty), "source_type": "Work Entry",
                    "source_name": entry.name, "source_key": _free_key("work-entry:" + entry.name), "state": CONFIRMED,
                    "entered_by": entry.entered_by, "confirmed_by": user, "confirmed_at": now})
        _store(doc)
        frappe.db.set_value(ENTRY, entry.name, {"posted_event": doc.name, "confirmed_by": user, "confirmed_at": now}, update_modified=False)
        posted += 1
    return posted, errors


@frappe.whitelist(methods=["POST"])
def amend(event, values=None, reason=None):
    """Correct a confirmed line: void it with a reason and, unless the new number is 0, write the corrected line."""
    doc = frappe.get_doc(EVENT, event, for_update=True)
    crew = frappe.db.get_value("Work Team", doc.work_team, "lotus_parent_team") if doc.work_team else None
    if not crew:
        frappe.throw("Dòng này chưa gắn đội nên không sửa được ở đây.")
    rights = _rights(doc.farm, crew)
    if not rights.supervisor:
        frappe.throw("Chỉ đội trưởng của đội (hoặc quản lý vườn) sửa số đã xác nhận.", frappe.PermissionError)
    reason = str(reason or "").strip()
    if not reason:
        frappe.throw("Sửa số đã xác nhận phải ghi lý do.")
    if doc.state != CONFIRMED:
        frappe.throw("Chỉ sửa được dòng đã xác nhận; dòng nháp sửa ngay trên bảng nhập.")
    lock("Farm", doc.farm)
    values = frappe.parse_json(values) or {}
    remove = str(values.get("qty")) == "0"
    clean = None if remove else _amended(doc, values)
    if clean:
        same_key = rules.row_key(doc.farm_block, str(doc.event_date), doc.event_type, clean["bunch_tag"], clean["reason"], doc.work_team)
        if doc.event_type != rules.SUCKER and any(_key_of(r) == same_key and r.name != doc.name
                                                  for r in _day_rows(doc.farm, str(doc.event_date), [doc.work_team])):
            frappe.throw("Đã có dòng cùng lô, việc, màu và lý do trong ngày; sửa dòng đó.")
    _amend_cap(doc, clean)
    doc.update({"state": VOIDED, "void_reason": reason[:140]})
    _store(doc)
    if remove:
        return {"voided": doc.name, "event": None}
    new = frappe.new_doc(EVENT)
    new.update({"farm": doc.farm, "farm_block": doc.farm_block, "work_team": doc.work_team, "cycle_no": doc.cycle_no, "event_type": doc.event_type,
                "event_date": doc.event_date, "area_ha": doc.area_ha, "source_type": doc.source_type, "source_name": doc.source_name,
                "source_key": _free_key("amend:" + doc.name), "state": CONFIRMED, "entered_by": doc.entered_by,
                "confirmed_by": frappe.session.user, "confirmed_at": now_datetime(), "notes": "Sửa: " + reason[:120]})
    new.update(clean)
    _store(new)
    if doc.source_type == "Work Entry" and doc.source_name:
        frappe.db.set_value(ENTRY, doc.source_name, "posted_event", new.name, update_modified=False)
    return {"voided": doc.name, "event": new.name}


def _amended(doc, values):
    if doc.event_type == rules.SUCKER:
        qty = rules.whole_number(values.get("qty", doc.qty))
        if qty is None:
            frappe.throw("Số chồi phải là số nguyên lớn hơn 0.")
        return {"qty": qty, "bunch_tag": None, "reason": None, "reject_stage": None, "weight_kg": 0}
    merged = {"event_type": doc.event_type, "qty": doc.qty, "bunch_tag": doc.bunch_tag, "reason": doc.reason, "reject_stage": doc.reject_stage,
              "weight_kg": doc.weight_kg}
    merged.update({k: values[k] for k in ("qty", "bunch_tag", "reason", "reject_stage", "weight_kg") if k in values})
    try:
        clean = rules.clean_row(merged, doc.bunch_tag)
    except rules.RowError as e:
        frappe.throw(str(e))
    clean.pop("event_type")
    if clean["reason"] and clean["reason"] not in {r.name for r in _reasons()}:
        frappe.throw("Lý do không có trong danh mục.")
    return clean


def _amend_cap(doc, clean):
    """A correction may neither push thu + loại above cắt, nor bring cắt below what was already used."""
    tags = {doc.bunch_tag, clean and clean["bunch_tag"]} - {None, ""}
    if not tags:
        return
    rows = [r for r in _ledger(doc.farm, tags, (CONFIRMED,)) if r.name != doc.name]
    if clean:
        rows.append(dict(clean, farm_block=doc.farm_block, event_type=doc.event_type))
    block = doc.farm_block
    beyond = {key: value for key, value in rules.over_cut(rows).items() if key[0] == block and key[1] in tags}
    if beyond:
        key, value = next(iter(beyond.items()))
        blocks = {block: {"block_code": frappe.db.get_value("Farm Block", block, "block_code")}}
        frappe.throw(_cap_message(blocks, _tag_label(doc.farm), key, value))
