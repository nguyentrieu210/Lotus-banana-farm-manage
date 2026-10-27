"""Team leader requests for materials or expenses. Approval never posts stock or money."""
import math

import frappe
from frappe.utils import flt, getdate, now_datetime, nowdate

DOCTYPE = "Lotus Field Proposal"
KIND_MATERIAL = "Vật tư"
KIND_COST = "Chi phí"
DRAFT, PENDING, APPROVED, RETURNED, REJECTED = (
    "Nháp", "Chờ duyệt", "Đã duyệt", "Trả lại", "Từ chối"
)
REQUEST_ROLES = {"Lotus Team Leader", "Lotus Field Supervisor", "Lotus Farm Manager"}
REVIEW_ROLES = {"Lotus Field Supervisor", "Lotus Farm Manager"}


def _roles(user=None):
    user = user or frappe.session.user
    return set(frappe.get_roles(user))


def _reviewer(user=None):
    user = user or frappe.session.user
    return user == "Administrator" or bool(_roles(user) & REVIEW_ROLES)


def _access():
    if frappe.session.user == "Guest":
        frappe.throw("Vui lòng đăng nhập để gửi đề xuất.", frappe.AuthenticationError)
    if not (frappe.session.user == "Administrator" or _roles() & REQUEST_ROLES):
        frappe.throw("Tài khoản chưa được cấp quyền đề xuất vật tư, chi phí.", frappe.PermissionError)


def permission(doc, ptype=None, user=None, **kwargs):
    user = user or frappe.session.user
    if ptype not in ("read", "select"):
        return False
    if not (user == "Administrator" or _roles(user) & REQUEST_ROLES):
        return False
    return bool(doc.owner == user or _reviewer(user))


def query(user=None):
    user = user or frappe.session.user
    if not (user == "Administrator" or _roles(user) & REQUEST_ROLES):
        return "1=0"
    if _reviewer(user):
        return "1=1"
    return "`tabLotus Field Proposal`.owner = " + frappe.db.escape(user)


def _doc(name):
    doc = frappe.get_doc(DOCTYPE, name)
    if not permission(doc, "read"):
        frappe.throw("Bạn không được xem đề xuất này.", frappe.PermissionError)
    return doc


def _version(doc, modified):
    if not modified or str(doc.modified) != str(modified):
        frappe.throw("Phiếu đã được cập nhật. Tải lại trước khi thao tác.")


def _scope(farm, block=None):
    """Use the same farm visibility rules already used by Lotus work screens."""
    farms = frappe.get_list("Farm", filters={"name": farm, "active": 1},
                            fields=["name", "company"], limit_page_length=1)
    if not farms:
        frappe.throw("Bạn không được dùng vườn đã chọn.", frappe.PermissionError)
    if block and not frappe.get_list("Farm Block", filters={"name": block, "farm": farm},
                                    fields=["name"], limit_page_length=1):
        frappe.throw("Lô không thuộc vườn đã chọn hoặc bạn không có quyền.")
    return farms[0].company


def _positive(value, label, allow_zero=False, limit=1_000_000_000):
    try:
        result = float(value)
    except (ValueError, TypeError, OverflowError):
        frappe.throw(label + " phải là số.")
    if not math.isfinite(result) or result > limit or (result < 0 if allow_zero else result <= 0):
        frappe.throw(label + " không hợp lệ.")
    return result


def _clean_lines(kind, rows):
    if not isinstance(rows, list) or not 1 <= len(rows) <= 30:
        frappe.throw("Mỗi phiếu cần từ 1 đến 30 dòng.")
    result = []
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            frappe.throw("Dòng %s không hợp lệ." % index)
        code = str(row.get("item_code") or "").strip() if kind == KIND_MATERIAL else ""
        description = str(row.get("description") or "").strip()
        uom = str(row.get("uom") or "").strip()
        if code:
            item = frappe.db.get_value("Item", code, ["item_name", "stock_uom", "disabled"], as_dict=True)
            if not item or item.disabled:
                frappe.throw("Dòng %s: mã vật tư không tồn tại hoặc đã ngừng dùng." % index)
            description = item.item_name
            if not uom:
                uom = item.stock_uom
            # Requests use the item's stocking unit; warehouse will handle conversions on issue.
            if uom != item.stock_uom:
                frappe.throw("Dòng %s: chọn đơn vị tồn kho của vật tư." % index)
        if not description or len(description) > 140:
            frappe.throw("Dòng %s: nhập tên vật tư hoặc khoản chi (tối đa 140 ký tự)." % index)
        if kind == KIND_MATERIAL and not uom:
            frappe.throw("Dòng %s: nhập đơn vị tính." % index)
        if len(uom) > 30:
            frappe.throw("Dòng %s: đơn vị tính quá dài." % index)
        qty = _positive(row.get("qty"), "Số lượng dòng %s" % index, limit=1_000_000)
        rate = _positive(row.get("rate", 0), "Giá dự kiến dòng %s" % index,
                         allow_zero=kind == KIND_MATERIAL)
        amount = round(qty * rate, 2)
        result.append(dict(item_code=code or None, description=description,
                           qty=qty, uom=uom or "lần", rate=rate, amount=amount))
    if sum(x["amount"] for x in result) > 100_000_000_000:
        frappe.throw("Tổng dự kiến vượt giới hạn, vui lòng kiểm tra lại.")
    return result


@frappe.whitelist(methods=["GET"])
def bootstrap():
    _access()
    from frappe.sessions import get_csrf_token
    farms = frappe.get_list("Farm", filters={"active": 1},
                            fields=["name", "farm_name", "company"], limit_page_length=200)
    blocks = frappe.get_list("Farm Block", filters={"farm": ["in", [f.name for f in farms] or [""]]},
                             fields=["name", "farm", "block_name"], limit_page_length=3000)
    items = frappe.get_all("Item", filters={"disabled": 0, "is_stock_item": 1},
                           fields=["name", "item_name", "stock_uom"],
                           order_by="item_name", limit_page_length=5000)
    return dict(user=frappe.session.user, csrf_token=get_csrf_token(),
                name=frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user,
                reviewer=_reviewer(), today=nowdate(), farms=farms, blocks=blocks, items=items)


@frappe.whitelist(methods=["GET"])
def proposals(view="mine"):
    _access()
    if view not in ("mine", "review"):
        frappe.throw("Bộ lọc không hợp lệ.")
    if view == "review" and not _reviewer():
        frappe.throw("Bạn không có quyền duyệt đề xuất.", frappe.PermissionError)
    filters = {"owner": frappe.session.user} if view == "mine" else {"state": PENDING}
    rows = frappe.get_list(DOCTYPE, filters=filters,
                           fields=["name", "kind", "farm", "farm_block", "reason", "state",
                                   "needed_date", "total_estimate", "modified", "owner"],
                           order_by="modified desc", limit_page_length=200)
    return rows


@frappe.whitelist(methods=["GET"])
def detail(name):
    _access()
    doc = _doc(name)
    return dict(name=doc.name, kind=doc.kind, farm=doc.farm, farm_block=doc.farm_block or "",
                reason=doc.reason, needed_date=str(doc.needed_date), state=doc.state,
                total_estimate=doc.total_estimate, owner=doc.owner, modified=str(doc.modified),
                reviewer=doc.reviewer or "", review_note=doc.review_note or "",
                lines=[dict(item_code=r.item_code or "", description=r.description, qty=r.qty,
                            uom=r.uom, rate=r.rate, amount=r.amount) for r in doc.lines],
                can_edit=doc.owner == frappe.session.user and doc.state in (DRAFT, RETURNED),
                can_review=_reviewer() and doc.state == PENDING and doc.owner != frappe.session.user)


@frappe.whitelist(methods=["POST"])
def save(values, name=None, modified=None):
    _access()
    values = frappe.parse_json(values) if isinstance(values, str) else values
    if not isinstance(values, dict):
        frappe.throw("Thông tin đề xuất không hợp lệ.")
    kind = values.get("kind")
    if kind not in (KIND_MATERIAL, KIND_COST):
        frappe.throw("Chọn loại đề xuất vật tư hoặc chi phí.")
    farm = str(values.get("farm") or "").strip()
    block = str(values.get("farm_block") or "").strip()
    company = _scope(farm, block)
    reason = str(values.get("reason") or "").strip()
    if len(reason) < 5 or len(reason) > 1000:
        frappe.throw("Ghi rõ lý do đề xuất (5 đến 1.000 ký tự).")
    try:
        needed_date = getdate(values.get("needed_date"))
    except (TypeError, ValueError):
        frappe.throw("Ngày cần không hợp lệ.")
    if not needed_date:
        frappe.throw("Chọn ngày cần vật tư hoặc chi phí.")
    if needed_date < getdate(nowdate()):
        frappe.throw("Ngày cần không được ở trong quá khứ.")
    lines = _clean_lines(kind, values.get("lines"))
    if name:
        from lotus_farm.controls import lock
        lock(DOCTYPE, name)
        doc = _doc(name)
        _version(doc, modified)
        if doc.owner != frappe.session.user or doc.state not in (DRAFT, RETURNED):
            frappe.throw("Chỉ người lập được sửa phiếu nháp hoặc phiếu trả lại.", frappe.PermissionError)
    else:
        doc = frappe.new_doc(DOCTYPE)
        doc.requester = frappe.session.user
    doc.update(dict(company=company, farm=farm, farm_block=block or None, kind=kind,
                    needed_date=needed_date, reason=reason, state=DRAFT,
                    total_estimate=round(sum(x["amount"] for x in lines), 2)))
    doc.set("lines", lines)
    if name:
        doc.save(ignore_permissions=True)
    else:
        doc.insert(ignore_permissions=True)
    return detail(doc.name)


def _notify(doc, submitted=False):
    """Best-effort mobile alerts; no approval or money flow depends on push."""
    try:
        from lotus_farm.push_notifications import _add_alert
        if submitted:
            owners = set()
            for role in REVIEW_ROLES:
                owners.update(frappe.get_all("Has Role", filters={"role": role},
                                             pluck="parent", limit_page_length=300))
            recipients = owners - {doc.owner}
            title, body = "Đề xuất mới chờ duyệt", doc.kind + " · " + doc.name
        else:
            recipients = {doc.owner}
            title, body = "Đề xuất đã xử lý", doc.name + " · " + doc.state
        for user in recipients:
            if not frappe.db.get_value("User", user, "enabled"):
                continue
            name = _add_alert(user, "proposal", title, body,
                              "/field-proposals?proposal=" + doc.name,
                              DOCTYPE, doc.name, key=doc.name + ":" + doc.state + ":" + str(doc.modified))
            if name:
                frappe.enqueue("lotus_farm.push_notifications._send_alert",
                               queue="short", enqueue_after_commit=True, alert_name=name)
    except Exception:
        frappe.log_error(title="Lotus field proposal notification", message=frappe.get_traceback())


@frappe.whitelist(methods=["POST"])
def submit(name, modified):
    _access()
    from lotus_farm.controls import lock
    lock(DOCTYPE, name)
    doc = _doc(name)
    _version(doc, modified)
    if doc.owner != frappe.session.user or doc.state not in (DRAFT, RETURNED):
        frappe.throw("Không thể gửi phiếu này.", frappe.PermissionError)
    if not doc.lines:
        frappe.throw("Phiếu chưa có khoản đề xuất.")
    doc.state = PENDING
    doc.review_note = ""
    doc.reviewer = ""
    doc.reviewed_at = None
    doc.save(ignore_permissions=True)
    _notify(doc, submitted=True)
    return detail(name)


@frappe.whitelist(methods=["POST"])
def review(name, decision, note, modified):
    _access()
    if not _reviewer():
        frappe.throw("Chỉ người phụ trách mới được duyệt.", frappe.PermissionError)
    if decision not in (APPROVED, RETURNED, REJECTED):
        frappe.throw("Kết quả duyệt không hợp lệ.")
    from lotus_farm.controls import lock
    lock(DOCTYPE, name)
    doc = _doc(name)
    _version(doc, modified)
    if doc.owner == frappe.session.user:
        frappe.throw("Không được tự duyệt đề xuất của mình.", frappe.PermissionError)
    if doc.state != PENDING:
        frappe.throw("Chỉ phiếu đang chờ duyệt mới được xử lý.")
    note = str(note or "").strip()
    if len(note) > 1000 or (decision != APPROVED and len(note) < 3):
        frappe.throw("Nêu rõ lý do trả lại hoặc từ chối (3 đến 1.000 ký tự).")
    doc.state = decision
    doc.review_note = note
    doc.reviewer = frappe.session.user
    doc.reviewed_at = now_datetime()
    doc.save(ignore_permissions=True)
    _notify(doc)
    return detail(name)
