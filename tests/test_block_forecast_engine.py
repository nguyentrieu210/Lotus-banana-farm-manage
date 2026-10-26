import datetime as dt
import unittest

from lotus_farm.block_forecast_engine import (
    forecast, source_rows, portions, months_after, WAVE_SHARES,
    SHOOT_TO_INJECT_DAYS, INJECT_TO_CUT_BUD_DAYS, CUT_BUD_TO_HARVEST_DAYS
)

def block(name="A1",trees=1000,flower="2026-11-01"):
    return dict(name=name,active=1,farm_zone="A",lotus_tree_count=trees,
                lotus_estimated_flowering_date=flower)

def cohort(name="C1",number=2,anchor="Selection",date="2026-11-01"):
    return dict(name=name,farm_block="A1",crop_cycle="CYCLE2",cohort_code=name,
                approval_state="Approved",version=1,cycle_no=number,
                anchor=anchor,anchor_date=date,quantity_basis="Selected Suckers",
                planned_qty=1000)

class BlockForecastTests(unittest.TestCase):
    def test_four_waves_exact_and_never_from_cut_journal(self):
        rows=forecast([block()],[])["rows"]
        self.assertEqual([x["tree_qty"] for x in rows],[170,400,250,180])
        self.assertEqual(sum(x["tree_qty"] for x in rows),1000)
        self.assertEqual(rows[0]["source"],"Kiểm kê lô + trổ dự kiến")
        self.assertEqual((dt.date.fromisoformat(rows[0]["cut_bud_date"])
                          -dt.date.fromisoformat(rows[0]["inject_date"])).days,16)
        self.assertEqual((dt.date.fromisoformat(rows[0]["harvest_date"])
                          -dt.date.fromisoformat(rows[0]["cut_bud_date"])).days,65)

    def test_approved_cohort_replaces_census_for_same_lot(self):
        selected=cohort()
        rows=forecast([block()], [selected])
        self.assertEqual(rows["source_count"],1)
        self.assertEqual(len(rows["rows"]),4)
        self.assertEqual(rows["rows"][0]["source"],"Plan Cohort đã duyệt")
        self.assertEqual(sum(r["tree_qty"] for r in rows["rows"]),1000)
        self.assertEqual(rows["rows"][0]["cycle_no"],2)

    def test_only_latest_approved_version_applies(self):
        old=cohort(); old["planned_qty"]=200;old["name"]="v1"
        new={**old,"planned_qty":400,"version":2,"name":"v2"}
        draft={**new,"approval_state":"Draft","version":3,"name":"draft"}
        rows=forecast([block()],[old,new,draft])["rows"]
        self.assertEqual(sum(r["tree_qty"] for r in rows),400)

    def test_one_source_per_lot_and_missing_source_never_invented(self):
        result=forecast([block(trees=None),block(name="B1",trees=100,flower=None)],[])
        self.assertEqual(result["rows"],[])
        self.assertEqual(len(result["warnings"]),2)

    def test_unapproved_cohort_does_not_block_farm_block_census(self):
        pending={**cohort(),"approval_state":"Draft"}
        result=forecast([block()], [pending])
        self.assertEqual(result["source_count"],1)
        self.assertEqual(result["rows"][0]["source"],"Kiểm kê lô + trổ dự kiến")

    def test_invalid_census_does_not_infer_from_area(self):
        b=block(trees=None);b["area_ha"]=9;b["planting_density"]=2400
        out=forecast([b],[])
        self.assertEqual(len(out["rows"]),0)

    def test_selection_uses_calendar_months_not_mother_cut(self):
        self.assertEqual(str(months_after("2026-11-01",6)),"2027-05-01")
        out=forecast([block()], [cohort()])
        self.assertEqual(out["rows"][0]["flower_window_start"],"2027-05-01")
        self.assertTrue(out["rows"][0]["harvest_date"].startswith("2027-"))

    def test_rounding_and_invalid_shares(self):
        self.assertEqual(portions(73),[12,29,18,14])
        self.assertEqual(portions(1000),[170,400,250,180])
        with self.assertRaises(ValueError):portions(1000,[.2,.3,.3,.3])

if __name__=="__main__":
    unittest.main()
