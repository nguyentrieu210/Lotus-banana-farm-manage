"""Safety and source-isolation checks for the new block forecast flow."""
import inspect
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class BlockForecastIntegrationTests(unittest.TestCase):
    def test_active_route_is_the_block_forecast(self):
        app=(ROOT/"frontend/src/App.vue").read_text(encoding="utf-8")
        self.assertIn("import('./BlockForecastApp.vue')",app)
        self.assertNotIn("CutForecastApp",app)

    def test_the_lot_and_the_lot_ledger_are_the_only_sources(self):
        from lotus_farm.block_forecast_engine import forecast,source_rows
        self.assertEqual(list(inspect.signature(source_rows).parameters),["blocks"])
        self.assertEqual(list(inspect.signature(forecast).parameters)[:2],["blocks","from_date"])
        api=(ROOT/"lotus_farm/block_forecast.py").read_text(encoding="utf-8")
        self.assertIn('frappe.get_list("Farm Block"',api)
        self.assertIn("bunch_rows(",api)
        # Every other document the forecast reads is a parameter set, a variety name or a ribbon label.
        read=set()
        for call in ("get_list","get_all","get_doc","get_value","get_meta","has_permission"):
            for part in api.split(call+"(")[1:]:
                read.add(part.lstrip()[1:].split(part.lstrip()[0])[0])
        self.assertEqual(read,{"Farm","Farm Block","Lotus Block Forecast Profile","Banana Variety","Bunch Tag"})

    def test_source_confidence_is_a_field_of_the_lot(self):
        data=json.loads((ROOT/"lotus_farm/lotus_farm/doctype/farm_block/farm_block.json").read_text(encoding="utf-8"))
        block={x["fieldname"]:x for x in data["fields"]}
        self.assertEqual(block["forecast_count_source"]["default"],"Planning Baseline")
        source=(ROOT/"lotus_farm/block_forecast.py").read_text(encoding="utf-8")
        engine=(ROOT/"lotus_farm/block_forecast_engine.py").read_text(encoding="utf-8")
        self.assertIn('"Planning Baseline"',engine)
        self.assertNotIn("Số cây chưa được xác nhận kiểm kê",source)

    def test_parameters_are_versioned_approved_and_immutable(self):
        from lotus_farm.forecast_parameters import DEFAULTS,validate
        self.assertEqual(len(DEFAULTS),24)
        self.assertEqual(validate(DEFAULTS)["inject_to_cut_days"],16)
        self.assertEqual(validate(DEFAULTS)["apply_sucker_yield_to_counted_trees"],0)
        doc=json.loads((ROOT/"lotus_farm/lotus_farm/doctype/lotus_block_forecast_profile/lotus_block_forecast_profile.json").read_text(encoding="utf-8"))
        fields={x["fieldname"] for x in doc["fields"]}
        self.assertTrue(set(DEFAULTS).issubset(fields))
        self.assertTrue({"version","approval_state","valid_from","valid_to","approved_by","source_reference"}.issubset(fields))
        source=(ROOT/"lotus_farm/lotus_farm/doctype/lotus_block_forecast_profile/lotus_block_forecast_profile.py").read_text(encoding="utf-8")
        self.assertIn('old.approval_state == "Approved"',source)
        self.assertIn("không được chồng ngày hiệu lực",source)

    def test_forecast_no_longer_writes_care_plans(self):
        code=(ROOT/"lotus_farm/block_forecast.py").read_text(encoding="utf-8")
        self.assertNotIn("def create_care_plan_draft(",code)
        self.assertNotIn("def care_plan_preview(",code)
        self.assertIn('"approval_state":"Approved"',code)

if __name__=="__main__":
    unittest.main()
