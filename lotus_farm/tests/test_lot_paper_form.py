import importlib.util
import pathlib
import unittest

# Load by path: the rules are pure and this test must run without a bench.
_spec = importlib.util.spec_from_file_location("lot_paper_form_rules", pathlib.Path(__file__).parents[1] / "lot_paper_form_rules.py")
rules = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rules)

WORKS = {"CB": {"label": "Cắt bắp", "stage": "Cut Bud"}, "CH": {"label": "Chích bắp", "stage": "Bud Injection"},
         "BB": {"label": "Bao buồng", "stage": "Bag"}, "TH": {"label": "Thu hoạch", "stage": "Harvest"}, "HB": {"label": "Hủy buồng", "stage": "Reject"},
         "CL": {"label": "Cắt lá", "stage": "", "uom": "Ha"}, "LC": {"label": "Làm cỏ", "stage": "", "uom": "Ha"}}
LOTS = [{"block": "b5", "code": "A5", "zone": "A", "rounds": ["CL"]}, {"block": "b6", "code": "A6", "zone": "A", "rounds": []},
        {"block": "b10", "code": "A10", "zone": "A", "rounds": ["CL", "LC"]}]


def form():
    return rules.layout(LOTS, WORKS, "Cam")


def col(form_, work):
    return next(c["code"] for c in form_["columns"] if c["work_type"] == work)


class Layout(unittest.TestCase):
    def test_bunch_stages_first_with_the_ribbon_of_the_day_then_the_work_given(self):
        f = form()
        self.assertEqual([c["label"] for c in f["columns"]], ["Cắt bắp (màu Cam)", "Chích bắp", "Bao buồng", "Thu hoạch", "Hủy buồng", "Cắt lá (Ha)", "Làm cỏ (Ha)"])
        self.assertEqual([c["code"] for c in f["columns"]], ["C1", "C2", "C3", "C4", "C5", "C6", "C7"])
        self.assertEqual([r["code"] for r in f["rows"]], ["A5", "A6", "A10"])
        self.assertEqual(f["expected"], [["A10", "C6"], ["A10", "C7"], ["A5", "C6"]])


class Check(unittest.TestCase):
    def test_a_clean_reading_gives_lines_marked_unchecked(self):
        f = form()
        lines, notes = rules.check(f, [{"lot": "A5", "col": col(f, "CB"), "qty": 12}, {"lot": "a5", "col": col(f, "CL"), "qty": "1,5", "done": True},
                                       {"lot": "A10", "col": col(f, "CL"), "qty": 2}, {"lot": "A10", "col": col(f, "LC"), "done": True}])
        self.assertEqual([(l["code"], l["work_type"], l["qty"], l["done"]) for l in lines],
                         [("A5", "CB", 12.0, False), ("A5", "CL", 1.5, True), ("A10", "CL", 2.0, False), ("A10", "LC", None, True)])
        self.assertTrue(all(l["flags"] == [rules.UNCHECKED] for l in lines))
        self.assertEqual(notes, [])

    def test_a_lot_or_a_column_not_on_the_form_is_a_note_not_a_line(self):
        f = form()
        lines, notes = rules.check(f, [{"lot": "B9", "col": "C1", "qty": 3}, {"lot": "A5", "col": "C9", "qty": 3}])
        self.assertEqual(lines, [])
        self.assertEqual(len(notes), 5, notes)
        self.assertIn("lô \"B9\" không in sẵn", notes[0])
        self.assertIn("cột \"C9\" không có trên phiếu", notes[1])
        self.assertIn("Lô A5: phiếu in việc \"Cắt lá (Ha)\" mà ô trống", notes[4], "every việc printed for a lô and left empty is named")

    def test_bunches_not_whole_more_than_left_and_harvest_without_kg_are_flagged(self):
        f = form()
        harvest = col(f, "Harvest" and "TH")
        lines, _ = rules.check(f, [{"lot": "A6", "col": col(f, "BB"), "qty": 12.5}, {"lot": "A6", "col": harvest, "qty": 40}],
                               left={("A6", harvest): 30, ("A6", col(f, "BB")): 50}, colours={("A6", harvest): "red43", ("A6", col(f, "BB")): "red43"})
        bag, cut = lines
        self.assertIn("Số buồng không phải số nguyên (12.5)", bag["flags"])
        self.assertIn("Vượt số còn lại (30)", cut["flags"])
        self.assertIn("Thiếu kg", cut["flags"])
        self.assertEqual(cut["bunch_tag"], "red43")

    def test_a_colour_that_cannot_be_told_and_a_reject_without_reason_need_the_reviewer(self):
        f = form()
        lines, _ = rules.check(f, [{"lot": "A6", "col": col(f, "HB"), "qty": 2}, {"lot": "A6", "col": col(f, "TH"), "qty": 5, "kg": 100}])
        self.assertEqual(lines[0]["flags"], [rules.UNCHECKED, "Chọn màu dây", "Chọn lý do hủy"])
        self.assertIn("Chọn màu dây", lines[1]["flags"])

    def test_empty_cells_are_skipped_and_a_cell_read_twice_counts_once(self):
        f = form()
        lines, notes = rules.check(f, [{"lot": "A5", "col": col(f, "CB"), "qty": None}, {"lot": "A6", "col": col(f, "CB"), "qty": 3},
                                       {"lot": "A6", "col": col(f, "CB"), "qty": 4}])
        self.assertEqual([(l["code"], l["qty"]) for l in lines], [("A6", 3.0)])
        self.assertTrue(any("đọc được hai lần" in n for n in notes))


if __name__ == "__main__":
    unittest.main()
