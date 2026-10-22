import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick} from './support/mount.mjs'
import {reactive} from 'vue'
const Form=await load('components/SchemaForm.vue')
test('choosing a submitted cut cohort fills its lot, cycle, suckers and tag together',async()=>{
 const model=reactive({farm:'F',source_cut_operation:'',ribbon_color:''})
 const option={value:'CUT-1',label:'CUT-1 · 21/10/2026 · 100 buồng',context:{farm:'F',farm_block:'B',farm_plot:'P',crop_cycle:'C',sucker_selection_batch:'S',tag:'T'}}
 const schema={doctype:'Harvest Actual',fields:[{fieldname:'source_cut_operation',fieldtype:'Link',options:'Bunch Operation',label:'Đợt cắt bắp gốc'}],tables:{}}
 const view=mount(Form,{schema,model,scope:{farm:'F'},linkOptions:async()=>[option]})
 try{
  view.root.querySelector('input').click();await tick();await tick()
  const choice=[...document.querySelectorAll('[role=option]')].find(el=>el.textContent.includes('CUT-1'))
  assert.ok(choice,'submitted cut option appears');choice.click();await tick()
  for(const [key,value] of Object.entries({farm:'F',farm_block:'B',farm_plot:'P',crop_cycle:'C',sucker_selection_batch:'S',ribbon_color:'T'}))assert.equal(model[key],value)
 }finally{view.unmount()}
})
test('cycle onboarding exposes the actual plot needed for an inherited root',async()=>{
 const field={fieldname:'farm_plot',fieldtype:'Link',options:'Farm Plot',label:'Thửa theo dõi'}
 const cycle=mount(Form,{schema:{doctype:'Crop Cycle',fields:[field],tables:{}},model:reactive({}),scope:{farm:'F'}})
 try{assert.ok(cycle.root.querySelector('input'),'a new cycle must be mapped to a real plot')}finally{cycle.unmount()}
 const operation=mount(Form,{schema:{doctype:'Harvest Actual',fields:[field],tables:{}},model:reactive({}),scope:{farm:'F'}})
 try{assert.equal(operation.root.querySelector('input'),null,'subsequent operations derive their plot from the cycle')}finally{operation.unmount()}
})

test('an inherited opening cut clears a previously selected sucker batch',async()=>{
 const model=reactive({farm:'OLD-F',farm_block:'OLD-B',farm_plot:'OLD-P',crop_cycle:'OLD-C',sucker_selection_batch:'OLD-S',ribbon_color:'OLD-T'})
 const option={value:'OPEN-CUT',label:'OPEN-CUT',context:{farm:'F',farm_block:'B',farm_plot:'P',crop_cycle:'OPEN-CYCLE',sucker_selection_batch:null,tag:'T'}}
 const schema={doctype:'Harvest Actual',fields:[{fieldname:'source_cut_operation',fieldtype:'Link',options:'Bunch Operation',label:'Đợt cắt bắp gốc'}],tables:{}}
 const view=mount(Form,{schema,model,scope:{farm:'F'},linkOptions:async()=>[option]})
 try{
  view.root.querySelector('input').click();await tick();await tick()
  const choice=[...document.querySelectorAll('[role=option]')].find(el=>el.textContent.includes('OPEN-CUT'))
  assert.ok(choice);choice.click();await tick()
  assert.equal(model.sucker_selection_batch,'')
  assert.equal(model.crop_cycle,'OPEN-CYCLE');assert.equal(model.farm_plot,'P');assert.equal(model.ribbon_color,'T')
 }finally{view.unmount()}
})

test('inherited close labels cover recorded production instead of asserting complete planting history',()=>{
 const schema={doctype:'Cycle Closing Report',fields:[{fieldname:'origin_basis',fieldtype:'Select',options:'Observed\nHandover',read_only:1},{fieldname:'coverage_start_date',fieldtype:'Date',read_only:1},{fieldname:'planting_date_known',fieldtype:'Check',read_only:1},{fieldname:'planted_qty',fieldtype:'Float',read_only:1},{fieldname:'tons_per_ha',fieldtype:'Float',read_only:1}],tables:{}}
 const model={origin_basis:'Handover',coverage_start_date:'2026-10-21',planting_date_known:0,planted_qty:0,tons_per_ha:2}
 const view=mount(Form,{schema,model,scope:{farm:'F'},readonly:true})
 try{assert.match(view.root.textContent,/Vụ kế thừa bàn giao/);assert.match(view.root.textContent,/2026-10-21/);assert.match(view.root.textContent,/Đã biết ngày trồng thực tếKhông/);assert.match(view.root.textContent,/Số cây trồng đã ghi nhận/);assert.match(view.root.textContent,/Sản lượng đã ghi nhận/)}finally{view.unmount()}
})
