import test from 'node:test'
import assert from 'node:assert/strict'
import {fillFor,legendFor} from '../src/map-land.js'

test('density is one hue light to dark; an uncounted lot is grey, never the lightest step',()=>{
 const steps=[1200,1600,1900,2200,2600].map(density=>fillFor({density},'density'))
 assert.equal(new Set(steps).size,5)
 assert.match(steps[0],/success-100/);assert.match(steps[4],/success-900/)
 assert.match(fillFor({density:null},'density'),/neutral-300/)
})

test('variety colour follows the variety, not its rank in the current filter',()=>{
 const context={varieties:['FHIA','VIP 126']}
 assert.equal(fillFor({variety:'VIP 126'},'variety',context),fillFor({variety:'VIP 126'},'variety',{varieties:['FHIA','VIP 126']}))
 assert.notEqual(fillFor({variety:'VIP 126'},'variety',context),fillFor({variety:'FHIA'},'variety',context))
 assert.match(fillFor({variety:null},'variety',context),/neutral-300/)
 assert.equal(legendFor('variety',context).at(-1).label,'Chưa có giống')
})

test('flowering months ahead of today, past months count as now',()=>{
 const context={today:'2026-10-21'}
 assert.match(fillFor({flowering_month:'2026-10'},'flowering',context),/info-200/)
 assert.match(fillFor({flowering_month:'2026-09'},'flowering',context),/info-200/)
 assert.match(fillFor({flowering_month:'2026-11'},'flowering',context),/info-400/)
 assert.match(fillFor({flowering_month:'2027-06'},'flowering',context),/info-800/)
 assert.equal(legendFor('zone'),null,'zones keep the zone legend of the map')
})
