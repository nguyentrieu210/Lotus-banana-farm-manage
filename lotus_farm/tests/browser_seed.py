"""Disposable CI-only fixture for the browser test against a running Frappe site."""
import json
from pathlib import Path
import frappe
from lotus_farm.tests.test_brd import TestBRDOnSite


def seed():
    TestBRDOnSite.setUpClass()
    case=TestBRDOnSite();case.setUp()
    plan,_,_=case.daily_plan(material=False)
    team=case.make('Work Team',farm=case.farm,team_code='BROWSER-'+case.tag,team_name='Browser team')
    allocation=case.make('Labor Allocation',**case.daily_scope(),work_plan=plan.name,work_plan_line=plan.lines[0].name,
        work_team=team.name,allocated_workdays=32,allocation_note='32 people for the test day')
    allocation.submit()
    frappe.db.commit()
    data=dict(farm=case.farm,company=case.company,plot=case.plot,plan=plan.name,task=plan.lines[0].name,work_name='Bag bunches')
    Path('/tmp/lotus-console-seed.json').write_text(json.dumps(data))
    return data
