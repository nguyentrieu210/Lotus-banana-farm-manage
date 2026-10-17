"""Non-mutating forecast contract tests (runnable with bench execute)."""
from datetime import timedelta
import frappe
from frappe.utils import getdate
from lotus_farm.vip126_timeline import _pick_anchor, _year_rows, SCENARIOS


def smoke():
    cfg = SCENARIOS["base"]
    b = frappe._dict(
        farm="LOTUS-222", name="TEST-A5", block_code="A5", variety="VIP 126",
        lotus_tree_count=9118, lotus_estimated_flowering_date="2026-11-01",
        planting_date=None
    )
    flower = _pick_anchor(b, [], cfg)
    assert str(flower["harvest_date"]) == "2027-01-24", flower
    first = _year_rows(b,flower,cfg,getdate("2026-10-01"),getdate("2029-09-30"))
    assert len(first)>=3
    assert first[0]["expected_date"] == "2027-01-24"
    assert all(first[i]["expected_date"] < first[i+1]["expected_date"] for i in range(len(first)-1))
    selection = {
        "priority":2,"source":"sucker","source_name":"Đã chọn chồi",
        "source_date":"2026-12-01","harvest_date":getdate("2026-12-01")+timedelta(days=245),
        "bunches":500,"observed":True,"batch":"TEST-001","cycle":"TEST-C1",
    }
    chosen=_pick_anchor(b,[selection],cfg)
    changed = _year_rows(b,chosen,cfg,getdate("2026-10-01"),getdate("2029-09-30"))
    assert chosen["source"]=="sucker"
    assert changed[0]["expected_date"] != first[0]["expected_date"]
    assert changed[1]["expected_date"] != first[1]["expected_date"]
    assert changed[1]["expected_date"] == str(getdate(changed[0]["expected_date"])+timedelta(days=270))
    shoot = {
        **selection,"priority":3,"source":"shoot","source_name":"Đã trổ",
        "source_date":"2027-01-20",
        "harvest_date":getdate("2027-01-20")+timedelta(days=84),
        "bunches":420,
    }
    latest=_pick_anchor(b,[selection,shoot],cfg)
    assert latest["source"]=="shoot"
    harvested = {
        **selection,"priority":5,"source":"harvest_actual",
        "source_name":"Đã thu hoạch","source_date":"2027-06-01",
        "harvest_date":getdate("2027-06-01"),"bunches":390,
    }
    final=_pick_anchor(b,[selection,shoot,harvested],cfg)
    assert final["source"]=="harvest_actual"
    future=_year_rows(b,final,cfg,getdate("2026-10-01"),getdate("2029-09-30"))
    assert all(r["expected_date"] > "2027-06-01" for r in future)
    assert str(b.lotus_estimated_flowering_date)=="2026-11-01"
    assert not b.planting_date
    assert all(r["commit_ready"] is False for r in first+changed+future)
    return {"tests":"passed","stage_chain":"flower -> sucker -> shoot -> actual harvest",
            "first_date":first[0]["expected_date"],
            "after_sucker":changed[0]["expected_date"],
            "after_sucker_next_ratoon":changed[1]["expected_date"],
            "after_shoot":str(latest["harvest_date"]),
            "after_actual_next_ratoon":future[0]["expected_date"]}
