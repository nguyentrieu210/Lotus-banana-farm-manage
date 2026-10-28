import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
const base=new URL('../../',import.meta.url)
const read=p=>readFileSync(new URL(p,base),'utf8')
test('archived zone scenario preserves its original A-D sequence and pending E',()=>{
 const py=read('lotus_farm/vip126_zone_plan.py')
 assert.match(py,/CONFIRMED_SEQUENCE = \("A", "B", "C", "D"\)/)
 assert.match(py,/ZONE_A_INFERRED_PLANTING = "2026-05-01"/)
 assert.match(py,/ZONE_A_EXPECTED_FLOWERING = "2026-11-01"/)
 assert.match(py,/add_months\(ZONE_A_INFERRED_PLANTING, offset\)/)
 assert.match(py,/add_months\(ZONE_A_EXPECTED_FLOWERING, offset\)/)
 assert.match(py,/sucker_selection_estimate/)
 assert.match(py,/PENDING_ZONE = "E"/)
 assert.match(py,/ESTIMATE_NOT_OBSERVED/)
})
test('retired zone migration cannot overwrite shared farm dates',()=>{
 const py=read('lotus_farm/vip126_zone_plan.py')
 const command=py.split('def apply_zone_estimates():')[1].split('\ndef ')[0]
 assert.match(command,/frappe\.throw\(/)
 assert.match(command,/Công cụ lịch khu cũ đã ngừng/)
 assert.doesNotMatch(command,/\.save\(|\.insert\(|set_value\(|\.commit\(/)
 const shared=read('lotus_farm/block_forecast.py').split('def sync_block_dates(')[1].split('\ndef ')[0]
 assert.match(shared,/lotus_estimated_sucker_selection_date=doc\.get\('lotus_estimated_flowering_date'\)/)
 assert.doesNotMatch(shared,/planting_date\s*=|timedelta/)
})
test('Trial data uses saved inferred planting before simulating missing E',()=>{
 const py=read('lotus_farm/vip126_trial.py')
 assert.match(py,/lotus_inferred_planting_date/)
 assert.match(py,/inferred_plant/)
 assert.match(py,/planned_dates\(zone\)/)
 assert.match(py,/flowering_distribution_percent/)
 assert.match(py,/commit_ready": False/)
 const ui=read('frontend/src/components/Vip126RollingForecast.vue')
 assert.match(ui,/ZonePlantingSchedule/)
 assert.match(ui,/Phân bổ trổ hoa: 20% – 60% – 20%/)
})
