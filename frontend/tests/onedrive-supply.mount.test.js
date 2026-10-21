import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,ref,h,createApp} from './support/mount.mjs'

const Supply=await load('components/OneDriveSupplyDialog.vue')
const Process=await load('components/OneDriveProcessWorkspace.vue')
const button=(root,text)=>[...root.querySelectorAll('button')].find(el=>el.textContent.trim()===text)
const modal=()=>document.querySelector('dialog[aria-label="Dự thu từ buồng đã cắt bắp"]')
const source={farm:'F',farm_zone:'A',farm_block:'B',farm_plot:'P',crop_cycle:'C',sucker_selection_batch:'',source:'CUT-1',source_kind:'Observed Cut',month:'2026-10',window_start:'2026-10-27',window_end:'2026-11-05',remaining_bunch_qty:10,process_adoption:'ADOPT-1',source_hash:'DETAIL-HASH'}
const preview={source_hash:'PREVIEW-HASH',drafts:[{source_cut_operation:'CUT-1',period_start_date:'2026-10-27',period_end_date:'2026-10-31',source_bunch_qty:5,gross_forecast_kg:100,packed_forecast_kg:82}],issues:[]}
async function choose(label,value){
 const field=[...modal().querySelectorAll('label')].find(el=>el.textContent.startsWith(label))
 const input=document.getElementById(field.htmlFor)
 assert.ok(input,`input for ${label}`);input.click();await tick();await tick()
 const option=[...modal().querySelectorAll('[role=option]')].find(el=>el.textContent.includes(value))
 assert.ok(option,`option ${value}`);option.click();await tick()
}
function mockServer(calls,handler){
 globalThis.fetch=async(url,options={})=>{
  const args=options.body?JSON.parse(options.body):Object.fromEntries(new URL(url,'http://localhost').searchParams)
  calls.push({url,options,args})
  const message=handler?await handler(url,args):url.includes('link_options')?[{value:args.doctype==='Item'?'ITEM-1':'PROFILE-1',label:args.doctype==='Item'?'ITEM-1':'PROFILE-1'}]:args.preview?preview:{documents:['HF-1']}
  return {ok:true,json:async()=>({message})}
 }
}

test('cut supply requires explicit outputs and confirms the exact preview before creating a draft',async()=>{
 const calls=[],created=[];mockServer(calls)
 const view=mount(Supply,{source,month:'2026-10',company:'Lotus',canPrepare:true,onCreated:r=>created.push(r)})
 try{
  await tick();assert.ok(button(modal(),'Xem trước dự thu').disabled)
  assert.match(modal().textContent,/Chưa có hồ sơ chồi/)
  await choose('Sản phẩm','ITEM-1');await choose('Hệ số đóng gói','PROFILE-1')
  assert.equal(button(modal(),'Xem trước dự thu').disabled,false)
  button(modal(),'Xem trước dự thu').click();await tick();await tick()
  const first=calls.find(r=>r.url.includes('prepare_cut_forecasts'))
  assert.equal(first.options.method,'POST');assert.equal(first.args.preview,1)
  assert.deepEqual(first.args.source_cuts,['CUT-1']);assert.equal(first.args.period_start,'2026-10-27');assert.equal(first.args.period_end,'2026-10-31')
  assert.deepEqual(first.args.output_mapping,[{item:'ITEM-1',packout_profile:'PROFILE-1',share_percent:100}])
  button(modal(),'Tạo dự thu nháp').click();await tick();await tick()
  const writes=calls.filter(r=>r.url.includes('prepare_cut_forecasts'))
  assert.equal(writes[1].args.preview,0);assert.equal(writes[1].args.expected_source_hash,'PREVIEW-HASH')
  assert.equal(writes[1].args.client_event_id,first.args.client_event_id)
  assert.deepEqual(created,[{documents:['HF-1']}])
 }finally{view.unmount()}
})

test('changing an output invalidates a preview and cannot create an unseen forecast',async()=>{
 const calls=[];mockServer(calls)
 const view=mount(Supply,{source,month:'2026-10',canPrepare:true})
 try{
  await tick();await choose('Sản phẩm','ITEM-1');await choose('Hệ số đóng gói','PROFILE-1')
  button(modal(),'Xem trước dự thu').click();await tick();await tick();assert.ok(button(modal(),'Tạo dự thu nháp'))
  const share=modal().querySelector('input[type=number]');share.value='80';share.dispatchEvent(new Event('input',{bubbles:true}));await tick()
  assert.equal(button(modal(),'Tạo dự thu nháp'),undefined)
  button(modal(),'Xem trước dự thu').click();await tick();await tick()
  const previews=calls.filter(r=>r.url.includes('prepare_cut_forecasts'))
  assert.equal(previews[1].args.output_mapping[0].share_percent,80)
  assert.notEqual(previews[1].args.client_event_id,previews[0].args.client_event_id)
 }finally{view.unmount()}
})

test('read-only source evidence offers no native draft creation',async()=>{
 const view=mount(Supply,{source,month:'2026-10',canPrepare:false})
 try{await tick();assert.equal(button(modal(),'Xem trước dự thu'),undefined);assert.equal(modal().querySelector('[role=combobox]'),null);assert.ok(button(modal(),'Mở đợt cắt bắp gốc'))}finally{view.unmount()}
})

test('a pending preview from a previous cut cannot populate the new source form',async()=>{
 const calls=[];let finishPreview
 mockServer(calls,async(url,args)=>url.includes('link_options')?[{value:args.doctype==='Item'?'ITEM-1':'PROFILE-1',label:args.doctype==='Item'?'ITEM-1':'PROFILE-1'}]:new Promise(resolve=>{finishPreview=()=>resolve(preview)}))
 const selected=ref(source),root=document.createElement('div');document.body.append(root)
 const app=createApp({render:()=>h(Supply,{source:selected.value,month:'2026-10',canPrepare:true})});app.mount(root)
 try{
  await tick();await choose('Sản phẩm','ITEM-1');await choose('Hệ số đóng gói','PROFILE-1')
  button(modal(),'Xem trước dự thu').click();await tick();assert.ok(finishPreview)
  selected.value={...source,source:'CUT-2',source_hash:'NEW-SOURCE'};await tick();finishPreview();await tick();await tick()
  assert.match(modal().textContent,/CUT-2/);assert.equal(button(modal(),'Tạo dự thu nháp'),undefined)
  assert.ok(button(modal(),'Xem trước dự thu').disabled,'new source requires fresh output selection and review')
 }finally{app.unmount();root.remove()}
})

test('forecast source drilldown offers only observed cuts and clears when the farm changes',async()=>{
 const payload={can_configure:true,adoptions:[],library:{}}
 globalThis.fetch=async()=>({ok:true,json:async()=>({message:{rows:[{farm:'F',farm_zone:'A',month:'2026-10',source_kinds:['Observed Cut']}],source_rows:[source,{...source,source:'SSB-1',source_kind:'Observed Selection'}]}})})
 const farm=ref('F'),root=document.createElement('div');document.body.append(root)
 const app=createApp({render:()=>h(Process,{payload,farm:farm.value,forecastOnly:true})});app.mount(root)
 try{
  await tick();await tick();button(root,'Nguồn buồng cắt bắp').click();await tick()
  const detail=document.querySelector('dialog[aria-label="Nguồn buồng cắt bắp theo kỳ"]')
  assert.match(detail.textContent,/CUT-1/);assert.doesNotMatch(detail.textContent,/SSB-1/)
  const cut=[...detail.querySelectorAll('.lotus-mobile-record')].find(el=>el.textContent.includes('CUT-1'));assert.ok(cut);cut.click();await tick()
  assert.equal(modal().open,true)
  farm.value='NEW-F';await tick();assert.equal(modal().open,false)
 }finally{app.unmount();root.remove()}
})
