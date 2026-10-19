import test from 'node:test'
import assert from 'node:assert/strict'
import {load,loadModule,mount,tick,h,ref,document,window} from './support/mount.mjs'

const Combobox=await load('components/ui/combobox/Combobox.vue')
const Toaster=await load('components/ui/toast/Toaster.vue')
const {toast}=await loadModule('use-toast.js')

const farms=[{value:'LOTUS-222',label:'Vườn Lô 222'},{value:'VIP-126',label:'Vườn VIP 126'},{value:'BD-01',label:'Bình Dương 01',group:'Bình Dương'}]
const options=()=>[...document.querySelectorAll('[role=option]')].map(o=>o.textContent.trim())

test('Combobox: opening shows every option, typing filters without accents, choosing emits the value',async()=>{
 const value=ref('VIP-126'),changes=[]
 const view=mount({setup:()=>()=>h(Combobox,{modelValue:value.value,options:farms,label:'Vườn',hideValues:true,'onUpdate:modelValue':v=>{value.value=v;changes.push(v)}})})
 await tick()
 const input=view.root.querySelector('input[role=combobox]')
 assert.equal(input.getAttribute('aria-label'),'Vườn')
 assert.equal(input.value,'Vườn VIP 126','shows the label of the stored code')
 view.root.querySelector('.lotus-combobox__trigger').click();await tick()
 assert.equal(options().length,3,'opening with a selected value still lists every option')
 input.value='binh duong';input.dispatchEvent(new window.Event('input',{bubbles:true}));await tick()
 assert.deepEqual(options(),['Bình Dương 01'])
 document.querySelector('[role=option]').dispatchEvent(new window.PointerEvent('pointerup',{bubbles:true}))
 document.querySelector('[role=option]').click();await tick()
 assert.equal(value.value,'BD-01');assert.deepEqual(changes,['BD-01'])
 view.unmount()
})

test('Toaster renders queued toasts with an action that runs once',async()=>{
 const view=mount(Toaster);await tick()
 let undone=0
 toast({title:'Đã xóa dòng 3',action:{label:'Hoàn tác',run:()=>undone++}});await tick()
 const item=document.querySelector('.lotus-toast')
 assert.ok(item,'toast is rendered');assert.match(item.textContent,/Đã xóa dòng 3/)
 ;[...item.querySelectorAll('button')].find(b=>b.textContent.includes('Hoàn tác')).click();await tick()
 assert.equal(undone,1);assert.equal(document.querySelectorAll('.lotus-toast').length,0,'action dismisses the toast')
 view.unmount()
})
