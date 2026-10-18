"""No mutation: verify the 20/60/20 flowering cohort and rolling simulation."""
from datetime import timedelta
import frappe
from frappe.utils import getdate
from lotus_farm.vip126_trial import (
    FLOWERING_DISTRIBUTION, _split_flowering_quantity, _flowering_rows,
    _trial_event_anchor, TRIAL,
)
from lotus_farm.vip126_timeline import SCENARIOS


def smoke():
    assert FLOWERING_DISTRIBUTION == (20, 60, 20)
    for n in range(0, 103):
        portions=_split_flowering_quantity(n)
        assert sum(portions)==n, (n,portions)
        assert all(v>=0 for v in portions), (n,portions)
    b=frappe._dict(name="TEST-A8",farm="LOTUS-222",block_code="A8",
                   variety="VIP 126")
    cfg=SCENARIOS["base"]
    anchor=_trial_event_anchor("shoot","2026-11-01",1000,"base")
    rows=_flowering_rows(b,anchor,cfg,TRIAL["base"],
                         getdate("2026-10-01"),getdate("2029-09-30"))
    waves=[r for r in rows if r["cycle_no"]==1]
    assert len(waves)==3, waves
    assert [r["flowering_month"] for r in waves] == [
       "2026-11","2026-12","2027-01"], waves
    assert [r["flowering_share_percent"] for r in waves] == [20,60,20]
    assert [r["flowering_bunches"] for r in waves] == [200,600,200]
    assert [r["expected_date"] for r in waves]==[
       "2027-01-22","2027-02-21","2027-03-24"], waves
    assert all(r["commit_ready"] is False for r in rows)
    second=[r for r in rows if r["cycle_no"]==2]
    assert len(second)==3
    assert [r["flowering_share_percent"] for r in second]==[20,60,20]
    assert all(r["expected_date"] == str(getdate(waves[i]["expected_date"])+
         timedelta(days=270)) for i,r in enumerate(second))
    new_anchor=_trial_event_anchor("sucker","2026-12-01",1000,"base")
    reforecast=_flowering_rows(b,new_anchor,cfg,TRIAL["base"],
                              getdate("2026-10-01"),getdate("2029-09-30"))
    assert reforecast[0]["expected_date"] != rows[0]["expected_date"]
    assert [r["flowering_share_percent"] for r in reforecast if r["cycle_no"]==1] == [20,60,20]
    cut_anchor=_trial_event_anchor("cut","2027-01-10",1000,"base")
    cut_rows=_flowering_rows(b,cut_anchor,cfg,TRIAL["base"],
                            getdate("2026-10-01"),getdate("2029-09-30"))
    assert len([r for r in cut_rows if r["cycle_no"]==1])==1, cut_rows
    assert [r["flowering_share_percent"] for r in cut_rows if r["cycle_no"]==2]==[20,60,20]
    return {"passed":True,"month_shares":[20,60,20],
            "flowering_bunches":[200,600,200],
            "harvest_dates":[r["expected_date"] for r in waves],
            "second_cycle":[r["expected_date"] for r in second],
            "sucker_override":reforecast[0]["expected_date"],
            "cut_first_record_kept":cut_rows[0]["expected_date"]}