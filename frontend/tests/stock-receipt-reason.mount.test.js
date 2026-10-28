import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,document,window,h,ref} from './support/mount.mjs'
Object.defineProperty(globalThis,'customElements',{value:window.customElements,configurable:true})
const Reason=await load('components/StockReceiptReason.vue')
const Warehouse=await load('WarehouseMobile.vue')
const reasons=[{value:'Purchase',label:'Mua ngoài',supplier:true},{value:'Recovery',label:'Thu hồi từ lô',lot:true},{value:'Surplus',label:'Thừa kiểm kê'}]
let view,calls,failOptions
globalThis.fetch=async(url,opts={})=>{
 const u=new URL(url,'http://localhost'),method=u.pathname.split('/api/method/')[1],args=opts.body?JSON.parse(opts.body):Object.fromEntries(u.searchParams)
 calls.push({method,args})
 if(method.endsWith('.receipt_options')&&failOptions)return {ok:false,status:500,json:async()=>({message:'Chưa tải được lý do nhập kho'})}
 const message=method.endsWith('.receipt_options')?{enabled:true,reasons,suppliers:[{name:'NCC',supplier_name:'Nhà cung cấp thử'}]}:
  method.endsWith('.bootstrap')?{user:'test@example.invalid',companies:[{name:'C'}],today:'2026-10-24',permissions:{'Stock Entry':true}}:
  method.endsWith('.setup')?{warehouses:[{name:'K',warehouse_name:'Kho thử'}],items:[{name:'I',item_name:'Vật tư thử',stock_uom:'Nos'}],suppliers:[],conversions:[]}:
  method.endsWith('.create_draft')?{doctype:'Stock Entry',name:'SE',docstatus:0}:
  method.endsWith('.document')?{doctype:'Stock Entry',name:'SE',posting_date:'2026-10-24',items:[]}:[]
 return {ok:true,status:200,json:async()=>({message})}
}
test.beforeEach(()=>{calls=[];failOptions=false})
test.afterEach(()=>view?.unmount())
async function click(text){const button=[...document.querySelectorAll('button')].find(e=>e.textContent.includes(text));assert.ok(button,text);button.click();await tick();await tick()}
function select(label,value){const e=document.querySelector(`select[aria-label="${label}"]`);assert.ok(e,label);e.value=value;e.dispatchEvent(new window.Event('change',{bubbles:true}))}
async function choose(label,text){const input=document.querySelector(`input[aria-label="${label}"]`);assert.ok(input,label);input.focus();await tick();const option=[...document.querySelectorAll('[role=option]')].find(e=>e.textContent.includes(text));assert.ok(option,text);option.click();await tick()}
async function start(){view=mount(Warehouse);await tick();await tick();await click('Nhập không theo đơn');await choose('Tên hàng','Vật tư thử')}
async function submit(){view.root.querySelector('form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await tick();await tick()}
const writes=()=>calls.filter(c=>c.method.endsWith('.create_draft'))
test('mobile direct receipt requires a reason and supplier, then sends both to the native draft',async()=>{
 await start();assert.equal(document.querySelector('select[aria-label="Lý do nhập kho"]').required,true)
 await submit();assert.equal(writes().length,0);assert.match(view.root.textContent,/Chọn lý do nhập kho/)
 select('Lý do nhập kho','Purchase');await tick();await submit();assert.equal(writes().length,0);assert.match(view.root.textContent,/Chọn nhà cung cấp/)
 await choose('Nhà cung cấp','Nhà cung cấp thử');await submit();assert.equal(writes().length,0);assert.match(view.root.textContent,/Nhập giá mua/)
 const price=document.querySelector('input[aria-label="Đơn giá mua"]');assert.ok(price,'bought goods ask their price');price.value='12000';price.dispatchEvent(new window.Event('input',{bubbles:true}));await tick();await submit()
 assert.equal(writes().length,1);assert.equal(writes()[0].args.receipt_reason,'Purchase');assert.equal(writes()[0].args.supplier,'NCC');assert.equal(writes()[0].args.lines[0].item,'I');assert.match(view.root.textContent,/Kiểm tra phiếu/)
})
test('mobile recovery receipt requires the source lot and preserves it in the request',async()=>{
 await start();select('Lý do nhập kho','Recovery');await tick();await submit();assert.equal(writes().length,0);assert.match(view.root.textContent,/Nhập lô thu hồi/)
 const lot=document.querySelector('input[aria-label="Lô thu hồi vật tư"]');assert.ok(lot);lot.value='A01';lot.dispatchEvent(new window.Event('input',{bubbles:true}));await tick();await submit()
 assert.equal(writes()[0].args.receipt_reason,'Recovery');assert.equal(writes()[0].args.lines[0].area,'A01');assert.equal(writes()[0].args.supplier,'')
})
test('mobile surplus receipt does not require a supplier or purchase order',async()=>{
 await start();select('Lý do nhập kho','Surplus');await tick();await submit()
 assert.equal(writes().length,1);assert.equal(writes()[0].args.receipt_reason,'Surplus');assert.equal(document.querySelector('input[aria-label="Nhà cung cấp"]'),null)
})
test('shared desktop reason fields expose loading failure and retry rather than hiding mandatory inputs',async()=>{
 failOptions=true;const handle=ref(null),reason=ref(''),supplier=ref('')
 view=mount({render:()=>h(Reason,{ref:handle,reason:reason.value,supplier:supplier.value,'onUpdate:reason':v=>reason.value=v,'onUpdate:supplier':v=>supplier.value=v})});await tick();await tick()
 assert.match(view.root.textContent,/Chưa tải được lý do/);assert.match(await handle.value.validate(),/Chưa tải được lý do/)
 failOptions=false;await click('Thử lại lý do nhập kho');assert.ok([...view.root.querySelectorAll('label')].some(e=>e.textContent.includes('Lý do nhập kho')))
 reason.value='Surplus';await tick();assert.equal(await handle.value.validate(),'')
})
