import test from 'node:test'
import assert from 'node:assert/strict'
import {load,createApp,h,tick,document,window} from './support/mount.mjs'
import {createRouter,createMemoryHistory} from 'vue-router'

globalThis.history??=window.history
const calls=[]
const M='lotus_farm.block_forecast.'
const board={
 farms:[{name:'LOTUS-222',farm_name:'Vườn 222'}],farm:'LOTUS-222',
 zone_list:['A','B','C'],blocks:[{name:'A1',block_code:'A1',farm_zone:'A'}],
 source_count:1,can_create:0,
 params:{waves:[17,40,25,18],sucker_to_flower_months:6},
 months:[{month:'2027-07',bunches:120,packed_kg:2400}],
 rows:[{key:'A1-1',farm_block:'A1',zone:'A',crop_cycle:'C2',
   cohort:'Selection-2026',wave:1,qty_basis:'Selected Suckers',tree_qty:170,
   flower_window_start:'2027-05-01',inject_date:'2027-05-06',
   cut_bud_date:'2027-05-22',harvest_date:'2027-07-26',
   bunches_harvest:145,kg_pack:2900,source:'Plan Cohort đã duyệt'}],
 warnings:[],rule:'Chỉ dự phóng'
}
let replies={}
globalThis.fetch=async(url,opts={})=>{
 const u=new URL(url,'http://localhost'),method=u.pathname.replace('/api/method/','')
 calls.push({method,opts})
 if(!(method in replies))return {ok:false,status:404,json:async()=>({message:'Missing '+method})}
 return {ok:true,status:200,json:async()=>({message:replies[method]})}
}
const Component=await load('BlockForecastApp.vue')
async function open(){
 const router=createRouter({history:createMemoryHistory('/lotus'),
   routes:[{path:'/:p(.*)*',component:{render:()=>null}}]})
 await router.push('/forecast');await router.isReady()
 const el=document.createElement('div');document.body.appendChild(el)
 const app=createApp({render:()=>h(Component,{embedded:true})})
 app.use(router);app.mount(el)
 for(let i=0;i<5;i++)await tick()
 return {el,app,router,close(){app.unmount();el.remove()}}
}
test('forecast page uses block/cohort API and never opens a cut journal',async()=>{
 calls.length=0;replies={[M+'board']:board}
 const ui=await open()
 try{
  assert.ok(calls.some(c=>c.method===M+'board'))
  assert.match(ui.el.textContent,/Dự thu theo lô & vụ cây/)
  assert.match(ui.el.textContent,/01\/05\/2027/)
  assert.match(ui.el.textContent,/26\/07\/2027/)
  assert.doesNotMatch(ui.el.textContent,/Nhật ký chặt mẹ|Nhập nhật ký|NHẬT KÝ GỐC/)
 }finally{ui.close()}
})
test('care view uses block-only proposal without submitting any document',async()=>{
 calls.length=0
 replies={[M+'board']:board,[M+'preview_care_plan']:{
   rows:[],materials:[],warnings:[],total_count:0,ready_count:0}}
 const ui=await open()
 try{
  const tabs=[...ui.el.querySelectorAll('button')]
  const care=tabs.find(x=>x.textContent.includes('Lịch chăm sóc theo lô'))
  assert.ok(care);care.click();await tick()
  const preview=[...ui.el.querySelectorAll('button')].find(x=>x.textContent.includes('Xem lịch'))
  assert.ok(preview);preview.click()
  for(let i=0;i<5;i++)await tick()
  assert.ok(calls.some(c=>c.method===M+'preview_care_plan'))
  assert.ok(!calls.some(c=>c.method===M+'create_care_plan_draft'))
 }finally{ui.close()}
})
