import test from 'node:test'
import assert from 'node:assert/strict'
import {load,mount,tick,h,window} from './support/mount.mjs'
Object.defineProperty(globalThis,'customElements',{value:window.customElements,configurable:true})

// Spec 005 (US5): Kho on the phone issues an approved yêu cầu cấp vật tư through the same create_draft / submit_document.
let calls=[]
globalThis.fetch=async(url,opts={})=>{
 const u=new URL(url,'http://localhost'),method=u.pathname.split('/api/method/lotus_farm.warehouse.')[1]
 const args=opts.body?JSON.parse(opts.body):Object.fromEntries(u.searchParams)
 calls.push({method,args})
 const message=method==='issue_lines'?{rows:[{item:'ANVIL',item_name:'Anvil 5SC',uom:'Litre',stock_uom:'Litre',required_qty:3,allocated_qty:0,remaining_qty:3,area:'A12',material_request:'MR-1',material_request_item:'L1',warehouse:'K'}],header:{warehouse:'K',receiver:'EMP',crew_name:'Đội A + B',team_name:'Tổ 3',work_name:'Phun thuốc'}}:
  method==='create_draft'?{doctype:'Stock Entry',name:'SE-1',docstatus:0}:
  method==='document'?{doctype:'Stock Entry',name:'SE-1',modified:'m',posting_date:'2026-11-11',items:[{item_name:'Anvil 5SC',qty:2,uom:'Litre',area:'A12',actual_qty:10}]}:
  method==='submit_document'?{ok:true}:null
 return {ok:true,status:200,json:async()=>({message})}
}
const Issue=await load('components/MobileIssueFromRequest.vue')
async function settle(){for(let i=0;i<10;i++)await tick()}
const rows=[{name:'MR-2',crew_name:'Đội C',needed:'2026-11-15'},{name:'MR-1',crew_name:'Đội A + B',team_name:'Tổ 3',work_name:'Phun thuốc',needed:'2026-11-09',blocks:['A12']}]

test('pick a request, change the quantity, save a draft, confirm and post',async()=>{
 calls=[];const done=[]
 const view=mount({setup:()=>()=>h(Issue,{company:'C',rows,employees:[{value:'EMP',label:'Người nhận'}],today:'2026-11-11',onDone:m=>done.push(m)})})
 await settle()
 const cards=[...view.root.querySelectorAll('.mobile-list-card')]
 assert.match(cards[0].textContent,/MR-1.*Quá hạn chưa cấp/,'by ngày cần, overdue said')
 cards[0].click();await settle()
 assert.deepEqual(calls[0],{method:'issue_lines',args:{company:'C',mode:'Request',name:'MR-1'}})
 const qty=view.root.querySelector('input[type=number],input[inputmode=decimal]');assert.ok(qty)
 qty.value='2';qty.dispatchEvent(new window.Event('input',{bubbles:true}));await settle()
 view.root.querySelector('form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await settle()
 const draft=calls.find(c=>c.method==='create_draft').args
 assert.equal(draft.kind,'issue');assert.equal(draft.issue_mode,'Request');assert.equal(draft.source,'K');assert.equal(draft.receiver_employee,'EMP');assert.ok(draft.client_event_id)
 assert.deepEqual(draft.lines,[{item:'ANVIL',qty:2,uom:'Litre',area:'A12',material_request:'MR-1',material_request_item:'L1'}])
 assert.match(view.root.textContent,/Tồn đang có: 10/)
 const post=[...view.root.querySelectorAll('button')].find(b=>b.textContent.includes('Ghi sổ phiếu'))
 assert.ok(post.disabled,'posting waits for the check')
 view.root.querySelector('.mobile-check').click();await settle()
 post.click();await settle()
 assert.deepEqual(calls.find(c=>c.method==='submit_document').args,{doctype:'Stock Entry',name:'SE-1',modified:'m'})
 assert.match(done[0],/Đã ghi sổ phiếu SE-1 theo yêu cầu MR-1/)
 view.unmount()
})

test('a link /warehouse?issue_request= goes straight to that request',async()=>{
 calls=[]
 const view=mount({setup:()=>()=>h(Issue,{company:'C',rows,employees:[],initial:'MR-1',today:'2026-11-11'})})
 await settle()
 assert.equal(calls[0].args.name,'MR-1')
 assert.ok(view.root.querySelector('form'),'the lines of MR-1 are on screen')
 view.unmount()
})

test('more than the remaining quantity is refused on the phone too',async()=>{
 calls=[]
 const view=mount({setup:()=>()=>h(Issue,{company:'C',rows,employees:[{value:'EMP',label:'Người nhận'}],initial:'MR-1',today:'2026-11-11'})})
 await settle()
 const qty=view.root.querySelector('input[type=number],input[inputmode=decimal]')
 qty.value='5';qty.dispatchEvent(new window.Event('input',{bubbles:true}));await settle()
 view.root.querySelector('form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));await settle()
 assert.equal(calls.filter(c=>c.method==='create_draft').length,0)
 assert.match(view.root.textContent,/vượt phần còn lại/)
 view.unmount()
})
