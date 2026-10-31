import test from 'node:test'
import assert from 'node:assert/strict'
import {groupSchema,previewAmount,splitBySessions,peopleRows,sessionCount,entryPayload,ribbonLeft,boardRows,wholeLot} from '../src/field-work-model.js'

test('each work group shows its own fields',()=>{
 assert.deepEqual([groupSchema({work_group:'Bunch',work_stage:'Bag'}).ribbonChoice,groupSchema({work_group:'Bunch',work_stage:'Bag'}).materials],[true,false])
 const cut=groupSchema({work_group:'Bunch',work_stage:'Cut Bud'})
 assert.equal(cut.ribbon,true);assert.equal(cut.ribbonChoice,false,'cắt bắp takes the week colour')
 const spray=groupSchema({work_group:'Protection',requires_material:1})
 assert.equal(spray.materials,true);assert.equal(spray.materialsRequired,true)
 assert.equal(groupSchema({work_group:'Field'}).materials,false)
})

test('money follows the pay mode of the phiếu',()=>{
 assert.equal(previewAmount({pay_mode:'Count',rate:4000},120),480000)
 assert.equal(previewAmount({pay_mode:'Lot',rate:300000,basis:'Area',lot_area_ha:4.48},1.2),1344000,'khoán lô: the whole lô')
 assert.equal(previewAmount({pay_mode:'Daywork',rate:0},10),0)
 assert.equal(wholeLot({basis:'Trees',lot_trees:10668}),10668)
})

test('khoán money is split by buổi and adds up',()=>{
 assert.deepEqual(splitBySessions(1000000,{A:2,B:2,C:1}),{A:400000,B:400000,C:200000})
 const odd=splitBySessions(100000,{A:1,B:1,C:1})
 assert.equal(Object.values(odd).reduce((s,v)=>s+v,0),100000)
 assert.deepEqual(splitBySessions(0,{A:1}),{A:0})
})

test('people: only the clock\'s present, members picked by default, buổi on another phiếu locked',()=>{
 const present=[
  {employee:'E1',employee_name:'An',team:'T01',morning:true,afternoon:true,taken:{}},
  {employee:'E2',employee_name:'Bình',team:'T01',morning:true,afternoon:false,taken:{Morning:{assignment:'OTHER'}}},
  {employee:'E3',employee_name:'Cúc',team:'T02',morning:true,afternoon:true,taken:{}},
 ]
 const rows=peopleRows(present,{name:'PG1',work_team:'T01'},null)
 const by=Object.fromEntries(rows.map(r=>[r.employee,r]))
 assert.deepEqual([by.E1.morning,by.E1.afternoon],[1,1])
 assert.equal(by.E2.morning,0,'already on another phiếu');assert.equal(by.E2.can_morning,false);assert.equal(by.E2.can_afternoon,false,'not present in the afternoon')
 assert.equal(by.E3.morning,0,'outside the tổ is not picked by default')
 assert.equal(sessionCount(rows),2)
 const saved=peopleRows(present,{name:'PG1',work_team:'T01'},{people:[{employee:'E3',morning:1,afternoon:0}]})
 assert.equal(Object.fromEntries(saved.map(r=>[r.employee,r])).E1.morning,0,'a saved report keeps its own choice')
})

test('payload sends people with a buổi and materials with an item',()=>{
 const ticket={name:'PG1',entry:{modified:'m1'}}
 const sent=entryPayload(ticket,'2026-11-02',{qty:'12',bunch_tag:'W45',done:true,notes:'',materials:[{item_code:'NPK',qty:'5',dose:'150 g/gốc'},{item_code:''}]},
  [{employee:'E1',morning:1,afternoon:0},{employee:'E2',morning:0,afternoon:0}])
 assert.equal(sent.assignment,'PG1');assert.equal(sent.qty,12);assert.equal(sent.done,1);assert.equal(sent.expected_modified,'m1')
 assert.deepEqual(JSON.parse(sent.people),[{employee:'E1',morning:1,afternoon:0}])
 assert.deepEqual(JSON.parse(sent.materials),[{item_code:'NPK',qty:5,dose:'150 g/gốc',stock_entry:null}])
})

test('bunches left to report are cut minus already done of that colour',()=>{
 const t={farm_block:'A1',work_stage:'Bag',entry:{bunch_tag:'W44',qty:10}}
 assert.equal(ribbonLeft(t,'W44',{cut:{'A1|W44':40},done:{'A1|W44|Bag':30}}),20,'today\'s own report is not counted twice')
 assert.equal(ribbonLeft(t,'W45',{cut:{},done:{}}),0)
 assert.equal(ribbonLeft(t,null,{}),null)
})

test('board rows put each phiếu under its lô and việc, latest first',()=>{
 const rows=boardRows({blocks:[{name:'A8',block_code:'A8'}],cells:[{farm_block:'A8',work_type:'CL',assigned_on:'2026-10-01',display:'Locked'},{farm_block:'A8',work_type:'CL',assigned_on:'2026-10-20',display:'Working'}]})
 assert.deepEqual(rows[0].cells.CL.map(c=>c.display),['Working','Locked'])
})
