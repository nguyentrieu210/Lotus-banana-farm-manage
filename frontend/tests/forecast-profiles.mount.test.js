import test from 'node:test'
import assert from 'node:assert/strict'
import {load,createApp,h,tick,document} from './support/mount.mjs'
const calls=[],M='lotus_farm.forecast_profiles.'
let state
globalThis.fetch=async(url,opts={})=>{
 const method=new URL(url,'http://localhost').pathname.replace('/api/method/','')
 calls.push({method,body:opts.body?JSON.parse(opts.body):null})
 return {ok:true,status:200,json:async()=>({message:method===M+'list_profiles'?state:{name:'P1'}})}
}
const Component=await load('components/ForecastProfiles.vue')
async function open(){
 calls.length=0;state={rows:[],defaults:{wave_1_share:.17,wave_2_share:.4,wave_3_share:.25,wave_4_share:.18},can_create:true,can_write:true,can_approve:true}
 const el=document.createElement('div');document.body.append(el)
 const app=createApp({render:()=>h(Component,{farm:'F1',blocks:[{name:'A1',block_code:'A1'}]})});app.mount(el)
 for(let i=0;i<6;i++)await tick()
 return {el,close(){app.unmount();el.remove()}}
}
test('profile editor saves percentages as fractions and never approves implicitly',async()=>{
 const ui=await open()
 try{
  [...ui.el.querySelectorAll('button')].find(b=>b.textContent==='Thêm bộ thông số').click()
  for(let i=0;i<3;i++)await tick()
  const dialog=document.querySelector('dialog[open]');assert.ok(dialog)
  assert.ok([...dialog.querySelectorAll('input')].some(e=>e.value==='17'))
  dialog.querySelector('form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))
  for(let i=0;i<8;i++)await tick()
  const saved=calls.find(c=>c.method===M+'save_draft');assert.ok(saved)
  assert.equal(saved.body.values.wave_1_share,.17)
  assert.equal(saved.body.values.apply_sucker_yield_to_counted_trees,0)
  assert.ok(!calls.some(c=>c.method===M+'approve'))
 }finally{ui.close()}
})
test('read-only users have no create, edit or approval actions',async()=>{
 const ui=await open()
 try{
  state={...state,can_create:false,can_write:false,can_approve:false,rows:[{name:'P1',profile_name:'Test',approval_state:'Draft'}]}
  ;[...ui.el.querySelectorAll('button')].find(b=>b.textContent==='Làm mới').click()
  for(let i=0;i<8;i++)await tick()
  assert.ok(![...ui.el.querySelectorAll('button')].some(b=>['Thêm bộ thông số','Sửa','Duyệt'].includes(b.textContent)))
 }finally{ui.close()}
})
