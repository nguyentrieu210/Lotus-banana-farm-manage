import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,document,window} from './support/mount.mjs'
Object.defineProperty(globalThis,'customElements',{value:window.customElements,configurable:true})

// /work after the owner's decision of 11/11/2026: tổ trưởng keep their tabs (no Vật tư tab); the đội trưởng creates and
// approves yêu cầu cấp vật tư: "chờ bạn duyệt" heads Xác nhận, the requests sit in Giao việc, ?request= opens one.
let calls=[],supervised=[]
const crews=[{name:'C',team_name:'Đội A + B',zones:['A']}]
globalThis.fetch=async(url,opts={})=>{
 const u=new URL(url,'http://localhost'),method=u.pathname.split('/api/method/')[1]||''
 calls.push({method,query:Object.fromEntries(u.searchParams)})
 const message=method==='lotus_farm.field_report.bootstrap'?{user:'u@example.invalid',farms:[{name:'F',farm_name:'Vườn'}],today:'2026-11-11',csrf_token:'x'}:
  method==='lotus_farm.field_report.setup'?{crews,my_crews:['C'],supervised_crews:supervised,teams:[{name:'T3',team_name:'Tổ 3',lotus_parent_team:'C',active:1}],my_teams:['T3'],blocks:[],works:[],zones:['A']}:
  method==='lotus_farm.issue_request.requests'?{rows:[{name:'MR-1',state:'Chờ duyệt',state_code:'sent',can_approve:true,needed:'2026-11-12'},{name:'MR-2',state:'Chờ duyệt',state_code:'sent',can_approve:true,needed:'2026-11-12'}],counts:{sent:2,approve:2}}:
  method==='lotus_farm.issue_request.detail'?{name:u.searchParams.get('name'),modified:'m',state:'Chờ duyệt',state_code:'sent',title:'Phun thuốc · Tổ 3',items:[],actions:{approve:true}}:[]
 return {ok:true,status:200,json:async()=>({message})}
}
const Work=await load('WorkMobile.vue')
async function settle(){for(let i=0;i<14;i++)await tick()}
const tabs=()=>[...document.querySelectorAll('.lotus-pwa-bottom .lotus-sr-only')].map(e=>e.textContent.trim())
const tab=label=>document.querySelector(`.lotus-pwa-bottom [aria-label="${label}"]`)
test.beforeEach(()=>{calls=[];window.history.replaceState({},'','/work')})

test('a tổ trưởng keeps Hôm nay · Tôi and has no Vật tư tab',async()=>{
 supervised=[]
 const view=mount(Work);await settle()
 assert.deepEqual(tabs(),['Hôm nay','Tôi'])
 assert.equal(calls.filter(c=>c.method==='lotus_farm.issue_request.requests').length,0)
 view.unmount()
})

test('a đội trưởng keeps 4 tabs; Xác nhận starts with the requests waiting for them, Giao việc lists the requests',async()=>{
 supervised=['C']
 const view=mount(Work);await settle()
 assert.deepEqual(tabs(),['Hôm nay','Xác nhận','Giao việc','Tôi'])
 tab('Xác nhận').click();await settle()
 const card=document.querySelector('.issue-requests__approve')
 assert.ok(card,'approve card');assert.match(card.textContent,/2 yêu cầu vật tư chờ bạn duyệt/)
 const main=document.querySelector('#lotus-content')
 assert.ok(main.textContent.indexOf('chờ bạn duyệt')<main.textContent.indexOf('Màu dây'),'the card heads the tab')
 tab('Giao việc').click();await settle()
 assert.match(main.textContent,/Yêu cầu cấp vật tư/)
 assert.ok([...main.querySelectorAll('button')].some(b=>b.textContent.includes('Đề nghị cấp vật tư')))
 view.unmount()
})

test('?request= opens Xác nhận and that request, then leaves the address',async()=>{
 supervised=['C']
 window.history.replaceState({},'','/work?request=MR-7')
 const view=mount(Work);await settle()
 assert.ok(document.querySelector('.issue-requests__approve'),'on Xác nhận')
 assert.ok(calls.some(c=>c.method==='lotus_farm.issue_request.detail'&&c.query.name==='MR-7'))
 assert.ok([...document.querySelectorAll('dialog[open]')].some(d=>/Phun thuốc · Tổ 3/.test(d.textContent)),'the request opens')
 assert.equal(new URL(location.href).searchParams.get('request'),null)
 view.unmount()
})
