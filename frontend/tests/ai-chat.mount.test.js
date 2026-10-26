import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,window,document,h,ref} from './support/mount.mjs'

const Chat=await load('components/AiChatBubble.vue')
const response=answer=>({ok:true,json:async()=>({message:{answer,steps:[{tool:'query',doctype:'Bin'}]}})})
const inbox=()=>({ok:true,json:async()=>({message:{rooms:[],unread:0}})})
const click=(root,label)=>root.querySelector(`button[aria-label="${label}"]`).click()
async function open(view){click(view.root,'Hỏi Trợ lý Lotus AI');await tick()}
async function type(view,text){const input=view.root.querySelector('textarea');input.value=text;input.dispatchEvent(new window.Event('input',{bubbles:true}));await tick();return input}

test('chat opens, submits once while busy, escapes HTML, saves and resets history',async t=>{
 window.sessionStorage.clear()
 let resolve,calls=0,body
 const original=globalThis.fetch
 globalThis.fetch=async(_url,options)=>{if(_url.includes('lotus_farm.chat.'))return inbox();calls++;body=JSON.parse(options.body);return new Promise(r=>{resolve=r})}
 const view=mount(Chat,{user:'tester@example.com'});t.after(()=>{view.unmount();globalThis.fetch=original})
 assert.equal(view.root.querySelector('[role=dialog]'),null)
 await open(view)
 assert.equal(document.activeElement,view.root.querySelector('textarea'))
 assert.equal(view.root.querySelectorAll('.ai-chat__chip').length,4)
 view.root.querySelector('.ai-chat__chip').click();await tick()
 assert.equal(calls,1);assert.equal(body.messages.at(-1).role,'user')
 assert.ok(view.root.querySelector('.ai-chat__thinking'))
 assert.equal(view.root.querySelector('button[aria-label="Cuộc hỏi mới"]').disabled,true)
 view.root.querySelector('form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await tick()
 assert.equal(calls,1)
 resolve(response('**Kết quả**\n| chưa đủ bảng\n<img src=x onerror=alert(1)>'));await tick();await tick()
 assert.ok(view.root.querySelector('.ai-md strong'))
 assert.equal(view.root.querySelector('.ai-md img'),null)
 assert.match(view.root.querySelector('.ai-chat__source').textContent,/Bin/)
 assert.equal(JSON.parse(window.sessionStorage.getItem('lotus-ai-chat|tester@example.com')).length,2)
 click(view.root,'Cuộc hỏi mới');await tick()
 assert.equal(view.root.querySelectorAll('.ai-chat__msg').length,0)
 view.root.querySelector('textarea').dispatchEvent(new window.KeyboardEvent('keydown',{key:'Escape',bubbles:true}));await tick()
 assert.equal(view.root.querySelector('[role=dialog]'),null)
 assert.equal(document.activeElement,view.root.querySelector('.ai-chat__fab'))
})

test('IME Enter does not send; failed requests retain the question for retry',async t=>{
 window.sessionStorage.clear()
 const original=globalThis.fetch;let calls=0
 globalThis.fetch=async url=>{if(url.includes('lotus_farm.chat.'))return inbox();calls++;throw new Error('offline')}
 const view=mount(Chat,{user:'retry'});t.after(()=>{view.unmount();globalThis.fetch=original})
 await open(view);const input=await type(view,'Tồn kho hôm nay?')
 input.dispatchEvent(new window.KeyboardEvent('keydown',{key:'Enter',isComposing:true,bubbles:true,cancelable:true}));await tick()
 assert.equal(calls,0)
 input.dispatchEvent(new window.KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true}));await tick();await tick()
 assert.equal(calls,1);assert.equal(input.value,'Tồn kho hôm nay?')
 assert.ok(view.root.querySelector('[role=alert]'))
 assert.equal(view.root.querySelector('button[type=submit]').disabled,false)
})

test('switching accounts isolates histories and ignores a previous account response',async t=>{
 window.sessionStorage.clear();window.sessionStorage.setItem('lotus-ai-chat|second','{}')
 const user=ref('first'),original=globalThis.fetch;let resolve
 globalThis.fetch=async url=>url.includes('lotus_farm.chat.')?inbox():new Promise(r=>{resolve=r})
 const view=mount({setup:()=>()=>h(Chat,{user:user.value})});t.after(()=>{view.unmount();globalThis.fetch=original})
 await open(view);view.root.querySelector('.ai-chat__chip').click();await tick()
 user.value='second';await tick()
 resolve(response('Thông tin tài khoản cũ'));await tick();await open(view)
 assert.equal(view.root.querySelectorAll('.ai-chat__msg').length,0)
 assert.doesNotMatch(view.root.textContent,/Thông tin tài khoản cũ/)
 assert.equal(window.sessionStorage.getItem('lotus-ai-chat|second'),'[]')
 assert.equal(JSON.parse(window.sessionStorage.getItem('lotus-ai-chat|first')).length,1)
})
