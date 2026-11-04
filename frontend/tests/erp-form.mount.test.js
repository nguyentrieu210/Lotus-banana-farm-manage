import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,document,window} from './support/mount.mjs'
Object.defineProperty(globalThis,'customElements',{value:window.customElements,configurable:true})
if(!globalThis.crypto?.randomUUID)Object.defineProperty(globalThis,'crypto',{value:{randomUUID:()=>Math.random().toString(36).slice(2)},configurable:true})
const ErpForm=await load('components/erp/ErpForm.vue')

// A Sales Invoice-like DocType: required customer, items grid, a field shown only for returns, a server-computed total.
const schema={doctype:'Sales Invoice',title_field:'customer',is_submittable:1,fields:[
 {fieldname:'customer',fieldtype:'Link',options:'Customer',label:'Khách hàng',reqd:1},
 {fieldname:'cb',fieldtype:'Column Break'},
 {fieldname:'posting_date',fieldtype:'Date',label:'Ngày hạch toán',reqd:1},
 {fieldname:'is_return',fieldtype:'Check',label:'Là hóa đơn trả hàng'},
 {fieldname:'return_against',fieldtype:'Link',options:'Sales Invoice',label:'Trả hàng cho hóa đơn',depends_on:'eval:doc.is_return'},
 {fieldname:'sec',fieldtype:'Section Break',label:'Hàng hóa'},
 {fieldname:'items',fieldtype:'Table',options:'Sales Invoice Item',label:'Hàng hóa',reqd:1},
 {fieldname:'grand_total',fieldtype:'Currency',label:'Tổng cộng',read_only:1}],
 tables:{'Sales Invoice Item':{doctype:'Sales Invoice Item',fields:[
  {fieldname:'item_code',fieldtype:'Link',options:'Item',label:'Mã hàng',reqd:1,in_list_view:1},
  {fieldname:'qty',fieldtype:'Float',label:'Số lượng',in_list_view:1},
  {fieldname:'rate',fieldtype:'Currency',label:'Đơn giá',in_list_view:1},
  {fieldname:'amount',fieldtype:'Currency',label:'Thành tiền',read_only:1,in_list_view:1}]}},
 permissions:{read:true,create:true,write:true,submit:true}}
const blank={doctype:'Sales Invoice',name:'new-sales-invoice-1',docstatus:0,posting_date:'2026-11-04',items:[],__islocal:1}
let calls,saved
globalThis.fetch=async(url,opts={})=>{
 const u=new URL(url,'http://localhost'),method=u.pathname.split('/api/method/lotus_farm.erp_workbench.')[1],args=opts.body?JSON.parse(opts.body):Object.fromEntries(u.searchParams)
 calls.push({method,args})
 const loaded=doc=>({doc,permissions:{read:true,create:true,write:true,submit:true,cancel:true,print:true},transitions:[],actions:doc.docstatus===1?[{target:'Delivery Note',label:'Delivery Note'}]:[],is_new:!!doc.__islocal})
 const message=method==='schema'?schema:
  method==='document'?loaded(saved||blank):
  method==='link_options'?(args.fieldname==='customer'?[{value:'KH-01',label:'Chợ đầu mối'}]:[{value:'CHUOI-A',label:'Chuối loại A'}]):
  method==='party_details'?{customer_name:'Chợ đầu mối',not_a_field:1}:
  method==='linked_values'?{}:
  method==='item_details'?{rate:15000,qty:1,item_name:'Chuối loại A'}:
  method==='preview'?{...args.values,grand_total:45000,items:args.values.items.map(r=>({...r,amount:r.qty*r.rate}))}:
  method==='action'?loaded(saved={...args.values,__islocal:undefined,name:'ACC-SINV-0001',docstatus:args.action==='submit'?1:0,modified:'2026-11-04 10:00:00'}):null
 return {ok:true,status:200,json:async()=>({message})}
}
let view
test.beforeEach(()=>{calls=[];saved=null})
test.afterEach(()=>view?.unmount())
const text=()=>view.root.textContent
const button=label=>[...view.root.querySelectorAll('button')].find(b=>b.textContent.trim().startsWith(label))
async function choose(label,option){const input=view.root.querySelector(`input[aria-label="${label}"]`)||[...view.root.querySelectorAll('input')].find(i=>i.closest('.lotus-field')?.textContent.includes(label));assert.ok(input,label);input.focus();input.value=option.slice(0,3);input.dispatchEvent(new window.Event('input',{bubbles:true}));await tick();await tick();const item=[...document.querySelectorAll('[role=option]')].find(e=>e.textContent.includes(option));assert.ok(item,option);item.dispatchEvent(new window.MouseEvent('mousedown',{bubbles:true}));item.click();await tick();await tick()}
const wait=ms=>new Promise(r=>setTimeout(r,ms))

test('new ERP document: metadata layout, depends_on, required check, party and item fill, server totals, idempotent save and submit',async()=>{
 let asked=0
 view=mount(ErpForm,{doctype:'Sales Invoice',label:'Hóa đơn bán hàng',company:'Lotus Agritech',currency:'VND',confirm:async()=>{asked++;return true}})
 await tick();await tick()
 assert.match(text(),/Mới · Hóa đơn bán hàng/)
 assert.doesNotMatch(text(),/Trả hàng cho hóa đơn/,'return field hidden until it is a return')
 const check=[...view.root.querySelectorAll('[role=checkbox],input[type=checkbox]')].find(e=>e.closest('.lotus-field')?.textContent.includes('Là hóa đơn trả hàng'));assert.ok(check);check.click();await tick()
 assert.match(text(),/Trả hàng cho hóa đơn/);check.click();await tick()

 button('Lưu').click();await tick()
 assert.match(text(),/Cần nhập: Khách hàng/);assert.equal(calls.filter(c=>c.method==='action').length,0)

 await choose('Khách hàng','Chợ đầu mối')
 assert.ok(calls.some(c=>c.method==='party_details'&&c.args.party==='KH-01'),'customer fills party details')
 button('Thêm dòng').click();await tick()
 await choose('Mã hàng dòng 1','Chuối loại A')
 const details=calls.find(c=>c.method==='item_details');assert.ok(details);assert.equal(details.args.item_code,'CHUOI-A');assert.equal(details.args.company,'Lotus Agritech')
 const qty=view.root.querySelector('input[aria-label="Số lượng dòng 1"]');qty.value='3';qty.dispatchEvent(new window.Event('input',{bubbles:true}));await tick()
 await wait(650);await tick()
 assert.ok(calls.some(c=>c.method==='preview'),'totals recomputed on the server');assert.match(text(),/45\.000/)

 button('Lưu').click();await tick();await tick()
 const save=calls.find(c=>c.method==='action');assert.equal(save.args.action,'save');assert.ok(save.args.client_key);assert.equal(save.args.values.customer,'KH-01');assert.equal(save.args.values.items[0].qty,3)
 assert.match(text(),/Đã lưu/)
 button('Ghi sổ').click();await tick();await tick()
 assert.equal(asked,1,'submit asks first');const submit=calls.filter(c=>c.method==='action')[1];assert.equal(submit.args.action,'submit');assert.notEqual(submit.args.client_key,save.args.client_key)
 assert.match(text(),/Đã ghi sổ/);assert.ok(button('Tạo Phiếu giao hàng')||button('Tạo'),'next-document action offered after submit')
})
