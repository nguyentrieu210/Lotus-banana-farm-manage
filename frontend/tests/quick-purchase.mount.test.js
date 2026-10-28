import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,document,window,h,ref} from './support/mount.mjs'
Object.defineProperty(globalThis,'customElements',{value:window.customElements,configurable:true})
const Form=await load('components/stock/StockDocumentForm.vue')
const reasons=[{value:'Purchase',label:'Mua ngoài',supplier:true},{value:'Surplus',label:'Thừa kiểm kê'}]
let calls=[]
globalThis.fetch=async(url,opts={})=>{
 const u=new URL(url,'http://localhost'),method=u.pathname.split('/api/method/')[1],args=opts.body?JSON.parse(opts.body):Object.fromEntries(u.searchParams)
 calls.push({method,args})
 const message=method.endsWith('.receipt_options')?{enabled:true,reasons,suppliers:[{name:'NCC',supplier_name:'Nhà cung cấp thử'}]}:
  method.endsWith('.receipt_accounts')?{accounts:[],default_account:''}:[]
 return {ok:true,status:200,json:async()=>({message})}
}

test('Mua nhanh opens the receipt form as a purchase: no reason to pick, camera reader, one save that posts',async()=>{
 const form=ref(null)
 const view=mount({setup:()=>()=>h(Form,{ref:form,company:'C',warehouses:[{name:'K',warehouse_name:'Kho 1'}],session:{today:'2026-10-28',companies:[{name:'C',default_currency:'VND'}]}})})
 await tick();form.value.openQuick();await tick();await tick();await tick()
 const dialog=document.body.textContent
 assert.match(dialog,/Mua nhanh/)
 assert.match(dialog,/Lưu & nhập kho/)
 assert.ok(document.querySelector("[aria-label=\"Chụp chứng từ bằng camera\"]")||/Chụp chứng từ/.test(dialog),"camera reader")
 assert.equal(document.querySelector('[aria-label="Lý do nhập kho"]'),null,'the reason is fixed to Purchase')
 assert.ok([...document.querySelectorAll('label,span')].some(e=>e.textContent.trim().startsWith('Nhà cung cấp')),'the supplier is still asked')
 assert.match(dialog,/Thêm chi phí vận chuyển/,'transport costs are one click away, not an open section')
 assert.doesNotMatch(dialog,/Các khoản chi phí/)
 view.unmount()
})
