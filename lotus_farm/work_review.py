"""Review mobile field results before they become ERP production facts.

Draft Daily Work Result stays docstatus=0 until the manager approves it.
Every transition checks the current farm/team scope on the server.
"""
from html import escape

import frappe

from lotus_farm.controls import lock, command
from lotus_farm.mobile_access import (
    SUPERVISOR, roles, is_manager, require_farm,
    scoped_result_capture,
)


def can_verify():
    return is_manager() or SUPERVISOR in roles()


def can_approve():
    return is_manager()


def _audit(doc, action, note):
    actor = frappe.session.user
    content = escape(f"{action} | {actor} | {note or ''}")
    frappe.get_doc({
        "doctype": "Comment", "comment_type": "Info",
        "reference_doctype": doc.doctype,
        "reference_name": doc.name, "content": content,
    }).insert(ignore_permissions=True)


def notify_transition(doc, event):
    """Write a scoped in-app alert; Web Push is an optional after-commit signal."""
    from lotus_farm.controls import farm_allowed
    from lotus_farm.push_notifications import _add_alert
    if event in ("Pending", "Verified"):
        role = SUPERVISOR if event == "Pending" else MANAGER
        assigned = set(frappe.get_all(
            "Has Role", filters={"role": role}, pluck="parent", limit_page_length=1000))
        if event == "Pending":
            team = frappe.db.get_value("Daily Work Plan Line", doc.work_plan_line, "work_team")
            permitted = set(frappe.get_all(
                "User Permission", filters={"allow": "Work Team", "for_value": team},
                pluck="user", limit_page_length=1000)) if team else set()
        else:
            permitted = set(frappe.get_all(
                "User Permission", filters={"allow": "Farm", "for_value": doc.farm},
                pluck="user", limit_page_length=1000))
        recipients = assigned & permitted
    else:
        recipients = {doc.owner}
    titles = {
        "Pending": "Có báo cáo cần kiểm tra",
        "Verified": "Có báo cáo chờ quản lý duyệt",
        "Changes Requested": "Báo cáo được yêu cầu sửa",
        "Approved": "Báo cáo công việc đã duyệt",
    }
    title = titles.get(event)
    if not title:
        return
    for user in recipients:
        if user == doc.owner and event in ("Pending", "Verified"):
            continue
        if not user or not frappe.db.get_value("User", user, "enabled") or not farm_allowed(doc.farm, user):
            continue
        key = f"result:{doc.name}:{event}:{doc.modified}"
        name = _add_alert(user, "work", title, f"Phiếu {doc.name}",
                          "/work?tab=tasks", "Daily Work Result", doc.name, key=key)
        if name:
            frappe.enqueue("lotus_farm.push_notifications._send_alert",
                           alert_name=name, queue="short", enqueue_after_commit=True)


def _load(name):
    if not name:
        frappe.throw("Chọn báo cáo cần kiểm tra.")
    # Lock in the same Farm -> Plan -> Result order as field.capture.
    doc = frappe.get_doc("Daily Work Result", name)
    require_farm(doc.farm)
    lock("Farm", doc.farm)
    lock("Daily Work Plan", doc.work_plan)
    doc = frappe.get_doc("Daily Work Result", name, for_update=True)
    if not is_manager():
        from lotus_farm.mobile_access import allowed_teams
        team = frappe.db.get_value("Daily Work Plan Line", doc.work_plan_line, "work_team")
        if team not in allowed_teams(doc.farm):
            frappe.throw("Không được kiểm tra báo cáo của tổ khác.", frappe.PermissionError)
    if doc.docstatus != 0:
        frappe.throw("Báo cáo đã được chốt hoặc huỷ.")
    return doc


@frappe.whitelist(methods=["POST"])
def decide(result, decision, reason=None):
    if decision not in ("Verify", "Approve", "Request Changes"):
        frappe.throw("Quyết định không hợp lệ.")
    if not can_verify():
        frappe.throw("Tài khoản không có quyền kiểm tra kết quả.", frappe.PermissionError)
    doc = _load(result)
    note = str(reason or "").strip()
    state = doc.review_state or "Pending"
    if doc.owner == frappe.session.user:
        frappe.throw("Người báo kết quả không được tự kiểm tra hoặc tự duyệt.", frappe.PermissionError)

    if decision == "Verify":
        if state != "Pending":
            frappe.throw("Chỉ kiểm tra báo cáo đang chờ kiểm tra.")
        doc.review_state = "Verified"
        doc.verified_by = frappe.session.user
        doc.verified_at = frappe.utils.now_datetime()
        doc.review_note = note[:500]
    elif decision == "Approve":
        if not can_approve():
            frappe.throw("Chỉ quản lý vườn được duyệt kết quả cuối.", frappe.PermissionError)
        if state != "Verified":
            frappe.throw("Báo cáo phải được đội trưởng kiểm tra trước khi duyệt.")
        if doc.verified_by == frappe.session.user:
            frappe.throw("Người đã kiểm tra không được tự duyệt lần hai.", frappe.PermissionError)
        # The day cannot close correctly if actual team labor exceeds allocation.
        allocated = sum(frappe.utils.flt(x) for x in frappe.get_all(
            "Labor Allocation",
            filters={"work_plan_line": doc.work_plan_line, "docstatus": 1},
            pluck="allocated_workdays"))
        if frappe.utils.flt(doc.actual_workdays) > allocated + 0.000001:
            frappe.throw("Số công thực tế vượt công đã phân. Điều chỉnh phân công trước khi duyệt.")
        plan = frappe.get_doc("Daily Work Plan", doc.work_plan)
        line = next((r for r in plan.lines if r.name == doc.work_plan_line), None)
        if not line:
            frappe.throw("Không tìm thấy công việc trong kế hoạch.")
        if line.norm_profile and not frappe.db.exists(
            "Material Requirement",
            {"work_plan_line": doc.work_plan_line, "docstatus": 1}):
            frappe.throw("Công việc có định mức vật tư nhưng chưa có phiếu nhu cầu đã xác nhận.")
        doc.review_state = "Approved"
        doc.reviewed_by = frappe.session.user
        doc.reviewed_at = frappe.utils.now_datetime()
        doc.review_note = note[:500]
    else:
        if state not in ("Pending", "Verified"):
            frappe.throw("Báo cáo không ở trạng thái có thể yêu cầu sửa.")
        if not note or len(note) > 500:
            frappe.throw("Ghi lý do cần sửa (tối đa 500 ký tự).")
        doc.review_state = "Changes Requested"
        doc.review_note = note
        doc.verified_by = None
        doc.verified_at = None
    with scoped_result_capture(doc.work_plan, doc.work_plan_line), command(doc, "review_result"):
        doc.flags.ignore_permissions = True
        doc.save(ignore_permissions=True)
        if decision == "Approve":
            doc.submit()
    _audit(doc, decision, note)
    notify_transition(doc, {
        "Verify": "Verified", "Approve": "Approved",
        "Request Changes": "Changes Requested",
    }[decision])
    return {"document": doc.name, "review_state": doc.review_state,
            "docstatus": doc.docstatus}


def prepare_revision(doc, values):
    """A rejected mobile report may be resubmitted by its original author only."""
    if doc.docstatus != 0 or doc.review_state != "Changes Requested":
        frappe.throw("Chỉ có thể sửa báo cáo bị trả lại.")
    if doc.owner != frappe.session.user:
        frappe.throw("Chỉ người đã báo mới được sửa kết quả.", frappe.PermissionError)
    if doc.work_plan != values.get("work_plan") or doc.work_plan_line != values.get("work_plan_line"):
        frappe.throw("Không được chuyển báo cáo sang công việc khác.", frappe.PermissionError)
    for field in ("farm_block", "farm_plot", "crop_cycle", "sucker_selection_batch", "posting_date"):
        if str(doc.get(field) or "") != str(values.get(field) or ""):
            frappe.throw("Không được đổi lô/ngày trong báo cáo sửa.", frappe.PermissionError)
    for field in ("completed_qty", "actual_workdays", "unfinished_reason"):
        doc.set(field, values.get(field))
    doc.review_state = "Pending"
    doc.verified_by = None
    doc.verified_at = None
    doc.review_note = None
    with scoped_result_capture(doc.work_plan, doc.work_plan_line):
        doc.flags.ignore_permissions = True
        doc.save(ignore_permissions=True)
    _audit(doc, "Resubmit", "Đã gửi lại kết quả sau yêu cầu sửa.")
    return doc


def assert_new_result(values):
    existing = frappe.db.exists(
        "Daily Work Result",
        {"work_plan_line": values["work_plan_line"], "docstatus": ["<", 2]},
    )
    if existing:
        frappe.throw("Công việc đã có báo cáo. Mở báo cáo cũ để sửa hoặc chờ duyệt.")