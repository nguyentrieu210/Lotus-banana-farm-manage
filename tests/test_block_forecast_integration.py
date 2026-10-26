"""Safety and source-isolation checks for the new block forecast flow."""
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class BlockForecastIntegrationTests(unittest.TestCase):
    def test_active_route_and_api_have_no_cut_journal_dependency(self):
        app=(ROOT/"frontend/src/App.vue").read_text(encoding="utf-8")
        ui=(ROOT/"frontend/src/BlockForecastApp.vue").read_text(encoding="utf-8")
        api=(ROOT/"lotus_farm/block_forecast.py").read_text(encoding="utf-8")
        engine=(ROOT/"lotus_farm/block_forecast_engine.py").read_text(encoding="utf-8")
        self.assertIn("import('./BlockForecastApp.vue')",app)
        self.assertNotIn("CutForecastApp",app)
        for code in (ui,api,engine):
            self.assertNotIn("lotus_cut_journal",code)
            self.assertNotIn("lotus_farm.cut_forecast.",code)
        self.assertNotIn('frappe.get_all("Lotus Cut Journal Entry"',api)
        self.assertNotIn("Lotus Cut Journal Entry",api)

    def test_legacy_documents_hidden_and_read_only(self):
        for key in ("lotus_cut_journal_entry","lotus_cut_journal_import","lotus_cut_forecast_profile"):
            info=json.loads((ROOT/f"lotus_farm/lotus_farm/doctype/{key}/{key}.json").read_text(encoding="utf-8"))
            self.assertEqual(info["hide_in_desk"],1)
            self.assertTrue(all(not p.get("write") and not p.get("create") and not p.get("delete")
                for p in info.get("permissions",[])))

    def test_new_document_pipeline_is_draft_only_with_approved_norms(self):
        code=(ROOT/"lotus_farm/block_forecast.py").read_text(encoding="utf-8")
        section=code.split("def create_care_plan_draft(",1)[1]
        self.assertIn('doc.insert()',section)
        self.assertNotIn('.submit(',section)
        self.assertIn('fingerprint!=plan["fingerprint"]',section)
        self.assertIn('"approval_state":"Approved"',code)
        self.assertIn('REQUIRES_FIELD_SURVEY',code)
        self.assertIn('MATERIAL_CODES',code)
        self.assertIn('lotus_forecast_sources',section)

if __name__=="__main__":
    unittest.main()
