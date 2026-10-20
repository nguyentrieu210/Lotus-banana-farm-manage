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
