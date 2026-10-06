import ast
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestSchema(unittest.TestCase):
    def test_doctype_fields_and_select_options(self):
        for path in (ROOT / "lotus_farm/lotus_farm/doctype").glob("*/*.json"):
            with self.subTest(path=path):
                doc = json.loads(path.read_text())
                fields = [f["fieldname"] for f in doc["fields"]]
                self.assertEqual(len(fields), len(set(fields)))
                self.assertEqual(set(doc["field_order"]), set(fields))
                self.assertTrue(doc.get("istable") or doc.get("permissions"))
                for f in doc["fields"]:
                    if f["fieldtype"] == "Select":
                        self.assertNotIn("\\n", f.get("options", ""))

    def test_all_python_parses(self):
        for path in ROOT.rglob("*.py"):
            if ".git" not in path.parts:
                ast.parse(path.read_text(), filename=str(path))

    def test_raw_reading_and_event_keys_are_unique(self):
        for slug, field in [("bunch_operation", "client_event_id"), ("scale_reading", "event_key")]:
            doc = json.loads((ROOT / f"lotus_farm/lotus_farm/doctype/{slug}/{slug}.json").read_text())
            self.assertEqual(next(f for f in doc["fields"] if f["fieldname"] == field)["unique"], 1)

    def test_exact_sales_order_line_required_by_controller(self):
        doc = json.loads(
            (ROOT / "lotus_farm/lotus_farm/doctype/forecast_allocation/forecast_allocation.json").read_text()
        )
        self.assertIn("sales_order_item", doc["field_order"])
        self.assertEqual(doc["istable"], 1)  # Existing child table identity preserved for migration.
