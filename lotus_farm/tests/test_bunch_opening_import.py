import datetime as dt
import importlib.util
import pathlib
import unittest

_spec = importlib.util.spec_from_file_location("bunch_opening_rules", pathlib.Path(__file__).parents[1] / "bunch_opening_rules.py")
rules = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rules)

WEEKS = ["Tuần 43 (19-25/10)", None, "Tuần 44 (26/10-01/11)", None, "Tuần 45 (02/11-08/11)", None, "Tuần 46 (09/11-15/11)", None]
COLOURS = [" ĐỎ(RÚT)", " ĐỎ", "TRẮNG( RÚT)", " TRẮNG", "TÍM( RÚT)", " TÍM", " CAM", "CAM"]
# Columns G..N of the book as it stood on 09/11/2026; C, D, E carried #REF! there.
LOTS = [("A1", 20, 22, 31, 21), ("A2", 6, 9, 17, 7), ("A3", 7, 10, 20, 6), ("A4", 3, 8, 19, None), ("A5", 13, 6, 17, None),
        ("A6", 21, 12, 14, None), ("A7", 5, 8, 9, None), ("A8", 38, 60, 57, 28), ("A9", None, 15, 22, None), ("A10", None, 16, 10, None),
        ("A11", None, 8, 7, None), ("A12", None, 5, 6, None), ("A13", None, 3, 7, None)]


def book(lots=LOTS, total=593, title="SỐ LIỆU CẮT BẮP NĂM 2026 FARM 222"):
    pad = [None] * 12
    rows = [[title] + [None] * 26,
            ["Lô", "Số cây ", "c", "d", "e", "GHI CHÚ"] + WEEKS + pad + [None],
            [None] * 6 + COLOURS + pad + [None]]
    for code, w43, w44, l1, l2 in lots:
        cells = [w43, None, w44, None, l1, l2, None, None]
        rows.append([code, 1000, "#REF!", "#REF!", "#REF!", ""] + cells + pad + [sum(x or 0 for x in cells)])
    rows.append(["TỔNG", None, None, None, None, None] + [None] * 8 + pad + [total])
    rows.append([None] * 27)
    rows.append(["Ghi chú:"] + [None] * 26)
    return rows


class ReadTheBook(unittest.TestCase):
    def setUp(self):
        self.result = rules.parse(book())

    def test_the_book_has_593_bunches_and_no_errors(self):
        self.assertEqual(self.result["errors"], [])
        self.assertEqual(self.result["total"], 593)
        self.assertEqual(sum(x["qty"] for x in self.result["lines"]), 593)
        self.assertEqual(self.result["year"], 2026)

    def test_colours_add_up_as_the_farm_counted_them(self):
        by = {}
        for x in self.result["lines"]:
            by[x["colour"]] = by.get(x["colour"], 0) + x["qty"]
        self.assertEqual(by, {"ĐỎ": 113, "TRẮNG": 182, "TÍM": 298})

    def test_first_column_is_lan_1_second_is_lan_2(self):
        a1 = {(x["week"], x["lan"]): x["qty"] for x in self.result["lines"] if x["code"] == "A1"}
        self.assertEqual(a1, {(43, 1): 20, (44, 1): 22, (45, 1): 31, (45, 2): 21})

    def test_week_46_keeps_two_columns_with_the_same_label_apart(self):
        rows = book()
        rows[3][12], rows[3][13] = 4, 5
        rows[3][26] += 9
        rows[16][26] = 602
        result = rules.parse(rows)
        self.assertEqual(result["errors"], [])
        a1 = {(x["week"], x["lan"]): (x["qty"], x["colour"]) for x in result["lines"] if x["code"] == "A1"}
        self.assertEqual(a1[(46, 1)], (4, "CAM"))
        self.assertEqual(a1[(46, 2)], (5, "CAM"))

    def test_working_columns_are_ignored(self):
        self.assertFalse(any("REF" in e["message"] for e in self.result["errors"]))


class RefuseBadCells(unittest.TestCase):
    def errors(self, edit):
        rows = book()
        edit(rows)
        return rules.parse(rows)["errors"]

    def test_fraction_is_reported_with_its_cell(self):
        errors = self.errors(lambda r: r[3].__setitem__(6, 2.5))
        self.assertTrue(any("G4" in e["message"] for e in errors))

    def test_text_is_reported_not_skipped(self):
        self.assertTrue(self.errors(lambda r: r[3].__setitem__(6, "ba mươi")))

    def test_row_total_is_checked(self):
        errors = self.errors(lambda r: r[3].__setitem__(26, 95))
        self.assertTrue(any("Cột tổng" in e["message"] for e in errors))

    def test_grand_total_is_checked(self):
        errors = self.errors(lambda r: r[16].__setitem__(26, 600))
        self.assertTrue(any("Dòng tổng" in e["message"] for e in errors))

    def test_another_file_is_refused(self):
        self.assertTrue(rules.parse([["x"], ["y"], ["z"], ["t"]])["errors"])

    def test_title_must_give_the_year(self):
        self.assertTrue(rules.parse(book(title="SỐ LIỆU CẮT BẮP"))["errors"])

    def test_book_without_a_total_row_is_reported(self):
        rows = book()[:16]
        self.assertTrue(any("TỔNG" in e["message"] for e in rules.parse(rows)["errors"]))


class Dates(unittest.TestCase):
    def test_lan_1_is_wednesday_lan_2_is_saturday(self):
        self.assertEqual(rules.cut_date(2026, 43, 1), dt.date(2026, 10, 21))
        self.assertEqual(rules.cut_date(2026, 43, 2), dt.date(2026, 10, 24))

    def test_key_is_per_lot_week_and_lan(self):
        self.assertEqual(rules.source_key("B", 2026, 45, 2), "opening:B:2026-45:2")


class Colours(unittest.TestCase):
    def test_header_and_calendar_label_match_ignoring_case_and_marks(self):
        self.assertTrue(rules.same_colour("TRẮNG", "Trắng"))
        self.assertTrue(rules.same_colour(rules.clean_colour(" ĐỎ-XANH LÁ( RÚT)"), "Đỏ - Xanh lá"))
        self.assertFalse(rules.same_colour("ĐỎ", "Trắng"))
        self.assertFalse(rules.same_colour("", "Trắng"))


if __name__ == "__main__":
    unittest.main()
