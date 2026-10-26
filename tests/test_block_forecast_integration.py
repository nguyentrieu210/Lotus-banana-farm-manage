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

    def test_source_confidence_and_cohort_wave_mode_are_fields(self):
        def fields(name):
            data=json.loads((ROOT/f"lotus_farm/lotus_farm/doctype/{name}/{name}.json").read_text(encoding="utf-8"))
            return {x["fieldname"]:x for x in data["fields"]}
        block=fields("farm_block")
        self.assertEqual(block["forecast_count_source"]["default"],"Planning Baseline")
        cohort=fields("plan_cohort")
        self.assertIn("Single Wave",cohort["forecast_distribution_mode"]["options"])

    def test_parameters_are_versioned_approved_and_immutable(self):
        from lotus_farm.forecast_parameters import DEFAULTS,validate
        self.assertEqual(len(DEFAULTS),22)
        self.assertEqual(validate(DEFAULTS)["inject_to_cut_days"],16)
        self.assertEqual(validate(DEFAULTS)["apply_sucker_yield_to_counted_trees"],0)
        doc=json.loads((ROOT/"lotus_farm/lotus_farm/doctype/lotus_block_forecast_profile/lotus_block_forecast_profile.json").read_text(encoding="utf-8"))
        fields={x["fieldname"] for x in doc["fields"]}
        self.assertTrue(set(DEFAULTS).issubset(fields))
        self.assertTrue({"version","approval_state","valid_from","valid_to","approved_by","source_reference"}.issubset(fields))
        source=(ROOT/"lotus_farm/lotus_farm/doctype/lotus_block_forecast_profile/lotus_block_forecast_profile.py").read_text(encoding="utf-8")
        self.assertIn('old.approval_state == "Approved"',source)
        self.assertIn("không được chồng ngày hiệu lực",source)

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
