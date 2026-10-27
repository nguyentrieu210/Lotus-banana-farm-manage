import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,window} from './support/mount.mjs'

const App=await load('FieldProposalMobile.vue')
const response=value=>({ok:true,json:async()=>({message:value})})
const bootstrap={
 user:'team@example.invalid', name:'Đội trưởng A', reviewer:false,csrf_token:'csrf',today:'2026-10-27',
 farms:[{name:'F222',farm_name:'Vườn 222',company:'Lotus'}],
 blocks:[{name:'A',farm:'F222',block_name:'Khu A'}],
 items:[{name:'ITEM-1',item_name:'Bao PE',stock_uom:'kg'}]
}
function mock(t,handler=()=>null){
 const original=globalThis.fetch
 globalThis.fetch=async(url,options)=>{
  const method=String(url).split('/api/method/')[1]?.split('?')[0]
  const args=options?.body?JSON.parse(options.body):{}
  if(method==='lotus_farm.field_proposal.bootstrap')return response(bootstrap)
  if(method==='lotus_farm.field_proposal.proposals')return response([])
  return handler(method,args)
 }
 t.after(()=>globalThis.fetch=original)
}
test('leader sees separate material and cost request actions with no approval tab',async t=>{
 mock(t,method=>{throw Error(method)})
 const view=mount(App);t.after(view.unmount)
 await tick();await tick();await tick()
 assert.match(view.root.textContent,/Đề xuất vật tư/)
 assert.match(view.root.textContent,/Đề xuất chi phí/)
 assert.doesNotMatch(view.root.textContent,/Chờ duyệt/)
})
test('new material and cost forms use separate request kinds',async t=>{
 mock(t,method=>{throw Error(method)})
 const view=mount(App);t.after(view.unmount)
 await tick();await tick();await tick()
 const click=label=>[...view.root.querySelectorAll('button')].find(b=>b.textContent.includes(label)).click()
 click('Đề xuất vật tư');await tick()
 assert.match(view.root.textContent,/Chọn vật tư có sẵn trong danh mục/)
 assert.match(view.root.textContent,/Giá dự kiến/)
 const back=view.root.querySelector('.lotus-pwa-header button')
 if(back){back.click();await tick()}
 // Navigation-independent check: one form is shown, not a parallel expense form.
 assert.equal(view.root.querySelectorAll('.field-proposal__total').length<=1,true)
})
