import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,document,window,h,ref} from './support/mount.mjs'
import {stockDraft,stockDraftRequest,stockUnits} from '../src/stock-document.js'
const Form=await load('components/StockDocumentForm.vue'),Receiving=await load('components/WarehouseReceiving.vue'),Link=await load('components/MobileLinkField.vue')
let view,handler,calls
globalThis.fetch=async(url,opts={})=>{const u=new URL(url,'http://localhost'),method=u.pathname.split('/api/method/')[1],args=opts.body?JSON.parse(opts.body):Object.fromEntries(u.searchParams);calls.push({method,args});return {ok:true,status:200,json:async()=>({message:await handler(method,args)})}}
test.beforeEach(()=>{calls=[];handler=async m=>m.endsWith('receipt_options')?{enabled:true,reasons:[{value:'Surplus',label:'Thừa kiểm kê'}]}:m.endsWith('purchase_order')?{name:'PO',supplier:'N',can_receive:true,currency:'VND',items:[{line:'L',item_name:'Hàng',remaining_qty:3,uom:'Nos',rate:10}]}:m.endsWith('receive_order')?{name:'PR'}:m.endsWith('purchase_receipt')?{name:'PR',docstatus:0,can_submit:true,can_print:true,items:[]}:{} })
test.afterEach(()=>view?.unmount())
function field(label){const l=[...document.querySelectorAll('label')].find(l=>l.textContent.replace('*','').trim()===label);return document.querySelector(`[aria-label="${label}"]`)||document.getElementById(l?.htmlFor)}
function fill(label,value){const e=field(label);assert.ok(e,label);e.value=value;e.dispatchEvent(new window.Event(e.tagName==='SELECT'?'change':'input',{bubbles:true}))}
async function click(text){const b=[...document.querySelectorAll('button')].find(e=>e.textContent.trim()===text);assert.ok(b,text);b.click();await tick();await tick()}
async function submit(){view.root.querySelector('form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await tick();await tick()}
for(const mobile of [false,true])for(const kind of ['receipt','issue','transfer','count'])test(`${mobile?'phone':'desktop'} ${kind} preserves the common document payload`,async()=>{
 const draft=ref({...stockDraft(kind,{date:'2026-10-24',warehouse:'K',event:'KEY'}),target:kind==='transfer'?'K2':'K',receiver_employee:'EMP',notes:'Sản xuất',receipt_reason:'Surplus',lines:[{item:'I',item_name:'Hàng',qty:2,rate:10,uom:'Nos',area:'A01'}]});let saved
 view=mount({render:()=>h(Form,{modelValue:draft.value,mobile,company:'C',warehouses:[{name:'K'},{name:'K2'}],employees:[{value:'EMP',label:'Người nhận'}],items:[{name:'I',item_name:'Hàng',stock_uom:'Nos'}],'onUpdate:modelValue':v=>draft.value=v,onSubmit:()=>saved=stockDraftRequest('C',draft.value)})});await tick();await tick()
 fill(kind==='count'?'Tồn thực đếm':'Số lượng','3');await tick();await submit()
 assert.ok(saved);assert.equal(saved.lines[0].qty,3);assert.equal(saved.client_event_id,'KEY');assert.equal(saved.kind,kind);assert.equal(saved.company,'C');assert.equal(saved.lines[0].area,'A01')
 if(kind==='receipt')assert.equal(saved.receipt_reason,'Surplus')
})
test('common form blocks same-warehouse transfer, missing receiver and excess planned issue',async()=>{
 const draft=ref({...stockDraft('transfer',{date:'2026-10-24',warehouse:'K'}),target:'K',lines:[{item:'I',qty:2,area:'A'}]});let saves=0
 view=mount({render:()=>h(Form,{modelValue:draft.value,mobile:true,company:'C','onUpdate:modelValue':v=>draft.value=v,onSubmit:()=>saves++})});await tick();await submit();assert.match(view.root.textContent,/Kho nhận phải khác/)
 draft.value={...draft.value,kind:'issue',receiver_employee:'',issue_mode:'Plan',lines:[{item:'I',qty:4,remaining_qty:3,area:'A'}]};await tick();await submit();assert.match(view.root.textContent,/vượt phần nhu cầu/)
 draft.value.lines[0].qty=2;await tick();await submit();assert.match(view.root.textContent,/HRMS/);assert.equal(saves,0)
})
test('package options retain native Item conversions without converting stock twice',()=>{
 assert.deepEqual(stockUnits({item:'I',uom:'Nos'},[{name:'I',stock_uom:'Nos',pack_uom:'Bao'}],[{parent:'I',uom:'Box'}]).map(r=>r.value),['Nos','Bao','Box'])
})
test('inline receiving sends base-unit partial quantity, reopens receipt and protects submit',async()=>{
 const handle=ref(null);view=mount({render:()=>h(Receiving,{ref:handle,mobile:true,inline:true,company:'C',today:'2026-10-24',confirm:async()=>true})});await handle.value.openOrder('PO');await tick()
 fill('Thực nhận','4');await tick();await submit();assert.equal(calls.filter(r=>r.method.endsWith('receive_order')).length,0)
 fill('Thực nhận','2');await tick();assert.equal(handle.value.hasChanges(),true);await submit();const r=calls.find(r=>r.method.endsWith('receive_order'));assert.equal(r.args.quantities.L,2);assert.ok(r.args.client_event_id);assert.equal(handle.value.hasChanges(),false)
 assert.ok(view.root.querySelector('a[href*="in-phieu"]'));assert.equal([...view.root.querySelectorAll('button')].find(e=>e.textContent==='Ghi sổ nhận hàng').disabled,true)
})
test('late receiving response cannot reopen after company changes',async()=>{
 let resolve;handler=async()=>new Promise(r=>resolve=r);const company=ref('C'),handle=ref(null)
 view=mount({render:()=>h(Receiving,{ref:handle,company:company.value,today:'2026-10-24',inline:true})});const pending=handle.value.openOrder('PO');await tick();company.value='OTHER';await tick();resolve({name:'PO',items:[]});await pending;await tick();assert.equal(handle.value.isOpen(),false);assert.doesNotMatch(view.root.textContent,/PO/)
})
test('remote mobile link ignores stale results and Enter while loading',async()=>{
 const pending=[],selected=[];view=mount(Link,{fetchOptions:q=>new Promise(resolve=>pending.push({q,resolve})),onSelect:r=>selected.push(r)})
 const input=view.root.querySelector('input');input.focus();await tick();pending[0].resolve([{value:'OLD',label:'Old'}]);await tick();input.value='new';input.dispatchEvent(new window.Event('input',{bubbles:true}));await new Promise(r=>setTimeout(r,180));await tick()
 const enter=new window.KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true});input.dispatchEvent(enter);assert.equal(enter.defaultPrevented,true);assert.equal(selected.length,0)
 pending.at(-1).resolve([{value:'NEW',label:'New'}]);await tick();assert.equal(document.querySelector('[role=option]').textContent.includes('New'),true);input.dispatchEvent(new window.KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true}));await tick();assert.equal(selected[0].value,'NEW')
})
