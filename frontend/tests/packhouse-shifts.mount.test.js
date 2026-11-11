import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,h,document,window} from './support/mount.mjs'

const listRow=(extra={})=>({name:'PS-1',shift_code:'S1',posting_date:'2026-12-20',docstatus:1,input_kg:3000,finished_kg:2400,secondary_kg:300,loss_kg:300,cartons:181,
 packout_percent:80,stock_entry:null,bunches:140,lots:2,receipt_state:null,modified:'m1',...extra})
const offered=[{harvest_entry:'H5',farm_block:'b5',block_code:'A5',bunch_tag:'red',colour:'Đỏ',colour_code:'DO',week:43,posting_date:'2026-12-20',bunches:100,kg:2000,left:100},
 {harvest_entry:'H6',farm_block:'b6',block_code:'A6',bunch_tag:'red',colour:'Đỏ',colour_code:'DO',week:43,posting_date:'2026-12-20',bunches:40,kg:1000,left:40}]
const detail=(extra={})=>({doc:{name:'PS-1',shift_code:'S1',posting_date:'2026-12-20',docstatus:1,started_at:'2026-12-20 07:00:00',ended_at:'2026-12-20 16:00:00',input_kg:3000,
 finished_kg:2400,secondary_kg:300,loss_kg:300,cartons:181,packout_percent:80,stock_entry:null,modified:'m1',sources:[]},
 split:[{harvest_entry:'H5',block_code:'A5',colour:'Đỏ',bunches:100,kg:2000,finished_kg:1600,cartons:121,kg_per_bunch:20,cartons_per_bunch:1.21,packout_percent:80},
  {harvest_entry:'H6',block_code:'A6',colour:'Đỏ',bunches:40,kg:1000,finished_kg:800,cartons:60,kg_per_bunch:25,cartons_per_bunch:1.5,packout_percent:80}],
 can_write:true,can_receive:true,receipt_state:null,...extra})

let calls=[],replies={}
globalThis.fetch=async(url,opts={})=>{
 const u=new URL(url,'http://localhost'),method=u.pathname.replace('/api/method/','').replace('lotus_farm.shift.','')
 calls.push({method,query:Object.fromEntries(u.searchParams),body:opts.body?JSON.parse(opts.body):null})
 if(!(method in replies))return {ok:false,status:404,json:async()=>({message:'Missing '+method})}
 return {ok:true,status:200,json:async()=>({message:typeof replies[method]==='function'?replies[method](calls.at(-1)):replies[method]})}
}
const Shifts=await load('components/field/PackhouseShifts.vue')
async function settle(){for(let i=0;i<10;i++)await tick()}
const dialog=()=>document.querySelector('dialog[open]')
const button=(root,text)=>[...root.querySelectorAll('button')].find(b=>b.textContent.trim().startsWith(text))
function type(input,value){input.value=value;input.dispatchEvent(new window.Event('input',{bubbles:true}));input.dispatchEvent(new window.Event('change',{bubbles:true}))}
function show(){calls=[];return mount({setup:()=>()=>h(Shifts,{farm:'F'})})}

test('one card per shift with what went in, what came out and where its stock stands',async()=>{
 replies={shifts:()=>[listRow(),listRow({name:'PS-2',shift_code:'S2',docstatus:0,receipt_state:null})]}
 const view=show();await settle()
 const cards=[...view.root.querySelectorAll('.packhouse__card')]
 assert.equal(cards.length,2)
 // Spec 004: the kit shift card — status chip, then bunches in, kg packed and cartons, then kg in, lô and packout rate.
 assert.match(cards[0].textContent,/Ca S1 · 20\/12.*Chưa nhập kho.*Buồng vào\s*140.*Thành phẩm \(kg\)\s*2\.400.*Thùng\s*181.*3\.000 kg vào từ 2 lô · tỷ lệ đóng gói 80%/)
 assert.match(cards[1].textContent,/Đang mở/)
 view.unmount()
})

test('a new shift takes its bunches from confirmed harvest lines',async()=>{
 replies={shifts:()=>[],harvest_sources:()=>offered,save_shift:({body})=>detail({doc:{...detail().doc,docstatus:0}}),close_shift:()=>detail()}
 const view=show();await settle()
 button(view.root,'Thêm ca').click();await settle()
 assert.match(dialog().textContent,/Lô A5 · Đỏ tuần 43.*còn 100 buồng/)
 type(dialog().querySelector('input[placeholder="VD: S1"]'),'S1');await settle()
 const boxes=[...dialog().querySelectorAll('.packhouse__sources input[type=checkbox],.packhouse__sources button[role=checkbox]')]
 boxes[0].click();boxes[1].click();await settle()
 assert.match(dialog().textContent,/Đã chọn 140 buồng, 3\.000 kg đưa vào ca/)
 button(dialog(),'Lưu và đóng ca').click();await settle()
 const saved=calls.find(c=>c.method==='save_shift')
 assert.ok(saved,'save_shift is called')
 const values=JSON.parse(saved.body.values)
 assert.deepEqual(values.sources.map(s=>[s.farm_block,s.bunches,s.kg,s.harvest_entry]),[['b5',100,2000,'H5'],['b6',40,1000,'H6']])
 assert.equal(values.started_at.slice(11),'07:00:00')
 assert.ok(calls.some(c=>c.method==='close_shift'),'then the shift is closed')
 view.unmount()
})

test('a closed shift shows the split by lô; the accountant makes the draft receipt',async()=>{
 replies={shifts:()=>[listRow()],shift:()=>detail(),'lotus_farm.finance.costing.receive_shift':()=>({stock_entry:'MAT-1',kg:2700,amount:15000000,docstatus:0})}
 const view=show();await settle()
 view.root.querySelector('.packhouse__card').click();await settle()
 assert.match(dialog().textContent,/3\.000 kg vào · 2\.400 kg thành phẩm · 300 kg phụ phẩm · hao 300 kg · tỷ lệ đóng gói 80%/)
 await new Promise(r=>setTimeout(r,300));await settle()
 assert.ok(dialog().querySelector('.ag-row[row-id="H5"]')&&dialog().querySelector('.ag-row[row-id="H6"]'),'one row per source')
 button(dialog(),'Lập phiếu nhập kho thành phẩm').click();await settle()
 assert.ok(calls.some(c=>c.method==='lotus_farm.finance.costing.receive_shift'&&c.body.shift==='PS-1'))
 assert.match(view.root.querySelector('[role=status]').textContent,/Đã lập phiếu nhập kho nháp MAT-1/)
 view.unmount()
})

test('without the accountant role there is no receipt button',async()=>{
 replies={shifts:()=>[listRow()],shift:()=>detail({can_receive:false})}
 const view=show();await settle()
 view.root.querySelector('.packhouse__card').click();await settle()
 assert.equal(button(dialog(),'Lập phiếu nhập kho thành phẩm'),undefined)
 view.unmount()
})
