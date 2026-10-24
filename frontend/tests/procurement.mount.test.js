import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,window,document,h,ref} from './support/mount.mjs'
import {allowedKinds,quoteChoices,purchaseRequest} from '../src/procurement.js'
const Workspace=await load('components/ProcurementWorkspace.vue')
const DocumentForm=await load('components/ProcurementDocumentForm.vue')
const catalogue={items:[{name:'I',item_name:'Phân',stock_uom:'Kg',is_stock_item:1},{name:'S',item_name:'Dịch vụ',stock_uom:'Nos',is_stock_item:0}],conversions:[],suppliers:[{name:'N',supplier_name:'NCC'}],warehouses:[{name:'K',warehouse_name:'Kho'}],can_create:true,can_quote:true,can_finance:false,can_view_finance:false,farms:[]}
let calls=[],handler,view
globalThis.fetch=async(url,opts={})=>{
 const parsed=new URL(url,'http://localhost'),method=parsed.pathname.split('/api/method/')[1]
 const args=opts.body?JSON.parse(opts.body):Object.fromEntries(parsed.searchParams)
 calls.push({method,args,write:opts.method==='POST'})
 const result=await handler(method,args)
 return {ok:!result?.exc_type,status:result?.exc_type?417:200,json:async()=>result?.exc_type?result:{message:result}}
}
const click=async label=>{const b=[...document.querySelectorAll('button')].find(n=>n.textContent.trim()===label);assert.ok(b,label);b.click();await tick();await tick()}
test.beforeEach(()=>{calls=[];handler=async(method,args)=>{
 if(method.endsWith('.bootstrap'))return args.company?catalogue:{companies:[{name:'C'}],csrf_token:'csrf'}
 if(method.endsWith('.needs'))return []
 if(method.endsWith('.orders'))return []
 if(method.endsWith('.quotations'))return [{name:'QI',quotation:'Q',supplier:'N',item_name:'Phân',qty:1,docstatus:0,modified:'v1',gross:null}]
 return {}
}})
test.afterEach(()=>view?.unmount())

test('new purchase route loads company scope and keeps finance actions hidden for buyer',async()=>{
 view=mount(Workspace,{company:'C',today:'2026-10-23'});await tick();await tick()
 assert.ok(calls.some(c=>c.method.endsWith('.needs')&&c.args.company==='C'))
 assert.ok(![...view.root.querySelectorAll('nav button')].some(b=>b.textContent==='Thanh toán'))
 await click('Đơn mua');await click('Thêm đơn mua')
 assert.match(view.root.textContent,/Đơn giá chưa VAT/)
 assert.ok(view.root.querySelector('form'))
})

test('unknown quote has no selectable payment price and confirmation targets original quotation',async()=>{
 view=mount(Workspace,{company:'C',mobile:true,today:'2026-10-23'});await tick();await tick()
 await click('Báo giá')
 const cell=[...view.root.querySelectorAll('.van-cell')].find(c=>c.textContent.includes('Phân'))
 assert.match(cell.textContent,/Chưa có giá/);cell.click();await tick()
 await click('Xác nhận báo giá')
 const confirm=calls.find(c=>c.method.endsWith('.confirm_quotation'))
 assert.equal(confirm.args.name,'Q');assert.equal(confirm.args.modified,'v1');assert.ok(confirm.write)
})

test('purchase editor classifies service from existing Item and removes extra lines',async()=>{
 let draft={supplier:'N',warehouse:'K',expected_date:'2026-10-23',notes:'',items:[{id:'1',item:'S',qty:1,uom:'Nos',rate:10,kind:'Service'},{id:'2',item:'I',qty:2,uom:'Kg',rate:20,kind:'Material'}]}
 view=mount(DocumentForm,{mobile:true,modelValue:draft,catalog:catalogue,type:'order','onUpdate:modelValue':next=>{draft=next}})
 await tick();const deleteButton=[...view.root.querySelectorAll('button')].find(b=>b.textContent==='Xóa dòng');deleteButton.click();await tick()
 assert.equal(draft.items.length,1);assert.equal(draft.items[0].item,'I')
 assert.deepEqual(allowedKinds(catalogue.items[1]).map(k=>k.value),['Service'])
})

test('quote selections preserve line version, reason and partial quantity',()=>{
 assert.deepEqual(quoteChoices([{name:'L',quotation:'Q',modified:'v',qty:10}],{L:{selected:true,qty:4,reason:'Giao sớm'}}),
  [{quotation:'Q',line:'L',modified:'v',qty:4,reason:'Giao sớm'}])
})

test('snapshot conflict retries reuse the exact idempotency key and payload',async()=>{
 const payload={client_key:'same',amount:100};let attempts=0
 const result=await purchaseRequest(async(method,args)=>{assert.equal(args,payload);if(++attempts===1){const error=Error('snapshot');error.code='QueryDeadlockError';throw error}return {voucher:'PE1'}},'write',payload,true)
 assert.equal(attempts,2);assert.equal(result.voucher,'PE1')
})

test('warehouse create-order action waits for catalogue initialization before opening the shared form',async()=>{
 let ready;const gate=new Promise(resolve=>{ready=resolve})
 const usual=handler;handler=async(method,args)=>method.endsWith('.bootstrap')&&args.company?gate:usual(method,args)
 const handle=ref(null)
 view=mount({render:()=>h(Workspace,{ref:handle,company:'C',today:'2026-10-23'})});await tick()
 let complete=false;const action=handle.value.createOrder().then(()=>{complete=true})
 await tick();assert.equal(complete,false);assert.equal(view.root.querySelector('form'),null)
 ready(catalogue);await action;await tick()
 assert.ok(view.root.querySelector('form'));assert.match(view.root.textContent,/Đơn giá chưa VAT/)
})

test('warehouse receiving action opens only submitted orders that still await delivery',async()=>{
 const usual=handler;handler=async(method,args)=>method.endsWith('.orders')?[
  {name:'PO-PENDING',docstatus:1,status:'Về một phần',remaining_lines:1},
  {name:'PO-DRAFT',docstatus:0,status:'Nháp',remaining_lines:1},
  {name:'PO-DONE',docstatus:1,status:'Đã nhận đủ',remaining_lines:0}]:usual(method,args)
 const handle=ref(null)
 view=mount({render:()=>h(Workspace,{ref:handle,company:'C',mobile:true})});await tick()
 await handle.value.startReceiving();await tick()
 assert.match(view.root.textContent,/PO-PENDING/);assert.doesNotMatch(view.root.textContent,/PO-DRAFT|PO-DONE/)
 await click('Xem tất cả đơn');assert.match(view.root.textContent,/PO-DRAFT/)
})
