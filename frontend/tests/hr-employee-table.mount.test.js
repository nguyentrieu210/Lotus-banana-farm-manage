import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,window} from './support/mount.mjs'

const HrApp=await load('HrApp.vue')
const people=[
 {name:'EMP-A',employee_name:'An',department:'Ban vườn',designation:'Worker',lotus_farm:'F1',lotus_worker_category:'Seasonal',lotus_payment_basis:'Daywork',status:'Active',lotus_onboarding_state:'Pending'},
 {name:'EMP-B',employee_name:'Bình',department:'Văn phòng',designation:'Accountant',lotus_farm:'F2',lotus_worker_category:'Permanent',lotus_payment_basis:'Monthly',status:'Inactive',lotus_onboarding_state:'Ready'},
]
let manager=true,calls=[]
globalThis.fetch=async(url,options={})=>{
 const target=new URL(url,'http://localhost'),method=target.pathname.split('.').at(-1)
 const args=options.body?JSON.parse(options.body):Object.fromEntries(target.searchParams)
 calls.push({method,args})
 const data=method==='bootstrap'?{companies:[{name:'Lotus'}],today:'2026-10-22',is_hr_manager:manager}:
  method==='catalogue'?{farms:[{name:'F1',farm_name:'Vườn 1'},{name:'F2',farm_name:'Vườn 2'}],departments:[],designations:[],teams:[],grades:[],employment_types:[],genders:[],openings:[],designation_groups:{},worker_categories:[],payment_bases:[]}:
  method==='overview'?{employees:people,candidates:[]}:
  method==='employee_detail'?{...people.find(p=>p.name===args.employee),modified:'version-1',onboarding_gaps:[]}:
  method==='save_employee'?{name:'EMP-NEW',onboarding_state:'Pending'}:null
 assert.ok(data,method)
 return {ok:true,json:async()=>({message:data})}
}
const records=root=>root.querySelector('.lotus-mobile-records')

test('HR employee list uses shared column filters and opens the selected employee through the real grid',async()=>{
 manager=true;calls=[]
 const view=mount(HrApp)
 try{
  await tick();await tick()
  assert.ok(view.root.querySelector('.workspace-employee-list .lotus-data-table'))
  assert.equal(view.root.querySelector('.workspace-employee-list table'),null)
  const grid=view.root.querySelector('.lotus-ag-grid').__vueParentComponent.proxy
  const department=grid.$props.columnDefs.find(c=>c.field==='department')
  department.headerComponentParams.apply(['Ban vườn']);await tick()
  assert.match(records(view.root).textContent,/An/)
  assert.doesNotMatch(records(view.root).textContent,/Bình/)
  assert.match(records(view.root).textContent,/Vườn 1.*Thời vụ.*Công nhật.*Chờ tiếp nhận/)
  view.root.querySelector('.lotus-ag-grid').__vueParentComponent.proxy.$emit('row-clicked',{data:people[0]});await tick();await tick()
  assert.deepEqual(calls.filter(c=>c.method==='employee_detail').map(c=>c.args.employee),['EMP-A'])
  assert.ok(document.querySelector('dialog[open]'))
 }finally{view.unmount()}
})

test('new desktop employee form accepts the full birth date and sends the exact ISO date to ERPNext',async()=>{
 manager=true;calls=[]
 const view=mount(HrApp)
 try{
  await tick();await tick()
  const add=[...view.root.querySelectorAll('button')].find(b=>b.textContent.includes('Thêm nhân viên'))
  assert.ok(add);add.click();await tick()
  const dialog=document.querySelector('dialog[open]'),input=dialog.querySelector('input[aria-label="Ngày sinh"]')
  assert.ok(input);assert.equal(input.required,true)
  input.value='15/06/1990';input.dispatchEvent(new window.Event('input',{bubbles:true}));await tick()
  assert.equal(input.checkValidity(),true)
  // Exercise the real save handler against a mocked ERP API; no production employee is created.
  dialog.querySelector('form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await tick();await tick()
  const saved=calls.find(c=>c.method==='save_employee')
  assert.equal(saved.args.values.date_of_birth,'1990-06-15')
  assert.equal(saved.args.values.date_of_joining,'2026-10-22')
 }finally{view.unmount()}
})

test('shared HR onboarding list keeps pending employees and read-only staff cannot open an editor',async()=>{
 manager=false;calls=[]
 const view=mount(HrApp,{hrView:'onboarding'})
 try{
  await tick();await tick()
  assert.match(records(view.root).textContent,/An/)
  assert.doesNotMatch(records(view.root).textContent,/Bình/)
  assert.equal(view.root.querySelector('.lotus-mobile-record').tagName,'ARTICLE')
  const grid=view.root.querySelector('.lotus-ag-grid').__vueParentComponent.proxy
  grid.$emit('row-clicked',{data:people[0]});await tick()
  assert.equal(calls.some(c=>c.method==='employee_detail'),false)
  assert.equal(document.querySelector('dialog[open]'),null)
 }finally{view.unmount()}
})