import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,ref,h,createApp} from './support/mount.mjs'
const Process=await load('components/OneDriveProcessWorkspace.vue')
const button=(root,text)=>[...root.querySelectorAll('button')].find(b=>b.textContent.trim()===text)
const payload={can_configure:true,can_import:true,workflow:[{title:'Bàn giao theo khu',route:'process',doctype:'Lotus Handover Cohort',can_read:true,count:301}],handovers:[{farm:'F',farm_zone:'A',source_event_date:'2026-03-31',equivalent_selection_date:'2026-03-31',source_cut_qty:100}],adoptions:[],library:{defaults:[],sources:[]},selection_months:[{farm:'F',farm_zone:'A',month:'2026-09',cohort_count:1,source_cut_qty:100}]}
test('workspace distinguishes historical cut stems, planned dates and actual selections',async()=>{
 const edits=[];const view=mount(Process,{payload,farm:'F',fromDate:'2026-10-20',onEdit:(...args)=>edits.push(args)})
 try{
  button(view.root,'Bàn giao').click();await tick();assert.match(view.root.textContent,/Cây cũ đã chặt/)
  button(view.root,'Chọn chồi').click();await tick();assert.match(view.root.textContent,/6 × n tháng/)
  button(view.root,'Ghi chọn chồi thực tế').click();await tick()
  assert.equal(edits[0][0],'Sucker Selection Batch');assert.equal(edits[0][2].farm_block,'')
  assert.equal(edits[0][2].selected_sucker_qty,undefined,'old stem count is never copied as actual suckers')
  button(view.root,'Thông số').click();await tick();button(view.root,'Thêm phiên bản áp dụng').click();await tick()
  assert.ok(button(document.body,'Áp dụng bản mới').disabled,'a source preset must be selected explicitly')
 }finally{view.unmount()}
})
test('a response from the preceding farm cannot reappear after scope changes',async()=>{
 let resolveOld
 globalThis.fetch=async()=>new Promise(resolve=>{resolveOld=()=>resolve({ok:true,json:async()=>({message:{rows:[{farm:'OLD',month:'2026-10',gross_kg:999}]}})})})
 const farm=ref('OLD');const root=document.createElement('div');document.body.append(root)
 const app=createApp({render:()=>h(Process,{payload,farm:farm.value,fromDate:'2026-10-20',forecastOnly:true})});app.mount(root);await tick()
 farm.value='NEW';await tick();resolveOld();await tick();await tick()
 try{assert.doesNotMatch(root.textContent,/999/)}finally{app.unmount();root.remove()}
})
