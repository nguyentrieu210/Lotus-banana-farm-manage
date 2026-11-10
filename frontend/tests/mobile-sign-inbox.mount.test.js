import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick} from './support/mount.mjs'

const Inbox=await load('components/LotusMobileSignInbox.vue')
const settle=async(n=5)=>{for(let i=0;i<n;i++)await tick()}
const row={doctype:'Material Request',name:'MAT-MR-1',chain:'purchase_proposal',chain_label:'Phiếu đề xuất mua vật tư',step_title:'Giám đốc phê duyệt',
 creator_name:'An',amount:2500000,modified:'m',print_url:'/lotus/in-de-xuat?name=MAT-MR-1'}

test('phone header shows Chờ tôi ký with its count, lists waiting documents and shares the count with home cards',async()=>{
 const calls=[],counts=[]
 const callFn=async(method)=>{calls.push(method);if(method.endsWith('inbox_count'))return {count:3};if(method.endsWith('inbox'))return {rows:[row],total:1}}
 window.addEventListener('lotus-sign-count',e=>counts.push(e.detail))
 const view=mount(Inbox,{callFn})
 await settle()
 const trigger=document.querySelector('button[aria-label^="Chờ tôi ký"]')
 assert.ok(trigger,'one button in the shared header')
 assert.equal(trigger.getAttribute('aria-label'),'Chờ tôi ký: 3 chứng từ')
 assert.ok(counts.includes(3),'home cards hear the same number')
 window.dispatchEvent(new CustomEvent('lotus-open-sign-inbox'));await settle()
 assert.ok(calls.some(m=>m.endsWith('.inbox')),'opening the list reads the inbox')
 assert.match(document.body.textContent,/Phiếu đề xuất mua vật tư · MAT-MR-1/)
 assert.match(document.body.textContent,/Giám đốc phê duyệt · An · 2\.500\.000 đ/)
 view.unmount()
})

test('a signing link opens the document sheet and is removed from the address bar',async()=>{
 window.history.replaceState({},'', '/buying?sign_dt=Material+Request&sign_dn=MAT-MR-1')
 const calls=[]
 const callFn=async(method,args)=>{calls.push([method,args]);if(method.endsWith('inbox_count'))return {count:1}
  if(method.endsWith('open_targets'))return {desktop_url:'/lotus/mua-hang',print_url:'/lotus/in-de-xuat?name=MAT-MR-1',mobile_url:'/buying?sign_dt=x'}
  if(method.endsWith('chain_status'))return {round:1,current:3,returned:false,can_sign:true,steps:[]}}
 const view=mount(Inbox,{callFn})
 await settle(8)
 assert.ok(calls.some(([m,a])=>m.endsWith('open_targets')&&a.name==='MAT-MR-1'))
 assert.equal(window.location.search,'','the link is consumed')
 view.unmount()
})
