import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
const root=new URL('../../',import.meta.url)
const read=p=>readFileSync(new URL(p,root),'utf8')

test('Photo boards and manager-confirmed A12 count sum to exactly 105632 for A',()=>{
 const ev=read('lotus_farm/vip126_evidence.py')
 for(const [code,count] of Object.entries({A1:6830,A2:8568,A3:8060,A4:8743,A12:10148})){
   assert.match(ev,new RegExp('"'+code+'": \\{"count": '+count))
 }
 assert.match(ev,/EXPECTED_A_TOTAL = 105632/)
 assert.match(ev,/EXPECTED_FARM_TOTAL = 269353/)
 assert.match(ev,/if current not in \(0, evidence\["count"\]\):/)
 assert.match(ev,/doc\.lotus_tree_count_source = evidence\["source"\]/)
})
test('Census reimport must not wipe photo values or reset corrected planting dates',()=>{
 const live=read('lotus_farm/vip126_live.py')
 assert.match(live,/if census_from_excel is not None and int\(doc\.get\("lotus_tree_count"\) or 0\) == 0/)
 assert.doesNotMatch(live,/updates\.update\(lotus_estimated_flowering_date/)
 assert.doesNotMatch(live,/updates\.update\(planting_date/)
 const preview=read('lotus_farm/forecast_import_preview.py')
 assert.match(preview,/existing\.lotus_tree_count or 0/)
 assert.match(preview,/existing\.lotus_tree_count_source/)
})
test('Calendar month planting -6 for first bloom; sucker stage starts own clock',()=>{
 const zone=read('lotus_farm/vip126_zone_plan.py')
 assert.match(zone,/ZONE_A_INFERRED_PLANTING = "2026-05-01"/)
 assert.match(zone,/add_months\(ZONE_A_INFERRED_PLANTING, offset\)/)
 assert.match(zone,/timedelta\(days=90\)/)
 assert.match(zone,/lotus_estimated_sucker_selection_date/)
 const timeline=read('lotus_farm/vip126_timeline.py')
 assert.match(timeline,/add_months\(r\.selection_date,6\)/)
 assert.match(timeline,/add_months\(planting,6\)/)
 const trial=read('lotus_farm/vip126_trial.py')
 assert.match(trial,/add_months\(anchor_day, 6\)/)
 assert.match(trial,/sucker_selection_after_planting_days": 90/)
 const profile=read('lotus_farm/vip126_profile.py')
 assert.match(profile,/sync_six_month_trial_draft/)
 assert.match(profile,/blocked_manual_edit/)
 assert.match(profile,/doc\.approval_state!="Draft"/)
})
