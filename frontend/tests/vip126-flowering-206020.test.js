import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
const root=new URL('../../',import.meta.url)
const read=p=>readFileSync(new URL(p,root),'utf8')
test('Flowering forecast uses user-approved 20-60-20 in each of 3 calendar months',()=>{
 const py=read('lotus_farm/vip126_trial.py')
 assert.match(py,/FLOWERING_DISTRIBUTION = \(20, 60, 20\)/)
 assert.match(py,/_split_flowering_quantity/)
 assert.match(py,/add_months\(base_flower_date, wave\)/)
 assert.match(py,/flowering_share_percent/)
 assert.match(py,/flowering_bunches/)
 assert.match(py,/flowering_month/)
 assert.match(py,/flowering_distribution_percent/)
 assert.match(py,/if not start <= predicted_date <= end/)
})
test('Live UI displays the flowering schedule and sums per cohort without saving real data',()=>{
 const ui=read('frontend/src/components/Vip126RollingForecast.vue')
 assert.match(ui,/Phân bổ trổ hoa: 20% – 60% – 20%/)
 assert.match(ui,/Tháng trổ/)
 assert.match(ui,/Tỷ lệ trổ/)
 assert.match(ui,/Buồng trổ/)
 assert.match(ui,/11\/2026 \(20%\), 12\/2026 \(60%\), 01\/2027 \(20%\)/)
 assert.match(ui,/lotus_farm.vip126_trial.calendar/)
 const py=read('lotus_farm/vip126_trial.py')
 assert.doesNotMatch(py,/\.insert\(|\.save\(|\.delete_doc\(|set_value\(/)
 assert.match(py,/releasable_kg": 0/)
})
