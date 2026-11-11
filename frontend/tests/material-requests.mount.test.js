import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,h,document,window} from './support/mount.mjs'

// Cards as lotus_farm.issue_request.requests returns them: `state` is the label, `state_code` the code.
const labels={sent:'Chờ duyệt',returned:'Trả lại',waiting:'Chờ cấp',partial:'Đã cấp một phần',done:'Đã cấp đủ'}
const row=(name,code,extra={})=>({name,title:'Phun thuốc · Tổ 3 · A12',state:labels[code],state_code:code,overdue:false,crew:'C',crew_name:'Đội A + B',team:'T3',team_name:'Tổ 3',work_name:'Phun thuốc',
 blocks:['A12','A13'],warehouse:'Kho vườn - L',needed:'2026-11-12',lines:2,open_lines:2,approver_name:'Đội trưởng A',can_approve:false,...extra})
const list=()=>({rows:[row('MR-1','sent',{can_approve:true}),row('MR-2','sent'),row('MR-3','returned'),row('MR-4','waiting',{needed:'2026-11-09',overdue:true}),row('MR-5','partial'),row('MR-6','done')]})
const setup={supervised_crews:['C'],teams:[{name:'T3',team_name:'Tổ 3',lotus_parent_team:'C',active:1},{name:'T5',team_name:'Tổ 5',lotus_parent_team:'C',active:1}]}

let calls=[],replies={}
globalThis.fetch=async(url,opts={})=>{
 const u=new URL(url,'http://localhost'),method=u.pathname.split('/api/method/lotus_farm.issue_request.')[1]
 const call={method,query:Object.fromEntries(u.searchParams),body:opts.body?JSON.parse(opts.body):null}
 calls.push(call)
 if(!(method in replies))return {ok:false,status:417,json:async()=>({message:'Missing '+method})}
 return {ok:true,status:200,json:async()=>({message:typeof replies[method]==='function'?replies[method](call):replies[method]})}
}
const List=await load('components/field/MaterialRequests.vue')
async function settle(){for(let i=0;i<10;i++)await tick()}
const dialog=()=>[...document.querySelectorAll('dialog[open]')].at(-1)
function show(props={}){calls=[];return mount({setup:()=>()=>h(List,{farm:'F',crew:'C',setup,...props})})}

test('count cards: chờ bạn duyệt, chờ duyệt, trả lại, chờ cấp, đang cấp, đã cấp',async()=>{
 replies={requests:list()}
 const view=show({compact:true});await settle()
 assert.equal(calls[0].method,'requests');assert.equal(calls[0].query.crew,'C');assert.equal(calls[0].query.view,'open')
 const cards=[...view.root.querySelectorAll('.issue-count')].map(c=>c.querySelector('strong').textContent+' '+c.querySelector('span').textContent)
 assert.deepEqual(cards,['1 Chờ bạn duyệt','2 Chờ duyệt','1 Trả lại','1 Chờ cấp','1 Đang cấp','1 Đã cấp (7 ngày)'])
 assert.ok([...view.root.querySelectorAll('button')].some(b=>b.textContent.includes('Đề nghị cấp vật tư')))
 view.root.querySelectorAll('.issue-count')[1].click();await settle()
 assert.match(dialog().textContent,/Chờ duyệt/)
 assert.deepEqual([...dialog().querySelectorAll('.issue-card strong')].map(s=>s.closest('.issue-card').textContent.match(/MR-\d/)[0]),['MR-1','MR-2'])
 view.unmount()
})

test('the server counts win over the rows',async()=>{
 replies={requests:{...list(),counts:{draft:0,sent:7,returned:0,waiting:3,picking:0,partial:0,done:4,closed:0,cancelled:0,approve:0,overdue:1}}}
 const view=show({compact:true});await settle()
 const cards=[...view.root.querySelectorAll('.issue-count')].map(c=>c.querySelector('strong').textContent+' '+c.querySelector('span').textContent)
 assert.deepEqual(cards,['7 Chờ duyệt','0 Trả lại','3 Chờ cấp','0 Đang cấp','4 Đã cấp (7 ngày)'],'no "chờ bạn duyệt" card when there is nothing to approve')
 view.unmount()
})

test('approve view: one card "N yêu cầu vật tư chờ bạn duyệt", hidden when none',async()=>{
 replies={requests:{rows:[row('MR-1','sent',{can_approve:true}),row('MR-2','sent',{can_approve:true})],counts:{sent:2,approve:2}}}
 let view=show({compact:true,view:'approve'});await settle()
 assert.equal(calls[0].query.view,'approve')
 assert.match(view.root.textContent,/2 yêu cầu vật tư chờ bạn duyệt/)
 view.unmount()
 replies={requests:{rows:[]}}
 view=show({compact:true,view:'approve'});await settle()
 assert.equal(view.root.querySelector('.issue-count'),null)
 view.unmount()
})

test('full list: filters on one row, overdue label, a card opens the request',async()=>{
 replies={requests:list(),detail:{name:'MR-4',modified:'m',state:'Chờ cấp',state_code:'waiting',items:[],actions:{}}}
 const view=show({view:'all'});await settle()
 const bar=view.root.querySelector('.issue-requests__filters')
 assert.ok(bar,'one filter row');assert.ok(bar.querySelector('[aria-label="Trạng thái"]'));assert.ok(bar.querySelector('[aria-label="Tổ"]'))
 const cards=[...view.root.querySelectorAll('.issue-card')]
 assert.equal(cards.length,6)
 assert.match(cards[0].textContent,/Quá hạn chưa cấp/,'overdue first and labelled')
 assert.ok(cards[0].classList.contains('is-late'))
 const state=bar.querySelector('[aria-label="Trạng thái"]')
 state.value='returned';state.dispatchEvent(new window.Event('change',{bubbles:true}));await settle()
 assert.equal(view.root.querySelectorAll('.issue-card').length,1)
 state.value='';state.dispatchEvent(new window.Event('change',{bubbles:true}));await settle()
 const team=bar.querySelector('[aria-label="Tổ"]')
 team.value='T5';team.dispatchEvent(new window.Event('change',{bubbles:true}));await settle()
 assert.equal(calls.at(-1).query.team,'T5','the tổ goes to the server')
 view.root.querySelector('.issue-card').click();await settle()
 assert.ok(calls.some(c=>c.method==='detail'))
 assert.match(dialog().textContent,/Yêu cầu cấp vật tư/)
 view.unmount()
})

test('a link with ?request= opens that request',async()=>{
 replies={requests:list(),detail:{name:'MR-9',modified:'m',state:'Chờ cấp',state_code:'waiting',items:[],actions:{}}}
 const view=show({view:'all',initialRequest:'MR-9'});await settle()
 assert.equal(calls.find(c=>c.method==='detail').query.name,'MR-9')
 view.unmount()
})

test('without the right to create, no button',async()=>{
 replies={requests:list()}
 const view=show({compact:true,setup:{supervised_crews:[],teams:[]}});await settle()
 assert.ok(![...view.root.querySelectorAll('button')].some(b=>b.textContent.includes('Đề nghị cấp vật tư')))
 view.unmount()
})
