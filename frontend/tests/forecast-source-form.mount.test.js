import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,createApp,h,tick} from './support/mount.mjs'
import {reactive} from 'vue'
import {label} from '../src/labels.js'

const Form=await load('components/ForecastForm.vue'),Schema=await load('components/SchemaForm.vue')
const Workspace=await load('components/ForecastWorkspace.vue')
const fields=[
 {fieldname:'forecast_basis',fieldtype:'Select',options:'Manual\nCut Bud Operations'},
 {fieldname:'harvest_profile',fieldtype:'Link',options:'Harvest Profile'},
 ...['source_bunch_qty','avg_bunch_weight_kg','bunch_survival_rate_percent','quality_pass_rate_percent','packout_rate_percent','safety_buffer_percent'].map(fieldname=>({fieldname,fieldtype:'Float'})),
 {fieldname:'confidence',fieldtype:'Select',options:'Low\nMedium\nHigh'},
 {fieldname:'item',fieldtype:'Link',options:'Item'},
 {fieldname:'packout_profile',fieldtype:'Link',options:'Packout Profile'},
 {fieldname:'output_plan',fieldtype:'Table',options:'Forecast Output Plan'},
 {fieldname:'process_adoption',fieldtype:'Link',options:'Lotus Process Adoption',read_only:1},
 {fieldname:'source_claims',fieldtype:'Table',options:'Forecast Source Claim',read_only:1},
]
const schema={fields,tables:{'Forecast Output Plan':[{fieldname:'item',fieldtype:'Link',options:'Item'},{fieldname:'packout_profile',fieldtype:'Link',options:'Packout Profile'},{fieldname:'source_share_percent',fieldtype:'Percent'}],'Forecast Source Claim':[{fieldname:'source_cut_operation',fieldtype:'Link',options:'Bunch Operation',read_only:1}]}}
const base={doctype:'Harvest Forecast',forecast_basis:'Cut Bud Operations',source_bunch_qty:10,avg_bunch_weight_kg:20,bunch_survival_rate_percent:95,quality_pass_rate_percent:100,packout_rate_percent:80,safety_buffer_percent:5,confidence:'High',output_plan:[{item:'ITEM',packout_profile:'PROFILE',source_share_percent:60}]}
function mountForm(model,readonly=false){
 const root=document.createElement('div');document.body.append(root)
 const app=createApp({render:()=>h(Form,{schema,model,scope:{farm:'F'},readonly})})
 app.component('SchemaForm',Schema);app.mount(root)
 return {root,unmount:()=>{app.unmount();root.remove()}}
}
function field(root,caption){return [...root.querySelectorAll('.lotus-field')].find(el=>el.querySelector(':scope>.lotus-field__label')?.textContent.replace('*','').trim()===caption)}

test('OneDrive draft keeps source weights and basis read-only while operators edit safety and product shares',async()=>{
 const model=reactive({...structuredClone(base),process_adoption:'ADOPT-1',source_claims:[{source_cut_operation:'CUT-1'}]})
 const view=mountForm(model)
 try{
  assert.equal(field(view.root,label('harvest_profile')),undefined)
  assert.equal(field(view.root,'Sản phẩm dự kiến'),undefined,'legacy single-product input is hidden')
  assert.equal(view.root.querySelectorAll('.lotus-field').length>0,true)
  for(const name of ['forecast_basis','source_bunch_qty','avg_bunch_weight_kg','bunch_survival_rate_percent','quality_pass_rate_percent','packout_rate_percent']){
   const wrapper=field(view.root,label(name));assert.ok(wrapper,name);assert.ok(wrapper.querySelector('.field-value'),`${name} shows server value`);assert.equal(wrapper.querySelector('input,select'),null)
  }
  assert.ok(field(view.root,label('safety_buffer_percent')).querySelector('input'))
  assert.ok(field(view.root,label('confidence')).querySelector('select'))
  const share=field(view.root,label('source_share_percent')).querySelector('input')
  assert.ok(share);share.value='75';share.dispatchEvent(new Event('input',{bubbles:true}));await tick()
  assert.equal(model.output_plan[0].source_share_percent,75)
  assert.match(view.root.textContent,/Phân bổ tỷ phần kg sơ chế OneDrive/);assert.match(view.root.textContent,/không nhân lại tỷ lệ/)
  assert.doesNotMatch(view.root.textContent,/Chỉ chọn một cách/)
 }finally{view.unmount()}
})

test('legacy forecast retains manual profile and single product controls without OneDrive shares',()=>{
 const view=mountForm(reactive({...structuredClone(base),process_adoption:'',source_claims:[]}))
 try{
  assert.ok(field(view.root,label('harvest_profile')).querySelector('input'))
  assert.ok(field(view.root,'Sản phẩm dự kiến').querySelector('input'))
  assert.ok(field(view.root,label('forecast_basis')).querySelector('select'))
  assert.ok(field(view.root,label('avg_bunch_weight_kg')).querySelector('input'))
  assert.equal(field(view.root,label('source_share_percent')),undefined)
  assert.match(view.root.textContent,/Chỉ chọn một cách/);assert.doesNotMatch(view.root.textContent,/Nguồn OneDrive đã đối chiếu/)
 }finally{view.unmount()}
})

test('OneDrive publications use reviewed retirement rather than the legacy clone revision action',async()=>{
 for(const process_adoption of ['ADOPT-1','']){
  const row={...structuredClone(base),name:'HF-1',farm:'F',farm_block:'B',crop_cycle:'C',supply_state:'Released',period_start_date:'2026-10-27',period_end_date:'2026-10-31',process_adoption}
  const view=mount(Workspace,{payload:{rows:[row]},canCreate:true})
  try{
   const tab=[...view.root.querySelectorAll('button')].find(el=>el.textContent==='Phiếu dự thu');tab.click();await tick();await tick()
   // Happy DOM has no grid layout; exercise the real mounted grid's row event boundary.
   const grid=view.root.querySelector('.forecast-grid-shell .lotus-data-table')?.__vueParentComponent?.proxy;assert.ok(grid,'shared forecast DataTable is mounted')
   grid.$emit('open',row);await tick()
   const inspector=view.root.querySelector('.forecast-inspector');assert.ok(inspector)
   const revise=[...inspector.querySelectorAll('button')].find(el=>el.textContent==='Tạo bản điều chỉnh')
   if(process_adoption){assert.equal(revise,undefined);assert.match(inspector.textContent,/đối soát phần đang giữ và kết thúc dự thu/)}
   else assert.ok(revise,'legacy forecast revision remains available')
  }finally{view.unmount()}
 }
})