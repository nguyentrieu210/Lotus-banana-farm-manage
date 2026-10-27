import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,h,ref,document,window} from './support/mount.mjs'
import {reactive} from 'vue'

const LotusField=await load('components/form/LotusField.vue')
const ModalForm=await load('components/form/ModalForm.vue')
const LineItemsEditor=await load('components/form/LineItemsEditor.vue')
const ListPage=await load('components/ListPage.vue')

test('LotusField wires label, required mark, hint and error to its control',async()=>{
 const value=ref('')
 const view=mount({setup:()=>()=>h(LotusField,{label:'Tên kho',required:true,hint:'Tên hiển thị',modelValue:value.value,'onUpdate:modelValue':v=>{value.value=v}})})
 await tick()
 const label=view.root.querySelector('label.lotus-field__label'),input=view.root.querySelector('input')
 assert.equal(label.getAttribute('for'),input.id,'the label names its control')
 assert.ok(label.querySelector('.lotus-field__required'),'required fields show *')
 assert.equal(input.getAttribute('aria-describedby'),input.id+'-hint')
 input.value='Kho phân bón';input.dispatchEvent(new window.Event('input'));await tick()
 assert.equal(value.value,'Kho phân bón')
 view.unmount()
})

test('LotusField picks the control from type and options',async()=>{
 const form=reactive({qty:'',unit:'',paid:false,amount:''})
 const view=mount({setup:()=>()=>h('div',[
  h(LotusField,{label:'Số lượng',type:'number',modelValue:form.qty,'onUpdate:modelValue':v=>{form.qty=v}}),
  h(LotusField,{label:'Đơn vị',options:[{value:'Kg',label:'Kg'},'Bao'],searchable:false,modelValue:form.unit,'onUpdate:modelValue':v=>{form.unit=v}}),
  h(LotusField,{label:'Đã trả',type:'checkbox',modelValue:form.paid,'onUpdate:modelValue':v=>{form.paid=v}}),
  h(LotusField,{label:'Số tiền',type:'money',modelValue:form.amount,'onUpdate:modelValue':v=>{form.amount=v}})
 ])})
 await tick()
 const qty=view.root.querySelector('input[type=number]'),amount=view.root.querySelector('input[inputmode=decimal][type=text]')
 qty.value='12.5';qty.dispatchEvent(new window.Event('input'));await tick()
 assert.equal(form.qty,12.5,'numbers come back as numbers')
 const select=view.root.querySelector('select')
 assert.deepEqual([...select.options].map(o=>o.textContent),['Chọn…','Kg','Bao'],'strings and {value,label} options both work')
 const box=view.root.querySelector('[role=checkbox]')
 assert.equal(view.root.querySelector('label[for="'+box.id+'"]').textContent,'Đã trả','the checkbox is labelled')
 box.click();await tick();assert.equal(form.paid,true)
 amount.value='1500000';amount.dispatchEvent(new window.Event('input'));await tick()
 assert.equal(amount.value,'1.500.000','money shows thousands separators in the field')
 assert.equal(form.amount,1500000,'and is stored as a number')
 view.unmount()
})

test('ModalForm shows the error, submits once through the form and closes with Hủy',async()=>{
 const open=ref(true),submitted=[]
 const view=mount({setup:()=>()=>h(ModalForm,{modelValue:open.value,'onUpdate:modelValue':v=>{open.value=v},title:'Thêm kho',error:'Tên kho đã tồn tại.',onSubmit:()=>submitted.push(1)},()=>h(LotusField,{label:'Tên kho'}))})
 await tick();await tick()
 const dialog=document.querySelector('dialog.workspace-modal')
 assert.equal(dialog.querySelector('[role=alert]').textContent,'Tên kho đã tồn tại.')
 const buttons=[...dialog.querySelectorAll('footer button')].map(b=>b.textContent.trim())
 assert.deepEqual(buttons,['Hủy','Lưu'],'standard footer')
 dialog.querySelector('form').dispatchEvent(new window.Event('submit',{cancelable:true}));await tick()
 assert.equal(submitted.length,1)
 ;[...dialog.querySelectorAll('footer button')].find(b=>b.textContent.trim()==='Hủy').click();await tick()
 assert.equal(open.value,false)
 view.unmount()
})

test('LineItemsEditor adds and removes rows but keeps the minimum',async()=>{
 const rows=ref([{item:'A',qty:1}])
 const columns=[{field:'item',label:'Vật tư',required:true},{field:'qty',label:'Số lượng',type:'number'}]
 const view=mount({setup:()=>()=>h(LineItemsEditor,{modelValue:rows.value,'onUpdate:modelValue':v=>{rows.value=v},columns,newRow:()=>({item:'',qty:1}),title:'Hàng hóa'})})
 await tick()
 assert.deepEqual([...view.root.querySelectorAll('.lotus-lines__head > span')].map(s=>s.textContent).slice(0,2),['Vật tư*','Số lượng'])
 assert.equal(view.root.querySelector('.lotus-lines__remove').disabled,true,'the last row cannot be removed')
 ;[...view.root.querySelectorAll('button')].find(b=>b.textContent.includes('Thêm dòng')).click();await tick()
 assert.equal(rows.value.length,2)
 view.root.querySelectorAll('.lotus-lines__remove')[0].click();await tick()
 assert.deepEqual(rows.value.map(r=>r.item),[''],'the chosen row is removed')
 const input=view.root.querySelector('input[aria-label="Vật tư dòng 1"]')
 input.value='Phân NPK';input.dispatchEvent(new window.Event('input'));await tick()
 assert.equal(rows.value[0].item,'Phân NPK','cells edit the row in place')
 view.unmount()
})

test('ListPage pages on the server and forwards table events',async()=>{
 const starts=[],searches=[]
 const view=mount({setup:()=>()=>h(ListPage,{title:'Phiếu nhập kho',rows:[{name:'MAT-1'}],columns:[{field:'name',headerName:'Số phiếu'}],paged:true,start:0,total:120,'onUpdate:start':v=>starts.push(v),'onUpdate:search':v=>searches.push(v)})})
 await tick();await tick()
 assert.equal(view.root.querySelector('section.lotus-list-page').getAttribute('aria-label'),'Phiếu nhập kho')
 assert.ok(view.root.querySelector('.workspace-list-toolbar input[type=search]'),'shared toolbar search')
 assert.match(view.root.querySelector('.lotus-pagination').textContent,/1–1 \/ 120/)
 const search=view.root.querySelector('input[type=search]');search.value='MAT';search.dispatchEvent(new window.Event('input'));await tick()
 assert.deepEqual(searches,['MAT'])
 view.unmount()
})
