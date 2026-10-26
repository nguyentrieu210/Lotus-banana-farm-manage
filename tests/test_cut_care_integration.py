"""Static UAT guards for staged Book2 care-plan integration.

These are source-structure checks, not a substitute for bench migrate + site UAT.
"""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CarePlanIntegrationGuards(unittest.TestCase):
    def test_cut_scope_links_exist_and_are_not_required_for_legacy_rows(self):
        f = json.loads((ROOT / "lotus_farm/lotus_farm/doctype/lotus_cut_journal_entry/lotus_cut_journal_entry.json").read_text(encoding="utf-8"))
        fields = {x["fieldname"]: x for x in f["fields"]}
        for code, target in (("farm_block", "Farm Block"), ("crop_cycle", "Crop Cycle"), ("plan_cohort", "Plan Cohort")):
            self.assertEqual(fields[code]["fieldtype"], "Link")
            self.assertEqual(fields[code]["options"], target)
            self.assertNotEqual(fields[code].get("reqd"), 1)
        self.assertEqual(fields["entry_key"]["unique"], 1)

    def test_draft_keeps_source_and_doctype_remains_unsubmitted(self):
        f = json.loads((ROOT / "lotus_farm/lotus_farm/doctype/daily_work_plan_line/daily_work_plan_line.json").read_text(encoding="utf-8"))
        fields = {x["fieldname"]: x for x in f["fields"]}
        self.assertEqual(fields["lotus_forecast_sources"]["fieldtype"], "Long Text")
        code = (ROOT / "lotus_farm/cut_forecast.py").read_text(encoding="utf-8")
        section = code.split("def create_care_plan_draft(", 1)[1].split("# Parameters ---", 1)[0]
        self.assertIn("fingerprint", section)
        self.assertIn('"Daily Work Plan", "create"', section)
        self.assertIn("doc.insert()", section)
        self.assertNotIn(".submit(", section)
        self.assertIn("lotus_forecast_sources", section)
        self.assertIn('if r["blocking_issue"]', section)
        self.assertIn('material_codes = {"CV021"', code)
        self.assertIn('approval_state":"Approved"', code)
        self.assertIn('row["norm_profile"]', code)
        self.assertIn('row["work_code"] == "CV021"', code)
        self.assertIn("material_summary", code)

    def test_ui_has_manual_mapping_and_calendar_actions(self):
        ui = (ROOT / "frontend/src/CutForecastApp.vue").read_text(encoding="utf-8")
        for text in ("assign_entry_scope", "preview_care_plan", "create_care_plan_draft",
                     "modified:String(scopeEntry.value.modified)", "scopeForm.farm_block", "Lịch chăm sóc theo lô"):
            self.assertIn(text, ui)


if __name__ == "__main__":
    unittest.main()
