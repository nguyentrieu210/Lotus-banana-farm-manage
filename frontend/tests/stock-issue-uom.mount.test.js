import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,document,window,h,ref} from './support/mount.mjs'
import {itemUnits,conversionFactor,stockQuantity,quantityLimit} from '../src/stock-units.js'
Object.defineProperty(globalThis,'customElements',{value:window.customElements,configurable:true})
const Form=await load('components/stock/StockDocumentForm.vue')
const Warehouse=await load('WarehouseMobile.vue')
const units=[{uom:'Kg',conversion_factor:1},{uom:'Bao',conversion_factor:25},{uom:'Gram',conversion_factor:0.001}]
const item={name:'I',item_name:'Phân thử',stock_uom:'Kg',uoms:units,pack_uom:'Bao',pack_factor:25,actual_qty:100}
let view,calls,handle
globalThis.fetch=async(url,opts={})=>{
 const u=new URL(url,'http://localhost'),method=u.pathname.split('/api/method/')[1],args=opts.body?JSON.parse(opts.body):Object.fromEntries(u.searchParams)
 calls.push({method,args})
 const message=method.endsWith('.bootstrap')?{user:'test@example.invalid',companies:[{name:'C'}],today:'2026-10-31',permissions:{'Stock Entry':true}}:
  method.endsWith('.setup')?{warehouses:[{name:'K',warehouse_name:'Kho thử'}],items:[item],suppliers:[],conversions:units.map(r=>({...r,parent:'I'}))}:
  method.endsWith('.overview')?{items:[item]}:
  method.endsWith('.employee_choices')?[{value:'EMP',label:'Người nhận thử'}]:
  method.endsWith('.block_codes')?[{code:'A01',label:'A01'}]:
  method.endsWith('.issue_sources')?{rows:[{name:'MR',date:'2026-10-31'}]}:
  method.endsWith('.issue_lines')?{rows:[{item:'I',item_name:item.item_name,uom:'Kg',stock_uom:'Kg',uoms:units,qty:50,required_qty:50,allocated_qty:0,remaining_qty:50,area:'A01',material_request:'MR',material_request_item:'MRI'}]}:
  method.endsWith('.create_draft')?{doctype:'Stock Entry',name:'SE',docstatus:0}:
  method.endsWith('.document')?{doctype:'Stock Entry',name:'SE',items:[]}:
  method.endsWith('.receipt_options')?{enabled:true,reasons:[],suppliers:[]}:[]
 return {ok:true,status:200,json:async()=>({message})}
}
test.beforeEach(()=>{calls=[];handle=ref(null)})
test.afterEach(()=>view?.unmount())
function control(label){
 return document.querySelector(`[aria-label="${label}"]`)||document.getElementById([...document.querySelectorAll('label')].find(e=>e.textContent.replace(/\*/g,'').trim()===label)?.htmlFor)
}
async function choose(label,text){
 const element=control(label)
 assert.ok(element,`missing ${label}`);element.focus();element.click();await tick();await tick()
 const option=[...document.querySelectorAll('[role=option]')].find(e=>e.textContent.includes(text))
 assert.ok(option,`missing option ${text}`);option.click();await tick()
}
function input(label,value){const e=control(label);assert.ok(e,label);e.value=value;e.dispatchEvent(new window.Event('input',{bubbles:true}))}
function select(label,value){const e=control(label);assert.ok(e,label);e.value=value;e.dispatchEvent(new window.Event('change',{bubbles:true}))}
async function desktop(){view=mount({render:()=>h(Form,{ref:handle,company:'C',warehouse:'K',warehouses:[{name:'K',warehouse_name:'Kho thử'}],session:{today:'2026-10-31',companies:[{name:'C',default_currency:'VND'}]}})});await handle.value.open('issue');await tick();await tick()}
test('configured units have item-specific factors and source limits use stock units',()=>{
 const row={stock_uom:'Kg',uom:'Bao',uoms:units,qty:2,remaining_qty:50}
 assert.equal(itemUnits(row).length,3);assert.equal(conversionFactor(row),25);assert.equal(stockQuantity(row),50);assert.equal(quantityLimit(row),2)
 assert.equal(stockQuantity({...row,uom:'Gram',qty:500}),0.5)
 assert.ok(Number.isNaN(conversionFactor({...row,uom:'Other'})))
})
test('desktop manual issue selects an alternative unit, previews stock quantity and preserves request unit',async()=>{
 await desktop();await choose('Vật tư dòng 1','Phân thử');await choose('Đơn vị xuất dòng 1','Bao')
 input('Số lượng dòng 1','2');await tick();assert.match(document.body.textContent,/50 kg/)
 await choose('Người nhận vật tư (HRMS)','Người nhận thử');await choose('Khu vực / lô sử dụng dòng 1','A01');input('Lý do xuất thủ công','Dùng thử nghiệm')
 document.querySelector('form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await tick();await tick()
 const save=calls.find(c=>c.method.endsWith('.create_draft'));assert.ok(save);assert.equal(save.args.lines[0].uom,'Bao');assert.equal(Number(save.args.lines[0].qty),2)
})
test('desktop request issue converts default remaining quantity and input limit when selecting a package',async()=>{
 await desktop();select('Hình thức xuất kho','Request');await tick();await tick();select('Yêu cầu vật tư đã duyệt','MR');await tick();await tick()
 await choose('Đơn vị xuất dòng 1','Bao')
 const qty=document.querySelector('input[aria-label="Số lượng dòng 1"]');assert.ok(qty);assert.equal(Number(qty.value),2);assert.equal(Number(qty.max),2)
 assert.match(document.body.textContent,/Còn 50 kg/);assert.match(document.body.textContent,/50 kg/)
})
test('mobile issue enables configured units and previews the correct quantity to deduct',async()=>{
 view=mount(Warehouse);await tick();await tick()
 const button=[...document.querySelectorAll('button')].find(e=>e.textContent.includes('Xuất kho'));assert.ok(button);button.click();await tick();await tick()
 await choose('Tên hàng','Phân thử');const unit=document.querySelector('select[aria-label="Đơn vị"]');assert.equal(unit.disabled,false)
 select('Đơn vị','Bao');input('Số lượng','2');await tick();assert.match(view.root.textContent,/Trừ tồn: 50 kg/)
 await choose('Người nhận hàng','Người nhận thử');input('Lô / nơi sử dụng','A01')
 view.root.querySelector('form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await tick();await tick()
 const save=calls.find(c=>c.method.endsWith('.create_draft'));assert.ok(save);assert.equal(save.args.lines[0].uom,'Bao');assert.equal(save.args.lines[0].qty,2)
})
