import datetime as dt
import unittest

from lotus_farm.block_forecast_engine import forecast, portions, months_after, distribute_daily
from lotus_farm.forecast_parameters import validate, approved_version, DEFAULTS

def block(name="A1",trees=1000,flower="2026-11-01",status="Unverified"):
    return dict(name=name,active=1,farm_zone="A",lotus_tree_count=trees,
                lotus_estimated_flowering_date=flower,forecast_count_source=status)

def cohort(name="C1",number=2,anchor="Selection",when="2026-11-01",
           basis="Selected Suckers",qty=1000):
    return dict(name=name,farm_block="A1",crop_cycle="CYCLE2",
                cohort_code=name,approval_state="Approved",version=1,cycle_no=number,
                anchor=anchor,anchor_date=when,quantity_basis=basis,
                planned_qty=qty,modified="2026-10-26")

def profile(**overrides):
    return dict(dict(name="PROFILE1",approval_state="Approved",active=1,
                     farm_block=None,version=1,valid_from="2026-01-01"),**overrides)

class BlockForecastTests(unittest.TestCase):
    def test_four_wave_allocation_and_no_cutting_dependency(self):
        result=forecast([block()],[],include_daily=True)
        rows=result["rows"]
        self.assertEqual([x["tree_qty"] for x in rows],[170,400,250,180])
        self.assertEqual(sum(x["tree_qty"] for x in rows),1000)
        self.assertEqual(len(result["daily_rows"]),120)
        self.assertEqual(rows[0]["source"],"Số cây gốc đợt trước đã chốt")
        self.assertEqual(rows[0]["parameter_status"],"Unapproved Book2 scenario")
        self.assertEqual((dt.date.fromisoformat(rows[0]["cut_bud_date"])
                        -dt.date.fromisoformat(rows[0]["inject_date"])).days,16)
        self.assertEqual((dt.date.fromisoformat(rows[0]["harvest_date"])
                        -dt.date.fromisoformat(rows[0]["cut_bud_date"])).days,65)
        self.assertEqual(rows[0]["flower_window_start"],"2026-11-01")
        self.assertEqual(rows[0]["flower_window_end"],"2026-11-30")

    def test_daily_and_monthly_quantity_conservation(self):
        result=forecast([block()],[],include_daily=True)
        daily=result["daily_rows"]
        self.assertEqual(sum(x["tree_qty"] for x in daily),1000)
        for field in ("bunches_shoot","bunches_cut","bunches_harvest","bunches_pack","kg_pack"):
            self.assertEqual(sum(x[field] for x in daily),sum(x[field] for x in result["rows"]),field)
        self.assertEqual(sum(x["bunches"] for x in result["monthly"]),
                         sum(x["bunches_harvest"] for x in result["rows"]))
        self.assertEqual(sum(x["packed_kg"] for x in result["monthly"]),
                         sum(x["kg_pack"] for x in result["rows"]))
        self.assertGreater(len(result["monthly"]),4) # four 30-day windows cross month boundaries
        self.assertLess(max(x["tree_qty"] for x in daily),20) # no fictitious single-day spike

    def test_approved_cohort_replaces_census_for_same_lot(self):
        rows=forecast([block()], [cohort()], profiles=[profile()])["rows"]
        self.assertEqual(len(rows),4)
        self.assertEqual(rows[0]["source"],"Plan Cohort")
        self.assertEqual(sum(r["tree_qty"] for r in rows),1000)
        self.assertEqual(rows[0]["parameter_status"],"Approved")
        self.assertEqual(rows[0]["count_status"],"Cohort Approved")
        self.assertEqual(rows[0]["cycle_no"],2)
        self.assertEqual(rows[0]["weight_kg"],20)

    def test_latest_approved_by_cycle_and_code(self):
        old=cohort(); old["planned_qty"]=200;old["name"]="v1"
        new={**old,"planned_qty":400,"version":2,"name":"v2"}
        draft={**new,"approval_state":"Draft","version":3,"name":"draft"}
        cycle1={**old,"crop_cycle":"CYCLE1","cohort_code":"C1","name":"other"}
        rows=forecast([block()],[old,new,draft,cycle1])["rows"]
        self.assertEqual(sum(r["tree_qty"] for r in rows),600)

    def test_unapproved_cohort_does_not_supersede_census(self):
        pending={**cohort(),"approval_state":"Draft"}
        result=forecast([block()], [pending])
        self.assertEqual(result["source_count"],1)
        self.assertEqual(result["rows"][0]["count_status"],"Planning Baseline")

    def test_missing_input_never_invents_density_or_tree_count(self):
        b=block(trees=None);b["area_ha"]=9;b["planting_density"]=2400
        out=forecast([b],[])
        self.assertEqual(len(out["rows"]),0)
        self.assertTrue(out["warnings"])

    def test_selection_to_first_flowers_uses_calendar_months(self):
        self.assertEqual(str(months_after("2026-11-01",6)),"2027-05-01")
        out=forecast([block()], [cohort()])
        self.assertEqual(out["rows"][0]["flower_window_start"],"2027-05-01")
        self.assertEqual(out["rows"][0]["harvest_date"],"2027-07-26")

    def test_observed_bunches_do_not_apply_per_tree_cut_rate(self):
        observed=cohort(anchor="Shooting",when="2026-11-01",basis="Bunches",qty=1000)
        wave=forecast([block()],[observed])["rows"]
        self.assertEqual(len(wave),1)
        self.assertEqual(wave[0]["bunches_cut"],1000)
        self.assertEqual(wave[0]["window_days"],1)

    def test_rate_conflict_is_capped_and_warned(self):
        p=profile(flowering_rate=.5,cut_rate_per_tree=.9)
        out=forecast([block()],[],profiles=[p])
        self.assertTrue(any("đã giới hạn" in w for w in out["warnings"]))
        self.assertTrue(all(r["bunches_cut"]<=r["bunches_shoot"] for r in out["rows"]))

    def test_profile_per_block_and_effective_version(self):
        global_p=profile(name="old-global",version=3)
        block_p=profile(name="block",farm_block="A1",version=2,wave_window_days=20)
        found=approved_version([global_p,block_p],"A1","2026-11-01")
        self.assertEqual(found["name"],"block")
        result=forecast([block()],[],profiles=[global_p,block_p],include_daily=True)
        self.assertEqual(len(result["daily_rows"]),80)
        self.assertEqual(result["rows"][0]["profile"],"block")

    def test_invalid_params_block_overlap_and_double_sucker_yield(self):
        with self.assertRaises(ValueError):validate({"wave_1_share":.2})
        with self.assertRaises(ValueError):validate({"wave_window_days":31,"wave_step_days":30})
        with self.assertRaises(ValueError):validate({"apply_sucker_yield_to_counted_trees":1})
        self.assertEqual(sum(portions(73,[.17,.40,.25,.18])),73)
        self.assertEqual(sum(distribute_daily(170,30)),170)
        self.assertEqual(len(distribute_daily(170,30)),30)

if __name__=="__main__":
    unittest.main()
