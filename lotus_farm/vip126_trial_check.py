"""Read-only test suite for historical OneDrive-based what-if scenario."""
from datetime import timedelta
from frappe.utils import getdate
from lotus_farm.vip126_trial import (
    _counts, _trial_event_anchor, _synthetic_anchor, TRIAL, TRIAL_FLOWERING,
)
from lotus_farm.vip126_timeline import _year_rows, SCENARIOS
import frappe


def smoke():
    scenario="base"
    c=TRIAL[scenario]
    # 1000 cut -> 980 harvested -> 960 processed -> 16320kg
    anchor=_trial_event_anchor("cut","2026-11-20",1000,scenario)
    actual=_counts(anchor,1,c)
    assert actual["cut_bunches"]==1000,actual
    assert actual["harvest_bunches"]==980,actual
    assert actual["preprocessed_bunches"]==960,actual
    assert actual["packed_kg"]==16320,actual
    assert actual["gross_kg"]==20000,actual
    farm_block=frappe._dict(name="TEST-A9",farm="LOTUS-222",block_code="A9",
                           variety="VIP 126",lotus_estimated_flowering_date="2026-11-01")
    original=_synthetic_anchor(farm_block,1000,scenario)
    before=_year_rows(farm_block,original,SCENARIOS[scenario],
        getdate("2026-10-01"),getdate("2029-10-01"))
    assert before[0]["expected_date"]=="2027-01-22"
    selected=_trial_event_anchor("sucker","2026-11-15",1000,scenario)
    after=_year_rows(farm_block,selected,SCENARIOS[scenario],
        getdate("2026-10-01"),getdate("2029-10-01"))
    assert after[0]["expected_date"]!=before[0]["expected_date"]
    assert after[1]["expected_date"]!=before[1]["expected_date"]
    assert after[1]["expected_date"]==str(
        getdate(after[0]["expected_date"])+timedelta(days=270))
    harvested=_trial_event_anchor("harvest_actual","2027-01-10",1000,scenario)
    future=_year_rows(farm_block,harvested,SCENARIOS[scenario],
        getdate("2026-10-01"),getdate("2029-10-01"))
    assert future[0]["expected_date"]>"2027-01-10"
    assert all(row["commit_ready"] is False for row in before+after+future)
    assert len(TRIAL_FLOWERING)==5
    return {"pass":True,"cut_1000_to_packed_kg":actual["packed_kg"],
            "before_first_harvest":before[0]["expected_date"],
            "after_sucker_first_harvest":after[0]["expected_date"],
            "after_sucker_next":after[1]["expected_date"],
            "after_mock_harvest_next":future[0]["expected_date"]}