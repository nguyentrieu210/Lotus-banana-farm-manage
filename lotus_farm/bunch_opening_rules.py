"""Reading the farm's cut-bud book (sổ cắt bắp). Pure: no Frappe, no database.

Columns are read by position: G to Z hold one week in two columns (first = lần 1, second = lần 2), because some weeks carry the same
label in both. Columns C, D, E are the farm's own working figures and are ignored. Column AA is the row total and is used as a check.
"""
import datetime as dt
import re
import unicodedata

HEADER_ROW, COLOUR_ROW, DATA_FROM = 1, 2, 3
FIRST_WEEK_COLUMN, LAST_WEEK_COLUMN, TOTAL_COLUMN = 6, 25, 26


def _cell(row, index):
    return row[index] if index < len(row) else None


def _letter(index):
    return chr(ord("A") + index)


def clean_colour(text):
    """'TRẮNG( RÚT)' and ' TRẮNG' are the same colour."""
    return re.sub(r"\s+", " ", re.sub(r"\(.*?\)", "", unicodedata.normalize("NFC", str(text or "")))).strip()


def same_colour(header, label):
    fold = lambda value: re.sub(r"[\s\-]+", "", clean_colour(value).casefold())
    return bool(header) and fold(header) == fold(label)


def cut_date(year, week, lần):
    """The book has no day: lần 1 is taken as Wednesday and lần 2 as Saturday of the ISO week."""
    return dt.date.fromisocalendar(int(year), int(week), 3 if int(lần) == 1 else 6)


def source_key(block, year, week, lần):
    return f"opening:{block}:{year}-{int(week):02d}:{int(lần)}"


def _whole(value):
    """(number, ok). Blank is (None, True); text, fractions and negatives are not bunches."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None, True
    if isinstance(value, bool):
        return None, False
    try:
        number = float(str(value).strip())
    except ValueError:
        return None, False
    if number != number or number < 0 or not number.is_integer():
        return None, False
    return int(number), True


def _weeks(rows):
    weeks = {}
    header, colours = rows[HEADER_ROW], rows[COLOUR_ROW]
    for column in range(FIRST_WEEK_COLUMN, LAST_WEEK_COLUMN, 2):
        found = re.search(r"tu[ầa]n\s*(\d+)", unicodedata.normalize("NFC", str(_cell(header, column) or "")), re.I)
        if found:
            week = int(found.group(1))
            weeks[column] = (week, 1, clean_colour(_cell(colours, column)))
            weeks[column + 1] = (week, 2, clean_colour(_cell(colours, column + 1)))
    return weeks


def parse(rows):
    """{year, lines[{code, week, lan, colour, qty, row}], errors[{row, code, message}], total}. Nothing is dropped silently."""
    rows = [list(r) for r in rows]
    result = {"year": None, "lines": [], "errors": [], "total": 0}
    label = str(_cell(rows[HEADER_ROW], 0) or "").strip().casefold() if len(rows) > HEADER_ROW else ""
    if len(rows) <= DATA_FROM or label != "lô":
        result["errors"].append({"row": 2, "code": "", "message": "File không đúng mẫu sổ cắt bắp (dòng 2 phải bắt đầu bằng cột Lô)."})
        return result
    year = re.search(r"(20\d\d)", str(_cell(rows[0], 0) or ""))
    if not year:
        result["errors"].append({"row": 1, "code": "", "message": "Tiêu đề sổ phải ghi năm, ví dụ NĂM 2026."})
        return result
    result["year"] = int(year.group(1))
    weeks = _weeks(rows)
    closed = False
    for offset, row in enumerate(rows[DATA_FROM:], start=DATA_FROM + 1):
        code = str(_cell(row, 0) or "").strip()
        if not code:
            continue
        if unicodedata.normalize("NFC", code).casefold().startswith("tổng"):
            stated, ok = _whole(_cell(row, TOTAL_COLUMN))
            if ok and stated is not None and stated != result["total"]:
                result["errors"].append({"row": offset, "code": code, "message": f"Dòng tổng ghi {stated}, cộng các lô được {result['total']}."})
            closed = True
            break
        row_sum = 0
        for column in range(FIRST_WEEK_COLUMN, LAST_WEEK_COLUMN + 1):
            qty, ok = _whole(_cell(row, column))
            if not ok:
                result["errors"].append({"row": offset, "code": code, "message": f"Ô {_letter(column)}{offset} không phải số buồng nguyên: {_cell(row, column)}."})
                continue
            if not qty:
                continue
            if column not in weeks:
                result["errors"].append({"row": offset, "code": code, "message": f"Ô {_letter(column)}{offset} có số nhưng cột chưa ghi tuần."})
                continue
            week, lần, colour = weeks[column]
            result["lines"].append({"code": code, "week": week, "lan": lần, "colour": colour, "qty": qty, "row": offset})
            row_sum += qty
        stated, ok = _whole(_cell(row, TOTAL_COLUMN))
        if ok and stated is not None and stated != row_sum:
            result["errors"].append({"row": offset, "code": code, "message": f"Cột tổng ghi {stated}, cộng các tuần được {row_sum}."})
        result["total"] += row_sum
    if not closed:
        result["errors"].append({"row": len(rows), "code": "", "message": "Không thấy dòng TỔNG cuối sổ."})
    return result
