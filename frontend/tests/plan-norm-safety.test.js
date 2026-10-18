import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {simulate,stages} from '../src/plan-norm-engine.js'

const cohort={name:'C1',farm:'F',farm_block:'B',cohort_name:'B - đợt 1',
 cohort_code:'C1',anchor:'Shooting',anchor_date:'2026-04-01',quantity_basis:'Bunches',planned_qty:100,
 approval_state:'Approved',version:1}
const profile={name:'HP',farm:'F',approval_state:'Approved',active:1,valid_from:'2025-01-01',
 shooting_to_harvest_days:82,cut_bud_to_harvest_days:65,
 avg_bunch_weight_kg:20,bunch_survival_rate_percent:100,quality_pass_rate_percent:100,packout_rate_percent:100}
const work={name:'SPRAY',work_name:'Phun',uom:'Ha',productivity_per_workday:2,allow_piecework:0}
const norm={name:'N',work_type:'SPRAY',farm:'F',approval_state:'Approved',valid_from:'2025-01-01',valid_to:'2029-12-31',version:1}
const rule={name:'R',farm:'F',work_type:'SPRAY',anchor:'Shooting',offset_days:0,quantity_basis:'Area',approval_state:'Approved'}
const board={blocks:[{name:'B',farm:'F',area_ha:4}],profiles:[profile],works:[work],rules:[rule],norms:[norm],norm_lines:{N:[]},cohorts:[cohort]}
test('single wave area norm calculates block area and labor only once',()=>{
 const data=simulate(board,{from:'2026-01-01',repeatRatoons:false});
 assert.equal(data.events.length,1);assert.equal(data.events[0].qty,4);assert.equal(data.events[0].required_workdays,2);
});
test('multiple waves in one large lot do not each consume full lot area',()=>{
 const second={...cohort,name:'C2',cohort_code:'C2',cohort_name:'B - đợt 2',anchor_date:'2026-05-01'};
 const data=simulate({...board,cohorts:[cohort,second]},{from:'2026-01-01'});
 assert.equal(data.events.length,0);
 assert.ok(data.warnings.some(s=>s.includes('diện tích từng đợt')));
});
test('negative schedule offset means before anchor',()=>{
 const crop={...cohort,anchor:'Shooting'};
 const data=simulate({...board,cohorts:[crop],rules:[{...rule,quantity_basis:'Bunches',offset_days:-2}]},
 {from:'2026-01-01',repeatRatoons:false});
 assert.equal(data.events[0].date,'2026-03-30');
});
test('unapproved rule cannot create any projected work item',()=>{
 const x=simulate({...board,rules:[{...rule,approval_state:'Draft'}]},{from:'2026-01-01'});
 assert.equal(x.events.length,0);
});
test('invalid milestone order fails safely',()=>{
 const result=stages({...cohort,anchor:'Shooting'}, {...profile,planting_to_harvest_days:70,sucker_to_harvest_days:90});
 assert.equal(result.harvest,'');assert.ok(result.warning);
});
test('planning engine and read-only board do not create operational documents',()=>{
 const engine=readFileSync(new URL('../src/plan-norm-engine.js',import.meta.url),'utf-8');
 const api=readFileSync(new URL('../../lotus_farm/plan_norm.py',import.meta.url),'utf-8');
 assert.ok(!/frappe\.get_doc\(\s*[\{\[]\s*["']doctype["']/.test(api));
 for (const name of ['Daily Work Plan','Material Requirement','Purchase Order','Stock Entry'])
   assert.ok(!new RegExp('frappe\\.new_doc\\([\\\"\\\']'+name).test(api));
 assert.ok(engine.includes('Never posts operational documents')&&api.includes('NEVER observed'));
});
