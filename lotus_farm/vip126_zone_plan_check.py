"""Idempotent zone planning checks against persisted Farm Block estimates."""
import frappe
from frappe.utils import add_months, getdate
from lotus_farm.vip126_zone_plan import (
    CONFIRMED_SEQUENCE, ZONE_A_INFERRED_PLANTING, ZONE_A_EXPECTED_FLOWERING,
    planned_dates, DISTRIBUTION, status, apply_zone_estimates
)
from lotus_farm.vip126_trial import TRIAL_FLOWERING


def smoke():
    assert CONFIRMED_SEQUENCE == ("A","B","C","D")
    assert DISTRIBUTION == (20,60,20)
    assert [planned_dates(z)["planting_estimate"] for z in CONFIRMED_SEQUENCE] == [
        "2026-02-19","2026-03-19","2026-04-19","2026-05-19"]
    assert [planned_dates(z)["flowering_estimate"] for z in CONFIRMED_SEQUENCE] == [
        "2026-11-01","2026-12-01","2027-01-01","2027-02-01"]
    assert planned_dates("E") is None
    assert TRIAL_FLOWERING["E"] == "2027-03-01"
    return {"passed": True,"zones":[planned_dates(z) for z in CONFIRMED_SEQUENCE],
            "E":{"source":"mock_trial_only"}}


def database_check():
    rows=frappe.get_all("Farm Block",filters={"farm":"LOTUS-222"},
          fields=["name","block_code","planting_date","lotus_tree_count",
                  "lotus_inferred_planting_date","lotus_estimated_flowering_date",
                  "lotus_estimation_basis"],limit_page_length=100)
    assert len(rows)==64, len(rows)
    counts={z:0 for z in "ABCDE"}
    saved=0
    observed_count=sum(bool(r.planting_date) for r in rows)
    for row in rows:
        z=row.block_code[0]
        counts[z]+=1
        plan=planned_dates(z)
        if plan:
            assert str(row.lotus_inferred_planting_date)==plan["planting_estimate"],row
            assert str(row.lotus_estimated_flowering_date)==plan["flowering_estimate"],row
            assert "LOTUS-ZONE-SEQUENCE-20261018" in (row.lotus_estimation_basis or "")
            saved+=1
        else:
            assert not row.lotus_inferred_planting_date
            assert not row.lotus_estimated_flowering_date
    assert counts=={"A":13,"B":12,"C":14,"D":12,"E":13},counts
    assert saved==51,saved
    assert observed_count==0,observed_count
    return {"passed":True,"lots":64,"lots_with_estimate":saved,
            "lots_pending":counts["E"],"actual_planting_date_count":observed_count,
            "zone_lots":counts,
            "counted_lots":sum(int(r.lotus_tree_count or 0)>0 for r in rows)}
