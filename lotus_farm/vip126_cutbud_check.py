"""No-write tests of 17d flowering-to-cut and 60–70d cut-to-harvest."""
import frappe
from frappe.utils import getdate
from lotus_farm.vip126_timeline import SCENARIOS, _validate_milestones
from lotus_farm.vip126_trial import _trial_event_anchor, _flowering_rows, TRIAL


def smoke():
    _validate_milestones()
    assert [SCENARIOS[k]["cut_to_harvest"] for k in ("low","base","high")] == [70,65,60]
    assert [SCENARIOS[k]["flower_to_harvest"] for k in ("low","base","high")] == [87,82,77]
    block=frappe._dict(name="TEST-A5",farm="LOTUS-222",block_code="A5",variety="VIP 126")
    config=SCENARIOS["base"]
    tr=TRIAL["base"]
    shoot=_trial_event_anchor("shoot","2026-11-01",1000,"base")
    rows=_flowering_rows(block,shoot,config,tr,getdate("2026-10-01"),getdate("2029-09-30"))
    first=[r for r in rows if r["cycle_no"]==1]
    assert [r["flowering_share_percent"] for r in first]==[20,60,20]
    assert [r["cut_date"] for r in first]==["2026-11-18","2026-12-18","2027-01-18"]
    assert [r["expected_date"] for r in first]==["2027-01-22","2027-02-21","2027-03-24"]
    assert [r["harvest_earliest_date"] for r in first]==["2027-01-17","2027-02-16","2027-03-19"]
    assert [r["harvest_latest_date"] for r in first]==["2027-01-27","2027-02-26","2027-03-29"]
    cut=_trial_event_anchor("cut","2026-11-18",1000,"base")
    actual_cut=_flowering_rows(block,cut,config,tr,getdate("2026-10-01"),getdate("2029-09-30"))
    primary=[r for r in actual_cut if r["cycle_no"]==1]
    assert len(primary)==1
    assert primary[0]["cut_date"]=="2026-11-18"
    assert primary[0]["expected_date"]=="2027-01-22"
    assert primary[0]["harvest_earliest_date"]=="2027-01-17"
    assert primary[0]["harvest_latest_date"]=="2027-01-27"
    assert all(r["commit_ready"] is False for r in rows+actual_cut)
    return {"passed":True,"flowering_to_cut_days":17,
            "cut_to_harvest_days":[60,65,70],
            "base_flower_to_harvest_days":82,
            "cut_dates":[r["cut_date"] for r in first],
            "base_harvest_dates":[r["expected_date"] for r in first],
            "actual_cut_does_not_add_17_twice":True}
