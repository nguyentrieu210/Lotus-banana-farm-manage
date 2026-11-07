import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,window} from './support/mount.mjs'
const Progress=await load('components/PurchaseProgress.vue')
const Form=await load('components/ProcurementDocumentForm.vue')
const Mobile=await load('components/MobilePurchaseProposal.vue')

test('purchase progress opens native chain documents inside the workspace',async()=>{
 let opened
 const view=mount(Progress,{navigate:true,progress:{stage:'Đang mua',lines:[],orders:[{name:'PO-1',docstatus:1}],payments:[{name:'PAY-1',docstatus:0,amount:100}],outstanding_amount:200},onOpen:(row,type)=>{opened={row,type}}})
 await tick()
 const order=[...view.root.querySelectorAll('a')].find(a=>a.textContent.includes('PO-1'))
 assert.ok(order)
 order.click();await tick()
 assert.deepEqual(opened,{row:{name:'PO-1',docstatus:1},type:'orders'})
 assert.match(view.root.textContent,/Đang mua/)
 assert.match(view.root.textContent,/Còn nợ/)
 assert.match(view.root.textContent,/PAY-1/)
 view.unmount()
})

test('independent proposal form exposes department, reason, stock and expected price without a work plan',async()=>{
 const view=mount(Form,{type:'need',catalog:{items:[],warehouses:[],conversions:[]},modelValue:{department:'Kho',notes:'Mua dự trữ',warehouse:'',expected_date:'2026-11-07',items:[{item:'',qty:2,rate:0,uom:''}]}})
 await tick()
 assert.match(view.root.textContent,/Bộ phận đề xuất/)
 assert.ok(view.root.querySelector('[aria-label="Giá dự kiến dòng 1"]'))
 assert.ok(view.root.querySelector('[aria-label="Tồn tham khảo dòng 1"]'))
 assert.equal(view.root.querySelector('[aria-label*="công việc"]'),null)
 view.unmount()
})

test('mobile proposals filter purchasing progress independently of signature state',async()=>{
 const previous=globalThis.fetch
 globalThis.fetch=async()=>({ok:true,json:async()=>({message:[{name:'MR-DRAFT',state:'Nháp',stage:'Nháp'},
  {name:'MR-ORDERED',state:'Đã duyệt',stage:'Đang mua'}]})})
 const view=mount(Mobile,{company:'C'})
 try {
  await tick();await tick()
  ;[...view.root.querySelectorAll('[role=tab]')].find(b=>b.textContent==='Tất cả').click()
  await tick();await tick()
  const select=view.root.querySelector('select[aria-label="Tiến độ"]')
  assert.ok(select)
  select.value='Đang mua';select.dispatchEvent(new window.Event('change',{bubbles:true}))
  await tick()
  assert.match(view.root.textContent,/MR-ORDERED/)
  assert.doesNotMatch(view.root.textContent,/MR-DRAFT/)
 } finally {view.unmount();globalThis.fetch=previous}
})
