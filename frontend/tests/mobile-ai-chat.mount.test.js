import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import {load,mount,tick,window,document,ref,h} from './support/mount.mjs'

const Chat=await load('components/LotusMobileAiChat.vue')
const popup=()=>document.querySelector('.lotus-mobile-ai__popup')
const response=answer=>({ok:true,json:async()=>({message:{answer,steps:[{tool:'query',doctype:'Bin'}]}})})
async function open(view){view.root.querySelector('button[aria-label="Hỏi trợ lý Lotus AI"]').click();await tick();assert.ok(popup())}

test('four phone apps use one shared chat in LotusMobileShell',()=>{
 const dir=new URL('../src/',import.meta.url)
 const shell=fs.readFileSync(new URL('components/LotusMobileShell.vue',dir),'utf8')
 assert.match(shell,/<LotusMobileAiChat :user="user"/)
 for(const [file,app] of [['WarehouseMobile.vue','warehouse'],['BuyingMobile.vue','buying'],['WorkMobile.vue','work'],['HrMobile.vue','hr']]){
  const src=fs.readFileSync(new URL(file,dir),'utf8')
  assert.ok(src.includes('<LotusMobileShell app="'+app+'" :user="session?.user'),file)
 }
})
test('logged-in user can query, and answer appears in the panel',async t=>{
 window.sessionStorage.clear()
 const original=globalThis.fetch
 let resolve,count=0
 globalThis.fetch=async(url,options)=>{count++;assert.equal(url,'/api/method/lotus_farm.ai_chat.ask');assert.equal(options.method,'POST');return new Promise(r=>resolve=r)}
 const user=ref('')
 const view=mount({setup:()=>()=>h(Chat,{user:user.value})})
 t.after(()=>{view.unmount();globalThis.fetch=original})
 assert.equal(view.root.querySelector('.lotus-mobile-ai__fab'),null)
 user.value='employee';await tick()
 await open(view)
 popup().querySelector('.lotus-mobile-ai__suggestion').click();await tick()
 assert.equal(count,1)
 resolve(response('**Đã tra cứu**'));await tick();await tick()
 assert.match(popup().textContent,/Đã tra cứu/)
 assert.equal(JSON.parse(window.sessionStorage.getItem('lotus-ai-chat|employee')).length,2)
 popup().querySelector('button[aria-label="Cuộc hỏi mới"]').click();await tick()
 assert.equal(popup().querySelectorAll('.lotus-mobile-ai__message').length,0)
})
test('account change drops previous responses',async t=>{
 window.sessionStorage.clear()
 const original=globalThis.fetch
 let finish
 globalThis.fetch=()=>new Promise(resolve=>finish=resolve)
 const user=ref('first')
 const view=mount({setup:()=>()=>h(Chat,{user:user.value})})
 t.after(()=>{view.unmount();globalThis.fetch=original})
 await open(view)
 popup().querySelector('.lotus-mobile-ai__suggestion').click();await tick()
 user.value='second';await tick()
 finish(response('Old answer'));await tick()
 await open(view)
 assert.doesNotMatch(popup().textContent,/Old answer/)
})
