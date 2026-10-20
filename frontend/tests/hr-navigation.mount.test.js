import test from 'node:test'
import assert from 'node:assert/strict'
import {load,loadModule,createApp,h,document,tick} from './support/mount.mjs'
import {createPinia,setActivePinia} from 'pinia'
import {createMemoryHistory} from 'vue-router'
const HrApp=await load('HrApp.vue')
const {createLotusRouter}=await loadModule('router.js')
const {useSession}=await loadModule('store.js')
const button=(root,label)=>[...root.querySelectorAll('button')].find(b=>b.textContent.trim()===label&&(!b.closest('dialog')||b.closest('dialog').open))
test('mounted HR keeps company and protects employee/candidate edits before changing URL',{timeout:10000},async()=>{
 const calls=[]
 globalThis.fetch=async(url,options={})=>{
  const target=new URL(url,'http://localhost'),method=target.pathname.split('/').at(-1),args=options.body?JSON.parse(options.body):Object.fromEntries(target.searchParams)
  calls.push({method,args})
  const data=method.endsWith('.bootstrap')?{today:'2026-10-20',is_hr_manager:true,companies:[{name:'A'},{name:'B'}]}:method.endsWith('.catalogue')?{farms:[],departments:[],designations:[],teams:[],grades:[],employment_types:[],genders:[],openings:[],designation_groups:{},worker_categories:[],payment_bases:[]}:method.endsWith('.overview')?{employees:[],candidates:[]}:null
  assert.notEqual(data,null,method)
  return {ok:true,json:async()=>({message:data})}
 }
 const pinia=createPinia();setActivePinia(pinia)
 Object.assign(useSession(),{ready:true,capabilities:{hr:true,hr_manage:true},modules:{},farms:[]})
 const router=createLotusRouter({history:createMemoryHistory('/lotus')})
 await router.push('/nhan-su')
 const root=document.createElement('div');document.body.append(root)
 const app=createApp({render:()=>h(HrApp,{embedded:true,hrView:router.currentRoute.value.query.hr_view||'employees'})})
 app.use(pinia);app.use(router);app.mount(root);await tick();await tick()
 try{
  assert.equal(root.querySelectorAll('[role=tab]').length,0)
  const company=root.querySelector('select');company.value='B';company.dispatchEvent(new Event('change',{bubbles:true}));await tick();await tick()
  for(const [view,label] of [['candidates','Thêm nhân viên'],['onboarding','Thêm ứng viên']]){
   button(root,label).click();await tick()
   const field=[...document.querySelectorAll('dialog[open] label')].find(l=>l.textContent.trim().startsWith('Họ tên'))
   const input=document.getElementById(field.htmlFor);input.value='Đang nhập';input.dispatchEvent(new Event('input',{bubbles:true}));await tick()
   const previous=router.currentRoute.value.fullPath
   let pending=router.push('/nhan-su?hr_view='+view);await tick()
   assert.ok(button(document.body,'Ở lại'));button(document.body,'Ở lại').click();await pending;await tick()
   assert.equal(router.currentRoute.value.fullPath,previous);assert.equal(input.value,'Đang nhập')
   pending=router.push('/nhan-su?hr_view='+view);await tick();button(document.body,'Rời đi').click();await pending;await tick()
   assert.equal(router.currentRoute.value.query.hr_view,view)
   assert.equal(root.querySelector('select').value,'B')
   assert.equal(input.closest('dialog')?.open||false,false)
  }
  assert.ok(calls.filter(c=>c.method.endsWith('.overview')).some(c=>c.args.company==='B'))
  assert.ok(calls.every(c=>!c.method.includes('save_')))
 }finally{app.unmount();root.remove()}
})
