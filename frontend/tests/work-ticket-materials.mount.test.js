import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,h,document} from './support/mount.mjs'

// Spec 005 (US4): a phiếu giao việc shows the yêu cầu cấp vật tư made for it, and starts one with việc, tổ, lô filled.
const ticket={name:'WA-1',farm:'F',crew:'C',work_team:'T3',team_name:'Tổ 3',farm_block:'B12',block_code:'A12',work_type:'PHUN',work_name:'Phun thuốc',state:'Open',display:'Open',
 pay_mode:'Daywork',assigned_on:'2026-11-10',modified:'m',progress:{qty:0,days:0,sessions:0},entries:[],shares:[],actions:{}}
let calls=[]
globalThis.fetch=async(url)=>{
 const u=new URL(url,'http://localhost'),method=u.pathname.split('/api/method/')[1]
 calls.push({method,query:Object.fromEntries(u.searchParams)})
 const message=method==='lotus_farm.field_report.ticket'?ticket:
  method==='lotus_farm.issue_request.requests'?{rows:[{name:'MR-1',title:'Phun thuốc · Tổ 3 · A12',state:'Đã cấp một phần',state_code:'partial',needed:'2026-11-12',totals:{required:1.5,posted:1,draft:0}}]}:
  method==='lotus_farm.issue_request.form_data'?{today:'2026-11-11',teams:[{name:'T3',team_name:'Tổ 3'}],blocks:[{name:'B12',block_code:'A12',zone:'A',area_ha:1}],works:[{name:'PHUN',work_name:'Phun thuốc'}],warehouses:[],can_approve:true}:[]
 return {ok:true,status:200,json:async()=>({message})}
}
const Ticket=await load('components/field/WorkTicket.vue')
async function settle(){for(let i=0;i<12;i++)await tick()}

test('Vật tư cho phiếu này: the requests of the phiếu with đề nghị, đã cấp, còn and state; the button fills the form',async()=>{
 const view=mount({setup:()=>()=>h(Ticket,{name:'WA-1',setup:{teams:[],supervised_crews:['C']}})})
 await settle()
 const asked=calls.find(c=>c.method==='lotus_farm.issue_request.requests')
 assert.ok(asked);assert.equal(asked.query.assignment,'WA-1');assert.equal(asked.query.farm,'F');assert.equal(asked.query.crew,'C')
 assert.match(view.root.textContent,/Vật tư cho phiếu này/)
 const card=view.root.querySelector('.issue-card')
 assert.match(card.textContent,/Đã cấp một phần/)
 assert.match(card.textContent,/Đề nghị 1,5 · đã cấp 1 · còn 0,5/)
 const button=[...view.root.querySelectorAll('button')].find(b=>b.textContent.includes('Đề nghị cấp vật tư'))
 assert.ok(button);button.click();await settle()
 assert.ok(calls.some(c=>c.method==='lotus_farm.issue_request.form_data'))
 const form=[...document.querySelectorAll('dialog[open]')].find(d=>/Đề nghị cấp vật tư/.test(d.textContent))
 assert.ok(form,'the form opens');assert.match(form.textContent,/theo phiếu giao việc/,'the lô carries the phiếu')
 view.unmount()
})
