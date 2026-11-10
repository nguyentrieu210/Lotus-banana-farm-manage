"""Opening balance of the sổ lô (cắt bắp lines) from the farm's cut-bud book: preview first, then write. Running it again adds nothing."""
import base64
import json
from io import BytesIO

import frappe
from frappe.utils import cint, getdate, now_datetime

from lotus_farm import bunch_opening_rules as rules
from lotus_farm import field_report as field
from lotus_farm import lot_ledger
from lotus_farm.controls import lock

OPENING = "Opening Import"
CACHE = "lotus_bunch_opening:"


def _manager(farm):
    field.require_farm(farm)
    if not field.is_manager():
        frappe.throw("Chỉ quản lý vườn nạp sổ cắt bắp.", frappe.PermissionError)


def _read(content):
    from openpyxl import load_workbook
    try:
        sheet = load_workbook(BytesIO(base64.b64decode(str(content).split(",", 1)[-1])), read_only=True, data_only=True).worksheets[0]
    except Exception:
        frappe.throw("Không đọc được file. Hãy chọn đúng file Excel sổ cắt bắp (.xlsx).")
    return list(sheet.iter_rows(values_only=True))


def _resolve(farm, parsed):
    """Tie each line of the book to its lô and colour of the week, and say what would happen to it."""
    errors = list(parsed["errors"])
    blocks = {b.block_code: b for b in frappe.get_all("Farm Block", filters={"farm": farm, "active": 1},
                                                      fields=["name", "block_code", "lotus_current_cycle_no"], limit_page_length=0)}
    tags = {(t.week_year, t.week_number, str(t.week_half)): t for t in frappe.get_all(
        "Bunch Tag", filters={"farm": farm, "period_basis": "Cut Bud", "week_year": parsed["year"]},
        fields=["name", "week_year", "week_number", "week_half", "color_label", "valid_from", "valid_to"], limit_page_length=0)}
    current = {r.source_key: r for r in lot_ledger.bunch_rows({"farm": farm, "source_type": OPENING, "state": ["!=", "Voided"]},
                                                              ["source_key", "qty"])}
    daily = {(r.farm_block, r.bunch_tag) for r in lot_ledger.bunch_rows({"farm": farm, "event_type": "Cut Bud", "state": ["!=", "Voided"],
                                                                        "source_type": ["!=", OPENING]}, ["farm_block", "bunch_tag"])}
    rows = []
    for line in parsed["lines"]:
        def bad(message):
            errors.append({"row": line["row"], "code": line["code"], "message": message})

        block = blocks.get(line["code"])
        where = f"tuần {line['week']} lần {line['lan']}"
        if not block:
            bad("Lô không có trong vườn.")
            continue
        if cint(block.lotus_current_cycle_no) < 1:
            bad("Lô chưa có vụ hiện tại trong danh mục lô.")
            continue
        tag = tags.get((parsed["year"], line["week"], str(line["lan"])))
        if not tag:
            bad(f"Chưa có màu dây của {where} trong lịch màu dây.")
            continue
        if not rules.same_colour(line["colour"], tag.color_label):
            bad(f"Sổ ghi màu {line['colour']} ở {where}, lịch màu dây là {tag.color_label}.")
            continue
        key = rules.source_key(block.name, parsed["year"], line["week"], line["lan"])
        if (block.name, tag.name) in daily:
            bad(f"Màu {tag.color_label} {where} đã được nhập hằng ngày; nạp thêm sẽ đếm trùng.")
            continue
        existing = current.get(key)
        if existing and cint(existing.qty) != line["qty"]:
            bad(f"{where}: sổ buồng đang có {existing.qty} buồng, file ghi {line['qty']}. Sửa dòng đó có lý do nếu số mới đúng.")
            continue
        rows.append(dict(line, block=block.name, tag=tag.name, ribbon=tag.color_label, cycle=cint(block.lotus_current_cycle_no), key=key,
                         date=str(rules.cut_date(parsed["year"], line["week"], line["lan"])), exists=bool(existing)))
    return rows, errors


def _summary(rows):
    colours = {}
    for r in rows:
        colours[r["ribbon"]] = colours.get(r["ribbon"], 0) + r["qty"]
    fresh = [r for r in rows if not r["exists"]]
    return {"lines": len(rows), "bunches": sum(r["qty"] for r in rows), "new_lines": len(fresh), "new_bunches": sum(r["qty"] for r in fresh),
            "already": len(rows) - len(fresh), "blocks": len({r["code"] for r in rows}), "colours": [{"label": k, "bunches": v} for k, v in colours.items()]}


@frappe.whitelist(methods=["POST"])
def preview(farm, content, filename=None):
    """Nothing is written. The token carries what was read to `commit`."""
    _manager(farm)
    parsed = rules.parse(_read(content))
    rows, errors = _resolve(farm, parsed)
    token = frappe.generate_hash(length=20)
    frappe.cache.set_value(CACHE + frappe.session.user + ":" + token, json.dumps(dict(farm=farm, parsed=parsed, filename=filename or "Sổ cắt bắp")), expires_in_sec=1800)
    return {"token": token, "rows": rows, "errors": errors, "summary": _summary(rows), "file_total": parsed["total"], "ready": not errors and any(not r["exists"] for r in rows)}


@frappe.whitelist(methods=["POST"])
def commit(farm, token):
    """Write the new lines as confirmed: this book is the farm's own settled record. Any problem in the file stops the whole import."""
    _manager(farm)
    key = CACHE + frappe.session.user + ":" + str(token)
    cached = frappe.cache.get_value(key)
    if not cached:
        frappe.throw("Bản xem trước đã hết hạn, hãy chọn lại file.")
    payload = json.loads(cached if isinstance(cached, str) else cached.decode())
    if payload["farm"] != farm:
        frappe.throw("Bản xem trước thuộc vườn khác.")
    lock("Farm", farm)
    rows, errors = _resolve(farm, payload["parsed"])
    if errors:
        frappe.throw("File còn lỗi, chưa ghi dòng nào. Hãy xem trước lại.")
    written = skipped = 0
    user, now = frappe.session.user, now_datetime()
    work = lot_ledger.work_for_stage(farm, "Cut Bud")
    if not work:
        frappe.throw("Vườn chưa có việc cắt bắp trong danh mục việc.")
    company = frappe.db.get_value("Farm", farm, "company")
    for r in rows:
        if r["exists"]:
            skipped += 1
            continue
        doc = frappe.new_doc(lot_ledger.ENTRY)
        doc.update({"farm": farm, "company": company, "farm_block": r["block"], "cycle_no": r["cycle"], "work_type": work.name, "stage": "Cut Bud",
                    "pay_mode": work.pay_mode, "uom": work.uom, "posting_date": getdate(r["date"]), "qty": r["qty"], "bunch_tag": r["tag"],
                    "source_type": OPENING, "source_name": str(payload["filename"])[:140], "source_key": r["key"], "state": "Confirmed",
                    "entered_by": user, "confirmed_by": user, "confirmed_at": now})
        field._store(doc)
        written += 1
    frappe.cache.delete_value(key)
    return {"written": written, "skipped": skipped, "bunches": sum(r["qty"] for r in rows if not r["exists"])}
