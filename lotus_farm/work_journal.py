"""Manual daily tracking only. Never posts production, attendance, payroll or stock."""
import hashlib
import json
import math
import re
import unicodedata
from contextvars import ContextVar
from io import BytesIO

import frappe
from frappe.utils import getdate, nowdate
from lotus_farm.controls import farm_allowed, query_condition, lock

CLERK = "Lotus Work Journal Clerk"
_writing = ContextVar("lotus_journal_write", default=False)


def manager(user=None):
    user = user or frappe.session.user
    return user == "Administrator" or "Lotus Farm Manager" in frappe.get_roles(user)


def farm_names(user=None):
    user = user or frappe.session.user
    if user == "Guest":
        return []
    if user == "Administrator":
        return frappe.get_all("Farm", pluck="name")
    return frappe.get_all("User Permission", filters={"user": user, "allow": "Farm"}, pluck="for_value")


def capabilities():
    readable = frappe.session.user != "Guest" and bool(farm_names())
    return {"work_journal.read": readable,
            "work_journal.write": readable and (manager() or CLERK in frappe.get_roles())}


def require(farm):
    if frappe.session.user == "Guest" or not farm_allowed(farm):
        frappe.throw("Bạn không được xem nhật ký của vườn này.", frappe.PermissionError)
    return frappe.get_doc("Farm", farm)


def permission(doc, user=None, permission_type=None):
    user = user or frappe.session.user
    if user == "Guest" or not farm_allowed(doc.get("farm"), user):
        return False
    if permission_type in ("delete", "submit", "cancel", "amend"):
        return False
    if permission_type in ("write", "create"):
        return manager(user) or (CLERK in frappe.get_roles(user) and (doc.is_new() or doc.owner == user))
    return True


def journal_query(user=None):
    return "1=0" if (user or frappe.session.user) == "Guest" else query_condition("Work Daily Journal", user)


def valid_date(value):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(value or "")):
        frappe.throw("Ngày phải có dạng YYYY-MM-DD.")
    try:
        day = getdate(value)
    except (ValueError, TypeError):
        frappe.throw("Ngày không hợp lệ.")
    if day > getdate(nowdate()):
        frappe.throw("Không được ghi nhật ký cho ngày tương lai.")
    return str(day)


def _can_write(doc=None):
    return manager() or (CLERK in frappe.get_roles() and (not doc or doc.owner == frappe.session.user))


def _view(doc):
    return {"name": doc.name, "farm": doc.farm, "date": str(doc.posting_date),
            "owner": doc.owner, "modified": str(doc.modified), "modified_by": doc.modified_by,
            "can_write": _can_write(doc), "rows": [
                {"row_id": r.row_id, "work_team": r.work_team, "farm_block": r.farm_block,
                 "work_type": r.work_type, "uom": r.uom,
                 "quantity": r.quantity if r.has_quantity else None,
                 "workdays": r.workdays if r.has_workdays else None, "notes": r.notes or ""}
                for r in doc.get("rows")]}


@frappe.whitelist()
def bootstrap():
    if frappe.session.user == "Guest":
        frappe.throw("Vui lòng đăng nhập.", frappe.AuthenticationError)
    from frappe.sessions import get_csrf_token
    return {"user": frappe.session.user, "today": nowdate(), "csrf_token": get_csrf_token(),
            "capabilities": capabilities(), "farms": frappe.get_all("Farm",
            filters={"name": ["in", farm_names() or [""]]}, fields=["name", "farm_name", "company"])}


@frappe.whitelist()
def catalogue(farm):
    require(farm)
    # Minimal tracking metadata; do not expose prices, employees or other teams' official tasks.
    return {"teams": frappe.get_all("Work Team", filters={"farm": farm}, fields=["name", "team_code", "team_name", "active"]),
            "blocks": frappe.get_all("Farm Block", filters={"farm": farm}, fields=["name", "block_code", "active"]),
            "works": frappe.get_all("Work Type", fields=["name", "work_code", "work_name", "uom", "active"])}


@frappe.whitelist()
def get(farm, date):
    require(farm)
    day = valid_date(date)
    name = frappe.db.get_value("Work Daily Journal", {"farm": farm, "posting_date": day})
    return _view(frappe.get_doc("Work Daily Journal", name)) if name else {
        "name": None, "farm": farm, "date": day, "modified": None, "rows": [], "can_write": _can_write()}


def _number(value, label):
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (ValueError, TypeError):
        frappe.throw(label + ": cần nhập số.")
    if isinstance(value, bool) or not math.isfinite(number) or number < 0 or number > 1_000_000_000:
        frappe.throw(label + ": số không âm, tối đa 1 tỷ.")
    return number


def validate_document(doc):
    if not _writing.get():
        frappe.throw("Hãy lưu qua màn Nhật ký công việc.", frappe.PermissionError)
    farm = require(doc.farm)
    doc.company = farm.company
    doc.posting_date = valid_date(str(doc.posting_date))
    old = doc.get_doc_before_save()
    if old and (old.farm != doc.farm or str(old.posting_date) != str(doc.posting_date)):
        frappe.throw("Không được chuyển nhật ký sang vườn hoặc ngày khác.")
    if not _can_write(old):
        frappe.throw("Bạn không có quyền sửa nhật ký này.", frappe.PermissionError)
    if old and old.owner != frappe.session.user and not str(doc.correction_reason or "").strip():
        frappe.throw("Nhập lý do sửa nhật ký thay người lập.")
    previous = {r.row_id: r for r in old.get("rows")} if old else {}
    seen = set()
    for i, row in enumerate(doc.get("rows"), 1):
        prefix = f"Dòng {i} · "
        if not re.fullmatch(r"[A-Za-z0-9-]{8,64}", row.row_id or "") or row.row_id in seen:
            frappe.throw(prefix + "ID dòng không hợp lệ hoặc trùng.")
        seen.add(row.row_id)
        prev = previous.get(row.row_id)
        for dt, field, label in (("Work Team", "work_team", "Tổ/đội"), ("Farm Block", "farm_block", "Lô lớn"), ("Work Type", "work_type", "Công việc")):
            name = row.get(field)
            if not name or not frappe.db.exists(dt, name):
                frappe.throw(prefix + label + ": chọn từ danh mục.")
            master = frappe.get_doc(dt, name)
            if dt != "Work Type" and master.farm != doc.farm:
                frappe.throw(prefix + label + " không thuộc vườn.")
            if not master.active and (not prev or prev.get(field) != name):
                frappe.throw(prefix + label + " đã ngừng hoạt động.")
            if dt == "Work Type":
                row.uom = prev.uom if prev and prev.work_type == name else master.uom
        if not row.has_quantity and not row.has_workdays:
            frappe.throw(prefix + "nhập số lượng hoặc tổng công.")
        row.quantity = _number(row.quantity, prefix + "Số lượng") if row.has_quantity else 0
        row.workdays = _number(row.workdays, prefix + "Tổng công") if row.has_workdays else 0
        if (row.has_quantity and row.quantity is None) or (row.has_workdays and row.workdays is None):
            frappe.throw(prefix + "Số liệu đã chọn không được trống.")
        if len(row.notes or "") > 500:
            frappe.throw(prefix + "Ghi chú tối đa 500 ký tự.")


@frappe.whitelist(methods=["POST"])
def save(farm, date, rows, request_id, expected_modified=None, correction_reason=None, expected_user=None):
    if expected_user != frappe.session.user:
        frappe.throw("Tài khoản đã thay đổi. Đăng nhập lại trước khi lưu.", frappe.PermissionError)
    require(farm)
    day = valid_date(date)
    rows = frappe.parse_json(rows)
    if not isinstance(rows, type([])) or len(rows) > 500:
        frappe.throw("Nhật ký cần là danh sách, tối đa 500 dòng.")
    if not re.fullmatch(r"[A-Za-z0-9-]{8,80}", str(request_id or "")):
        frappe.throw("Mã yêu cầu lưu không hợp lệ.")
    payload = {"farm": farm, "date": day, "rows": rows, "expected_modified": expected_modified,
               "correction_reason": correction_reason}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    request_name = hashlib.sha256((frappe.session.user + ":" + request_id).encode()).hexdigest()
    lock("Farm", farm)
    if frappe.db.get_value("Work Journal Request", request_name, "name", for_update=True):
        saved = frappe.get_doc("Work Journal Request", request_name, for_update=True)
        if saved.owner != frappe.session.user or saved.payload_hash != digest:
            frappe.throw("Mã yêu cầu đã dùng cho nội dung khác.")
        return json.loads(saved.response_json)
    name = frappe.db.get_value("Work Daily Journal", {"farm": farm, "posting_date": day}, for_update=True)
    doc = frappe.get_doc("Work Daily Journal", name, for_update=True) if name else frappe.new_doc("Work Daily Journal")
    if not _can_write(doc if name else None):
        frappe.throw("Bạn không có quyền sửa nhật ký này.", frappe.PermissionError)
    if (name and str(doc.modified) != str(expected_modified)) or (not name and expected_modified):
        frappe.throw("Nhật ký đã thay đổi trên máy khác. Giữ bản đang nhập và tải lại để đối chiếu.", frappe.TimestampMismatchError)
    doc.farm, doc.posting_date, doc.correction_reason = farm, day, str(correction_reason or "").strip()[:500]
    if not name and not rows:
        frappe.throw("Thêm ít nhất một dòng công việc.")
    allowed = {"row_id", "work_team", "farm_block", "work_type", "uom", "quantity", "workdays", "notes"}
    previous_names = {r.row_id: r.name for r in doc.get("rows")}
    doc.set("rows", [])
    for row in rows:
        if not isinstance(row, dict) or set(row) - allowed:
            frappe.throw("Dòng có trường ngoài phạm vi cho phép.")
        doc.append("rows", {k: v for k, v in row.items() if k not in ("quantity", "workdays", "uom")} | {
            "name": previous_names.get(row.get("row_id")),
            "has_quantity": row.get("quantity") is not None and row.get("quantity") != "",
            "has_workdays": row.get("workdays") is not None and row.get("workdays") != "",
            "quantity": _number(row.get("quantity"), "Số lượng"), "workdays": _number(row.get("workdays"), "Tổng công")})
    token = _writing.set(True)
    try:
        doc.save(ignore_permissions=True)
    finally:
        _writing.reset(token)
    response = _view(doc)
    frappe.get_doc({"doctype": "Work Journal Request", "name": request_name, "journal": doc.name,
                    "payload_hash": digest, "response_json": json.dumps(response, default=str)}).insert(ignore_permissions=True, set_name=request_name)
    return response


def _filters(farm, from_date, to_date):
    require(farm)
    start, end = valid_date(from_date), valid_date(to_date)
    if start > end:
        frappe.throw("Từ ngày phải trước hoặc bằng đến ngày.")
    return {"farm": farm, "posting_date": ["between", [start, end]]}


@frappe.whitelist()
def journal_list(farm, from_date, to_date, work_team=None, farm_block=None, work_type=None, search=None):
    parents = frappe.get_all("Work Daily Journal", filters=_filters(farm, from_date, to_date),
                             fields=["name", "posting_date", "owner", "modified", "modified_by"], order_by="posting_date desc", limit_page_length=0)
    result = []
    def fold(value):
        return ''.join(c for c in unicodedata.normalize('NFD',str(value or '').lower()) if not unicodedata.combining(c)).replace('đ','d')
    needle=fold(search)
    labels={}
    if needle:
        for kind,field in (("teams","team_name"),("blocks","block_code"),("works","work_name")):
            labels.update({r.name: r.get(field) or r.name for r in catalogue(farm)[kind]})
    for parent in parents:
        doc = frappe.get_doc("Work Daily Journal", parent.name)
        for row in _view(doc)["rows"]:
            if any(value and row[field] != value for field, value in (("work_team", work_team), ("farm_block", farm_block), ("work_type", work_type))):
                continue
            if needle and needle not in fold(' '.join([row['notes'],*(str(row[k])+' '+labels.get(row[k],'') for k in ('work_team','farm_block','work_type'))])):
                continue
            result.append({**parent, "date": str(parent.posting_date), **row})
    return result


list = journal_list


@frappe.whitelist()
def summary(farm, from_date, to_date, work_team=None, farm_block=None, work_type=None, search=None):
    rows = journal_list(farm, from_date, to_date, work_team, farm_block, work_type, search)
    groups = {}
    for row in rows:
        key = (row["work_type"], row["uom"])
        group = groups.setdefault(key, {"work_type": key[0], "uom": key[1], "quantity": None, "workdays": None})
        for field in ("quantity", "workdays"):
            if row[field] is not None:
                group[field] = (group[field] or 0) + row[field]
    return {"rows": rows, "groups": [*groups.values()], "total_workdays": sum(r["workdays"] or 0 for r in rows)}


@frappe.whitelist()
def history(farm, date):
    current = get(farm, date)
    if not current["name"]:
        return []
    versions = frappe.get_all("Version", filters={"ref_doctype": "Work Daily Journal", "docname": current["name"]},
                              fields=["name", "owner", "creation", "data"], order_by="creation desc", limit_page_length=0)
    return [{"user": row.owner, "at": row.creation, "changes": json.loads(row.data)} for row in versions]


@frappe.whitelist()
def export(farm, from_date, to_date, work_team=None, farm_block=None, work_type=None, search=None):
    from openpyxl import Workbook
    data = summary(farm, from_date, to_date, work_team, farm_block, work_type, search)
    names = catalogue(farm)
    maps = {key: {r.name: r.get(label) or r.name for r in names[key]} for key, label in (("teams", "team_name"), ("blocks", "block_code"), ("works", "work_name"))}
    book = Workbook(); sheet = book.active; sheet.title = "Nhật ký theo dõi"
    sheet.append(["Ngày", "Tổ", "Lô", "Công việc", "Đơn vị", "Số lượng", "Tổng công", "Ghi chú", "Người nhập", "Cập nhật bởi"])
    for r in data["rows"]:
        values = [r["date"], maps["teams"].get(r["work_team"], r["work_team"]), maps["blocks"].get(r["farm_block"], r["farm_block"]), maps["works"].get(r["work_type"], r["work_type"]), r["uom"], r["quantity"], r["workdays"], r["notes"], r["owner"], r["modified_by"]]
        sheet.append(["'" + value if isinstance(value, str) and value.startswith(("=", "+", "-", "@")) else value for value in values])
    sheet.freeze_panes = "A2"; sheet.auto_filter.ref = sheet.dimensions
    output = BytesIO(); book.save(output)
    frappe.local.response.filename = f"nhat-ky-{from_date}-{to_date}.xlsx"
    frappe.local.response.filecontent = output.getvalue(); frappe.local.response.type = "binary"


def install():
    if frappe.db.exists("DocType", "Work Daily Journal"):
        frappe.db.add_unique("Work Daily Journal", ["farm", "posting_date"], constraint_name="unique_journal_farm_date")
