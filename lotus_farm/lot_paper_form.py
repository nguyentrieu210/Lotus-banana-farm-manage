"""Phiếu giấy của tổ-ngày và đọc ảnh phiếu (spec 002, US1 phần sau).

form_url (POST) opens the tổ's report of the day, fixes the layout of its paper form (columns with short codes, rows of
the lô given to the tổ) in the report's machine_draft and returns the print page. read_photo (POST) sends a photo of the
filled form to the model (document_ai, same key and hourly limit), checks the cells with fixed rules
(lot_paper_form_rules) and writes them as Draft lines marked machine_read with review_flags. Nothing machine-read can be
sent until someone opens the lô, checks it and saves it (that clears the flags); a lô that already has lines entered by
hand keeps them and its cells are only listed as notes.
"""
import json

import frappe
from frappe.utils import cint, flt, getdate, now_datetime

from lotus_farm import document_ai
from lotus_farm import field_report as field
from lotus_farm import lot_ledger
from lotus_farm import lot_ledger_rules as rules
from lotus_farm import lot_paper_form_rules as paper
from lotus_farm import lot_report as lr
from lotus_farm.controls import lock

PRINT_ROUTE = "/lotus/in-phieu-ngay"
PROMPT = """Ảnh chụp một PHIẾU BÁO CÁO NGÀY của một tổ làm vườn chuối: phiếu in sẵn, người ta viết tay số vào ô.
Phiếu là một bảng: mỗi hàng là một lô (cột đầu in mã lô, ví dụ A5); mỗi cột có mã in ở đầu cột (C1, C2, ...).
Các cột của phiếu này:
__COLUMNS__
Các lô in trên phiếu: __ROWS__.
Mã báo cáo in ở góc trên bên phải phiếu: __REPORT__.
Chỉ đọc những ô có viết tay. Với mỗi ô có viết:
- "lot": mã lô in ở đầu hàng,
- "col": mã cột in ở đầu cột,
- "qty": số viết trong ô (số buồng, hoặc khối lượng việc), null nếu ô chỉ có dấu xong,
- "kg": số kg nếu ô thu hoạch có ghi kg, ngược lại null,
- "done": true nếu ô có dấu xong cả lô (✓, X) ở phần "xong", ngược lại false.
Không đoán số không đọc rõ; bỏ qua ô trống. Không thêm lô hay cột không in trên phiếu.
Chỉ trả về JSON đúng dạng: {"report": "<mã báo cáo đọc được>", "cells": [{"lot": "A5", "col": "C1", "qty": 12, "kg": null, "done": false}]}"""


def _draft(doc):
    try:
        return json.loads(doc.machine_draft or "{}") or {}
    except ValueError:
        return {}


def _form(doc):
    """The layout of the report's paper form, from what the tổ is given on the day."""
    data = lr.today(doc.farm, doc.work_team, str(doc.report_date))
    works = {w["name"]: {"label": w["label"], "stage": w["stage"] or "", "uom": w.get("uom") or ""} for w in data["works"]}
    lots = [{"block": l["block"], "code": l["code"], "zone": l["zone"],
             "rounds": [a["work_type"] for a in l["assignments"] if a["kind"] == field.rules.ROUND and a.get("work_type")]}
            for l in data["lots"] if l["active"]]
    ribbon = data.get("ribbon") or {}
    form = paper.layout(lots, works, ribbon.get("label"))
    form["ribbon"] = {"label": ribbon.get("label") or "", "code": ribbon.get("code") or "", "week": ribbon.get("week")}
    return form


@frappe.whitelist(methods=["POST"])
def form_url(farm, team, date=None):
    """Open (or create) the tổ's report of the day and fix the layout of its paper form; the print page reads it."""
    report = lr.open_report(farm, team, date)
    doc = frappe.get_doc(lr.REPORT, report["name"])
    draft = _draft(doc)
    draft.update(form=_form(doc), printed_at=str(now_datetime()), printed_by=frappe.session.user)
    doc.machine_draft = json.dumps(draft, ensure_ascii=False)
    lr._store(doc)
    return {"url": f"{PRINT_ROUTE}?report={doc.name}", "report": lr._report_row(doc.name)}


def print_context(name):
    """What the print page shows: the fixed layout (or today's if the form was never fixed), the tổ, the day, the ribbon."""
    doc, rights = lr._load(name)
    if not (rights.write or rights.confirm):
        frappe.throw("Bạn không in được phiếu của tổ này.", frappe.PermissionError)
    form = _draft(doc).get("form") or _form(doc)
    teams = {t.name: t for t in field._teams(doc.farm)}
    return {"report": doc.name, "date": doc.report_date, "company": doc.company, "farm": doc.farm,
            "farm_name": frappe.db.get_value("Farm", doc.farm, "farm_name") or doc.farm,
            "team_name": teams.get(doc.work_team, frappe._dict()).team_name or doc.work_team,
            "crew_name": teams.get(doc.crew, frappe._dict()).team_name or doc.crew or "", "form": form}


def _colours(lot, column):
    """The one colour a bao / thu / hủy cell can be on this lô, or None when there are several (the reviewer picks)."""
    field_name = "bag_left" if column["stage"] == paper.BAG else "left"
    open_ = [c for c in lot.get("colours") or [] if cint(c.get(field_name)) > 0]
    if column["stage"] == paper.HARVEST:
        return open_[-1]["tag"] if len(open_) == 1 else None  # colours are newest first
    return open_[0]["tag"] if len(open_) == 1 else None


@frappe.whitelist(methods=["POST"])
def read_photo(report, file_url):
    """Read a photo of the filled paper form into Draft lines marked machine_read, each with what the reviewer must check."""
    doc, rights = lr._load(report, for_update=True)
    if not rights.write:
        frappe.throw("Bạn chỉ nhập cho tổ của mình.", frappe.PermissionError)
    if not rules.can_edit(doc.state):
        frappe.throw("Báo cáo đã gửi. Nhờ đội trưởng mở lại nếu cần đọc lại phiếu.")
    field._closed(doc.company, getdate(doc.report_date))
    draft = _draft(doc)
    form = draft.get("form") or _form(doc)
    document_ai.count_use()
    columns = "\n".join(f"- {c['code']}: {c['label']}" + (" (số buồng và kg)" if c["kg"] else "") + (" (số và ô xong cả lô)" if c["done"] else "")
                        for c in form["columns"])
    prompt = PROMPT.replace("__COLUMNS__", columns).replace("__ROWS__", ", ".join(r["code"] for r in form["rows"])).replace("__REPORT__", doc.name)
    found = document_ai.read_photo(file_url, prompt)
    notes = []
    if str(found.get("report") or "").strip() and str(found.get("report")).strip() != doc.name:
        notes.append(f"Mã báo cáo trên ảnh là \"{found.get('report')}\", không phải {doc.name}: kiểm lại có đúng phiếu của tổ và ngày không.")
    data = lr.today(doc.farm, doc.work_team, str(doc.report_date))
    lots = {l["code"]: l for l in data["lots"]}
    columns_by_code = {c["code"]: c for c in form["columns"]}
    left, colours = {}, {}
    for lot in lots.values():
        for column in form["columns"]:
            key = (lot["code"], column["code"])
            if column["stage"] == paper.CUT:
                colours[key] = (data.get("ribbon") or {}).get("name")
            elif column["stage"] in (paper.BAG, paper.HARVEST, paper.REJECT):
                colours[key] = _colours(lot, column)
                chosen = next((c for c in lot.get("colours") or [] if c["tag"] == colours[key]), None)
                if chosen:
                    left[key] = cint(chosen["bag_left"] if column["stage"] == paper.BAG else chosen["left"])
            elif column["stage"] == paper.INJECT and lot.get("trees"):
                left[key] = cint(lot["trees"])
    lines, more = paper.check(form, found.get("cells") or [], left, colours)
    notes += more
    written = _write(doc, rights, data, lots, lines, columns_by_code, notes)
    draft.update(photo=file_url, read_at=str(now_datetime()), read_by=frappe.session.user, model=document_ai.MODEL,
                 cells=found.get("cells") or [], notes=notes, written=written)
    doc.reload()
    doc.machine_draft = json.dumps(draft, ensure_ascii=False)
    doc.source = "Photo"
    lr._store(doc)
    return {"lines": sum(len(v) for v in written.values()), "lots": sorted(written), "notes": notes, "report": lr._report_row(doc.name)}


def _write(doc, rights, data, lots, lines, columns, notes):
    """Write the machine lines lô by lô as flagged drafts. A lô that already has lines in the report is left alone."""
    lock("Farm", doc.farm)
    day = getdate(doc.report_date)
    works = lot_ledger.works(doc.farm)
    crew_teams = lr._crew_teams(doc.farm, rights.team.lotus_parent_team, doc.work_team)
    present = [p for p in lr._present(doc.company, day, doc.work_team, crew_teams) if p["own"]]
    people = {p["employee"]: {"morning": 1 if p.get("morning") else 0, "afternoon": 1 if p.get("afternoon") else 0} for p in present}
    names = {p["employee"]: p.get("employee_name") or p["employee"] for p in present}
    given = lr._assignments(doc.farm, doc.work_team, str(day))
    cycles = lr._cycles(list({l["block"] for l in lines}))
    written = {}
    for code in sorted({l["code"] for l in lines}, key=lambda c: (len(c), c)):
        lot = lots[code]
        block = lot["block"]
        if lr._lines(doc.name, block):
            notes.append(f"Lô {code} đã có số nhập tay trong báo cáo: giữ số đã nhập, không ghi số máy đọc.")
            continue
        rounds = {a.work_type: a for a in given if a.farm_block == block and a.kind == field.rules.ROUND}
        standing = next((a.name for a in given if a.farm_block == block and a.kind != field.rules.ROUND), None)
        written[code] = []
        for line in (l for l in lines if l["code"] == code):
            work = works[line["work_type"]]
            qty = line["qty"]
            clean = {"work": work, "stage": line["stage"] or None, "qty": qty, "area_ha": None, "bunch_tag": line["bunch_tag"],
                     "reject_stage": None, "reason": None, "weight_kg": line["kg"], "disease": None, "severity": None,
                     "done": 1 if line["done"] else 0, "notes": "Máy đọc từ ảnh phiếu giấy", "machine_read": 1, "materials": [],
                     "people": dict(people), "key": rules.line_key(doc.name, block, work.name, line["bunch_tag"], None)}
            flags = list(line["flags"])
            if work.requires_material:
                flags.append("Ghi vật tư và liều")
            if lr.pay_mode(work, rounds.get(work.name)) == rules.PAY_LOT and work.name not in rounds:
                flags.append("Khoán lô nhưng lô chưa giao cho tổ")
            if line["stage"] == paper.REJECT:
                clean["reject_stage"] = "After Cut" if line["bunch_tag"] else "Before Cut"
            entry = lr._write_line(doc, doc.name, block, clean, None, cint(cycles.get(block)), rounds, standing, names, "; ".join(flags))
            written[code].append(entry.name)
    return written
