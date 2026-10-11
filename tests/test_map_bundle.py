import copy
import unittest
from pathlib import Path
import json

from lotus_farm.map_bundle import MapBundleError, validate_bundle


def square(x=106.8, y=11.6):
    return {"type": "Polygon", "coordinates": [[
        [x, y], [x + .0001, y], [x + .0001, y + .0001],
        [x, y + .0001], [x, y]]]
    }


def fixture():
    size = {"A": 42, "B": 40, "C": 41, "D": 41, "E": 41}
    block_count = {"A": 13, "B": 12, "C": 14, "D": 12, "E": 13}
    blocks = [
        dict(code=zone + str(i), area_ha_pdf=215.16 / 64,
             irrigation_codes=[], geometry=square())
        for zone, count in block_count.items() for i in range(1, count + 1)
    ]
    by_code = {b["code"]: b for b in blocks}
    plots = []
    for zone, count in size.items():
        for i in range(1, count + 1):
            code = zone + str(i)
            parent = zone + str(1 + (i - 1) % block_count[zone])
            by_code[parent]["irrigation_codes"].append(code)
            plots.append(dict(code=code, parent_block=parent,
                              candidate_blocks=[parent], area_ha_pdf=1.0,
                              boundary_method="vector-enclosed",
                              needs_manual_review=False, geometry=square()))
    by_plot = {p["code"]: p for p in plots}
    duplicates = {"A35": "A5", "C17": "C6", "C24": "C13", "E7": "E10"}
    for code, second in duplicates.items():
        by_code[second]["irrigation_codes"].append(code)
        by_plot[code]["candidate_blocks"].append(second)
        by_plot[code]["parent_block"] = None
        by_plot[code]["needs_manual_review"] = True
    # E6 is mentioned in a second block's note, but the table's list only has one owner.
    by_code["E6"]["irrigation_codes"].remove("E6")
    by_code["E4"]["irrigation_codes"].append("E6")
    by_plot["E6"]["candidate_blocks"] = ["E4", "E5"]
    by_plot["E6"]["parent_block"] = None
    by_plot["E6"]["needs_manual_review"] = True
    manual = ["A35", "C17", "C24", "E6", "E7"]
    return dict(format="lotus-erp-map-draft-v1", approved=False,
                requires_field_validation=True, verification="UNVERIFIED_PDF_ALIGNMENT",
                care_blocks=blocks, irrigation_plots=plots,
                manual_review=[{"code":c} for c in manual])


class MapBundleTest(unittest.TestCase):
    def test_checked_in_pdf_bundle(self):
        source = Path(__file__).resolve().parents[1] / "data" / "lotus-erp-map-draft.json"
        real = json.loads(source.read_text(encoding="utf-8"))
        summary = validate_bundle(real)
        self.assertEqual((summary["care_blocks"], summary["irrigation_plots"]), (64, 205))
        self.assertEqual(summary["direct_parent_plots"], 200)
        self.assertEqual(real["unlabelled_color_parts"], [41])
        self.assertFalse(real["approved"])
        self.assertEqual({x["code"] for x in real["manual_review"]}, {"A35", "C17", "C24", "E6", "E7"})

    def test_draft_only(self):
        source = fixture()
        self.assertEqual(validate_bundle(source)["direct_parent_plots"], 200)
        source["approved"] = True
        with self.assertRaises(MapBundleError):
            validate_bundle(source)

    def test_manual_shares_never_have_parent(self):
        source = fixture()
        next(p for p in source["irrigation_plots"] if p["code"] == "C17")["parent_block"] = "C6"
        with self.assertRaises(MapBundleError):
            validate_bundle(source)

    def test_geometry_is_lon_lat_and_closed(self):
        source = fixture()
        next(p for p in source["irrigation_plots"] if p["code"] == "A1")["geometry"]["coordinates"][0][0] = [11.6, 106.8]
        with self.assertRaises(MapBundleError):
            validate_bundle(source)


if __name__ == "__main__":
    unittest.main()
