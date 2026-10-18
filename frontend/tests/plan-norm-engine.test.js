import test from 'node:test'
import assert from 'node:assert/strict'
import {allocate,stages,day,simulate,pickProfile} from '../src/plan-norm-engine.js'
const profile={name:'HP1',approval_state:'Approved',active:1,farm:'F',valid_from:'2025-01-01',version:1,
  planting_to_harvest_days:270,sucker_to_harvest_days:180,shooting_to_harvest_days:82,cut_bud_to_harvest_days:65,
  ratoon_interval_days:270,avg_bunch_weight_kg:20,bunch_survival_rate_percent:90,quality_pass_rate_percent:80,packout_rate_percent:75}
const wave={name:'A1-1',farm:'F',farm_block:'A1',cohort_code:'A1-1',cohort_name:'A1 đợt 1',
  anchor:'Planting',anchor_date:'2026-01-01',quantity_basis:'Bunches',planned_qty:1000,approval_state:'Approved',version:1}
const board={blocks:[{name:'A1',farm:'F',area_ha:1}],cohorts:[wave],profiles:[profile],
  rules:[{name:'cut',farm:'F',rule_name:'Cắt bắp',work_type:'CUT',anchor:'Cut Bud',offset_days:0,repeat_days:0,quantity_basis:'Bunches',approval_state:'Approved'}],
  works:[{name:'CUT',work_name:'Cắt bắp',uom:'Buồng',productivity_per_workday:100,allow_piecework:1,piecework_rate:2000}],
  norms:[{name:'N1',farm:'F',work_type:'CUT',version:1,approval_state:'Approved',valid_from:'2025-01-01',valid_to:'2029-12-31'}],
  norm_lines:{N1:[{item:'BAG',uom:'Cái',norm_qty:1,basis_qty:1,frequency:1,conversion_factor:1}]}};
test('rounding 20-60-20 preserves whole bunches',()=>{
 assert.deepEqual(allocate(1001,[20,60,20]),[200,600,201]);
 assert.throws(()=>allocate(1000,[20,60,30]));
});
test('phase order and calendar use real date offsets',()=>{
 const s=stages(wave,profile);
 assert.equal(s.harvest,day('2026-01-01',270));assert.ok(s.dates.Shooting<s.dates['Cut Bud']);
});
test('three waves are once each and no duplicate after version update',()=>{
 const x=simulate(board,{from:'2026-01-01',months:36,repeatRatoons:false});
 assert.equal(x.harvests.length,3);assert.equal(x.events.length,3);
 assert.equal(x.harvests.reduce((a,b)=>a+b.bunches,0),1000);
 assert.equal(x.materials.reduce((a,b)=>a+b.quantity,0),1000);
 assert.ok(x.events.every(e=>e.projected));
 const older={...wave,name:'old',version:0};
 const v=simulate({...board,cohorts:[wave,older]},{from:'2026-01-01',repeatRatoons:false});
 assert.equal(v.harvests.length,3);
});
test('draft ignored by default and preview permitted when explicitly enabled',()=>{
 const draft={...wave,name:'draft',approval_state:'Draft'};
 assert.equal(simulate({...board,cohorts:[draft]},{from:'2026-01-01'}).harvests.length,0);
 assert.equal(simulate({...board,cohorts:[draft]},{from:'2026-01-01',includeDraft:true,repeatRatoons:false}).harvests.length,3);
});
test('unknown conversion is warned and never assumes one tree equals a bunch',()=>{
 const tree={...wave,quantity_basis:'Trees'};
 const x=simulate({...board,cohorts:[tree]},{from:'2026-01-01',repeatRatoons:false});
 assert.equal(x.events.length,0);assert.equal(x.harvests.length,0);
 assert.ok(x.warnings.some(w=>w.includes('không coi cây = buồng')));
});
test('no profile approval means no estimate',()=>{
 const q=simulate({...board,profiles:[{...profile,approval_state:'Draft'}]},{from:'2026-01-01'});
 assert.equal(q.harvests.length,0);assert.ok(q.warnings.length);
});
test('most specific approved profile wins',()=>{
 const scoped={...profile,name:'specific',farm_block:'A1',version:1};
 assert.equal(pickProfile([profile,scoped],wave,{variety:''},'2026-01-01').name,'specific');
});
