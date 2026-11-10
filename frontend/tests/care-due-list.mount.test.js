import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,h,document,window} from './support/mount.mjs'

const row=(code,extra={})=>({farm_block:'b-'+code,code,zone:'A',work_type:'CL',work_name:'Cắt lá',last_done:'2026-10-20',due_date:'2026-11-03',overdue_days:7,
 status:'overdue',rule:'r1',repeat_days:14,assignment:null,work_team:null,team_name:'',area_ha:4,...extra})
const due=(extra={})=>({today:'2026-11-10',until:'2026-11-15',has_rules:true,can_assign:true,teams:[{name:'T1',team_name:'Tổ 01'},{name:'T2',team_name:'Tổ 02'}],
 rows:[row('A5'),row('A6',{status:'due',overdue_days:0,due_date:'2026-11-12',last_done:null}),row('A7',{assignment:'WA-1',work_team:'T2',team_name:'Tổ 02'}),
  row('A8',{status:'later',overdue_days:0,due_date:'2026-11-30'}),row('A5',{work_type:'SO',work_name:'Sửa ống nước',status:'later',overdue_days:0,due_date:'2026-11-24'})],
 summary:[{work_type:'CL',work_name:'Cắt lá',overdue:2,due:1,later:1,given:1,to_give:2},{work_type:'SO',work_name:'Sửa ống nước',overdue:0,due:0,later:1,given:0,to_give:0}],...extra})

let calls=[],replies={}
globalThis.fetch=async(url,opts={})=>{
 const u=new URL(url,'http://localhost'),method=u.pathname.replace('/api/method/lotus_farm.care_cycle.','')
 calls.push({method,query:Object.fromEntries(u.searchParams),body:opts.body?JSON.parse(opts.body):null})
 if(!(method in replies))return {ok:false,status:404,json:async()=>({message:'Missing '+method})}
 return {ok:true,status:200,json:async()=>({message:typeof replies[method]==='function'?replies[method](calls.at(-1)):replies[method]})}
}
const List=await load('components/field/CareDueList.vue')
async function settle(){for(let i=0;i<10;i++)await tick()}
const dialog=()=>document.querySelector('dialog[open]')
const button=(root,text)=>[...root.querySelectorAll('button')].find(b=>b.textContent.trim().startsWith(text))
function show(props={}){calls=[];return mount({setup:()=>()=>h(List,{farm:'F',crew:'C',...props})})}
function tickBox(label){
 const field=[...dialog().querySelectorAll('.care-due__lots li')].find(li=>li.textContent.includes(label))
 const box=field.querySelector('input[type=checkbox],button[role=checkbox]');box.click()
}
async function pickTeam(name){
 const select=dialog().querySelector('select')
 select.value=name;select.dispatchEvent(new window.Event('change',{bubbles:true}));await settle()
}

test('one card per việc with the lô late, due and left to give',async()=>{
 replies={due:()=>due()}
 const view=show();await settle()
 assert.equal(calls[0].method,'due');assert.equal(calls[0].query.crew,'C')
 const cards=[...view.root.querySelectorAll('.care-due__card')]
 assert.equal(cards.length,2)
 assert.match(cards[0].textContent,/Cắt lá.*2 lô quá hạn · 1 lô đến hạn.*1 lô đã giao · 2 lô chưa giao/)
 assert.ok(cards[0].classList.contains('is-late'))
 assert.match(cards[1].textContent,/Chưa lô nào đến hạn/)
 view.unmount()
})

test('a việc opens its lô: late and due first, the lô already given name their tổ and cannot be ticked',async()=>{
 replies={due:()=>due()}
 const view=show();await settle()
 view.root.querySelector('.care-due__card').click();await settle()
 assert.match(dialog().querySelector('.lotus-modal-form__header, header')?.textContent||dialog().textContent,/Giao Cắt lá/)
 const items=[...dialog().querySelectorAll('.care-due__lots li')]
 assert.deepEqual(items.map(li=>li.textContent.match(/Lô A\d/)[0]),['Lô A5','Lô A7','Lô A6'],'late first; a lô due later is not listed')
 assert.match(dialog().querySelector('.care-due__zone header').textContent,/Khu A.*Chọn cả khu/)
 assert.match(items[0].textContent,/Quá hạn 7 ngày · xong lần trước 20\/10\/2026/)
 assert.match(items[2].textContent,/Đến hạn 12\/11\/2026 · chưa làm lần nào/)
 assert.match(items[1].textContent,/đã giao Tổ 02/);assert.equal(items[1].querySelector('input[type=checkbox],button[role=checkbox]'),null)
 view.unmount()
})

test('the đội trưởng ticks lô, picks a tổ and gives them at once',async()=>{
 replies={due:()=>due(),assign:()=>({created:['WA-2','WA-3']})}
 const view=show();await settle()
 view.root.querySelector('.care-due__card').click();await settle()
 button(dialog(),'Chọn hết lô chưa giao').click();await settle()
 await pickTeam('T1')
 dialog().querySelector('button[type=submit]').click();await settle()
 const sent=calls.find(c=>c.method==='assign')
 assert.ok(sent,'assign is called')
 assert.equal(sent.body.work_type,'CL');assert.equal(sent.body.team,'T1');assert.equal(sent.body.crew,'C')
 assert.deepEqual(JSON.parse(sent.body.blocks),['b-A5','b-A6'])
 assert.equal(sent.body.due_date,'2026-11-15','the end of the period is the default hạn xong')
 assert.equal(dialog(),null,'the dialog closes')
 assert.match(view.root.querySelector('[role=status]').textContent,/Đã giao cắt lá 2 lô cho Tổ 01/)
 assert.equal(calls.filter(c=>c.method==='due').length,2,'the list is read again')
 view.unmount()
})

test('nothing is given without a tổ',async()=>{
 replies={due:()=>due(),assign:()=>({created:[]})}
 const view=show();await settle()
 view.root.querySelector('.care-due__card').click();await settle()
 tickBox('Lô A6');await settle()
 dialog().querySelector('button[type=submit]').click();await settle()
 assert.equal(calls.filter(c=>c.method==='assign').length,0)
 view.unmount()
})

test('a tổ trưởng sees the list but gives nothing',async()=>{
 replies={due:()=>due({can_assign:false,teams:[]})}
 const view=show();await settle()
 view.root.querySelector('.care-due__card').click();await settle()
 assert.equal(dialog().querySelectorAll('.care-due__lots input[type=checkbox],.care-due__lots button[role=checkbox]').length,0)
 assert.equal(dialog().querySelector('button[type=submit]'),null)
 view.unmount()
})

test('without any cycle the quản lý vườn is sent to set them',async()=>{
 replies={due:()=>due({has_rules:false,rows:[],summary:[]})}
 const view=show();await settle()
 assert.match(view.root.textContent,/Chưa có vòng chăm sóc nào/)
 assert.equal(view.root.querySelector('a').getAttribute('href'),'/lotus/cong-viec?field_view=cycles')
 view.unmount()
})

test('the period goes to the server',async()=>{
 replies={due:()=>due()}
 const view=show();await settle()
 const select=view.root.querySelector('.care-due__tools select')
 select.value='13';select.dispatchEvent(new window.Event('change',{bubbles:true}));await settle()
 assert.match(calls.at(-1).query.to_date||'',/^\d{4}-\d{2}-\d{2}$/)
 view.unmount()
})
