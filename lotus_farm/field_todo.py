"""Independent field work to-do board.

Five selected OneDrive banana field-work groups. No payroll, attendance, labor
allocation, Daily Work Plan, material or stock documents are created here.
"""
from contextvars import ContextVar
from datetime import date
import math
import re
import uuid

import frappe
from frappe.utils import getdate, now_datetime

from lotus_farm.mobile_access import (
    allowed_teams, can_assign, can_capture, can_review_all, is_field_user,
    is_manager, require_farm, require_team, roles, SUPERVISOR,
)

_writing = ContextVar("field_todo_write", default=False)

GROUPS = (
    ("0102", "Trồng mới"),
    ("0103", "Chăm sóc vườn"),
    ("0104", "Bảo vệ thực vật"),
    ("0105", "Chăm sóc buồng"),
    ("0106", "Thu hoạch"),
)
GROUP_MAP = dict(GROUPS)
ALIASES = {"010304002": "LOTUS-SICK", "010507001": "LOTUS-BAG"}


def _access(farm):
    if not is_field_user():
        frappe.throw("Không có quyền xem công việc ngoài vườn.", frappe.PermissionError)
    require_farm(farm)
    if not frappe.db.exists("Farm", {"name": farm, "active": 1}):
        frappe.throw("Vườn không hoạt động.")


def _team_scope(farm):
    return allowed_teams(farm)


def _catalog():
    sections = frappe.get_all(
        "Work Category", filters={"category_code": ["like", "OD-01%"]},
        fields=["name", "category_code", "category_name"], limit_page_length=1000,
        order_by="category_code asc")
    section_map = {r.name: r for r in sections
                   if r.category_code[3:7] in GROUP_MAP}
    works = frappe.get_all(
        "Work Type", filters={"category": ["in", list(section_map) or [""]]},
        fields=["name", "work_code", "work_name", "category"],
        limit_page_length=1000)
    entries = [{
        "name": w.name, "code": w.work_code[3:],
        "work_name": w.work_name,
        "group_code": section_map[w.category].category_code[3:7],
        "section_code": section_map[w.category].category_code[3:],
        "section": section_map[w.category].category_name.split(" / ", 1)[-1]
    } for w in works if w.work_code.startswith("OD-")]
    for source_code, lotus_code in ALIASES.items():
        original = frappe.db.get_value("Work Type", {"work_code": lotus_code},
                                       ["name", "work_name"], as_dict=True)
        if not original:
            frappe.throw("Thiếu công việc đã có của Lotus: " + lotus_code)
        section_code = source_code[:6]
        section = next((s.category_name.split(" / ", 1)[-1] for s in sections
                        if s.category_code == "OD-" + section_code), "")
        entries.append({"name": original.name, "code": source_code,
                        "work_name": original.work_name, "group_code": source_code[:4],
                        "section_code": section_code, "section": section})
    codes = [w["code"] for w in entries]
    if len(set(codes)) != len(codes):
        frappe.throw("Danh mục công việc có mã trùng. Cần rà soát trước.")
    return sorted(entries, key=lambda w: (w["group_code"], w["section_code"],
                                          w["work_name"]))


def _validate_work(work_type):
    found = next((work for work in _catalog() if work["name"] == work_type), None)
    if not found:
        frappe.throw("Công việc không thuộc 5 nhóm đã chọn.", frappe.PermissionError)
    return found


def _read(doc):
    return {
        "name": doc.name, "farm": doc.farm, "farm_block": doc.farm_block,
        "work_team": doc.work_team, "work_type": doc.work_type,
        "group_code": doc.group_code, "section_code": doc.section_code,
        "tracking_mode": doc.tracking_mode,
        "start_date": str(doc.start_date), "due_date": str(doc.due_date),
        "target_qty": doc.target_qty if doc.tracking_mode == "Quantity" else None,
        "quantity_unit": doc.quantity_unit or "",
        "description": doc.description or "",
        "status": doc.status,
        "reported_qty": doc.reported_qty if doc.tracking_mode == "Quantity" and doc.reported_by else None,
        "report_note": doc.report_note or "", "reported_by": doc.reported_by or "",
        "reported_at": str(doc.reported_at) if doc.reported_at else "",
        "review_note": doc.review_note or "", "reviewed_by": doc.reviewed_by or "",
        "reviewed_at": str(doc.reviewed_at) if doc.reviewed_at else "",
        "modified": str(doc.modified),
    }


def _save(doc, *, create=False):
    flag = _writing.set(True)
    try:
        doc.save(ignore_permissions=True) if not create else doc.insert(ignore_permissions=True)
    finally:
        _writing.reset(flag)
    return _read(doc)


def _load(name):
    if not name:
        frappe.throw("Chọn công việc.")
    doc = frappe.get_doc("Field Todo", name)
    _access(doc.farm)
    if doc.work_team not in _team_scope(doc.farm):
        frappe.throw("Không có quyền với tổ được giao.", frappe.PermissionError)
    return doc


def _if_current(doc, expected_modified):
    if not expected_modified or str(doc.modified) != str(expected_modified):
        frappe.throw("Công việc đã được người khác cập nhật. Tải lại trước khi sửa.",
                     frappe.TimestampMismatchError)


def _note(value, max_length=500):
    text = str(value or "").strip()
    if len(text) > max_length:
        frappe.throw("Ghi chú quá dài.")
    return text


def _date(value, title):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(value or "")):
        frappe.throw(title + " không hợp lệ.")
    try:
        return getdate(value)
    except Exception:
        frappe.throw(title + " không hợp lệ.")


def _number(value, title, required=False):
    if value is None or str(value).strip() == "":
        if required:
            frappe.throw("Cần nhập " + title + ".")
        return None
    try:
        result = float(value)
    except (ValueError, TypeError):
        frappe.throw(title + " phải là số.")
    if isinstance(value, bool) or not math.isfinite(result) or result < 0 or result > 1_000_000_000:
        frappe.throw(title + " phải là số không âm hợp lệ.")
    return result


@frappe.whitelist()
def catalog(farm):
    _access(farm)
    items = _catalog()
    blocks = frappe.get_all("Farm Block", filters={"farm": farm, "active": 1},
                            fields=["name", "block_code", "block_name"],
                            order_by="block_code asc", limit_page_length=1000)
    teams = frappe.get_all("Work Team", filters={"farm": farm, "active": 1,
        "name": ["in", list(_team_scope(farm)) or [""]]},
        fields=["name", "team_code", "team_name"],
        order_by="team_code asc", limit_page_length=1000)
    return {"groups": [{"code": code, "name": name,
                        "count": sum(1 for w in items if w["group_code"] == code)}
                       for code, name in GROUPS],
            "sections": sorted({(w["section_code"], w["section"], w["group_code"])
                               for w in items}),
            "works": items, "blocks": blocks, "teams": teams,
            "can_assign": can_assign(), "can_capture": can_capture(),
            "can_review": is_manager() or SUPERVISOR in roles()}


@frappe.whitelist()
def board(farm, include_closed=0):
    _access(farm)
    team_ids = _team_scope(farm)
    if not team_ids:
        return {"rows": []}
    filters = {"farm": farm, "work_team": ["in", list(team_ids)]}
    if str(include_closed).lower() not in ("1", "true"):
        filters["status"] = ["not in", ["Accepted"]]
    entries = frappe.get_all("Field Todo", filters=filters, pluck="name",
                             order_by="modified desc", limit_page_length=1000)
    rows = [_read(frappe.get_doc("Field Todo", name)) for name in entries]
    works = {w["name"]: w for w in _catalog()}
    block_names = {b.name: b.block_code for b in frappe.get_all(
        "Farm Block", filters={"farm": farm}, fields=["name", "block_code"], limit_page_length=1000)}
    team_names = {t.name: t.team_name for t in frappe.get_all(
        "Work Team", filters={"farm": farm}, fields=["name", "team_name"], limit_page_length=1000)}
    for row in rows:
        w = works.get(row["work_type"], {})
        row["work_name"] = w.get("work_name", row["work_type"])
        row["section"] = w.get("section", "")
        row["group_name"] = GROUP_MAP.get(row["group_code"], row["group_code"])
        row["block_code"] = block_names.get(row["farm_block"], row["farm_block"])
        row["team_name"] = team_names.get(row["work_team"], row["work_team"])
    return {"rows": rows}


@frappe.whitelist(methods=["POST"])
def create(farm, farm_block, work_team, work_type, tracking_mode,
           start_date, due_date, request_key,
           target_qty=None, quantity_unit=None, description=None):
    _access(farm)
    if not can_assign():
        frappe.throw("Chỉ quản lý/giám sát được giao việc.", frappe.PermissionError)
    require_team(farm, work_team)
    if not frappe.db.exists("Farm Block", {"name": farm_block, "farm": farm, "active": 1}):
        frappe.throw("Lô không thuộc vườn đang chọn.", frappe.PermissionError)
    work = _validate_work(work_type)
    if tracking_mode not in ("Quantity", "Completion"):
        frappe.throw("Chọn kiểu báo cáo số lượng hoặc hoàn thành.")
    start, due = _date(start_date, "Ngày bắt đầu"), _date(due_date, "Hạn hoàn thành")
    if due < start:
        frappe.throw("Hạn hoàn thành không được trước ngày bắt đầu.")
    qty = _number(target_qty, "số lượng giao", required=False) if tracking_mode == "Quantity" else None
    uom = _note(quantity_unit, 30) if tracking_mode == "Quantity" else ""
    if tracking_mode == "Quantity" and not uom:
        frappe.throw("Cần nhập đơn vị khối lượng, ví dụ buồng hoặc cây.")
    desc = _note(description)
    if not re.fullmatch(r"[0-9a-fA-F-]{36}", str(request_key or "")):
        frappe.throw("Mã gửi yêu cầu không hợp lệ.")
    from lotus_farm.controls import lock
    lock("Farm", farm)
    previous = frappe.db.get_value("Field Todo", {"request_key": request_key}, "name")
    if previous:
        doc = _load(previous)
        if any([doc.farm != farm, doc.work_team != work_team, doc.farm_block != farm_block,
                doc.work_type != work_type, doc.tracking_mode != tracking_mode,
                str(doc.start_date) != str(start), str(doc.due_date) != str(due),
                (doc.target_qty if doc.tracking_mode == "Quantity" else None) != qty,
                (doc.quantity_unit or "") != uom, (doc.description or "") != desc]):
            frappe.throw("Mã yêu cầu đã dùng với nội dung khác.")
        return _read(doc)
    doc = frappe.new_doc("Field Todo")
    doc.update({"farm": farm, "farm_block": farm_block, "work_team": work_team,
                "work_type": work_type, "group_code": work["group_code"],
                "section_code": work["section_code"], "tracking_mode": tracking_mode,
                "start_date": start, "due_date": due, "target_qty": qty or 0,
                "quantity_unit": uom, "description": desc, "status": "Open",
                "request_key": request_key})
    return _save(doc, create=True)


@frappe.whitelist(methods=["POST"])
def update(name, action, expected_modified, reported_qty=None, note=None, work_team=None):
    doc = _load(name)
    from lotus_farm.controls import lock
    lock("Farm", doc.farm)
    doc.reload()
    _if_current(doc, expected_modified)
    if action == "reassign":
        if not can_assign() or doc.status not in ("Open", "Doing", "Rework"):
            frappe.throw("Không thể đổi tổ khi công việc đã báo xong.")
        require_team(doc.farm, work_team)
        doc.work_team = work_team
    elif action == "start":
        if not can_assign() or doc.status not in ("Open", "Rework"):
            frappe.throw("Công việc không thể bắt đầu ở trạng thái này.")
        doc.status = "Doing"
    elif action == "report":
        if not can_capture() or doc.status not in ("Open", "Doing", "Rework"):
            frappe.throw("Không thể báo hoàn thành công việc này.")
        if doc.tracking_mode == "Quantity":
            qty = _number(reported_qty, "số lượng hoàn thành", required=True)
            if qty == 0:
                frappe.throw("Số lượng báo hoàn thành phải lớn hơn 0.")
            doc.reported_qty = qty
        else:
            doc.reported_qty = 0
        doc.status = "Reported"
        doc.report_note = _note(note)
        doc.reported_by = frappe.session.user
        doc.reported_at = now_datetime()
        doc.reviewed_by = ""
        doc.reviewed_at = None
        doc.review_note = ""
    elif action in ("accept", "rework"):
        if not (is_manager() or SUPERVISOR in roles() and doc.work_team in _team_scope(doc.farm)):
            frappe.throw("Bạn không có quyền nghiệm thu.", frappe.PermissionError)
        if doc.status != "Reported":
            frappe.throw("Chỉ nghiệm thu công việc đã báo xong.")
        if action == "rework" and not _note(note):
            frappe.throw("Cần ghi lý do yêu cầu làm lại.")
        doc.status = "Accepted" if action == "accept" else "Rework"
        doc.review_note = _note(note)
        doc.reviewed_by = frappe.session.user
        doc.reviewed_at = now_datetime()
    else:
        frappe.throw("Thao tác không hợp lệ.")
    return _save(doc)
