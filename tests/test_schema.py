import ast
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestSchema(unittest.TestCase):
    def test_doctype_fields_and_select_options(self):
        for path in (ROOT / "lotus_farm/lotus_farm/doctype").glob("*/*.json"):
            with self.subTest(path=path):
                doc = json.loads(path.read_text(encoding="utf-8-sig"))
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
                ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
