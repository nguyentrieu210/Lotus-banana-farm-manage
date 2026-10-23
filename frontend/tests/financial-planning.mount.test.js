import test from 'node:test'
import assert from 'node:assert/strict'
import {load,loadModule,createApp,h,tick,document,window} from './support/mount.mjs'
import {createPinia,setActivePinia} from 'pinia'
import {createRouter,createMemoryHistory} from 'vue-router'
import {newPlan,resizeRows,compareResults,resultCsv} from '../src/financial-planning.js'

const pinia=createPinia();setActivePinia(pinia)
const Component=await load('components/finance/FinancePlanning.vue')
const {useSession}=await loadModule('store.js')
const API='lotus_farm.finance.planning.'
let calls=[],handlers={}
globalThis.fetch=async(url,options={})=>{
 const target=new URL(url,'http://localhost:8080'),method=target.pathname.replace('/api/method/','')
 const args=options.body?JSON.parse(options.body):Object.fromEntries(target.searchParams)
 calls.push({method,args})
 try{const handler=handlers[method];if(!handler)throw Error('Unexpected API '+method);return {ok:true,status:200,json:async()=>({message:typeof handler==='function'?handler(args):handler})}}
 catch(e){return {ok:false,status:409,json:async()=>({_server_messages:JSON.stringify([JSON.stringify({message:e.message})])})}}
}
const totals={gross_kg:1000,sales_kg:800,revenue:8000000,operating_cost:5000000,profit:3000000,closing_cash:-2000000,funding_gap:2000000,receivables_after_horizon:0,payables_after_horizon:0}
const result={base:{totals,rows:[],warnings:[]},scenario:{totals,rows:[{month:'2026-01',...totals}],warnings:[]}}
function doc(extra={}){const values=newPlan('2026-10-23');Object.assign(values.rows[0],{gross_kg:1000,sales_kg:800,price_per_kg:10000,labour:5000000});return {name:'LFP-2026-00001',modified:'2026-10-23 10:00:00',state:'Draft',values,result,source_snapshot:{},...extra}}
function setup(extra={}){
 calls=[]
 handlers={[API+'overview']:{company:'Lotus',currency:'VND',plans:[{name:'LFP-2026-00001',title:'Kế hoạch 2026',start_month:'2026-01',month_count:12,state:'Draft'}],farms:[],can_write:true,can_approve:true,can_forecast:true,...extra},
  [API+'detail']:doc(),[API+'preview']:result}
}
async function mount(){
 Object.assign(useSession(),{user:'acc@lotus',today:'2026-10-23',ready:true,capabilities:{finance:true,finance_ledger:true}})
 const router=createRouter({history:createMemoryHistory('/lotus'),routes:[{path:'/:p(.*)*',component:{render:()=>null}}]})
 await router.push('/tai-chinh?tab=planning');await router.isReady()
 const root=document.createElement('div');document.body.append(root)
 const app=createApp({render:()=>h(Component)});app.use(pinia);app.use(router);app.mount(root)
 for(let i=0;i<5;i++)await tick()
 return {root,router,unmount(){app.unmount();root.remove()}}
}
const text=root=>root.textContent.replace(/\s+/g,' ')
const button=(root,label)=>[...root.querySelectorAll('button')].find(b=>b.textContent.trim()===label)
const modal=()=>document.querySelector('dialog[open]')
async function settle(){for(let i=0;i<5;i++)await tick()}
async function input(field,value){field.value=String(value);field.dispatchEvent(new window.Event('input',{bubbles:true}));await tick()}
async function field(label,value){const wrapper=[...modal().querySelectorAll('.lotus-field')].find(e=>e.textContent.includes(label));assert.ok(wrapper,'field '+label);await input(wrapper.querySelector('input'),value)}

test('plan months resize across years while retaining matching budgets',()=>{
 const values=newPlan('2026-10-23');values.rows[11].labour=500
 const rows=resizeRows({...values,start_month:'2026-12',month_count:3})
 assert.deepEqual(rows.map(r=>r.month),['2026-12','2027-01','2027-02'])
 assert.equal(rows[0].labour,500)
 assert.equal(rows[1].labour,0)
 const comparison=compareResults(result)
 assert.equal(comparison.find(r=>r.key==='funding_gap').difference,0)
 assert.match(resultCsv(result.scenario),/01\/2026/)
})

test('loads a saved plan and displays cash shortage and monthly budgets',async t=>{
 setup();const view=await mount()
 t.after(view.unmount)
 assert.match(text(view.root),/Thiếu vốn cao nhất\s*2\.000\.000 đ/)
 assert.ok(view.root.querySelectorAll('.ag-row').length>0)
 assert.match(text(view.root),/01\/2026/)
 assert.ok(button(view.root,'Lưu kế hoạch').disabled)
 view.unmount()
})

test('editing a month recomputes, then saves the full plan with the current revision',async t=>{
 setup();handlers[API+'save']=args=>({...doc(),values:JSON.parse(args.values),modified:'next'})
 const view=await mount()
 t.after(view.unmount)
 view.root.querySelector('.ag-row[row-id="2026-01"] .ag-cell').click();await settle()
 assert.match(modal().textContent,/Ngân sách tháng 01\/2026/)
 await field('Giá bán chưa VAT',12000)
 modal().querySelector('form').dispatchEvent(new window.Event('submit',{cancelable:true}));await settle()
 assert.ok(!button(view.root,'Lưu kế hoạch').disabled)
 assert.ok(button(view.root,'Lấy sản lượng dự thu').disabled,'save local edits before replacing source quantities')
 button(view.root,'Lưu kế hoạch').click();await settle()
 const sent=calls.find(c=>c.method===API+'save')
 assert.equal(sent.args.modified,'2026-10-23 10:00:00')
 assert.equal(JSON.parse(sent.args.values).rows[0].price_per_kg,12000)
 assert.ok(button(view.root,'Lưu kế hoạch').disabled)
 view.unmount()
})

test('invalid quantities stay in the row editor and never reach the server',async t=>{
 setup();const view=await mount()
 t.after(view.unmount)
 view.root.querySelector('.ag-row[row-id="2026-01"] .ag-cell').click();await settle()
 await field('Thành phẩm bán',1200)
 modal().querySelector('form').dispatchEvent(new window.Event('submit',{cancelable:true}));await settle()
 assert.match(modal().textContent,/không được vượt kg thu hoạch/)
 assert.equal(calls.filter(c=>c.method===API+'preview').length,0)
 view.unmount()
})

test('source import shows the proposed sources and sends their fingerprint',async t=>{
 setup();const source={name:'HF-1',month:'2026-01',farm:'F1',gross_kg:1000,sales_kg:800}
 handlers[API+'forecast_preview']={sources:[source],rows:[],warnings:['Phiếu qua nhiều tháng'],fingerprint:'FP1'}
 handlers[API+'apply_forecast']=()=>doc({source_snapshot:{sources:[source]}})
 const view=await mount();button(view.root,'Lấy sản lượng dự thu').click();await settle()
 t.after(view.unmount)
 assert.match(modal().textContent,/HF-1/)
 assert.match(modal().textContent,/Tháng không có nguồn về 0/)
 button(modal(),'Thay sản lượng các tháng').click();await settle()
 assert.deepEqual(calls.find(c=>c.method===API+'apply_forecast').args,{name:'LFP-2026-00001',modified:'2026-10-23 10:00:00',fingerprint:'FP1'})
 view.unmount()
})

test('stale save keeps the local changes and shows the error',async t=>{
 setup();handlers[API+'save']=()=>{throw Error('Kế hoạch đã thay đổi. Mở lại trước khi lưu.')}
 const view=await mount();view.root.querySelector('.ag-row[row-id="2026-01"] .ag-cell').click();await settle()
 t.after(view.unmount)
 await field('Vật tư (đ)',1234);modal().querySelector('form').dispatchEvent(new window.Event('submit',{cancelable:true}));await settle()
 button(view.root,'Lưu kế hoạch').click();await settle()
 assert.match(text(view.root),/Kế hoạch đã thay đổi/)
 assert.ok(!button(view.root,'Lưu kế hoạch').disabled)
 view.unmount()
})

test('approved plans and auditors cannot edit, import or approve',async()=>{
 setup();handlers[API+'detail']=doc({state:'Approved'})
 const approved=await mount()
 assert.equal(button(approved.root,'Lưu kế hoạch'),undefined)
 assert.equal(button(approved.root,'Lấy sản lượng dự thu'),undefined)
 assert.ok(button(approved.root,'Tính dự phóng').disabled,'approved results remain frozen')
 assert.ok(button(approved.root,'Nhân bản'))
 approved.unmount()
 setup({can_write:false,can_approve:false});const auditor=await mount()
 assert.equal(button(auditor.root,'Tạo kế hoạch'),undefined)
 assert.equal(button(auditor.root,'Duyệt kế hoạch'),undefined)
 auditor.unmount()
})

test('creating a plan persists its month horizon and stable request key',async t=>{
 setup({plans:[]});handlers[API+'save']=args=>({...doc(),values:JSON.parse(args.values)})
 const view=await mount();button(view.root,'Tạo kế hoạch').click();await settle()
 t.after(view.unmount)
 assert.match(modal().textContent,/Tháng bắt đầu/)
 modal().querySelector('form').dispatchEvent(new window.Event('submit',{cancelable:true}));await settle()
 const sent=calls.find(c=>c.method===API+'save')
 assert.equal(JSON.parse(sent.args.values).rows.length,12)
 assert.match(sent.args.request_key,/^[a-f0-9-]{36}$/)
 assert.match(text(view.root),/Nháp/)
 view.unmount()
})

test('reload and leaving the page ask before discarding unsaved budgets',async t=>{
 setup();const view=await mount();t.after(view.unmount)
 view.root.querySelector('.ag-row[row-id="2026-01"] .ag-cell').click();await settle()
 await field('Vật tư (đ)',1234);modal().querySelector('form').dispatchEvent(new window.Event('submit',{cancelable:true}));await settle()
 let navigation=view.router.push('/tai-chinh?tab=overview');await settle()
 assert.match(modal().textContent,/thay đổi chưa lưu/)
 button(modal(),'Hủy').click();await navigation;await settle()
 assert.equal(view.router.currentRoute.value.query.tab,'planning')
 button(view.root,'Làm mới').click();await settle()
 assert.match(modal().textContent,/Tải lại bản đã lưu/)
 button(modal(),'Đồng ý').click();await settle()
 assert.ok(button(view.root,'Lưu kế hoạch').disabled)
})

test('scenario changes hide stale totals and send user entered factors for recalculation',async t=>{
 setup();const view=await mount();t.after(view.unmount)
 button(view.root,'Dự phóng & dòng tiền').click();await settle()
 assert.ok(button(view.root,'Dự phóng & dòng tiền').classList.contains('on'))
 const label=[...view.root.querySelectorAll('.lotus-field')].find(e=>e.textContent.includes('Sản lượng (%)'))
 await input(label.querySelector('input'),75)
 assert.match(text(view.root),/Dữ liệu đã thay đổi/)
 assert.equal(view.root.querySelector('.fp-stats'),null)
 button(view.root,'Tính dự phóng').click();await settle()
 const request=calls.findLast(c=>c.method===API+'preview')
 assert.equal(JSON.parse(request.args.values).quantity_percent,75)
 assert.ok(view.root.querySelector('.fp-stats'))
})

test('chief approval requires confirmation and then locks the budget controls',async t=>{
 setup();handlers[API+'approve']=doc({state:'Approved',approved_by:'chief@lotus'})
 const view=await mount();t.after(view.unmount)
 button(view.root,'Duyệt kế hoạch').click();await settle()
 assert.equal(calls.filter(c=>c.method===API+'approve').length,0)
 button(modal(),'Đồng ý').click();await settle()
 assert.deepEqual(calls.find(c=>c.method===API+'approve').args,{name:'LFP-2026-00001',modified:'2026-10-23 10:00:00'})
 assert.equal(button(view.root,'Lưu kế hoạch'),undefined)
 assert.match(text(view.root),/Đã duyệt/)
})
