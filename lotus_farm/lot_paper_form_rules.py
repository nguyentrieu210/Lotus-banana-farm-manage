"""Phiếu giấy của tổ-ngày và đọc ảnh phiếu (spec 002, US1 phần sau). Pure: no Frappe, no database.

The printed form has one row per lô of the tổ and fixed columns with short codes: the bunch stages (chích bắp, cắt bắp
with the ribbon of the day printed, bao buồng, thu hoạch with kg, hủy buồng) and the việc vườn given to the tổ on those
lô (up to MAX_FIELD columns). The model reading a photo of it returns the cells written in; check() turns them into
lines and flags the doubtful ones with fixed rules, never with the model's own confidence: lô or column not on the
form, bunches not a whole number, more than is left, harvest without kg, a colour that cannot be told, and a việc the
form printed for a lô left empty.
"""
INJECT, CUT, BAG, HARVEST, REJECT = "Bud Injection", "Cut Bud", "Bag", "Harvest", "Reject"
BUNCH_COLUMNS = ((CUT, "Cắt bắp"), (INJECT, "Chích bắp"), (BAG, "Bao buồng"), (HARVEST, "Thu hoạch"), (REJECT, "Hủy buồng"))
MAX_FIELD = 4
UNCHECKED = "Máy đọc, chưa kiểm"


def _natural(code):
    return (len(str(code or "")), str(code or ""))


def layout(lots, works, ribbon_label=None):
    """lots: [{block, code, zone, rounds: [work_type]}]; works: {name: {label, stage, uom}} (bunch stages and việc vườn).
    Returns the columns (code, label, work_type, stage, kg, done), the rows and the cells the form expects filled."""
    by_stage = {w["stage"]: name for name, w in works.items() if w.get("stage")}
    columns = []
    for stage, label in BUNCH_COLUMNS:
        if stage in by_stage:
            text = label + (f" (màu {ribbon_label})" if stage == CUT and ribbon_label else "")
            columns.append({"work_type": by_stage[stage], "stage": stage, "label": text, "kg": stage == HARVEST, "done": False})
    given = sorted({w for lot in lots for w in lot.get("rounds") or [] if w in works and not works[w].get("stage")},
                   key=lambda w: works[w]["label"])[:MAX_FIELD]
    for work in given:
        columns.append({"work_type": work, "stage": "", "label": works[work]["label"] + (f" ({works[work]['uom']})" if works[work].get("uom") else ""),
                        "kg": False, "done": True})
    for index, column in enumerate(columns, 1):
        column["code"] = f"C{index}"
    rows = sorted(({"block": l["block"], "code": l["code"], "zone": l.get("zone") or ""} for l in lots), key=lambda r: (r["zone"], _natural(r["code"])))
    code_of = {c["work_type"]: c["code"] for c in columns}
    expected = [[l["code"], code_of[w]] for l in lots for w in l.get("rounds") or [] if w in code_of]
    return {"columns": columns, "rows": rows, "expected": sorted(expected)}


def _number(value):
    if value in (None, "", "-"):
        return None
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return None


def check(form, cells, left=None, colours=None):
    """cells: [{lot, col, qty, kg, done}] read from the photo. left: {(lô code, column code): what is left (bunches of the
    colour for bao/thu/hủy, trees for chích)}. colours: {(lô code, column code): the one colour that applies, or None when
    several could}. Returns (lines, notes): one line per filled cell with its flags, and notes about the photo as a whole."""
    left, colours = left or {}, colours or {}
    rows = {r["code"]: r for r in form["rows"]}
    columns = {c["code"]: c for c in form["columns"]}
    lines, notes, seen = [], [], set()
    for cell in cells or []:
        lot, col = str(cell.get("lot") or "").strip().upper(), str(cell.get("col") or "").strip().upper()
        qty, kg, done = _number(cell.get("qty")), _number(cell.get("kg")), bool(cell.get("done"))
        if lot not in rows:
            notes.append(f"Phiếu có lô \"{lot or '?'}\" không in sẵn: kiểm ảnh rồi nhập tay.")
            continue
        if col not in columns:
            notes.append(f"Lô {lot}: cột \"{col or '?'}\" không có trên phiếu: kiểm ảnh rồi nhập tay.")
            continue
        if (lot, col) in seen:
            notes.append(f"Lô {lot}, cột {col}: đọc được hai lần, chỉ lấy lần đầu.")
            continue
        seen.add((lot, col))
        column = columns[col]
        if qty is None and not done:
            continue
        flags = [UNCHECKED]
        if column["stage"] and qty is not None and not float(qty).is_integer():
            flags.append(f"Số buồng không phải số nguyên ({qty:g})")
        if (lot, col) in left and qty is not None and qty > left[(lot, col)]:
            flags.append(f"Vượt số còn lại ({left[(lot, col)]:g})")
        if column["kg"] and not kg:
            flags.append("Thiếu kg")
        if column["stage"] in (BAG, HARVEST, REJECT) and not colours.get((lot, col)):
            flags.append("Chọn màu dây")
        if column["stage"] == REJECT:
            flags.append("Chọn lý do hủy")
        lines.append({"block": rows[lot]["block"], "code": lot, "col": col, "work_type": column["work_type"], "stage": column["stage"],
                      "qty": qty, "kg": kg if column["kg"] else None, "done": done and column["done"],
                      "bunch_tag": colours.get((lot, col)), "flags": flags})
    filled = {(l["code"], l["col"]) for l in lines}
    for lot, col in form["expected"]:
        if (lot, col) not in filled:
            notes.append(f"Lô {lot}: phiếu in việc \"{columns[col]['label']}\" mà ô trống. Nếu tổ đã làm, nhập tay.")
    return lines, notes
