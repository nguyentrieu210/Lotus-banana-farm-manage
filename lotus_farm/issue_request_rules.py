"""Yêu cầu cấp vật tư (spec 005): the rules, without Frappe.

A request is an ERPNext Material Request of type Material Issue. Its state is read from the document (docstatus, the
status ERPNext computes, the time it was sent, the reason it was returned) and from the stock issues made against its
lines; nothing else is stored.

Who (chủ vườn, 11/11/2026: "đội trưởng duyệt, không cần tổ trưởng, đội trưởng nhập luôn"): the đội trưởng of the đội
enters the request (for the whole đội or naming one tổ) and approves it, their own included; a quản lý vườn enters for any
đội and approves any request, their own included. Tổ trưởng do not make requests. One approval step, recorded with the
name of the person who approved.
"""
from datetime import date, datetime
import math

DRAFT, SENT, RETURNED = "Nháp", "Chờ duyệt", "Trả lại"
WAITING, PICKING, PARTIAL, DONE = "Chờ cấp", "Kho đang lập phiếu", "Đã cấp một phần", "Đã cấp đủ"
CLOSED, CANCELLED = "Đã đóng", "Đã hủy"
STATES = (DRAFT, SENT, RETURNED, WAITING, PICKING, PARTIAL, DONE, CLOSED, CANCELLED)
# Short codes for the screens (colour, filters), one per state.
CODES = {DRAFT: "draft", SENT: "sent", RETURNED: "returned", WAITING: "waiting", PICKING: "picking",
         PARTIAL: "partial", DONE: "done", CLOSED: "closed", CANCELLED: "cancelled"}
EDITABLE = (DRAFT, RETURNED)
OPEN_AFTER_APPROVAL = (WAITING, PICKING, PARTIAL)
STOPPED_STATUSES = ("Stopped", "Closed")
MAX_LINES = 100
EPSILON = 0.000001


def _day(value):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def state(docstatus, status=None, sent_at=None, return_reason=None, totals=None):
    """The state of one request. totals: {required, posted, draft} in stock units over all its lines."""
    docstatus = int(docstatus or 0)
    totals = totals or {}
    if docstatus == 2:
        return CANCELLED
    if docstatus == 0:
        if sent_at:
            return SENT
        return RETURNED if str(return_reason or "").strip() else DRAFT
    if status in STOPPED_STATUSES:
        return CLOSED
    required = float(totals.get("required") or 0)
    posted = float(totals.get("posted") or 0)
    if status == "Issued" or (required > 0 and posted >= required - EPSILON):
        return DONE
    if float(totals.get("draft") or 0) > EPSILON:
        return PICKING
    if status == "Partially Ordered" or posted > EPSILON:
        return PARTIAL
    return WAITING


def overdue(current, needed, today):
    """Still something to issue after the day it was needed. Never closes anything by itself."""
    needed, today = _day(needed), _day(today)
    return bool(current in OPEN_AFTER_APPROVAL and needed and today and needed < today)


def approver_for(crew_leader):
    """Who is expected to approve: the đội trưởng of the đội, or None (= a quản lý vườn) when the đội has none."""
    return crew_leader or None


def may_approve(user, crew_leader, user_is_manager=False):
    """FR-010 as decided 11/11/2026: the đội trưởng of the đội or a quản lý vườn, their own request included."""
    if not user:
        return False
    return bool(user_is_manager) or (bool(crew_leader) and user == crew_leader)


def may_request(team, members, supervisor):
    """None when this user may request for `team` (None or '' = the whole đội), else why not. members: the tổ of the đội;
    supervisor: đội trưởng of the đội or quản lý vườn. Tổ trưởng do not make requests."""
    if not supervisor:
        return "Chỉ đội trưởng của đội hoặc quản lý vườn lập yêu cầu cấp vật tư."
    if team and team not in members:
        return "Tổ không thuộc đội."
    return None


def line_issues(lines, zone_blocks=None, today=None, needed=None, max_lines=MAX_LINES):
    """Why these lines cannot be sent, as messages (empty = fine). lines: [{item_code, farm_block, qty, work_type?}].
    zone_blocks: the lô of the đội's khu that are active (None skips that check); today/needed: refuse a day already past."""
    errors = []
    if not lines:
        return ["Thêm ít nhất một vật tư cho một lô."]
    if len(lines) > max_lines:
        errors.append(f"Một yêu cầu tối đa {max_lines} dòng. Tách thành hai yêu cầu.")
    seen, works = set(), set()
    for line in lines:
        item, block = line.get("item_code"), line.get("farm_block")
        if not item:
            errors.append("Dòng thiếu vật tư.")
        if not block:
            errors.append("Dòng thiếu lô.")
        try:
            qty = float(line.get("qty") or 0)
        except (TypeError, ValueError):
            qty = float("nan")
        if not math.isfinite(qty) or qty <= 0:
            errors.append(f"Số lượng của {item or 'vật tư'} ở lô {line.get('block_code') or block or ''} phải lớn hơn 0.")
        if zone_blocks is not None and block and block not in zone_blocks:
            errors.append(f"Lô {line.get('block_code') or block} không thuộc khu của đội hoặc không còn hoạt động.")
        key = (item, block)
        if item and block and key in seen:
            errors.append(f"{item} ở lô {line.get('block_code') or block} có hai dòng. Gộp lại một dòng.")
        seen.add(key)
        if line.get("work_type"):
            works.add(line["work_type"])
    if len(works) > 1:
        errors.append("Một yêu cầu chỉ cho một việc. Lập hai yêu cầu.")
    needed, today = _day(needed), _day(today)
    if needed and today and needed < today:
        errors.append("Ngày cần đã qua. Chọn ngày cần từ hôm nay.")
    return list(dict.fromkeys(errors))


def lowered(old, new):
    """The approver may only lower or drop lines. old/new: {line key: qty}; a key missing from new is dropped.
    Returns [(key, old qty, new qty)] for the lines that changed; ValueError when a line is added or raised."""
    added = [k for k in new if k not in old]
    if added:
        raise ValueError("Người duyệt không thêm dòng. Trả lại để người lập sửa.")
    changes = []
    for key, before in old.items():
        after = float(new.get(key, 0) or 0)
        before = float(before or 0)
        if not math.isfinite(after) or after < 0:
            raise ValueError("Số lượng không hợp lệ.")
        if after > before + EPSILON:
            raise ValueError("Người duyệt chỉ giảm số. Muốn tăng thì trả lại để người lập sửa.")
        if after < before - EPSILON:
            changes.append((key, before, after))
    if all(float(new.get(k, 0) or 0) <= EPSILON for k in old):
        raise ValueError("Không còn dòng nào. Trả lại yêu cầu thay vì duyệt.")
    return changes


def split_by_area(total, areas, whole=False):
    """Split a total over lô by area (largest remainder), keeping the total exact. areas: {lô: area_ha or None}, in the
    order to show. whole: the unit takes whole numbers only (Chai, Gói, Bao). Lô without an area are not guessed.
    Returns {shares: {lô: qty}, missing: [lô without area], dropped: [lô that get 0]}."""
    total = float(total or 0)
    if not math.isfinite(total) or total <= 0:
        raise ValueError("Tổng phải lớn hơn 0.")
    missing = [b for b, a in areas.items() if not a or float(a) <= 0]
    usable = [(b, float(a)) for b, a in areas.items() if b not in missing]
    if not usable:
        raise ValueError("Các lô đã chọn chưa có diện tích. Nhập số cho từng lô.")
    scale = 1 if whole else 1000
    units = round(total * scale)
    if whole and abs(units - total) > EPSILON:
        raise ValueError("Đơn vị này chỉ nhận số nguyên.")
    area_sum = sum(a for _, a in usable)
    raw = [(b, units * a / area_sum) for b, a in usable]
    floors = {b: math.floor(r + 1e-9) for b, r in raw}
    rest = units - sum(floors.values())
    order = sorted(range(len(raw)), key=lambda i: (-(raw[i][1] - floors[raw[i][0]]), i))
    for i in order[:rest]:
        floors[raw[i][0]] += 1
    shares = {b: (floors[b] if whole else round(floors[b] / scale, 3)) for b, _ in usable}
    dropped = [b for b, q in shares.items() if q <= 0]
    return {"shares": {b: q for b, q in shares.items() if q > 0}, "missing": missing, "dropped": dropped}


def progress(required, posted=0, draft=0):
    """One line: requested, issued (posted), held by draft issues, and what is left to issue."""
    required, posted, draft = float(required or 0), float(posted or 0), float(draft or 0)
    left = required - posted - draft
    return {"required": required, "posted": posted, "draft": draft, "remaining": round(left, 6) if left > EPSILON else 0.0}


def duplicates(lines, open_lines):
    """Lines that another open request already holds for the same vật tư × lô (a warning, not a block).
    open_lines: [{item_code, farm_block, request, ...}]."""
    wanted = {(l.get("item_code"), l.get("farm_block")) for l in lines}
    return [o for o in open_lines if (o.get("item_code"), o.get("farm_block")) in wanted]


def actions(current, user, owner, can_approve=False, is_manager=False, warehouse_manager=False, approved_by=None,
            has_issues=False, has_drafts=False, can_request=False, can_print=False):
    """What this user may do with a request in this state (the server checks each again when it is done).
    has_issues: any stock issue (draft or posted) against it; has_drafts: draft issues holding part of it."""
    mine = user == owner
    approver = bool(user and (user == approved_by or is_manager))
    after = current in OPEN_AFTER_APPROVAL
    # The đội trưởng approves their own draft directly ("Lưu và duyệt"); returning is for someone else's request.
    approvable = current == SENT or (mine and current in EDITABLE)
    return {
        "edit": mine and current in EDITABLE,
        "send": mine and current in EDITABLE,
        "delete": mine and current in EDITABLE,
        "withdraw": mine and current == SENT,
        "approve": bool(can_approve) and approvable,
        "lower": bool(can_approve) and current == SENT,
        "return": bool(can_approve) and current == SENT and not mine,
        "close": after and not has_drafts and (mine or approver or bool(warehouse_manager)),
        "reopen": current == CLOSED and approver,
        "cancel": after and not has_issues and (mine or (bool(user) and user == approved_by)),
        "copy": bool(can_request) and current != DRAFT,
        "print": bool(can_print),
    }


def title(work_name, team_name=None, block_codes=(), limit=140):
    """'Phun thuốc · Tổ 3 · A12, A13' (the list of lô shortened when long)."""
    codes = [str(c) for c in block_codes if c]
    shown = ", ".join(codes[:6]) + (f" +{len(codes) - 6}" if len(codes) > 6 else "")
    parts = [str(work_name or "").strip(), str(team_name or "").strip(), shown]
    return " · ".join(p for p in parts if p)[:limit]
