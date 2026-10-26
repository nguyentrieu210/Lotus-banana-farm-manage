import test from 'node:test'
import assert from 'node:assert/strict'
import {allocate,day,simulate} from '../src/plan-norm-engine.js'

test('Book2 four-wave allocation follows Excel rounding, last wave balances',()=>{
 assert.deepEqual(allocate(1000,[17,40,25,18]),[170,400,250,180])
 assert.deepEqual(allocate(73,[17,40,25,18]),[12,29,18,14])
 assert.deepEqual(allocate(1001,[17,40,25,18]),[170,400,250,181])
 assert.throws(()=>allocate(1000,[17,40,25,19]),/100%/)
 // Legacy 3-wave mode remains compatible with older scenarios.
 assert.deepEqual(allocate(1001,[20,60,20]),[200,600,201])
})

const work={name:'W',work_name:'Cắt bắp',uom:'Buồng',productivity_per_workday:100,
 allow_daywork:1,allow_piecework:1,piecework_rate:2000}
const payload={
 blocks:[{name:'B',farm:'F',area_ha:5}],
 cohorts:[{name:'C',farm:'F',farm_block:'B',cohort_code:'C',cohort_name:'Đợt 1',
   anchor:'Selection',anchor_date:'2026-01-01',quantity_basis:'Bunches',planned_qty:1000,
   approval_state:'Approved',version:1}],
 profiles:[{name:'P',farm:'F',approval_state:'Approved',active:1,
  valid_from:'2025-01-01',sucker_to_harvest_days:250,
  shooting_to_harvest_days:82,cut_bud_to_harvest_days:65,
  avg_bunch_weight_kg:20,bunch_survival_rate_percent:100,quality_pass_rate_percent:100,packout_rate_percent:100}],
 rules:[{name:'R',farm:'F',work_type:'W',anchor:'Cut Bud',offset_days:0,
   quantity_basis:'Bunches',approval_state:'Approved'}],
 works:[work],norms:[],norm_lines:{}
}
test('four waves use 30-day windows and labor daywork / piecework are alternatives',()=>{
 const result=simulate(payload,{from:'2026-01-01',months:18,
   flowerShares:[17,40,25,18],dayworkRate:290000,absenceReserve:0.1,
   repeatRatoons:false})
 assert.equal(result.harvests.length,4)
 assert.equal(result.events.length,4)
 assert.equal(result.events.reduce((a,e)=>a+e.qty,0),1000)
 assert.deepEqual(result.harvests.map(e=>e.bunches),[170,400,250,180])
 assert.equal(result.harvests[1].date,day(result.harvests[0].date,30))
 assert.equal(result.harvests[2].date,day(result.harvests[1].date,30))
 assert.equal(Math.round(result.events.reduce((a,e)=>a+e.required_workdays,0)*100)/100,10)
 assert.equal(result.events.reduce((a,e)=>a+e.daywork_cost,0),2900000)
 assert.equal(result.events.reduce((a,e)=>a+e.piecework_cost,0),2000000)
 assert.ok(Math.abs(result.events.reduce((a,e)=>a+e.staffed_workdays,0)-10/0.9)<1e-8)
 assert.match(result.rule,/HAI PHƯƠNG ÁN/)
 const monthEvents=result.monthly.filter(m=>m.tasks>0)
 assert.equal(monthEvents.reduce((a,m)=>a+m.daywork_cost,0),2900000)
})

test('unknown wage does not invent a cost and reserve does not inflate paid workdays',()=>{
 const r=simulate(payload,{from:'2026-01-01',months:18,flowerShares:[17,40,25,18],repeatRatoons:false})
 assert.ok(r.events.every(e=>e.daywork_cost===null))
 assert.ok(r.events.every(e=>e.staffed_workdays===e.required_workdays))
 assert.throws(()=>simulate(payload,{absenceReserve:1}),/vắng mặt/)
})
