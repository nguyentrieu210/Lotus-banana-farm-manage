import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,document,window,h,ref} from './support/mount.mjs'
import {visibleBuyingNavigation,normalizeBuyingView} from '../src/procurement-navigation.js'
import {stockNavigation,normalizeStockView} from '../src/stock-navigation.js'
const MasterForm=await load('components/ProcurementMasterForm.vue')
const Masters=await load('components/ProcurementMasters.vue')
const Workspace=await load('components/ProcurementWorkspace.vue')
const Stock=await load('StockApp.vue')
const Receiving=await load('components/WarehouseReceiving.vue')
let view,calls=[],handler
const catalog={items:[],conversions:[],suppliers:[{name:'N',supplier_name:'NCC'}],warehouses:[],can_create:true,can_create_supplier:true,can_create_item:true,can_finance:false,can_view_finance:true,can_invoice:true,farms:[]}
globalThis.fetch=async(url,opts={})=>{const u=new URL(url,'http://localhost'),method=u.pathname.split('/api/method/')[1],args=opts.body?JSON.parse(opts.body):Object.fromEntries(u.searchParams);calls.push({method,args});return {ok:true,status:200,json:async()=>({message:await handler(method,args)})}}
async function click(label){const b=[...document.querySelectorAll('button')].find(x=>x.textContent.trim()===label);assert.ok(b,label);b.click();await tick();await tick()}
test.beforeEach(()=>{calls=[];handler=async(m,a)=>{
 if(m.endsWith('procurement_masters.options'))return {supplier_groups:[{name:'Local'}],item_groups:[{name:'Goods'}],uoms:[{name:'Nos'}],countries:[{name:'Vietnam'}],can_create_supplier:true,can_create_item:true}
 if(m.endsWith('procurement_masters.listing'))return {rows:[{name:'N',supplier_name:'NCC'}],total_count:51,has_more:!Number(a.start)}
 if(m.endsWith('procurement.bootstrap'))return a.company?catalog:{companies:[{name:'C'}]}
 if(m.endsWith('.invoices'))return {rows:[{name:'PI',supplier:'N',bill_no:'HD-1',date:'2026-10-24',amount:100,docstatus:1}],total_count:51,has_more:!Number(a.start)}
 if(m.endsWith('.invoice'))return {name:'PI',doctype:'Purchase Invoice',supplier:'N',bill_no:'HD-1',due_date:'2026-10-30',amount:100,outstanding_amount:80,items:[],taxes:[],docstatus:1}
 return []
}})
test.afterEach(()=>view?.unmount())
test('purchase menu separates finance and masters and warehouse lists its operations before its catalogues',()=>{
 assert.deepEqual(stockNavigation.filter(x=>!x.setup).map(x=>x.label),['Tồn kho','Nhập kho','Xuất kho','Chuyển kho','Kiểm kê','Sổ kho','Nhu cầu vật tư','Báo cáo nhập – xuất – tồn'])
 assert.deepEqual(stockNavigation.filter(x=>x.setup).map(x=>x.label),['Kho','Vật tư','Nhóm vật tư','Đơn vị tính'])
 assert.equal(normalizeStockView('history'),'receipts','old links to Phiếu kho open Nhập kho')
 assert.equal(normalizeStockView('setup'),'warehouses')
 const buyer=visibleBuyingNavigation({capabilities:{purchasing:true}})
 assert.ok(buyer.some(x=>x.id==='suppliers'));assert.ok(buyer.some(x=>x.id==='items'));assert.ok(!buyer.some(x=>x.finance))
 assert.equal(normalizeBuyingView('unknown'),'orders')
})
test('supplier profile exposes full identity but no bank editor to buyer and saves once while in flight',async()=>{
 let release;const gate=new Promise(r=>{release=r});const usual=handler;handler=async(m,a)=>m.endsWith('.save')?gate:usual(m,a)
 let saved
 view=mount(MasterForm,{company:'C',kind:'suppliers',onSaved:r=>{saved=r}});await tick();await tick()
 assert.match(view.root.textContent,/Mã số thuế/);assert.match(view.root.textContent,/Điều khoản thanh toán/);assert.doesNotMatch(view.root.textContent,/Số tài khoản NCC/)
 const name=view.root.querySelector('input[maxlength="140"]');name.value='NCC mới';name.dispatchEvent(new window.Event('input',{bubbles:true}));await tick()
 const form=view.root.querySelector('form');form.dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await tick();form.dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await tick()
 const saves=calls.filter(c=>c.method.endsWith('.save'));assert.equal(saves.length,1);assert.equal(saves[0].args.values.supplier_name,'NCC mới');assert.equal(saves[0].args.values.group,'Local');assert.ok(saves[0].args.client_key)
 release({name:'N-NEW'});await tick();assert.equal(saved.name,'N-NEW')
})
test('supplier listing pages and filters on server rather than truncating the local catalog',async()=>{
 view=mount(Masters,{company:'C',kind:'suppliers',mobile:true});await tick();await tick()
 await click('Sau');assert.equal(calls.filter(c=>c.method.endsWith('.listing')).at(-1).args.start,'50')
 // Search waits until typing pauses (220 ms) before asking the server.
 const input=view.root.querySelector('input');input.value='0123456789';input.dispatchEvent(new window.Event('input',{bubbles:true}));await new Promise(r=>setTimeout(r,300));await tick()
 const last=calls.filter(c=>c.method.endsWith('.listing')).at(-1);assert.equal(last.args.start,'0');assert.equal(last.args.search,'0123456789')
})
test('invoice inquiry is visible to reader, pages on server and opens original invoice inside workspace',async()=>{
 view=mount(Workspace,{company:'C',buyingView:'invoices',mobile:true,today:'2026-10-24'});await tick();await tick()
 assert.ok(calls.some(c=>c.method.endsWith('.invoices')));assert.ok(![...view.root.querySelectorAll('button')].some(x=>x.textContent==='Chi / tạm ứng NCC'))
 await click('Sau');assert.equal(calls.filter(c=>c.method.endsWith('.invoices')).at(-1).args.start,'50')
 const row=[...view.root.querySelectorAll('.van-cell')].find(x=>x.textContent.includes('PI'));assert.ok(row);row.click();await tick();assert.match(view.root.textContent,/Hóa đơn\s*HD-1/);assert.match(view.root.textContent,/Còn nợs*80/)
})
test('warehouse receipts list opens supplier receiving through the shared picker',async()=>{
 const usual=handler;handler=async(m,a)=>{
  if(m==='lotus_farm.warehouse.bootstrap')return {companies:[{name:'C'}],today:'2026-10-24',permissions:{'Item':true,'Warehouse':true,'Purchase Order':true,'Purchase Receipt':true,'Stock Entry':true}}
  if(m==='lotus_farm.warehouse.overview')return {warehouses:[{name:'K',warehouse_name:'Kho'}],items:[],total_count:0,catalogue_count:1,has_more:false,currency:'VND'}
  if(m==='lotus_farm.warehouse_planning.overview')return {orders:[{name:'PO',supplier:'N'}]}
  if(m==='lotus_farm.warehouse.documents')return {rows:[],total_count:0,has_more:false}
  return usual(m,a)
 }
 view=mount(Stock,{embedded:true,stockView:'history'});await tick();await tick()
 assert.equal(view.root.querySelector('[role=tab]'),null,'embedded Kho is navigated from the sidebar')
 assert.equal(view.root.querySelector('section.lotus-list-page').getAttribute('aria-label'),'Phiếu nhập kho')
 assert.equal(calls.find(c=>c.method==='lotus_farm.warehouse.documents').args.kind,'receipts')
 await click('Nhập theo đơn mua');assert.ok(calls.some(c=>c.method==='lotus_farm.warehouse_planning.overview'))
 assert.ok(!calls.some(c=>c.method==='lotus_farm.procurement.bootstrap'))
})
test('shared receiving includes actual receipt costs in the native draft request',async()=>{
 const usual=handler;handler=async(m,a)=>{
  if(m.endsWith('.purchase_order'))return {name:'PO',supplier:'N',currency:'VND',can_receive:true,items:[{line:'L',item_name:'Phân',remaining_qty:2,uom:'Nos',rate:100000,warehouse:'K'}]}
  if(m.endsWith('.receipt_accounts'))return {accounts:[{name:'E',account_name:'Chi phí'}],default_account:'E'}
  if(m.endsWith('.receive_order'))return {name:'PR'}
  if(m.endsWith('.purchase_receipt'))return {name:'PR',supplier:'N',docstatus:0,items:[],goods_total:100000,valuation_charges:3000,incoming_total:103000,currency:'VND'}
  return usual(m,a)
 }
 const handle=ref(null);view=mount({render:()=>h(Receiving,{ref:handle,company:'C',today:'2026-10-24'})});await tick()
 await handle.value.openOrder('PO');await tick()
 // Line grids label each cell by its column header and row number.
 function fill(label,value){const input=[...document.querySelectorAll('input')].find(x=>(x.getAttribute('aria-label')||'').startsWith(label));assert.ok(input,label);input.value=value;input.dispatchEvent(new window.Event('input',{bubbles:true}))}
 fill('Thực nhận dòng 1','1');await click('Thêm chi phí');fill('Khoản chi phí dòng 1','Bốc xếp thử');fill('Số tiền (VND) dòng 1','3000');await tick()
 await click('Ghi nhận hàng')
 const request=calls.find(c=>c.method.endsWith('.receive_order'));assert.ok(request);assert.equal(request.args.post,1);assert.equal(Number(request.args.quantities.L),1);assert.equal(request.args.additional_costs[0].amount,3000);assert.equal(request.args.additional_costs[0].expense_account,'E')
 assert.match(document.body.textContent,/Giá trị nhập\s*103\.000 VND/)
})
