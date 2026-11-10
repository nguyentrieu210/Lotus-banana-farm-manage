import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,h,document,window} from './support/mount.mjs'

const rule=(extra={})=>({name:'r1',rule_name:'Cắt lá',work_type:'CL',farm_zone:null,repeat_days:14,valid_from:'2026-10-01',valid_to:null,version:1,
 approval_state:'Approved',notes:'',in_force:true,...extra})
const list=(extra={})=>({works:[{name:'CL',work_name:'Cắt lá',uom:'Ha',group:'Field'},{name:'SO',work_name:'Sửa ống nước',uom:'Ha',group:'Field'}],zones:['A','B'],can_edit:true,
 rules:[rule({name:'r2',version:2,repeat_days:7,valid_from:'2026-12-01',approval_state:'Draft',in_force:false}),rule(),
  rule({name:'r3',rule_name:'Sửa ống nước khu B',work_type:'SO',farm_zone:'B',repeat_days:30})],...extra})

let calls=[],replies={}
globalThis.fetch=async(url,opts={})=>{
 const u=new URL(url,'http://localhost'),method=u.pathname.replace('/api/method/lotus_farm.care_cycle.','')
 calls.push({method,query:Object.fromEntries(u.searchParams),body:opts.body?JSON.parse(opts.body):null})
 if(!(method in replies))return {ok:false,status:404,json:async()=>({message:'Missing '+method})}
 return {ok:true,status:200,json:async()=>({message:typeof replies[method]==='function'?replies[method](calls.at(-1)):replies[method]})}
}
const Settings=await load('components/field/CareCycleSettings.vue')
async function settle(){for(let i=0;i<10;i++)await tick()}
const dialog=()=>document.querySelector('dialog[open]')
const button=(root,text)=>[...root.querySelectorAll('button')].find(b=>b.textContent.trim().startsWith(text))
function type(input,value){input.value=value;input.dispatchEvent(new window.Event('input',{bubbles:true}));input.dispatchEvent(new window.Event('change',{bubbles:true}))}
function show(){calls=[];return mount({setup:()=>()=>h(Settings,{farm:'F'})})}

test('one card per cycle: the version in force, and the one waiting for approval',async()=>{
 replies={rule_list:()=>list()}
 const view=show();await settle()
 const cards=[...view.root.querySelectorAll('.care-cycles__card')]
 assert.equal(cards.length,2)
 assert.match(cards[0].textContent,/Cắt lá.*14 ngày một lần · cả vườn · từ 01\/10\/2026.*Chờ duyệt: 7 ngày · từ 01\/12\/2026/)
 assert.match(cards[1].textContent,/Sửa ống nước khu B.*30 ngày một lần · khu B/)
 view.unmount()
})

test('a cycle opens its versions; the quản lý vườn approves the one waiting',async()=>{
 replies={rule_list:()=>list(),approve_rule:()=>rule({name:'r2'})}
 const view=show();await settle()
 view.root.querySelector('.care-cycles__card').click();await settle()
 const versions=[...dialog().querySelectorAll('.care-cycles__versions li')]
 assert.match(versions[0].textContent,/Phiên bản 2 · 7 ngày.*Chờ duyệt/);assert.match(versions[1].textContent,/Phiên bản 1 · 14 ngày.*Đang áp dụng/)
 assert.equal(button(dialog(),'Tạo phiên bản mới'),undefined,'no second draft while one waits')
 button(versions[0],'Duyệt').click();await settle()
 assert.deepEqual(calls.find(c=>c.method==='approve_rule').body,{name:'r2'})
 assert.match(view.root.querySelector('[role=status]').textContent,/Đã duyệt phiên bản 2 của Cắt lá/)
 view.unmount()
})

test('a new cycle needs its việc before anything is saved',async()=>{
 replies={rule_list:()=>list({rules:[]}),save_rule:({body})=>({...rule(),...body,name:'r9',version:1,approval_state:'Draft',rule_name:'Sửa ống nước'})}
 const view=show();await settle()
 assert.match(view.root.textContent,/Chưa có vòng chăm sóc nào/)
 button(view.root,'Đặt vòng mới').click();await settle()
 const number=dialog().querySelector('input[inputmode=numeric]');type(number,'30');await settle()
 dialog().querySelector('button[type=submit]').click();await settle()
 assert.equal(calls.filter(c=>c.method==='save_rule').length,0,'a việc must be chosen first')
 view.unmount()
})

test('someone who is not quản lý vườn only reads',async()=>{
 replies={rule_list:()=>list({can_edit:false})}
 const view=show();await settle()
 assert.equal(button(view.root,'Đặt vòng mới'),undefined)
 view.root.querySelector('.care-cycles__card').click();await settle()
 assert.equal(button(dialog(),'Duyệt'),undefined)
 view.unmount()
})
