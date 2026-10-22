import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,h,ref,window} from './support/mount.mjs'

const DatePicker=await load('components/ui/date-picker/DatePicker.vue')
const WorkspaceModal=await load('components/WorkspaceModal.vue')
async function enter(input,text){input.value=text;input.dispatchEvent(new window.Event('input',{bubbles:true}));await tick()}
function fixture(initial='',props={}){
 const value=ref(initial)
 const view=mount({setup:()=>()=>h(DatePicker,{...props,modelValue:value.value,'onUpdate:modelValue':v=>value.value=v})})
 return {...view,value,input:()=>view.root.querySelector('input')}
}

test('date field accepts full typed/pasted Vietnamese dates and emits ISO without timezone conversion',async()=>{
 const view=fixture('',{required:true,label:'Ngày sinh',max:'2026-10-22',id:'dob'})
 try{
  await tick();const input=view.input()
  assert.equal(input.placeholder,'dd/mm/yyyy');assert.equal(input.id,'dob')
  assert.equal(input.required,true);assert.equal(input.checkValidity(),false)
  for(const [text,iso] of [['15/06/1990','1990-06-15'],['29/02/2000','2000-02-29'],['1/2/1985','1985-02-01']]){
   await enter(input,text);assert.equal(view.value.value,iso);assert.equal(input.checkValidity(),true)
  }
  input.dispatchEvent(new window.FocusEvent('blur'));await tick();assert.equal(input.value,'01/02/1985')
  view.value.value='1978-12-31';await tick();assert.equal(input.value,'31/12/1978')
  view.value.value='';await tick();assert.equal(input.value,'')
 }finally{view.unmount()}
})

test('invalid, incomplete and out-of-range edits block submission and never retain an old date',async()=>{
 const view=fixture('1990-06-15',{required:true,min:'1900-01-01',max:'2026-10-22'})
 try{
  await tick();const input=view.input()
  await enter(input,'1');assert.equal(view.value.value,'');assert.equal(input.value,'1')
  for(const text of ['31/02/2000','29/02/1999','32/01/2000','01/13/2000','01/01/0000','1990-06-15','01/01/1899','23/10/2026']){
   await enter(input,text);assert.equal(view.value.value,'',text);assert.equal(input.checkValidity(),false,text)
   assert.ok(input.validationMessage,text)
  }
  await enter(input,'15/06/1990');assert.equal(view.value.value,'1990-06-15');assert.equal(input.checkValidity(),true)
  await enter(input,'');assert.equal(view.value.value,'');assert.equal(input.checkValidity(),false)
 }finally{view.unmount()}
 const optional=fixture()
 try{await tick();assert.equal(optional.input().checkValidity(),true)}finally{optional.unmount()}
})

test('calendar stays inside the employee modal, selects a date and updates the same text field',async()=>{
 const value=ref('1990-06-15')
 const view=mount({setup:()=>()=>h(WorkspaceModal,{modelValue:true,title:'Nhân viên'},()=>h(DatePicker,{modelValue:value.value,'onUpdate:modelValue':v=>value.value=v,label:'Ngày sinh'}))})
 try{
  await tick();const dialog=document.querySelector('dialog[open]')
  dialog.querySelector('.lotus-date__trigger').click();await tick()
  assert.ok(dialog.querySelector('.lotus-date__content'))
  const day=[...dialog.querySelectorAll('.lotus-calendar__day')].find(e=>e.textContent.trim()==='16'&&!e.hasAttribute('data-outside-view'))
  assert.ok(day);day.click();await tick()
  assert.equal(value.value,'1990-06-16');assert.equal(dialog.querySelector('input').value,'16/06/1990')
  assert.equal(dialog.querySelector('.lotus-date__content'),null)
 }finally{view.unmount()}
})

test('readonly and disabled date fields prevent keyboard changes and calendar opening',async()=>{
 for(const props of [{readonly:true},{disabled:true}]){
  const view=fixture('1990-06-15',props)
  try{await tick();assert.equal(view.input()[props.readonly?'readOnly':'disabled'],true);assert.equal(view.root.querySelector('.lotus-date__trigger').disabled,true)}finally{view.unmount()}
 }
})
