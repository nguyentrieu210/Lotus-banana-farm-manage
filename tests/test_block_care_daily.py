"""Unit consistency: spread forecast into DAILY care steps, not single spikes."""
import datetime as dt
import unittest
from lotus_farm.block_forecast_engine import forecast
from lotus_farm.block_forecast import _work_events

class CareDailyTests(unittest.TestCase):
    def test_four_sprays_cut_and_harvest_conserve_daily_quantity(self):
        b=dict(name="A1",active=1,farm_zone="A",lotus_tree_count=1000,
               lotus_estimated_flowering_date="2026-11-01",
               forecast_count_source="Census Confirmed")
        waves=forecast([b],[],include_daily=True)
        work=_work_events(waves["daily_rows"],dt.date(2026,11,1),dt.date(2027,6,1))
        self.assertEqual(len({r["schedule_key"] for r in work}),len(work))
        for code,basis in [("CV020","bunches_shoot"),("CV023","bunches_shoot"),
                           ("CV025","bunches_shoot"),("CV027","bunches_shoot"),
                           ("CV024","bunches_shoot"),("CV026","bunches_shoot"),
                           ("CV028","bunches_shoot"),("CV031","bunches_cut"),
                           ("CV029","bunches_cut"),("CV034","bunches_harvest"),
                           ("CV035","bunches_harvest"),("CV036","bunches_harvest")]:
            total=sum(r["planned_qty"] for r in work if r["work_code"]==code)
            expected=sum(r[basis] for r in waves["rows"])
            self.assertEqual(total,expected,(code,total,expected))
        self.assertGreater(len([x for x in work if x["work_code"]=="CV020"]),100)
        self.assertLess(max(x["planned_qty"] for x in work if x["work_code"]=="CV020"),20)

    def test_cohort_supersedes_census_in_daily_work(self):
        b=dict(name="A1",active=1,farm_zone="A",lotus_tree_count=500,
               lotus_estimated_flowering_date="2026-11-01")
        c=dict(name="A",farm_block="A1",crop_cycle="C2",cohort_code="NEXT",
               approval_state="Approved",anchor="Selection",anchor_date="2026-05-01",
               quantity_basis="Selected Suckers",planned_qty=500,version=1)
        result=forecast([b],[c],include_daily=True)
        self.assertEqual(result["source_count"],1)
        self.assertEqual(sum(r["tree_qty"] for r in result["rows"]),500)

if __name__=="__main__":
    unittest.main()
